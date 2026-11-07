"""精确反汇编辅助：capstone 驱动，自动标注 .idata2 导入槽。

用法：
    python scripts/disasm.py <start_rva_hex> <end_rva_hex> [--dll]
"""
import struct
import sys
import re

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe import Image

import capstone

img = Image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

# ---- .idata2 导入槽：RVA -> 名字 ----
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import importmap

SLOTS = importmap.build(img)


def annotate_slot(rva):
    if rva in SLOTS:
        return SLOTS[rva]
    return None


def dis(start, end, show_bytes=True):
    """反汇编 RVA 区间 [start, end)。自动解引用 .idata2 槽。"""
    data = img.read(start, end - start)
    if data is None:
        print('  !! 区间不在文件里（虚拟空洞）: 0x%08x-0x%08x' % (start, end))
        return
    va0 = 0x10000000 + start
    for ins in md.disasm(data, va0):
        rva = ins.address - 0x10000000
        note = ''
        # call/jmp dword ptr [abs]
        if ins.mnemonic in ('call', 'jmp') and ins.operands and \
                ins.operands[0].type == capstone.x86.X86_OP_MEM and \
                ins.operands[0].mem.base == 0 and ins.operands[0].mem.index == 0:
            tgt_va = ins.operands[0].mem.disp
            tgt_rva = tgt_va - 0x10000000
            nm = annotate_slot(tgt_rva)
            if nm:
                note = '   ; >>> IMPORT %s  [slot 0x%06x]' % (nm, tgt_rva)
            else:
                note = '   ; [abs 0x%08x]' % tgt_va
        # 直接相对 call/jmp
        elif ins.mnemonic in ('call', 'jmp') and ins.operands and \
                ins.operands[0].type == capstone.x86.X86_OP_IMM:
            t = ins.operands[0].imm - 0x10000000
            note = '   ; -> 0x%08x' % t
        else:
            # 检查操作数里的绝对地址（push imm32 / mov reg,imm32）
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_IMM and op.imm >= 0x10000000:
                    t = op.imm
                    rv = t - 0x10000000
                    nm = annotate_slot(rv)
                    if nm:
                        note = '   ; >>> IMPORT %s' % nm
                    else:
                        s = img.cstr(rv, 80)
                        if s:
                            note = '   ; "%s"  @0x%08x' % (s, rv)
                        else:
                            note = '   ; abs 0x%08x' % t
        if show_bytes:
            bs = ' '.join('%02x' % b for b in ins.bytes)
            print('  0x%08x  %-24s %-8s %s%s' % (rva, bs[:24], ins.mnemonic, ins.op_str, note))
        else:
            print('  0x%08x  %-8s %s%s' % (rva, ins.mnemonic, ins.op_str, note))


def refs_to(rva, width=4):
    """全文件搜索指向给定 RVA(VA=base+rva) 的 dword 引用。"""
    pat = struct.pack('<I', 0x10000000 + rva)
    out = []
    i = img.data.find(pat)
    while i >= 0:
        v = img.voff(i)
        if v is not None:
            out.append(v)
        i = img.data.find(pat, i + 1)
    return out


if __name__ == '__main__':
    a = int(sys.argv[1], 16)
    b = int(sys.argv[2], 16)
    dis(a, b)
