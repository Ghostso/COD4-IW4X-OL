#!/usr/bin/env python3
"""138 动态卷: 对某个 run 目录出报告（请求台账 + 应答框架 + 与语料对账）。
用法: python -X utf8 tools\dyn138_run_report.py ONCE_20261031_191256
"""
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"

rid = sys.argv[1] if len(sys.argv) > 1 else "ONCE_20261031_174715"
log = os.path.join(RUNS, rid, "kit", "lobby_srv.log")
print("=== run %s ===" % rid)
print("日志存在:", os.path.isfile(log))

RE_REQ = re.compile(r"解密成功 #\d+ seq=\d+ hmac=(\w+) marker=0x(\w+) "
                    r"service=(\d+) ver=0x(\w+) task=(\d+) declared=(\d+)")
RE_RESP = re.compile(r"-> 0x(\w+) 应答 seq=(\d+)\(replyId=(\d+)\) service=(\d+) "
                     r"task=(\d+) 对象=(\d+) \((\d+) 字节\)")
RE_UNM = re.compile(r"UNMAPPED service=(\d+) task=(\d+) payload=(\d+)B")

req, decl, resp, rbytes, robjs, unm = Counter(), {}, Counter(), {}, {}, Counter()
order = []
hmac_bad = 0
n = 0
with open(log, encoding="utf-8", errors="replace") as f:
    for ln in f:
        n += 1
        m = RE_REQ.search(ln)
        if m:
            k = (int(m.group(3)), int(m.group(5)))
            req[k] += 1
            decl.setdefault(k, set()).add(int(m.group(6)))
            order.append(k)
            if m.group(1).upper() != "OK":
                hmac_bad += 1
            continue
        m = RE_RESP.search(ln)
        if m:
            k = (int(m.group(4)), int(m.group(5)))
            resp[k] += 1
            rbytes.setdefault(k, set()).add(int(m.group(7)))
            robjs.setdefault(k, set()).add(int(m.group(6)))
            continue
        m = RE_UNM.search(ln)
        if m:
            unm[(int(m.group(1)), int(m.group(2)))] += 1

print("行数 %d ; 请求 %d (hmac!=OK %d) ; 应答 %d ; UNMAPPED 次 %d"
      % (n, sum(req.values()), hmac_bad, sum(resp.values()), sum(unm.values())))
print("不同 (svc,task) = %d ; 其中未实现 = %d" % (len(req), len(unm)))

recs = json.load(open(CORPUS, encoding="utf-8"))
cpairs = Counter((r["svc"], r["task"]) for r in recs)
new = [k for k in req if k not in cpairs]
print("\n★ 语料里没有的 (svc,task) = %d 个 %s" % (len(new), sorted(new) if new else ""))
print("\n%-9s %-4s %-4s %-16s %-22s %s" % ("(svc,task)", "次数", "实现", "declared", "应答字节", "对象数"))
for k in sorted(req):
    print("%-9s %-4d %-4s %-16s %-22s %s" % (
        "%d/%d" % k, req[k], "否" if k in unm else "是",
        ",".join(map(str, sorted(decl[k])))[:16],
        ",".join(map(str, sorted(rbytes[k])))[:22],
        ",".join(map(str, sorted(robjs[k])))[:12]))
print("\n请求顺序:", " ".join("%d/%d" % k for k in order))
