"""完整反汇编 type 0x02 的 handler (0x63495A)，并追它调用的关键函数。

0x63495A 已知片段:
    lea edx,[ebx+0x10798] ; call 0x4a3af0   ; 查找
    call 0x625940                          ; 读某个消息体
    cmp [0x76446b0], 0xa                   ; 某个全局状态 == 10 ?
    call 0x62bbf0 / 0x62bad0               ; 两种分支
    mov edx,[edi+0x18] ; call edx          ; 虚函数分发

要弄清:
  - 0x4a3af0 是什么(查找/匹配)
  - 0x625940 是什么(读消息?)
  - [0x76446b0] 是什么状态
  - [edi+0x18] 分发到的对象是什么类型
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

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
    ('type02 handler 0x63495A', 0x0063495A, 0x180),
    ('0x4a3af0 lookup', 0x004A3AF0, 0x100),
    ('0x625940 reader', 0x00625940, 0x120),
    ('0x62bbf0', 0x0062BBF0, 0x100),
    ('0x62bad0', 0x0062BAD0, 0x100),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = []
for label, va, n in TARGETS:
    code = read_at(va, n)
    lines.append('')
    lines.append('=' * 66)
    lines.append('%s @ 0x%08X' % (label, va))
    lines.append('=' * 66)
    if not code:
        lines.append('  (unreadable)')
        continue
    c = 0
    for ins in md.disasm(code, va):
        lines.append('  %08X  %-20s %s %s'
                     % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        c += 1
        if ins.mnemonic == 'ret' or c > 48:
            break

txt = '\n'.join(lines)
p = os.path.join(OUT, 'type02_full.txt')
open(p, 'w', encoding='utf-8').write(txt + '\n')
print(txt)
