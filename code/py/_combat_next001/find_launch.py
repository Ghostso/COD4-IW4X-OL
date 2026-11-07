# -*- coding: utf-8 -*-
import io, os, re, glob
KIT = r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT"
pat = re.compile(r"(run_all\.py[^\r\n]{0,160})")
seen = {}
for p in glob.glob(os.path.join(KIT, "*.txt")) + glob.glob(os.path.join(KIT, "*.log")):
    try:
        s = io.open(p, "rb").read().decode("utf-8", "replace")
    except Exception:
        continue
    for m in pat.finditer(s):
        cmd = m.group(1).strip()
        seen.setdefault(cmd, []).append(os.path.basename(p))
for cmd, files in sorted(seen.items(), key=lambda kv: -len(kv[1]))[:15]:
    print("  %-90s  (%s)" % (cmd[:90], ",".join(sorted(set(files))[:3])))
print()
print("=== run_all.py --help / argv defaults ===")
r = io.open(os.path.join(KIT, "run_all.py"), encoding="utf-8").read()
i = r.find("add_argument")
print(r[max(0,i-100):i+1800])
