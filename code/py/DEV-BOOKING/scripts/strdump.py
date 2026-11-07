# -*- coding: utf-8 -*-
"""Dump ASCII/UTF-16 strings and pointer tables from a VA in image_best.bin."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
IMG = ROOT / "CODOLServer" / "_mainline" / "_dyn100_run_20260925_182324" / "live" / "image_best.bin"
BASE = 0x400000


def load() -> bytes:
    return IMG.read_bytes()


def cstr(img: bytes, va: int, limit: int = 300) -> str:
    off = va - BASE
    if off < 0 or off >= len(img):
        return "<bad va>"
    end = img.find(b"\x00", off, off + limit)
    if end < 0:
        end = off + limit
    raw = img[off:end]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return repr(raw)


def wstr(img: bytes, va: int, limit: int = 300) -> str:
    off = va - BASE
    if off < 0 or off >= len(img):
        return "<bad va>"
    out = []
    for i in range(0, limit, 2):
        lo = img[off + i]
        hi = img[off + i + 1]
        if lo == 0 and hi == 0:
            break
        out.append(chr(lo | (hi << 8)))
    return "".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("va", type=lambda s: int(s, 0))
    ap.add_argument("--table", type=int, default=0, help="dump N dwords as pointers")
    args = ap.parse_args()
    img = load()
    print(f"VA 0x{args.va:08X}")
    print(f"  ascii : {cstr(img, args.va)!r}")
    print(f"  utf16 : {wstr(img, args.va)!r}")
    if args.table:
        off = args.va - BASE
        print(f"  table[{args.table}] @0x{args.va:X}")
        for i in range(args.table):
            val = struct.unpack_from("<I", img, off + i * 4)[0]
            extra = ""
            if BASE <= val < BASE + len(img):
                extra = f" -> {cstr(img, val)!r}"
            print(f"    [{i:3d}] 0x{val:08X}{extra}")


if __name__ == "__main__":
    main()
