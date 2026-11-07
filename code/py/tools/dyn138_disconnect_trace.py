#!/usr/bin/env python3
"""138: 定位「点创建房间 -> 大厅连接断开」的精确时序。
找出每个 run 里 连接结束 事件前最后 N 条请求，以及重连后第一条。
用法: python -X utf8 tools/dyn138_disconnect_trace.py [run_id...]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
rids = sys.argv[1:] or ["ONCE_20261031_200457", "ONCE_20261031_191256",
                        "ONCE_20261031_174715"]

TS = re.compile(r"^\[(\d\d:\d\d:\d\d)\]")
REQ = re.compile(r"解密成功 #\d+ seq=(\d+) .*service=(\d+) ver=0x\w+ task=(\d+)")
CONN = re.compile(r"大厅连接(建立|结束)")

for rid in rids:
    log = os.path.join(RUNS, rid, "kit", "lobby_srv.log")
    if not os.path.isfile(log):
        continue
    print("=" * 78)
    print(rid)
    print("=" * 78)
    lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
    # 记录每次连接区间
    for i, ln in enumerate(lines):
        m = CONN.search(ln)
        if not m:
            continue
        ts = TS.match(ln)
        kind = m.group(1)
        print("\n--- [%s] 连接%s (L%d) ---" % (ts.group(1) if ts else "?", kind, i + 1))
        if kind == "结束":
            # 往前找最后 8 条请求
            pre = []
            for j in range(i - 1, max(-1, i - 200), -1):
                r = REQ.search(lines[j])
                if r:
                    t2 = TS.match(lines[j])
                    pre.append((j + 1, t2.group(1) if t2 else "?", r.group(2), r.group(3)))
                    if len(pre) >= 8:
                        break
            print("   断开前最后 8 条请求:")
            for j, t2, svc, task in reversed(pre):
                print("      L%-4d [%s] %s/%s" % (j, t2, svc, task))
            # 断连原因行
            for j in range(i - 1, max(-1, i - 4), -1):
                if "异常" in lines[j] or "Reset" in lines[j]:
                    print("   原因: " + lines[j].strip())
        else:
            # 重连后前 6 条
            post = []
            for j in range(i + 1, min(len(lines), i + 200)):
                r = REQ.search(lines[j])
                if r:
                    t2 = TS.match(lines[j])
                    post.append((j + 1, t2.group(1) if t2 else "?", r.group(2), r.group(3)))
                    if len(post) >= 6:
                        break
            print("   重连后前 6 条请求:")
            for j, t2, svc, task in post:
                print("      L%-4d [%s] %s/%s" % (j, t2, svc, task))
