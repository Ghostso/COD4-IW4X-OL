# -*- coding: utf-8 -*-
import sys,re,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
# xrefs to key HTTP/updater strings
targets={0xC5B440:"GET %s HTTP/1.1",0xC383FC:"POST request",0xD28CA0:"down-update.qq.com",0xC37CD4:"POST to GET",0xC38934:"HTTP/1.0 keepalive"}
hits={k:[] for k in targets}
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_IMM and (op.imm&0xffffffff) in targets:
            hits[op.imm&0xffffffff].append((ins.address-C.IB,fs(ins.address-C.IB),ins.mnemonic))
for t,n in targets.items():
    print("=== %s (0x%X) refs: %d ==="%(n,t,len(hits[t])))
    for r,f,m in hits[t][:10]: print("   0x%06X in func 0x%06X (%s)"%(r,f,m))
print()
# libcurl-ish strings
import re
for pat in [rb"curl_[a-z_]+", rb"CURLcode", rb"libcurl", rb"curl_easy"]:
    cnt=sum(len(list(re.finditer(re.escape(pat),C.d))) for _ in [0] if True)
    print("pattern %r occurrences via bytes.count: %d"%(pat, C.d.count(pat.rstrip(b'[a-z_]+') if False else pat.split(b'[')[0])))
