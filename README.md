# Automotive Diagnostic Simulator

A fully functional simulation of automotive ECU diagnostics built in Python.
Implements **CAN bus communication**, **ISO 15765-2 transport layer (CAN-TP)**,
and **UDS (Unified Diagnostic Services / ISO 14229)** — the exact protocols
used in real vehicles by companies like Bosch, Continental, and Delphi.

No hardware required. Runs entirely on your laptop using UDP sockets to
simulate the CAN bus between two processes.

---

## Demo

```
──────────────────────────────────────────────────
  Live Data Scan — All DIDs
──────────────────────────────────────────────────
  ●  VIN                             SIMVIN00000000001
  ●  ECU Part Number                 SIM-ECU-PART-001
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
  DTC Code       Status
  ────────────  ────────
  0x0c0100     0x09
  0x0b1200     0x08
  0x0e0300     0x0f
```

---

## Architecture

```
┌─────────────────────────────┐         UDP localhost          ┌──────────────────────────────┐
│       ECU Simulator          │  ◄────────────────────────►   │     Diagnostic Tool           │
│                              │    port 5000 ←→ port 5001     │                               │
│  ecu_simulator/              │                               │  diagnostic_tool/             │
│  ├── main.py                 │   ISO 15765-2 CAN-TP frames   │  ├── main.py  (CLI)           │
│  ├── ecu_state.py            │                               │  ├── uds_client.py            │
│  ├── can_interface.py        │                               │  ├── can_interface.py         │
│  └── uds/                   │                               │  └── formatter.py             │
│      ├── session.py  0x10    │                               │                               │
│      ├── read_data.py 0x22   │                               │                               │
│      ├── security.py 0x27    │                               │                               │
│      └── dtc.py  0x14/0x19   │                               │                               │
└─────────────────────────────┘                               └──────────────────────────────┘
```

---

## Standards Implemented

| Standard | Description |
|---|---|
| ISO 11898 | CAN bus (simulated over UDP) |
| ISO 15765-2 | CAN Transport Protocol (Single Frame, First Frame, Consecutive Frame, Flow Control) |
| ISO 14229-1 | Unified Diagnostic Services (UDS) application layer |

---

## UDS Services

| Service ID | Name | What It Does |
|---|---|---|
| `0x10` | Diagnostic Session Control | Switches ECU between Default, Extended, and Programming sessions |
| `0x22` | Read Data By Identifier | Reads live sensor values and ECU info via DID codes |
| `0x27` | Security Access | Two-step seed/key challenge-response to unlock protected functions |
| `0x14` | Clear Diagnostic Information | Erases all stored fault codes (requires security unlock) |
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
│
├── ecu_simulator/              # Simulates the car's ECU (server side)
│   ├── main.py                 # Event loop — listens and routes UDS requests
│   ├── ecu_state.py            # Internal ECU state: sensors, session, DTCs, security
│   ├── can_interface.py        # ISO 15765-2 CAN-TP layer (UDP socket backend)
│   └── uds/                   # UDS service handlers (one file per service)
│       ├── __init__.py
│       ├── session.py          # 0x10 Diagnostic Session Control
│       ├── read_data.py        # 0x22 Read Data By Identifier
│       ├── security.py         # 0x27 Security Access (seed/key)
│       └── dtc.py              # 0x14 Clear DTC + 0x19 Read DTC
│
├── diagnostic_tool/            # Simulates the mechanic's scanner (client side)
│   ├── main.py                 # CLI entry point with subcommands
│   ├── uds_client.py           # High-level UDS request/response handler
│   ├── can_interface.py        # Tester-side CAN-TP layer (UDP socket backend)
│   └── formatter.py            # Colored terminal output
│
└── requirements.txt
```

---

## Installation

**Requirements:** Python 3.10 or higher

```bash
git clone https://github.com/hoomankheder/automotive-diagnostic-simulator.git
cd automotive-diagnostic-simulator
pip install python-can
```

> No other dependencies required. The CAN bus is simulated over localhost UDP sockets —
> no hardware, no drivers, no virtual CAN setup needed.

---

## Running

You need **two terminal windows** open at the same time.

**Terminal 1 — Start the ECU Simulator:**
```bash
cd ecu_simulator
python main.py
```

**Terminal 2 — Run diagnostic commands:**
```bash
cd diagnostic_tool

# Read all live sensor values at once
python main.py scan-all

# Read a specific sensor
python main.py read-did 0x0100        # Engine RPM
python main.py read-did 0xF190        # VIN

# Switch diagnostic session
python main.py session extended

# Perform security unlock (seed/key exchange)
python main.py security-access

# Read stored fault codes
python main.py read-dtc

# Clear all fault codes (auto-unlocks if needed)
python main.py clear-dtc
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

## License

MIT License — free to use, modify, and distribute.
