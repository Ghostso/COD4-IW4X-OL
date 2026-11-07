"""从若干"取到某对象"的调用点向后反汇编, 列出**所有间接 call/jmp 及其槽位位移**。
   用来回答"谁通过 vtable 调了某个方法"——尤其是那些没有静态 E8 调用者的槽位函数。

用法:
  python -I vcall_after.py 0xBAC600 --len 0x140
  python -I vcall_after.py 0xBAC600 --len 0x140 --want 4      # 只报 +4
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

# 找出所有调用 target 的点
target = int(sys.argv[1], 16)
length = 0x140
want = None
for i, a in enumerate(sys.argv):
    if a == '--len':
        length = int(sys.argv[i + 1], 0)
    if a == '--want':
        want = int(sys.argv[i + 1], 0)

sites = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    blob = d[ra:ra + n]
    i = 0
    while True:
        i = blob.find(b'\xe8', i)
        if i < 0 or i + 5 > len(blob):
            break
        va = ib + va_ + i
        r = int.from_bytes(blob[i + 1:i + 5], 'little', signed=True)
        if (va + 5 + r) & 0xFFFFFFFF == target:
            sites.append(va + 5)
        i += 1

print('从 %d 个调用点后方各反汇编 0x%X 字节\n' % (len(sites), length))
for s in sorted(sites):
    o = va2off(secs, ib, s)
    if o is None:
        continue
    out = []
    try:
        for ins in md.disasm(d[o:o + length], s):
            if ins.mnemonic in ('call', 'jmp') and '[' in ins.op_str:
                out.append('      %08X  %-10s %s' % (ins.address, ins.mnemonic, ins.op_str))
    except Exception:
        pass
    if out:
        print('--- 从 %08X 起 ---' % s)
        for line in out:
            print(line)
        print()
    elif want is None:
        print('--- 从 %08X 起 ---  (无间接调用)' % s)
