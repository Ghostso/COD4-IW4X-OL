"""精确枚举 "mov dword/word/byte ptr [reg+disp], imm" —— 直接给出写入的立即数。

比 scan_pat 强的地方: 它按 **modrm 全枚举 + disp32 匹配 + 取出 imm** 一条龙,
不用再人工反汇编认值。用于把状态机的每个状态取值全部列清。

用法:
  python -I scan_memwr.py --dword 0x4d4           # 所有  mov dword [reg+0x4d4], imm
  python -I scan_memwr.py --word  0x502           # 所有  mov word  [reg+0x502], imm
  python -I scan_memwr.py --dword 0x4d4 --any     # 连 [esp+..]/[ebp+..]/SIB 形式一起收
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

mode = 'dword'
disp = 0x4d4
sizes = {'byte': 1, 'word': 2, 'dword': 4}
for i, a in enumerate(sys.argv):
    if a == '--byte':
        mode, disp = 'byte', int(sys.argv[i + 1], 0)
    if a == '--word':
        mode, disp = 'word', int(sys.argv[i + 1], 0)
    if a == '--dword':
        mode, disp = 'dword', int(sys.argv[i + 1], 0)

isz = sizes[mode]
opsize = b'' if mode == 'dword' else (b'\x66' if mode == 'word' else b'')
disp_b = disp.to_bytes(4, 'little')

# c7 = mov r/m32, imm32 ; mod=10(0x80) → modrm = 0x80|reg<<3|rm, rm!=4 才有 disp32
pats = []
for reg in range(8):
    for rm in (0, 1, 2, 3, 5, 6, 7):          # rm=4 需 SIB
        modrm = 0x80 | (reg << 3) | rm
        pats.append(opsize + b'\xc7' + bytes([modrm]) + disp_b)
# SIB 形式  mod=10 rm=100 → modrm = 0x80|reg<<3|4
for reg in range(8):
    for sib_rm in (0, 1, 2, 3, 5, 6, 7):      # scale=0, index=none(100) 会是 esp; 这里 index=reg2
        for index in range(8):
            if index == 4:
                continue
            sib = (0 << 6) | (index << 3) | sib_rm
            modrm = 0x80 | (reg << 3) | 4
            pats.append(opsize + b'\xc7' + bytes([modrm, sib]) + disp_b)

hits = []
for pat in pats:
    immlen = isz
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            if i + len(pat) + immlen <= len(blob):
                imm = int.from_bytes(blob[i + len(pat):i + len(pat) + immlen], 'little')
                hits.append((ib + va_ + i, pat.hex(), imm))
            i = blob.find(pat, i + 1)

hits.sort()
seen = set()
out = []
for va, h, imm in hits:
    if va in seen:
        continue
    seen.add(va)
    out.append((va, imm))

print('mov %s [reg+0x%X], imm  —— %d 处' % (mode, disp, len(out)))
from collections import Counter
c = Counter(v for _, v in out)
print('取值分布: %s' % ', '.join('%d×%d' % (n, v) for v, n in sorted(c.items(), key=lambda kv: -kv[1])))
print()
for va, imm in out:
    print('  %08X  = %-6d (0x%X)' % (va, imm, imm))
