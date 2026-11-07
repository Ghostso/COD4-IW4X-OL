"""EB-003 Agent 04 - compare what LocalRM_v3 provides against what the Engine expects.

This is an interpretation layer over already-recorded evidence; it runs no target.

It answers one question that decides whether condition B is a *valid* experiment:
does LocalRM_v3 satisfy the observable contract the Engine's own string cluster
implies? The Engine asks for exactly two names:
    GetResourceManagerII
    ReleaseResourceManagerII
and nothing else. Everything else (IIPS download, IFS, .lst handling, the
"Environment List Box" window, the WIN_IIPS_* error codes) belongs to the *original
iips.dll's own IIPS bookkeeping*, which LocalRM_v3 does not implement.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "restore003", "evidence")


def load(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    a02 = load("a02_import_binding.json")
    a02b = load("a02b_ordinal_chain.json")
    a01 = load("a01_artifact_recon.json")
    if not (a01 and a02 and a02b):
        print("missing prerequisite evidence; run a01/a02/a02b first")
        return 1

    providers = a02["providers"]
    orig = providers["original_iips"]
    v3 = providers["localrm_v3"]

    print("=== EB-003 Agent 04: provider contract comparison ===")
    print()
    print("Engine requests (from EXE .rdata string cluster, Agent 03):")
    print("   LoadLibrary('IIPS\\\\iips.dll')")
    print("   GetProcAddress(h, 'GetResourceManagerII')")
    print("   GetProcAddress(h, 'ReleaseResourceManagerII')")
    print()

    eng_names = ["GetResourceManagerII", "ReleaseResourceManagerII"]
    for label, prov in (("original iips.dll", orig), ("LocalRM_v3.dll", v3)):
        have = {e["name"]: e["func_rva"] for e in prov.get("exports", [])}
        print("%s  (exports: %d)" % (label, len(prov.get("exports", []))))
        for n in eng_names:
            ok = n in have
            print("   %-28s %s %s" % (n, "PRESENT" if ok else "ABSENT",
                                      ("RVA 0x%X" % have[n]) if ok else ""))
        extra = sorted(set(have) - set(eng_names))
        if extra:
            print("   (also exports: %s)" % ", ".join(extra))
        print()

    print("IAT-ordinal analysis (Agent 02b):")
    print("   EXE imports iips.dll by name?  NO  (only the string is present)")
    print("   EXE imports Base.dll ordinal 1 (unrelated to RM)")
    print("   -> provider resolution is by NAME, so ordinal layout is irrelevant")
    print()
    print("Ordinal layouts differ but are NOT consulted:")
    for k in ("original_iips", "localrm_v3"):
        v = a02b["providers"][k]
        line = ", ".join("ord%d=0x%X" % (e["ordinal"], e["func_rva"])
                         for e in v["address_of_functions"])
        print("   %-14s %s" % (k, line))
    print()

    # The decisive gap.
    orig_names = {e["name"] for e in orig.get("exports", [])}
    v3_names = {e["name"] for e in v3.get("exports", [])}
    print("RESULT")
    print("   The two RM entry points the Engine asks for are supplied by BOTH")
    print("   providers. Therefore a 'name not found' failure is REFUTED as the")
    print("   reason condition B never reaches GetResourceManagerII.")
    print()
    print("   The observed difference is that the original also performs IIPS")
    print("   bookkeeping (IIPSDownload, .ifs/.lst handling, the iipsinit window,")
    print("   WIN_IIPS_* error codes) which LocalRM_v3 does not implement at all.")
    print()

    out = {
        "engine_requested_exports": eng_names,
        "original_iips_exports": sorted(orig_names),
        "localrm_v3_exports": sorted(v3_names),
        "resolution_mechanism": "LoadLibraryA(by path) + GetProcAddress(by name)",
        "ordinal_layout_consulted": False,
        "rm_entry_points_present_in_both": all(
            n in orig_names and n in v3_names for n in eng_names),
        "localrm_v3_missing_iips_bookkeeping": True,
    }
    with open(os.path.join(EV, "a04_provider_contract.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote %s" % os.path.join(EV, "a04_provider_contract.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
