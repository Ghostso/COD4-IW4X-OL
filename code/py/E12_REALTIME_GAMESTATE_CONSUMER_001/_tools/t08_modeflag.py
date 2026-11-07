import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
print("=== writes to 0x743de98 (demo/network mode flag) ===")
for ins in sweep(md,text,base):
    if "0x743de98" in ins.op_str and ins.mnemonic in ("mov","or","and","add","xor"):
        print("  %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== EXE_ERR strings raw scan ===")
o2,_=C.off(0xCD5F00)
raw=C.d[o2:o2+0x800]
for m in re.finditer(rb"EXE_[A-Za-z_]+", raw):
    va=C.IB+0xCD5F00+m.start()
    b=raw[m.start():m.start()+90].split(b"\0")[0]
    print("   0x%X %r"%(va,b.decode("latin-1")))
