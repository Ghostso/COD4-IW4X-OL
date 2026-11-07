# -*- coding: utf-8 -*-
"""044: integrity manifest + independent self-verification. READ-ONLY w.r.t. inputs."""
import _common as c, os, csv, hashlib, json

T = c.ROOT
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()

# ---- collect deliverables ----
files = []
for base, dirs, fs in os.walk(T):
    for fn in fs:
        p = os.path.join(base, fn)
        rel = os.path.relpath(p, T).replace("\\", "/")
        if rel.startswith("scripts/__pycache__/"):
            continue
        if rel in ("SHA256SUMS.txt", "FILE_HASH_MANIFEST.tsv"):
            continue
        files.append((rel, p))
files.sort()

# ---- independently re-verify claims ----
checks = []
def chk(name, ok, detail=""):
    checks.append((name, "PASS" if ok else "FAIL", detail))

# 1) input hashes
chk("input S-IMG sha256", sha(c.IMG) == "17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045", c.IMG)
chk("input S-DLL sha256", sha(c.DLL) == "ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20", c.DLL)
chk("input S-EXE sha256", sha(c.EXE) == "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537", c.EXE)

# 2) required deliverables present
req = ["00_INDEX.md","01_SAMPLE_SCOPE_AND_HASHES.md","02_DECODER_TYPE_DOMAIN.tsv",
       "03_DECODER_CONTROL_FLOW.md","04_INDIRECT_CALL_SCAN.tsv","05_FUNCTION_POINTER_CANDIDATES.tsv",
       "06_BLOCKER_REASSESSMENT.tsv","07_RUNTIME_EVIDENCE_NECESSITY.md","08_NEXT_ACTION_DECISION.md",
       "09_CORRECTION_LOG.md","TEST_AND_VALIDATION_RESULTS.md","SHA256SUMS.txt","FILE_HASH_MANIFEST.tsv"]
for r in req:
    chk("deliverable present: " + r, os.path.exists(os.path.join(T, r)), "")

# 3) every TSV has a header + rectangular
for r in [x for x in req if x.endswith(".tsv") and x not in ("SHA256SUMS.txt","FILE_HASH_MANIFEST.tsv")]:
    p = os.path.join(T, r)
    rows = list(csv.reader(open(p, encoding="utf-8"), delimiter="\t"))
    n = len(rows[0]) if rows else 0
    rect = all(len(x) == n for x in rows) if rows else False
    chk("TSV header+rectangular: " + r, n > 0 and len(rows) > 1 and rect, "%d cols / %d rows" % (n, len(rows)-1))

# 4) 06 covers BE-01..BE-07
rows = list(csv.reader(open(os.path.join(T,"06_BLOCKER_REASSESSMENT.tsv"), encoding="utf-8"), delimiter="\t"))
ids = [x[0] for x in rows[1:]]
chk("06 covers BE-01..BE-07", ids == ["BE-%02d" % i for i in range(1,8)], str(ids))

# 5) 08 picks exactly one decision
d8 = open(os.path.join(T,"08_NEXT_ACTION_DECISION.md"), encoding="utf-8").read()
chk("08 states a single decision", "### 决策:" in d8 and d8.count("### 决策:") == 1, "")

# 6) regenerable: E8 callers of decoders still match
IB = c.IMG_IB; IMG = c._bi
sec0 = c.IMG_SECS[0]; PLO = sec0["raw"]; PHI = sec0["raw"] + sec0["rsize"]
def e8(tgt):
    s=[]; i=PLO
    while i < PHI-5:
        if IMG[i]==0xE8:
            rel=int.from_bytes(IMG[i+1:i+5],"little",signed=True)
            if IB+i+5+rel == IB+tgt: s.append(i)
        i+=1
    return s
chk("E8 callers 0x87C110 == [0x85D49D]", ["%x"%x for x in e8(0x87C110)]==["85d49d"], str(["%x"%x for x in e8(0x87C110)]))
chk("E8 callers 0x87D5A0 == 4 sites", len(e8(0x87D5A0))==4, str(["%x"%x for x in e8(0x87D5A0)]))
chk("E8 callers 0x87EDB0 == [0x87C9B7]", ["%x"%x for x in e8(0x87EDB0)]==["87c9b7"], str(["%x"%x for x in e8(0x87EDB0)]))

# 7) files unchanged outside 044 (spot check on 043 dir)
p43 = os.path.join(c.WS, "CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043", "SHA256SUMS.txt")
ok43 = True
if os.path.exists(p43):
    for line in open(p43, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line: continue
        parts = line.split(None, 1)
        if len(parts) != 2: continue
        h, rel = parts[0], parts[1].lstrip("*").strip()
        fp = os.path.join(c.WS, "CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043", rel)
        if os.path.exists(fp) and sha(fp) != h:
            ok43 = False; break
chk("043 deliverables unmodified (re-hash 043 manifest)", ok43, p43)

# ---- write manifests ----
man = ["file\tbytes\tsha256"]
sums = []
for rel, p in files:
    b = os.path.getsize(p)
    h = sha(p)
    man.append("%s\t%d\t%s" % (rel, b, h))
    sums.append("%s  %s" % (h, rel))
c.w(os.path.join(T, "FILE_HASH_MANIFEST.tsv"), "\n".join(man) + "\n")
c.w(os.path.join(T, "SHA256SUMS.txt"), "\n".join(sums) + "\n")

# ---- validation report ----
L = ["# TEST_AND_VALIDATION_RESULTS", "",
     "**镜像:** S-IMG `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`",
     "**日期:** 2026-10-13 (Asia/Shanghai)","","## 1. 独立校验项","",
     "| # | 校验 | 结果 | 证据 |","|---|---|---|---|"]
for i,(n,s,d) in enumerate(checks,1):
    L.append("| %d | %s | **%s** | `%s` |" % (i, n, s, d))
L += ["", "## 2. 覆盖范围与算法(可复现)", "",
      "- Phase A: `scripts/a01_identity.py`(哈希 / 节区表 / 约定探测 / E8 目标扫描 / 12 份镜像盘点)。",
      "- Phase B: `scripts/_cfg.py` + `b01_cfg.py`(递归下降 CFG)+ `b02_types.py`(字段/比较/间接提取)。",
      "- Phase C: `scripts/c01_indirect.py`(PASS-A 线性扫描 + PASS-B 覆盖缺口扫描;union)+ `c02_focus.py`(跳表/近邻寄存器间接)。",
      "- Phase E: `scripts/e01_alt_images.py` / `e02_raw_copies.py`(跨镜像 IAT 可达性)。",
      "- Phase D/交付: `scripts/d01_tables.py` / `g_docs.py` / `_mk_index.py` / `_mk_corr.py`。","",
      "## 3. 局限(明示,不掩盖)", "",
      "1. 间接调用扫描只覆盖**已映射且存在于文件内**的节区 #0;缺失节区内的跳表**无法排除**。",
      "2. `0x87xxxx` 区扫描到 12 处 `[reg*4+disp]` 候选表基址,**全部证伪**为乘 4 索引位移(见 `05`);",
      "   这是**排除**性结论,不表示「不存在其它跳表」。",
      "3. 「无引用」一律记作**未发现**,**不**等价于「无调用者」。",
      "4. 类型域 `{0,1,21,22}` 只是**该字段在本函数内被显式比较**的值,不是协议完整类型枚举。",""]
c.w(os.path.join(T, "TEST_AND_VALIDATION_RESULTS.md"), "\n".join(L))
print("\n".join("%-45s %s %s" % (n, s, d) for (n,s,d) in checks))
print("\ndeliverable files hashed:", len(files))