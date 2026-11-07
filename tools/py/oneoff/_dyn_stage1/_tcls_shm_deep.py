from pathlib import Path
import pefile
from capstone import *

ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
P=ROOT/r"WeGame\tcls\tcls_core.exe"
d=P.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
imp={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
    for x in (e.imports or []):
        if x.name:
            imp[base+x.address]=x.name.decode(errors="replace")

def rva_of_va(va): return va-base
def off(va):
    r=va-base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+(r-s.VirtualAddress)
    raise ValueError(hex(va))
def dis(start,size):
    b=d[off(start):off(start)+size]
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    return list(md.disasm(b,start))
def ann(ins):
    if ins.mnemonic in ("call","jmp") and ins.op_str.startswith("dword ptr ["):
        try: return imp.get(int(ins.op_str[12:-1],16),"")
        except: return ""
    return ""

def dump(start,size,label=""):
    print("=====",label,hex(start),hex(start+size))
    for i in dis(start,size):
        print("%08X %-22s %-7s %-32s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str,ann(i)))

def xrefs(target):
    out=[]
    for s in pe.sections:
        b=d[s.PointerToRawData:s.PointerToRawData+min(s.SizeOfRawData,len(d))]
        va=base+s.VirtualAddress
        for k in range(len(b)-4):
            if int.from_bytes(b[k:k+4],"little")==target:
                out.append(va+k)
    return out

# functions around all producers and helper
for a,n in [(0x404020,0x180),(0x4077F0,0x260),(0x407D10,0x260),(0x4078F0,0x280),(0x407E80,0x2A0),(0x407F80,0x220),(0x407FC0,0x260)]:
    try: dump(a,n)
    except Exception as e: print("ERR",hex(a),e)

print("=== XREFS ===")
for t in [0x5822E8,0x582310,0x556094,0x404020,0x4078F0,0x407D10]:
    print(hex(t),[hex(x) for x in xrefs(t)])

# identify all calls to 404020 / 4078f0 elsewhere
for fn in [0x404020,0x4078F0]:
    xs=xrefs(fn)
    print("CALLREF",hex(fn),[hex(x) for x in xs])
    for x in xs:
        dump(x-24,80,"caller")
