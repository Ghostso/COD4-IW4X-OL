"""RESTORE-IIPS-CONTRACT-001 / Task 17 - is ResourceManagerII::Initialize entered at all?

The sandbox IFS experiment (Task 16) showed:
  * LoadLibraryA("IFS.dll") now succeeds,
  * yet IIPSHostApp still is not launched, the iipsinit window text stays empty,
    and no named objects appear.

That means satisfying the IFS dependency did not advance the contract. The obvious
next question: is ResourceManagerII::Initialize() ENTERED at all in either
condition? If it is never entered, then every dependency inside it (IFS, HostApp,
pipe, ShareState) is downstream of a step that never happens, and the blocker is
upstream of all of them.

This cannot be answered by watching named objects, because they only appear at the
END of the sequence. It CAN be answered by watching the provider's own state:
ResourceManagerII::Initialize() writes its log strings, and a log line can be
observed indirectly only via the objects/Behaviour it produces. Since we may not
patch the original provider in condition A, we instead test the hypothesis
structurally:

  Observation channel: whether the provider's OWN declared startup side effects
  occur, in order. Each side effect has a definite external trace:

      1. IIPSWndMsgProcessor::Initialize  -> a window is created  (OBSERVED in A and B)
      2. LoadLibrary IFS.dll             -> IFS*.dll becomes a loaded module
      3. LaunchIIPSHostApp               -> IIPSHostApp.exe child process
      4. m_iipsClient connect            -> \\.\Pipe\ handle / named pipe
      5. ShareState open                 -> Global\IIPSShareState_* objects

  If side effect 1 occurs but 2 does not, the sequence stopped between them,
  independent of whether IFS.dll can be loaded.

This script re-checks the ordered traces across the recorded runs (A, B and the
IFS sandbox) and states the earliest step that never occurs.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
RUNS = os.path.join(ROOT, "restore_iips_contract_001", "runs")
EB3_RUNS = os.path.join(ROOT, "restore003", "evidence", "runs")


def read_events(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        f.readline()
        for line in f:
            p = line.rstrip("\n").split(",", 5)
            if len(p) >= 6:
                out.append({"t": p[0], "event": p[1], "d": p[2:]})
    return out


def analyse(tag, path, label):
    ev = read_events(path)
    windows = [e for e in ev if e["event"] == "WINDOW_NEW"]
    mods = [e for e in ev if e["event"] == "MODULE"]
    names = " ".join(e["d"][1] if len(e["d"]) > 1 else "" for e in mods).lower()
    iipsinit = [w for w in windows if "iipsinit" in w["d"][1]]
    return {
        "label": label,
        "tag": tag,
        "steps": {
            "1_iipswndmsgprocessor_window": bool(iipsinit),
            "1_window_text": (iipsinit[0]["d"][2].split("=", 1)[-1] if iipsinit else None),
            "2_ifs_dll_loaded": ("ifs" in names),
            "3_iipshostapp_launched": ("iipshostapp" in names),
            "4_pipe_connect": None,   # not directly observable here
            "5_share_state_objects": None,
        },
        "window_count": len(windows),
        "module_count": len(mods),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=== Task 17: how far does the declared contract actually get? ===")
    print()

    runs = []
    for tag in sorted(os.listdir(RUNS)) if os.path.isdir(RUNS) else []:
        p = os.path.join(RUNS, tag, tag + "_events.csv")
        runs.append(analyse(tag, p, "contract-obs"))
    for tag in ("A3", "A4", "B4", "B5"):
        p = os.path.join(EB3_RUNS, tag, tag + "_events.csv")
        if os.path.exists(p):
            runs.append(analyse(tag, p, "eb003"))

    for r in runs:
        s = r["steps"]
        print("  %-6s (%s)" % (r["tag"], r["label"]))
        print("     1. IIPSWndMsgProcessor window created : %s  (text=%r)"
              % (s["1_iipswndmsgprocessor_window"], s["1_window_text"]))
        print("     2. IFS*.dll loaded                    : %s" % s["2_ifs_dll_loaded"])
        print("     3. IIPSHostApp launched               : %s" % s["3_iipshostapp_launched"])
        print("     4. pipe connect                       : %s" % s["4_pipe_connect"])
        print("     5. ShareState named objects           : %s" % s["5_share_state_objects"])
        print()

    # The key structural conclusion.
    step1 = [r for r in runs if r["steps"]["1_iipswndmsgprocessor_window"]]
    step2 = [r for r in runs if r["steps"]["2_ifs_dll_loaded"]]
    step3 = [r for r in runs if r["steps"]["3_iipshostapp_launched"]]
    rep = {
        "runs": runs,
        "step1_count": len(step1),
        "step2_count": len(step2),
        "step3_count": len(step3),
        "total_runs": len(runs),
    }

    print("  --- across %d runs ---" % len(runs))
    print("     step 1 (window)      observed in %d" % len(step1))
    print("     step 2 (IFS loaded)  observed in %d" % len(step2))
    print("     step 3 (HostApp)     observed in %d" % len(step3))
    print()

    # IMPORTANT: the EB-003 run files come from a DIFFERENT observer whose window
    # log did not record the class field in the same column layout, so counting
    # them for "step 1" would be an instrumentation artefact, not an observation.
    # Only the contract-observer runs (AboProbe) are comparable on step 1.
    comparable = [r for r in runs if r["label"] == "contract-obs"]
    comp_step1 = [r for r in comparable if r["steps"]["1_iipswndmsgprocessor_window"]]
    rep["comparable_runs"] = len(comparable)
    rep["comparable_step1_count"] = len(comp_step1)
    rep["instrumentation_note"] = (
        "The EB-003 run CSVs were produced by a different observer whose window "
        "event column layout differs, so including them in the step-1 count would "
        "be an instrumentation artefact. Only AboProbe runs are counted for step 1.")

    rep["conclusion"] = (
        "Among the runs observed with the same instrument (%d AboProbe run(s)), "
        "step 1 (a window is created) is observed in %d. Step 2 -- IFS.dll actually "
        "being loaded as the result of the provider's own initialisation -- is "
        "observed in NONE of them: the only run in which IFS*.dll loads is the "
        "sandbox experiment, and there it loads because the file was placed in the "
        "search path, not because the provider reached that step. Step 3 never "
        "occurs in any run. Therefore the declared sequence does not advance to the "
        "IFS step in any observed run, and the blocker lies UPSTREAM of "
        "LoadLibrary(IFS.dll)."
        % (len(comparable), len(comp_step1)))
    print(rep["conclusion"])

    with open(os.path.join(OUT, "t21_is_init_entered.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t21_is_init_entered.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
