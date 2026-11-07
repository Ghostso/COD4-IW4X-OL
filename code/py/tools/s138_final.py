#!/usr/bin/env python3
"""s138_final: 生成"type -> 处理函数 / 反序列化器 / C++ 类 / 字段位序列"总表。

三级证据链(均可复核):
  L1 0x636F3C 47 项跳转表(type -> handler)           s138_jt47.py
  L2 handler 内 `mov [obj+4], <k> ; mov [obj], <vftable>` 的 k  == type
     (k 即序列化器 0x628320 `mov al,[esi+4]` 写出的 8 位类型号)  s138_ctor_typeid.py
  L3 反序列化器内 位流原语调序列                             s138_fieldsum.py

用法: s138_final.py [--md]
"""
import re
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

PRIMS = {
    0xB774E0: ("code", 4), 0xB77B10: ("wCode", 4),
    0xB772E0: ("read", 8), 0xB777C0: ("write", 8),
    0x4F3DE0: ("string", 8), 0x4F3EB0: ("blob", 8),
    0x4F3D60: ("string60", 8), 0xB76AF0: ("blobB", 8),
    0xB761E0: ("u32", 4), 0xB769A0: ("u64", 4),
}
CODENAME = {1: "Bool", 2: "Char8", 3: "UChar8", 4: "WChar16", 5: "Int16",
            6: "UInt16", 7: "Int32", 8: "UInt32", 9: "Int64", 10: "UInt64",
            11: "RangedInt32", 12: "RangeUInt32", 13: "Float32", 14: "Float64",
            15: "RangeFloat32", 16: "String", 18: "MultiByteString",
            19: "Blob", 21: "FullType", 22: "Blob", 23: "StructData"}

JT = 0x636F3C
CASES = [struct.unpack_from("<I", d, JT - VA + 4 * i)[0] for i in range(0x2F)]
ORDER = sorted(set(CASES))
END = {a: (ORDER[i + 1] if i + 1 < len(ORDER) else 0x636F3C + 0x300)
       for i, a in enumerate(ORDER)}


def cstr(f):
    e = d.find(b"\x00", f)
    return d[f:e].decode("latin1") if e > 0 else None


def name_of(vt):
    try:
        col = struct.unpack_from("<I", d, vt - VA - 4)[0]
        ti = struct.unpack_from("<I", d, col - VA + 0x0C)[0]
        nm = cstr(ti - VA + 8)
        if nm and nm.startswith(".?A"):
            return nm[4:].split("@@")[0]
    except Exception:
        pass
    return None


MOV = re.compile(r"\[(\w+)(?: ?([+-]) ?(0x[0-9a-f]+|\d+))?\], (-?0x[0-9a-f]+|-?\d+)")


def num(s):
    s = s.strip()
    return int(s, 16) if "0x" in s.lower() else int(s, 10)


def scan_movs(lo, hi):
    out = []
    for ins in md.disasm(d[lo - VA:hi - VA], lo):
        if ins.mnemonic == "int3":
            break
        if ins.mnemonic != "mov":
            continue
        m = MOV.search(ins.op_str)
        if not m:
            continue
        b, sg, dh, v = m.groups()
        disp = 0
        if dh:
            disp = num(dh) * (-1 if sg == "-" else 1)
        out.append((ins.address, b, disp, num(v)))
    return out


def ctor_of(h, end):
    """返回 (构造点, 类名, [obj+4] 类型号)"""
    ms = scan_movs(h, end)
    for addr, base, disp, val in ms:
        if not (0xDC7000 <= val < 0xDC7800):
            continue
        nm = name_of(val)
        if not nm or "dwRoomMessage" not in nm:
            continue
        tid = None
        for a2, b2, d2, v2 in ms:
            if b2 == base and d2 == disp + 4 and a2 < addr and addr - a2 < 0x20:
                tid = v2
        return addr, nm, tid, val
    return None, None, None, None


def callees(h, end):
    """顺序反汇编(正确处理 int3 间隙)取 call 目标"""
    out = []
    for ins in md.disasm(d[h - VA:end - VA], h):
        if ins.mnemonic == "int3":
            break
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if 0x400000 <= t < 0xD00000:
                out.append(t)
    return out


