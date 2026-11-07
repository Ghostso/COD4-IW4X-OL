"""List every conclusion I made about the 0x87 gate, in order, so the
back-and-forth is visible instead of hidden in 275 KB of prose."""
import io
import re

MAN = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
src = io.open(MAN, encoding="utf-8", errors="replace").read()
lines = src.splitlines()

print("=== every line that states something about the 0x87 gate ===")
pat = re.compile(r"0x87|0BA3AE6|BA3AE6|cmp\s+cl")
for i, l in enumerate(lines):
    if pat.search(l):
        t = l.strip()
        if not t or t.startswith("//"):
            continue
        print("%6d| %s" % (i + 1, t[:150]))
