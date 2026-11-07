import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# Find function starts by scanning for prologues in .text
text=[s for s in pe.sections if b".text" in s.Name][0]
blob=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
code_va=ib+text.VirtualAddress
starts=[]
i=0
n=len(blob)
while i < n-5:
    # push ebp; mov ebp,esp  OR  push -1; push imm (SEH)  OR call-target-aligned
    if blob[i]==0x55 and blob[i+1]==0x8B and blob[i+2]==0xEC:
        starts.append(code_va+i); i+=1; continue
    if blob[i]==0x6A and blob[i+1]==0xFF and blob[i+2]==0x68:
        starts.append(code_va+i); i+=1; continue
    i+=1
print("candidate function starts in .text: %d"%len(starts))
# Print functions whose range covers the pipe VAs
keys=[0x10033F00,0x10034000,0x10034100,0x10034200,0x10034300,0x10034400,0x10037200,0x10037300]
for k in keys:
    prev=[s for s in starts if s<=k]
    nxt=[s for s in starts if s>k]
    if prev:
        print("VA 0x%08X covered by func 0x%08X (next 0x%08X)"%(k, max(prev), min(nxt) if nxt else 0))
