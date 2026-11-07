# -*- coding: utf-8 -*-
"""Build consolidated question register Q-01..Q-111 from authoritative sources."""
import os, csv, re, io

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = os.path.join(ROOT, "CODOL-DEMONWARE-BUNDLE-001")
os.makedirs(OUT, exist_ok=True)

rows = []   # dict: q, task, layer, question, impact, weight, status, score, weighted, evidence

def norm_impact(s):
    s = (s or "").strip().upper()
    for k in ("I4","I3","I2","I1"):
        if k in s: return k
    return s or "?"

W = {"I4":8,"I3":5,"I2":3,"I1":1}
def score_of(status, given=None):
    if given not in (None, ""):
        try: return float(given)
        except Exception: pass
    s = (status or "").upper()
    if "PROVEN" in s or "CLOSED" in s: return 1.0
    if "INFERRED" in s:
        return 0.6 if ("强" in status or "STRONG" in s) else 0.3
    if "BLOCKED" in s or "REFUTED" in s or "NOT-OBSERVED" in s: return 0.0
    return 0.0

# ---------------- 1) XVAL-02 authoritative ledger Q-01..Q-43 -------------
xv = os.path.join(ROOT, "XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT",
                  "XVAL02_QUESTION_REGISTER_MIGRATION.csv")
with open(xv, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        q = (r.get("Stable_ID") or "").strip()
        if not q.startswith("Q-"): continue
        rows.append(dict(
            q=q, task=(r.get("Origin_Task") or "").strip(),
            layer=(r.get("Protocol_Layer") or "").strip(),
            question=(r.get("Question") or "").strip(),
            impact=norm_impact(r.get("XVAL02_Impact") or r.get("XVAL01_Impact") or r.get("Hist_Impact")),
            weight=int(float(r.get("XVAL02_Weight") or 0)),
            status=(r.get("XVAL02_State") or "").strip(),
            score=float(r.get("XVAL02_Score") or 0.0),
            weighted=float(r.get("XVAL02_Weighted") or 0.0),
            evidence=(r.get("Evidence") or "").strip(),
            change=(r.get("Change_Type") or "").strip(),
        ))
print("XVAL-02 rows:", len(rows))

# ---------------- 2) E21..E27 + PEER + KEYFLOW deltas -------------
DELTAS = [
    ("E-21","E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001/E21_UNIFIED_REGISTER_DELTA.md"),
    ("E-22","E22_HMAC_DIRECTION_RETURN_PATH_001/E22_UNIFIED_REGISTER_DELTA.md"),
    ("E-23","E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001/E23_UNIFIED_REGISTER_DELTA.md"),
    ("E-24","E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001/E24_UNIFIED_REGISTER_DELTA.md"),
    ("E-25","E25_HANDSHAKE_RESPONSE_SEND_PATH_001/E25_UNIFIED_REGISTER_DELTA.md"),
    ("E-26","E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/E26_UNIFIED_REGISTER_DELTA.md"),
    ("E-27","E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/E27_UNIFIED_REGISTER_DELTA.md"),
    ("PEER-REUSE-AUDIT-001","CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/07_QUESTION_REGISTER_DELTA.md"),
    ("CODEC-KEYFLOW-001","CLIENT-DEMONWARE-CODEC-KEYFLOW-001/07_QUESTION_REGISTER_DELTA.md"),
]
qrow = re.compile(r"^\|\s*(Q-\d+)\s*\|")
for task, rel in DELTAS:
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        print("MISSING", path); continue
    text = open(path, encoding="utf-8").read()
    n = 0
    for line in text.splitlines():
        m = qrow.match(line)
        if not m: continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # layout: Q|layer|question|impact|weight|status|score|weighted|evidence
        if len(cells) < 8: continue
        q, layer, question, impact, weight, status, score, weighted = cells[:8]
        ev = cells[8] if len(cells) > 8 else ""
        try: w = int(float(weight))
        except Exception: continue
        rows.append(dict(q=q, task=task, layer=layer, question=question,
                         impact=norm_impact(impact), weight=w, status=status,
                         score=score_of(status, score), weighted=float(w)*score_of(status, score),
                         evidence=ev, change=""))
        n += 1
    print(task, "->", n)

rows.sort(key=lambda r: int(r["q"].split("-")[1]))
tot = sum(r["weight"] for r in rows)
sc  = sum(r["weighted"] for r in rows)
i4  = [r for r in rows if r["impact"]=="I4"]
i4w, i4s = sum(r["weight"] for r in i4), sum(r["weighted"] for r in i4)
print("TOTAL", len(rows), "weight", tot, "score", round(sc,2), "rate", round(100*sc/tot,3))
print("I4", len(i4), "weight", i4w, "score", round(i4s,2), "rate", round(100*i4s/i4w,3))
import json
json.dump(dict(rows=rows, total=tot, score=sc, i4_weight=i4w, i4_score=i4s),
          open(os.path.join(OUT,"_register_raw.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
