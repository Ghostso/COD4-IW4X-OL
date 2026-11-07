# -*- coding: utf-8 -*-
"""042 evidence generation: dump key function binaries/Disasm + build evidence TSVs.
Read-only. Target = unpacked client engine image (image_best.bin, sha 17ce...f045)."""
import sys, os, struct, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C

EV=C.EV
os.makedirs(EV, exist_ok=True)
def dumpfn(rva, end, path, label):
    lines=["# %s  RVA=%08x..%08x  VA=%08x..%08x"%(label,rva,end,C.IB+rva,C.IB+end)]
    for i in C.dis_range(rva, end):
        lines.append("%08x  %-18s %-8s %s"%(i.address-C.IB, i.bytes.hex(), i.mnemonic, i.op_str))
    open(os.path.join(EV,path),"w",encoding="utf-8",newline="").write("\n".join(lines)+"\n")
    print("wrote", path, "(%d insns)"%(len(lines)-1))

dumpfn(0x87be00,0x87bf50,"netbuf_packetread_87be00.txt","packet read primitive 0x87BE00")
dumpfn(0x87c110,0x87c200,"netbuf_deser_87c110.txt","net-buffer deserializer entry 0x87C110")
dumpfn(0x87d5a0,0x87d650,"netbuf_deser_87d5a0.txt","net-buffer deserializer entry 0x87D5A0")
dumpfn(0x87a890,0x87a980,"netbuf_helper_87a890.txt","net-buffer sizeinfo helper 0x87A890")
dumpfn(0x85d3a0,0x85d430,"msgwrap_85d3a0.txt","message wrapper 0x85D3A0")
dumpfn(0x85d430,0x85d4c0,"msgwrap_85d430.txt","message wrapper 0x85D430")
dumpfn(0x85e6f0,0x85e800,"msgdispatch_85e6f0.txt","message dispatcher 0x85E6F0")
dumpfn(0x85e4f0,0x85e5c0,"msghandler_85e4f0.txt","dispatch handler 0x85E4F0")
dumpfn(0x85e5c0,0x85e6f0,"msghandler_85e5c0.txt","dispatch handler 0x85E5C0")
dumpfn(0x87ba50,0x87ba60,"packetread_thunk_87ba50.txt","packet-read thunk 0x87BA50")
print("done")
