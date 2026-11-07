#!/usr/bin/env python3
"""对每个 dwRoomMessage 类，分别提取 vtable[1](serialize) 与
vtable[2](deserialize) 的 5 位标签序列，逐项比对。

若两侧序列完全相同 ⇒ 坐实"5 位前缀是该字段的固定 ID，deserialize
用 readBitsExpect 断言它"。若不同 ⇒ 该假设被推翻。"""
import re
import subprocess
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD, RB, RD = 0xB77B10, 0xB777C0, 0xB774E0, 0xB772E0
MAXDEPTH = 4

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def body(b, va, maxlen=0x1000):
    o = va - BASE
    if not (0 <= o < len(b) - 16):
        return []
    out = []
    for ins in md.disasm(b[o:o + maxlen], va):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


_wc = {}


def is_writer(b, va, want, depth=0):
    """函数体（含一层递归）内是否有 call want。"""
    key = (va, want)
    if key in _wc:
        return _wc[key]
    _wc[key] = False
    ok = False
    for ins in body(b, va):
        if ins.mnemonic == "call" and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t == want:
                ok = True
                break
            if depth < 1 and is_writer(b, t, want, depth + 1):
                ok = True
                break
    _wc[key] = ok
    return ok


def tag_seq(b, va, tagcall, skipcall, depth=0, stack=None):
    """返回标签序列（只收 tagcall 前的立即数），递归进子函数。
    stack 是当前调用栈（防环），返回时弹出 —— 同一子函数被调用多次要分别计。"""
    if stack is None:
        stack = ()
    if va in stack or depth > MAXDEPTH:
        return []
    stack = stack + (va,)
    ins_list = body(b, va)
    if not ins_list:
        return []
    out = []
    pend = []
    for ins in ins_list:
        m, ops = ins.mnemonic, ins.operands
        if m == "push":
            pend.append(ops[0].imm if ops and ops[0].type == X.X86_OP_IMM
                        else None)
            pend = pend[-8:]
            continue
        if m == "call" and ops and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == tagcall:
                out.append(pend[-1] if pend and pend[-1] is not None
                           else None)
            elif t in (WB, WD, RB, RD, 0xC427F0):
                pass
            elif is_writer(b, t, tagcall):
                out.extend(tag_seq(b, t, tagcall, skipcall, depth + 1, stack))
            pend = []
            continue
    return out


def classes():
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    rows = []
    for line in out.splitlines():
        mm = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                      r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if mm:
            rows.append((mm.group(1), mm.group(4), mm.group(5)))
    return rows


def fmt(seq):
    return " ".join("%02x" % x if x is not None else "??" for x in seq)


def main():
    b = open(DUMP, "rb").read()
    same = diff = zero = 0
    for name, sva, dva in classes():
        s = tag_seq(b, int(sva, 16), WB, WD)
        d = tag_seq(b, int(dva, 16), RB, RD)
        if not s or not d:
            zero += 1
            continue
        if s == d:
            same += 1
            print("[SAME] %-44s %s" % (name, fmt(s)))
        else:
            diff += 1
            print("[DIFF] %-44s" % name)
            print("       ser: %s" % fmt(s))
            print("       der: %s" % fmt(d))
    print("\nSAME=%d DIFF=%d EMPTY=%d" % (same, diff, zero))


if __name__ == "__main__":
    main()
