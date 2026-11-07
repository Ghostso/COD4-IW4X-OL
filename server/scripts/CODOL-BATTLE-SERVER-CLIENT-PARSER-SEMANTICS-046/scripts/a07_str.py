# -*- coding: utf-8 -*-
"""a07: read string literals referenced by the 0x85D8xx receive function."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva):
    b=C.raw(rva,300)
    if b is None: return "<outside file>"
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")
print("=== strings referenced in the receive function ===")
for va in (0xD85AB0,):
    print("  VA 0x%08X RVA 0x%08X -> %r"%(va, va-IB, s(va-IB)))
print()
print("=== string referenced at 0x85D7CA (fmt from 0xC3F57E call in 0x85D5A0) ===")
print("  ", repr(s(0xD85AB0-IB)))
