# snowcrash

A command-line Modbus TCP client for **read, single-write, and bulk-write** operations against holding registers, with structured JSON logging of every action. Built for hands-on offensive security training, controlled lab manipulation exercises, and authorized OT/ICS pentest work.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Mode](https://img.shields.io/badge/mode-active-red)
![Protocol](https://img.shields.io/badge/protocol-Modbus%20TCP-green)
![Use](https://img.shields.io/badge/use-authorized%20testing%20only-critical)

---

## ⚠️ Read This First

This tool **writes to industrial control devices**. Modbus has no authentication, no authorization, and no built-in safety interlocks — if a register is writable, this script will write to it. On a real PLC, that means changing setpoints, flipping processor modes, injecting faults, or disrupting the physical process the device controls.

**Use this tool only against:**
- Lab simulators you own (e.g., the [Simple HVAC Simulator](#))
- Equipment you have explicit, written authorization to test
- Training environments where impact is contained and intentional

Do not point this at production OT networks, vendor demo gear at a conference, or anything that could affect a process you don't fully understand. You are solely responsible for how you use this code.

---

## Overview

`snowcrash` is a single-purpose CLI for talking to Modbus TCP holding registers. Three modes:

| Mode | What it does |
|------|--------------|
| `read` | Reads N consecutive holding registers starting at a given address |
| `write` | Writes a single value to a single register (FC 6) |
| `write-N` | Writes the same value to N consecutive registers in one transaction (FC 16) |

Every operation — including connection attempts, errors, and successful writes — gets timestamped and appended to an optional JSON log file, giving you a structured evidence trail for reports or rule-back scenarios.

The name is a nod to Stephenson — the bulk-write mode lets you scribble identical values across a range of registers in one shot, which is exactly the kind of motion that crashes things that weren't designed to defend themselves.

---

## Features

- **Three operation modes** — read, single write, bulk write
- **JSON logging** — structured, timestamped, append-only; perfect for pentest evidence
- **Single-shot CLI** — easy to chain in shell scripts, orchestrate from other tools, or invoke from CI
- **Single dependency** — `pymodbus` and that's it
- **Clean error handling** — Modbus exceptions and general errors are logged separately

---

## Prerequisites

- Python 3.8 or newer
- `pymodbus` — the script uses `pymodbus.client.ModbusTcpClient`

> **Compatibility note:** This script passes `unit=1` to the read/write calls. That keyword was renamed to `slave=` in newer pymodbus releases. If you hit a `TypeError` mentioning `unit` after upgrading pymodbus, swap `unit=1` for `slave=1` throughout the script. See [Known Limitations](#known-limitations).

---

## Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/snowcrash.git
cd snowcrash

# (Optional) virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows

# Install the one dependency
pip install pymodbus
```

---

## Usage

The script uses `key=value` style flags rather than argparse-style `--key value`.

### Read mode

```bash
python snowcrash.py -ip=127.0.0.1 -mode=read -address=4 -count=3
```

Reads 3 consecutive holding registers starting at register address 4.

### Single write

```bash
python snowcrash.py -ip=127.0.0.1 -mode=write -address=4 -value=85
```

Writes the value `85` to register address 4.

### Bulk write (write-N)

```bash
python snowcrash.py -ip=127.0.0.1 -mode=write-10 -address=20 -value=0
```

Writes the value `0` to 10 consecutive registers starting at address 20. The number after `write-` controls how many registers get written in a single transaction.

### Logging to JSON

Add `-output=<filename>` to any command to append a structured entry to a JSON log file:

```bash
python snowcrash.py -ip=127.0.0.1 -mode=read -address=4 -count=3 -output=session.json
```

If the file doesn't exist it's created. If it exists, the new entry is appended to the existing JSON array.

---

## Argument Reference

| Flag | Required | Purpose |
|------|----------|---------|
| `-ip=` | Yes | Target Modbus TCP server IP address |
| `-mode=` | Yes | One of `read`, `write`, or `write-N` (where N is an integer) |
| `-address=` | Yes | Starting register address |
| `-count=` | Read mode | Number of registers to read |
| `-value=` | Write modes | Integer value to write |
| `-output=` | Optional | Path to JSON log file |

The default Modbus TCP port (502) and unit ID (1) are hardcoded.

---

## JSON Log Format

Each operation appends one object to a JSON array. Keys present depend on the mode and outcome:

```json
[
  {
    "ip": "127.0.0.1",
    "mode": "read",
    "address": 4,
    "count": 3,
    "value": null,
    "status": "connected",
    "timestamp": "2026-04-29T14:32:11.847291"
  },
  {
    "ip": "127.0.0.1",
    "mode": "read",
    "address": 4,
    "count": 3,
    "value": null,
    "result": "read_success",
    "registers": {
      "4": 72,
      "5": 0,
      "6": 75
    },
    "timestamp": "2026-04-29T14:32:11.962104"
  },
  {
    "ip": "127.0.0.1",
    "mode": "write",
    "address": 4,
    "count": 1,
    "value": 85,
    "status": "connected",
    "timestamp": "2026-04-29T14:33:02.118337"
  },
  {
    "ip": "127.0.0.1",
    "mode": "write",
    "address": 4,
    "count": 1,
    "value": 85,
    "result": "write_success",
    "written_register": 4,
    "written_value": 85,
    "timestamp": "2026-04-29T14:33:02.231558"
  }
]
```

That structure parses cleanly with `jq`, `pandas`, or any JSON-aware report generator.

---

## Lab Exercise Ideas

The cleanest pairing is with the [Simple HVAC Simulator](#) — fire up the simulator on `127.0.0.1:502`, then drive it from `snowcrash`:

**Read & confirm**
```bash
python snowcrash.py -ip=127.0.0.1 -mode=read -address=1 -count=70 -output=baseline.json
```
Pulls the entire register window from the simulator and saves it as a known-good baseline.

**Setpoint manipulation**
```bash
python snowcrash.py -ip=127.0.0.1 -mode=write -address=4 -value=85 -output=session.json
```
Drives the AC setpoint to 85°F. Watch the HMI react in real time.

**Bulk register zeroing**
```bash
python snowcrash.py -ip=127.0.0.1 -mode=write-50 -address=1 -value=0 -output=session.json
```
Writes zero across 50 registers in one transaction. Useful for fuzzing-style "what does the device do under unexpected bulk writes" exercises against your own lab gear.

**Scripted attack chains**

Because each invocation is a single shot, you can chain operations from a shell script:

```bash
#!/bin/bash
LOG=attack_chain.json
TARGET=127.0.0.1
python snowcrash.py -ip=$TARGET -mode=read   -address=1  -count=70 -output=$LOG  # recon
python snowcrash.py -ip=$TARGET -mode=write  -address=31 -value=0  -output=$LOG  # disable security
python snowcrash.py -ip=$TARGET -mode=write  -address=4  -value=99 -output=$LOG  # crank setpoint
python snowcrash.py -ip=$TARGET -mode=read   -address=1  -count=70 -output=$LOG  # confirm state
```

The resulting `attack_chain.json` is a complete, timestamped record of every action — directly usable in a pentest report or training debrief.

---

## Detection Engineering Use

Since the tool produces clean, predictable Modbus traffic patterns, it's also useful on the defensive side:

- Generate known-bad traffic against a lab target while running Snort/Suricata/Zeek
- Tune detection rules for unauthorized writes to processor mode, security mode, or setpoint registers
- Build labeled training datasets — capture clean Modbus traffic, then capture `snowcrash`-driven manipulation traffic, and feed both to your detection pipeline

---

## Known Limitations

- **Holding registers only** — no coils, no input registers, no discrete inputs. Function codes 3, 6, and 16 only.
- **`unit=` keyword may need updating** — recent `pymodbus` releases renamed the keyword to `slave=`. If you hit a `TypeError`, that's why.
- **Hardcoded port and unit ID** — port 502 and unit 1 are baked in. Edit the source for non-standard environments.
- **No bounds checking** — values are passed straight through. Out-of-range writes get whatever response the device provides.
- **Single-shot only** — no built-in loop, flood, or fuzz modes. Wrap with a shell loop if you need repetition.
- **No connection retry** — one connect attempt per invocation; if the link is flaky, handle retries from the shell.
- **Custom argument parser** — uses `-key=value` format, not standard `--key value`. Documented in the Usage section but worth knowing if you're scripting around it.

---

## Contributing

Issues and PRs welcome. A short list of high-value additions:

- Migrate from custom arg parsing to `argparse` for proper `--help`, validation, and shell completion
- Coil read/write support (FC 1, 5, 15) and input register support (FC 4)
- Configurable unit ID and port via flags
- Read-back-after-write verification mode
- Loop / fuzz / replay modes for sustained scenarios
- Update `unit=` to `slave=` for current pymodbus compatibility

---

## License

Add a license file (MIT, Apache 2.0, or similar) to declare reuse terms. Until then, all rights reserved by default.

Whatever license you pick, it does not exempt users from the legal and ethical obligations laid out in the disclaimer above.

---

## Author

Vibe-coded hands-on companion tool for OT/ICS cybersecurity training and authorized Modbus pentest work.
