"""
UDS Service 0x22 — Read Data By Identifier (ISO 14229-1 §11.2)

Data Identifiers (DIDs) exposed by this simulated ECU:
  0xF190  VIN (Vehicle Identification Number)
  0xF187  ECU Part Number
  0xF189  ECU Software Version
  0xF186  Active Diagnostic Session
  0x0100  Engine RPM          (2 bytes, big-endian, unit: rpm)
  0x0101  Coolant Temperature (1 byte,  unit: °C, offset 0)
  0x0102  Battery Voltage     (2 bytes, big-endian, unit: mV)
  0x0103  Vehicle Speed       (1 byte,  unit: km/h)
"""

import struct
from ecu_simulator.ecu_state import ECUState, SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING

# Negative Response Codes
NRC_REQUEST_OUT_OF_RANGE        = 0x31
NRC_CONDITIONS_NOT_CORRECT      = 0x22

# Static string DIDs
STATIC_DIDS: dict[int, bytes] = {
    0xF190: b"SIMVIN00000000001",        # 17-char VIN
    0xF187: b"SIM-ECU-PART-001 ",
    0xF189: b"SW:1.2.3",
}


def handle(payload: bytes, state: ECUState) -> bytes:
    """
    Request  : [0x22, DID_high, DID_low]
    Positive : [0x62, DID_high, DID_low, <data bytes>]
    Negative : [0x7F, 0x22, NRC]
    """
    if len(payload) < 3:
        return _negative(NRC_CONDITIONS_NOT_CORRECT)

    did = (payload[1] << 8) | payload[2]
    data = _read_did(did, state)

    if data is None:
        print(f"  [UDS] ReadDID  DID={did:#06x}  → NOT FOUND")
        return _negative(NRC_REQUEST_OUT_OF_RANGE)

    print(f"  [UDS] ReadDID  DID={did:#06x}  → {data.hex(' ').upper()}")
    return bytes([0x62, payload[1], payload[2]]) + data


# DID dispatch

def _read_did(did: int, state: ECUState) -> bytes | None:
    if did in STATIC_DIDS:
        return STATIC_DIDS[did]

    if did == 0xF186:
        return bytes([state.session])

    if did == 0x0100:
        return struct.pack(">H", state.engine_rpm)

    if did == 0x0101:
        return bytes([state.coolant_temp_c & 0xFF])

    if did == 0x0102:
        return struct.pack(">H", state.battery_voltage_mv)

    if did == 0x0103:
        return bytes([state.vehicle_speed_kmh & 0xFF])

    return None   # DID unknown


def _negative(nrc: int) -> bytes:
    return bytes([0x7F, 0x22, nrc])
