#!/usr/bin/env python3
"""Reversible, exact-build C1.exe patch for the one-Esc pause close path.

This changes only the on-disk 1.1.1.13 .text UI routine. It installs no DLL,
hook, or runtime code. Run --inspect first; --build writes a separate candidate.
--apply must only be used after the C1 client has exited.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct

BASE_SHA256 = "086b2bcf109c8340a898606e5caa2678242449452bcf62b2dda22a6e37dda91f"
FIRST_PATCH_SHA256 = "39e23375088b483063b29d323eeabba1f5839acf6dff825923a2bbb7eb3cf3ad"
SECOND_PATCH_SHA256 = "2f6233d31e41afb73b1a34fbbbe2e9051fe9a2b9024f898c8a33e4abda30e103"
THIRD_PATCH_SHA256 = "faaf5de4786622b1305d4064d102718b4b1cf0ba343bb5618360183dca3d2071"
FOURTH_PATCH_SHA256 = "d8211b2bb030a055cac9cd641bf518968bff3fd58ab51c6e950465124734ba60"
IMAGE_BASE = 0x400000
CALL_VA = 0x005F4F91
CAVE_VA = 0x005F4F9A
ORIGINAL_CLOSE_VA = 0x08411826
CONTINUE_VA = 0x005F4F3D
ORIGINAL_CALL = bytes.fromhex("e890c8e107")
ORIGINAL_CAVE = b"\xcc" * 22
KEY_EVENT_CALL_VA = 0x005F37B3
KEY_EVENT_CAVE_VA = 0x00B28740
ORIGINAL_KEY_EVENT_CALL = bytes.fromhex("833de039830200")
ORIGINAL_KEY_EVENT_CAVE = b"\xcc" * 61
OLD_KEY_EVENT_CALL_VA = 0x005F3894
OLD_KEY_EVENT_CALL = bytes.fromhex("e867350100")


def branch(opcode: int, instruction_va: int, target_va: int) -> bytes:
    return bytes([opcode]) + struct.pack("<i", target_va - instruction_va - 5)


# Focused-menu branch originally calls Menus_CloseAll and returns. After that
# call, enter its existing no-visible-menu branch, which checks Scaleform and
# clears KEYCATCH_UI if the movie no longer owns input. The Scaleform close
# path itself writes cl_paused=0 (live C1 watch; CODOL_C1_VIRTUALIZED §Q7).
PATCH_CALL = branch(0xE9, CALL_VA, CAVE_VA)
PATCH_CAVE = (branch(0xE8, CAVE_VA, ORIGINAL_CLOSE_VA)
              + branch(0xE9, CAVE_VA + 5, CONTINUE_VA)
              + b"\xcc" * 12)
# Live traces of v2 and v3: the first closing Esc skips the later TopVisible
# site entirely.  UI_KeyEvent always reaches this point after forwarding the
# key to Scaleform.  On Esc-down in pause mode, close the focused legacy menu
# and make the second pass that releases KEYCATCH_UI.  Replay the displaced
# open-menu-count comparison before returning to its original branch.
PATCH_KEY_EVENT_CALL = branch(0xE9, KEY_EVENT_CALL_VA, KEY_EVENT_CAVE_VA) + b"\x90\x90"
def key_event_cave() -> bytes:
    code = bytearray()
    code += bytes.fromhex("837d0c1b")
    branches = []
    branches.append(len(code)); code += b"\x75\x00"
    code += bytes.fromhex("837d1000")
    branches.append(len(code)); code += b"\x74\x00"
    code += bytes.fromhex("833d4c46830202")
    branches.append(len(code)); code += b"\x75\x00"
    at = KEY_EVENT_CAVE_VA + len(code)
    code += branch(0xE8, at, 0x005F4F20)
    at = KEY_EVENT_CAVE_VA + len(code)
    code += branch(0xE8, at, 0x005F4F20)
    done = len(code)
    for at in branches:
        code[at + 1] = done - (at + 2)
    code += ORIGINAL_KEY_EVENT_CALL
    at = KEY_EVENT_CAVE_VA + len(code)
    code += branch(0xE9, at, KEY_EVENT_CALL_VA + len(ORIGINAL_KEY_EVENT_CALL))
    return bytes(code).ljust(len(ORIGINAL_KEY_EVENT_CAVE), b"\xcc")

PATCH_KEY_EVENT_CAVE = key_event_cave()
SECOND_KEY_EVENT_CAVE = bytes.fromhex(
    "e8bbe6adff85c0742f837d0c1b7529837d10007423833d4c46830202751a"
    "8b153420570285d27410837a0c00750ae8adc7acffe888e6adffe91cb1acff"
)
THIRD_KEY_EVENT_CAVE = bytes.fromhex(
    "e8bbe6adff837d0c1b751e837d10007418833d4c46830202750f"
    "e8c1c7acffe8bcc7acffe897e6adffe92bb1acff"
).ljust(len(ORIGINAL_KEY_EVENT_CAVE), b"\xcc")
assert len(PATCH_KEY_EVENT_CAVE) == len(ORIGINAL_KEY_EVENT_CAVE)


def file_offset(data: bytes, va: int) -> int:
    if data[:2] != b"MZ":
        raise ValueError("not a PE file")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    sections = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("expected 32-bit C1.exe")
    if struct.unpack_from("<I", data, optional + 28)[0] != IMAGE_BASE:
        raise ValueError("unexpected PE image base")
    rva = va - IMAGE_BASE
    table = optional + optional_size
    for i in range(sections):
        sec = table + i * 40
        size, base, raw_size, raw = struct.unpack_from("<IIII", data, sec + 8)
        if base <= rva < base + min(size, raw_size):
            return raw + rva - base
    raise ValueError(f"VA {va:#x} is not mapped to file data")


def patch(data: bytes) -> bytes:
    digest = hashlib.sha256(data).hexdigest()
    if digest != BASE_SHA256:
        raise ValueError(f"C1.exe SHA-256 mismatch: {digest}; refusing unknown build")
    call_off, cave_off = file_offset(data, CALL_VA), file_offset(data, CAVE_VA)
    key_call_off = file_offset(data, KEY_EVENT_CALL_VA)
    key_cave_off = file_offset(data, KEY_EVENT_CAVE_VA)
    if data[call_off:call_off + 5] != ORIGINAL_CALL:
        raise ValueError("pause close call bytes changed")
    if data[cave_off:cave_off + 22] != ORIGINAL_CAVE:
        raise ValueError("pause code cave is occupied")
    if data[key_call_off:key_call_off + len(ORIGINAL_KEY_EVENT_CALL)] != ORIGINAL_KEY_EVENT_CALL:
        raise ValueError("pause key event call bytes changed")
    if data[key_cave_off:key_cave_off + 61] != ORIGINAL_KEY_EVENT_CAVE:
        raise ValueError("pause key event code cave is occupied")
    changed = bytearray(data)
    changed[call_off:call_off + 5] = PATCH_CALL
    changed[cave_off:cave_off + 22] = PATCH_CAVE
    changed[key_call_off:key_call_off + len(ORIGINAL_KEY_EVENT_CALL)] = PATCH_KEY_EVENT_CALL
    changed[key_cave_off:key_cave_off + 61] = PATCH_KEY_EVENT_CAVE
    return bytes(changed)


def first_patch(data: bytes) -> bytes:
    """The installed first attempt, accepted only for an exact upgrade/restore."""
    if hashlib.sha256(data).hexdigest() != BASE_SHA256:
        raise ValueError("first patch requires the exact original image")
    changed = bytearray(data)
    changed[file_offset(data, CALL_VA):file_offset(data, CALL_VA) + 5] = PATCH_CALL
    changed[file_offset(data, CAVE_VA):file_offset(data, CAVE_VA) + 22] = PATCH_CAVE
    result = bytes(changed)
    if hashlib.sha256(result).hexdigest() != FIRST_PATCH_SHA256:
        raise ValueError("first patch digest mismatch")
    return result


def second_patch(data: bytes) -> bytes:
    changed = bytearray(first_patch(data))
    off = file_offset(data, OLD_KEY_EVENT_CALL_VA)
    changed[off:off + len(OLD_KEY_EVENT_CALL)] = branch(0xE9, OLD_KEY_EVENT_CALL_VA, KEY_EVENT_CAVE_VA)
    off = file_offset(data, KEY_EVENT_CAVE_VA)
    changed[off:off + len(SECOND_KEY_EVENT_CAVE)] = SECOND_KEY_EVENT_CAVE
    result = bytes(changed)
    if hashlib.sha256(result).hexdigest() != SECOND_PATCH_SHA256:
        raise ValueError("second patch digest mismatch")
    return result


def third_patch(data: bytes) -> bytes:
    changed = bytearray(first_patch(data))
    off = file_offset(data, OLD_KEY_EVENT_CALL_VA)
    changed[off:off + len(OLD_KEY_EVENT_CALL)] = branch(0xE9, OLD_KEY_EVENT_CALL_VA, KEY_EVENT_CAVE_VA)
    off = file_offset(data, KEY_EVENT_CAVE_VA)
    changed[off:off + len(THIRD_KEY_EVENT_CAVE)] = THIRD_KEY_EVENT_CAVE
    result = bytes(changed)
    if hashlib.sha256(result).hexdigest() != THIRD_PATCH_SHA256:
        raise ValueError("third patch digest mismatch")
    return result


def write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as f:
        f.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path, help="exact C1 1.1.1.13 executable")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--build", type=Path, metavar="OUTPUT_EXE")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    exe = args.exe.resolve()
    backup = exe.with_name(exe.name + ".codol-pause-original")

    if args.restore:
        original = backup.read_bytes()
        if hashlib.sha256(original).hexdigest() != BASE_SHA256:
            raise ValueError("backup is not the exact original C1.exe")
        current_hash = hashlib.sha256(exe.read_bytes()).hexdigest()
        if current_hash not in (FIRST_PATCH_SHA256, SECOND_PATCH_SHA256, THIRD_PATCH_SHA256, FOURTH_PATCH_SHA256):
            raise ValueError("current executable has other changes; refusing restore")
        if hashlib.sha256(patch(original)).hexdigest() != FOURTH_PATCH_SHA256:
            raise ValueError("fourth patch digest mismatch")
        temp = exe.with_name(exe.name + ".codol-pause-restore-tmp")
        write_new(temp, original)
        os.replace(temp, exe)
        print("Restored exact original C1.exe; backup retained")
        return

    current = exe.read_bytes()
    current_hash = hashlib.sha256(current).hexdigest()
    if current_hash in (FIRST_PATCH_SHA256, SECOND_PATCH_SHA256, THIRD_PATCH_SHA256, FOURTH_PATCH_SHA256):
        if not backup.exists():
            raise ValueError("first patch installed but original backup missing")
        original = backup.read_bytes()
        if hashlib.sha256(original).hexdigest() != BASE_SHA256:
            raise ValueError("original backup digest mismatch")
        if current_hash == FIRST_PATCH_SHA256:
            expected = first_patch(original)
        elif current_hash == SECOND_PATCH_SHA256:
            expected = second_patch(original)
        elif current_hash == THIRD_PATCH_SHA256:
            expected = third_patch(original)
        else:
            expected = patch(original)
        if expected != current:
            raise ValueError("installed pause patch differs from expected bytes")
    else:
        original = current
    candidate = patch(original)
    if hashlib.sha256(candidate).hexdigest() != FOURTH_PATCH_SHA256:
        raise ValueError("fourth patch digest mismatch")
    print("Exact 1.1.1.13 image and pause-site bytes verified")
    print("Original SHA-256:", BASE_SHA256)
    print("Patched SHA-256:", hashlib.sha256(candidate).hexdigest())
    if args.inspect:
        return
    if args.apply and current_hash == FOURTH_PATCH_SHA256:
        print("Exact fourth pause patch already installed")
        return
    if args.build:
        write_new(args.build.resolve(), candidate)
        print("Wrote separate patched candidate:", args.build.resolve())
        return
    if backup.exists():
        if hashlib.sha256(backup.read_bytes()).hexdigest() != BASE_SHA256:
            raise ValueError("existing backup does not match exact original C1.exe")
    else:
        write_new(backup, original)
    temp = exe.with_name(exe.name + ".codol-pause-install-tmp")
    write_new(temp, candidate)
    try:
        os.replace(temp, exe)
    except OSError:
        temp.unlink(missing_ok=True)
        raise
    print("Installed static pause patch; original backup:", backup)


if __name__ == "__main__":
    main()
