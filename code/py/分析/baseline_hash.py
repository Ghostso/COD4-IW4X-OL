import hashlib, os, sys, json

sys.stdout.reconfigure(encoding="utf-8")

CLIENT_DIR = "COD OL"
OUT = "分析/00_baseline_module_hashes.csv"

FILES = [
    "codoMP_client_shipRetail.exe",
    "codoMP_client_shipRetailBase.dll",
    "GameDataPlatformServer.dll",
    "GDPImpl.dll",
    "GDPLoader.dll",
    "GDPCODOTrail.dll",
    "GameRpcs.dll",
    "TenProxy.dll",
    "TenRpcs.dll",
    "TenSLX.dll",
    "TenSp.dll",
    "TCJ.dll",
    "TerSafe.dll",
    "PolicyProbe.dll",
    "BugTrace.dll",
    "GbSpy.dll",
    "TCLS/Tenio/ProtocalHandler.dll",
]

os.makedirs("分析", exist_ok=True)

rows = []
for name in FILES:
    path = os.path.join(CLIENT_DIR, name)
    if not os.path.exists(path):
        rows.append((name, "MISSING", 0, ""))
        continue
    blob = open(path, "rb").read()
    rows.append((name, "present", len(blob), hashlib.sha256(blob).hexdigest()))

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("module|state|size|sha256\n")
    for name, state, size, sha in rows:
        fh.write("%s|%s|%d|%s\n" % (name, state, size, sha))

for name, state, size, sha in rows:
    print("%-42s %-8s %10d %s" % (name, state, size, sha[:24]))
print("written:", OUT)
