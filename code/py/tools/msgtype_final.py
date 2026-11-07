#!/usr/bin/env python3
"""全镜像扫描：所有 "mov dword [reg], imm32" 且 imm32 落在 dwRoom 位流类
vtable 段（0xdc7400..0xdc8000）；再在附近找 [reg+4] 的类型号。

不依赖 dwroom_serializers.py 的 50 个类，而是**发现**全部构造函数。
"""
import struct
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def main():
    b = open(DUMP, "rb").read()
    size = len(b)
    # 全镜像，跳过数据段有明显风险，但 capstone 逐条解码即可
    md.skipdata = True
    ins_all = []
    CHUNK = 0x400000
    for start in range(0x400000, 0x400000 + size, CHUNK):
        lo = start - BASE
        if lo < 0:
            continue
        hi = min(lo + CHUNK, size)
        if hi <= lo:
            break
        try:
            for ins in md.disasm(b[lo:hi], start):
                ins_all.append(ins)
        except Exception:
            pass
    print("解码 %d 条指令" % len(ins_all))

    vf_writes = []
    typ_writes = []
    for ins in ins_all:
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if dst.type != X.X86_OP_MEM or src.type != X.X86_OP_IMM:
            continue
        rg = md.reg_name(dst.mem.base)
        if (dst.mem.disp == 0 and dst.size == 4 and
                0xdc7400 <= src.imm < 0xdc8000):
            vf_writes.append((ins.address, rg, src.imm))
        elif dst.mem.disp == 4 and dst.size in (1, 4):
            typ_writes.append((ins.address, rg, src.imm, dst.size))
    print("dwRoom 位流类 vfptr 装填点 %d 处" % len(vf_writes))
    for a, rg, v in vf_writes:
        print("  %#010x  [%s] = %#x" % (a, rg, v))

    # 每个装填点附近找 [reg+4]=imm（就近）
    print("\n=== 构造函数 -> 类型号 ===")
    out = []
    for a, rg, vf in vf_writes:
        best = None
        for ta, trg, timm, tsz in typ_writes:
            if trg != rg or abs(ta - a) > 0x80:
                continue
            if best is None or abs(ta - a) < abs(best[0] - a):
                best = (ta, timm, tsz)
        out.append((vf, best, a))
        print("  vfptr=%#x @%#x  type=%s" % (
            vf, a, ("%d(%dB)@%#x" % (best[1], best[2], best[0]))
            if best else "?"))

    # 与 dwroom_serializers 的 COL 对应
    import re
    import subprocess
    r = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    vf2name = {}
    for line in r.splitlines():
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                     r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if m:
            vf2name[int(m.group(2), 16) + 4] = m.group(1)

    print("\n=== 最终表 ===")
    rows = []
    for vf, typ, a in out:
        name = vf2name.get(vf, "?<vfptr %#x>" % vf)
        rows.append((name, typ[1] if typ else None, vf, a))
    rows.sort(key=lambda x: (x[1] if x[1] is not None else 999))
    for name, t, vf, a in rows:
        print("%-46s type=%-5s vfptr=%#x ctor=%#x" % (
            name, t if t is not None else "?", vf, a))
    with open("_byte_papers/msgtype_final.txt", "w", encoding="utf-8") as f:
        for name, t, vf, a in rows:
            f.write("%s\t%s\t%#x\t%#x\n" % (name, t, vf, a))


if __name__ == "__main__":
    main()
