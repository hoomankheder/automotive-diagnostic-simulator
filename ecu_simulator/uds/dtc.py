"""
UDS DTC Services

  0x14 — Clear Diagnostic Information (ISO 14229-1 §12.3)
  0x19 — Read DTC Information       (ISO 14229-1 §12.2)

Supported 0x19 sub-functions:
  0x01  reportNumberOfDTCByStatusMask
  0x02  reportDTCByStatusMask
"""

from ecu_simulator.ecu_state import ECUState, SECURITY_UNLOCKED

# NRCs
NRC_CONDITIONS_NOT_CORRECT     = 0x22
NRC_REQUEST_OUT_OF_RANGE       = 0x31
NRC_SECURITY_ACCESS_DENIED     = 0x33
NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12


# ==========================================================
#  0x14 — Clear DTC
# ==========================================================

def handle_clear(payload: bytes, state: ECUState) -> bytes:
    """
    Request  : [0x14, 0xFF, 0xFF, 0xFF]  (group = all DTCs)
    Positive : [0x54]
    """
    if state.security != SECURITY_UNLOCKED:
        return bytes([0x7F, 0x14, NRC_SECURITY_ACCESS_DENIED])

    state.clear_dtcs()
    print("  [UDS] ClearDTC  → all DTCs cleared")
    return bytes([0x54])



#  0x19 — Read DTC Information


def handle_read(payload: bytes, state: ECUState) -> bytes:
    if len(payload) < 3:
        return bytes([0x7F, 0x19, NRC_CONDITIONS_NOT_CORRECT])

    sub  = payload[1]
    mask = payload[2]   # status mask

    if sub == 0x01:
        return _report_count(mask, state)
    elif sub == 0x02:
        return _report_dtcs(mask, state)
    else:
        return bytes([0x7F, 0x19, NRC_SUB_FUNCTION_NOT_SUPPORTED])



# Sub-function helpers


def _report_count(mask: int, state: ECUState) -> bytes:
    matching = [s for _, info in state.dtcs.items()
                if info["status"] & mask]
    count = len(matching)
    print(f"  [UDS] ReadDTC(0x01) mask={mask:#04x} → {count} DTC(s)")
    # Response: [0x59, 0x01, DTCStatusAvailabilityMask, formatId, count_hi, count_lo]
    return bytes([0x59, 0x01, 0xFF, 0x01,
                  (count >> 8) & 0xFF, count & 0xFF])


def _report_dtcs(mask: int, state: ECUState) -> bytes:
    matching = [(code, info) for code, info in state.dtcs.items()
                if info["status"] & mask]

    print(f"  [UDS] ReadDTC(0x02) mask={mask:#04x} → {len(matching)} DTC(s)")
    for code, info in matching:
        print(f"        DTC {code:#08x}  status={info['status']:#04x}"
              f"  \"{info['name']}\"")

    # Response: [0x59, 0x02, availMask, <DTC1 3-byte + status>, ...]
    resp = bytearray([0x59, 0x02, 0xFF])
    for code, info in matching:
        resp += bytes([(code >> 16) & 0xFF,
                       (code >>  8) & 0xFF,
                        code        & 0xFF,
                        info["status"]])
    return bytes(resp)
