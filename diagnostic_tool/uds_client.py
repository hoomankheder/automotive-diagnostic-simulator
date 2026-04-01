"""
UDS Client
High-level UDS request/response handler.
Each method builds the correct request bytes, sends them,
and parses the ECU's response into something human-readable.
"""

from can_interface import TesterCANInterface

# Negative Response Code lookup table (ISO 14229-1 Annex A)
NRC_DESCRIPTIONS = {
    0x10: "General Reject",
    0x11: "Service Not Supported",
    0x12: "Sub-Function Not Supported",
    0x13: "Incorrect Message Length",
    0x22: "Conditions Not Correct",
    0x24: "Request Sequence Error",
    0x25: "No Response From Sub-Net Component",
    0x31: "Request Out Of Range",
    0x33: "Security Access Denied",
    0x35: "Invalid Key",
    0x36: "Exceeded Number Of Attempts",
    0x37: "Required Time Delay Not Expired",
    0x70: "Upload/Download Not Accepted",
    0x78: "Response Pending",
    0x7E: "Sub-Function Not Supported In Active Session",
    0x7F: "Service Not Supported In Active Session",
}

# Session names
SESSION_NAMES = {0x01: "Default", 0x02: "Programming", 0x03: "Extended Diagnostic"}

# Known DID names (for pretty printing)
DID_NAMES = {
    0xF190: "VIN",
    0xF187: "ECU Part Number",
    0xF189: "ECU Software Version",
    0xF186: "Active Session",
    0x0100: "Engine RPM",
    0x0101: "Coolant Temperature (°C)",
    0x0102: "Battery Voltage (mV)",
    0x0103: "Vehicle Speed (km/h)",
}


class UDSClient:

    def __init__(self, bus: TesterCANInterface):
        self.bus = bus

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, data: bytes) -> bytes | None:
        self.bus.send_request(data)
        return self.bus.receive_response()

    def _is_negative(self, resp: bytes) -> bool:
        return resp is not None and len(resp) >= 3 and resp[0] == 0x7F

    def _nrc_text(self, resp: bytes) -> str:
        nrc = resp[2]
        return NRC_DESCRIPTIONS.get(nrc, f"Unknown NRC {nrc:#04x}")

    # ------------------------------------------------------------------
    # 0x10 — Diagnostic Session Control
    # ------------------------------------------------------------------

    def session_control(self, session_id: int) -> dict:
        """Switch ECU diagnostic session."""
        resp = self._send(bytes([0x10, session_id]))

        if resp is None:
            return {"success": False, "error": "No response (timeout)"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}
        if resp[0] != 0x50:
            return {"success": False, "error": f"Unexpected SID {resp[0]:#04x}"}

        return {
            "success":  True,
            "session":  SESSION_NAMES.get(session_id, f"{session_id:#04x}"),
            "p2_ms":    int.from_bytes(resp[2:4], 'big'),
            "p2ext_ms": int.from_bytes(resp[4:6], 'big'),
        }

    # ------------------------------------------------------------------
    # 0x22 — Read Data By Identifier
    # ------------------------------------------------------------------

    def read_data_by_id(self, did: int) -> dict:
        """Read a single DID from the ECU."""
        resp = self._send(bytes([0x22, (did >> 8) & 0xFF, did & 0xFF]))

        if resp is None:
            return {"success": False, "error": "No response (timeout)"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}
        if resp[0] != 0x62:
            return {"success": False, "error": f"Unexpected SID {resp[0]:#04x}"}

        raw = resp[3:]
        return {
            "success":  True,
            "did":      did,
            "did_name": DID_NAMES.get(did, f"DID {did:#06x}"),
            "raw":      raw.hex(' ').upper(),
            "decoded":  _decode_did(did, raw),
        }

    # ------------------------------------------------------------------
    # 0x27 — Security Access
    # ------------------------------------------------------------------

    def security_access(self) -> dict:
        """Full seed/key exchange. Returns unlock result."""

        # Step 1: Request seed
        resp = self._send(bytes([0x27, 0x01]))
        if resp is None:
            return {"success": False, "error": "No response to seed request"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}

        seed = (resp[2] << 8) | resp[3]

        # Already unlocked (ECU returns seed = 0x0000)
        if seed == 0x0000:
            return {"success": True, "note": "ECU already unlocked"}

        # Step 2: Calculate and send key
        key = seed ^ 0xA5B6
        resp = self._send(bytes([0x27, 0x02, (key >> 8) & 0xFF, key & 0xFF]))

        if resp is None:
            return {"success": False, "error": "No response to key"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}

        return {"success": True, "seed": f"{seed:#06x}", "key": f"{key:#06x}"}

    # ------------------------------------------------------------------
    # 0x19 — Read DTC Information
    # ------------------------------------------------------------------

    def read_dtc_by_status(self, status_mask: int = 0xFF) -> dict:
        """Read all DTCs matching the status mask."""
        resp = self._send(bytes([0x19, 0x02, status_mask]))

        if resp is None:
            return {"success": False, "error": "No response (timeout)"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}
        if resp[0] != 0x59:
            return {"success": False, "error": f"Unexpected SID {resp[0]:#04x}"}

        # Parse DTC records: each is 3 bytes DTC + 1 byte status
        dtcs = []
        data = resp[3:]   # skip 0x59, sub, availMask
        i = 0
        while i + 3 < len(data):
            code   = (data[i] << 16) | (data[i+1] << 8) | data[i+2]
            status = data[i+3]
            dtcs.append({"code": f"{code:#08x}", "status": f"{status:#04x}"})
            i += 4

        return {"success": True, "dtcs": dtcs, "count": len(dtcs)}

    # ------------------------------------------------------------------
    # 0x14 — Clear DTC
    # ------------------------------------------------------------------

    def clear_dtc(self) -> dict:
        """Clear all DTCs (group = 0xFFFFFF = all)."""
        resp = self._send(bytes([0x14, 0xFF, 0xFF, 0xFF]))

        if resp is None:
            return {"success": False, "error": "No response (timeout)"}
        if self._is_negative(resp):
            return {"success": False, "error": self._nrc_text(resp)}

        return {"success": True}


# ------------------------------------------------------------------
# DID decoder — converts raw bytes to human-readable values
# ------------------------------------------------------------------

def _decode_did(did: int, raw: bytes) -> str:
    try:
        if did == 0xF186:
            val = raw[0]
            return SESSION_NAMES.get(val, f"Session {val:#04x}")
        if did == 0x0100:   # Engine RPM — 2 bytes big-endian
            return f"{int.from_bytes(raw, 'big')} rpm"
        if did == 0x0101:   # Coolant temp — 1 byte
            return f"{raw[0]} °C"
        if did == 0x0102:   # Battery voltage — 2 bytes, millivolts
            mv = int.from_bytes(raw, 'big')
            return f"{mv} mV  ({mv/1000:.2f} V)"
        if did == 0x0103:   # Vehicle speed — 1 byte
            return f"{raw[0]} km/h"
        # Default: try UTF-8 string, fall back to hex
        return raw.decode('utf-8', errors='replace').strip()
    except Exception:
        return raw.hex(' ').upper()
