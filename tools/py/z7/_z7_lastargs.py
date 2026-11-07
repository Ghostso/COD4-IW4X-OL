"""Show the exact switch values the last run was launched with."""
import glob
import os
import re
import sys

which = sys.argv[1] if len(sys.argv) > 1 else None
RUNS = r"run_codol_001\runs"

ds = sorted(glob.glob(os.path.join(RUNS, "IFS1_*")), key=os.path.getmtime)
d = which or ds[-1]
lp = os.path.join(d, "launch.txt")
print("run:", os.path.basename(d))
if not os.path.exists(lp):
    print("no launch.txt")
    raise SystemExit(0)

txt = open(lp, encoding="utf-8", errors="replace").read()
m = re.search(r"ARGS=(.*)", txt)
args = m.group(1).strip() if m else ""

for k in ["--poke-e57", "--post83-trace", "--post83-seconds",
          "--handshake-ready-file", "--handshake-echo-file",
          "--poke-lobby-host", "--poke-lobby-port", "--poke-lobby-globals",
          "--lobby-ready-only", "--abort-on-cfg0", "--compat4",
          "--patch-85-pass", "--poke-lobby-644", "--follow-85"]:
    pat = re.escape(k) + r'(?:\s+("[^"]*"|\S+))?'
    mm = re.search(pat, args)
    val = mm.group(1) if (mm and mm.group(1)) else "(not passed)"
    print("   %-26s %s" % (k, val))
