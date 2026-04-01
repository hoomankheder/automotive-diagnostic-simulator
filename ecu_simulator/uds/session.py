"""
UDS Service 0x10 — Diagnostic Session Control (ISO 14229-1 §9.2)

Allows the tester to switch the ECU between diagnostic sessions:
  0x01  defaultSession
  0x02  programmingSession
  0x03  extendedDiagnosticSession
"""

from ecu_state import ECUState, SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING

# UDS negative response codes
NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12
NRC_CONDITIONS_NOT_CORRECT      = 0x22

VALID_SESSIONS = {SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING}

SESSION_NAMES = {
    SESSION_DEFAULT:     "Default",
    SESSION_EXTENDED:    "Extended Diagnostic",
    SESSION_PROGRAMMING: "Programming",
}


def handle(payload: bytes, state: ECUState) -> bytes:
    """
    Request  : [0x10, subFunction]
    Positive : [0x50, subFunction, P2_high, P2_low, P2ex_high, P2ex_low]
    Negative : [0x7F, 0x10, NRC]
    """
    if len(payload) < 2:
        return _negative(NRC_CONDITIONS_NOT_CORRECT)

    sub = payload[1]

    if sub not in VALID_SESSIONS:
        return _negative(NRC_SUB_FUNCTION_NOT_SUPPORTED)

    state.session = sub
    print(f"  [UDS] Session → {SESSION_NAMES[sub]}")

    # P2 = 25 ms, P2* = 5000 ms (typical defaults, encoded as 2-byte big-endian)
    p2    = (25).to_bytes(2, 'big')
    p2ext = (5000).to_bytes(2, 'big')

    return bytes([0x50, sub]) + p2 + p2ext



def _negative(nrc: int) -> bytes:
    return bytes([0x7F, 0x10, nrc])
