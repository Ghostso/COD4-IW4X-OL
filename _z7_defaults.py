"""Confirm every switch I added today is inert by default, so the driver does
not need restoring -- only the observer binary did."""
import re

P = r"CODOLServer\_mainline\_e57a5c_experiment.py"
d = open(P, encoding="utf-8", errors="replace").read()

pairs = [
    (r'--plain-port", type=int, default=(\d+)', "plain-port"),
    (r'--poke-port", type=int, default=(\d+)', "poke-port"),
    (r'--token", default="([^"]+)"', "token"),
    (r'--patch-delay", type=float, default=([\d.]+)', "patch-delay"),
    (r'--serve-delay", type=float, default=([\d.]+)', "serve-delay"),
]
print("=== current defaults (must match the pre-document values) ===")
for pat, name in pairs:
    m = re.search(pat, d)
    print("   %-14s %s" % (name, m.group(1) if m else "?"))

print()
print("=== switches added today: all must default to OFF ===")
for k in ["--compat4", "--no-poke", "--patch-87-gate", "--patch-85-srcbase",
          "--poke-lobby-644"]:
    m = re.search(re.escape(k) + r'[^\n]*action="store_true"', d)
    print("   %-20s %s" % (k, "store_true -> OFF unless passed" if m else "?"))
