import os, re
root = r"./run_codol_001/sandbox_ifs1_20260923/IIPS/TPFUI"
pat = re.compile(r"([^\"'<>;?\s]+\.png)(?:\?([0-9]+),([0-9]+),([0-9]+),([0-9]+))?", re.I)
need = {}
for d, _, fs in os.walk(root):
    for fn in fs:
        if not fn.lower().endswith((".tpf", ".xml")):
            continue
        p = os.path.join(d, fn)
        try:
            s = open(p, encoding="utf-8-sig", errors="ignore").read()
        except Exception:
            continue
        for m in pat.finditer(s):
            path = m.group(1).replace("\\", "\\").replace("/", "\\").lstrip("\\")
            if ":" in path:
                path = path.split(":", 1)[1]
            if m.group(4):
                w, h = int(m.group(4)), int(m.group(5))
            else:
                w = h = 1
            key = path.lower()
            old = need.get(key, (0, 0, m.group(1)))
            need[key] = (max(old[0], w), max(old[1], h), old[2])
print("refs", len(need))
top = sorted(need.items(), key=lambda kv: -(kv[1][0] * kv[1][1]))[:25]
for k, (w, h, orig) in top:
    print(w, h, orig)
print("max", max((w for w, h, _ in need.values()), default=0),
      max((h for w, h, _ in need.values()), default=0))
base = os.path.join(root, "IIPSRes")
missing, placeholders = [], []
for k, (w, h, orig) in need.items():
    cands = [os.path.join(base, k), os.path.join(root, k)]
    p = next((x for x in cands if os.path.exists(x)), None)
    if not p:
        missing.append(orig)
    elif os.path.getsize(p) <= 69:
        placeholders.append((p, w, h))
print("missing", len(missing), "placeholders", len(placeholders))
print("missing sample", missing[:15])
