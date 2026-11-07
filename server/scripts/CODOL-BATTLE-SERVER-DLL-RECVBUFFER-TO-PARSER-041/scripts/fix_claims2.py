# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
lines=io.open(os.path.join(ROOT,"05_DATAFLOW_GRAPH.md"),encoding="utf-8").read().split("\n")
for i,l in enumerate(lines):
    if "0x2310B1/0x2310C1 call 0x22A670" in l:
        lines[i]=l.replace("job.id","job+0x14")
io.open(os.path.join(ROOT,"05_DATAFLOW_GRAPH.md"),"w",encoding="utf-8",newline="").write("\n".join(lines))
t=io.open(os.path.join(ROOT,"06_HYPOTHESIS_LEDGER.md"),encoding="utf-8").read()
t=t.replace("5. 结果结构仅含 `{seq, rtt, payload_len, ttl}`,与\"延迟探测\"一致。",
            "5. 结果结构仅含 `{seq, rtt, payload_len, ttl}`,与\"延迟探测\"一致(其中 ttl 被调用方线程过程读回)。")
io.open(os.path.join(ROOT,"06_HYPOTHESIS_LEDGER.md"),"w",encoding="utf-8",newline="").write(t)
print("done")
