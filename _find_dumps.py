from pathlib import Path
for p in Path('.').rglob('*'):
 try:
  if p.is_file() and (p.suffix.lower() in ('.dmp','.mdmp','.dump','.bin','.mem') or 'dump' in p.name.lower()):
   print(p.stat().st_size,p)
 except OSError: pass
