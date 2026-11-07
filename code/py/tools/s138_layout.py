#!/usr/bin/env python3
"""138: 从写函数入口到首条 ret，抽取位流字段布局。
规则(已静态验证):
  call 0xB77B10 -> 写 5 位"字段标记"(marker): 标记值 = call 前最近一次 push imm
  call 0xB777C0 -> 写 width 位: 调用前两次 push, 第一次=width(imm 或 寄存器), 第二次=值来源(lea reg,[base+disp] / push reg / push [mem])
  头部: b77b10(3) = 5 位常量3, 然后 b777c0(ptr,8) = 8 位类型号
用法: s138_layout.py <VA>
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dis(va, maxlen=0x600):
    code = d[va - VA:va - VA + maxlen]
    out = []
    for ins in md.disasm(code, va):
        out.append(ins)
        if ins.mnemonic == "ret" or ins.mnemonic.startswith("ret "):
            break
        if ins.mnemonic == "ret" or ins.mnemonic == "retn":
            break
    # filter to first ret inclusive
    res = []
    for ins in out:
        res.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return res


def num(p):
    p = p.strip()
    try:
        if p.startswith("0x"):
            return int(p, 16)
        if p.isdigit():
            return int(p, 10)
    except ValueError:
        return None
    return None


def run(entry):
    ins = dis(entry)
    # track last 3 pushes
    pushes = []
    last_marker = None
    print("== serializer 0x%08X ==" % entry)
    i = 0
    rows = []
    for x in ins:
        if x.mnemonic == "push":
            pushes.append((x.address, x.op_str))
            if len(pushes) > 4:
                pushes.pop(0)
        elif x.mnemonic == "call":
            t = x.op_str.strip()
            if t == "0xb77b10":
                # marker = last push imm
                mk = None
                if pushes:
                    mk = num(pushes[-1][1])
                last_marker = mk
                rows.append(("MARKER", mk, None, x.address))
                pushes = []
            elif t == "0xb777c0":
                width = None
                src = None
                if len(pushes) >= 2:
                    w0 = pushes[-2][1]
                    mm = re.match(r"^0x([0-9a-f]+)$", w0)
                    width = int(mm.group(1), 16) if mm else w0
                    src = pushes[-1][1]
                elif len(pushes) == 1:
                    src = pushes[-1][1]
                rows.append(("VALUE", last_marker, (width, src), x.address))
                last_marker = None
                pushes = []
            elif t in ("0xb774e0", "0xb772e0"):
                rows.append(("READ", None, (t, pushes[-1][1] if pushes else None), x.address))
                pushes = []
            else:
                pushes = []
        elif x.mnemonic in ("mov", "lea", "add", "test", "cmp", "je", "jne", "jmp"):
            # keep pushes; they may be args to non-bits calls? reset on other call only
            pass
        else:
            pass
    # print
    n = 0
    for kind, mk, val, addr in rows:
        if kind == "MARKER":
            pass
        elif kind == "VALUE":
            n += 1
            w, src = val
            print("  #%-2d 0x%08X marker=%-5s width=%-5s src=%s" % (
                n, addr, ("0x%02X" % mk) if mk is not None else "?", w, src))
    return rows


if __name__ == "__main__":
    for a in sys.argv[1:]:
        run(int(a, 0))
        print()
