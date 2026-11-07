#!/usr/bin/env python3
"""s138_fieldsum: 对每个 dwRoomMessage 类型, 输出一串"字段序列"摘要。

规则:
  位流原语(已确证):
    0xB774E0 assertCode(code)      ret 4   [ebp+8]=code
    0xB772E0 readData(&dst,nbits)  ret 8   [ebp+8]=&dst, [ebp+0xc]=nbits
    0xB777C0 writeData(src,nbits)  ret 8
    0xB77B10 writeCode(code)       ret 4
    0x4F3DE0 readString(rd,&dst)   ret 8   = code(0x10) + 8位长 + 字符
    0x4F3EB0 readBlob(rd,&dst)     ret 8   = code(0x13)+code(8)+u32len+data
  参数 = 紧邻 call 的最后 retimm/4 个 push 的逆序。
  对 `lea reg,[ebp-X]` 形式的栈槽, 再跟踪 `mov [edi+D],reg` 得到目标字段偏移。

用法: s138_fieldsum.py [type...]   默认全部
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
    0xB774E0: ("code", 4),
    0xB77B10: ("code", 4),
    0xB772E0: ("read", 8),
    0xB777C0: ("write", 8),
    0x4F3DE0: ("string", 8),
    0x4F3EB0: ("blob", 8),
    0xB76AF0: ("blobB", 8),
    0xB761E0: ("u32", 4),
    0xB769A0: ("u64", 4),
}
CODENAME = {1: "Bool", 2: "Char8", 3: "UChar8", 4: "WChar16", 5: "Int16",
            6: "UInt16", 7: "Int32", 8: "UInt32", 9: "Int64", 10: "UInt64",
            11: "RangedInt32", 12: "RangeUInt32", 13: "Float32",
            14: "Float64", 15: "RangeFloat32", 16: "String",
            18: "MultiByteString", 19: "Blob", 21: "FullType",
            22: "Blob", 23: "StructData"}

JT = 0x636F3C
CASES = [struct.unpack_from("<I", d, JT - VA + 4 * i)[0] for i in range(0x2F)]

# type -> (handler_end, deserializer, deser_end)
DESER = {
    0x02: (0x625940, 0x625A20, 0x625AAC), 0x04: (0x625DB0, 0x625DB0, 0x625E1A),
    0x05: (0x626B30, 0x626B30, 0x626BFE), 0x06: (0x627230, 0x627230, 0x6273A0),
    0x07: (0x627B40, 0x627B40, 0x627B79), 0x08: (0x627CE0, 0x627CE0, 0x627CFC),
    0x09: (0x627B40, 0x627B40, 0x627B79), 0x0A: (0x626130, 0x626130, 0x6261B6),
    0x0C: (0x625F50, 0x625F50, 0x6260A0), 0x0E: (0x627E00, 0x627E00, 0x627EA0),
    0x0F: (0x627EE0, 0x627EE0, 0x627F35), 0x10: (0x629090, 0x629090, 0x62910A),
    0x11: (0x625DB0, 0x625DB0, 0x625E1A), 0x12: (0x628B90, 0x628B90, 0x629020),
    0x13: (0x6280B0, 0x6280B0, 0x6281A0), 0x14: (0x628260, 0x628260, 0x628318),
    0x15: (0x625DB0, 0x625DB0, 0x625E1A), 0x16: (0x6284E0, 0x6284E0, 0x6285A5),
    0x17: (0x628610, 0x628610, 0x6286A0), 0x18: (0x6268A0, 0x6268A0, 0x626950),
    0x1A: (0x625DB0, 0x625DB0, 0x625E1A), 0x1B: (0x6283C0, 0x6283C0, 0x628422),
    0x1C: (0x626730, 0x626730, 0x626805), 0x1D: (0x6263C0, 0x6263C0, 0x626648),
    0x1E: (0x625DB0, 0x625DB0, 0x625E1A), 0x1F: (0x627CE0, 0x627CE0, 0x627CFC),    0x20: (0x629020, 0x629020, 0x62908A), 0x21: (0x629090, 0x629090, 0x62910A),
    0x22: (0x6291B0, 0x6291B0, 0x629265), 0x23: (0x625DB0, 0x625DB0, 0x625E1A),
    0x24: (0x625DB0, 0x625DB0, 0x625E1A), 0x25: (0x6269E0, 0x6269E0, 0x626A7E),
    0x26: (0x628740, 0x628740, 0x6287CE), 0x27: (0x629090, 0x629090, 0x62910A),
    0x2B: (0x627C30, 0x627C30, 0x627CC9), 0x2C: (0x625AB0, 0x625AB0, 0x625B24),
    0x2D: (0x629090, 0x629090, 0x62910A), 0x2E: (0x629090, 0x629090, 0x62910A),
    # 共享 0x4F3DE0 readString 的简化变体(0x4F3D60: code0x10 + 8位长度 + 字符)
    0x08: (0x627CE0, 0x627CE0, 0x627CFC),
    0x26: (0x628740, 0x628740, 0x6287CE),
}
# 0x4F3D60 也是一个 string 原语(readString 的简化版), 补进 PRIMS
PRIMS[0x4F3D60] = ("string", 8)

MOVA = re.compile(r"(\w+), (?:dword ptr )?\[(ebp|esi|edi|ebx)(?: ([+-]) (0x[0-9a-f]+))?\]$")
MOVB = re.compile(r"(?:dword ptr |byte ptr )?\[(\w+)(?: ([+-]) (0x[0-9a-f]+))?\], (\w+)$")


def num(s):
    s = s.strip()
    if not re.match(r"^-?(0x[0-9a-fA-F]+|[0-9]+)$", s):
        raise ValueError(s)
    return int(s, 16) if "0x" in s.lower() else int(s, 10)


def func_insns(lo, hi):
    out = []
    for ins in md.disasm(d[lo - VA:hi - VA], lo):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


def summarize(lo, hi, label):
    insns = func_insns(lo, hi)
    pending = []
    regs = {}
    base_of = {}
    seq = []
    for ins in insns:
        m, o = ins.mnemonic, ins.op_str
        parts = [x.strip() for x in o.split(",")]
        if m == "push":
            pending.append(regs.get(o, o))
            continue
        if m in ("mov", "lea") and len(parts) == 2:
            dst, src = parts
            if dst.startswith("ecx"):
                regs.pop("ecx", None)
                continue
            mm = MOVA.match(o)
            if mm and "[" in src:
                r, b, sg, off = mm.groups()
                off = num(off) * (-1 if sg == "-" else 1) if off else 0
                regs[r] = "%s%+#x" % (b, off)
            elif "[" not in src:
                regs[dst] = src
            else:
                regs.pop(dst, None)
            continue
        if m in ("add", "sub") and len(parts) == 2 and parts[0] in regs:
            try:
                a = num(re.sub(r"^(byte|word|dword) ptr ", "", parts[1]))
            except ValueError:
                continue
            regs[parts[0]] = "(%s %s %#x)" % (regs[parts[0]],
                                              "+" if m == "add" else "-", a)
            continue
        if m == "inc" and parts[0] in regs:
            regs[parts[0]] = "(%s + 1)" % regs[parts[0]]
            continue
        if m == "dec" and parts[0] in regs:
            regs[parts[0]] = "(%s - 1)" % regs[parts[0]]
            continue
        if m != "call":
            continue
        tgt = int(o, 16) if o.startswith("0x") else None
        if tgt in PRIMS:
            name, ri = PRIMS[tgt]
            n = ri // 4
            args = list(reversed(pending[-n:] if len(pending) >= n else pending))
            if name == "code":
                c = None
                try:
                    c = num(args[0])
                except Exception:
                    pass
                seq.append(("code", c, ins.address))
            else:
                seq.append((name, args, ins.address))
        pending = []
        regs = {}
    return seq


def render(t):
    if t not in DESER:
        return
    de, lo, hi = DESER[t]
    seq = summarize(lo, hi, "deser")
    print("\n== type 0x%02X  deser 0x%08X" % (t, de))
    for name, val, addr in seq:
        if name == "code":
            print("   0x%08X  code %-3s %s" % (
                addr, val if val is not None else "?",
                CODENAME.get(val, "?")))
        else:
            print("   0x%08X  %-7s %s" % (addr, name, ", ".join(val)))


if __name__ == "__main__":
    targets = [int(a, 0) for a in sys.argv[1:]] or sorted(DESER)
    for t in targets:
        render(t)
