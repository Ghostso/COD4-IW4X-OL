# -*- coding: utf-8 -*-
"""把大厅日志里"客户端请求过但我们没实现"的 (service, task) 全部清点成有限清单。

输入：run_codol_001\runs\**\lobby_srv.log
输出：每个 (service, task) 的出现次数、是否被实现、以及我们回的是什么。
判据（只在日志文本里找，不做推断）：
  - "UNMAPPED service=X task=Y"           -> 未实现，回空 ACK
  - "空应答"/"空 ACK"/"空页"                -> 有分支但无内容
  - 其余带 "-> ..." 说明的                     -> 已实现
"""
import os
import re
import collections

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL\CHAIN_UNIFIED_20261103\run_codol_001\runs"

req = collections.Counter()        # (svc,task) -> times seen
unmapped = collections.Counter()   # (svc,task) -> times answered UNMAPPED
empty = collections.Counter()
handled = collections.Counter()
logs = 0

for dp, dn, fn in os.walk(BASE):
    if "lobby_srv.log" not in fn:
        continue
    logs += 1
    p = os.path.join(dp, "lobby_srv.log")
    try:
        text = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    # 每个请求: "service=X ver=0x03 task=Y declared=Z"
    for m in re.finditer(r"service=(\d+) ver=0x03 task=(\d+) declared=\d+", text):
        req[(int(m.group(1)), int(m.group(2)))] += 1
    for m in re.finditer(r"UNMAPPED service=(\d+) task=(\d+)", text):
        unmapped[(int(m.group(1)), int(m.group(2)))] += 1
    for m in re.finditer(r"->\s*(\S+)\s+(\d+)/(\d+)\s+空应答", text):
        empty[(int(m.group(2)), int(m.group(3)))] += 1

print("logs scanned: %d" % logs)
print("distinct (service,task) the client requested: %d\n" % len(req))

print("%-10s %8s %10s %10s  %s" % ("svc/task", "times", "UNMAPPED", "空应答", "状态"))
for (s, t), n in sorted(req.items(), key=lambda kv: (-unmapped.get(kv[0], 0), -kv[1])):
    u = unmapped.get((s, t), 0)
    e = empty.get((s, t), 0)
    if u:
        st = "★ 未实现（回空 ACK）"
    elif e:
        st = "有空分支但无内容"
    else:
        st = "已实现"
    print("%-10s %8d %10d %10d  %s" % ("%d/%d" % (s, t), n, u, e, st))

print()
miss = [k for k in req if unmapped.get(k, 0)]
print("★ 未实现条目共 %d 条（占客户端请求种类的 %.0f%%）"
      % (len(miss), 100.0 * len(miss) / max(1, len(req))))
print("   出现次数合计 %d" % sum(req[k] for k in miss))
