"""按 vtable 槽位枚举虚调用点 —— 解决"函数有地址、但没有静态 E8 调用者"的问题。

原理(字节级):
   MSVC 的虚调用形状是 `mov reg,[obj]` + `mov reg2,[reg+SLOT]` + `call reg2`。
   本工具全库线性反汇编(带 skipdata, 分块避免 OOM), 对每个 `call <寄存器>` 指令
   往回看最多 12 条指令, 找 `mov reg,[reg+SLOT]` 且被调寄存器 == 该 reg,
   并顺带统计窗口内是否出现"对象来源"线索(可通过 --provenance 传立即数或位移)。

用法:
  python -I find_vcall_slot.py 4                      # 找所有 vt+0x04 的虚调用点
  python -I find_vcall_slot.py 0x24 --provenance 0x643300
  python -I find_vcall_slot.py 4 --near 0x1f0         # 只报窗口内出现 [+0x1f0] 的
"""
import sys
import capstone

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

SLOT = int(sys.argv[1], 0) if len(sys.argv) > 1 else 4
prov = None
near = None
for i, a in enumerate(sys.argv):
    if a == '--provenance' and i + 1 < len(sys.argv):
        prov = int(sys.argv[i + 1], 0)
    if a == '--near' and i + 1 < len(sys.argv):
        near = int(sys.argv[i + 1], 0)

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True
SLOT_S = "+ 0x%x]" % SLOT
REGS = ('eax', 'ecx', 'edx', 'ebx', 'esi', 'edi')


def sweep():
    CHUNK, OVER = 1 << 16, 32
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        base = ib + va_
        pos = 0
        while pos < n:
            end = min(pos + CHUNK, n)
            win = []
            try:
                for ins in md.disasm(d[ra + pos: ra + end], base + pos):
                    win.append(ins)
                    if len(win) > 14:
                        win.pop(0)
                    if ins.mnemonic == 'call' and ins.op_str in REGS:
                        yield ins, list(win)
            except Exception:
                pass
            pos = end - OVER if end < n else end


hits = []
for ins, win in sweep():
    called = ins.op_str
    for back in win[:-1][::-1]:
        s = back.op_str.replace(' ', '')
        if back.mnemonic == 'mov' and s.endswith(',' + called) and SLOT_S in s and s.startswith('dwordptr['):
            txt = ' ; '.join('%s %s' % (w.mnemonic, w.op_str) for w in win)
            if prov is not None and ('%08x' % prov) not in ''.join(x.bytes.hex() for x in win):
                break
            if near is not None and ('+0x%x]' % near) not in txt:
                break
            hits.append((ins.address, back.address, txt))
            break

print('slot +0x%x 虚调用点: %d' % (SLOT, len(hits)))
for ca, la, txt in hits:
    print('  call@%08X  slotload@%08X' % (ca, la))
    print('     %s' % txt)
