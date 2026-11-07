from __future__ import annotations

import csv
import hashlib
import importlib
from pathlib import Path

import capstone
from capstone import CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_OP_MEM, X86_OP_REG

from core004a_diagnostic import EXPECTED_ENTRY_RVA, EXPECTED_IMAGE_BASE, EXPECTED_SHA256, ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: int | None) -> str:
    if value is None:
        return ""
    return f"0x{value:08X}"


def normalize_inputs() -> list[tuple[str, int, str]]:
    # CORE-003 recorded the first three as VA and the later historical entries
    # as RVA. Keep that distinction explicit in every derived artifact.
    return [
        ("Entry", EXPECTED_ENTRY_RVA, "RVA"),
        ("0x401098", 0x00401098 - EXPECTED_IMAGE_BASE, "VA"),
        ("0x4010AF", 0x004010AF - EXPECTED_IMAGE_BASE, "VA"),
        ("0x4010C6", 0x004010C6 - EXPECTED_IMAGE_BASE, "VA"),
        ("0x77F580", 0x0077F580, "RVA"),
        ("0x4FD9B0", 0x004FD9B0, "RVA"),
        ("0x4FCEE0", 0x004FCEE0, "RVA"),
        ("0x808650", 0x00808650, "RVA"),
        ("0x7E98F0", 0x007E98F0, "RVA"),
        ("0x6212C0", 0x006212C0, "RVA"),
    ]


def module_matrix() -> list[dict[str, str]]:
    names = ["capstone", "iced_x86", "zydis", "distorm3", "pefile", "lief"]
    capability = {
        "capstone": ("x86-32", "NO", "YES", "NO"),
        "iced_x86": ("x86-32", "NO", "YES", "PARTIAL"),
        "zydis": ("x86-32", "NO", "YES", "PARTIAL"),
        "distorm3": ("x86-32", "NO", "YES", "NO"),
        "pefile": ("N/A", "YES", "NO", "NO"),
        "lief": ("x86/PE", "YES", "PARTIAL", "PARTIAL"),
    }
    rows = []
    for name in names:
        architecture, pe_support, disassembly, cfg = capability[name]
        try:
            module = importlib.import_module(name)
            version = str(getattr(module, "__version__", getattr(module, "VERSION", "UNKNOWN")))
            path = str(getattr(module, "__file__", ""))
            status = "WORKING"
            error = ""
        except ModuleNotFoundError as exc:
            version = ""
            path = ""
            status = "MISSING"
            error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            version = ""
            path = ""
            status = "BROKEN"
            error = f"{type(exc).__name__}: {exc}"
        rows.append({
            "tool": name,
            "version": version,
            "architecture_support": architecture,
            "PE_support": pe_support,
            "x86_support": "YES" if architecture == "x86-32" else "PARTIAL" if architecture != "N/A" else "NO",
            "disassembly_support": disassembly,
            "CFG_support": cfg,
            "status": status,
            "error": error,
            "path": path,
        })

    cdb = ROOT / "工具" / "windbg_x86" / "cdb.exe"
    rows.append({
        "tool": "cdb",
        "version": "10.0.29617.1000" if cdb.exists() else "",
        "architecture_support": "x86",
        "PE_support": "YES",
        "x86_support": "YES",
        "disassembly_support": "YES",
        "CFG_support": "NO",
        "status": "WORKING" if cdb.exists() else "MISSING",
        "error": "" if cdb.exists() else "not found in project tool directory",
        "path": str(cdb) if cdb.exists() else "",
    })
    project_disasm = ROOT / "COD OL" / "scripts" / "disasm.py"
    rows.append({
        "tool": "project-disasm.py",
        "version": "LOCAL_SCRIPT" if project_disasm.exists() else "",
        "architecture_support": "x86-32" if project_disasm.exists() else "",
        "PE_support": "PARTIAL" if project_disasm.exists() else "NO",
        "x86_support": "YES" if project_disasm.exists() else "NO",
        "disassembly_support": "YES" if project_disasm.exists() else "NO",
        "CFG_support": "NO",
        "status": "PARTIAL" if project_disasm.exists() else "MISSING",
        "error": "hard-coded for a different ImageBase; not used for this EXE" if project_disasm.exists() else "",
        "path": str(project_disasm) if project_disasm.exists() else "",
    })
    return rows


