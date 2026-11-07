"""Read C1's client-to-server reliable window without reading command text.

Usage: python tools/codol_client_reliable_probe.py --pid <C1 PID> --seconds 600
The exact executable and addresses are from C1.exe SHA-256
086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F.
Only sample time, sequence, acknowledgement, and their difference are written
to CSV. UTC epoch milliseconds can be aligned with the server trace.
"""

import argparse
import ctypes
import hashlib
from pathlib import Path
import sys
import tempfile
import time


EXPECTED_SHA256 = "086b2bcf109c8340a898606e5caa2678242449452bcf62b2dda22a6e37dda91f"
CLIENT_POINTER_VA = 0x016F8068
CLIENT_POINTER_XOR = 0x26F950CC
RELIABLE_SEQUENCE_OFFSET = 0x140
RELIABLE_ACK_OFFSET = 0x144
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class ProcessReader:
    def __init__(self, pid):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                              ctypes.c_void_p, ctypes.c_size_t,
                                              ctypes.POINTER(ctypes.c_size_t)]
        kernel.ReadProcessMemory.restype = ctypes.c_int
        kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                       ctypes.c_wchar_p,
                                                       ctypes.POINTER(ctypes.c_uint32)]
        kernel.QueryFullProcessImageNameW.restype = ctypes.c_int
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.kernel = kernel
        self.handle = kernel.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION,
                                         0, pid)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), f"cannot open C1 PID {pid}")

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def image_path(self):
        name = ctypes.create_unicode_buffer(32768)
        length = ctypes.c_uint32(len(name))
        if not self.kernel.QueryFullProcessImageNameW(self.handle, 0, name,
                                                       ctypes.byref(length)):
            raise OSError(ctypes.get_last_error(), "cannot identify process image")
        return Path(name.value)

    def u32(self, address):
        value = ctypes.c_uint32()
        received = ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, ctypes.c_void_p(address),
                                             ctypes.byref(value), ctypes.sizeof(value),
                                             ctypes.byref(received)) or received.value != 4:
            raise OSError(ctypes.get_last_error(), f"cannot read C1 state at 0x{address:x}")
        return value.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True, help="PID of the running C1.exe")
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument("--interval-ms", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("this read-only probe requires Windows")
    if args.pid <= 0 or args.seconds <= 0 or not 20 <= args.interval_ms <= 1000:
        parser.error("PID and seconds must be positive; interval-ms must be 20..1000")
    output = args.output or Path(tempfile.gettempdir()) / f"codol-c1-reliable-{args.pid}-{int(time.time())}.csv"
    reader = ProcessReader(args.pid)
    try:
        image = reader.image_path()
        if image.name.lower() != "c1.exe" or hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED_SHA256:
            raise RuntimeError("process is not the verified 1.1.1.13 C1.exe")
        pointer = reader.u32(CLIENT_POINTER_VA) ^ CLIENT_POINTER_XOR
        if pointer < 0x10000 or pointer > 0x7FFFFFFF:
            raise RuntimeError("C1 reliable state pointer is not initialized")
        output.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        count = peak = 0
        print(f"capturing C1 reliable window csv={output}", flush=True)
        with output.open("w", encoding="ascii", newline="") as stream:
            stream.write("utc_epoch_ms,elapsed_ms,sequence,acknowledgement,outstanding\n")
            try:
                while time.monotonic() - started < args.seconds:
                    sequence = reader.u32(pointer + RELIABLE_SEQUENCE_OFFSET)
                    acknowledgement = reader.u32(pointer + RELIABLE_ACK_OFFSET)
                    outstanding = (sequence - acknowledgement) & 0xFFFFFFFF
                    utc_epoch_ms = time.time_ns() // 1_000_000
                    elapsed = int((time.monotonic() - started) * 1000)
                    stream.write(f"{utc_epoch_ms},{elapsed},{sequence},{acknowledgement},{outstanding}\n")
                    count += 1
                    peak = max(peak, outstanding)
                    if outstanding >= 200:
                        stream.flush()
                    time.sleep(args.interval_ms / 1000)
            except KeyboardInterrupt:
                pass
        print(f"C1 reliable samples={count} peak_outstanding={peak} csv={output}")
    finally:
        reader.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as exc:
        print(f"C1 reliable probe: {exc}", file=sys.stderr)
        sys.exit(1)
