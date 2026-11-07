#!/usr/bin/env python3
"""138 勘察: 大厅连接生命周期 —— 什么时候连上 / 什么时候断 / 断后还有没有活动。
用法: python -X utf8 tools\dyn138_conn_life.py [run_id...]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
rids = sys.argv[1:] or ["ONCE_20261031_174715", "ONCE_20261031_191256",
                        "ONCE_20261031_200457"]

TS = re.compile(r"^\[(\d\d:\d\d:\d\d)\]")
CONN = re.compile(r"大厅连接|连接结束|开始|=== |ConnectionReset|keepalive|recv 异常")

for rid in rids:
    log = os.path.join(RUNS, rid, "kit", "lobby_srv.log")
    if not os.path.isfile(log):
        continue
    print("=" * 70)
    print(rid)
    print("=" * 70)
    first_ts = last_ts = None
    events = []
    with open(log, encoding="utf-8", errors="replace") as f:
        for n, ln in enumerate(f, 1):
            m = TS.match(ln)
            if m:
                ts = m.group(1)
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            if CONN.search(ln):
                events.append((n, ln.strip()[:150]))
    print("日志首条时间=%s  末条时间=%s" % (first_ts, last_ts))
    print("\n连接事件:")
    for n, ln in events:
        print("   L%-4d %s" % (n, ln))
    # 断连之后还有多少条请求？
    print()
