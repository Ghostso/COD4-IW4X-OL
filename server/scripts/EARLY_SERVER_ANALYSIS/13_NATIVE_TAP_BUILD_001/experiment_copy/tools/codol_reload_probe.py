"""Passive C1 reload evidence; no debugger, writes, or gameplay assertions.

Pass the current C1 PID and its verified MainModule base. Capture during an
equipped fast-mag reload; disconnected definitions are deliberately not read.
"""
import argparse
import ctypes
import json
import struct
import time


def inspect(pid, base, samples, interval):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x10, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def address(link_address):
        return base + link_address - 0x400000

    def read(pointer, size):
        data = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, pointer, data, size, ctypes.byref(got)) or got.value != size:
            raise OSError(f"Unreadable C1 memory at {pointer:#x}")
        return data.raw

    def word(pointer):
        return struct.unpack("<I", read(pointer, 4))[0]

    def name(pointer):
        if not pointer:
            return None
        data = bytearray()
        for i in range(256):
            value = read(pointer + i, 1)
            if value == b"\0":
                return data.decode("ascii", errors="backslashreplace")
            data.extend(value)
        return {"address": hex(pointer), "error": "name exceeds 255 bytes"}

    def state(pointer):
        if pointer < 0x10000:
            return None
        data = read(pointer, 0x360)
        u32 = lambda offset: struct.unpack_from("<I", data, offset)[0]
        weapon = u32(0x33c)
        result = {"address": hex(pointer), "commandTime": u32(0),
                  "weapon": weapon, "weaponMode": u32(0x35c), "hands": []}
        for hand in range(2):
            values = struct.unpack_from("<7i", data, 0x268 + hand * 28)
            result["hands"].append(dict(zip(
                ("animation", "time", "delay", "kickTime", "state", "freshPull", "shotCount"), values)))
        # C1 40ab60: fifteen weapon IDs, five bytes of state per entry.
        inventory = list(struct.unpack_from("<15I", data, 0x2a0))
        slot = inventory.index(weapon) if weapon and weapon in inventory else None
        special = word(address(0x238a908))
        if weapon and special and read(special + 12, 1) != b"\0":
            slot = 14
        result["inventorySlot"] = slot
        result["inventoryBytes"] = list(data[0x2dc + slot * 5:0x2e1 + slot * 5]) if slot is not None else None
        return result

    try:
        # Instruction guards prevent silently using offsets from another build.
        signature = bytes.fromhex("55 8bec 83790408 7d1e 83c016")
        if read(address(0x418080), len(signature)) != signature:
            raise ValueError("C1 animation producer signature mismatch")
        camera = (b"\xa1" + struct.pack("<I", address(0x6c3d2ac)) +
                  bytes.fromhex("8b0c85") + struct.pack("<I", address(0x16d3b58)) +
                  bytes.fromhex("81f10c400b49d9815c010000"))
        if read(address(0x429070), len(camera)) != camera:
            raise ValueError("C1 camera consumer signature mismatch")
        for sample in range(samples):
            try:
                index = word(address(0x6c3d2ac))
                if index > 1024:
                    raise ValueError("Implausible C1 pointer-table index")
                cg = word(address(0x16d3b58) + 4 * index) ^ 0x490b400c
                predicted = state(cg)
                snapshot = state(word(cg + 0x35e4))
                active = bool(snapshot and snapshot["commandTime"] and predicted["commandTime"])
                result = {"sample": sample, "hasGameplaySnapshot": active,
                          "predicted": predicted, "snapshot": snapshot}
                if active and 0 < predicted["weapon"] < 2048:
                    definition = word(address(0x150d720) + predicted["weapon"] * 4)
                    result["definition"] = {"address": hex(definition),
                        "dualMag": read(definition + 0xbc7, 1)[0],
                        "durations": {hex(offset): word(definition + offset)
                                      for offset in (0x5c8, 0x5cc, 0x5d4, 0x5d8)},
                        "animationNames": {str(bank): {str(slot): name(word(definition + bank + slot * 4))
                                             for slot in (9, 10, 11, 12)}
                                           for bank in (0x7c, 0x13c, 0x1fc)}}
                print(json.dumps(result), flush=True)
            except OSError as error:
                print(json.dumps({"sample": sample, "unavailable": str(error)}), flush=True)
            if sample + 1 < samples:
                time.sleep(interval)
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--base", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.05)
    args = parser.parse_args()
    if not 1 <= args.samples <= 1000 or not 0.01 <= args.interval <= 1:
        parser.error("samples must be 1..1000 and interval 0.01..1 seconds")
    inspect(args.pid, args.base, args.samples, args.interval)
