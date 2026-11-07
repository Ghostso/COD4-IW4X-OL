#!/usr/bin/env python3
"""Build a TCLS_SHAREDMEMEMORY<pid> byte image for TenProxy.dll's consumer.

Byte-exact model recovered from TenProxy.dll (image base 0x10000000) and
cross-checked against the producer tcls_core.exe sub_407D10.

Model (all offsets relative to the mapping base):

    +0x000  DWORD        slot capacity N (producer writes 0x40).  Used by
                         Initialize only as `N >= 0x40`.
    +0x004  DWORD[64]    offset table, 1-based:
                         entry_off = dword[+0x004 + 4*(tag-1)]
    +0x104               first byte after the table
    entry = base + entry_off
    entry +0x000 DWORD   payload byte length
    entry +0x004 bytes   payload

    Channel indirection:
    +0x004 + 4*(0x14-1) = +0x050  DWORD  channel-table offset
    ch_base = base + dword[+0x050]
    ch_base + 4*(channel-1)       DWORD  sub-table offset (1-based channel)
    sub     = base + that
    sub + 4*(tag-1)               DWORD  entry offset (1-based tag)

This script only writes a file.  It never creates a mapping, never touches a
running process, and never launches the game.  ASCII-only source.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

SIZE = 0x80000
SLOT_CAPACITY = 0x40          # dword at +0x00 that Initialize compares to 0x40
TABLE_OFF = 0x004
TABLE_SLOTS = 0x40
ENTRY_AREA = TABLE_OFF + 4 * TABLE_SLOTS      # 0x104

CHANNEL_SLOT = 0x14           # index used by the mapped+0x50 raw channel read
CHANNEL_PTR_OFF = TABLE_OFF + 4 * (CHANNEL_SLOT - 1)   # 0x050
CHANNEL_PTR_MASK = 0xFFFF     # Initialize adds the dword, but producer
                              # semantics keep the table inside one segment;
                              # a table below 64 KiB is masked to itself.


class Builder:
    def __init__(self, size: int = SIZE):
        self.buf = bytearray(size)
        self.cursor = ENTRY_AREA
        struct.pack_into("<I", self.buf, 0x000, SLOT_CAPACITY)

    def _alloc(self, nbytes: int, align: int = 4) -> int:
        if align > 1 and self.cursor % align:
            self.cursor += align - (self.cursor % align)
        off = self.cursor
        self.cursor += nbytes
        if self.cursor > len(self.buf):
            raise SystemExit("payload exceeds mapping size")
        return off

    def put_entry(self, payload: bytes) -> int:
        off = self._alloc(4 + len(payload))
        struct.pack_into("<I", self.buf, off, len(payload))
        self.buf[off + 4:off + 4 + len(payload)] = payload
        return off

    def set_tag(self, tag: int, payload: bytes) -> int:
        if not 1 <= tag <= TABLE_SLOTS:
            raise SystemExit("tag %d outside table" % tag)
        off = self.put_entry(payload)
        struct.pack_into("<I", self.buf, TABLE_OFF + 4 * (tag - 1), off)
        return off

    def set_dword(self, tag: int, value: int) -> int:
        return self.set_tag(tag, struct.pack("<I", value))

    def alloc_dwords(self, count: int) -> int:
        return self._alloc(4 * count)


def build(host: str, port: int, channel: int = 1, fields=("1004", "0", "0"),
          game_signature: bytes = b"\x00" * 0x80,
          qq_signature: bytes = b"\x00" * 0x80,
          login_key: bytes = b"\x00" * 0x10,
          jump_signature: bytes = b"\x00" * 0x70,
          dns_text: bytes = b"", tag16: int = 0) -> bytes:
    b = Builder()

    # The +0x50 raw dword is masked with 0xFFFF by Initialize, so keep the
    # channel table below 64 KiB and allocate it at a low offset first.
    chan_off = b.alloc_dwords(channel)            # byte offset, NOT 4*index
    sub_off = b.alloc_dwords(TABLE_SLOTS)         # sub-table: 64 dwords
    struct.pack_into("<I", b.buf, chan_off + 4 * (channel - 1), sub_off)
    if chan_off > CHANNEL_PTR_MASK:
        raise SystemExit("channel table offset must fit 16 bits")

    # --- flat tags read through slot +0x24 / +0x28 / +0x2C -------------
    b.set_dword(0x01, 1)                           # ApplySettings gate: must be non-zero
    # TenProxy reads both tags during Initialize and requires a DWORD entry
    # header (length == 4).  Their business values are unresolved; preserving
    # zero keeps the old value semantics while satisfying the container ABI.
    b.set_dword(0x02, 0)
    b.set_dword(0x06, 0)
    b.set_dword(0x16, tag16)                       # second probe / block+0x04
    b.set_tag(0x18, bytes(qq_signature))          # slot +0x28, cap 0x80
    b.set_tag(0x19, b"\x00" * 0x10)               # slot +0x28, cap 0x10
    b.set_dword(0x12, channel)                    # slot +0x24, channel id
    if dns_text:
        b.set_tag(0x07, dns_text)                 # slot +0x28, cap 0x400
    b.set_tag(0x1B, bytes(jump_signature))        # slot +0x28, cap 0x70
    b.set_tag(0x03, bytes([0x01]))                # gate: non-zero
    b.set_tag(0x04, bytes(game_signature))        # slot +0x28, cap 0x80
    b.set_tag(0x05, bytes(login_key))             # slot +0x28, cap 0x10
    b.set_tag(0x0E, b"")                          # slot +0x2C
    b.set_tag(0x0F, "TCLS_SHAREDMEMEMORY".encode("utf-16-le"))  # window name
    b.set_tag(0x10, b"\x00" * 0x28)               # slot +0x2C
    b.set_tag(0x1A, bytes([0x01]))                # gate: non-zero

    text = (";".join([host, str(port)] + list(fields)) + "\x00").encode("ascii")
    e8 = b.put_entry(text)
    e7 = b.put_entry(struct.pack("<I", len(text)))
    e5 = b.put_entry(struct.pack("<I", 0))
    for tag, off in ((0x08, e8), (0x07, e7), (0x05, e5)):
        struct.pack_into("<I", b.buf, sub_off + 4 * (tag - 1), off)

    # Initialize loads [this+0x18C8] (= mapped+4), then reads [eax+0x4C],
    # i.e. mapped+0x50.  That is table slot tag 0x14.
    struct.pack_into("<I", b.buf, CHANNEL_PTR_OFF, chan_off)
    return bytes(b.buf)


def describe(data: bytes) -> dict:
    def d(off):
        return struct.unpack_from("<I", data, off)[0]
    out = {
        "size": len(data),
        "slot_capacity@0x000": d(0x000),
        "table@0x004": "0x40 dword slots",
        "entry_area@0x104": True,
        "table_slot_tag_0x13@0x04C": d(0x04C),
        "channel_ptr@0x050": d(CHANNEL_PTR_OFF),
    }
    raw_ch = d(CHANNEL_PTR_OFF)
    ch = raw_ch & CHANNEL_PTR_MASK
    sub = d(ch + 0)
    out["channel_table"] = ch
    out["channel0_subtable"] = sub
    out["sub_entry_tag5"] = d(sub + 4 * 4)
    out["sub_entry_tag7"] = d(sub + 4 * 6)
    out["sub_entry_tag8"] = d(sub + 4 * 7)
    tag8 = d(sub + 4 * 7)
    out["tag8_len"] = d(tag8)
    out["tag8_text"] = data[tag8 + 4:tag8 + 4 + d(tag8)].decode("latin1")
    non_zero = sum(1 for c in data if c)
    out["non_zero_bytes"] = non_zero
    out["used_prefix"] = hex(max(0x104, tag8 + 4 + d(tag8)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=443)
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--field", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--json")
    args = ap.parse_args()
    fields = args.field or ["1004", "0", "0"]
    data = build(args.host, args.port, args.channel, fields)
    info = describe(data)
    text = json.dumps(info, indent=1)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
        print("WROTE", args.json)
    else:
        print(text)
    if args.out:
        Path(args.out).write_bytes(data)
        print("WROTE %s (%d bytes)" % (args.out, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
