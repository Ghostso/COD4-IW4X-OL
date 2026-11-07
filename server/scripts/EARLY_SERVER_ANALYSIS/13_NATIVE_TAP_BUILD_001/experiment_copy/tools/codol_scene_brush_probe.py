"""Passive C1 1.1.1.13 brush scene/entity capture; never writes process memory.

Fixed image base is intentional: exact code guards reject another build/base.
No debugger, hooks, input, or renderer changes. Inactive gameplay is not sampled.
"""
import argparse
import ctypes
import json
import math
import struct


def inspect(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.ReadProcessMemory.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x10, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size,
                                       ctypes.byref(got)) or got.value != size:
            raise OSError(f"Unreadable C1 memory {address:#x}")
        return buffer.raw

    def word(address):
        return struct.unpack("<I", read(address, 4))[0]

    def decoded_origin(data):
        x, y, z = struct.unpack_from("<3I", data, 0x18)
        return struct.unpack("<3f", struct.pack("<3I",
            x ^ 0x073ff35a, y ^ x ^ 0xedb436a0, z ^ y ^ 0x893fead3))

    try:
        guards = {
            0x429070: "a1acd2c3068b0c85583b6d0181f10c400b49d9815c010000",
            0xa80510: "568b74240866837e3400746b6a0168fc",
            0xa804f0: "8b4424048b15a039cf008bc8c1e1042bc8",
        }
        for address, code in guards.items():
            expected = bytes.fromhex(code)
            if read(address, len(expected)) != expected:
                raise ValueError(f"Wrong C1 build/base at {address:#x}")
        cg_index = word(0x6c3d2ac)
        entity_index = word(0x6c3d2b4)
        if max(cg_index, entity_index) > 1024:
            raise ValueError("Invalid encoded pointer table index")
        cg = word(0x16d3b58 + cg_index * 4) ^ 0x490b400c
        entities = word(0x16d3b58 + entity_index * 4) ^ 0x189bfead
        command_time = word(cg)
        result = {"pid": pid, "commandTime": command_time,
            "hasPredictedGameplayState": command_time > 0,
            "viewOrigin": struct.unpack("<3f", read(cg + 0xb0384, 12)),
            "limitations": ["Reads are not an atomic engine frame.",
                "commandTime identifies predicted state, not a received snapshot pointer.",
                "Quaternion is captured, not independently recomputed.",
                "Submission does not establish shadow casting or artifact causation."]}
        if not command_time:
            result["status"] = "inactive; scene capture skipped"
            return result
        count = word(0xfe12fc)
        if count > 512:
            raise ValueError("Invalid C1 scene brush count")
        scene = read(0xfe1304, count * 0x28) if count else b""
        world = word(0xcf39a0)
        if world < 0x10000:
            raise ValueError("No C1 render world")
        model_base = word(world + 0xd4)
        records = []
        for i in range(count):
            row = scene[i * 0x28:(i + 1) * 0x28]
            entity = struct.unpack_from("<H", row, 2)[0]
            model = struct.unpack_from("<I", row, 4)[0]
            quaternion = struct.unpack_from("<4f", row, 8)
            origin = struct.unpack_from("<3f", row, 0x18)
            record = {"slot": i, "entity": entity,
                "modelPointer": hex(model), "origin": origin,
                "quaternion": quaternion,
                "quaternionNorm": math.sqrt(sum(v*v for v in quaternion))}
            delta = model - model_base
            record["inlineModelIndex"] = delta // 60 if delta >= 0 and delta % 60 == 0 else None
            if entity < 2048:
                cent = read(entities + entity * 0x228, 0x228)
                number, kind, flags = struct.unpack_from("<3I", cent, 0xe4)
                current_origin = decoded_origin(cent)
                record["centity"] = {"nextEntityNumber": number, "type": kind,
                    "flags": hex(flags), "inlineModelIndex": struct.unpack_from("<I", cent, 0x17c)[0],
                    "solid": hex(struct.unpack_from("<I", cent, 0x18c)[0]),
                    "angles": struct.unpack_from("<3f", cent, 0x24),
                    "origin": current_origin,
                    "scale": struct.unpack_from("<f", cent, 0x30)[0]}
                record["maxOriginDifference"] = max(abs(a-b) for a,b in zip(origin, current_origin))
                record["modelIndexMatches"] = record["inlineModelIndex"] == record["centity"]["inlineModelIndex"]
            records.append(record)
        count_after = word(0xfe12fc)
        unchanged = count_after == count and (not count or read(0xfe1304, count*0x28) == scene)
        result.update(status="captured", count=count,
            sceneUnchangedAcrossReads=unchanged, commandTimeAfter=word(cg), records=records)
        return result
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    print(json.dumps(inspect(parser.parse_args().pid), indent=2, allow_nan=False))
