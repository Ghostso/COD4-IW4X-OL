"""sockaddr 构造 def-use 追踪（只读）。

对 connect/bind 调用点：从函数真入口线性解码到调用点，
列出所有写栈/写内存的指令 + 所有 push 序列，定位 sockaddr 三字段写入。
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X

TARGETS = [
    (0x00425530, 0x00425802, 'A connect'),
    (0x00650cfe, 0x00650d4e, 'B connect'),
    (0x00431460, None,       'A bind+listen'),
    (0x006747c0, None,       'B bind+listen'),
]


def main():
    img = Image()
    for fstart, callva, tag in TARGETS:
        print('=' * 78)
        print('### %s  func 0x%08x  (到 0x%08x)' % (tag, fstart, callva or fstart + 0x1200))
        print('=' * 78)
        n = (callva - fstart + 1) if callva else 0x1200
        insns = []
        for ins in X.dis(img, fstart, n):
            insns.append(ins)
        if callva:
            insns = [i for i in insns if i.address <= callva]
        print('   指令数 %d' % len(insns))
        print('')
        print('   -- 写内存指令（含栈槽） --')
        for ins in insns:
            op = ins.op_str
            if not op.startswith(('byte ptr [', 'word ptr [', 'dword ptr [', 'qword ptr [')):
                continue
            if '],' not in op.split('ptr')[1]:
                continue
            print('   %08x  %-20s %-12s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, op))
        print('')
        print('   -- ret / call 边界 --')
        for ins in insns:
            if ins.mnemonic in ('ret', 'retn', 'call') and not ins.op_str.startswith('dword ptr [0x10'):
                print('   %08x  %-20s %-12s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        print('')


if __name__ == '__main__':
    main()