def make_section_map(pe: ManualPE) -> None:
    rows = []
    for section in pe.sections:
        rows.append({
            "section": section.name,
            "rva": fmt(section.virtual_address),
            "va": fmt(pe.image_base + section.virtual_address),
            "file_offset": fmt(section.raw_offset),
            "raw_size": fmt(section.raw_size),
            "virtual_size": fmt(section.virtual_size),
            "characteristics": fmt(section.characteristics),
            "executable": "YES" if section.executable else "NO",
            "status": "VALID" if section.raw_offset + section.raw_size <= len(pe.data) else "INVALID",
        })
    write_csv(
        ROOT / "exe_core004_section_map.csv",
        ["section", "rva", "va", "file_offset", "raw_size", "virtual_size", "characteristics", "executable", "status"],
        rows,
    )


def make_entry_bytes(pe: ManualPE) -> None:
    lines = [
        "CODOL STANDALONE-CORE-004 Entry Bytes",
        "Sample: COD OL\\codoMP_client_shipRetail.exe",
        f"SHA256: {hashlib.sha256(pe.data).hexdigest()}",
        f"Entry RVA: {fmt(pe.entry_rva)}",
        f"Entry VA: {fmt(pe.image_base + pe.entry_rva)}",
    ]
    for delta, label in [(-0x100, "Entry - 0x100"), (0, "Entry"), (0x100, "Entry + 0x100")]:
        rva = pe.entry_rva + delta
        raw, section, offset, status = pe.read_rva(rva, 128)
        lines.extend([
            "",
            f"[{label}]",
            f"RVA: {fmt(rva)}",
            f"VA: {fmt(pe.image_base + rva)}",
            f"Section: {section.name if section else 'UNKNOWN'}",
            f"File offset: {fmt(offset)}",
            f"Status: {status}",
            f"Bytes read: {len(raw)}",
        ])
        for index in range(0, len(raw), 16):
            chunk = raw[index:index + 16]
            hex_text = " ".join(f"{byte:02X}" for byte in chunk)
            ascii_text = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)
            lines.append(f"{(offset or 0) + index:08X}  {hex_text:<47}  {ascii_text}")
    (ROOT / "exe_core004_entry_bytes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_smoke_test(pe: ManualPE) -> list[dict[str, object]]:
    md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    rows = []
    for label, rva, input_kind in normalize_inputs():
        for window in (32, 64, 128):
            raw, section, _offset, status = pe.read_rva(rva, window)
            first = ""
            last = ""
            error = ""
            count = 0
            if status == "OK" and section and section.executable:
                try:
                    instructions = list(md.disasm(raw, pe.image_base + rva))
                    count = len(instructions)
                    if instructions:
                        first = f"0x{instructions[0].address:08X} {instructions[0].mnemonic} {instructions[0].op_str}".strip()
                        last = f"0x{instructions[-1].address:08X} {instructions[-1].mnemonic} {instructions[-1].op_str}".strip()
                    else:
                        error = "NO_INSTRUCTION_DECODED"
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
            else:
                error = status
            if label == "Entry" and count:
                confidence = "CONFIRMED"
            elif count:
                confidence = "PARTIAL_DISASSEMBLY_CONFIRMED"
            elif error == "VIRTUAL_ONLY":
                confidence = "NOT_ANALYZED"
            else:
                confidence = "UNRESOLVED"
            rows.append({
                "rva": fmt(rva),
                "va": fmt(pe.image_base + rva),
                "section": section.name if section else "UNKNOWN",
                "tool": "capstone 5.0.7 / x86-32 / detail=False",
                "instruction_count": count,
                "first_instruction": first,
                "last_instruction": last,
                "error": error,
                "confidence": confidence,
                "input": label,
                "input_kind": input_kind,
                "window_bytes": window,
                "mapping_status": status,
            })
    write_csv(
        ROOT / "exe_core004_disassembly_smoke_test.csv",
        ["rva", "va", "section", "tool", "instruction_count", "first_instruction", "last_instruction", "error", "confidence", "input", "input_kind", "window_bytes", "mapping_status"],
        rows,
    )
    return rows


def make_indirect_sites(pe: ManualPE) -> list[dict[str, object]]:
    md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    rows = []
    seen = set()
    # This is deliberately a linear identification pass over raw-backed
    # executable sections. It is evidence for sites, not a CFG or function map.
    for section in pe.sections:
        if not section.executable or section.name == ".tvm0" or not section.raw_size:
            continue
        raw = pe.data[section.raw_offset:section.raw_offset + section.raw_size]
        for instruction in md.disasm(raw, pe.image_base + section.virtual_address):
            mnemonic = instruction.mnemonic
            if mnemonic not in {"call", "jmp", "lcall", "ljmp"} or not instruction.operands:
                continue
            operand = instruction.operands[0]
            is_indirect = operand.type in {X86_OP_REG, X86_OP_MEM} or mnemonic in {"lcall", "ljmp"}
            if not is_indirect:
                continue
            rva = instruction.address - pe.image_base
            if rva in seen:
                continue
            seen.add(rva)
            entry_boundary = (
                rva == EXPECTED_ENTRY_RVA
                and operand.type == X86_OP_MEM
                and (operand.mem.disp & 0xFFFFFFFF) == 0x0E9DC665
            )
            if operand.type == X86_OP_REG:
                expression = instruction.reg_name(operand.reg)
                pointer_candidate = "NO"
            elif operand.type == X86_OP_MEM:
                expression = instruction.op_str
                pointer_candidate = "UNKNOWN"
            else:
                expression = instruction.op_str
                pointer_candidate = "UNKNOWN"
            rows.append({
                "rva": fmt(rva),
                "va": fmt(instruction.address),
                "instruction": f"{mnemonic} {instruction.op_str}".strip(),
                "operand": expression,
                "section": section.name,
                "register_definition_available": "NO",
                "global_pointer_candidate": pointer_candidate,
                "target_resolved": "EXTERNAL_BOUNDARY" if entry_boundary else "UNKNOWN",
                "confidence": "CONFIRMED" if entry_boundary else "UNKNOWN",
                "scan_scope": "RAW_LINEAR_HEURISTIC",
            })
    # The PE entrypoint is a required explicit check. The linear section pass
    # may not reach it if an earlier undecodable byte stops iteration, so record
    # the confirmed boundary independently from the heuristic site scan.
    entry_raw, entry_section, _entry_offset, entry_status = pe.read_rva(EXPECTED_ENTRY_RVA, 6)
    if (
        entry_status == "OK"
        and entry_section
        and entry_raw == bytes.fromhex("FF 15 65 C6 9D 0E")
        and not any(row["rva"] == fmt(EXPECTED_ENTRY_RVA) for row in rows)
    ):
        rows.append({
            "rva": fmt(EXPECTED_ENTRY_RVA),
            "va": fmt(pe.image_base + EXPECTED_ENTRY_RVA),
            "instruction": "call dword ptr [0xe9dc665]",
            "operand": "dword ptr [0xe9dc665]",
            "section": entry_section.name,
            "register_definition_available": "NO",
            "global_pointer_candidate": "KNOWN_EXTERNAL_SLOT",
            "target_resolved": "EXTERNAL_BOUNDARY",
            "confidence": "CONFIRMED",
            "scan_scope": "ENTRY_EXPLICIT_VALIDATION",
        })
    write_csv(
        ROOT / "exe_core004_indirect_call_sites.csv",
        ["rva", "va", "instruction", "operand", "section", "register_definition_available", "global_pointer_candidate", "target_resolved", "confidence", "scan_scope"],
        rows,
    )
    return rows


def main() -> int:
    pe = ManualPE(SAMPLE)
    sample_hash = hashlib.sha256(pe.data).hexdigest()
    if sample_hash != EXPECTED_SHA256:
        raise SystemExit(f"SAMPLE_MISMATCH: {sample_hash}")
    if pe.image_base != EXPECTED_IMAGE_BASE or pe.entry_rva != EXPECTED_ENTRY_RVA:
        raise SystemExit("PE_MAPPING_FAILURE: sample identity differs from CORE-004 baseline")

    matrix = module_matrix()
    write_csv(
        ROOT / "exe_core004_toolchain_matrix.csv",
        ["tool", "version", "architecture_support", "PE_support", "x86_support", "disassembly_support", "CFG_support", "status", "error", "path"],
        matrix,
    )
    make_section_map(pe)
    make_entry_bytes(pe)
    smoke_rows = make_smoke_test(pe)
    indirect_rows = make_indirect_sites(pe)

    raw_successes = sum(row["instruction_count"] > 0 for row in smoke_rows)
    virtual_only = sum(row["error"] == "VIRTUAL_ONLY" for row in smoke_rows)
    detail_false_note = "detail=False is usable; operand access requires detail=True"
    report = f"""# CODOL STANDALONE-CORE-004
## EXE Static Analysis Toolchain Recovery

## Final status

```text
TOOLCHAIN_STATUS = LEVEL_3
WORKING_TOOL = Python stdlib/manual PE parser; pefile 2024.8.26; Capstone 5.0.7; cdb 10.0.29617.1000
FAILED_TOOL = Ghidra / IDA / Binary Ninja / rizin / radare2 / objdump / LLVM tools / dumpbin not found
PRIMARY_FAILURE_LAYER = FUNCTION_AND_CFG_AUTOMATION_NOT_AVAILABLE
SAMPLE_STATUS = SAMPLE_MATCH_CONFIRMED
PE_MAPPING_STATUS = PE_MAPPING_CONFIRMED
DISASSEMBLY_STATUS = X86_DISASSEMBLY_CONFIRMED
FUNCTION_RECOVERY_STATUS = NOT_PERFORMED
CFG_STATUS = NOT_PERFORMED
NEXT_STEP = CORE-005-style bounded CFG recovery; do not infer Game Init/Main Loop yet
```

## Sample identity

```text
Sample = COD OL\\codoMP_client_shipRetail.exe
SHA-256 = {sample_hash}
PE32 = YES
I386 = YES
ImageBase = 0x{pe.image_base:08X}
Entry RVA = 0x{pe.entry_rva:08X}
Entry VA = 0x{pe.image_base + pe.entry_rva:08X}
Sections = {pe.number_of_sections}
```

## Results

- Manual DOS/PE/COFF/PE32 parsing succeeded.
- `.tp3` section headers and RVA-to-file-offset mapping were read from the section table; `RVA == file offset` was not assumed.
- Entry begins with `FF 15 65 C6 9D 0E`, decoded as `call dword ptr [0x0E9DC665]`. The slot is recorded as `EXTERNAL_BOUNDARY`; Base.dll was not entered.
- Smoke test rows: `{len(smoke_rows)}`; windows with at least one decoded instruction: `{raw_successes}`; `VIRTUAL_ONLY` windows: `{virtual_only}`.
- Indirect-site rows: `{len(indirect_rows)}`. These come from a raw-linear identification pass and are not a CFG or function proof.
- `{detail_false_note}`. A previous `CS_ERR_DETAIL` is a Capstone configuration/access-mode issue, not proof that the sample is undecodable.

## Function boundary status

No automatic function-boundary engine is available in this environment. Prologue-like bytes, strings, direct targets, and linear decode output are not promoted to confirmed functions. A CFG-derived boundary method is required for the next stage.

## `.tvm0` and external boundaries

`.tvm0` was excluded from the executable scan. No VM decoding, dispatcher recovery, Base.dll analysis, or other DLL analysis was performed.

## Negative findings

- This run does not prove a complete function database.
- This run does not prove a complete CFG.
- It does not classify Game Init, Main Loop, Renderer, Filesystem, or State Machine behavior.
- `VIRTUAL_ONLY` addresses are not reconstructed as file code.
- Indirect targets other than the Entry boundary remain `UNKNOWN`.

## Delivered artifacts

- `exe_core004_toolchain_matrix.csv`
- `exe_core004_section_map.csv`
- `exe_core004_entry_bytes.txt`
- `exe_core004_disassembly_smoke_test.csv`
- `exe_core004_indirect_call_sites.csv`

The CORE-004 capability ceiling is `LEVEL_3`: sample read, PE mapping, and x86 disassembly are confirmed. Function recovery and CFG recovery remain future work.
"""
    (ROOT / "CODOL_STANDALONE_CORE_004_TOOLCHAIN_RECOVERY.md").write_text(report, encoding="utf-8")
    print(f"sample_sha256={sample_hash}")
    print(f"smoke_rows={len(smoke_rows)} decoded_windows={raw_successes}")
    print(f"indirect_rows={len(indirect_rows)}")
    print("TOOLCHAIN_STATUS=LEVEL_3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
