"""找房间"准备"按钮的本地处理代码。

已知按钮无反应、且点击后无任何 11/4 上行。
说明点击在本地就被拦下，或根本没绑定处理。

思路:
  1. 房间 UI 的状态串: Active_To_Ready / Active_To_Ready_Alt / Ready_To_Holding
  2. 找引用这些串的代码(UI 状态机), 看它的判定条件
  3. 也找 "Ready" 相关的 UI 动作名

先定位这些字符串被谁引用（绝对地址立即数）。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

STRINGS = {
    0x00DAFC04: 'Active_To_Ready_Alt',
    0x00DAFC18: 'Active_To_Ready',
    0x00DAFC38: 'Ready_To_Holding',
    0x00DAFC4C: 'Ready',
    0x00DBFDCC: 'isroomhost',
    0x00DBFDD8: 'team',
}

regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for addr, name in STRINGS.items():
    needle = struct.pack('<I', addr)
    hits = []
    for base, size, fn, prot in regions:
        if not (prot & 0x20):
            continue
        data = blob(fn)
        if len(data) != size:
            continue
        i = data.find(needle)
        while i >= 0 and len(hits) < 12:
            if (base + i) % 4 == 0:
                hits.append(base + i)
            i = data.find(needle, i + 1)
    lines.append('')
    lines.append('=== %s (0x%08X) 被引用 %d 处 ===' % (name, addr, len(hits)))
    for h in hits[:6]:
        lines.append('  --- 引用点 0x%08X ---' % h)
        code = read_at(h - 0x30, 0x70)
        if not code:
            continue
        for n, ins in enumerate(md.disasm(code, h - 0x30)):
            mark = '  <<<' if ins.address <= h < ins.address + ins.size else ''
            lines.append('    %08X  %-18s %s %s%s'
                         % (ins.address, ins.bytes.hex(), ins.mnemonic,
                            ins.op_str, mark))
            if n > 14:
                break

txt = '\n'.join(lines)
open(os.path.join(OUT, 'ready_button_refs.txt'), 'w', encoding='utf-8').write(txt + '\n')
print(txt[:7000])
