import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
o,_=C.off(0x1000); text=C.d[o:o+C.pe.sections[0].SizeOfRawData]
print("scanning...")
seq=[]
for ins in sweep(md, text, C.IB+0x1000): seq.append((ins.address-C.IB, ins.mnemonic, ins.op_str))
print("insns:",len(seq))
# The reader must do: read bit = (data[bitpos>>3] >> (bitpos&7)) & 1 ; bitpos++
# structural marker: 'shr r,3' AND 'and r,7' in the SAME function AND a byte load 'movzx/mov ... byte ptr [...+...]'
cand=[]
for i,(rva,m,op) in enumerate(seq):
    if m=="and" and op.replace(" ","").endswith(",7"):
        for j in range(i+1,min(i+8,len(seq))):
            if seq[j][1]=="shr" and seq[j][2].replace(" ","").endswith(",3"):
                # look ahead for a byte load within 8
                win=seq[j:j+9]
                if any(w[1] in ("mov","movzx") and "byte ptr" in w[2] for w in win):
                    cand.append(rva); break
print("reader-shaped sites:",len(cand))
def cluster(xs, gap=0x600):
    out=[]
    for a in xs:
        if out and a-out[-1][-1]<=gap: out[-1].append(a)
        else: out.append([a])
    return out
cl=cluster(cand)
print("clusters:",len(cl))
for c in cl: print("   0x%X .. 0x%X  (%d sites)" % (c[0],c[-1],len(c)))