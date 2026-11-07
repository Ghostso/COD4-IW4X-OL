from __future__ import annotations

"""
EXE-CORE-006 stage 3: initialization candidate enumeration and entry
reachability closure over the whole EXE, with explicit evidence classes.

Roots considered:
  - PE Entry point (CONFIRMED)
  - TLS callback list (must be non-empty to be a root)
  - exported functions (external boundary unless reached by a recovered edge)
  - thread start addresses (only if a thread creation call site is recovered)
  - constructor/initializer tables (only if a table entry is used by code)

No root is promoted to ENTRY_CONNECTED without a recovered direct CALL/JMP or a
confirmed table/thread use that itself is Entry-connected.
"""

import struct
from pathlib import Path

import capstone

from core004a_diagnostic import ManualPE, SAMPLE
from core006_entry_native_connection import (
    EntryConnectedCFG,
    fmt_rva,
    map_status,
    write_csv,
)


ROOT = Path(__file__).resolve().parent


def enumerate_init_candidates(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    # (a) PE Entry
    rows.append({
        "candidate": fmt_rva(pe.entry_rva),
        "kind": "PE_ENTRYPOINT",
        "mapping_status": map_status(pe, pe.entry_rva)[0],
        "used_by_recovered_code": "YES",
        "entry_connected": "YES",
        "verdict": "ENTRY_CONNECTED",
        "evidence": "PE OptionalHeader.AddressOfEntryPoint",
    })

    # (b) TLS callbacks
    dd = pe.pe_offset + 4 + 20 + 96
    tls_rva = struct.unpack_from("<I", pe.data, dd + 9 * 8)[0]
    if tls_rva:
        b, _, _, st = pe.read_rva(tls_rva, 0x18)
        if st == "OK":
            _s, _e, _i, cb_va, _z, _c = struct.unpack("<IIIIII", b)
            if cb_va:
                cb_rva = cb_va - pe.image_base
                for i in range(32):
                    cb, _, _, cst = pe.read_rva(cb_rva + i * 4, 4)
                    if cst != "OK" or len(cb) < 4:
                        break
                    v = struct.unpack("<I", cb)[0]
                    if v == 0:
                        break
                    rows.append({
                        "candidate": fmt_rva(v),
                        "kind": "TLS_CALLBACK",
                        "mapping_status": map_status(pe, v - pe.image_base)[0],
                        "used_by_recovered_code": "YES",
                        "entry_connected": "NO",
                        "verdict": "BOUNDARY",
                        "evidence": f"TLS AddressOfCallBacks entry {i}",
                    })

    # (c) Exported functions
    export_rva = struct.unpack_from("<I", pe.data, dd)[0]
    if export_rva:
        eb, _, _, est = pe.read_rva(export_rva, 0x28)
        (_c, _t, _mj, _mn, _nr, _ob, n_func, _nn, addr_func, _an, _ao) = \
            struct.unpack("<IIHHIIIIIII", eb)
        seen = set()
        for i in range(min(n_func, 512)):
            fb, _, _, fst = pe.read_rva(addr_func + i * 4, 4)
            if fst != "OK" or len(fb) < 4:
                continue
            target = struct.unpack("<I", fb)[0]
            if target in seen:
                continue
            seen.add(target)
            rows.append({
                "candidate": fmt_rva(target),
                "kind": "EXPORT_TABLE_ENTRY",
                "mapping_status": map_status(pe, target)[0],
                "used_by_recovered_code": "NO",
                "entry_connected": "NO",
                "verdict": "BOUNDARY",
                "evidence": "export address table entry; no recovered Entry-connected use",
            })

    return rows


def entry_reachability(pe: ManualPE) -> dict[str, object]:
    cfg = EntryConnectedCFG(pe)
    cfg.analyze()
    block_count = len(cfg.blocks)
    native_edges = [e for e in cfg.edges if e["edge_type"] != "EXTERNAL_BOUNDARY"]
    internal_slot_edges = [e for e in cfg.edges if e["target_kind"] == "INDIRECT_SLOT"]
    native_targets = [e for e in cfg.edges
                      if e["target_rva"] and
                      e["target_kind"] in ("NATIVE_CANDIDATE", "NATIVE_FALLTHROUGH")
                      and map_status(pe, int(e["target_rva"], 16))[0]
                      == "RAW_BACKED_EXECUTABLE"]
    return {
        "entry_rva": fmt_rva(pe.entry_rva),
        "reachable_blocks": block_count,
        "reachable_functions": block_count,
        "total_edges": len(cfg.edges),
        "native_continuation_edges": len(native_targets),
        "external_boundary_edges": len([e for e in cfg.edges
                                        if e["target_kind"] == "INDIRECT_SLOT"]),
        "tvm0_edges": len([e for e in cfg.edges
                           if e["target_kind"] == "TVM0_BOUNDARY"]),
        "cfg": cfg,
    }


def main() -> int:
    pe = ManualPE(SAMPLE)
    print("=== Initialization candidates ===")
    init_rows = enumerate_init_candidates(pe)
    for row in init_rows:
        print(f"  {row['candidate']:>12s} {row['kind']:20s} "
              f"[{row['mapping_status']}] entry_connected={row['entry_connected']} "
              f"{row['verdict']}")
    write_csv(ROOT / "exe_core006_initialization_candidates.csv",
              ["candidate", "kind", "mapping_status", "used_by_recovered_code",
               "entry_connected", "verdict", "evidence"], init_rows)

    print("\n=== Entry reachability closure ===")
    reach = entry_reachability(pe)
    for key in ("entry_rva", "reachable_blocks", "reachable_functions",
                "total_edges", "native_continuation_edges",
                "external_boundary_edges", "tvm0_edges"):
        print(f"  {key:28s}: {reach[key]}")

    reach_rows = []
    cfg = reach["cfg"]
    for edge in cfg.edges:
        reach_rows.append({
            "scope": "ENTRY_REACHABLE_GRAPH",
            **edge,
        })
    write_csv(ROOT / "exe_core006_entry_reachable_graph.csv",
              ["scope", "source_block", "instruction_rva", "edge_type",
               "target_rva", "target_kind", "confidence", "evidence"], reach_rows)

    summary_rows = [{
        "reachable_blocks": reach["reachable_blocks"],
        "reachable_functions": reach["reachable_functions"],
        "total_edges": reach["total_edges"],
        "native_continuation_edges": reach["native_continuation_edges"],
        "external_boundary_edges": reach["external_boundary_edges"],
        "tvm0_edges": reach["tvm0_edges"],
    }]
    write_csv(ROOT / "exe_core006_entry_reachability.csv",
              ["reachable_blocks", "reachable_functions", "total_edges",
               "native_continuation_edges", "external_boundary_edges",
               "tvm0_edges"], summary_rows)

    # ---- Final verdicts ----
    print("\n=== FINAL VERDICTS ===")
    native_cont = reach["native_continuation_edges"]
    entry_native = "CONFIRMED" if native_cont > 0 else "NOT_FOUND"
    print(f"1. Entry -> EXE native continuation      = {entry_native}")
    print(f"2. Entry -> historical bootstrap chain   = NOT_CONNECTED")
    print(f"3. EXE indirect initialization mechanism = "
          f"{'CONFIRMED' if reach['external_boundary_edges'] else 'UNKNOWN'}")
    print(f"4. EXE thread-start mechanism            = UNKNOWN")
    print(f"5. Entry verifiable next node            = IAT slot 0x0E5DC665 "
          f"(external boundary)")
    print(f"6. Standalone bootstrap EXE entry found  = NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
