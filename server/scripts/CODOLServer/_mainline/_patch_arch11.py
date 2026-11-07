import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()
s = s.replace('STAMP = "20260928_2215"', 'STAMP = "20260928_2245"', 1)
old = '    "CODOLServer/logs/PLAIN/codec2_20260928_193323.jsonl",\n]'
new = ('    "CODOLServer/logs/PLAIN/codec2_20260928_193323.jsonl",\n'
       '    "CODOLServer/archive/CONFIRMED_20260928_2215/CHECKSUMS.txt",\n'
       '    "CODOLServer/_mainline/frida_lobby_codec.DO_NOT_RUN.py",\n]')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
