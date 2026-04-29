import sys
import json
import datetime
import os
import re
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

def parse_args():
    args = {
        "ip": None,
        "mode": None,
        "write_count": 1,
        "address": None,
        "count": 1,
        "value": None,
        "output": None
    }
    for arg in sys.argv[1:]:
        if arg.startswith("-ip="):
            args["ip"] = arg.split("=", 1)[1]
        elif arg.startswith("-mode="):
            mode_val = arg.split("=", 1)[1].lower()
            match = re.match(r"write-(\d+)", mode_val)
            if match:
                args["mode"] = "write-multi"
                args["write_count"] = int(match.group(1))
            else:
                args["mode"] = mode_val
        elif arg.startswith("-address="):
            args["address"] = int(arg.split("=", 1)[1])
        elif arg.startswith("-count="):
            args["count"] = int(arg.split("=", 1)[1])
        elif arg.startswith("-value="):
            args["value"] = int(arg.split("=", 1)[1])
        elif arg.startswith("-output="):
            args["output"] = arg.split("=", 1)[1]
    return args

def write_log(entry, filename):
    if not filename:
        return
    entry["timestamp"] = datetime.datetime.now().isoformat()
    try:
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                json.dump([entry], f, indent=2)
        else:
            with open(filename, "r") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]
                except json.JSONDecodeError:
                    data = []

            data.append(entry)

            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Failed to write to log file: {e}")

def test_connection(client, ip, log, output):
    if client.connect():
        print(f"[+] Successfully connected to Modbus server at {ip}")
        log["status"] = "connected"
        write_log(log, output)
        return True
    else:
        print(f"[!] Failed to connect to Modbus server at {ip}")
        log["status"] = "connection_failed"
        write_log(log, output)
        return False

def read_registers(client, address, count, log, output):
    print(f"[*] Reading {count} registers starting at address {address}...")
    result = client.read_holding_registers(address, count, unit=1)
    if result.isError():
        print("[!] Error reading holding registers.")
        log["result"] = "read_error"
    else:
        log["result"] = "read_success"
        log["registers"] = {str(address + i): val for i, val in enumerate(result.registers)}
        print("[+] Register values:")
        for reg, val in log["registers"].items():
            print(f"  Register {reg}: {val}")
    write_log(log, output)

def write_single_register(client, address, value, log, output):
    print(f"[*] Writing value {value} to register {address}...")
    result = client.write_register(address, value, unit=1)
    if result.isError():
        print("[!] Error writing to register.")
        log["result"] = "write_error"
    else:
        print(f"[+] Successfully wrote value {value} to register {address}.")
        log["result"] = "write_success"
    log["written_register"] = address
    log["written_value"] = value
    write_log(log, output)

def write_multiple_registers(client, start_address, value, count, log, output):
    print(f"[*] Writing value {value} to {count} registers starting at address {start_address}...")
    values = [value] * count
    result = client.write_registers(start_address, values, unit=1)
    if result.isError():
        print("[!] Error writing to multiple registers.")
        log["result"] = "write_multi_error"
    else:
        print(f"[+] Successfully wrote value {value} to registers {start_address} to {start_address + count - 1}.")
        log["result"] = "write_multi_success"
    log["written_registers"] = {str(start_address + i): value for i in range(count)}
    write_log(log, output)

if __name__ == "__main__":
    args = parse_args()
    log_entry = {
        "ip": args["ip"],
        "mode": args["mode"],
        "address": args["address"],
        "count": args["count"],
        "value": args["value"]
    }

    if not args["ip"]:
        print("Usage:")
        print("  python snowcrash.py -ip=<Modbus_IP> -mode=read -address=<start> -count=<n>")
        print("  python snowcrash.py -ip=<Modbus_IP> -mode=write -address=<reg> -value=<val>")
        print("  python snowcrash.py -ip=<Modbus_IP> -mode=write-<n> -address=<start> -value=<val>")
        print("  Optional: -output=<logfile.json>")
        sys.exit(1)

    client = ModbusTcpClient(args["ip"])

    try:
        if test_connection(client, args["ip"], log_entry, args["output"]):
            if args["mode"] == "read":
                if args["address"] is not None:
                    read_registers(client, args["address"], args["count"], log_entry, args["output"])
                else:
                    print("[!] Missing -address for read mode.")

            elif args["mode"] == "write":
                if args["address"] is not None and args["value"] is not None:
                    write_single_register(client, args["address"], args["value"], log_entry, args["output"])
                else:
                    print("[!] Missing -address or -value for write mode.")

            elif args["mode"] == "write-multi":
                if args["address"] is not None and args["value"] is not None:
                    write_multiple_registers(
                        client,
                        args["address"],
                        args["value"],
                        args["write_count"],
                        log_entry,
                        args["output"]
                    )
                else:
                    print("[!] Missing -address or -value for write-multi mode.")

    except ModbusException as e:
        print(f"[!] Modbus error: {e}")
        log_entry["error"] = str(e)
        write_log(log_entry, args["output"])
    except Exception as e:
        print(f"[!] General error: {e}")
        log_entry["error"] = str(e)
        write_log(log_entry, args["output"])
    finally:
        client.close()
        print("[*] Connection closed.")
