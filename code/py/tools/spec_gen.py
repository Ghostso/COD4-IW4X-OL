#!/usr/bin/env python3
"""从 serialize_extract6 的逆向结果自动生成 spec 表（不再手工抄写）。

循环体默认 N=1（可 --loops N 指定）。
变长串用占位 "str"，变长 blob 用 ("blob", 0)。

用法:
  python -I tools/spec_gen.py            # 打印 Python dict
  python -I tools/spec_gen.py --write    # 写入 _byte_papers/msg_spec.py
"""
import re
import subprocess
import sys

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402

SKIP = {"dwRoomMatch", "dwRoomMatchUber", "dwRoom", "dwRoomImp",
        "dwRoomDMZLeagueCallbackHandler", "dwRoomEventTournamentHandler"}


def short(name):
    return re.sub(r"^dwRoomMessage|^dwRoomSpy", "", name) or name


def main():
    b = open(E.DUMP, "rb").read()
    rows = E.rows_from_vtable()
    # vtable 表还缺 P2PInfo，补上（元组形状 = (name, serialize, deserialize)）
    rows.append(("dwRoomMessageP2PInfo", "0x627fc0", "0x6280b0"))

    out = {}
    cache = {}      # serialize VA -> spec（多个类可共用同一 spec）
    for name, ser, _der in rows:
        if name in SKIP:
            continue
        va = int(ser, 16)
        if va in cache:
            out[short(name)] = cache[va]
            continue
        seq, loops = E.analyze(b, va, E.WB, E.WD)
        if not seq:
            continue
        spec = []
        # 循环区间
        ranges = []
        ins = E.func_insns(b, va)
        for i in ins:
            if i.mnemonic.startswith("j") and i.operands and \
                    i.operands[0].type == E.X.X86_OP_IMM:
                t = i.operands[0].imm
                if t <= i.address and va <= t:
                    ranges.append((t, i.address))

        def in_loop(a):
            return any(lo <= a <= hi for lo, hi in ranges)

        i = 0
        n = len(seq)
        while i < n:
            lp, kind, w, at, v = seq[i]
            if kind == "call":
                i += 1
                continue
            if kind != "tag":
                i += 1
                continue
            # blob 形态：tag 0x13, tag 0x08, data 32, data N
            if v == 0x13 and i + 3 < n:
                k2 = seq[i + 1]
                k3 = seq[i + 2]
                k4 = seq[i + 3]
                if (k2[1] == "tag" and k2[4] == 0x08 and
                        k3[1] == "data" and k3[2] == 32):
                    if k4[1] == "data":
                        spec.append((0x13, ("blob", (k4[2] or 0) // 8)))
                        i += 4
                        continue
            # 串：tag + data(VAR)
            if i + 1 < n and seq[i + 1][1] == "data":
                w1 = seq[i + 1][2]
                if w1 is None:
                    spec.append((v, "str"))
                else:
                    spec.append((v, w1))
                i += 2
                continue
            i += 1
        out[short(name)] = spec
        cache[va] = spec
    lines = ["SPEC = {"]
    for k, v in out.items():
        lines.append("    %r: %r," % (k, v))
    lines.append("}")
    text = "\n".join(lines)
    if "--write" in sys.argv:
        open("_byte_papers/msg_spec.py", "w", encoding="utf-8").write(text)
        print("写入 _byte_papers/msg_spec.py，%d 条消息" % len(out))
    else:
        print(text)


if __name__ == "__main__":
    main()
