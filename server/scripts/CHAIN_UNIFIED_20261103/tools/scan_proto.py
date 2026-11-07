"""在闭包清单里筛"仍有协议语义"的函数。

判据（命中任一即列出）：
  A. 调用了记录序列化/解析器：0xBC2540 0xBC25F0 0xBC0570 0xBC0FC0 0xBC0E60
                              0xBC0CB0 0xBC0750 0xBBFE30 0xBBFFE0 0xBC2820 0xBC2C60
  B. 访问了会话状态偏移：+0x4d4 / +0x502 / +0x504 / +0x448 / +0x50c / +0x510 / +0x5c4
  C. 访问了引擎表：+0x170 / +0x268 / +0x40 / +0x148 / +0x188
  D. 调用了协议门控：0xBBDE10 0xBBE110 0xBB3270 0xBB9C00 0xBB9F70 0xBB9EF0 0xBB9D40

用法: python -I scan_proto.py <closure.txt>
"""
import sys, re, struct, bisect
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

PROTO_CALLS = {0xBC2540, 0xBC25F0, 0xBC0570, 0xBC0FC0, 0xBC0E60, 0xBC0CB0, 0xBC0750,
               0xBBFE30, 0xBBFFE0, 0xBC2820, 0xBC2C60,
               0xBBDE10, 0xBBE110, 0xBB3270, 0xBB9C00, 0xBB9F70, 0xBB9EF0, 0xBB9D40,
               0xBBF940, 0xBBF040, 0xBBEA60, 0xBBE5C0, 0xBBE6E0, 0xBBE820, 0xBBE2B0}
STATE_OFF = [0x4d4, 0x502, 0x504, 0x448, 0x50c, 0x510, 0x5c4, 0x5c8, 0x4d0, 0x514]
TABLE_OFF = [0x170, 0x268, 0x148, 0x188, 0x40, 0x34, 0x60]


def in_exec(va):
    for va0, vs, ra, rs in secs:
        if ib + va0 <= va < ib + va0 + max(vs, rs):
            return True
    return False


def rd(va, n):
    o = va2off(secs, ib, va)
    if o is None or o < 0 or o + n > len(d):
        return None
    return d[o:o + n]


# 入口表
entries = set()
for va0, vs, ra, rs in secs:
    size = min(max(vs, rs), len(d) - ra)
    if size <= 0:
        continue
    blob = d[ra:ra + size]
    base = ib + va0
    i = blob.find(b'\xe8')
    while i >= 0:
        if i + 5 <= len(blob):
            rel = struct.unpack_from('<i', blob, i + 1)[0]
            t = (base + i + 5 + rel) & 0xFFFFFFFF
            if in_exec(t):
                entries.add(t)
        i = blob.find(b'\xe8', i + 1)
    j = blob.find(b'\x55\x8b\xec\x6a\xff\x68')
    while j >= 0:
        entries.add(base + j)
        j = blob.find(b'\x55\x8b\xec\x6a\xff\x68', j + 1)
ENT = sorted(entries)


def size_of(va):
    k = bisect.bisect_right(ENT, va)
    return (ENT[k] - va) if k < len(ENT) else 0x400


md = Cs(CS_ARCH_X86, CS_MODE_32)

closure = []
for ln in open(sys.argv[1], encoding='utf-8', errors='ignore'):
    m = re.search(r'0x([0-9A-Fa-f]{8})', ln)
    if m:
        closure.append(int(m.group(1), 16))
closure = sorted(set(closure))

hits = []
for f in closure:
    sz = min(size_of(f) or 0x400, 0x2000)
    code = rd(f, sz)
    if not code:
        continue
    reasons = []
    state_hit = set()
    table_hit = set()
    for ins in md.disasm(code, f):
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
            t = int(ins.op_str, 16)
            if t in PROTO_CALLS:
                reasons.append('call 0x%08X' % t)
        m2 = re.search(r'\[[a-z0-9]+ \+ (0x[0-9a-f]+)\]', ins.op_str)
        if m2:
            off = int(m2.group(1), 16)
            if off in STATE_OFF:
                state_hit.add(off)
            if off in TABLE_OFF:
                table_hit.add(off)
    if state_hit:
        reasons.append('STATE' + ','.join('+0x%X' % o for o in sorted(state_hit)))
    if table_hit:
        reasons.append('TABLE' + ','.join('+0x%X' % o for o in sorted(table_hit)))
    if reasons:
        hits.append((f, sz, reasons))

print('闭包 %d 个函数；命中"仍有协议语义"判据的 %d 个\n' % (len(closure), len(hits)))
for f, sz, rs in hits:
    print('  0x%08X  size=%-5d  %s' % (f, sz, ' | '.join(rs[:6])))
