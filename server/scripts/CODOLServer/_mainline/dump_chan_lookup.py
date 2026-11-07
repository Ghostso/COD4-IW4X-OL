"""验证 room channel push 的解码端。

链路: dwLobbyEventHandler 槽6 (0x7F1060) -> 0x7E7C90(按 key 路由) -> 0x6371F0(房间信道)
0x6371F0 开头 call 0x7E7970(param1, param2) —— 那是"按 key 找信道"。

本脚本 dump:
  0x7E7970  按 key 查信道
  0x7E79C0  被 0x7F10C0(槽7) 调用, 3 参数
  0x7F10C0  槽7
  0x7F1110  槽8
  0x7F0A30  槽17
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
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


TARGETS = [
    ('lookup_by_key 0x7E7970', 0x007E7970, 0x140),
    ('0x7E79C0', 0x007E79C0, 0x160),
    ('slot7 0x7F10C0', 0x007F10C0, 0x90),
    ('slot8 0x7F1110', 0x007F1110, 0x90),
    ('slot4 0x7F1040', 0x007F1040, 0x90),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va, n in TARGETS:
    code = read_at(va, n)
    lines.append('')
    lines.append('=== %s ===' % label)
    if not code:
        lines.append('  (unreadable)')
        continue
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-22s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

txt = '\n'.join(lines)
open(os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.',
                  'chan_lookup.txt'), 'w', encoding='utf-8').write(txt + '\n')
print(txt)
