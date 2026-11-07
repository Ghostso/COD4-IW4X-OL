"""Summarize the runtime gate/state trace (ASCII only)."""
import collections
import json
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "_dyn_game_out3", "state.jsonl")

rows = []
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    o = json.loads(line)
    if "ev" in o:
        print("event:", o)
        continue
    rows.append(o)

print("samples = %d" % len(rows))
if not rows:
    sys.exit(0)

for key in ("flag_61f", "u5CC", "uA50", "dwLobby_state", "state_prev"):
    if key in rows[0]:
        c = collections.Counter(r.get(key) for r in rows)
        print("%-14s -> %s" % (key, dict(c)))

print("--- state transitions ---")
prev = None
for r in rows:
    k = (r.get("dwLobby_state"), r.get("state_prev"), r.get("flag_61f"), r.get("u5CC"))
    if k != prev:
        print("  t=%8.2f  dwLobby_state=%-4s state_prev=%-4s flag_61f=%-2s u5CC=%s"
              % (r.get("t", -1), r.get("dwLobby_state"), r.get("state_prev"),
                 r.get("flag_61f"), r.get("u5CC")))
        prev = k

print("--- code_7EF210 variants ---")
c = collections.Counter(r.get("code_7EF210") for r in rows)
for k, v in c.items():
    print("  x%-4d %s" % (v, k))
