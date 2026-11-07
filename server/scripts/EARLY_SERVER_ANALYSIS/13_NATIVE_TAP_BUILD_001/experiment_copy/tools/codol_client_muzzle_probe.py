"""Passive exact-build C1 probe for CalcMuzzlePoint's player DObj path.

Usage: python tools/codol_client_muzzle_probe.py --pid <C1 PID> --seconds 120
Samples are not atomic engine frames. Pair timestamps with console_mp.log and
the native `codol_hitprobe <slot>` result before changing a producer.
"""

import argparse
import csv
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import time

from codol_client_reliable_probe import EXPECTED_SHA256, ProcessReader


class Reader(ProcessReader):
    def read(self, address, size):
        import ctypes

        if not 0x10000 <= address <= 0x7FFFFFFF or not 1 <= size <= 4096:
            raise ValueError("C1 read outside bounded user address/size")
        buffer = ctypes.create_string_buffer(size)
        received = ctypes.c_size_t()
        if (not self.kernel.ReadProcessMemory(self.handle, ctypes.c_void_p(address),
                                              buffer, size, ctypes.byref(received))
                or received.value != size):
            raise OSError(ctypes.get_last_error(), f"unreadable C1 address 0x{address:x}")
        return buffer.raw

    def u8(self, address):
        return self.read(address, 1)[0]

    def u16(self, address):
        return struct.unpack("<H", self.read(address, 2))[0]

    def i16(self, address):
        return struct.unpack("<h", self.read(address, 2))[0]


def guarded_state(reader, entity):
    cg_index = reader.u32(0x6C3D2AC)
    cent_index = reader.u32(0x6C3D2B4)
    if cg_index > 1024 or cent_index > 1024:
        raise ValueError("encoded C1 pointer index out of range")
    cg = reader.u32(0x16D3B58 + cg_index * 4) ^ 0x490B400C
    cent_base = reader.u32(0x16D3B58 + cent_index * 4) ^ 0x189BFEAD
    cent = cent_base + entity * 0x228
    number, kind = reader.u32(cent + 0xE4), reader.u32(cent + 0xE8)
    if number != entity or kind not in (0, 1):
        raise ValueError("target centity number/type is not active")
    predicted = reader.u32(cg + 0x140)
    flags = reader.u32(cg + 0x10)
    # Client-info +0xAF4 is copied from the 0x12c clientState vehicle/alternate
    # entity selector. An on-foot player normally has zero here; this is not
    # the separately linked world-gun child.
    alternate = reader.u32(cg + 0x15AE24 + number * 0xB50 + 0xAF4) if kind == 1 else 0
    if alternate >= 2048:
        raise ValueError("alternate centity index out of range")
    selected = cent_base + (alternate if alternate else entity) * 0x228
    selected_num = reader.u32(selected + 0xE4)
    selected_type = reader.u32(selected + 0xE8)
    if selected_num >= 2048:
        raise ValueError("selected centity entity number out of range")
    # An uninitialized/recycled centity may still contain another valid number.
    # Record that mismatch, but never attribute its DObj/tags to this player.
    selected_match = int(selected_num == (alternate if alternate else entity))
    handle = reader.i16(0x25D9ED8 + selected_num * 2) if selected_match else 0
    model_count = flash = silenced = 0
    if handle > 0:
        dobj = 0x2575ED8 + 0xC8 * handle
        model_count = reader.u8(dobj + 9)
        if model_count > 32:
            raise ValueError("selected DObj model count out of range")
        model_array = reader.u32(dobj + 0xC0)
        flash_id, silenced_id = reader.u16(0x24EDFF4), reader.u16(0x24EDFF6)
        for offset in range(model_count):
            model = reader.u32(model_array + 4 * offset)
            if model < 0x10000:
                continue
            bones = reader.u8(model + 4)
            names = reader.u32(model + 0x2C)
            if not bones or names < 0x10000:
                continue
            ids = struct.unpack("<" + str(bones) + "H", reader.read(names, bones * 2))
            flash |= flash_id in ids
            silenced |= silenced_id in ids
    return (number, kind, predicted, flags, alternate, selected_num, selected_type, selected_match,
            handle, model_count, int(flash), int(silenced))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--entity", type=int, default=0, help="bot/player slot, default 0")
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--interval-ms", type=int, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("the passive probe requires Windows")
    if args.pid <= 0 or not 0 <= args.entity < 64 or not 0 < args.seconds <= 600:
        parser.error("PID, entity, or duration is outside the supported range")
    if not 20 <= args.interval_ms <= 1000:
        parser.error("interval-ms must be 20..1000")
    output = args.output or (Path(tempfile.gettempdir()) /
                             f"codol-c1-muzzle-{args.pid}-{int(time.time())}.csv")
    reader = Reader(args.pid)
    try:
        image = reader.image_path()
        if image.name.lower() != "c1.exe" or hashlib.sha256(image.read_bytes()).hexdigest() != EXPECTED_SHA256:
            raise RuntimeError("process is not the verified 1.1.1.13 C1.exe")
        # Exact image/base guards from the existing passive world-lightmap probe.
        for address, code in ((0xA82E20, "a19441cf00"),
                              (0x429070, "a1acd2c3068b0c85583b6d0181f10c400b49d9815c010000")):
            expected = bytes.fromhex(code)
            if reader.read(address, len(expected)) != expected:
                raise RuntimeError("C1 image/base signature mismatch")
        output.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + args.seconds
        samples = errors = 0
        with output.open("w", newline="", encoding="ascii") as stream:
            writer = csv.writer(stream)
            writer.writerow(("utc_epoch_ms", "entity", "entity_type", "predicted_client",
                             "cg_flags", "alternate_entity_index", "selected_entity", "selected_type", "selected_match",
                             "dobj_handle", "dobj_model_count", "tag_flash", "tag_flash_silenced",
                             "error"))
            try:
                while time.monotonic() < deadline:
                    stamp = time.time_ns() // 1_000_000
                    try:
                        row = guarded_state(reader, args.entity)
                        writer.writerow((stamp, *row, ""))
                        samples += 1
                    except (OSError, ValueError) as exc:
                        writer.writerow((stamp, *("" for _ in range(12)), str(exc)))
                        errors += 1
                    if (samples + errors) % 20 == 0:
                        stream.flush()
                    time.sleep(args.interval_ms / 1000)
            except KeyboardInterrupt:
                pass
        print(f"muzzle samples={samples} unavailable={errors} csv={output}")
    finally:
        reader.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as exc:
        print(f"C1 muzzle probe: {exc}", file=sys.stderr)
        sys.exit(1)