def prims_of(lo, maxlen=0x600):
    seq = []
    pending, regs = [], {}
    for ins in md.disasm(d[lo - VA:lo - VA + maxlen], lo):
        m, o = ins.mnemonic, ins.op_str
        parts = [x.strip() for x in o.split(",")]
        if m == "push":
            pending.append(regs.get(o, o))
            continue
        if m in ("mov", "lea") and len(parts) == 2:
            dst, src = parts
            mm = re.match(
                r"(\w+), (?:dword ptr )?\[(\w+)(?: ([+-]) (0x[0-9a-f]+))?\]$", o)
            if mm:
                r, b, sg, off = mm.groups()
                regs[r] = "%s%+#x" % (b, num(off) * (-1 if sg == "-" else 1)) \
                    if off else b
            elif re.match(r"\w+, \w+(?: [*+-] \w+)?$", o) and "[" not in src:
                regs[dst] = src
            else:
                regs.pop(dst, None)      # 含 [ebp + ebx + 12] 等复合寻址
            continue
        if m in ("add", "sub") and len(parts) == 2 and parts[0] in regs:
            try:
                a = num(re.sub(r"^(byte|word|dword) ptr ", "", parts[1]))
            except ValueError:
                continue
            regs[parts[0]] = "(%s %s %#x)" % (regs[parts[0]],
                                              "+" if m == "add" else "-", a)
            continue
        if m != "call":
            if m.startswith("ret"):
                break
            continue
        tgt = int(o, 16) if o.startswith("0x") else None
        if tgt in PRIMS:
            name, ri = PRIMS[tgt]
            n = ri // 4
            args = list(reversed(pending[-n:] if len(pending) >= n else pending))
            seq.append((ins.address, name, args))
            if name == "code":
                continue
        elif tgt is not None:
            seq.append((ins.address, "call", ["0x%08X" % tgt]))
        pending, regs = [], {}
        if m.startswith("ret"):
            break
    return seq


def fmt_prims(seq):
    out = []
    for addr, name, args in seq:
        if name == "code":
            try:
                c = num(args[0])
                out.append("code%d(%s)" % (c, CODENAME.get(c, "?")))
            except Exception:
                out.append("code(%s)" % args)
        elif name in ("read", "write"):
            # args = [dst, nbits] (最后 push 的是第 1 参)
            out.append("%s@%s/%d" % (name, args[0], num(args[1])))
        elif name == "string":
            out.append("String->%s" % (args[1] if len(args) > 1 else args))
        elif name in ("blob", "blobB"):
            out.append("Blob->%s" % (args[1] if len(args) > 1 else args))
        elif name == "call":
            out.append("call%s" % args[0])
        else:
            out.append("%s(%s)" % (name, ",".join(args)))
    return out


def main():
    as_md = "--md" in sys.argv
    if as_md:
        print("| type | 处理函数 | 类名 | 反序列化器 | 字段序列 |")
        print("|------|----------|------|-----------|----------|")
    else:
        print("type  handler    class                                        deser      fields")
        print("-" * 130)
    for t in range(0x2F):
        h = CASES[t]
        end = END[h]
        addr, nm, tid, vt = ctor_of(h, end)
        if nm is None:
            # 尝试直接 callee
            for c in callees(h, end):
                addr, nm, tid, vt = ctor_of(c, c + 0x180)
                if nm:
                    break
        deser = None
        if nm is not None:
            # 反序列化器 = handler 区间内、构造点之前、且自身含位流原语的 call
            best = None
            for c in callees(h, end):
                if c >= addr or not (0x625000 <= c < 0x62A000):
                    continue
                if any(nm2 in ("code", "read", "string", "blob")
                       for _, nm2, _ in prims_of(c)[:3]):
                    best = c
            deser = best
        fields = ""
        if deser:
            seq = prims_of(deser)
            fields = "; ".join(fmt_prims(seq))
        if as_md:
            print("| 0x%02X | 0x%08X | %s | %s | %s |" % (
                t, h, nm or "-",
                ("0x%08X" % deser) if deser else "-", fields or "(无位流原语)"))
        else:
            print("0x%02X  0x%08X  %-44s %-10s %s" % (
                t, h, nm or "(无内联构造)",
                ("0x%08X" % deser) if deser else "-", fields))


main()
