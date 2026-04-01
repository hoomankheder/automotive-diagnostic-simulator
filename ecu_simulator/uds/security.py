"""
UDS Service 0x27 — Security Access (ISO 14229-1 §10.2)

Two-step challenge-response:
  Step 1  Request seed  → tester sends [0x27, 0x01]
                        ← ECU replies  [0x67, 0x01, seed_hi, seed_lo]

  Step 2  Send key      → tester sends [0x27, 0x02, key_hi, key_lo]
                        ← ECU replies  [0x67, 0x02]  (positive)
                                    or [0x7F, 0x27, 0x35]  (invalid key)

Algorithm (intentionally simple for demo):
  key = seed XOR 0xA5B6
"""

from ecu_state import ECUState, SESSION_DEFAULT, SECURITY_UNLOCKED

# Negative Response Codes
NRC_SUB_FUNCTION_NOT_SUPPORTED  = 0x12
NRC_CONDITIONS_NOT_CORRECT      = 0x22
NRC_REQUEST_SEQUENCE_ERROR      = 0x24
NRC_INVALID_KEY                 = 0x35


def handle(payload: bytes, state: ECUState) -> bytes:
    if len(payload) < 2:
        return _negative(NRC_CONDITIONS_NOT_CORRECT)

    sub = payload[1]

    # ---- 0x01 : Request Seed ----
    if sub == 0x01:
        if state.session == SESSION_DEFAULT:
            # Security Access not allowed in default session
            return _negative(NRC_CONDITIONS_NOT_CORRECT)

        if state.security == SECURITY_UNLOCKED:
            # Already unlocked — return seed 0x0000 per standard
            print("  [UDS] SecurityAccess → already unlocked (seed=0x0000)")
            return bytes([0x67, 0x01, 0x00, 0x00])

        seed = state.generate_seed()
        print(f"  [UDS] SecurityAccess → seed={seed:#06x}")
        return bytes([0x67, 0x01, (seed >> 8) & 0xFF, seed & 0xFF])

    # ---- 0x02 : Send Key ----
    elif sub == 0x02:
        if len(payload) < 4:
            return _negative(NRC_CONDITIONS_NOT_CORRECT)
        if state._seed is None:
            return _negative(NRC_REQUEST_SEQUENCE_ERROR)

        key = (payload[2] << 8) | payload[3]
        if state.validate_key(key):
            state.security = SECURITY_UNLOCKED
            state._seed = None
            print("  [UDS] SecurityAccess → UNLOCKED ✓")
            return bytes([0x67, 0x02])
        else:
            print(f"  [UDS] SecurityAccess → invalid key={key:#06x}")
            return _negative(NRC_INVALID_KEY)

    else:
        return _negative(NRC_SUB_FUNCTION_NOT_SUPPORTED)


def _negative(nrc: int) -> bytes:
    return bytes([0x7F, 0x27, nrc])
