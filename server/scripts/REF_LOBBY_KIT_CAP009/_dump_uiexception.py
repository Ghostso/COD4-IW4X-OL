# -*- coding: utf-8 -*-
"""从 lobby_srv.log 里把 71/7(ClientException/UIException) 的文本解出来。

这些是客户端上报的"哪个 UI 操作失败了、为什么失败", 是修大厅功能最直接的线索。
"""
import re
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"lobby_srv.log"
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    seen = {}
    for i, l in enumerate(lines):
        m = re.search(r"service=71 ver=0x.. task=7 declared=(\d+)", l)
        if not m or i + 1 >= len(lines):
            continue
        hm = re.match(r"\s*payload\(\d+\): ([0-9a-f ]+)$", lines[i + 1].strip())
        if not hm:
            continue
        bs = bytes(int(x, 16) for x in hm.group(1).split())
        txt = "".join(chr(b) if 32 <= b < 127 else "." for b in bs)
        if "UIException" not in txt:
            continue
        # 去掉二进制噪声, 只留可读片段
        parts = re.findall(r"[\x20-\x7e]{4,}", txt)
        key = " | ".join(parts)
        seen[key] = seen.get(key, 0) + 1
    for k, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print("%dx  %s" % (n, k))
        print("-" * 100)


if __name__ == "__main__":
    main()
