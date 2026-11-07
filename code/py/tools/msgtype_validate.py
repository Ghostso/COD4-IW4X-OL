#!/usr/bin/env python3
"""校验类型号表：覆盖、重复、缺口。并把 Text 的特殊情形人工补入。"""
import sys

SRC = "_byte_papers/msgtype_stack2.txt"

# 人工补正（有代码依据）：
#   dwRoomMessageText 的类型号 2 是在工厂 0x62b94b 里先按基类写入
#   ("mov [ebp-0x1c],2") 再把 vfptr 换成 Text 的 0xdc7504 —— 即 Text 就是 2。
MANUAL = {
    "dwRoomMessageText": 2,
}

SKIP = {   # 非 dwRoomMessage 家族（无类型号）
    "dwRoomMatch", "dwRoomMatchUber", "dwRoom",
    "dwRoomImp", "dwRoomDMZLeagueCallbackHandler",
    "dwRoomEventTournamentHandler",
}


def main():
    rows = []
    for line in open(SRC, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5 or p[0] == "class":
            continue
        name = p[0]
        t = p[1] if p[1] else None
        if name in MANUAL:
            t = str(MANUAL[name])
        rows.append((name, int(t) if t not in (None, "") else None))

    msg_rows = [(n, t) for n, t in rows if n not in SKIP]
    print("dwRoomMessage 家族: %d 类, 有类型号 %d" % (
        len(msg_rows), sum(1 for _, t in msg_rows if t is not None)))
    print("\n=== 类型号排序 ===")
    for name, t in sorted(msg_rows, key=lambda x: (x[1] is None, x[1] or 0)):
        print("%3s  0x%-3s  %s" % (
            t if t is not None else "?",
            ("%02x" % t) if t is not None else "--", name))

    nums = [t for _, t in msg_rows if t is not None]
    lo, hi = min(nums), max(nums)
    have = set(nums)
    print("\n范围 %d..%d（共 %d 个号），实有 %d，缺 %d 个" % (
        lo, hi, hi - lo + 1, len(have), hi - lo + 1 - len(have)))
    print("缺口:", [i for i in range(lo, hi + 1) if i not in have])
    dup = {}
    for n, t in msg_rows:
        if t is not None:
            dup.setdefault(t, []).append(n)
    d = {k: v for k, v in dup.items() if len(v) > 1}
    print("重复:", d if d else "无")
    missing = [n for n, t in msg_rows if t is None]
    print("未命中:", missing)


if __name__ == "__main__":
    main()
