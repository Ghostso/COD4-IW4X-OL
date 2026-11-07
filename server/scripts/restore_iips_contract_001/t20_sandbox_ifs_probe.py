"""RESTORE-IIPS-CONTRACT-001 / Task 16 - single-factor sandbox experiment.

Hypothesis: the init sequence cannot pass the IFS step because LoadLibrary("IFS.dll")
cannot resolve. If that is the immediate blocker, then exposing the existing
IFS2.dll under the name IFS.dll INSIDE THE SANDBOX (and only there) should let the
contract advance past the IFS step.

Safety: this modifies ONLY restore_iips_contract_001/sandbox_ifs. The real install
is never written; its SHA256 is re-verified at the end.

This is a diagnosis experiment, not a repair: the sandbox is built fresh, the one
file is added, and the same observer is run in the same way as condition B.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

# The console here is GBK; decoding subprocess output as GBK loses data and
# printing non-GBK characters raises. Force UTF-8 with replacement so the run is
# never aborted by a console-encoding problem.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def safe(s):
    return s.encode("utf-8", "replace").decode("utf-8", "replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
SBX_SRC = os.path.join(ROOT, "restore003", "sandbox_B")
SBX = os.path.join(ROOT, "restore_iips_contract_001", "sandbox_ifs")
OBS = os.path.join(ROOT, "restore_iips_contract_001", "observer2", "out", "AboProbe.exe")

ORIGINAL_SHA = "E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 16: sandbox IFS.dll single-factor experiment ===")
    print()

    if not os.path.isdir(SBX_SRC):
        print("  sandbox_B missing; rebuild it first with restore003/mk_sandbox.ps1")
        return 1

    # Rebuild the experiment sandbox with the same junction/hardlink strategy the
    # round's own mk_sandbox.ps1 uses: copying is wrong here because IIPS\ holds
    # junctions back into the real install (copytree cannot traverse them).
    if os.path.isdir(SBX):
        resolved = os.path.realpath(SBX)
        base = os.path.realpath(os.path.join(ROOT, "restore_iips_contract_001"))
        if not resolved.startswith(base):
            print("  refusing to remove %s (outside round dir)" % resolved)
            return 2
        # Remove only our own sandbox dir; use the shell so junctions are not
        # followed destructively.
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", SBX],
                       capture_output=True, text=True)
    os.makedirs(os.path.join(SBX, "IIPS"), exist_ok=True)

    src_game = GAME
    # Junction every top-level entry of the real game dir, except IIPS.
    for e in os.listdir(src_game):
        if e == "IIPS":
            continue
        s = os.path.join(src_game, e)
        d = os.path.join(SBX, e)
        if os.path.isdir(s):
            subprocess.run(["cmd", "/c", "mklink", "/J", d, s],
                           capture_output=True, text=True)
        else:
            subprocess.run(["cmd", "/c", "mklink", "/H", d, s],
                           capture_output=True, text=True)

    # IIPS: junction subdirectories, copy files, and substitute the provider with
    # LocalRM_v3 (condition B), exactly as restore003/mk_sandbox.ps1 does.
    src_iips = os.path.join(src_game, "IIPS")
    dst_iips = os.path.join(SBX, "IIPS")
    v3 = os.path.join(ROOT, "LocalRM_v3.dll")
    for e in os.listdir(src_iips):
        s = os.path.join(src_iips, e)
        d = os.path.join(dst_iips, e)
        if os.path.isdir(s):
            subprocess.run(["cmd", "/c", "mklink", "/J", d, s],
                           capture_output=True, text=True)
        else:
            if e.lower() == "iips.dll":
                continue
            shutil.copy2(s, d)
    shutil.copy2(v3, os.path.join(dst_iips, "iips.dll"))
    print("  sandbox built: %s" % SBX)

    src = os.path.join(GAME, "IIPS", "IFS2.dll")
    if not os.path.exists(src):
        print("  IFS2.dll missing in install")
        return 3
    dst = os.path.join(SBX, "IIPS", "IFS.dll")
    shutil.copy2(src, dst)
    rep["added_file"] = {"name": "IIPS\\IFS.dll", "source": "COD OL\\IIPS\\IFS2.dll",
                         "size": os.path.getsize(dst), "sha256": sha(dst)}
    print("  added IIPS\\IFS.dll (copy of IFS2.dll, %d bytes)" % os.path.getsize(dst))

    # Confirm the name now resolves in the sandbox IIPS directory.
    r = subprocess.run([OBS, "--nameprobe", os.path.join(SBX, "IIPS")],
                       capture_output=True)
    np_out = r.stdout.decode("utf-8", "replace")
    rep["nameprobe_output"] = np_out
    print()
    print("  name resolution in the experiment sandbox:")
    for line in np_out.splitlines():
        print("     " + safe(line))

    # Run the observer against the sandbox.
    print()
    print("  running observer against the experiment sandbox (60s)...")
    r2 = subprocess.run([OBS, "--mode", "B", "--tag", "IFS1", "--duration", "60",
                         "--sandbox", SBX],
                        capture_output=True, timeout=180)
    run_out = r2.stdout.decode("utf-8", "replace")
    rep["run_output_tail"] = "\n".join(run_out.splitlines()[-30:])
    for line in run_out.splitlines():
        if any(k in line for k in ("WINDOW_NEW", "PROCESS_END", "RUN_START")):
            print("     " + safe(line))

    # Analyse the run's event file.
    ev = os.path.join(ROOT, "restore_iips_contract_001", "runs", "IFS1",
                      "IFS1_events.csv")
    summary = os.path.join(ROOT, "restore_iips_contract_001", "runs", "IFS1",
                           "IFS1_summary.txt")
    res = {"events_file": ev, "windows": [], "modules_interesting": [],
           "process_end": None, "ifs_loaded": False, "iipshost": False}
    if os.path.exists(ev):
        with open(ev, encoding="utf-8") as f:
            for line in f:
                if ",WINDOW_NEW," in line:
                    res["windows"].append(line.strip())
                if ",PROCESS_END," in line:
                    res["process_end"] = line.strip()
                if ",MODULE," in line and ("IFS" in line or "iips" in line.lower()):
                    res["modules_interesting"].append(line.strip())
                    if "IFS" in line or "ifs" in line:
                        res["ifs_loaded"] = True
                if ",MODULE," in line and "IIPSHostApp" in line:
                    res["iipshost"] = True

    print()
    print("  --- experiment result ---")
    print("     IFS*.dll loaded        : %s" % res["ifs_loaded"])
    print("     IIPSHostApp loaded     : %s" % res["iipshost"])
    print("     windows                : %d" % len(res["windows"]))
    for w in res["windows"]:
        print("        %s" % w)
    print("     process_end            : %s" % res["process_end"])

    # Re-verify the real install is untouched.
    rep["original_iips_sha_after"] = sha(os.path.join(GAME, "IIPS", "iips.dll"))
    rep["original_iips_unchanged"] = (rep["original_iips_sha_after"] == ORIGINAL_SHA)
    print()
    print("     original iips.dll unchanged: %s" % rep["original_iips_unchanged"])

    rep["result_summary"] = {
        "ifs_now_loadable_in_sandbox": res["ifs_loaded"],
        "iipshost_started": res["iipshost"],
        "window_count": len(res["windows"]),
        "process_end": res["process_end"],
    }
    with open(os.path.join(OUT, "t20_sandbox_ifs.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t20_sandbox_ifs.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
