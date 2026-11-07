#!/usr/bin/env python3
"""s138_rest: 找出尚未解出的消息类(dwRoomMessageCard/Score/JoinMemberInfos/
   MyPartyInvitation/... ) 的反序列化器, 并打印位流原语序列。
方法: 全镜像搜 "mov [base+X], <该类的 vftable>" 的构造点, 取其前后 ±0x120 的
      函数(向前找 push ebp/mov ebp,esp 序言), 再扫位流原语。
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
    0xB774E0: ("code", 4), 0xB77B10: ("wcode", 4),
    0xB772E0: ("read", 8), 0xB777C0: ("write", 8),
    0x4F3DE0: ("string", 8), 0x4F3EB0: ("blob", 8),
    0xB76AF0: ("blobB", 8), 0xB761E0: ("u32", 4), 0xB769A0: ("u64", 4),
}
CODENAME = {1: "Bool", 2: "Char8", 3: "UChar8", 4: "WChar16", 5: "Int16",
            6: "UInt16", 7: "Int32", 8: "UInt32", 9: "Int64", 10: "UInt64",
            11: "RangedInt32", 12: "RangeUInt32", 13: "Float32", 14: "Float64",
            15: "RangeFloat32", 16: "String", 18: "MultiByteString",
            19: "Blob", 21: "FullType", 22: "Blob", 23: "StructData"}

TARGETS = {
    "dwRoomMessageCard": 0xDC7570,
    "dwRoomMessageScore": 0xDC757C,
    "dwRoomMessageJoinMemberInfos": 0xDC7588,
    "dwRoomMessageMyPartyInvitation": 0xDC75AC,
    "dwRoomMessageSyncPartyPendingToNewMember": 0xDC75C4,
    "dwRoomMessageLeaveWithMe": 0xDC75E8,
    "dwRoomMessageRequestMemberList": 0xDC7600,
    "dwRoomMessageQQMembership": 0xDC76F0,
    "dwRoomMessageNetcafePrivileges": 0xDC76FC,
}

MOV = re.compile(r"\[(\w+)(?: ?([+-]) ?(0x[0-9a-f]+|\d+))?\], (-?0x[0-9a-f]+|-?\d+)")


def num(s):
    s = s.strip()
    return int(s, 16) if "0x" in s.lower() else int(s, 10)


def prologue_of(addr, back=0x400):
    """向前找最近的 'push ebp; mov ebp,esp' 序言"""
    lo = max(0x400000, addr - back)
    last = None
    for ins in md.disasm(d[lo - VA:addr - VA + 8], lo):
        if ins.address <= addr and ins.bytes[:3] == b"\x55\x8b\xec":
            last = ins.address
    return last


def func_body(lo, maxlen=0x300):
    out = []
    for ins in md.disasm(d[lo - VA:lo - VA + maxlen], lo):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
    return out


def scan_prims(lo):
    insns = func_body(lo)
    pending = []
    regs = {}
    res = []
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
            mm = re.match(r"(\w+), (?:dword ptr )?\[(\w+)(?: ([+-]) (0x[0-9a-f]+))?\]$", o)
            if mm:
                r, b, sg, off = mm.groups()
                if off:
                    regs[r] = "%s%+d" % (b, num(off) * (-1 if sg == "-" else 1))
                else:
                    regs[r] = b
            elif "[" not in src:
                regs[dst] = src
            else:
                regs.pop(dst, None)
            continue
        if m != "call":
            continue
        tgt = int(o, 16) if o.startswith("0x") else None
        if tgt in PRIMS:
            name, ri = PRIMS[tgt]
            n = ri // 4
            args = list(reversed(pending[-n:] if len(pending) >= n else pending))
            res.append((ins.address, name, args))
        pending = []
        regs = {}
    return res, insns


for cls, vt in TARGETS.items():
    pat = struct.pack("<I", vt)
    sites = []
    idx = 0
    while True:
        p = d.find(pat, idx)
        if p < 0:
            break
        idx = p + 1
        sites.append(VA + p)
    print("\n" + "=" * 70)
    print("%s  vftable=0x%08X   立即数引用点: %s" % (
        cls, vt, ", ".join("0x%08X" % s for s in sites)))
    for s in sites:
        pro = prologue_of(s)
        print("  -- 构造点 0x%08X, 推测函数起点 0x%08X" % (
            s, pro if pro else 0))
        if not pro:
            continue
        prims, insns = scan_prims(pro)
        for a, name, args in prims:
            extra = ""
            if name in ("code", "wcode") and args:
                try:
                    c = num(args[0])
                    extra = "  ; %s" % CODENAME.get(c, "?")
                except Exception:
                    pass
            print("       0x%08X  %-7s %s%s" % (
                a, name, ", ".join(str(x) for x in args), extra))
