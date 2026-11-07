#!/usr/bin/env python3
"""统计每个 task 的 blob 是否满足「首 u32 = 长度-4」的内层长度前缀规则。"""
import json
import struct
import sys
from collections import Counter

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse  # noqa: E402


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    total = Counter()
    good = Counter()
    prefix4 = Counter()   # 首 4 字节像不像长度（任意偏移）
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        ok, elems, _why = parse(b)
        if not ok:
            continue
        key = (r["svc"], r["task"])
        for t, v in elems:
            if t != 0x13:
                continue
            total[key] += 1
            if len(v) >= 4:
                n = struct.unpack_from("<I", v, 0)[0]
                if n == len(v) - 4:
                    good[key] += 1
                # 也统计"任意位置有 u32 == len - pos"的情况
                for off in range(0, min(16, len(v) - 3)):
                    if struct.unpack_from("<I", v, off)[0] == len(v) - off - 4:
                        prefix4[key] += 1
                        break

    print("%-10s %8s %8s %8s" % ("task", "blobs", "首-u32", "任意off"))
    for k in sorted(total, key=lambda x: (x[0], x[1])):
        print("%-10s %8d %8d %8d" % ("%d/%d" % k, total[k], good[k], prefix4[k]))


if __name__ == "__main__":
    main()
