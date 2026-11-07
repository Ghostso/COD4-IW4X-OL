#!/usr/bin/env python3
"""s138_typefields: 反序列化函数(及嵌套一层)的位流原语调序列 + 字段目标偏移。

用法: s138_typefields.py [-dN] <VA>...
     -dN  嵌套层数 (默认 1)

判据(已确证):
  0xB774E0  assertCode(code)          ret 4   [ebp+8]=code，读5位断言
  0xB772E0  readData(dst, nbits)      ret 8   [ebp+8]=&dst, [ebp+0xc]=nbits
  0xB777C0  writeData(src, nbits)     ret 8
  0xB77B10  writeCode(code)           ret 4
  0x4F3DE0  readString(reader, dst)   ret 8   前置 assertCode(0x10)
  0x4F3EB0  readBlob(reader, dst)     ret 8   前置 assertCode(0x13)+(0x08)+u32len
  0xB76AF0  readBlobB(dst, &cap)      ret 8
  0xB761E0  readU32(dst)              ret 4
参数 = 紧邻 call 的最后 retimm/4 个 push 的**逆序**(最后 push = 第 1 参)。
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

PRIMS = {
    0xB774E0: ("assertCode", 4),
    0xB772E0: ("readData", 8),
    0xB777C0: ("writeData", 8),
    0xB77B10: ("writeCode", 4),
    0x4F3DE0: ("readString", 8),
    0x4F3EB0: ("readBlob", 8),
    0xB76AF0: ("readBlobB", 8),
    0xB761E0: ("readU32", 4),
    0xB769A0: ("readU64", 4),
    0xB76A30: ("readStrCap", 8),
    0xB75D40: ("bitlen", 4),
    0x8435D0: ("error", 8),
    0xB75B10: ("strAssign", 8),
}
# 0xB773D0 名字表实测: 1/2/3/8/10/13/15 (见 s138_bitstream.py F_* 常量)
CODENAME = {1: "bool", 2: "u8", 3: "u8d", 8: "u32", 10: "u64", 13: "blob",
            16: "string", 21: "full"}

ESPCALL = 0xC3C20F


def body(va, maxlen=0xC00):
    code = d[va - VA: va - VA + maxlen]
    out = []
    for ins in md.disasm(code, va):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
        if len(out) > 1400:
            break
    return out


def render(va, depth=0, maxdepth=1, indent=0, seen=None):
    if seen is None:
        seen = set()
    if va in seen or depth > maxdepth:
        return
    seen.add(va)
    pad = "  " * indent
    insns = body(va)
    if not insns:
        print("%s== 0x%08X  (no code)" % (pad, va))
        return
    print("%s== 0x%08X" % (pad, va))
    pending = []
    regs = {}      # reg -> 表达式
    ecxval = "?"
    for ins in insns:
        m, o = ins.mnemonic, ins.op_str
        parts = [x.strip() for x in o.split(",")]
        if m == "push":
            pending.append(regs.get(o, o))
            continue
        if m in ("mov", "lea") and len(parts) == 2:
            dst, src = parts
            if dst.startswith("ecx"):
                ecxval = regs.get(src, src)
                if "[" in src:
                    regs.pop("ecx", None)
                else:
                    regs["ecx"] = src
                continue
            if m == "mov" and "[" in src:
                regs.pop(dst, None)      # 载入值，不是地址
                continue
            regs[dst] = src
            continue
        if m in ("add", "sub", "inc", "dec") and len(parts) == 2:
            dst = parts[0]
            if dst in regs:
                try:
                    raw = parts[1]
                    a = int(raw, 16) if "0x" in raw or any(
                        c in "abcdef" for c in raw.lower()) else int(raw, 10)
                except Exception:
                    regs.pop(dst, None)
                else:
                    regs[dst] = "(%s %s %d)" % (regs[dst],
                                                "+" if m in ("add", "inc") else "-",
                                                a)
            continue
        if m == "call":
            tgt = int(o, 16) if o.startswith("0x") else None
            if tgt is None:
                print("%s  0x%08X  %-22s INDIRECT %s" % (pad, ins.address,
                                                         ins.bytes.hex(), o))
                pending, regs, ecxval = [], {}, "?"
                continue
            if tgt in PRIMS:
                name, retimm = PRIMS[tgt]
                n = retimm // 4
                args = list(reversed(pending[-n:] if len(pending) >= n
                                     else pending))
                extra = ""
                if name in ("assertCode", "writeCode") and args:
                    try:
                        c = int(args[0], 0) if not args[0].startswith("0x") \
                            else int(args[0], 16)
                        extra = "  ; code %d = %s" % (c, CODENAME.get(c, "?"))
                    except Exception:
                        pass
                print("%s  0x%08X  %-22s %-10s (%s)   ecx=%s%s" % (
                    pad, ins.address, ins.bytes.hex(), name,
                    ", ".join(args), ecxval, extra))
            elif tgt == ESPCALL:
                print("%s  0x%08X  %-22s __security_check_cookie" % (
                    pad, ins.address, ins.bytes.hex()))
            else:
                print("%s  0x%08X  %-22s call 0x%08X (%s)  ecx=%s" % (
                    pad, ins.address, ins.bytes.hex(), tgt,
                    ", ".join(pending[-6:]), ecxval))
                if depth < maxdepth and tgt != va:
                    render(tgt, depth + 1, maxdepth, indent + 1, seen)
            pending, regs, ecxval = [], {}, "?"
            continue
        if m.startswith("j"):
            print("%s  0x%08X  %-22s %-8s %s" % (pad, ins.address,
                                                 ins.bytes.hex(), m, o))
            continue
    print("%s  (end)" % pad)


if __name__ == "__main__":
    maxdepth = 1
    vas = []
    for a in sys.argv[1:]:
        if a.startswith("-d"):
            maxdepth = int(a[2:])
        else:
            vas.append(int(a, 0))
    for a in vas:
        render(a, 0, maxdepth)
        print()
