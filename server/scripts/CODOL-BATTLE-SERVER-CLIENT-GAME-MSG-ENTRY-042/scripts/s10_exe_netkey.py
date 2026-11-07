# -*- coding: utf-8 -*-
"""Targeted search for message/network parser symbols in the EXE (raw offsets),
printing surrounding printable context."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
def show(kw, limit=8, ctx=64):
    print("### %s" % kw)
    j=0; n=0
    while n<limit:
        k=data.find(kw,j)
        if k<0: break
        a=max(0,k-ctx); b=min(len(data),k+len(kw)+ctx)
        seg=data[a:b]
        # printable only
        pr="".join(chr(c) if 32<=c<127 else "." for c in seg)
        print("  @%08x %s" % (k, pr))
        j=k+1; n+=1
    if n==0: print("  (none)")
for kw in (b"netchan",b"NETCHAN",b"NetChan",b"MSG_",b"SV_",b"CL_",b"gamestate",b"Gamestate",
           b"ConfigString",b"Configstring",b"connectResponse",b"challenge",b"GAME_",b"CG_",
           b"svc_",b"clc_",b"PACKET",b"Packet",b"packet",b"message",b"Message",b"parse",b"Parse",
           b"OPCODE",b"Opcode",b"opcode",b"sequenc",b"Sequence",b"fragment",b"Fragment"):
    show(kw, limit=6, ctx=48)
