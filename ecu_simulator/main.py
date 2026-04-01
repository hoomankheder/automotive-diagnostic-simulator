"""
ECU Simulator — Main Entry Point
Automotive Diagnostic Simulator  |  github.com/hoomankheder/automotive-diagnostic-simulator

Listens on a virtual CAN bus and responds to UDS requests.
Run alongside diagnostic_tool/main.py in two separate terminals.

Usage:
    python main.py [--channel vcan0] [--log-level DEBUG]
"""

import argparse
import logging
import sys

from can_interface import CANInterface
from ecu_state import ECUState
from uds import session, read_data, security, dtc

# ---- UDS Service IDs ----
SID_SESSION    = 0x10
SID_READ_DATA  = 0x22
SID_SECURITY   = 0x27
SID_CLEAR_DTC  = 0x14
SID_READ_DTC   = 0x19

NRC_SERVICE_NOT_SUPPORTED = 0x11


def dispatch(payload: bytes, state: ECUState) -> bytes:
    """Route incoming UDS request to the appropriate service handler."""
    if not payload:
        return b''

    sid = payload[0]

    if sid == SID_SESSION:
        return session.handle(payload, state)
    elif sid == SID_READ_DATA:
        return read_data.handle(payload, state)
    elif sid == SID_SECURITY:
        return security.handle(payload, state)
    elif sid == SID_CLEAR_DTC:
        return dtc.handle_clear(payload, state)
    elif sid == SID_READ_DTC:
        return dtc.handle_read(payload, state)
    else:
        print(f"  [UDS] Unknown SID {sid:#04x}")
        return bytes([0x7F, sid, NRC_SERVICE_NOT_SUPPORTED])


def run(channel: str):
    state = ECUState()
    bus   = CANInterface(channel=channel)

    print("=" * 55)
    print("  Automotive ECU Simulator")
    print(f"  CAN channel : {channel}  (virtual)")
    print(f"  ECU name    : {state.ecu_name}")
    print("  Waiting for UDS requests... (Ctrl-C to stop)")
    print("=" * 55)

    try:
        while True:
            payload = bus.receive_request(timeout=None)
            if payload is None:
                continue

            print(f"\n→ REQ  {payload.hex(' ').upper()}")
            response = dispatch(payload, state)

            if response:
                bus.send(response)
                print(f"← RESP {response.hex(' ').upper()}")

    except KeyboardInterrupt:
        print("\nECU simulator stopped.")
    finally:
        bus.close()



def main():
    parser = argparse.ArgumentParser(description="Automotive ECU Simulator")
    parser.add_argument("--channel",   default="vcan0",
                        help="python-can virtual channel name (default: vcan0)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run(args.channel)


if __name__ == "__main__":
    main()
