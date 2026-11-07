import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
d = json.loads(Path("E:/CODOL_SANDBOX/RUN001/ol-mod-runtime-manifest.json").read_text(encoding="utf-8-sig"))
files = d.get("files", [])
print("=== plugin / exe entries ===")
for f in files:
    p = str(f.get("path", ""))
    if "Plugins/" in p or p.lower().endswith(".exe"):
        print(p, "|", f.get("sha256"), "|", f.get("size"))
print()
print("=== configuration / gameExecutable ===")
print(json.dumps(d.get("configuration"), ensure_ascii=False, indent=2)[:1200])
print("gameExecutable:", json.dumps(d.get("gameExecutable"), ensure_ascii=False)[:400])
print("project:", d.get("project"), "titleId:", d.get("titleId"), "arch:", d.get("architecture"))
