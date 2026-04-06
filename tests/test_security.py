from ecu_simulator.ecu_state import ECUState, SECURITY_UNLOCKED
from ecu_simulator.uds.security import handle


def test_security_unlock_flow():
    ecu = ECUState()
    ecu.session = 3  # Extended session

    # Step 1: request seed
    seed_response = handle(bytes([0x27, 0x01]), ecu)

    assert seed_response[0] == 0x67

    seed = (seed_response[2] << 8) | seed_response[3]

    # Step 2: send correct key
    key = seed ^ 0xA5B6
    key_bytes = key.to_bytes(2, 'big')

    response = handle(bytes([0x27, 0x02]) + key_bytes, ecu)

    assert response[0] == 0x67
    assert ecu.security == SECURITY_UNLOCKED


def test_security_fails_in_default_session():
    ecu = ECUState()

    response = handle(bytes([0x27, 0x01]), ecu)

    assert response[0] == 0x7F  # Negative response