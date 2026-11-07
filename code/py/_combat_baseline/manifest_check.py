import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
p = Path("E:/CODOL_SANDBOX/RUN001/ol-mod-runtime-manifest.json")
d = json.loads(p.read_text(encoding="utf-8-sig"))
print("top-level keys:", list(d.keys())[:20])
files = d.get("files") or d.get("Files") or []
print("file entries:", len(files))
hits = [f for f in files if "game" in str(f.get("path","")).lower() or "ayria" in str(f.get("path","")).lower() or "localnet" in str(f.get("path","")).lower()]
for f in hits[:20]:
    print(json.dumps({k: f.get(k) for k in ("path","sha256","size","length","version")}, ensure_ascii=False))
meta = {k: v for k, v in d.items() if k != "files"}
print("meta:", json.dumps(meta, ensure_ascii=False)[:1500])
