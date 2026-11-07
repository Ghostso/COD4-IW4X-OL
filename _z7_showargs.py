"""List argparse options of a script (avoids shell quoting problems)."""
import re
import sys

p = sys.argv[1]
d = open(p, encoding="utf-8", errors="replace").read()
for m in re.finditer(r'add_argument\(\s*"([^"]+)"([^\n]*)', d):
    print("   %-26s %s" % (m.group(1), m.group(2)[:90]))
