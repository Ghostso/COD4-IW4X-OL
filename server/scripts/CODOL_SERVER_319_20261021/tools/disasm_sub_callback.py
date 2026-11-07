# -*- coding: utf-8 -*-
"""看清订阅回调里"成功 vs 失败"到底按什么条件分。

已知:
  0x4AA966  cmp byte [ebp+0xc], 0      <- 入参1 = 是否成功?
  0x4AA97E  je 0x4aa9bd                <- 为 0 跳失败
  0x4AA980  test esi,esi ; jne 0x4aa9bd
  0x4AA984  test edx,edx ; jne 0x4aa9bd
  0x4AA988  成功: 读 [eax+0x10]/[eax+0x14] 写全局

⇒ 失败条件 = (入参1==0) || (0xc1b8020 != 0) || (0xc1b8038 != 0)
   后两个是全局状态 —— 很可能是"上一条请求的错误码/错误计数"。

再把整个函数从头扫一遍, 找它的调用者(谁传的 入参1)。
"""
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def find_callers(b, target_va, limit=10):
    out = []
    i = 0
    while i < len(b) - 5:
        j = b.find(b"\xE8", i)
        if j < 0:
            break
        rel = int.from_bytes(b[j + 1:j + 5], "little", signed=True)
        if (j + 5 + rel + BASE) == target_va:
            out.append(j + BASE)
            if len(out) >= limit:
                break
        i = j + 1
    return out


def main():
    b = DUMP.read_bytes()
    print("== 订阅回调函数 0x4AA960 的调用者 ==")
    for c in find_callers(b, 0x4AA960):
        print("   0x%X" % c)

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    print("\n== 0x4AAA10 起的第二个回调 ==")
    code = b[0x4AAA10 - BASE:0x4AAA10 - BASE + 0x110]
    for ins in md.disasm(code, 0x4AAA10):
        note = ""
        for op in ins.operands:
            try:
                v = op.imm
            except Exception:
                continue
            if 0xD00000 <= v <= 0xF00000:
                so = v - BASE
                chunk = b[so:so + 70].split(b"\x00")[0]
                if chunk and all(32 <= x < 127 for x in chunk):
                    note = '   ; "%s"' % chunk.decode("latin1")
        print("  0x%08X  %-7s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
