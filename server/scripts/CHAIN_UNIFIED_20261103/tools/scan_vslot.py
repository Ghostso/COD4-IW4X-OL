"""按字节模式快速枚举 "call dword ptr [reg + SLOT]" 虚调用点。

比 find_vcall_slot.py 的全库线性反汇编快几个数量级：
  x86 的 `call r/m32` 是 FF /2，寄存器直接形式  FF 50+reg  disp8/32
  所以 `call dword ptr [eax+4]` = FF 50 04，`[ecx+4]` = FF 51 04 ...
  disp==0 时 4 字节 disp 形式 = FF 90 0000 0000 等。

用法:
  python -I scan_vslot.py 4                 # 列出所有 [reg+4] 间接调用
  python -I scan_vslot.py 4 --near 0x331C0C8   # 窗口内出现该立即数才算
  python -I scan_vslot.py 4 --ctx 40        # 反汇编前 40 字节上下文
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

SLOT = int(sys.argv[1], 0) if len(sys.argv) > 1 else 4
near = None
ctx = 0
for i, a in enumerate(sys.argv):
    if a == '--near' and i + 1 < len(sys.argv):
        near = int(sys.argv[i + 1], 0)
    if a == '--ctx' and i + 1 < len(sys.argv):
        ctx = int(sys.argv[i + 1], 0)

# 收集所有段的可搜索区域: (file_off_start, file_off_end, va)
regions = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    regions.append((ra, ra + n, ib + va_))

# 构造所有 "FF <modrm> <disp>" 形态的候选
pats = []
for reg in range(8):                 # eax..edi
    modrm = 0x50 + reg               # mod=01 (disp8)
    pats.append(bytes([0xFF, modrm, SLOT & 0xFF]))
    modrm = 0x90 + reg               # mod=10 (disp32)
    pats.append(bytes([0xFF, modrm]) + (SLOT & 0xFFFFFFFF).to_bytes(4, 'little'))
SIB = [0xA0 + r for r in range(8)]   # mod=10, rm=100 (SIB)
for reg in range(8):
    pass

hits = []
for start, end, va0 in regions:
    blob = d[start:end]
    for pat in pats:
        i = blob.find(pat)
        while i >= 0:
            hits.append((va0 + i, pat.hex()))
            i = blob.find(pat, i + 1)
    # SIB 形式: FF 94 <sib> <disp32>  /  FF 54 <sib> <disp8>
    for reg in range(8):
        m = 0x94 + reg
        j = 0
        while True:
            j = blob.find(bytes([0xFF, m]), j)
            if j < 0:
                break
            if j + 6 <= len(blob):
                sib = blob[j + 2]
                disp = int.from_bytes(blob[j + 3:j + 7], 'little')
                if sib == 0x24 and disp == SLOT:      # [esp+SLOT]
                    hits.append((va0 + j, blob[j:j + 7].hex()))
                if sib == 0x2D and disp == SLOT:      # [ebp+SLOT]
                    hits.append((va0 + j, blob[j:j + 7].hex()))
            j += 1

if near is not None:
    nb = near.to_bytes(4, 'little')
    keep = []
    for addr, h in hits:
        lo = max(0, addr - ib - 0x100)
        hi = addr - ib + 0x20
        if nb in d[lo:hi]:
            keep.append((addr, h))
    hits = keep

print('slot +0x%x : call [reg+SLOT] 命中 %d 处' % (SLOT, len(hits)))
md = None
if ctx:
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.skipdata = True

for addr, h in sorted(hits):
    print('  %08X  %s' % (addr, h))
    if md:
        off = addr - ib - ctx
        for ins in md.disasm(d[off:addr - ib + 8], addr - ctx):
            print('        %08X  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
