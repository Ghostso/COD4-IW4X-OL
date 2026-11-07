"""Read C1 1.1.1.13 eye-height state without attaching a debugger or writing memory.

Use after joining Killhouse: python tools/codol_camera_probe.py --pid <C1 PID>
A zero-height disconnected playerstate is not an in-game camera diagnosis.
Offsets are checked against C1's actual camera consumer instructions, not IW3.
"""
import argparse
import ctypes
import json
import struct
import time


def inspect(pid, samples, interval):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x10, False, pid)  # PROCESS_VM_READ only
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(got)) or got.value != size:
            raise OSError(f"Cannot read camera state at {address:#x}")
        return buffer.raw

    def word(address):
        return struct.unpack("<I", read(address, 4))[0]

    def playerstate(address):
        if address < 0x10000:
            return None
        try:
            data = read(address, 0x1f0)
        except OSError as error:
            return {"address": hex(address), "unavailable": str(error)}
        def integer(offset):
            return struct.unpack_from("<i", data, offset)[0]
        origin = struct.unpack_from("<3f", data, 0x1c)
        height = struct.unpack_from("<f", data, 0x15c)[0]
        return {"address": hex(address), "commandTime": integer(0),
                "pm_type": integer(4), "pm_flags": hex(integer(12)),
                "other_flags": hex(integer(16)), "origin": origin,
                "viewHeightTarget": integer(0x158), "viewHeightCurrent": height,
                "eyeZ": origin[2] + height,
                "linkWeaponEnt": integer(0x1ec),
                "lerpTime": integer(0x160), "lerpTarget": integer(0x164),
                "lerpDown": integer(0x168)}

    try:
        # mov eax,[index]; mov ecx,[eax*4+table]; xor ecx,key; fld [ecx+15c].
        expected = bytes.fromhex("a1 acd2c306 8b0c85 583b6d01 81f1 0c400b49 d981 5c010000")
        if read(0x429070, len(expected)) != expected:
            raise ValueError("Camera consumer does not match C1 1.1.1.13; refusing guessed offsets")
        for sample in range(samples):
            index = word(0x6c3d2ac)
            if index > 1024:
                raise ValueError("C1 camera pointer table index is implausible")
            cg = word(0x16d3b58 + index * 4) ^ 0x490b400c
            predicted = playerstate(cg)
            refdef_vieworg = struct.unpack("<3f", read(cg + 0xb0384, 12))
            # Snapshot pointer locations are documented by the alpha0022 live
            # camera audit; independently print both instead of accepting a
            # disconnected/zero predicted state as evidence of bad eye height.
            snap = playerstate(word(cg + 0x35e4))
            next_snap = playerstate(word(cg + 0x35d4))
            active = bool(snap and "unavailable" not in snap and snap["commandTime"] > 0)
            render_delta = (refdef_vieworg[2] - predicted["origin"][2]
                            if predicted and "origin" in predicted else None)
            print(json.dumps({"sample": sample, "hasGameplaySnapshot": active,
                              "predicted": predicted, "snap": snap,
                              "nextSnap": next_snap,
                              "refdefViewOrigin": refdef_vieworg,
                              "renderEyeDeltaZ": render_delta}, allow_nan=False), flush=True)
            if sample + 1 < samples:
                time.sleep(interval)
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if not 1 <= args.samples <= 10 or not 0.05 <= args.interval <= 5:
        parser.error("samples must be 1..10 and interval 0.05..5 seconds")
    inspect(args.pid, args.samples, args.interval)
