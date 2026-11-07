# -*- coding: utf-8 -*-
"""追踪"购买成功"之后客户端发起的每一个请求, 看它靠什么更新 UI。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    idx = [i for i, l in enumerate(lines) if "购买成功" in l]
    if not idx:
        print("没有购买成功记录")
        return 1
    i = idx[-1]
    print("最后一次购买成功 @行 %d: %s" % (i, lines[i].strip()))
    print()
    print("之后的所有请求:")
    for j in range(i, min(len(lines), i + 60)):
        l = lines[j]
        if "解密成功" in l:
            m = re.search(r"service=(\d+) ver=\S+ task=(\d+) declared=(\d+)", l)
            if m:
                print("  %5d| svc=%s task=%s declared=%s" %
                      (j, m.group(1), m.group(2), m.group(3)))
        elif "-> " in l and ("marketplace" in l or "UNMAPPED" in l):
            print("  %5d|      %s" % (j, l.strip()[:110]))
        elif "大厅连接" in l:
            print("  %5d| %s" % (j, l.strip()[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
