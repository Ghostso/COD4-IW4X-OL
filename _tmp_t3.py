import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 0xB75DA0 是什么函数 (判据里读计时器的) ===')
c=rd(0xB75DA0,0x30)
if c:
    for ins in md.disasm(c,0xB75DA0):
        print('   %08X  %-16s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        if ins.mnemonic=='ret': break
print()
print('=== dwRoomMatchUber 的 +0x130 = 0x3B046DB8 指向什么 ===')
P=0x3B046DB8
b=rd(P,0x20)
print('  内容:', b.hex(' ') if b else '未覆盖')
for k in range(0,0x20,4):
    v=u32(P+k)
    print('    [+0x%02X] = 0x%08X' % (k, v or 0))
print()
print('=== 关键: +0x138 处到底是 0 还是"另一个结构" ===')
print('  0x63C1E7 lea ecx,[esi+0x138] / call 0xB75DA0')
print('  => 0xB75DA0 把 ecx 当对象, 读它的某个 float')
b=rd(0x3ACA0CD8+0x138,0x10)
print('  对象+0x138 的 16 字节:', b.hex(' ') if b else '未覆盖')
