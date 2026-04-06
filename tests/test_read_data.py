from ecu_simulator.ecu_state import ECUState
from ecu_simulator.uds.read_data import handle


def test_read_engine_rpm():
    ecu = ECUState()

    request = bytes([0x22, 0x01, 0x00])  # Example DID
    response = handle(request, ecu)

    assert response[0] == 0x62  # Positive response


def test_read_data_invalid_did():
    ecu = ECUState()

    request = bytes([0x22, 0xFF, 0xFF])
    response = handle(request, ecu)

    assert response[0] == 0x7F  # Negative response