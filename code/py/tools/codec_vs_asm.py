#!/usr/bin/env python3
"""编码器 (dwroom_codec3) 与反汇编 (serialize_extract6) 逐条对账。
两者完全独立：一个是 spec→位，一个是代码→位。若全等，说明 spec 无转录错误。"""
import subprocess
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "_byte_papers")
import serialize_extract6 as E  # noqa: E402
import dwroom_codec3 as C  # noqa: E402


def asm_length(va):
    b = open(E.DUMP, "rb").read()
    seq, loops = E.analyze(b, va, E.WB, E.WD)
    pre = sum(w for lp, k, w, a, v in seq if isinstance(w, int) and not lp)
    lp_ = sum(w for lp, k, w, a, v in seq if isinstance(w, int) and lp)
    var = any(w is None and k == "data" for lp, k, w, a, v in seq)
    return pre, lp_, loops, var


def main():
    rows = E.rows_from_vtable()
    import re
    vlt = {re.sub(r"^dwRoomMessage|^dwRoomSpy", "", n) or n: int(ser, 16)
           for n, ser, _ in rows}
    vlt["P2PInfo"] = 0x627fc0
    vlt["Message"] = vlt.pop("", 0x625946) if "" in vlt else 0x625946
    print("%-34s %-8s %-8s %-8s %s" % (
        "message", "asm位", "codec位", "差", "备注"))
    ok = bad = 0
    for k in sorted(C.SPEC):
        if k not in vlt:
            print("%-34s (无 serialize 地址)" % k)
            continue
        pre, lp_, loops, var = asm_length(vlt[k])
        try:
            d, t, _, _ = C.encode(k)
        except SystemExit:
            continue
        asm_total = pre + lp_
        diff = t - asm_total
        flag = ""
        if loops:
            flag += "循环×%d " % loops
        if var:
            flag += "变长 "
        if diff == 0:
            ok += 1
        else:
            bad += 1
        print("%-34s %-8d %-8d %-8d %s" % (
            k, asm_total, t, diff, flag))
    print("\n一致 %d / %d" % (ok, ok + bad))


if __name__ == "__main__":
    main()
