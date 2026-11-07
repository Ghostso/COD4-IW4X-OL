import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
VT=0x00DC7274
# 0x63C5E0 在 vtable 里的偏移
offs=[]
for off in range(0,0x200,4):
    b=rd(VT+off,4)
    if b and struct.unpack('<I',b)[0]==0x0063C5E0:
        offs.append(off)
print('=== 0x63C5E0 在 vtable 0x%08X 中的偏移: %s ===' % (VT, [hex(o) for o in offs]))
print()
# 找所有 'call dword ptr [reg + off]' 形式的间接调用, 且 off 匹配
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
for o in offs:
    pat=struct.pack('<H', o)
    print('=== 搜 call [reg+0x%X] 形态 (opcode FF /2 是 call) ===' % o)
    # FF 90+disp32 = call [eax+disp32]; FF 91 = [ecx]; FF 92=[edx]; FF 93=[ebx]
    # FF 94 = SIB; FF 95=[ebp]; FF 96=[esi]; FF 97=[edi]
    cnt=0
    for modrm in range(0x90,0x98):
        needle=bytes([0xFF, modrm]) + struct.pack('<I', o)
        i=img.find(needle, 0x400000-LO, 0x0EA59000-LO)
        while i>=0 and cnt<10:
            if all(cov[i+k]==1 for k in range(6)):
                print('   0x%08X  %s' % (LO+i, needle.hex(' ')))
                cnt+=1
            i=img.find(needle, i+1, 0x0EA59000-LO)
    if cnt==0: print('   无')
