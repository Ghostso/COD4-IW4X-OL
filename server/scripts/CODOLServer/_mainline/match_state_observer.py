"""Read-only sampling on the launcher's early client handle.

All offsets are tied to target build 1649370. The observer reports unreadable
fields as null rather than treating failed reads as zero.
"""
import json
import os
import struct
import time


def read_u32(read, address):
    raw = read(address, 4)
    return struct.unpack("<I", raw)[0] if len(raw) == 4 else None


def observe(read):
    imp = read_u32(read, 0x082E13FC)
    match = read_u32(read, 0x082E1518)
    return {
        "dw_room_imp": imp,
        "dw_room_imp_vtable": read_u32(read, imp) if imp else None,
        "room_start_gate": read(imp + 0x106E8, 16).hex() if imp else None,
        "room_start_address": read(imp + 0x7238, 67).hex() if imp else None,
        "room_start_session": read(imp + 0x7248, 8).hex() if imp else None,
        "room_start_key": read(imp + 0x7404, 16).hex() if imp else None,
        "connection_state": read_u32(read, 0x076446B0),
        "startgame_gate_enabled": read(0x0E36DDA0, 1).hex(),
        "gate_a_283": read(imp + 0x283, 1).hex() if imp else None,
        "gate_a_38710": read(imp + 0x38710, 1).hex() if imp else None,
        "gate_b": read(imp + 0x10614, 1).hex() if imp else None,
        "gate_b_code": read(0x0062FE80, 11).hex(),
        "dw_room_match_uber": match,
        "dw_room_match_uber_vtable": read_u32(read, match) if match else None,
        "match_state": read_u32(read, match + 0x20) if match else None,
        "match_timer_120": read(match + 0x120, 8).hex() if match else None,
        "match_timer_138": read(match + 0x138, 16).hex() if match else None,
        "start_requested": read(0x0849B61C, 4).hex(),
    }


def watch(handle, read_memory, log, pid, seconds=300.0, interval=0.05):
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "match_state_observer.jsonl")
    start = time.time()
    previous = None
    with open(output, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({
            "type": "provenance", "pid": pid, "build": "1649370",
            "source": "local runtime RTTI and dwRoomMatchUber 0x63C5E0",
            "read_only": True,
        }) + "\n")
        stream.flush()
        while time.time() - start < seconds:
            def read(address, size):
                return read_memory(handle, address, size)
            sample = observe(read)
            sample["t"] = round(time.time() - start, 3)
            significant = {k: v for k, v in sample.items() if k != "t"}
            if significant != previous:
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                previous = significant
            time.sleep(interval)
    log("-- [match observer] read-only state trace -> %s" % output)
