import sys, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
o,_=C.off(0x1000); text=C.d[o:o+C.pe.sections[0].SizeOfRawData]
seq=[]
for ins in sweep(md, text, C.IB+0x1000): seq.append((ins.address-C.IB,ins.mnemonic,ins.op_str))
print("insns:",len(seq))
starts=[r for r,m,_ in seq if m=="push" and _=="ebp"]
print("prologue candidates:",len(starts))
def func_start(a):
    i=bisect.bisect_right(starts,a)-1
    return starts[i] if i>=0 else None
sites=[0xA0EFC,0xA0F0B,0xA135E,0xA17B5,0xA1B74,0xA2490,0xA249B,0xA24A7,0xA26F4,0xA276C,0xA27A8,0xA27D7,0xA2879,0xA28A9,0xAA5C7,0xAA600,0xAA6FE,0xAA710,0xAA79D,0xAA7AF,0xAA7C1,0xAA7D3,0xAA7E5,0xAADC5,0xAADD0]
import collections
byf=collections.defaultdict(list)
for s in sites: byf[func_start(s)].append(s)
print()
print("=== containing functions of MSG_ReadBits callers in cluster ===")
for f in sorted(byf): print("   func 0x%06X : sites %s" % (f,["0x%X"%x for x in byf[f]]))