# -*- coding: utf-8 -*-
"""大厅协议全量矩阵: 把 lobby_srv.log 里客户端发的每个 service/task 统计出来。

输出: service, task, 次数, payload 长度范围, 服务端处理结果(空ACK/映射/失败)。
用于回答: "大厅里客户端到底要哪些数据? 我们回了什么?"

用法:
    python _lobby_task_matrix.py [lobby_srv.log] [out.csv]
"""
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))

# <- ... service=93 ver=0x03 task=131 declared=61
RE_REQ = re.compile(r"service=(\d+)\s+ver=0x[0-9A-Fa-f]+\s+task=(\d+)\s+declared=(\d+)")
RE_UNMAPPED = re.compile(r"UNMAPPED service=(\d+) task=(\d+) payload=(\d+)B")
RE_REPLY = re.compile(r"->\s+(.*)$")
RE_PAYLOAD = re.compile(r"payload\((\d+)\)")


def main():
    log = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "lobby_srv.log")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "lobby_task_matrix.csv")
    lines = open(log, "r", encoding="utf-8", errors="replace").read().splitlines()
    reqs = defaultdict(lambda: {"n": 0, "sizes": [], "replies": defaultdict(int)})
    unmapped = defaultdict(int)
    pending = None
    for ln in lines:
        m = RE_REQ.search(ln)
        if m:
            svc, task, decl = int(m.group(1)), int(m.group(2)), int(m.group(3))
            pending = (svc, task)
            reqs[pending]["n"] += 1
            reqs[pending]["sizes"].append(decl)
            continue
        m = RE_PAYLOAD.search(ln)
        if m and pending:
            reqs[pending]["sizes"].append(int(m.group(1)))
            continue
        m = RE_UNMAPPED.search(ln)
        if m:
            unmapped[(int(m.group(1)), int(m.group(2)))] += 1
            pending = None
            continue
        m = RE_REPLY.search(ln)
        if m and pending:
            txt = m.group(1).strip()
            if txt.startswith("0x85"):
                reqs[pending]["replies"][txt.split("对象=")[-1].split("(")[0].strip()] += 1
            elif txt:
                key = txt[:48]
                reqs[pending]["replies"][key] += 1

    rows = []
    for (svc, task), d in sorted(reqs.items()):
        sizes = d["sizes"] or [0]
        reps = "; ".join("%s x%d" % (k, v) for k, v in
                         sorted(d["replies"].items(), key=lambda x: -x[1])[:3])
        rows.append((svc, task, d["n"], min(sizes), max(sizes), reps,
                     unmapped.get((svc, task), 0)))
    with open(out, "w", encoding="utf-8") as f:
        f.write("service,task,count,min_declared,max_declared,replies,unmapped\n")
        for r in rows:
            f.write("%d,%d,%d,%d,%d,\"%s\",%d\n" % r)

    print("%-9s %-6s %-6s %-12s %-10s %s" %
          ("service", "task", "次数", "declared", "UNMAPPED", "服务端应答"))
    print("-" * 100)
    for svc, task, n, lo, hi, reps, um in rows:
        print("%-9d %-6d %-6d %-12s %-10d %s"
              % (svc, task, n, ("%d..%d" % (lo, hi)) if lo != hi else str(lo),
                 um, reps[:60]))
    print()
    print("共 %d 个 service/task 组合 -> %s" % (len(rows), out))
    print("其中从未映射(UNMAPPED)的: %d 个"
          % sum(1 for r in rows if r[6] > 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
