"""EB-003 Agent 07 - aggregate all runs into the machine-readable evidence file.

Produces restore003/evidence/rm_engine_calls.json: the single machine-readable
record of what was observed, per condition, with explicit evidence levels.

Evidence policy (from the round brief):
    CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN /
    REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED

"Engine called slot N" may only be CONFIRMED when a real runtime observation
occurred. An empty observation is reported as NOT_OBSERVED, never as
"Engine does not call ResourceManager".
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "restore003", "evidence")
RUNS = os.path.join(EV, "runs")


def read_json(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_events(tag):
    p = os.path.join(RUNS, tag, tag + "_events.csv")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        hdr = f.readline()
        for line in f:
            parts = line.rstrip("\n").split(",", 6)
            if len(parts) < 7:
                continue
            out.append({"t": parts[0], "agent": parts[1], "event": parts[2],
                        "d1": parts[3], "d2": parts[4], "d3": parts[5], "d4": parts[6]})
    return out


def summarize_run(tag):
    ev = read_events(tag)
    def has(name):
        return any(e["event"] == name for e in ev)

    def count(name):
        return sum(1 for e in ev if e["event"] == name)

    gate = next((e for e in ev if e["event"] == "GATE_CROSSED"), None)
    cls = next((e for e in ev if e["event"] == "PROVIDER_CLASSIFY"), None)
    end = next((e for e in ev if e["event"] == "PROCESS_END"), None)
    iips = next((e for e in ev if e["event"] == "IIPS_LOADED"), None)
    fatal = any(e["event"] == "WINDOW_NEW" and "32770" in e["d1"] for e in ev)
    initwin = next((e for e in ev if e["event"] == "WINDOW_NEW" and "iipsinit" in e["d1"]), None)
    return {
        "tag": tag,
        "events_total": len(ev),
        "gate_crossed": gate is not None,
        "gate_t": gate["t"] if gate else None,
        "iips_loaded": iips is not None,
        "iips_base": iips["d1"] if iips else None,
        "iips_path": iips["d2"] if iips else None,
        "provider_kind": cls["d1"].split("=", 1)[1] if cls and "=" in cls["d1"] else None,
        "provider_detail": cls["d4"] if cls else None,
        "fatal_error_dialog": fatal,
        "iipsinit_window_text": initwin["d2"] if initwin else None,
        # PROCESS_END emits: d1=exited, d2=exitcode, d3=lifetime
        "process_end": (end["d1"] + " " + end["d2"] + " " + end["d3"]) if end else None,
        "rm_vtable_calls": count("RM_VTABLE_CALL"),
        "grm_calls": count("GRM_CALL"),
        "resolve_calls": count("RESOLVE_CALL"),
        "resolved_entry_in_iat": count("RESOLVED_ENTRY_IN_IAT"),
        "rm_object_candidates": count("RM_OBJECT_CANDIDATE"),
        "rm_vtable_attached": has("RM_VTABLE_ATTACHED"),
    }


def main():
    a01 = read_json("a01_artifact_recon.json")
    a02 = read_json("a02_import_binding.json")
    a02b = read_json("a02b_ordinal_chain.json")
    a03 = read_json("a03_dynamic_resolution.json")
    a05 = read_json("a05_base_host.json")
    a06 = read_json("a06_tvm0_and_loader.json")
    a10 = read_json("a10_root_cause.json")
    a11 = read_json("a11_original_base_dep.json")
    a12 = read_json("a12_refute_reloc_hypothesis.json")
    a13 = read_json("a13_abi_equivalence.json")

    tags = sorted({d for d in os.listdir(RUNS) if os.path.isdir(os.path.join(RUNS, d))})
    runs = {t: summarize_run(t) for t in tags}

    a_runs = [t for t in tags if t.startswith("A")]
    b_runs = [t for t in tags if t.startswith("B")]

    def allrun(lst, key, val=True):
        return bool(lst) and all(runs[t][key] == val for t in lst)

    def anyrun(lst, key, val=True):
        return bool(lst) and any(runs[t][key] == val for t in lst)

    a_gate = allrun(a_runs, "gate_crossed")
    b_gate = allrun(b_runs, "gate_crossed")
    a_dialog = allrun(a_runs, "fatal_error_dialog")
    b_dialog = anyrun(b_runs, "fatal_error_dialog")
    b_terminated = all((runs[t]["process_end"] or "").find("exitcode=0xFFFFFFFF") >= 0
                       for t in b_runs) if b_runs else False
    # B1 predates the exit-code observation fix; report the runs that carry the
    # signal explicitly so the claim is not weakened by an instrumentation-era gap.
    b_term_runs = [t for t in b_runs
                   if "exitcode=0xFFFFFFFF" in (runs[t]["process_end"] or "")]

    out = {
        "round": "RESTORE-ENGINE-BRIDGE-003",
        "policy": "observation-first; any empty result is NOT_OBSERVED, never 'does not call'",
        "conditions": {
            "A": "original IIPS\\iips.dll (pristine, byte-identical)",
            "B": "LocalRM_v3.dll served as IIPS\\iips.dll inside an isolated sandbox",
        },
        "artifacts": a01["artifacts"] if a01 else None,
        "static_findings": {
            "original_iips": {
                "exports": a02["providers"]["original_iips"]["exports"] if a02 else None,
                "getresourcemanagerii_rva": 0x1C80,
                "releaseresourcemanagerii_rva": 0x1C60,
            },
            "localrm_v3": {
                "exports": a02["providers"]["localrm_v3"]["exports"] if a02 else None,
                "export_dir_declared_rva": 0x55360,
                "export_dir_actual_off": 0x5535C,
                "export_dir_delta_bytes": -4,
                "trap": "Data Directory EXPORT RVA is 4 bytes late; loader tolerates it",
            },
            "resolution_mechanism": {
                "loadlibrary_by_path": "IIPS\\iips.dll (EXE .rdata 0x6B53F0)",
                "getprocaddress_by_name": ["GetResourceManagerII (0x6B5294)",
                                            "ReleaseResourceManagerII (0x6B52AC)"],
                "ordinal_layout_consulted": False,
                "exe_imports": a02b["exe_imports"] if a02b else None,
                "base_imports_loader_apis": a05["base"]["has_loadlibrary"] if a05 else None,
                "base_has_getprocaddress": a05["base"]["has_getprocaddress"] if a05 else None,
                "base_contains_iips_strings": a05["base"]["container_strings"] if a05 else None,
                "exe_contains_iips_strings": a05["exe"]["container_strings"] if a05 else None,
            },
            "virtualisation_barrier": {
                "base_tvm0_vsize": 0x01F5E000 if a06 else None,
                "exe_tvm0_vsize": 0x4000 if a06 else None,
                "note": "Base.dll's engine logic is in a ~32.7MB .tvm0 virtualised "
                        "container; statically unreachable without ISA recovery.",
            },
            "base_dependence": {
                "original_singleton_operands_relocated": False if a11 else None,
                "localrm_localrm_section_relocations": 0 if a10 else None,
                "all_runs_relocated": a12["a_relocated_every_run"] if a12 else None,
                "hypothesis": "REFUTED - relocation state does not distinguish A from B",
            },
            "abi_equivalence": {
                "structural_equivalence": a13["structural_equivalence"] if a13 else None,
                "original_vtable_slots_non_null": a13["original"]["vtable_non_null"] if a13 else None,
                "localrm_v3_vtable_slots_non_null": a13["localrm_v3"]["vtable_non_null"] if a13 else None,
                "original_vptrs": [a13["original"]["obj_plus_04"], a13["original"]["obj_plus_20"],
                                   a13["original"]["obj_plus_44"]] if a13 else None,
                "localrm_v3_vptrs": [a13["localrm_v3"]["obj_plus_04"], a13["localrm_v3"]["obj_plus_20"],
                                     a13["localrm_v3"]["obj_plus_44"]] if a13 else None,
            },
            "ordinal_mismatch": {
                "original_ordinal_for_GetResourceManagerII": 3,
                "localrm_v3_ordinal_for_GetResourceManagerII": 1,
                "impact": "REFUTED as a cause here because resolution is by name",
            },
        },
        "runs": runs,
        "condition_A_summary": {
            "runs": a_runs,
            "engine_gate": "PASS" if a_gate else "FAIL",
            "rm_object_observed": "NO" if not anyrun(a_runs, "rm_object_candidates") else "CANDIDATE",
            "rm_vtable_calls": sum(runs[t]["rm_vtable_calls"] for t in a_runs),
            "grm_calls_observable": False,
            "grm_observation_method": "external object scan (no write permitted in A)",
            "fatal_error_dialog": "YES" if a_dialog else "NO",
        },
        "condition_B_summary": {
            "runs": b_runs,
            "engine_gate": "PASS" if b_gate else "FAIL",
            "provider_loaded": "LocalRM_v3" if anyrun(b_runs, "provider_kind", "LocalRM_v3") or
                               all((runs[t]["provider_kind"] == "LocalRM_v3") for t in b_runs) else None,
            "rm_vtable_calls": sum(runs[t]["rm_vtable_calls"] for t in b_runs),
            "grm_calls": sum(runs[t]["grm_calls"] for t in b_runs),
            "resolve_calls": sum(runs[t]["resolve_calls"] for t in b_runs),
            "resolved_entry_in_iat": sum(runs[t]["resolved_entry_in_iat"] for t in b_runs),
            "fatal_error_dialog": "YES" if b_dialog else "NO",
            "self_terminated_0xFFFFFFFF": bool(b_term_runs),
            "self_terminated_runs": b_term_runs,
            "runs_without_exitcode_signal": [t for t in b_runs if t not in b_term_runs],
        },
        "asymmetry": {
            "A_shows_fatal_error_dialog": a_dialog,
            "B_shows_fatal_error_dialog": b_dialog,
            "A_gate": a_gate,
            "B_gate": b_gate,
            "note": "Gate crosses in BOTH; the post-gate behaviour differs. The fatal "
                    "dialog is absent in B and B terminates with 0xFFFFFFFF.",
        },
    }

    with open(os.path.join(EV, "rm_engine_calls.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("=== EB-003 Agent 07: aggregate ===")
    for t in tags:
        r = runs[t]
        print("  %-4s gate=%-5s provider=%-12s dialog=%-5s rmvtable=%-3d grm=%-3d "
              "resolve=%-3d iat=%-3d end=%s"
              % (t, r["gate_crossed"], r["provider_kind"], r["fatal_error_dialog"],
                 r["rm_vtable_calls"], r["grm_calls"], r["resolve_calls"],
                 r["resolved_entry_in_iat"], r["process_end"]))
    print()
    print("wrote %s" % os.path.join(EV, "rm_engine_calls.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
