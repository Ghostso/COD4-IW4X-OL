#!/usr/bin/env python3
"""只读 .ifs 的低熵区（明文清单），统计与前端的资源路径分布。

不读载荷（23GB），只读每个文件的清单区窗口。
"""
import os
import re
import sys
from collections import Counter


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    prefixes = Counter()
    ext = Counter()
    extset = {}
    for fn in files:
        p = os.path.join(root, fn)
        with open(p, "rb") as f:
            # 读前 256KB（够覆盖所有 16KB 清单与大多数小文件清单）
            w = f.read(256 * 1024)
        for m in re.finditer(rb"[ -~]{6,}", w):
            s = m.group().decode("latin1")
            if "/" not in s:
                continue
            # 扩展名
            if "." in s:
                e = s.rsplit(".", 1)[1].split("\\")[0].split("/")[0]
                if 1 <= len(e) <= 6:
                    ext[e] += 1
                    extset.setdefault(e, s)
            # 顶级目录 + 二级
            parts = s.split("/")
            if len(parts) >= 2:
                prefixes["/".join(parts[:2])] += 1
    print("=== 扩展名 top 30 ===")
    for k, v in ext.most_common(30):
        print("  .%-8s %6d   例: %s" % (k, v, extset[k][:70]))
    print()
    print("=== 路径前缀 top 40 ===")
    for k, v in prefixes.most_common(40):
        print("  %-45s %d" % (k, v))


if __name__ == "__main__":
    main()
