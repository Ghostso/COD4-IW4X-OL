import os
import re

base = r"COD OL\IIPS\TenioLog"
names = sorted(
    [n for n in os.listdir(base) if n.startswith("20260925_")],
    key=lambda n: os.path.getmtime(os.path.join(base, n)),
)
if not names:
    raise SystemExit("no 20260925 logs")

path = os.path.join(base, names[-1])
blob = open(path, "rb").read()
for enc in ("utf-8", "gbk", "utf-16"):
    try:
        text = blob.decode(enc)
        break
    except UnicodeDecodeError:
        continue
else:
    raise SystemExit("undecodable")

print("FILE %s (%d bytes, decoded %s)" % (path, len(blob), enc))
lines = text.splitlines()
print("lines=%d" % len(lines))
for line in lines:
    low = line.lower()
    if any(k in low for k in (
            "error", "fail", "cannot", "can't", "pipe", "hostpid",
            "polic", "tpfui", "iipsres", "loadimage", "creator",
            "component", "start", "listen")):
        print(line)
