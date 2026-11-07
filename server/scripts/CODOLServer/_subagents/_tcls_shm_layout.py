#!/usr/bin/env python3
"""TCLS_SHAREDMEMEMORY<pid> layout model for CODOL.

Read-only static analysis produced the layout; this script turns it into a
concrete byte image and (only when explicitly asked) creates the named
mapping for a given process id.

Nothing is created and nothing is written unless --create / --out is passed.
The script never launches the game.

Container model (recovered from TenProxy.dll, image base 0x10000000):

    mapped + 0x000  DWORD   version = 0x40 (64 tag slots)
    mapped + 0x004  DWORD[64] table A: table A[tag-1] = offset of tag entry
    mapped + 0x104  end of table A
    mapped + 0x04C  DWORD   raw read by slot +0x2C as tag 5 -> channel table
                            (the table A entry for tag 0x13)

    entry = mapped + tableA[tag-1]
    entry + 0x000   DWORD   payload byte length
    entry + 0x004   bytes   payload

    channel table at mapped + OFFB, indexed by (channel - 1):
        sub = mapped + dword[OFFB + 4*(channel-1)]
        entry = mapped + dword[sub + 4*(tag-1)]

ASCII-only source.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent

NAME_FMT = "TCLS_SHAREDMEMEMORY%d"
SIZE = 0x80000
VERSION = 0x40
TABLE_A_OFF = 0x004
TABLE_A_COUNT = 0x40
ENTRY_AREA = 0x104

# Tags read from table A by CTclsProxy slots +0x24 / +0x28 / +0x2C
TABLE_A_TAGS = {
    0x01: ("dword", "CTclsProxy::Initialize slot+0x24 -> this+0x8AC"),
    0x02: ("dword", "CTclsProxy::Initialize slot+0x24 -> this+0x8AC"),
    0x03: ("block", "CTclsProxy::Initialize slot+0x28 -> this+0x10C0 (1 byte)"),
    0x04: ("block", "CTclsProxy::Initialize slot+0x28 -> this+0x8B0 (GameSignature)"),
    0x05: ("block", "CTclsProxy::Initialize slot+0x28 -> this+0x1038 (LoginKey)"),
    0x07: ("string", "ApplySettings slot+0x28 -> block+0x0B0, len at block+0x4B0"),
    0x0E: ("block", "CTclsProxy::Initialize slot+0x2C -> this+0x8C (cap 0x410)"),
    0x0F: ("block", "CTclsProxy::Initialize slot+0x2C -> this+0x49C (TCLS window name)"),
    0x10: ("block", "CTclsProxy::Initialize slot+0x2C -> this+0x11DC (cap 0x28)"),
    0x12: ("dword", "ApplySettings slot+0x24 -> channel selector"),
    0x16: ("dword", "ApplySettings slot+0x28 -> block+0x04, len at block+0x14"),
    0x18: ("block", "ApplySettings slot+0x28 -> block+0x18, len at block+0x98"),
    0x19: ("block", "ApplySettings slot+0x28 -> block+0x9C, len at block+0xAC"),
    0x1A: ("block", "CTclsProxy::Initialize slot+0x28 -> this+0x1144 (1 byte)"),
    0x1B: ("block", "ApplySettings slot+0x28 -> block+0x4B4 / JumpSignature"),
    0x1A: ("block", "CTclsProxy::Initialize slot+0x28 -> this+0x1144 (1 byte)"),
    0x1B: ("block", "ApplySettings slot+0x28 -> block+0x4B4 / JumpSignature"),
    0x13: ("ptr", "entry reached by a RAW read at mapped+0x4C (raw mode) or "
                  "by the normal indexed read (tag mode); value = offset of "
                  "the channel table"),
}

# Tags read from the channel sub-table by slots +0x30 / +0x38
CHANNEL_TAGS = {
    0x05: ("dword", "ApplySettings slot+0x38 -> block+0x538"),
    0x07: ("dword", "ApplySettings slot+0x38 -> must equal tag 8 length"),
    0x08: ("block", "ApplySettings slot+0x30 -> split on ';' and ':'"),
}


class Builder:
    def __init__(self, channel=1):
        self.buf = bytearray(SIZE)
        self.cursor = ENTRY_AREA
        self.channel = channel
        struct.pack_into("<I", self.buf, 0x000, VERSION)
        self.entries = []

    def _alloc(self, size, align=4):
        if self.cursor % align:
            self.cursor += align - (self.cursor % align)
        off = self.cursor
        self.cursor += size
        if self.cursor > SIZE:
            raise SystemExit("payload exceeds mapping size")
        return off

    def put_entry(self, payload):
        """Allocate [len][payload] and return its offset."""
        off = self._alloc(4 + len(payload))
        struct.pack_into("<I", self.buf, off, len(payload))
        self.buf[off + 4:off + 4 + len(payload)] = payload
        return off

    def set_table_a(self, tag, entry_off):
        if not 1 <= tag <= TABLE_A_COUNT:
            raise SystemExit("tag %d out of table A range" % tag)
        struct.pack_into("<I", self.buf, TABLE_A_OFF + 4 * (tag - 1), entry_off)

    def set_dword_a(self, tag, value):
        off = self.put_entry(struct.pack("<I", value))
        self.set_table_a(tag, off)
        return off

    def set_block_a(self, tag, payload):
        off = self.put_entry(payload)
        self.set_table_a(tag, off)
        return off

    def build_channel(self, tag8_text, tag7_hint, tag5_value):
        """Create tag 19 -> channel table -> channel sub-table -> entries."""
        if tag7_hint != len(tag8_text):
            raise SystemExit("tag 7 dword must equal tag 8 payload length")
        ch_tag5 = self.put_entry(struct.pack("<I", tag5_value))
        ch_tag7 = self.put_entry(struct.pack("<I", tag7_hint))
        ch_tag8 = self.put_entry(tag8_text)
        sub_off = self._alloc(TABLE_A_COUNT * 4)
        struct.pack_into("<I", self.buf, sub_off + 4 * (0x05 - 1), ch_tag5)
        struct.pack_into("<I", self.buf, sub_off + 4 * (0x07 - 1), ch_tag7)
        struct.pack_into("<I", self.buf, sub_off + 4 * (0x08 - 1), ch_tag8)
        chan_off = self._alloc(4 * self.channel)
        struct.pack_into("<I", self.buf, chan_off + 4 * (self.channel - 1), sub_off)
        # Slot +0x2C with tag 5 reads the dword at mapped+0x4C RAW (no
        # length field), so table A[0x1B-1] must be the offset of the
        # channel-table payload itself.
        if TABLE_A_OFF + 4 * (0x13 - 1) != 0x4C:
            raise SystemExit("table A layout assumption broken")
        self.set_table_a(0x13, chan_off)
        return ch_tag8


def build_payload(host, port, extra_fields, channel=1, tag8_text=None,
                  tag1=1, tag2=0, tag6=0, tag3=0x01, tag4=b"\x00" * 0x80,
                  tag5=0, tag7_hint=None, tag0e=b"", tag0f=b"", tag10=b"",
                  tag16=0, tag18=b"\x00" * 0x80, tag19=b"\x00" * 0x10,
                  tag1a=0x01, tag1b=b"\x00" * 0x70):
    b = Builder(channel=channel)
    if tag8_text is None:
        fields = [host, str(port)] + list(extra_fields)
        tag8_text = (";".join(fields) + "\x00").encode("ascii")
        if tag7_hint is None:
            tag7_hint = len(tag8_text)
    if tag7_hint is None:
        tag7_hint = len(tag8_text)
    b.set_dword_a(0x01, tag1)
    b.set_dword_a(0x02, tag2)
    # Initialize reads tags 2 and 6 as DWORDs.  Keep the values zero until
    # their business semantics are recovered, but emit valid length headers.
    b.set_dword_a(0x06, tag6)
    b.set_block_a(0x03, bytes([tag3]))
    b.set_block_a(0x04, bytes(tag4))
    b.set_block_a(0x05, bytes(0x10))          # LoginKey placeholder
    b.set_block_a(0x07, b"\x00" * 0x20 + b"\x00")
    b.set_block_a(0x0E, bytes(tag0e))
    b.set_block_a(0x0F, bytes(tag0f) if tag0f else
                  "TCLS_SHAREDMEMEMORY".encode("utf-16-le") + b"\x00\x00")
    b.set_block_a(0x10, bytes(tag10) if tag10 else b"\x00\x00")
    b.set_dword_a(0x12, channel)
    b.set_dword_a(0x16, tag16)
    b.set_block_a(0x18, bytes(tag18))
    b.set_block_a(0x19, bytes(tag19))
    b.set_block_a(0x1A, bytes([tag1a]))
    b.set_block_a(0x1B, bytes(tag1b))
    b.build_channel(tag8_text, tag7_hint, tag5)
    return bytes(b.buf)


def cmd_layout(args):
    layout = {
        "object_name_format": NAME_FMT,
        "object_name_example": NAME_FMT % 1234,
        "mapping_size": SIZE,
        "zero_fill": True,
        "header": {
            "version_dword": {
                "offset": 0x000,
                "value": VERSION,
                "consumer_check": "TenProxy.dll 0x100062F4 cmp [this+0x18D0],0x40 ; jae ok",
                "on_failure": "TenProxy initialize aborts, [this+0x18E0] stays 0",
            },
            "table_a": {
                "offset": TABLE_A_OFF,
                "count": TABLE_A_COUNT,
                "indexing": "1-based: table_a[tag-1] = absolute offset of entry",
                "entry_area_starts": ENTRY_AREA,
            },
            "channel_table_pointer": {
                "read_at": 0x050,
                "meaning": "raw dword; offset of channel table payload",
                "note": "equals table A slot for tag 19 (0x13)",
            },
        },
        "entry_format": {
            "plus_0x00": "DWORD payload length",
            "plus_0x04": "payload bytes",
        },
        "channel_model": {
            "selector_tag": 0x12,
            "selector_source": "table A, slot +0x24",
            "indexing": "1-based: channel table[channel-1] = offset of sub-table",
            "sub_table": "dword[64]; sub_table[tag-1] = offset of entry",
        },
        "table_a_tags": [
            {"tag": t, "kind": v[0], "note": v[1]}
            for t, v in sorted(TABLE_A_TAGS.items())
        ],
        "channel_tags": [
            {"tag": t, "kind": v[0], "note": v[1]}
            for t, v in sorted(CHANNEL_TAGS.items())
        ],
        "game_config_block": {
            "va": 0x331C5C0,
            "size": 0xD40,
            "writer": "0x641600 ApplySettings, called only from 0x642739",
            "periodic": "re-runs on a timer, re-memsets the block each pass",
            "fields": [
                {"off": "0x000", "size": 4, "src": "parser success flag",
                 "insn": "0x641BC8 mov [0x331C5C0],eax"},
                {"off": "0x004", "size": 0x10, "src": "tag 0x16 (DWORD)",
                 "len_at": "0x014", "insn": "0x641661 push 0x331C5C4"},
                {"off": "0x018", "size": 0x80, "src": "tag 0x18 (block)",
                 "len_at": "0x098", "insn": "0x641694 push 0x331C5D8"},
                {"off": "0x09C", "size": 0x10, "src": "tag 0x19 (block)",
                 "len_at": "0x0AC", "insn": "0x6416C4 push 0x331C65C"},
                {"off": "0x0B0", "size": 0x400, "src": "tag 7 (string)",
                 "len_at": "0x4B0", "insn": "0x64178C push 0x331C670"},
                {"off": "0x4B4", "size": 0x80, "src": "tag 0x1B (block)",
                 "len_at": "0x534", "insn": "0x6417FE push 0x331CA74"},
                {"off": "0x538", "size": 4, "src": "channel tag 5 (DWORD)",
                 "insn": "0x64185B push 0x331CAF8"},
            ],
        },
        "consumers": [
            {"site": "0x7F2B90", "reads": ["0x331C5C0", "0x331C5C4",
                                           "0x331C5D8", "0x331C658",
                                           "0x331C65C", "0x331C670",
                                           "0x331CAF8"],
             "call": "0x7F2D2A call 0xB88CC0 (objA, real connection)"},
        ],
    }
    text = json.dumps(layout, indent=1, ensure_ascii=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("WROTE", args.out)
    else:
        print(text)


def cmd_build(args):
    payload = build_payload(host=args.host, port=args.port,
                            extra_fields=args.field, channel=args.channel)
    print("payload size 0x%X, non-zero bytes %d" %
          (len(payload), sum(1 for c in payload if c)))
    if args.out:
        Path(args.out).write_bytes(payload)
        print("WROTE", args.out)


def cmd_create(args):
    """Create TCLS_SHAREDMEMEMORY<pid> and leave it alive for --keep seconds."""
    import ctypes
    import ctypes.wintypes as wt
    import time

    payload = build_payload(host=args.host, port=args.port,
                            extra_fields=args.field, channel=args.channel)
    name = NAME_FMT % args.pid
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    h = k32.CreateFileMappingW(wt.HANDLE(-1).value, None, 0x04, 0,
                               len(payload), name)
    if not h:
        raise SystemExit("CreateFileMappingW(%s) failed: %d" %
                         (name, ctypes.get_last_error()))
    view = k32.MapViewOfFile(h, 0x000F001F, 0, 0, len(payload))
    if not view:
        raise SystemExit("MapViewOfFile failed: %d" % ctypes.get_last_error())
    ctypes.memmove(view, payload, len(payload))
    print("CREATED %s size 0x%X (keep %d s)" % (name, len(payload), args.keep))
    time.sleep(args.keep)
    print("released")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("layout")
    p.add_argument("--out")
    p.set_defaults(func=cmd_layout)

    p = sub.add_parser("build")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=443)
    p.add_argument("--field", action="append", default=[],
                   help="extra trailing fields for the tag 8 string")
    p.add_argument("--channel", type=int, default=1)
    p.add_argument("--out")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("create")
    p.add_argument("--pid", type=int, required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=443)
    p.add_argument("--field", action="append", default=[])
    p.add_argument("--channel", type=int, default=1)
    p.add_argument("--keep", type=int, default=300)
    p.set_defaults(func=cmd_create)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
