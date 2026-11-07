"""CODOL 3.19 first-frame motion snapshot codec.

Ported from MotionSnapshot.cs / battle_server._build_motion_snapshot.
The writer deliberately keeps a split bit/raw cursor; Bytes() appends at
the end without moving Bit, matching the client decoder layout.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = ROOT.parent / "CODOL-Combat-Server-v0.1" / "tests" / "golden_first_snapshot.hex"


class BitWriter:
    def __init__(self) -> None:
        self.data = bytearray()
        self.bit = 0

    def raw(self, value: bytes) -> None:
        self.data += value

    def byte(self, value: int) -> None:
        self.data.append(value & 0xFF)

    def bits(self, value: int, width: int) -> None:
        for i in range(width):
            if (self.bit & 7) == 0:
                self.bit = len(self.data) * 8
                self.data.append(0)
            self.data[self.bit >> 3] |= ((value >> i) & 1) << (self.bit & 7)
            self.bit += 1

    def run(self, run: int, index_bits: int = 7) -> None:
        """Native 0x670CB0 run codec; playerState uses 7 bits."""
        if index_bits == 1:
            for _ in range(run):
                self.bits(1, 1)
            self.bits(0, 1)
            return
        if run == 1:
            self.bits(1, 1)
            return
        self.bits(0, 1)
        left = run - 1
        mask = (1 << index_bits) - 1
        while left >= mask:
            self.bits(mask, index_bits)
            left -= mask
        self.bits(left, index_bits)

    def index(self, index: int, previous: list[int], index_bits: int = 7) -> None:
        run = index - previous[0]
        previous[0] = index
        self.run(run, index_bits)

    def legacy_index(self, index: int, previous: list[int]) -> None:
        """Preserve the historical 141-byte KAT path (four-bit chunks)."""
        skip = index - previous[0] - 1
        previous[0] = index
        if skip == 0:
            self.bits(1, 1)
            return
        self.bits(0, 1)
        while skip >= 15:
            self.bits(15, 4)
            skip -= 15
        self.bits(skip, 4)

    def scalar(self, value: int, width: int) -> None:
        self.bits(1 if value else 0, 1)
        if not value:
            return
        low = width & 7
        if low:
            self.bits(value & ((1 << low) - 1), low)
        for shift in range(low, width, 8):
            self.byte(value >> shift)


def f32(value: float) -> bytes:
    return struct.pack("<f", value)


def build_default_golden() -> bytes:
    ack = 0
    server_time = 1000
    command_time = 1000
    first = True
    x, y, z = 48.0, -572.0, -116.0
    pitch = yaw = roll = 0
    vx = vy = 0.0
    aim_fraction = 0.0
    aiming = False
    weapon = 1156
    ammo_key = 585
    capacity = 30
    clip = 30
    reserve = 90
    weapon_time = 0
    weapon_delay = 0
    weapon_state = 0
    event_sequence = 0

    w = BitWriter()
    prev = [-1]
    w.raw(struct.pack("<I", ack))
    w.byte(0)
    w.raw(struct.pack("<I", server_time))
    w.raw(bytes((0 if first else 1, 8 if first else 4)))
    w.bits(0, 1)
    w.bits(1, 1)
    w.bits(220, 8)

    w.legacy_index(0, prev); w.bits(1, 1); w.raw(struct.pack("<I", command_time))
    w.legacy_index(1, prev); w.bits(0, 1); w.byte(event_sequence)
    w.legacy_index(3, prev); w.scalar(weapon_time, 16)
    w.legacy_index(8, prev); w.raw(f32(x))
    w.legacy_index(10, prev); w.raw(f32(z))
    w.legacy_index(11, prev); w.raw(f32(y))
    w.legacy_index(13, prev); w.raw(f32(vy))
    w.legacy_index(14, prev); w.raw(f32(vx))
    w.legacy_index(17, prev); w.scalar(weapon_state, 6)
    w.legacy_index(18, prev); w.raw(struct.pack("<H", yaw & 0xFFFF))
    w.legacy_index(19, prev); w.raw(struct.pack("<H", pitch & 0xFFFF))
    w.legacy_index(20, prev); w.scalar(0x10 if aiming else 0, 32)

    for i in range(4):
        w.legacy_index(21 + i, prev)
        w.bits(1, 1)
        has = i == 0 and capacity > 0
        if has:
            w.bits(1, 1)
            w.bits(weapon & 0x7FF, 11)
        else:
            w.bits(0, 1)

    w.legacy_index(29, prev); w.raw(struct.pack("<H", roll & 0xFFFF))
    w.legacy_index(34, prev); w.raw(f32(60.0))
    w.legacy_index(38, prev); w.scalar(60, 8)
    w.legacy_index(39, prev); w.scalar(weapon, 11)
    w.legacy_index(41, prev); w.raw(f32(aim_fraction))
    w.legacy_index(44, prev); w.scalar(weapon_delay, 16)
    w.legacy_index(54, prev); w.bits(1, 1); w.bits(0x1000, 31)
    w.legacy_index(56, prev); w.scalar(139, 10)
    w.legacy_index(60, prev); w.scalar(190, 16)
    w.legacy_index(61, prev); w.scalar(2047, 16)
    w.legacy_index(63, prev); w.scalar(800, 16)
    w.legacy_index(68, prev); w.scalar(2047, 11)

    w.raw(f32(1.0)); w.bits(0, 8)
    w.bits(1, 1); w.bits(5, 17)
    w.raw(struct.pack("<H", 100)); w.raw(struct.pack("<H", 100))

    w.legacy_index(84, prev)
    for _ in range(9):
        w.bits(15, 4)
    w.bits(0, 4)
    w.bits(1, 1); w.bits(1, 1)
    for _ in range(8):
        w.bits(0, 1)

    clip_count = 1
    w.bits(1, 1)
    w.bits(clip_count, 17)
    for i in range(clip_count):
        w.bits(1, 1)
        w.bits(i, 4)
        w.bits(weapon & 0x7FF, 11)
        w.bits(1, 1)
        w.bits(clip & 0x1FF, 9)
        w.bits(0, 1)
    w.bits(0, 1)

    w.bits(1, 1); w.bits(1, 1)
    for i in range(15):
        if i == 0:
            w.bits(1, 1); w.bits(1, 1); w.bits(weapon & 0x7FF, 11)
            for _ in range(5): w.bits(0, 1)
            w.bits(0, 12)
        else:
            w.bits(0, 1); w.bits(0, 12)

    w.bits(1, 1)
    w.bits(0, 4); w.bits(ammo_key & 0x7FF, 11); w.bits(reserve & 0xFFF, 12); w.bits(0, 1)
    for _ in range(13):
        w.bits(0, 1)
    w.bits(0, 1); w.bits(0, 1); w.bits(0, 1); w.bits(1, 1); w.bits(2047, 11)
    w.bits(0, 1); w.bits(0, 1)
    w.byte(0x05)
    return bytes(w.data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    args = ap.parse_args()
    golden = bytes.fromhex(args.golden.read_text(encoding="ascii").strip())
    built = build_default_golden()
    print(f"golden={len(golden)} bytes built={len(built)} bytes")
    print(f"byte_exact={golden == built}")
    if golden != built:
        for i, (a, b) in enumerate(zip(golden, built)):
            if a != b:
                print(f"first_diff=0x{i:X} golden=0x{a:02X} built=0x{b:02X}")
                break
        print("golden_hex=" + golden.hex())
        print("built_hex =" + built.hex())
    return 0 if golden == built else 1


if __name__ == "__main__":
    raise SystemExit(main())


