from __future__ import annotations

"""
EXE-CORE-006 stage 2: function-table reclassification, thread seeds,
historical bootstrap chain revalidation, connection matrix.

Only static analysis of codoMP_client_shipRetail.exe. No patching, no hooks,
no DLL internals, no .tvm0 semantic decoding.
"""

import csv
import hashlib
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

from core004a_diagnostic import ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
EXPECTED_ENTRY_RVA = 0x0E5DC690
IMAGE_BASE = 0x00400000

HISTORICAL_CANDIDATES = [0x0077F580, 0x0077F8B3, 0x004FD9B0, 0x004FCEE0,
                         0x00808650, 0x007E98F0, 0x006212C0]

CORE005_TABLE_SUSPECTS = [
    0x00CA812C, 0x00CA8190, 0x00CA819C, 0x00CA84C8,
]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: int | None) -> str:
    return "" if value is None else f"0x{value:08X}"


def classify_mapping(pe: ManualPE, rva: int) -> str:
    section, offset, status = pe.rva_to_offset(rva)
    if section is None and status == "PE_HEADERS":
        return "PE_HEADERS"
    if section is None:
        return status
    if section.name == ".tvm0":
        return "TVM0_BOUNDARY"
    if status == "VIRTUAL_ONLY":
        return "VIRTUAL_ONLY"
    if status != "OK":
        return status
    return "RAW_BACKED_EXECUTABLE" if section.executable else "RAW_BACKED_DATA"


def decode_at(pe: ManualPE, rva: int, max_insns: int = 24):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    data, section, off, status = pe.read_rva(rva, max_insns * 15)
    if status != "OK" or section is None or not section.executable:
        return [], status
    return list(md.disasm(data, IMAGE_BASE + rva, count=max_insns)), "OK"


def xref_scan(pe: ManualPE, target_rva: int) -> dict[str, object]:
    """Search raw file bytes for direct CALL/JMP rel32 to target and for absolute
    pointer DWORDs equal to target VA / RVA. Returns explicit evidence counts."""
    direct_call = 0
    direct_jmp = 0
    abs_va_ptr = 0
    abs_rva_ptr = 0
    call_sites: list[int] = []
    jmp_sites: list[int] = []
    ptr_sites: list[int] = []
    target_va = IMAGE_BASE + target_rva
    target_bytes = struct.pack("<I", target_va)
    target_rva_bytes = struct.pack("<I", target_rva)
    for section in pe.sections:
        if not section.executable or section.raw_size == 0:
            continue
        raw = pe.data[section.raw_offset:section.raw_offset + section.raw_size]
        base_rva = section.virtual_address
        for i in range(len(raw) - 5):
            op = raw[i]
            if op not in (0xE8, 0xE9):
                continue
            disp = struct.unpack_from("<i", raw, i + 1)[0]
            # instruction RVA is base_rva + i; next = rva + 5
            if ((base_rva + i) + 5 + disp) & 0xFFFFFFFF == target_rva:
                if op == 0xE8:
                    direct_call += 1
                    call_sites.append(base_rva + i)
                else:
                    direct_jmp += 1
                    jmp_sites.append(base_rva + i)
    for section in pe.sections:
        if section.raw_size == 0:
            continue
        raw = pe.data[section.raw_offset:section.raw_offset + section.raw_size]
        base_rva = section.virtual_address
        for i in range(0, len(raw) - 4, 4):
            chunk = raw[i:i + 4]
            if chunk == target_bytes:
                abs_va_ptr += 1
                ptr_sites.append(base_rva + i)
            elif chunk == target_rva_bytes and target_rva != 0:
                abs_rva_ptr += 1
    return {
        "direct_call": direct_call,
        "direct_jmp": direct_jmp,
        "abs_va_ptr": abs_va_ptr,
        "abs_rva_ptr": abs_rva_ptr,
        "call_sites": call_sites[:8],
        "jmp_sites": jmp_sites[:8],
        "ptr_sites": ptr_sites[:8],
    }


