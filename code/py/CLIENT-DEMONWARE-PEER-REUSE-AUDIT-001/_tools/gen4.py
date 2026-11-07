# -*- coding: utf-8 -*-
import os, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001"
p = os.path.join(root,"07_QUESTION_REGISTER_DELTA.md")
t = open(p,encoding="utf-8").read()
t = t.replace(
"| Q-101 | 对端/适配 | 参考对端是否实现客户端 codec 层 | I4 | 8 | REFUTED | 0.0 | 0.0 | 05 §缺口（常量/置换扫描 0 命中） |",
"| Q-101 | 对端/适配 | 参考对端派生链是否已与 2697 客户端完全等同（含 20B/16B codec 层） | I4 | 8 | REFUTED | 0.0 | 0.0 | 05 §缺口（codec 常量/置换扫描 0 命中；对端无对应实现） |")
open(p,"w",encoding="utf-8").write(t)

files = sorted(f for f in os.listdir(root) if f.endswith(".md"))
lines = []
for f in files:
    h = hashlib.sha256(open(os.path.join(root,f),"rb").read()).hexdigest()
    lines.append("%s  %s" % (h, f))
for d,f in [("_data","func_AAB310.txt"),("_data","recv_frame_parser.txt"),("_data","recv_parser_core.txt"),("_data","dispatcher.txt"),("_data","frame_85_region.txt")]:
    fp = os.path.join(root,d,f)
    if os.path.exists(fp):
        lines.append("%s  %s/%s" % (hashlib.sha256(open(fp,"rb").read()).hexdigest(), d, f))
open(os.path.join(root,"SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("manifest rewritten,", len(lines), "entries")
