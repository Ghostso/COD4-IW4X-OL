"""Passive C1 action-slot/HUD evidence. Reads only; never attaches a debugger."""
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
        ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x10, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def address(value):
        return base + value - 0x400000

    def read(pointer, size):
        data = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, pointer, data, size, ctypes.byref(got)) or got.value != size:
            raise OSError(f"Unreadable C1 address {pointer:#x}")
        return data.raw

    def word(pointer):
        return struct.unpack("<I", read(pointer, 4))[0]

    def name(pointer):
        if not pointer:
            return None
        result = bytearray()
        for offset in range(192):
            byte = read(pointer + offset, 1)
            if byte == b"\0":
                return result.decode("ascii", errors="backslashreplace")
            result.extend(byte)
        return "<unterminated>"

    def state(pointer):
        if pointer < 0x10000:
            return None
        data = read(pointer, 0x598)
        words = lambda offset, count: list(struct.unpack_from("<" + str(count) + "I", data, offset))
        inventory = words(0x2a0, 15)
        reserves = [words(0x360 + slot * 8, 2) for slot in range(15)]
        clips = [words(0x3d8 + slot * 12, 3) for slot in range(15)]
        result = {"address": hex(pointer), "commandTime": words(0, 1)[0],
            "pmType": words(4, 1)[0], "pmFlags": words(8, 1)[0],
            "otherFlags": words(0x10, 1)[0], "eFlags": words(0xec, 1)[0],
            "progress": words(0x64, 1)[0], "rewardIDs": words(0x68, 5),
            "targets": words(0x7c, 5), "inventory": inventory, "actions": []}
        for slot, (kind, weapon, override) in enumerate(zip(
                words(0x544, 5), words(0x558, 5), words(0x578, 5)), 1):
            action = {"slot": slot, "type": kind, "weapon": weapon,
                "materialOverride": override, "owned": weapon != 0 and weapon in inventory}
            if kind == 1 and 0 < weapon < 2048:
                definition = word(address(0x150d720) + weapon * 4)
                if definition:
                    icon = word(definition + 0xb94)
                    ammo, clip = word(definition + 0x568), word(definition + 0x570)
                    action.update({"weaponName": name(word(definition)),
                        "hudIcon": name(word(icon)) if icon else None,
                        "hideWithoutAmmo": read(definition + 0xbd1, 1)[0],
                        "ammoIndex": ammo, "clipIndex": clip,
                        "reserveEntries": [entry for entry in reserves if entry[0] == ammo],
                        "clipEntries": [entry for entry in clips if entry[0] == clip]})
                    if weapon in inventory:
                        pos = 0x2dc + inventory.index(weapon) * 5
                        action["inventoryFlags"] = list(data[pos:pos + 5])
            result["actions"].append(action)
        return result

    try:
        # C1 action drawer, zero-based action parameter at playerState+558.
        if read(address(0x42b5a6), 7) != bytes.fromhex("8bbcbe58050000"):
            raise ValueError("C1 action-drawer instruction signature mismatch")
        commands = {}
        for index in range(86):
            command = name(word(address(0xcd62c0) + index * 4))
            if command and command.startswith("+actionslot "):
                commands[index] = command
        bindings = [{"key": key, "command": commands[command]}
            for key in range(256)
            if (command := word(address(0x16f5164) + key * 12)) in commands]
        for sample in range(samples):
            try:
                index = word(address(0x6c3d2ac))
                if index > 1024:
                    raise ValueError("C1 player pointer index outside bounds")
                cg = word(address(0x16d3b58) + index * 4) ^ 0x490b400c
                predicted = state(cg)
                snapshot = state(word(cg + 0x35e4))
                client = word(cg + 0x35c0)
                # C1 0x603db8..0x603e04 expands {ACTION_SLOT_HELP} from this
                # clientInfo byte + 1, then resolves the formatted +actionslot
                # command's key binding. This may differ from the reward slot.
                help_slot = (read(cg + 0x15ae80 + client * 0xb50, 1)[0] + 1
                    if client < 64 else None)
                result = {"sample": sample, "bindings": bindings,
                    "active": bool(snapshot and snapshot["commandTime"] and predicted["commandTime"]),
                    "connectionState": word(address(0x16fc2e8)),
                    "clientInfoValid": word(cg + 0x15ae24 + client * 0xb50) if client < 64 else None,
                    "actionSlotHelpSlot": help_slot,
                    "actionSlotHelpBindings": [binding["key"] for binding in bindings
                        if binding["command"] == f"+actionslot {help_slot}"],
                    "predicted": predicted, "snapshot": snapshot}
                print(json.dumps(result), flush=True)
            except (OSError, ValueError) as error:
                print(json.dumps({"sample": sample, "error": str(error)}), flush=True)
            if sample + 1 < samples:
                time.sleep(interval)
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid", type=int)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0x400000)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.25)
    args = parser.parse_args()
    if not 1 <= args.samples <= 120 or not 0.05 <= args.interval <= 1:
        parser.error("samples must be 1..120; interval must be 0.05..1 seconds")
    inspect(args.pid, args.base, args.samples, args.interval)
