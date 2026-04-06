from ecu_simulator.ecu_state import ECUState, SECURITY_UNLOCKED
from ecu_simulator.uds.dtc import handle_read, handle_clear


def test_read_dtc_returns_data():
    ecu = ECUState()

    response = handle_read(bytes([0x19, 0x02, 0xFF]), ecu)

    assert response[0] == 0x59  # Positive response


def test_clear_dtc_requires_unlock():
    ecu = ECUState()
    ecu.session = 3  # Extended

    response = handle_clear(bytes([0x14, 0xFF, 0xFF, 0xFF]), ecu)

    assert response[0] == 0x7F  # Should fail without unlock


def test_clear_dtc_after_unlock():
    ecu = ECUState()
    ecu.session = 3
    ecu.security = SECURITY_UNLOCKED

    response = handle_clear(bytes([0x14, 0xFF, 0xFF, 0xFF]), ecu)

    assert response[0] == 0x54  # Success