def analyze_exports(pe: ManualPE) -> list[dict[str, object]]:
    rows = []
    dd = pe.pe_offset + 4 + 20 + 96
    export_rva = struct.unpack_from("<I", pe.data, dd)[0]
    if not export_rva:
        return rows
    b, _, _, st = pe.read_rva(export_rva, 0x28)
    (_c, _t, _mj, _mn, name_rva, ord_base, n_func, n_name,
     addr_func, addr_name, addr_ord) = struct.unpack("<IIHHIIIIIII", b)
    funcs = []
    for i in range(n_func):
        fb, _, _, _ = pe.read_rva(addr_func + i * 4, 4)
        funcs.append(struct.unpack("<I", fb)[0])
    out = []
    for i in range(n_name):
        ob, _, _, _ = pe.read_rva(addr_ord + i * 2, 2)
        o = struct.unpack("<H", ob)[0]
        nb, _, _, _ = pe.read_rva(addr_name + i * 4, 4)
        nrva = struct.unpack("<I", nb)[0]
        sb, _, _, _ = pe.read_rva(nrva, 256)
        nm = sb.split(b"\0")[0].decode("latin1", "replace")
        out.append({"ordinal": ord_base + o, "index": o,
                    "function_rva": funcs[o], "name": nm})
    return out


def find_pointer_tables(pe: ManualPE, scan_sections, min_run: int = 8):
    """Find runs of consecutive DWORDs that are plausible code pointers
    (value maps to an executable section). Reports the raw pointer-table runs."""
    runs = []
    for section in scan_sections:
        if section.raw_size == 0:
            continue
        raw = pe.data[section.raw_offset:section.raw_offset + section.raw_size]
        i = 0
        while i + 4 <= len(raw):
            value = struct.unpack_from("<I", raw, i)[0]
            rva = value - IMAGE_BASE
            ok = False
            if value and (value & 0xFFFF0000) and rva < pe.size_of_image:
                sec = pe.section_for_rva(rva)
                ok = sec is not None and sec.executable
            if not ok:
                i += 4
                continue
            start = i
            count = 0
            targets = []
            while i + 4 <= len(raw):
                v = struct.unpack_from("<I", raw, i)[0]
                rr = v - IMAGE_BASE
                s2 = pe.section_for_rva(rr) if (v and rr < pe.size_of_image) else None
                if not (s2 is not None and s2.executable):
                    break
                targets.append(rr)
                count += 1
                i += 4
            if count >= min_run:
                runs.append({
                    "table_rva": section.virtual_address + start,
                    "section": section.name,
                    "count": count,
                    "first_target_rva": targets[0],
                    "first_target_mapping": classify_mapping(pe, targets[0]),
                })
            else:
                i = start + 4
    return runs


