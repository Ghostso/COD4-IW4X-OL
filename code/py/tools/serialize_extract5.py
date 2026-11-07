#!/usr/bin/env python3
"""位流提取器 v5 —— v4 之上再修一个缺陷：

  D5（v4）递归无门槛 ⇒ 任何 call 都跟进，可能把无关函数算进来。
        判据改为："目标函数体内是否出现 call WB/WD"（即它是位流写入者）。

用法:
  python -I tools/serialize_extract5.py 0x627d80
  python -I tools/serialize_extract5.py --all
"""
import re
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WB, WD = 0xB77B10, 0xB777C0
MAXDEPTH = 4

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = True


def body(b, va, maxlen=0x1000):
    o = va - BASE
    if not (0 <= o < len(b) - 16):
        return []
    out = []
    for ins in _md.disasm(b[o:o + maxlen], va):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


_writer_cache = {}


def is_bitwriter(b, va, depth=0):
    """函数体（含一层递归）内是否有 call WB/WD。"""
    if va in _writer_cache:
        return _writer_cache[va]
    _writer_cache[va] = False   # 防环
    ins_list = body(b, va)
    ok = False
    for ins in ins_list:
        if ins.mnemonic == "call" and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t in (WB, WD):
                ok = True
                break
            if depth < 1 and is_bitwriter(b, t, depth + 1):
                ok = True
                break
    _writer_cache[va] = ok
    return ok


def width_of(pend):
    for p in reversed(pend):
        if p[0] == "imm":
            return p[1]
    return None


def analyze(b, va, depth=0, seen=None):
    if seen is None:
        seen = set()
    empty = {"pre": 0, "loop": 0, "loops": 0, "var": False, "seq": [],
             "var_pre": False, "var_loop": False}
    if va in seen or depth > MAXDEPTH:
        return empty
    seen.add(va)
    ins_list = body(b, va)
    if not ins_list:
        return empty

    ranges = []
    for ins in ins_list:
        if ins.mnemonic.startswith("j") and ins.operands and \
                ins.operands[0].type == X.X86_OP_IMM:
            t = ins.operands[0].imm
            if t <= ins.address and va <= t < ins.address:
                ranges.append((t, ins.address))

    def in_loop(a):
        return any(lo <= a <= hi for lo, hi in ranges)

    pre = loop = 0
    var_pre = var_loop = False
    seq = []
    pend = []
    skipped = []
    for ins in ins_list:
        m, ops = ins.mnemonic, ins.operands
        lp = in_loop(ins.address)
        if m == "push":
            if ops[0].type == X.X86_OP_IMM:
                pend.append(("imm", ops[0].imm))
            elif ops[0].type == X.X86_OP_MEM:
                pend.append(("mem",))
            else:
                pend.append(("reg",))
            pend = pend[-8:]
            continue
        if m == "call" and ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            if t == WB:
                if lp:
                    loop += 5
                else:
                    pre += 5
                tagv = pend[-1][1] if pend and pend[-1][0] == "imm" else None
                seq.append((lp, "bits", 5, ins.address, tagv))
            elif t == WD:
                w = width_of(pend)
                if w is None:
                    if lp:
                        var_loop = True
                    else:
                        var_pre = True
                else:
                    if lp:
                        loop += w
                    else:
                        pre += w
                seq.append((lp, "data", w, ins.address, None))
            elif is_bitwriter(b, t):
                sub = analyze(b, t, depth + 1, seen)
                if sub["seq"]:
                    seq.append((lp, "call " + hex(t), None, ins.address, None))
                    seq.extend([(lp,) + tuple(s[1:]) for s in sub["seq"]])
                    if lp:
                        loop += sub["pre"] + sub["loop"]
                        var_loop = var_loop or sub["var"]
                    else:
                        pre += sub["pre"] + sub["loop"]
                        var_pre = var_pre or sub["var"]
            else:
                skipped.append(hex(t))
            pend = []
            continue

    return {"pre": pre, "loop": loop, "loops": len({r[0] for r in ranges}),            "var": var_pre or var_loop, "seq": seq,
            "var_pre": var_pre, "var_loop": var_loop, "skipped": skipped}


def report(va, d):
    print("===== %#010x =====" % va)
    for lp, kind, w, at, tagv in d["seq"]:
        print("%s %-14s %-6s tag=%-5s @%#x" % (
            "  L" if lp else "   ", kind,
            ("%d" % w) if w is not None else "VAR",
            ("0x%02x" % tagv) if tagv is not None else "-", at))
    print("-- 头/循环外: %d 位 = %.2f 字节%s" % (
        d["pre"], d["pre"] / 8.0, " (含变长)" if d["var_pre"] else ""))
    if d["loops"]:
        print("-- 循环体: %d 位 = %.2f 字节 × N%s" % (
            d["loop"], d["loop"] / 8.0, " (含变长)" if d["var_loop"] else ""))
    if d.get("skipped"):
        print("-- 跳过的非位流 call: %s" % ", ".join(sorted(set(d["skipped"]))))
    print()


def main():
    b = open(DUMP, "rb").read()
    if "--tags" in sys.argv:
        import subprocess
        out = subprocess.run(
            [sys.executable, "-I", "tools/dwroom_serializers.py"],
            capture_output=True, text=True, encoding="latin1").stdout
        rows = []
        for line in out.splitlines():
            mm = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                          r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
            if mm:
                rows.append((mm.group(1), mm.group(4)))
        seen = set()
        for name, va in rows:
            if va in seen:
                continue
            seen.add(va)
            d = analyze(b, int(va, 16))
            if not d["seq"]:
                continue
            parts = []
            for lp, kind, w, at, tagv in d["seq"]:
                if kind != "bits":
                    continue
                parts.append(("L" if lp else "") +
                             ("%02x" % tagv if tagv is not None else "??"))
            print("%-46s %s" % (name, " ".join(parts)))
        return
    if "--all" in sys.argv:
        import subprocess
        out = subprocess.run(
            [sys.executable, "-I", "tools/dwroom_serializers.py"],
            capture_output=True, text=True, encoding="latin1").stdout
        rows = []
        for line in out.splitlines():
            mm = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                          r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
            if mm:
                rows.append((mm.group(1), mm.group(4)))
        seen = set()
        for name, va in rows:
            if va in seen:
                continue
            seen.add(va)
            d = analyze(b, int(va, 16))
            print("%-46s pre=%-5d loop=%-5d x%-2d%s" % (
                name, d["pre"], d["loop"], d["loops"],
                "  VAR" if d["var"] else ""))
        return
    va = int(sys.argv[1], 0)
    report(va, analyze(b, va))


if __name__ == "__main__":
    main()
