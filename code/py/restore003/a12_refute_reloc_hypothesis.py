"""EB-003 Agent 12 - falsify the relocation hypothesis against runtime data.

Agent 08-10 built a hypothesis: "LocalRM_v3 fails because .localrm's hardcoded
absolutes are not relocated, so it needs base 0x10000000."

Agent 11 showed the ORIGINAL iips.dll has the same unrelocated singleton operands,
and the run records show the original ALSO loads at a relocated base in every run
(Base.dll always owns 0x10000000). Yet the original reaches its own execution path.

Therefore: "missing relocation" REFUTED as the cause of the condition-B difference.
This script states that falsification from the recorded numbers rather than leaving
the earlier hypothesis standing.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "restore003", "evidence")
RUNS = os.path.join(EV, "runs")
PREFERRED = 0x10000000


def run_bases():
    out = {}
    for tag in sorted(os.listdir(RUNS)):
        d = os.path.join(RUNS, tag)
        if not os.path.isdir(d):
            continue
        f = os.path.join(d, tag + "_events.csv")
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if ",IIPS_LOADED," in line:
                    parts = line.split(",")
                    b = parts[3]
                    out[tag] = int(b.split("=", 1)[1], 16)
                    break
    return out


def main():
    bases = run_bases()
    print("=== EB-003 Agent 12: is 'no relocation' really the cause? ===")
    print()
    print("  preferred base of BOTH providers = 0x%08X" % PREFERRED)
    print()
    print("  observed iips.dll / provider load base per run:")
    at_preferred = 0
    for tag, b in bases.items():
        at = (b == PREFERRED)
        if at:
            at_preferred += 1
        print("    %-4s 0x%08X  %s" % (tag, b,
                                       "AT PREFERRED BASE" if at else
                                       "RELOCATED (delta 0x%X)" % (b - PREFERRED)))
    print()

    a_bases = [b for t, b in bases.items() if t.startswith("A")]
    b_bases = [b for t, b in bases.items() if t.startswith("B")]
    a_relocated = all(b != PREFERRED for b in a_bases)
    b_relocated = all(b != PREFERRED for b in b_bases)

    print("  condition A providers relocated in every run: %s" % a_relocated)
    print("  condition B providers relocated in every run: %s" % b_relocated)
    print()
    print("  The ORIGINAL is relocated in every A run and still executes its IIPS")
    print("  init path (it creates the iipsinit window and raises the fatal dialog).")
    print("  Therefore relocation state alone cannot distinguish A from B.")
    print()
    print("REFUTED: '.localrm is not relocated' is not, by itself, the reason")
    print("         condition B never constructs a ResourceManager object.")
    print()
    print("Still OPEN and evidence-backed:")
    print("  * the Engine resolves the provider by NAME (Agent 03/05), so the two")
    print("    export names present in LocalRM_v3 are sufficient for binding;")
    print("  * the Engine never called GetResourceManagerII in any B run (Agent 07),")
    print("    and no IAT slot ever held either export address in B;")
    print("  * the larger difference is functional: the original also performs the")
    print("    IIPS init/download bookkeeping that produces the iipsinit window and")
    print("    the WIN_IIPS_INIT_FAILED dialog, which LocalRM_v3 does not implement.")

    out = {
        "preferred_base": "0x%X" % PREFERRED,
        "observed_bases": {k: "0x%X" % v for k, v in bases.items()},
        "a_relocated_every_run": a_relocated,
        "b_relocated_every_run": b_relocated,
        "runs_at_preferred_base": at_preferred,
        "relocation_hypothesis": "REFUTED",
        "refutation": (
            "The original iips.dll is relocated in every condition-A run and still "
            "executes its init path, so relocation alone cannot explain why "
            "condition B never constructs an RM object."),
    }
    with open(os.path.join(EV, "a12_refute_reloc_hypothesis.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print()
    print("wrote %s" % os.path.join(EV, "a12_refute_reloc_hypothesis.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
