from pathlib import Path
import re
d=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TenProxy.dll").read_bytes()
terms=[]
for m in re.finditer(rb"[\x20-\x7e]{4,}",d):
 s=m.group()
 if any(x.lower() in s.lower() for x in [b"TCLS",b"SHARED",b"MAPPING",b"MEMORY",b"TENPROXY",b"TAS",b"TP3"]):
  terms.append((m.start(),s))
for o,s in terms: print(hex(o),s)
