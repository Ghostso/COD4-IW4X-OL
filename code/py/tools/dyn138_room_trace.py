#!/usr/bin/env python3
"""138 勘察: 在某个 run 的 lobby_srv.log 里查 service=11 / 21 / 6 的请求与推送。

用法: python -X utf8 tools\dyn138_room_trace.py [run_id]
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
rids = sys.argv[1:] or ["ONCE_20261031_200457", "ONCE_20261031_191256",
                        "ONCE_20261031_174715"]

RE_REQ = re.compile(r"解密成功 #\d+ seq=(\d+) hmac=(\w+) marker=0x(\w+) "
                    r"service=(\d+) ver=0x(\w+) task=(\d+) declared=(\d+)")
RE_RESP = re.compile(r"-> 0x(\w+) 应答 seq=(\d+)\(replyId=(\d+)\) service=(\d+) "
                     r"task=(\d+) 对象=(\d+) \((\d+) 字节\)")
RE_PUSH = re.compile(r"push|推送|instant_push|build_push", re.I)

for rid in rids:
    log = os.path.join(RUNS, rid, "kit", "lobby_srv.log")
    if not os.path.isfile(log):
        print("%s : 日志不存在" % rid)
        continue
    print("=" * 72)
    print("run %s" % rid)
    print("=" * 72)
    hits11 = []
    hits21 = []
    hits6 = []
    pushes = []
    n = 0
    with open(log, encoding="utf-8", errors="replace") as f:
        for n, ln in enumerate(f, 1):
            m = RE_REQ.search(ln)
            if m:
                svc, task = int(m.group(4)), int(m.group(6))
                rec = (n, svc, task, int(m.group(7)), ln.strip()[:120])
                if svc == 11:
                    hits11.append(rec)
                elif svc == 21:
                    hits21.append(rec)
                elif svc == 6:
                    hits6.append(rec)
                continue
            if RE_PUSH.search(ln) and ("应答" not in ln):
                pushes.append((n, ln.strip()[:140]))
    def show(name, rows):
        print("\n-- service %s : %d 条 --" % (name, len(rows)))
        for n, svc, task, decl, ln in rows:
            print("   L%-4d %d/%d declared=%d" % (n, svc, task, decl))
    show("11", hits11)
    show("21", hits21)
    show("6", hits6)
    print("\n-- 推送/ push 字样 : %d 条 --" % len(pushes))
    for n, ln in pushes[:15]:
        print("   L%-4d %s" % (n, ln))
    print("\n日志总行数 %d" % n)
