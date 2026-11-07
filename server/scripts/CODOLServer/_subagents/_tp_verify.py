#!/usr/bin/env python3
"""Evaluate both layout models against the real TenProxy.dll reader semantics.

No process, no mapping, no debugger.  Pure emulation of the exact instruction
sequences recovered at:

  GetDWORD 0x10007DA0   (vtable +0x24)
  GetBytes 0x10007EA0   (vtable +0x28)
  GetBlock 0x10008250   (vtable +0x30, channel)
  GetDwordC 0x10008510  (vtable +0x38, channel)

ASCII-only output.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _tenproxy_build as B  # noqa: E402


def dw(buf, off):
    if off < 0 or off + 4 > len(buf):
        return None
    return struct.unpack_from("<I", buf, off)[0]


class Proxy:
    """Mirror of the CTclsProxy fields the readers touch."""

    def __init__(self, mapped: bytes):
        self.base = mapped
        self.p_18c4 = 0        # mapped base
        self.p_18c8 = 0        # mapped + 4  (tag table)
        self.p_18cc = None     # byte offset of channel table (from mapped+0x50)
        self.p_18d0 = dw(mapped, 0)
        self.init_ok = False

    def initialize(self):
        # 0x100061E8..0x100062FB then 0x1000635E..0x10006383
        if self.p_18d0 is None or self.p_18d0 < 0x40:
            return False
        self.p_18c4 = 0
        self.p_18c8 = 4
        chan = dw(self.base, self.p_18c8 + 0x4C)
        # 0x10006392 mov ecx,[eax+0x4C] ; 0x100063A1 add edx,[ebp-0x10A4]
        # edx = mapped base, so p_channel = mapped + (dword & 0xFFFF)
        self.p_18cc = None if chan is None else (chan & 0xFFFF)
        self.init_ok = True
        return True

    def _entry(self, tag):
        """GetDWORD/GetBytes raw part: uses [this+0x18C8] as index base."""
        if self.p_18c8 == 0 or self.p_18c4 is None:
            return None, 0
        off = dw(self.base, self.p_18c8 + 4 * tag - 4)
        if off is None:
            return None, 0
        return off, off + 4

    def get_dword(self, tag):
        off, payload = self._entry(tag)
        if off is None:
            return 0
        ln = dw(self.base, off)
        if ln != 4:
            return 0
        val = dw(self.base, payload)
        return 1 if val is None else val

    def get_bytes(self, tag, want: int):
        """Return (ok, length, bytes)."""
        off, payload = self._entry(tag)
        if off is None:
            return 0, 0, b""
        ln = dw(self.base, off)
        if ln is None:
            return 0, 0, b""
        if want == 0:
            return 1, ln, b""
        n = min(want, ln)
        return 1, ln, self.base[payload:payload + n]

    # --- channel readers: base = mapped + dword[this+0x18CC] -------------
    def _chan_entry(self, tag, channel):
        if self.p_18cc is None:
            return None
        sub = dw(self.base, self.p_18cc + 4 * channel - 4)
        if sub is None:
            return None
        off = dw(self.base, sub + 4 * tag - 4)
        return off

    def chan_get_block(self, tag, channel, want):
        off = self._chan_entry(tag, channel)
        if off is None:
            return 0, 0, b""
        ln = dw(self.base, off)
        if ln is None:
            return 0, 0, b""
        if want == 0:
            return 1, ln, b""
        n = min(want, ln)
        return 1, ln, self.base[off + 4:off + 4 + n]

    def chan_get_dword(self, tag, channel):
        off = self._chan_entry(tag, channel)
        if off is None:
            return 0
        ln = dw(self.base, off)
        if ln != 4:
            return 0
        val = dw(self.base, off + 4)
        return 1 if val is None else val


def kuhn_model():
    """The hypothesis under test: table A holds *entry* offsets and tag 0x13
    points at the channel table the same way."""
    buf = bytearray(B.SIZE)
    struct.pack_into("<I", buf, 0, 0x40)          # version
    cur = 0x200

    def entry(payload):
        nonlocal cur
        off = cur
        struct.pack_into("<I", buf, off, len(payload))
        buf[off + 4:off + 4 + len(payload)] = payload
        cur += 4 + len(payload) + ((-(4 + len(payload))) % 4)
        return off

    def tag(t, payload):
        struct.pack_into("<I", buf, 4 + 4 * (t - 1), entry(payload))

    tag(0x12, struct.pack("<I", 1))
    sub = cur
    cur += 0x100
    ch = cur
    cur += 4
    struct.pack_into("<I", buf, 4 + 4 * (0x13 - 1), ch)   # tag 0x13 = table
    struct.pack_into("<I", buf, ch, sub)                  # channel 1 -> sub
    struct.pack_into("<I", buf, sub + 4 * (0x08 - 1),
                     entry(b"127.0.0.1;443;1004;0;0\x00"))
    struct.pack_into("<I", buf, sub + 4 * (0x07 - 1),
                     entry(struct.pack("<I", 23)))
    struct.pack_into("<I", buf, sub + 4 * (0x05 - 1),
                     entry(struct.pack("<I", 0)))
    return bytes(buf)


def report(name, buf):
    p = Proxy(buf)
    ok = p.initialize()
    print("== %s ==" % name)
    print("  mapped+0x000 = 0x%X  -> Initialize accepted: %s"
          % (dw(buf, 0) or 0, ok))
    ch = dw(buf, 0x50)
    print("  mapped+0x050 = 0x%X  -> channel table base = 0x%X"
          % (ch or 0, (0 if ch is None else ch)))
    print("  p_18cc (channel base) = 0x%X" % (p.p_18cc or 0))
    print("  GetDWORD(0x12) = %d   %s" % (
        p.get_dword(0x12), "<-- OK" if p.get_dword(0x12) else "<-- FAIL"))
    ok8, ln8, data8 = p.chan_get_block(0x08, 1, 0x400)
    print("  chan GetBytes(8) ok=%s len=%d %r" % (ok8, ln8, data8))
    val7 = p.chan_get_dword(0x07, 1)
    print("  chan GetDWORD(7) = %d  match8=%s"
          % (val7, val7 == ln8))
    print("  chan GetDWORD(5) = %d" % p.chan_get_dword(0x05, 1))


def main():
    report("Kuhn model (table holds ENTRY offsets)",
           kuhn_model())
    report("Corrected model (table holds TAG SLOT offsets)",
           B.build("127.0.0.1", 443))
    return 0


if __name__ == "__main__":
    sys.exit(main())
