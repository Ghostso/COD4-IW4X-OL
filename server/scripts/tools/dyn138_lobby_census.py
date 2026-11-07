#!/usr/bin/env python3
"""138 动态卷: 解析本次 run 的 lobby_srv.log -> (service,task) 台账.
输出: 每条 (svc,task): 次数 / 是否实现(UNMAPPED) / declared 长度集合 / 应答字节数集合 / 对象数集合
"""
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG = (r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
       r"\ONCE_20261031_174715\kit\lobby_srv.log")

RE_REQ = re.compile(r"解密成功 #(\d+) seq=(\d+) hmac=(\w+) marker=0x(\w+) "
                    r"service=(\d+) ver=0x(\w+) task=(\d+) declared=(\d+)")
RE_UNMAPPED = re.compile(r"UNMAPPED service=(\d+) task=(\d+) payload=(\d+)B")
RE_RESP = re.compile(r"-> 0x(\w+) 应答 seq=(\d+)\(replyId=(\d+)\) service=(\d+) "
                     r"task=(\d+) 对象=(\d+) \((\d+) 字节\)")

req = Counter()
decl = defaultdict(Counter)
unmapped = Counter()
resp = Counter()
resp_bytes = defaultdict(Counter)
resp_objs = defaultdict(Counter)
order = []
nline = 0
with open(LOG, encoding="utf-8", errors="replace") as f:
    for line in f:
        nline += 1
        m = RE_REQ.search(line)
        if m:
            svc, task, d = int(m.group(5)), int(m.group(7)), int(m.group(8))
            req[(svc, task)] += 1
            decl[(svc, task)][d] += 1
            order.append((svc, task))
            continue
        m = RE_UNMAPPED.search(line)
        if m:
            unmapped[(int(m.group(1)), int(m.group(2)))] += 1
            continue
        m = RE_RESP.search(line)
        if m:
            svc, task = int(m.group(4)), int(m.group(5))
            resp[(svc, task)] += 1
            resp_bytes[(svc, task)][int(m.group(7))] += 1
            resp_objs[(svc, task)][int(m.group(6))] += 1

print("日志行数 %d ; 解密请求 %d ; 应答 %d ; UNMAPPED %d"
      % (nline, sum(req.values()), sum(resp.values()), sum(unmapped.values())))
print("不同 (svc,task) 请求 = %d ; 不同应答 = %d ; UNMAPPED 种类 = %d"
      % (len(req), len(resp), len(unmapped)))
print()
print("%-8s %-5s %-5s %-8s %-18s %-22s %s" % (
    "(svc,task)", "次数", "实现", "declared", "应答字节数", "对象数", "同 task 在语料?"))
for k in sorted(req):
    svc, task = k
    d = sorted(decl[k])
    rb = sorted(resp_bytes[k])
    ro = sorted(resp_objs[k])
    print("%-8s %-5d %-5s %-8s %-18s %-22s" % (
        "%d/%d" % k, req[k],
        "否" if k in unmapped else "是",
        ",".join(map(str, d))[:8],
        ",".join(map(str, rb))[:18],
        ",".join(map(str, ro))[:22]))
print()
print("UNMAPPED(=客户端要了但没实现) 清单:")
for k in sorted(unmapped):
    print("   %d/%d  x%d" % (k[0], k[1], unmapped[k]))
print()
print("前 40 个请求顺序:", " ".join("%d/%d" % k for k in order[:40]))
