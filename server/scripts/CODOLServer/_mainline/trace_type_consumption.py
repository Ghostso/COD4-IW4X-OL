"""精确追踪 0x634870 里 type 被消费之后，body 的读取起点。

0x634870 入口(已实测):
    006348AE  call readBits(3)       ; 5 位 == 3
    006348C2  call readData(8)       ; type
    006348D8  mov esi,[eax*4+0x82E1458]   ; 前置拦截表
    006348E7  je 0x63494A            ; 空 -> 跳到跳转表
    0063494A  cmp eax,0x2e
    00634953  jmp [eax*4+0x636f3c]   ; 按 type 分派

★ 关键: readBits/readData 是从**同一个位读流**消费的。
  位读流的位置在 readData(8) 之后已前移到第 13 位。
  所以 handler 拿到的流，游标在 type 之后。

问题: handler 是怎么拿到这个流的？
  0x637000 在 0x637048/0x63705D 自己读过 readBits(3)+readData(8)，
  然后在 0x637121/0x637128 call 0x637000（递归）或
  0x637161/0x6371B9 call 0x634870。

  看 0x637000 的分支:
      type==1 -> Manifold 分支 (0x637076 之后)
      否则    -> 0x63718D 分支

  0x63718D 分支:
      push ...; mov eax,[edx+0x25c8]; call 0x634870
  说明 0x634870 收到的流是**同一个**，游标已在 type 之后。

本脚本: 读 0x634870 的 0x63494A..0x634960 区间，
      确认它分派前有没有重置流位置。
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


md = Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 0x6348A5..0x634960 (type 消费到分派) ===')
code = read_at(0x006348A5, 0xC0)
for ins in md.disasm(code, 0x006348A5):
    print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(),
                                   ins.mnemonic, ins.op_str))
    if ins.address > 0x634960:
        break

print()
print('=== 0x63718D..0x6371C0 (非 Manifold 分支如何调 0x634870) ===')
code = read_at(0x0063718D, 0x60)
for ins in md.disasm(code, 0x0063718D):
    print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(),
                                   ins.mnemonic, ins.op_str))
    if ins.address > 0x6371C0:
        break
