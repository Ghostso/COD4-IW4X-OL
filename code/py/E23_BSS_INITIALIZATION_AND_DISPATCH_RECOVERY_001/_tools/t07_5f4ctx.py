import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# byte-pattern scan for any operand encoding referencing disp 0x5f4: modrm variants
# We look for the raw pattern of [reg+0x000005f4] i.e. bytes  f4 05 00 00 after modrm
print("=== byte-level scan for  disp32=0x000005F4 in .text/.rdata/.data raw ===")
def scan(name):
    for s in secs:
        if s[0]!=name: continue
        n,va,vs,rp,rs=s
        blob=d[rp:rp+rs]
        pat=b"\xf4\x05\x00\x00"
        i=0; found=[]
        while True:
            j=blob.find(pat,i)
            if j<0: break
            found.append(va+j-4+ 0)  # approximate: instruction start unknown
            i=j+1
        print(name,"dword 0x5F4 occurrences:",len(found))
        for f in found[:40]: print("   near RVA",hex(f))
for nm in (".text",".rdata",".data"): scan(nm)
# show context around 0x1DE91 and 0x1DF7A
def show(rva,n,tag):
    print("="*70); print(tag,hex(IB+rva))
    o=off_of(rva)
    for ins in md.disasm(d[o:o+n],IB+rva):
        print("%06X %-20s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
show(0x1DD80,0x140,"around 0x1DE91")
show(0x1DE70,0x160,"around 0x1DF7A")
