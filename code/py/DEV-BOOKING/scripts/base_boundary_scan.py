# -*- coding: utf-8 -*-
"""Narrow, read-only Base.dll boundary scan for Booking dispatch evidence.

Only searches for Booking-related strings and nearby PE section metadata.
No whole-DLL reversing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pefile


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
DLL = ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll"

NEEDLES = [
    b"mmbook",
    b"mmbook accepted",
    b"mmbook timedout",
    b"mmstart",
    b"booking",
    b"Booking",
    b"DedicatedControl",
    b"dedicated",
    b"bridge",
    b"sharedRoomClient",
    b"bookingDispatcher",
    b"dispatcher",
    b"callback",
    b"MM_RESERVE_CMD_REQUEST",
]


def iter_ascii_strings(data: bytes, min_len: int = 4):
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        yield m.start(), m.group().decode("ascii", "replace")


def main() -> None:
    data = DLL.read_bytes()
    print(f"Base.dll = {DLL}")
    print(f"size     = {len(data):,} bytes")
    pe = pefile.PE(data=data, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    print(f"imagebase= 0x{image_base:X}")
    print("sections:")
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode("ascii", "replace")
        print(
            f"  {name:<8} VA=0x{s.VirtualAddress:08X} "
            f"VS=0x{s.Misc_VirtualSize:X} RAW=0x{s.PointerToRawData:X} "
            f"RS=0x{s.SizeOfRawData:X} flags=0x{s.Characteristics:08X}"
        )
    print()

    print("needle scan:")
    for needle in NEEDLES:
        hits = []
        pos = 0
        while True:
            hit = data.find(needle, pos)
            if hit < 0:
                break
            hits.append(hit)
            pos = hit + 1
        print(f"  {needle!r}: {len(hits)}")
        for file_off in hits[:20]:
            va = image_base + file_off
            try:
                rva = pe.get_rva_from_offset(file_off)
                sec = pe.get_section_by_rva(rva)
                sec_name = sec.Name.rstrip(b"\x00").decode("ascii", "replace")
                print(
                    f"    off=0x{file_off:08X} rva=0x{rva:08X} "
                    f"va~=0x{va:08X} section={sec_name}"
                )
            except Exception:
                print(f"    off=0x{file_off:08X}")
    print()

    print("interesting ASCII strings (booking/mm/dispatch):")
    pat = re.compile(r"(mm|book|dispatch|reserve|dedicated|bridge)", re.I)
    count = 0
    for off, s in iter_ascii_strings(data):
        if len(s) > 180:
            continue
        if not pat.search(s):
            continue
        try:
            rva = pe.get_rva_from_offset(off)
            sec = pe.get_section_by_rva(rva)
            sec_name = sec.Name.rstrip(b"\x00").decode("ascii", "replace")
        except Exception:
            rva = None
            sec_name = "?"
        print(
            f"  0x{off:08X} rva={rva if rva is None else hex(rva)} "
            f"section={sec_name}: {s}"
        )
        count += 1
        if count >= 400:
            print("  ... truncated at 400")
            break


if __name__ == "__main__":
    main()
