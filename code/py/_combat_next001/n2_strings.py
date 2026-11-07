# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=80):
    b = pe.read(va, maxn)
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1")

print("=== exact string table 0xDC6700..0xDC67A0 ===")
cur = 0xDC6700
end = 0xDC67A0
p = cur
while p < end:
    b = pe.read(p, 1)
    if b is None: break
    if b[0] == 0:
        p += 1; continue
    s = cstr(p)
    print("   %08X  %r" % (p, s))
    p += len(s) + 1

print()
print("=== bytes 0xDC6720..0xDC6740 ===")
print("   " + pe.read(0xDC6720, 32).hex(" "))
print()
print("=== so: 0xDC6724 = %r ; 0xDC672C = %r ===" % (cstr(0xDC6724), cstr(0xDC672C)))
print("   0xDC672C-0xDC6724 = %d" % (0xDC672C - 0xDC6724))
print("   'mmbook' len=%d incl NUL=%d" % (len(cstr(0xDC6724)), len(cstr(0xDC6724)) + 1))