def main() -> int:
    digest = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    print(f"sample_match = {'CONFIRMED' if digest == EXPECTED_SHA256 else 'MISMATCH'}")
    pe = ManualPE(SAMPLE)

    # ---- 1. Historical candidate revalidation with strict evidence ----
    print("\n=== Historical bootstrap candidate revalidation ===")
    hist_rows = []
    for cand in HISTORICAL_CANDIDATES:
        mapping = classify_mapping(pe, cand)
        xr = xref_scan(pe, cand)
        insns, st = decode_at(pe, cand, 12)
        decode_ok = bool(insns) and st == "OK"
        first = f"{insns[0].mnemonic} {insns[0].op_str}" if insns else ""
        if xr["direct_call"] > 0 or xr["direct_jmp"] > 0 or xr["abs_va_ptr"] > 0:
            classification = "ENTRY_CONNECTED_CANDIDATE"  # xref exists somewhere
        elif mapping == "VIRTUAL_ONLY":
            classification = "HISTORICAL_ONLY"
        else:
            classification = "NOT_FOUND"
        hist_rows.append({
            "candidate_rva": fmt(cand),
            "mapping_status": mapping,
            "decode_status": st,
            "first_instruction": first,
            "direct_call_incoming": xr["direct_call"],
            "direct_jmp_incoming": xr["direct_jmp"],
            "absolute_va_pointer_occurrences": xr["abs_va_ptr"],
            "absolute_rva_pointer_occurrences": xr["abs_rva_ptr"],
            "classification": classification,
        })
        print(f"  {fmt(cand)} {mapping:22s} call={xr['direct_call']} "
              f"jmp={xr['direct_jmp']} va_ptr={xr['abs_va_ptr']} -> {classification}")
    write_csv(ROOT / "exe_core006_historical_revalidation.csv",
              ["candidate_rva", "mapping_status", "decode_status",
               "first_instruction", "direct_call_incoming", "direct_jmp_incoming",
               "absolute_va_pointer_occurrences", "absolute_rva_pointer_occurrences",
               "classification"], hist_rows)

    # Direct incoming edge for each candidate from recovered direct CALL/JMP only.

    # ---- 2. Function table analysis ----
    print("\n=== Pointer-table run discovery (executable targets) ===")
    table_runs = find_pointer_tables(pe, pe.sections, min_run=8)
    print(f"  executable-pointing table runs: {len(table_runs)}")
    for run in table_runs[:20]:
        print(f"    table@{run['table_rva_hex'] if 'table_rva_hex' in run else fmt(run['table_rva'])} "
              f"count={run['count']} first=0x{run['first_target_rva']:08X} "
              f"[{run['first_target_mapping']}]")
    write_csv(ROOT / "exe_core006_function_tables.csv",
              ["table_rva", "section", "count", "first_target_rva",
               "first_target_mapping"], table_runs)

    # ---- 3. Thread seed analysis ----
    print("\n=== Thread API symbol scan ===")
    thread_rows = []
    symbols = [b"CreateThread", b"_beginthreadex", b"_beginthread",
               b"NtCreateThreadEx", b"RtlUserThreadStart", b"CreateRemoteThread",
               b"RtlCreateUserThread"]
    data = pe.data
    for sym in symbols:
        hits = [m.start() for m in re.finditer(re.escape(sym), data)]
        thread_rows.append({
            "symbol": sym.decode(),
            "occurrences": len(hits),
            "first_offsets": ";".join(hex(h) for h in hits[:4]),
            "result": "SYMBOL_ABSENT" if not hits else "SYMBOL_FOUND",
        })
        print(f"  {sym.decode():22s} occurrences={len(hits)}")
    write_csv(ROOT / "exe_core006_thread_seeds.csv",
              ["symbol", "occurrences", "first_offsets", "result"], thread_rows)

    # ---- 4. Connection matrix ----
    print("\n=== Connection matrix ===")
    matrix = []

    def add(entity, entity_kind, mapping, entry_reachable, mechanism, verdict, evidence):
        matrix.append({
            "entity": entity, "entity_kind": entity_kind, "mapping_status": mapping,
            "entry_reachable": entry_reachable, "mechanism": mechanism,
            "verdict": verdict, "evidence": evidence,
        })

    add("0x0E5DC690", "PE_ENTRY", "RAW_BACKED_EXECUTABLE", "YES", "PE_ENTRYPOINT",
        "ENTRY_CONNECTED", "PE OptionalHeader.AddressOfEntryPoint")
    add("0x0E5DC665", "IAT_SLOT", "RAW_BACKED_DATA", "YES",
        "call dword ptr [IAT slot]", "EXTERNAL_BOUNDARY",
        "import thunk 0x80000001 -> Base.dll ordinal 1")
    for cand in HISTORICAL_CANDIDATES:
        mapping = classify_mapping(pe, cand)
        add(fmt(cand), "HISTORICAL_BOOTSTRAP", mapping, "NO", "DIRECT_CALL_OR_POINTER",
            "HISTORICAL_ONLY" if mapping == "VIRTUAL_ONLY" else "UNKNOWN",
            "no recovered direct CALL/JMP/pointer from Entry-connected graph")
    for ex in analyze_exports(pe):
        add(fmt(ex["function_rva"]), "EXPORTED_FUNCTION",
            classify_mapping(pe, ex["function_rva"]), "NO", "PE_EXPORT_TABLE",
            "BOUNDARY", "exported as " + ex["name"][:48])
    write_csv(ROOT / "exe_core006_connection_matrix.csv",
              ["entity", "entity_kind", "mapping_status", "entry_reachable",
               "mechanism", "verdict", "evidence"], matrix)
    print(f"  matrix rows: {len(matrix)}")

    # ---- 5. Section / raw backing summary ----
    print("\n=== Section raw-backing summary ===")
    sect_rows = []
    zero_gap = 0
    for s in pe.sections:
        sect_rows.append({
            "index": s.index, "name": s.name,
            "virtual_address": fmt(s.virtual_address),
            "virtual_size": fmt(s.virtual_size),
            "raw_size": fmt(s.raw_size),
            "executable": "YES" if s.executable else "NO",
            "raw_backed_end_rva": fmt(s.virtual_address + s.raw_size),
            "virtual_only_bytes": fmt(max(0, s.virtual_size - s.raw_size)),
        })
    write_csv(ROOT / "exe_core006_sections.csv",
              ["index", "name", "virtual_address", "virtual_size", "raw_size",
               "executable", "raw_backed_end_rva", "virtual_only_bytes"], sect_rows)

    # ---- 6. Entry region raw inspection ----
    entry_rva = pe.entry_rva
    sec = pe.section_for_rva(entry_rva)
    delta = entry_rva - sec.virtual_address
    raw = pe.data[sec.raw_offset + delta: sec.raw_offset + sec.raw_size]
    trailing = 0
    for b in raw[6:]:
        if b == 0:
            trailing += 1
        else:
            break
    print(f"\n=== Entry region ===")
    print(f"  entry section            : {sec.name} "
          f"(VA 0x{sec.virtual_address:08X})")
    print(f"  trailing zero bytes after entry: {trailing} "
          f"(0x{trailing:X}) to end of raw section")
    print(f"  native continuation after Entry: NONE (zero-filled)")

    # ---- 7. Cross-section direct transfers into the stub section ----
    stub = None
    for s in pe.sections:
        if s.virtual_address <= pe.entry_rva < s.virtual_address + s.mapped_size:
            stub = s
            break
    cross_rows = []
    if stub is not None:
        lo = stub.virtual_address
        hi = stub.virtual_address + stub.mapped_size
        for s in pe.sections:
            if not s.executable or s.raw_size == 0:
                continue
            raw = pe.data[s.raw_offset:s.raw_offset + s.raw_size]
            base_rva = s.virtual_address
            for i in range(len(raw) - 5):
                if raw[i] not in (0xE8, 0xE9):
                    continue
                disp = struct.unpack_from("<i", raw, i + 1)[0]
                target = ((base_rva + i) + 5 + disp) & 0xFFFFFFFF
                if lo <= target < hi:
                    cross_rows.append({
                        "call_site_rva": fmt(base_rva + i),
                        "site_section": s.name,
                        "opcode": "E8" if raw[i] == 0xE8 else "E9",
                        "target_rva": fmt(target),
                        "target_section": stub.name,
                        "target_mapping": classify_mapping(pe, target),
                    })
    print(f"\n=== Cross-section direct transfers into stub section: "
          f"{len(cross_rows)} ===")
    for row in cross_rows:
        print(f"  {row['call_site_rva']} -> {row['target_rva']} "
              f"[{row['target_mapping']}]")
    write_csv(ROOT / "exe_core006_cross_section_transfers.csv",
              ["call_site_rva", "site_section", "opcode", "target_rva",
               "target_section", "target_mapping"], cross_rows)

    print("\nartifacts: exe_core006_historical_revalidation.csv, "
          "exe_core006_function_tables.csv, exe_core006_thread_seeds.csv, "
          "exe_core006_connection_matrix.csv, exe_core006_sections.csv, "
          "exe_core006_cross_section_transfers.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
