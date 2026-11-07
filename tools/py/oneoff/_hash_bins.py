import hashlib
from pathlib import Path
for p in Path('.').rglob('*'):
 if p.is_file() and p.name.lower() in ('codomp_client_shipretail.exe','codomp_client_shipretailbase.dll'):
  h=hashlib.sha256(p.read_bytes()).hexdigest()
  print(h,p.stat().st_size,p)
