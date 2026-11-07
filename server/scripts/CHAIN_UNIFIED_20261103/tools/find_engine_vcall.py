"""找出"在某函数的窗口内先取到引擎句柄、随后做 vt+DISP 虚调用"的点。

动机: 引擎对象的 vtable(`0xD5AFA4`)槽位函数(如 vt+0x04=0xBB45E0、vt+0x10=0xBB4FA0)
      在镜像里**不作为立即数出现**(scan_const 各只命中 1 次 = 表项本身), 所以只能反着找:
      枚举所有 `mov rA,[rB+DISP]; call rA` 与 `mov rA,[rB]; call [rA+DISP]`,
      再看它前面 WIN 字节内有没有"取引擎"的痕迹:
        - E8 到 0xBAC600   (= mov eax,[ecx+0x1F0], 引擎 getter)
        - E8 到 0x643300   (单例 getter)
        - `mov reg,[0x331C0C8]` 的编码 (a1 c8 c0 31 03 / 8b <modrm> c8 c0 31 03)
      引擎对象 = [0x643300()+0x1F0] = [0x331C0C8]^0xD362501F

用法:
  python -I find_engine_vcall.py 4
  python -I find_engine_vcall.py 0x10 --win 0x900
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

disp = int(sys.argv[1], 0) if len(sys.argv) > 1 else 4
win = 0x900
gap = 40
for i, a in enumerate(sys.argv):
    if a == '--win':
        win = int(sys.argv[i + 1], 0)
    if a == '--gap':
        gap = int(sys.argv[i + 1], 0)

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']
GE = 0xBAC600          # 引擎 getter
SING = 0x643300        # 单例 getter
G331 = bytes.fromhex('c8c03103')
# mov reg,[reg+0x1F0] 的各寄存器编码 (mod=10, disp32=0x1F0)
F1F0 = b''.join(bytes([0x8B, 0x80 | (r << 3) | rm]) + (0x1F0).to_bytes(4, 'little')
                for r in range(8) for rm in (0, 1, 2, 3, 5, 6, 7))


def e8_targets(blob, base):
    """返回 blob 内所有 E8 的目标 VA"""
    out = []
    i = 0
    while True:
        i = blob.find(b'\xe8', i)
        if i < 0 or i + 5 > len(blob):
            break
        r = int.from_bytes(blob[i + 1:i + 5], 'little', signed=True)
        out.append((base + i + 5 + r) & 0xFFFFFFFF)
        i += 1
    return out


def has_engine_acq(lo_va, hi_va):
    o1 = va2off(secs, ib, lo_va)
    o2 = va2off(secs, ib, hi_va)
    if o1 is None or o2 is None or o2 <= o1:
        return []
    blob = d[o1:o2]
    hits = []
    for t in e8_targets(blob, lo_va):
        if t in (GE, SING):
            hits.append('call 0x%08X' % t)
    if G331 in blob:
        hits.append('ref [0x331C0C8]')
    if F1F0 in blob:
        hits.append('load [reg+0x1F0]')
    return hits


rows = []
# 形态 B: mov rA,[rB+disp] ; call rA
for r in range(8):
    pat = bytes([0xFF, 0xD0 + r])
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            ca = ib + va_ + i
            for back in range(3, gap + 1):
                mv = ca - back
                om = va2off(secs, ib, mv)
                if om is None:
                    continue
                b = d[om:om + 8]
                if len(b) < 3 or b[0] != 0x8B:
                    continue
                modrm = b[1]
                mod = modrm >> 6
                if ((modrm >> 3) & 7) != r:
                    continue
                rB = modrm & 7
                if mod == 0:
                    dd = 0 if rB != 5 else None
                elif mod == 1:
                    dd = b[2]
                elif mod == 2 and len(b) >= 6:
                    dd = int.from_bytes(b[2:6], 'little')
                else:
                    dd = None
                if dd == disp:
                    rows.append((ca, mv, 'B', r, rB))
                    break
                break
            i = blob.find(pat, i + 1)

# 形态 A: mov rA,[rB] ; ... ; call [rA+disp]
if disp <= 0xFF:
    for r in range(8):
        pat = bytes([0xFF, 0x10 | r, disp])
        for va_, vs, ra, rs in secs:
            n = min(vs, rs)
            if n <= 0 or ra <= 0:
                continue
            blob = d[ra:ra + n]
            i = blob.find(pat)
            while i >= 0:
                ca = ib + va_ + i
                for back in range(3, gap + 1):
                    mv = ca - back
                    om = va2off(secs, ib, mv)
                    if om is None:
                        continue
                    b = d[om:om + 8]
                    if len(b) >= 2 and b[0] == 0x8B and (b[1] >> 6) == 0 and ((b[1] >> 3) & 7) == r \
                            and (b[1] & 7) != 5:
                        rows.append((ca, mv, 'A', r, b[1] & 7))
                        break
                i = blob.find(pat, i + 1)

rows.sort()
print('vt+0x%X 候选虚调用点 %d 个, 其中窗口(0x%X)内含"取引擎"的:' % (disp, len(rows), win))
kept = []
for ca, mv, form, rA, rB in rows:
    h = has_engine_acq(ca - win, ca)
    if h:
        kept.append((ca, mv, form, rA, rB, h))
for ca, mv, form, rA, rB, h in kept:
    print('  ★ %s call@%08X (mov@%08X %s<-[%s])   前窗内: %s'
          % (form, ca, mv, REG[rA], REG[rB], ' | '.join(h)))
if not kept:
    print('  (无)')
