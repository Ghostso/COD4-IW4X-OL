import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
j=json.loads(Path("scripts/_tmp/ca8xxx_dataflow_closure.json").read_text(encoding="utf-8"))
print([(hex(e["rva"]),e["name"].encode("latin1").hex()) for e in j["exports"]])
