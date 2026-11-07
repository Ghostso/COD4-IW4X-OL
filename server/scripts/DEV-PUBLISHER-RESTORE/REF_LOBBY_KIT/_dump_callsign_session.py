# -*- coding: utf-8 -*-
"""按时间顺序打印一段会话里所有 (service, task, payload), 找 Callsign 的拥有/试戴调用。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    start = 0
    if len(sys.argv) > 1:
        start = int(sys.argv[1])
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(lines)
    for i in range(start, min(end, len(lines))):
        ln = lines[i]
        if ("解密成功" in ln or "-> " in ln or "UNMAPPED" in ln
                or "ConnectionReset" in ln or "大厅连接" in ln
                or "payload(" in ln):
            print("%5d| %s" % (i, ln[:220]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
