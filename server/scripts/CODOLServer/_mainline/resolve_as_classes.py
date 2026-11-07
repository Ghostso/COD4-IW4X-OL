"""解出所有 AS_* 类的 vtable，定位 SetReadyState / GetReadyState 的实现。

RTTI 规则（项目已实测）:
    TypeDescriptor @ name_va - 9
    COL.pTD == TD
    搜到 COL 后，vtable 在 COL 的引用处

做法:
  1. 全镜像找 "?AVAS_SetReadyState@@" 等名字
  2. 由名字得 TD，找引用该 TD 的 COL
  3. 由 COL 找 vtable（vtable[-1] == COL）
  4. 反汇编 vtable[0]（一般是 Execute 或 Process）
"""
import json
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
TARGETS = ['AS_SetReadyState', 'AS_GetReadyState', 'AS_IsRoomHost',
           'AS_GetRoomInfo', 'AS_StartMatch', 'AS_VoteMap']

snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
size = os.path.getsize(os.path.join(RUN, snap + '.bin'))
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')
CACHE = {}


def read(va, n):
    off = va - lo
    if off < 0:
        return None
    cov.seek(off)
    if cov.read(n) != b'\x01' * n:
        return None
    f.seek(off)
    d = f.read(n)
    return d if len(d) == n else None


def scan(needle, limit=20):
    hits = []
    pos = 0
    CH = 16 << 20
    while pos < size and len(hits) < limit:
        cov.seek(pos)
        if cov.read(1) != b'\x01':
            pos += CH
            continue
        f.seek(pos)
        data = f.read(min(CH, size - pos))
        if not data:
            break
        i = data.find(needle)
        while i >= 0 and len(hits) < limit:
            hits.append(lo + pos + i)
            i = data.find(needle, i + 1)
        pos += max(1, len(data) - len(needle))
    return hits


md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for t in TARGETS:
    name = ('.?AV' + t + '@@').encode()
    nhits = scan(name, 6)
    lines.append('')
    lines.append('=== %s  名字命中 %d ===' % (t, len(nhits)))
    if not nhits:
        continue
    name_va = nhits[0]
    td_va = name_va - 9
    lines.append('  name @0x%08X  TD @0x%08X' % (name_va, td_va))
    # 找引用 TD 的 COL
    col_hits = scan(struct.pack('<I', td_va), 12)
    lines.append('  引用该 TD 的位置 %d 处: %s'
                 % (len(col_hits), [hex(x) for x in col_hits[:6]]))
    for ch in col_hits:
        col = ch - 0x0C           # COL.pTD 在 +0x0C
        hdr = read(col, 0x10)
        if not hdr:
            continue
        sig, off_, cd, ptd = struct.unpack('<IIII', hdr)
        if ptd != td_va:
            continue
        lines.append('  ★ COL @0x%08X (sig=%d)' % (col, sig))
        # 找引用该 COL 的 vtable
        vt_hits = scan(struct.pack('<I', col), 8)
        for vh in vt_hits:
            vt = vh + 4
            head = read(vt, 0x10)
            if not head:
                continue
            v0, v1, v2, v3 = struct.unpack('<4I', head)
            lines.append('    vtable @0x%08X  slots: %s'
                         % (vt, [hex(x) for x in (v0, v1, v2, v3)]))
            for sv in (v0, v1):
                if 0x00400000 <= sv < 0x01000000:
                    code = read(sv, 0x60)
                    if not code:
                        continue
                    lines.append('      --- slot 0x%08X ---' % sv)
                    for n, ins in enumerate(md.disasm(code, sv)):
                        lines.append('        %08X  %-18s %s %s'
                                     % (ins.address, ins.bytes.hex(),
                                        ins.mnemonic, ins.op_str))
                        if n > 12:
                            break
        break

txt = '\n'.join(lines)
open(os.path.join(OUT, 'as_classes.txt'), 'w', encoding='utf-8').write(txt + '\n')
print(txt[:8000])
cov.close()
f.close()
