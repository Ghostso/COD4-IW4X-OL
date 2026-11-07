"""反汇编 CA_* 状态表附近，找状态判定逻辑。

引用点: 0x005C8073..0x005C80A9 (CA_CINEMATIC/LOADING/GAMESTATE/PRIMED/ACTIVE)
这些像是 "状态名 -> 索引" 的字符串表，用来显示当前连接状态。
"""
import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

CACHE = {}


def blob(b):
    if b not in CACHE:
        CACHE[b] = open(os.path.join(D, regions[b][1]), 'rb').read()
    return CACHE[b]


def read_at(va, n):
    for base, (size, fn) in regions.items():
        if base <= va < base + size and va + n <= base + size:
            return blob(base)[va - base:va - base + n]
    return None


print('=== 0x005C8040 附近 (CA_* 引用区) 反汇编 ===')
code = read_at(0x005C8040, 128)
if code:
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(code, 0x005C8040):
        line = '  %08X  %-22s %s %s' % (ins.address, ins.bytes.hex(),
                                        ins.mnemonic, ins.op_str)
        # 标注引用的字符串
        try:
            if ins.op_str.startswith('0x'):
                va = int(ins.op_str, 16)
                s = read_at(va, 40)
                if s and all(32 <= c <= 126 or c == 0 for c in s[:20]):
                    txt = s.split(b'\x00')[0].decode('latin1')
                    if txt:
                        line += '   ; "%s"' % txt
        except ValueError:
            pass
        print(line)

print()
print('=== CA_* 引用所在区域是什么 (前后) ===')
d = read_at(0x005C7FC0, 0x120)
if d:
    cur = []
    pos = 0x005C7FC0
    for ch in d:
        if ch == 0:
            if len(cur) >= 4:
                print('  0x%08X  %s' % (pos - len(cur), ''.join(cur)))
            cur = []
        elif 32 <= ch <= 126:
            cur.append(chr(ch))
        else:
            cur = []
        pos += 1
