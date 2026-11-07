# -*- coding: utf-8 -*-
"""Locate code referencing the 'net-buffer' reader diagnostic strings. Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
strs={
 0x99EE98:"net-buffer NOT enough",
 0x99EEF0:"string length error",
 0x99EF50:"wstring length error",
 0x99EFB8:"net-buffer NOT enough (unit)",
 0x99F290:"string from net-buffer format error",
 0x99F428:"wstring from net-buffer format error",
}
code_lo,code_hi=0x1000,0x8a8000
code=b[code_lo:code_hi]
for rva,label in strs.items():
    va=C.IB+rva
    pat=struct.pack("<I",va)
    refs=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        refs.append(code_lo+j); i=j+1
    print("%-40s VA=%08x refs=%s" % (label,va,[hex(x) for x in refs]))
