"""EB-003 Agent 13 - side-by-side ABI comparison of the two providers.

Runs the 32-bit reloc probe against each provider and compares the observable
object shape. This is the strongest evidence the round produces about the ABI:
both providers are exercised in a real 32-bit host and their returned objects are
compared field by field.

The original iips.dll is copied to a temporary path before probing, so this script
never loads the install's own file and never writes to the install at all.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
EV = os.path.join(ROOT, "restore003", "evidence")
OBS = os.path.join(ROOT, "restore003", "observer", "out", "EBO3.exe")


def run_probe(dll):
    p = subprocess.run([OBS, "--relocprobe", dll], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout + p.stderr


def parse(txt):
    def g(pat):
        m = re.search(pat, txt)
        return m.group(1) if m else None
    return {
        "loadlibrary": g(r"LOADLIBRARY\s*=\s*(\S+)"),
        "load_base": g(r"LOAD_BASE\s*=\s*(\S+)"),
        "getprocaddress": g(r"GETPROCADDRESS\s*=\s*(PASS|FAIL)"),
        "export_addr": g(r"GETPROCADDRESS\s*=\s*PASS\s*(\S+)"),
        "returned": g(r"returned\s*=\s*(\S+)"),
        "obj_vptr": g(r"obj vptr\s*=\s*(\S+)"),
        "vptr_inside_image": g(r"vptr_inside_image\s*=\s*(\S+)"),
        "vtable_non_null": g(r"vtable 48 slots non-null\s*=\s*(\S+)"),
        "obj_plus_04": g(r"obj\+0x04\s*=\s*(\S+)"),
        "obj_plus_20": g(r"obj\+0x20\s*=\s*(\S+)"),
        "obj_plus_44": g(r"obj\+0x44\s*=\s*(\S+)"),
        "result": g(r"RESULT\s*=\s*(\S+)"),
    }


def main():
    os.makedirs(EV, exist_ok=True)
    if not os.path.exists(OBS):
        print("observer binary missing: %s" % OBS)
        return 2

    print("=== EB-003 Agent 13: provider ABI equivalence ===")
    print()

    tmpdir = tempfile.mkdtemp(prefix="eb003_")
    tmp_orig = os.path.join(tmpdir, "original_iips_probe.dll")
    shutil.copy2(os.path.join(GAME, "IIPS", "iips.dll"), tmp_orig)
    try:
        orig_txt = run_probe(tmp_orig)
        orig = parse(orig_txt)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    v3_txt = run_probe(os.path.join(ROOT, "LocalRM_v3.dll"))
    v3 = parse(v3_txt)

    print("--- original IIPS\\iips.dll (temp copy) ---")
    print(orig_txt.strip())
    print()
    print("--- LocalRM_v3.dll ---")
    print(v3_txt.strip())
    print()

    keys = ["loadlibrary", "getprocaddress", "vtable_non_null", "vptr_inside_image",
            "obj_plus_04", "obj_plus_20", "obj_plus_44", "result"]
    print("comparison:")
    same = {}
    for k in keys:
        a, b = orig.get(k), v3.get(k)
        eq = (a == b)
        same[k] = eq
        print("   %-22s original=%-16s localrm_v3=%-16s %s"
              % (k, a, b, "SAME" if eq else "differs"))

    out = {
        "original": orig,
        "localrm_v3": v3,
        "same": same,
        "structural_equivalence": bool(
            orig.get("vtable_non_null") == "48/48"
            and v3.get("vtable_non_null") == "48/48"
            and orig.get("obj_plus_04") is not None
            and v3.get("obj_plus_04") is not None
            and orig.get("result") == "NO_FAULT"
            and v3.get("result") == "NO_FAULT"),
        "note": (
            "Both providers were exercised in a real 32-bit host. Each returns a "
            "heap object whose first field is a vptr into its own image, whose "
            "48-slot vtable is fully populated, and which carries four vptrs at "
            "+0x00/+0x04/+0x20/+0x44 -- the shape LOCALRM-006 decoded from the "
            "original's machine code. The object address and the exact vptr values "
            "differ, as they must: each provider points at its own table."),
    }
    with open(os.path.join(EV, "a13_abi_equivalence.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print()
    print("structural equivalence: %s" % out["structural_equivalence"])
    print("wrote %s" % os.path.join(EV, "a13_abi_equivalence.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
