"""列出 dwLobbyEventHandler vtable 全部槽位, 并粗解每个槽的函数体特征。

vtable 起点 = 0x00DE07A4 (COL=0x00E081F8 -> ?AVdwLobbyEventHandler@@)
0x7F1060 在 index 6 (0xDE07BC)。

对每个非平凡槽, 打印前若干条指令, 便于识别"哪个槽处理房间 push"。
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
VT = 0x00DE07A4
N = 60

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


raw = read_at(VT, N * 4)
md = Cs(CS_ARCH_X86, CS_MODE_32)

out = []
for i in range(N):
    v = struct.unpack_from('<I', raw, i * 4)[0]
    if not (0x00400000 <= v < 0x01000000):
        out.append('[%2d] 0x%08X = 0x%08X  (非代码, 表尾?)' % (i, VT + i * 4, v))
        continue
    out.append('[%2d] 0x%08X = 0x%08X' % (i, VT + i * 4, v))
    code = read_at(v, 0x40)
    if code:
        for n, ins in enumerate(md.disasm(code, v)):
            if n > 7:
                break
            out.append('        %08X  %-18s %s %s'
                       % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

txt = '\n'.join(out)
open(os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.',
                  'lobby_event_handler_vtable.txt'), 'w', encoding='utf-8').write(txt + '\n')
print(txt[:6000])
