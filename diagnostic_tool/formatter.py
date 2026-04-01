"""
Output Formatter
Handles all terminal output — colored, aligned, readable.
No external dependencies (uses only ANSI escape codes).
"""

# ANSI color codes
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _ok(text):    return f"{GREEN}✓{RESET}  {text}"
def _fail(text):  return f"{RED}✗{RESET}  {text}"
def _info(text):  return f"{CYAN}→{RESET}  {text}"
def _warn(text):  return f"{YELLOW}!{RESET}  {text}"


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'─' * 50}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 50}{RESET}")


def print_session(result: dict):
    header("Session Control (0x10)")
    if result["success"]:
        print(_ok(f"Session switched → {BOLD}{result['session']}{RESET}"))
        print(_info(f"P2 timeout    : {result['p2_ms']} ms"))
        print(_info(f"P2* timeout   : {result['p2ext_ms']} ms"))
    else:
        print(_fail(f"Failed: {result['error']}"))


def print_read_did(result: dict):
    header(f"Read Data By ID (0x22)  —  DID {result.get('did', '?'):#06x}")
    if result["success"]:
        print(_ok(f"{result['did_name']}"))
        print(_info(f"Raw bytes : {result['raw']}"))
        print(_info(f"Decoded   : {BOLD}{result['decoded']}{RESET}"))
    else:
        print(_fail(f"Failed: {result['error']}"))


def print_security(result: dict):
    header("Security Access (0x27)")
    if result["success"]:
        if "note" in result:
            print(_warn(result["note"]))
        else:
            print(_ok("ECU unlocked successfully"))
            print(_info(f"Seed : {result['seed']}"))
            print(_info(f"Key  : {result['key']}  (seed XOR 0xA5B6)"))
    else:
        print(_fail(f"Failed: {result['error']}"))


def print_dtcs(result: dict):
    header("Read DTC Information (0x19)")
    if not result["success"]:
        print(_fail(f"Failed: {result['error']}"))
        return

    count = result["count"]
    if count == 0:
        print(_ok("No active DTCs found"))
        return

    print(_warn(f"{count} DTC(s) found:"))
    print()
    print(f"  {'DTC Code':<14} {'Status'}")
    print(f"  {'─' * 12}  {'─' * 8}")
    for dtc in result["dtcs"]:
        print(f"  {RED}{dtc['code']}{RESET}     {dtc['status']}")


def print_clear_dtc(result: dict):
    header("Clear DTC (0x14)")
    if result["success"]:
        print(_ok("All DTCs cleared successfully"))
    else:
        print(_fail(f"Failed: {result['error']}"))


def print_scan_all(results: list):
    header("Live Data Scan — All DIDs")
    for r in results:
        if r["success"]:
            label = f"{r['did_name']:<30}"
            print(f"  {GREEN}●{RESET}  {label}  {BOLD}{r['decoded']}{RESET}")
        else:
            label = f"DID {r.get('did', '?'):#06x}"
            print(f"  {RED}●{RESET}  {label:<30}  {r['error']}")
    print()
