"""Byte-level comparison of the 09-28 breakthrough run against the latest run,
to find what actually differs instead of guessing.
"""
import os
import re

RUNS = r"run_codol_001\runs"
BRK = os.path.join(RUNS, "IFS1_ELEVATED_20260928_183320")


def last_run():
    ds = [d for d in os.listdir(RUNS)
          if d.startswith("IFS1_") and "20261002" in d]
    ds.sort(key=lambda n: os.path.getmtime(os.path.join(RUNS, n)))
    return os.path.join(RUNS, ds[-1])


def args(d):
    lp = os.path.join(d, "launch.txt")
    if not os.path.exists(lp):
        return ""
    m = re.search(r"ARGS=(.*)", open(lp, encoding="utf-8",
                                    errors="replace").read())
    return m.group(1).strip() if m else ""


def events(d):
    f = os.path.join(d, "aboprobe.stdout")
    if not os.path.exists(f):
        return {}
    x = open(f, "rb").read().decode("gbk", "replace")
    out = {}
    for k in ["POKE_LOBBY_HOST", "POKE_LOBBY_PORT", "POKE_LOBBY_GLOBALS",
              "POKE_LOBBY_COMPLETE", "POKE_E57", "VSD_PROBE",
              "LOBBY_READY_ONLY", "LOBBY_5E8_READY", "LOBBY_ECHO_READY",
              "POST83_SAMPLE", "FAST_644", "CONN_D9", "CODEC_TRANSITION"]:
        out[k] = len(re.findall(r"," + k + ",", x))
    m = re.search(r"lifetime=([\d.]+)", x)
    out["_life"] = m.group(1) if m else "-"
    # the disconnect dialog text, if any
    dl = [l for l in x.splitlines() if "DLG_CHILD" in l and "Static" in l]
    out["_dlg"] = " | ".join(s.split("text=")[-1][:30] for s in dl)
    return out


a = BRK
b = last_run()

print("breakthrough :", os.path.basename(a))
print("latest       :", os.path.basename(b))
print()
print("=== ARGS ===")
print("  BRK:", args(a)[:600])
print()
print("  NOW:", args(b)[:600])

print()
print("=== events ===")
ea, eb = events(a), events(b)
keys = [k for k in ea if not k.startswith("_")]
print("  %-24s %-10s %-10s" % ("event", "BRK", "NOW"))
for k in keys:
    mark = "" if ea[k] == eb[k] else "   <-- DIFF"
    print("  %-24s %-10s %-10s%s" % (k, ea[k], eb[k], mark))
print()
print("  life   BRK=%s  NOW=%s" % (ea["_life"], eb["_life"]))
print("  dialog BRK=[%s]" % ea["_dlg"])
print("  dialog NOW=[%s]" % eb["_dlg"])
