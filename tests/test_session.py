from ecu_simulator.ecu_state import ECUState
from ecu_simulator.uds.session import handle


def test_switch_to_extended_session():
    ecu = ECUState()

    request = bytes([0x10, 0x03])  # Extended session
    response = handle(request, ecu)

    assert response[0] == 0x50  # Positive response
    assert ecu.session == 3     # Extended session (integer in your implementation)