# -*- coding: utf-8 -*-
"""Inspect .tvm0/.tls structure and the 3 exports; search both modules for game-net symbols."""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C

def cstr(r, ml=200):
    o=C.rva2off(r)
    if o is None: return None
    e=C._b.find(b"\0",o,o+ml)
    if e<0: e=o+ml
    return C._b[o:e]

print("=== DLL exports context ===")
for r in (0x1d6582c,0x203d4f7,0x1aa13b0):
    print("export RVA %08x section=%s first16=%s" % (r, C.sec_of_rva(r), C.raw(r,16).hex()))
    ins=C.dis_at(r,16)
    print("   disasm:", (ins.mnemonic+" "+ins.op_str) if ins else None)

# entropy + byte histogram of .tvm0 head to see if it's x86
tv=[s for s in C.SECTIONS if s["name"]==".tvm0"][0]
head=C._b[tv["raw"]:tv["raw"]+0x40]
print("\n.tvm0 head 64 bytes:", head.hex())
import collections, math
d=C._b[tv["raw"]:tv["raw"]+0x40000]
cnt=collections.Counter(d)
ent=-sum((c/len(d))*math.log2(c/len(d)) for c in cnt.values())
print(".tvm0 first 256KB entropy=%.3f"%ent)
# count E8/E9/55 8B EC in first 256KB
print("  E8 count:", d.count(0xE8), " E9:", d.count(0xE9), " prologue(55 8B EC):", d.count(b"\x55\x8b\xec"))

# search both binaries for game-net keywords (case-insensitive ascii)
KW=[b"netchan",b"NETCHAN",b"NetChan",b"clc_",b"svc_",b"gamestate",b"Gamestate",b"gameState",
    b"configstring",b"ConfigString",b"configString",b"opcode",b"Opcode",b"OPCODE",
    b"svc_ops",b"msgtype",b"MsgType",b"packet",b"Packet",b"challenge",b"connectResponse",
    b"GAME_",b"CG_",b"SV_",b"CL_"]
print("\n=== keyword search ===")
for kw in KW:
    for mod,data,base in (("DLL",C._b,C.IB),("EXE",C._bex,0x400000)):
        cnt=data.count(kw)
        if cnt:
            # first few RVAs
            locs=[]; i=0
            while len(locs)<4:
                j=data.find(kw,i)
                if j<0: break
                locs.append(j); i=j+1
            print("  %-14s %-4s count=%-4d first_off=%s" % (kw.decode(), mod, cnt, [hex(x) for x in locs]))
