import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

s = s.replace('STAMP = "20260928_2315"', 'STAMP = "20260928_2359"', 1)

# drop references to archives that were reclaimed for disk space
root = os.path.join(r"D:\BaiduNetdiskDownload\使命召唤OL", "CODOLServer", "archive")
keep = set(os.listdir(root)) if os.path.isdir(root) else set()
out = []
for line in s.splitlines(True):
    m = re.search(r'"CODOLServer/archive/(CONFIRMED_\d+_\d+)/CHECKSUMS\.txt"', line)
    if m and m.group(1) not in keep:
        print("drop stale ref:", m.group(1))
        continue
    out.append(line)
s = "".join(out)

if '"CODOLServer/LOBBY_BREAKTHROUGH_REPRO_20260928.md"' not in s:
    old = '    "CODOLServer/_mainline/_ba0ff0.txt",\n]'
    new = ('    "CODOLServer/_mainline/_ba0ff0.txt",\n'
           '    "CODOLServer/LOBBY_BREAKTHROUGH_REPRO_20260928.md",\n'
           '    "CODOLServer/logs/PLAIN/h81_20260928_202316.jsonl",\n]')
    if s.count(old) == 1:
        s = s.replace(old, new, 1)
        print("added new refs")

open(p, "w", encoding="utf-8").write(s)
print("ok")
