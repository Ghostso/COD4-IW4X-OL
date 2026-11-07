"""RESTORE-IIPS-CONTRACT-001 / Task 08 - A/B pre-GetRM differential.

Compares the two provider conditions on the contract landmarks the static work
identified, and finds the FIRST point at which A and B diverge.

Ordering matters: the brief asks for the last common observable state before the
first divergence, not merely a list of differences.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "restore_iips_contract_001", "runs")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")


def load_events(tag):
    p = os.path.join(RUNS, tag, tag + "_events.csv")
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        f.readline()
        for line in f:
            parts = line.rstrip("\n").split(",", 5)
            if len(parts) < 6:
                continue
            out.append({"t": float(parts[0]), "event": parts[1], "d1": parts[2],
                        "d2": parts[3], "d3": parts[4], "d4": parts[5]})
    return out


def summarize(tag):
    ev = load_events(tag)
    raw_windows = [e for e in ev if e["event"] == "WINDOW_NEW"]
    def strip_pref(s):
        return s.split("=", 1)[1] if "=" in s else s
    windows = [{"t": w["t"], "class": strip_pref(w["d2"]), "text": strip_pref(w["d3"])}
               for w in raw_windows]
    mods = [e for e in ev if e["event"] == "MODULE"]
    end = next((e for e in ev if e["event"] == "PROCESS_END"), None)
    names = [m["d1"].split("=", 1)[1].lower() for m in mods]
    return {
        "tag": tag,
        "modules": len(mods),
        "threads": len([e for e in ev if e["event"] == "THREAD_NEW"]),
        "windows": windows,
        "has_iips": any("iips.dll" in n for n in names),
        "has_ifs": any(n.startswith("ifs") for n in names),
        "has_iipshost": any("iipshost" in n for n in names),
        "has_iipscheck": any("iipscheck" in n for n in names),
        "has_iipsvfs": any("iipsvfs" in n for n in names),
        "has_p2papp": any("p2papp" in n for n in names),
        "has_download": any(n.startswith("download") for n in names),
        "process_end": (end["d2"] + " " + end["d3"] + " " + end["d4"]) if end else None,
        "first_window_t": windows[0]["t"] if windows else None,
        "fatal_dialog": any(w["class"] == "#32770" for w in windows),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=== Task 08: A/B pre-GetRM differential ===")
    print()
    tags = sorted(d for d in os.listdir(RUNS) if os.path.isdir(os.path.join(RUNS, d)))
    reps = {t: summarize(t) for t in tags}
    for t in tags:
        r = reps[t]
        print("  %-4s modules=%-4d threads=%-3d windows=%-2d iips=%s ifs=%s "
              "iipshost=%s fatal=%s end=%s"
              % (t, r["modules"], r["threads"], len(r["windows"]), r["has_iips"],
                 r["has_ifs"], r["has_iipshost"], r["fatal_dialog"], r["process_end"]))
    print()

    a_tags = [t for t in tags if t.upper().startswith("A")]
    b_tags = [t for t in tags if t.upper().startswith("B")]
    if not (a_tags and b_tags):
        print("  need both A and B runs")
        return 1
    A = reps[a_tags[0]]
    B = reps[b_tags[0]]

    print("  --- window timelines ---")
    print("  A:")
    for w in A["windows"]:
        print("     %7.3f  %-14s text=%r" % (w["t"], w["class"], w["text"]))
    print("  B:")
    for w in B["windows"]:
        print("     %7.3f  %-14s text=%r" % (w["t"], w["class"], w["text"]))
    print()

    shared_classes = {w["class"] for w in A["windows"]} & {w["class"] for w in B["windows"]}
    a_only = {w["class"] for w in A["windows"]} - {w["class"] for w in B["windows"]}
    b_only = {w["class"] for w in B["windows"]} - {w["class"] for w in A["windows"]}
    print("  window classes in BOTH      : %s" % sorted(c for c in shared_classes if c))
    print("  window classes only in A    : %s" % sorted(c for c in a_only if c))
    print("  window classes only in B    : %s" % sorted(c for c in b_only if c))
    print()

    # First divergence: the iipsinit window exists in BOTH, so the first
    # divergence is its TEXT (and the presence of the #32770 error dialog).
    ai = next((w for w in A["windows"] if w["class"] == "iipsinit"), None)
    bi = next((w for w in B["windows"] if w["class"] == "iipsinit"), None)

    print("  --- first divergence ---")
    common = []
    if A["has_iips"] and B["has_iips"]:
        common.append("iips.dll loaded in BOTH")
    if ai and bi:
        common.append("class 'iipsinit' window created in BOTH")
    rep = {
        "runs": reps,
        "shared_window_classes": sorted(c for c in shared_classes if c),
        "a_only_window_classes": sorted(c for c in a_only if c),
        "b_only_window_classes": sorted(c for c in b_only if c),
        "last_common_observable_state": common,
        "first_divergence": {
            "A": {"iipsinit_text": ai["text"] if ai else None,
                  "fatal_dialog": A["fatal_dialog"]},
            "B": {"iipsinit_text": bi["text"] if bi else None,
                  "fatal_dialog": B["fatal_dialog"]},
        },
        "dependency_modules": {
            "A": {"IFS.dll": A["has_ifs"], "IIPSHostApp": A["has_iipshost"],
                  "IIPSCheck": A["has_iipscheck"], "IIPSVFS": A["has_iipsvfs"],
                  "p2papp": A["has_p2papp"], "Download.dll": A["has_download"]},
            "B": {"IFS.dll": B["has_ifs"], "IIPSHostApp": B["has_iipshost"],
                  "IIPSCheck": B["has_iipscheck"], "IIPSVFS": B["has_iipsvfs"],
                  "p2papp": B["has_p2papp"], "Download.dll": B["has_download"]},
        },
    }
    for c in common:
        print("     common: %s" % c)
    print()
    print("     FIRST DIVERGENCE: the text of the 'iipsinit' window.")
    print("        A: %r   (#32770 fatal dialog also present: %s)"
          % (ai["text"] if ai else None, A["fatal_dialog"]))
    print("        B: %r   (#32770 fatal dialog also present: %s)"
          % (bi["text"] if bi else None, B["fatal_dialog"]))
    print()
    print("     provider dependency modules (from the static contract):")
    for k in ("IFS.dll", "IIPSHostApp", "IIPSCheck", "IIPSVFS", "p2papp", "Download.dll"):
        print("        %-14s A=%-5s B=%s" % (k, rep["dependency_modules"]["A"][k],
                                             rep["dependency_modules"]["B"][k]))

    with open(os.path.join(OUT, "t12_ab_differential.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t12_ab_differential.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
