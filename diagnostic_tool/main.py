"""
Automotive Diagnostic Tool — CLI Entry Point
Automotive Diagnostic Simulator  |  github.com/hoomankheder/automotive-diagnostic-simulator

Sends UDS requests to the ECU Simulator over a virtual CAN bus.
Run AFTER starting ecu_simulator/main.py in a separate terminal.

Usage examples:
    python main.py session default
    python main.py session extended
    python main.py read-did 0xF190
    python main.py read-did 0x0100
    python main.py security-access
    python main.py read-dtc
    python main.py clear-dtc
    python main.py scan-all
"""

import argparse
import logging
import sys

from can_interface import TesterCANInterface
from uds_client   import UDSClient
from formatter    import (print_session, print_read_did, print_security,
                          print_dtcs, print_clear_dtc, print_scan_all)

# All DID codes exposed by the ECU simulator
ALL_DIDS = [0xF190, 0xF187, 0xF189, 0xF186, 0x0100, 0x0101, 0x0102, 0x0103]

# Session name → byte value
SESSION_MAP = {
    "default":     0x01,
    "programming": 0x02,
    "extended":    0x03,
}


def cmd_session(client: UDSClient, args):
    sid = SESSION_MAP.get(args.type.lower())
    if sid is None:
        print(f"Unknown session '{args.type}'. Choose: default, extended, programming")
        sys.exit(1)
    result = client.session_control(sid)
    print_session(result)


def cmd_read_did(client: UDSClient, args):
    try:
        did = int(args.did, 16)
    except ValueError:
        print(f"Invalid DID '{args.did}'. Use hex format, e.g. 0x0100")
        sys.exit(1)
    result = client.read_data_by_id(did)
    result["did"] = did
    print_read_did(result)


def cmd_security_access(client: UDSClient, args):
    # Security access only works in extended session
    # Auto-switch session first
    switch = client.session_control(0x03)
    if not switch["success"]:
        print(f"Could not switch to extended session: {switch['error']}")
        sys.exit(1)
    result = client.security_access()
    print_security(result)


def cmd_read_dtc(client: UDSClient, args):
    mask = int(args.mask, 16) if hasattr(args, 'mask') and args.mask else 0xFF
    result = client.read_dtc_by_status(mask)
    print_dtcs(result)


def cmd_clear_dtc(client: UDSClient, args):
    # Clear DTC requires security access — auto-unlock first
    client.session_control(0x03)
    unlock = client.security_access()
    if not unlock["success"]:
        print(f"Security unlock failed: {unlock['error']}")
        sys.exit(1)
    result = client.clear_dtc()
    print_clear_dtc(result)


def cmd_scan_all(client: UDSClient, args):
    results = []
    for did in ALL_DIDS:
        r = client.read_data_by_id(did)
        r["did"] = did
        results.append(r)
    print_scan_all(results)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diagnostic_tool",
        description="Automotive UDS Diagnostic Tool — talks to ECU Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py session extended
  python main.py read-did 0x0100
  python main.py security-access
  python main.py read-dtc
  python main.py clear-dtc
  python main.py scan-all
        """
    )

    parser.add_argument("--channel",   default="vcan0",
                        help="Virtual CAN channel (must match ECU simulator)")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    sub = parser.add_subparsers(dest="command", required=True)

    # session
    p_session = sub.add_parser("session", help="Switch diagnostic session")
    p_session.add_argument("type", choices=["default", "extended", "programming"])

    # read-did
    p_read = sub.add_parser("read-did", help="Read a DID value (e.g. 0x0100)")
    p_read.add_argument("did", help="DID in hex, e.g. 0x0100")

    # security-access
    sub.add_parser("security-access", help="Perform seed/key security unlock")

    # read-dtc
    p_dtc = sub.add_parser("read-dtc", help="Read stored DTCs")
    p_dtc.add_argument("--mask", default="FF",
                       help="Status mask in hex (default: FF = all)")

    # clear-dtc
    sub.add_parser("clear-dtc", help="Clear all stored DTCs (requires security unlock)")

    # scan-all
    sub.add_parser("scan-all", help="Read all known DIDs in one shot")

    return parser


COMMAND_MAP = {
    "session":         cmd_session,
    "read-did":        cmd_read_did,
    "security-access": cmd_security_access,
    "read-dtc":        cmd_read_dtc,
    "clear-dtc":       cmd_clear_dtc,
    "scan-all":        cmd_scan_all,
}


def main():
    parser = build_parser()
    args   = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    bus    = TesterCANInterface(channel=args.channel)
    client = UDSClient(bus)

    try:
        handler = COMMAND_MAP[args.command]
        handler(client, args)
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        bus.close()
        print()   # clean newline after output


if __name__ == "__main__":
    main()
