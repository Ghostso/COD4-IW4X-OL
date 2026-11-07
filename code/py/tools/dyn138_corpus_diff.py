#!/usr/bin/env python3
"""138 动态卷: 把本次会话的 (svc,task) 与语料对账 -> 哪些是**新任务**(语料里没有)."""
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
LOG = (r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
       r"\ONCE_20261031_174715\kit\lobby_srv.log")

recs = json.load(open(CORPUS, encoding="utf-8"))
corpus_pairs = Counter()
for r in recs:
    corpus_pairs[(r["svc"], r["task"])] += 1

RE_REQ = re.compile(r"解密成功 #\d+ seq=\d+ hmac=\w+ marker=0x\w+ "
                    r"service=(\d+) ver=0x\w+ task=(\d+) declared=(\d+)")
run_pairs = Counter()
decl = {}
with open(LOG, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = RE_REQ.search(line)
        if m:
            k = (int(m.group(1)), int(m.group(2)))
            run_pairs[k] += 1
            decl.setdefault(k, set()).add(int(m.group(3)))

print("语料 (svc,task) 种类 = %d ; 本次会话种类 = %d" % (len(corpus_pairs), len(run_pairs)))
new = sorted(k for k in run_pairs if k not in corpus_pairs)
seen = sorted(k for k in run_pairs if k in corpus_pairs)
print("\n★ 本次出现但**语料里没有**的 (svc,task) = %d 个：" % len(new))
for k in new:
    print("   %d/%d  x%d  declared=%s" % (k[0], k[1], run_pairs[k], sorted(decl[k])))
print("\n语料里也有、本次也出现的 (svc,task) = %d 个：" % len(seen))
for k in seen:
    print("   %d/%d  x%d (语料 %d 条) declared=%s"
          % (k[0], k[1], run_pairs[k], corpus_pairs[k], sorted(decl[k])))
