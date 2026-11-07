import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()
s = s.replace('STAMP = "20260928_2359"', 'STAMP = "20260929_0100"', 1)
old = '    "CODOLServer/_mainline/_ba0ff0.txt",\n]'
new = ('    "CODOLServer/_mainline/_ba0ff0.txt",\n'
       '    "CODOLServer/HANDOFF_20260928_LOBBY_PROTOCOL.md",\n'
       '    "CODOLServer/archive/CONFIRMED_20260928_2359/CHECKSUMS.txt",\n]')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
