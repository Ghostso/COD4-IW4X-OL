import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
j=json.loads(Path("scripts/_tmp/ca8xxx_dataflow_closure.json").read_text(encoding="utf-8"))
print([(hex(e["rva"]),repr(e["name"])) for e in j["exports"]])
print("cfg",j["cfg_instruction_count"])
print([r for r in j["refs"] if r["rva"] in (0x3667a,0x36691)])
