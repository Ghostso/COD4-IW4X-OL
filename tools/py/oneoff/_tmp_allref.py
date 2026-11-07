import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img):
        return None
    return img[o:o+n]
# 0x08269818 是 dvar "3291" 的句柄槽。
# 找所有代码里对该槽的读/写。用 find 定位，然后看前 2 字节是什么指令。
print('=== 所有引用句柄槽 0x08269818 的代码位置 ===')
pat = struct.pack('<I', 0x08269818)
i = img.find(pat, 0)
found=[]
while i>=0:
    va = LO+i
    if 0x00400000 <= va < 0x0EA59000 and cov[i]==1:
        # 尝试从 -1 到 -6 解指令
        best=None
        for back in range(1,7):
            s=i-back
            if s<0 or cov[s]!=1: continue
            import capstone
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
            md=Cs(CS_ARCH_X86, CS_MODE_32)
            for ins in md.disasm(img[s:i+4], LO+s):
                if len(ins.bytes)==back+4 and '0x8269818' in ins.op_str.replace('0x08269818','0x8269818').replace('0x08269818','0x8269818'):
                    best=(ins.address, ins.mnemonic, ins.op_str)
                break
        if best:
            found.append(best)
    i = img.find(pat, i+1)
for a,m,o in found:
    mark = '  ★写' if m in ('mov',) and o.startswith('dword ptr [0x8269818]') else ''
    print('   %08X  %-7s %s%s' % (a,m,o,mark))
print('  共', len(found))
