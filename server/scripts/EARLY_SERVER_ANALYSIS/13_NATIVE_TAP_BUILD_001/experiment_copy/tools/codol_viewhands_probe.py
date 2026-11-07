"""Read C1 1.1.1.13 first-person model selectors without writing memory."""
import argparse
import ctypes
import json
import struct


def inspect(pid):
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

    def read(address, size):
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(got)) or got.value != size:
            raise OSError(f"Cannot read C1 state at {address:#x}")
        return buffer.raw

    def word(address):
        return struct.unpack("<I", read(address, 4))[0]

    def state(address):
        if address < 0x10000:
            return None
        data = read(address, 0x360)
        integer = lambda offset: struct.unpack_from("<i", data, offset)[0]
        equipped = struct.unpack_from("<15I", data, 0x2A0)
        return {"address": hex(address), "commandTime": integer(0),
                "arms": integer(0x144), "hands": integer(0x148),
                "weapon": integer(0x33C), "weaponsEquipped": equipped}

    try:
        # Same decoded cg pointer and exact build guard as codol_camera_probe.py.
        expected = bytes.fromhex("a1 acd2c306 8b0c85 583b6d01 81f1 0c400b49 d981 5c010000")
        if read(0x429070, len(expected)) != expected:
            raise ValueError("C1 camera consumer does not match 1.1.1.13")
        index = word(0x6C3D2AC)
        cg = word(0x16D3B58 + index * 4) ^ 0x490B400C
        print(json.dumps({"predicted": state(cg),
                          "snap": state(word(cg + 0x35E4)),
                          "nextSnap": state(word(cg + 0x35D4))}))
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    inspect(parser.parse_args().pid)
