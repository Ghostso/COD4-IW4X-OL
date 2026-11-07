import hashlib, os, re
base = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\07_OFFLINE_001"
man = os.path.join(base, "OFFLINE_001_CHECKSUMS.txt")
ok=0; bad=0; missing=0
for line in open(man, encoding="utf-8"):
    line=line.rstrip("\n")
    m = re.match(r'^([0-9A-Fa-f]{64})  (.+)$', line)
    if not m: continue
    want, path = m.group(1).upper(), m.group(2)
    p = path if os.path.isabs(path) else os.path.join(base, path)
    if not os.path.exists(p):
        print("MISSING", path); missing+=1; continue
    got = hashlib.sha256(open(p,"rb").read()).hexdigest().upper()
    if got==want: ok+=1
    else:
        print("MISMATCH", path, "\n  want", want, "\n  got ", got); bad+=1
print(f"OK={ok} BAD={bad} MISSING={missing}")
