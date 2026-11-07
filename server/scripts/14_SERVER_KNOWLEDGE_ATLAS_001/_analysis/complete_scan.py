import pefile, struct
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def va2off(va):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=va<v+min(vs,rs): return rp+(va-v)
    return None
print("=== raw bytes VA 0x4A2E38..0x4A2E68 ===")
o=va2off(0x4A2E38)
print(data[o:o+0x30].hex(" "))
print()
TARGETS={"0x4A2E50":0x4A2E50, "0x4A2E60":0x4A2E60, "0x4A2E40":0x4A2E40}
print("=== COMPLETE rel32 E8/E9 target scan (.text + .tvm0) ===")
for nm in (".text",".tvm0"):
    va,vs,rp,rs=S[nm]; code=data[rp:rp+rs]; base=IB+va
    hits={k:[] for k in TARGETS}
    total_e8=0; total_e9=0
    for i in range(len(code)-5):
        b=code[i]
        if b==0xE8 or b==0xE9:
            disp=struct.unpack_from("<i",code,i+1)[0]
            tgt=base+i+5+disp
            if b==0xE8: total_e8+=1
            else: total_e9+=1
            for k,t in TARGETS.items():
                if tgt==t: hits[k].append(hex(base+i))
    print(" %s: E8=%d E9=%d" % (nm,total_e8,total_e9))
    for k,v in hits.items(): print("    -> %s : %d %s" % (k,len(v),v[:8]))
print()
print("=== thunk-bank signature count in .text ===")
sig=bytes.fromhex("558BEC8B4D108B49088B4514")
va,vs,rp,rs=S[".text"]; code=data[rp:rp+rs]
c=0; locs=[]
i=0
while True:
    j=code.find(sig,i)
    if j<0: break
    c+=1; locs.append(IB+va+j); i=j+1
print("signature 'push ebp;mov ebp,esp;mov ecx,[ebp+0x10];mov ecx,[ecx+8];mov eax,[ebp+0x14]' count =", c)
print("range: 0x%X .. 0x%X" % (min(locs), max(locs)) if locs else "none")
print()
print("=== imm32 0x3FC occurrences in .text ===")
pat=struct.pack("<I",0x3FC)
hits=[]; i=0
while True:
    j=code.find(pat,i)
    if j<0: break
    hits.append(IB+va+j); i=j+1
print("count =", len(hits))
for h in hits[:20]: print("   VA 0x%X (RVA 0x%X)" % (h, h-IB))