# Automotive Diagnostic Simulator

A working simulation of automotive ECU diagnostics built in Python.
Implements the full protocol stack used in real vehicles — CAN bus, ISO 15765-2 transport layer,
and UDS (ISO 14229) — across two communicating processes with no hardware required.

---

## Architecture

```
┌─────────────────────────┐     UDP localhost      ┌──────────────────────────┐
│      ECU Simulator       │  port 5000 ↔ port 5001 │    Diagnostic Tool        │
│                          │ ◄────────────────────► │                          │
│  ecu_state.py            │   ISO 15765-2 frames   │  uds_client.py           │
│  uds/ (one file/service) │                        │  formatter.py            │
│  can_interface.py        │                        │  can_interface.py        │
└─────────────────────────┘                        └──────────────────────────┘
```

The CAN bus is simulated over UDP sockets. Each datagram is a 12-byte CAN frame:
4 bytes arbitration ID + 8 bytes data. No CAN adapter or drivers needed.

---

## Standards Implemented

| Standard | What It Does |
|---|---|
| ISO 11898 | CAN bus — simulated over UDP localhost |
| ISO 15765-2 | CAN-TP — SF / FF / CF / FC frame handling |
| ISO 14229-1 | UDS — five diagnostic services |

---

## UDS Services

| SID | Service | Notes |
|---|---|---|
| `0x10` | Diagnostic Session Control | Switches ECU between Default, Extended, and Programming sessions |
| `0x22` | Read Data By Identifier | Reads live sensor values and ECU info via DID codes |
| `0x27` | Security Access | Two-step seed/key challenge-response to unlock protected functions |
| `0x14` | Clear DTC | Erases all stored fault codes (requires security unlock) |
| `0x19` | Read DTC Information | Reads stored Diagnostic Trouble Codes and their status bytes |

---

## Data Identifiers (DIDs)

| DID | Name | Example Value |
|---|---|---|
| `0xF190` | VIN | `SIMVIN00000000001` |
| `0xF187` | ECU Part Number | `SIM-ECU-PART-001` |
| `0xF189` | ECU Software Version | `SW:1.2.3` |
| `0xF186` | Active Diagnostic Session | `Extended Diagnostic` |
| `0x0100` | Engine RPM | `729 rpm` (time-varying) |
| `0x0101` | Coolant Temperature | `41 °C` (rises over time) |
| `0x0102` | Battery Voltage | `12152 mV / 12.15 V` |
| `0x0103` | Vehicle Speed | `46 km/h` (time-varying) |

---

## Project Structure

```
automotive-diagnostic-simulator/
├── ecu_simulator/
│   ├── main.py               # Event loop and UDS routing
│   ├── ecu_state.py          # Session, security, DTCs, live sensors
│   ├── can_interface.py      # ISO 15765-2 framing over UDP
│   └── uds/
│       ├── session.py        # 0x10
│       ├── read_data.py      # 0x22
│       ├── security.py       # 0x27
│       └── dtc.py            # 0x14 + 0x19
├── diagnostic_tool/
│   ├── main.py               # CLI with argparse subcommands
│   ├── uds_client.py         # Request builder and response parser
│   ├── can_interface.py      # Tester-side transport layer
│   └── formatter.py          # Colored terminal output (ANSI)
├── tests/
│   ├── test_session.py
│   ├── test_security.py
│   ├── test_read_data.py
│   └── test_dtc.py
└── requirements.txt
```

---

## Installation

Requires Python 3.10+

```bash
git clone https://github.com/hoomankheder/automotive-diagnostic-simulator.git
cd automotive-diagnostic-simulator
pip install python-can pytest
```

---

## Running

Open two terminals.

**Terminal 1 — ECU Simulator:**
```bash
cd ecu_simulator
python main.py
```

**Terminal 2 — Diagnostic Tool:**
```bash
cd diagnostic_tool

python main.py scan-all  # Read all live sensor values at once
python main.py read-did 0x0100  # Engine RPM
python main.py session extended  # Switch diagnostic session
python main.py security-access  # Perform security unlock (seed/key exchange)
python main.py read-dtc  # Read stored fault codes
python main.py clear-dtc  # Clear all fault codes (auto-unlocks if needed)
```

---

## Testing

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_session.py    ..   PASSED
tests/test_security.py   ...  PASSED
tests/test_read_data.py  ..   PASSED
tests/test_dtc.py        .    PASSED

```

Tests cover positive responses, negative responses (NRC validation),
and state-dependent behavior — session transitions, security enforcement,
and access control for protected services.

---

## Live Demo Output

```
──────────────────────────────────────────────────
  Live Data Scan — All DIDs
──────────────────────────────────────────────────
  ●  VIN                             SIMVIN00000000001
  ●  ECU Software Version            SW:1.2.3
  ●  Active Session                  Default
  ●  Engine RPM                      729 rpm
  ●  Coolant Temperature (°C)        41 °C
  ●  Battery Voltage (mV)            12152 mV  (12.15 V)
  ●  Vehicle Speed (km/h)            46 km/h

──────────────────────────────────────────────────
  Security Access (0x27)
──────────────────────────────────────────────────
  ✓  ECU unlocked successfully
  →  Seed : 0x1b8f
  →  Key  : 0xbe39  (seed XOR 0xA5B6)

──────────────────────────────────────────────────
  Read DTC Information (0x19)
──────────────────────────────────────────────────
  !  3 DTC(s) found:
     0x0c0100    0x09
     0x0b1200    0x08
     0x0e0300    0x0f
```

---

## How It Works

### CAN Bus Layer
The physical CAN bus is simulated using **UDP sockets on localhost**.
Each UDP datagram carries one CAN frame: 4 bytes of arbitration ID followed by 8 bytes of data.
The ECU listens on port `5000`, the diagnostic tool listens on port `5001`.

### Transport Layer (ISO 15765-2 / CAN-TP)
UDS messages longer than 7 bytes are split into multiple CAN frames.
The implementation handles all four frame types:
- **Single Frame (SF)** — complete message in one frame
- **First Frame (FF)** — first segment of a long message
- **Consecutive Frame (CF)** — remaining segments
- **Flow Control (FC)** — receiver tells sender to continue

### UDS Application Layer (ISO 14229)
Each UDS service is implemented as a separate Python module.
The ECU's main loop receives a raw payload, reads the Service ID (first byte),
routes it to the correct handler, and sends back either a positive response
or a Negative Response Code (NRC) explaining why the request was rejected.

### Security Access (0x27)
The seed/key algorithm used here is: `key = seed XOR 0xA5B6`.
In real ECUs this is a proprietary algorithm, often involving AES or
manufacturer-specific hash functions. The structure of the two-step
challenge-response is identical to production implementations.

---

The same protocol stack implemented here is used in production ECUs across
the automotive industry for end-of-line testing, field diagnostics, and
ECU reprogramming.

---

---


## License

MIT
