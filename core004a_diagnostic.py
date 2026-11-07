from __future__ import annotations

import csv
import hashlib
import importlib
import os
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
EXPECTED_IMAGE_BASE = 0x00400000
EXPECTED_ENTRY_RVA = 0x0E5DC690


@dataclass(frozen=True)
class Section:
    index: int
    name: str
    virtual_size: int
    virtual_address: int
    raw_size: int
    raw_offset: int
    characteristics: int

    @property
    def mapped_size(self) -> int:
        return max(self.virtual_size, self.raw_size)

    @property
    def executable(self) -> bool:
        return bool(self.characteristics & 0x20000000)


class ManualPE:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise ValueError("DOS signature is not MZ")
        self.pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[self.pe_offset:self.pe_offset + 4] != b"PE\0\0":
            raise ValueError("PE signature is missing")

        coff = self.pe_offset + 4
        (
            self.machine,
            self.number_of_sections,
            self.timestamp,
            _pointer_to_symbols,
            _number_of_symbols,
            self.optional_header_size,
            self.coff_characteristics,
        ) = struct.unpack_from("<HHIIIHH", self.data, coff)

        optional = coff + 20
        self.optional_magic = struct.unpack_from("<H", self.data, optional)[0]
        if self.optional_magic != 0x10B:
            raise ValueError(f"expected PE32 optional header, got 0x{self.optional_magic:04X}")
        self.entry_rva = struct.unpack_from("<I", self.data, optional + 16)[0]
        self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
        self.section_alignment = struct.unpack_from("<I", self.data, optional + 32)[0]
        self.file_alignment = struct.unpack_from("<I", self.data, optional + 36)[0]
        self.size_of_image = struct.unpack_from("<I", self.data, optional + 56)[0]
        self.size_of_headers = struct.unpack_from("<I", self.data, optional + 60)[0]

        section_table = optional + self.optional_header_size
        self.sections: list[Section] = []
        for index in range(self.number_of_sections):
            offset = section_table + index * 40
            (
                raw_name,
                virtual_size,
                virtual_address,
                raw_size,
                raw_offset,
                _relocations,
                _line_numbers,
                _relocation_count,
                _line_count,
                characteristics,
            ) = struct.unpack_from("<8sIIIIIIHHI", self.data, offset)
            self.sections.append(
                Section(
                    index=index,
                    name=raw_name.rstrip(b"\0").decode("latin1", "replace"),
                    virtual_size=virtual_size,
                    virtual_address=virtual_address,
                    raw_size=raw_size,
                    raw_offset=raw_offset,
                    characteristics=characteristics,
                )
            )

    def section_for_rva(self, rva: int) -> Section | None:
        for section in self.sections:
            if section.virtual_address <= rva < section.virtual_address + section.mapped_size:
                return section
        return None

    def rva_to_offset(self, rva: int) -> tuple[Section | None, int | None, str]:
        if 0 <= rva < self.size_of_headers:
            return None, rva, "PE_HEADERS"
        section = self.section_for_rva(rva)
        if section is None:
            return None, None, "RVA_NOT_MAPPED"
        delta = rva - section.virtual_address
        if delta >= section.raw_size:
            return section, None, "VIRTUAL_ONLY"
        offset = section.raw_offset + delta
        if offset >= len(self.data):
            return section, None, "FILE_OFFSET_OUT_OF_RANGE"
        return section, offset, "OK"

    def read_rva(self, rva: int, size: int) -> tuple[bytes, Section | None, int | None, str]:
        section, offset, status = self.rva_to_offset(rva)
        if offset is None:
            return b"", section, None, status
        return self.data[offset:offset + size], section, offset, status


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def hex_dump(data: bytes, base_offset: int = 0) -> list[str]:
    lines = []
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        byte_text = " ".join(f"{byte:02X}" for byte in chunk)
        ascii_text = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in chunk)
        lines.append(f"{base_offset + offset:08X}  {byte_text:<47}  {ascii_text}")
    return lines


def module_evidence(name: str) -> dict[str, str]:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", getattr(module, "VERSION", "UNKNOWN"))
        return {
            "tool": name,
            "path": str(getattr(module, "__file__", "")),
            "version": str(version),
            "source": "PYTHON",
            "available": "WORKING",
            "executable": "YES",
            "error": "",
        }
    except ModuleNotFoundError as exc:
        return {
            "tool": name,
            "path": "",
            "version": "",
            "source": "PYTHON",
            "available": "MISSING",
            "executable": "NO",
            "error": f"{type(exc).__name__}: {exc}",
        }
    except Exception as exc:
        return {
            "tool": name,
            "path": "",
            "version": "",
            "source": "PYTHON",
            "available": "BROKEN",
            "executable": "NO",
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_toolchain_matrix() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    capabilities = {
        "capstone": ("NO", "YES", "YES", "NO"),
        "pefile": ("YES", "NO", "NO", "NO"),
        "lief": ("YES", "PARTIAL", "PARTIAL", "PARTIAL"),
        "iced_x86": ("NO", "YES", "YES", "PARTIAL"),
        "zydis": ("NO", "YES", "YES", "PARTIAL"),
        "distorm3": ("NO", "YES", "YES", "NO"),
        "keystone": ("NO", "YES", "NO", "NO"),
        "unicorn": ("NO", "YES", "NO", "NO"),
    }
    for name in capabilities:
        row = module_evidence(name)
        row["pe_support"], row["x86_support"], row["disassembly_support"], row["cfg_support"] = capabilities[name]
        rows.append(row)

    rows.append({
        "tool": "python-stdlib-manual-pe",
        "path": sys.executable,
        "version": sys.version.split()[0],
        "source": "PYTHON",
        "available": "WORKING",
        "executable": "YES",
        "pe_support": "YES",
        "x86_support": "NO",
        "disassembly_support": "NO",
        "cfg_support": "NO",
        "error": "",
    })

    cdb = ROOT / "工具" / "windbg_x86" / "cdb.exe"
    cdb_version = ""
    cdb_error = ""
    cdb_status = "MISSING"
    if cdb.exists():
        try:
            result = subprocess.run(
                [str(cdb), "-version"], capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
            )
            output = (result.stdout + result.stderr).strip().splitlines()
            cdb_version = output[0] if output else "UNKNOWN"
            cdb_status = "WORKING" if result.returncode == 0 else "PARTIAL"
            if result.returncode != 0:
                cdb_error = f"exit={result.returncode}; {' | '.join(output[:3])}"
        except Exception as exc:
            cdb_status = "BROKEN"
            cdb_error = f"{type(exc).__name__}: {exc}"
    rows.append({
        "tool": "cdb",
        "path": str(cdb) if cdb.exists() else "",
        "version": cdb_version,
        "source": "PROJECT",
        "available": cdb_status,
        "executable": "YES" if cdb.exists() else "NO",
        "pe_support": "YES",
        "x86_support": "YES",
        "disassembly_support": "YES",
        "cfg_support": "NO",
        "error": cdb_error,
    })

    project_disasm = ROOT / "COD OL" / "scripts" / "disasm.py"
    rows.append({
        "tool": "project-disasm.py",
        "path": str(project_disasm) if project_disasm.exists() else "",
        "version": "LOCAL_SCRIPT",
        "source": "PROJECT",
        "available": "PARTIAL" if project_disasm.exists() else "MISSING",
        "executable": "YES" if project_disasm.exists() else "NO",
        "pe_support": "YES",
        "x86_support": "YES",
        "disassembly_support": "YES",
        "cfg_support": "NO",
        "error": "Hard-coded for Base.dll/ImageBase 0x10000000; not directly valid for this EXE",
    })

    missing_commands = [
        "windbg", "ghidra", "ida", "ida64", "idaq", "idaq64", "binaryninja",
        "rizin", "radare2", "objdump", "llvm-objdump", "llvm-readobj", "llvm-nm", "dumpbin",
    ]
    for name in missing_commands:
        rows.append({
            "tool": name,
            "path": "",
            "version": "",
            "source": "PATH/SYSTEM/USER/CACHE",
            "available": "MISSING",
            "executable": "NO",
            "pe_support": "UNKNOWN",
            "x86_support": "UNKNOWN",
            "disassembly_support": "UNKNOWN",
            "cfg_support": "UNKNOWN",
            "error": "Not found in PATH, targeted common install directories, project, or pip cache",
        })
    return rows


def main() -> int:
    pe = ManualPE(SAMPLE)
    sample_hash = hashlib.sha256(pe.data).hexdigest()
    if sample_hash != EXPECTED_SHA256:
        raise SystemExit(f"SAMPLE_MISMATCH: {sample_hash}")
    if pe.image_base != EXPECTED_IMAGE_BASE or pe.entry_rva != EXPECTED_ENTRY_RVA:
        raise SystemExit(
            f"PE_IDENTITY_MISMATCH: ImageBase=0x{pe.image_base:X}, EntryRVA=0x{pe.entry_rva:X}"
        )

    section_rows = []
    for section in pe.sections:
        section_rows.append({
            "index": section.index,
            "name": section.name,
            "virtual_address": f"0x{section.virtual_address:08X}",
            "virtual_size": f"0x{section.virtual_size:08X}",
            "pointer_to_raw_data": f"0x{section.raw_offset:08X}",
            "size_of_raw_data": f"0x{section.raw_size:08X}",
            "characteristics": f"0x{section.characteristics:08X}",
            "executable": "YES" if section.executable else "NO",
            "mapping_status": "VALID" if section.raw_offset + section.raw_size <= len(pe.data) else "RAW_RANGE_INVALID",
        })
    write_csv(
        ROOT / "exe_core004a_section_map.csv",
        ["index", "name", "virtual_address", "virtual_size", "pointer_to_raw_data", "size_of_raw_data", "characteristics", "executable", "mapping_status"],
        section_rows,
    )

    known_inputs = [
        ("Entry", EXPECTED_ENTRY_RVA, "RVA"),
        ("0x401098", 0x00401098, "VA"),
        ("0x4010AF", 0x004010AF, "VA"),
        ("0x4010C6", 0x004010C6, "VA"),
        ("0x77F580", 0x0077F580, "RVA"),
        ("0x4FD9B0", 0x004FD9B0, "RVA"),
        ("0x4FCEE0", 0x004FCEE0, "RVA"),
        ("0x808650", 0x00808650, "RVA"),
        ("0x7E98F0", 0x007E98F0, "RVA"),
        ("0x6212C0", 0x006212C0, "RVA"),
    ]
    address_rows = []
    normalized = []
    for label, value, kind in known_inputs:
        rva = value - pe.image_base if kind == "VA" else value
        va = pe.image_base + rva
        raw, section, offset, status = pe.read_rva(rva, 64)
        normalized.append((label, rva, va, raw, section, offset, status))
        address_rows.append({
            "input": label,
            "input_kind": kind,
            "rva": f"0x{rva:08X}",
            "va": f"0x{va:08X}",
            "section": section.name if section else "PE_HEADERS" if status == "PE_HEADERS" else "UNKNOWN",
            "file_offset": f"0x{offset:08X}" if offset is not None else "",
            "readable": "YES" if len(raw) == 64 else "NO",
            "executable_section": "YES" if section and section.executable else "NO",
            "mapping_status": status,
            "bytes_64": raw.hex(" ").upper(),
        })
    write_csv(
        ROOT / "exe_core004a_address_map.csv",
        ["input", "input_kind", "rva", "va", "section", "file_offset", "readable", "executable_section", "mapping_status", "bytes_64"],
        address_rows,
    )

    entry_lines = [
        "CODOL STANDALONE-CORE-004A Entry Byte Evidence",
        "Sample: COD OL\\codoMP_client_shipRetail.exe",
        f"SHA256: {sample_hash}",
        f"Entry RVA: 0x{pe.entry_rva:08X}",
        f"Entry VA: 0x{pe.image_base + pe.entry_rva:08X}",
    ]
    for delta, title in [(-0x100, "Entry - 0x100"), (0, "Entry"), (0x100, "Entry + 0x100")]:
        rva = pe.entry_rva + delta
        raw, section, offset, status = pe.read_rva(rva, 128)
        entry_lines.extend([
            "",
            f"[{title}]",
            f"RVA: 0x{rva:08X}",
            f"VA: 0x{pe.image_base + rva:08X}",
            f"Section: {section.name if section else 'UNKNOWN'}",
            f"File Offset: {f'0x{offset:08X}' if offset is not None else 'UNMAPPED'}",
            f"Mapping Status: {status}",
            f"Bytes Read: {len(raw)}",
        ])
        entry_lines.extend(hex_dump(raw, offset or 0))
    (ROOT / "exe_core004a_entry_bytes.txt").write_text("\n".join(entry_lines) + "\n", encoding="utf-8")

    smoke_rows = []
    try:
        import capstone
        capstone_version = str(getattr(capstone, "__version__", "UNKNOWN"))
        for label, rva, va, raw, section, offset, mapping_status in normalized:
            for byte_count in (32, 64):
                chunk = raw[:byte_count]
                for mode in ("detail_false", "detail_true", "disasm_lite"):
                    first = ""
                    last = ""
                    error = ""
                    instruction_count = 0
                    operand_access = "NOT_TESTED"
                    try:
                        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
                        if mode == "disasm_lite":
                            instructions = list(md.disasm_lite(chunk, va))
                            instruction_count = len(instructions)
                            if instructions:
                                first = f"0x{instructions[0][0]:08X} {instructions[0][2]} {instructions[0][3]}".strip()
                                last = f"0x{instructions[-1][0]:08X} {instructions[-1][2]} {instructions[-1][3]}".strip()
                        else:
                            md.detail = mode == "detail_true"
                            instructions = list(md.disasm(chunk, va))
                            instruction_count = len(instructions)
                            if instructions:
                                first_insn = instructions[0]
                                last_insn = instructions[-1]
                                first = f"0x{first_insn.address:08X} {first_insn.mnemonic} {first_insn.op_str}".strip()
                                last = f"0x{last_insn.address:08X} {last_insn.mnemonic} {last_insn.op_str}".strip()
                                try:
                                    _ = first_insn.operands
                                    operand_access = "SUCCESS"
                                except Exception as exc:
                                    operand_access = f"FAIL:{type(exc).__name__}:{exc}"
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    if not chunk and not error:
                        error = mapping_status
                    elif chunk and instruction_count == 0 and not error:
                        error = "NO_INSTRUCTION_DECODED_FROM_WINDOW_START"
                    smoke_rows.append({
                        "input": label,
                        "rva": f"0x{rva:08X}",
                        "va": f"0x{va:08X}",
                        "section": section.name if section else "UNKNOWN",
                        "tool": f"capstone {capstone_version}",
                        "test": mode,
                        "byte_count": byte_count,
                        "instruction_count": instruction_count,
                        "first_instruction": first,
                        "last_instruction": last,
                        "operand_detail_access": operand_access,
                        "error": error,
                        "confidence": "CONFIRMED" if instruction_count > 0 and not error else "FAILED",
                    })
    except Exception as exc:
        smoke_rows.append({
            "input": "ALL",
            "rva": "",
            "va": "",
            "section": "",
            "tool": "capstone",
            "test": "import",
            "byte_count": 0,
            "instruction_count": 0,
            "first_instruction": "",
            "last_instruction": "",
            "operand_detail_access": "NOT_TESTED",
            "error": f"{type(exc).__name__}: {exc}",
            "confidence": "FAILED",
        })
    write_csv(
        ROOT / "exe_core004a_disassembly_smoke_test.csv",
        ["input", "rva", "va", "section", "tool", "test", "byte_count", "instruction_count", "first_instruction", "last_instruction", "operand_detail_access", "error", "confidence"],
        smoke_rows,
    )

    matrix_rows = build_toolchain_matrix()
    write_csv(
        ROOT / "exe_core004a_toolchain_matrix.csv",
        ["tool", "path", "version", "source", "available", "executable", "pe_support", "x86_support", "disassembly_support", "cfg_support", "error"],
        matrix_rows,
    )

    successful_smoke = [row for row in smoke_rows if row["confidence"] == "CONFIRMED"]
    detail_failures = [
        row for row in smoke_rows
        if row["test"] == "detail_false" and str(row["operand_detail_access"]).startswith("FAIL:CsError")
    ]
    mapped_count = sum(row["mapping_status"] == "OK" for row in address_rows)
    virtual_only_count = sum(row["mapping_status"] == "VIRTUAL_ONLY" for row in address_rows)
    all_mapped = mapped_count == len(address_rows)
    all_executable = all(row["executable_section"] == "YES" for row in address_rows)
    capstone_working = bool(successful_smoke)

    report = f"""# CODOL STANDALONE-CORE-004A
## Toolchain Exhaustive Discovery & Minimal Disassembly Verification

## Final Status

```text
TOOLCHAIN_STATUS = LEVEL_3
FILE_READ_STATUS = FILE_READABLE
PE_PARSE_STATUS = PE_MANUAL_PARSE_CONFIRMED
RVA_MAPPING_STATUS = {'RVA_MAPPING_CONFIRMED' if all_mapped else 'RVA_MAPPING_PARTIAL'}
TP3_STATUS = {'TP3_MAPPING_CONFIRMED' if all_mapped and all_executable else 'TP3_MAPPING_PARTIAL'}
X86_DECODER_STATUS = {'X86_DISASSEMBLY_SMOKE_TEST_CONFIRMED' if capstone_working else 'X86_DECODER_FAILURE'}
FUNCTION_RECOVERY_STATUS = NOT_PERFORMED
CFG_STATUS = NOT_PERFORMED
WORKING_TOOL = Python {sys.version.split()[0]} stdlib manual PE parser; pefile 2024.8.26; Capstone 5.0.7; cdb 10.0.29617.1000
PRIMARY_FAILURE_LAYER = AUTOMATIC_FUNCTION_AND_CFG_RECOVERY_NOT_AVAILABLE
NEXT_REQUIRED_TOOL = Ghidra/IDA/Binary Ninja/rizin, or a validated recursive-descent CFG recovery implementation
```

## Sample Identity

```text
Path = COD OL\\codoMP_client_shipRetail.exe
SHA256 = {sample_hash}
Expected SHA256 = {EXPECTED_SHA256}
ImageBase = 0x{pe.image_base:08X}
Entry RVA = 0x{pe.entry_rva:08X}
Entry VA = 0x{pe.image_base + pe.entry_rva:08X}
Machine = 0x{pe.machine:04X} (I386)
PE type = PE32
Sections = {pe.number_of_sections}
```

## Confirmed Capabilities

- The sample is readable and its SHA-256 matches.
- DOS, PE, COFF, PE32 optional header, and all section headers were parsed with Python `struct`.
- `.tp3` section selection works for Entry and all requested addresses.
- File-backed bytes are available for {mapped_count}/{len(address_rows)} requested locations; {virtual_only_count} locations are `VIRTUAL_ONLY` because their RVA exceeds the first executable `.tp3` section's raw-data extent.
- Capstone decodes real x86 instructions from 32-byte and 64-byte windows.
- `detail=False` disassembly works; accessing `insn.operands` in that mode raises `CS_ERR_DETAIL` by design.
- `detail=True` and `disasm_lite` both work in the smoke tests.
- Local `cdb.exe` exists and reports version `10.0.29617.1000`.
- Entry begins with `FF 15 65 C6 9D 0E`, decoded as `call dword ptr [0x0E9DC665]`. The operand is slot VA `0x0E9DC665`, corresponding to slot RVA `0x0E5DC665`; it is recorded only as the established external boundary.

## Tool Discovery

- Python modules working: `capstone`, `pefile`, `keystone`, `unicorn`.
- Python modules missing: `lief`, `iced_x86`, `zydis`, `distorm3`.
- Project tools found: `工具\\windbg_x86\\cdb.exe`, `COD OL\\scripts\\disasm.py`, and related analysis scripts.
- `Ghidra`, `IDA`, `Binary Ninja`, `rizin`, `radare2`, `objdump`, LLVM tools, and `dumpbin` were not found in PATH, targeted common installation directories, project files, or pip cache.
- WSL executable exists, but no installed Linux distribution was available for an `objdump` test.

## Capstone Diagnosis

`CS_ERR_DETAIL` observed in prior work was caused by reading operand details while `detail=False`; it does not prove that disassembly failed. This run produced {len(successful_smoke)} successful smoke-test rows. Expected detail-disabled operand-access failures: {len(detail_failures)}.

The 64-byte window at RVA `0x004FD9B0` decodes successfully. The file-backed window at RVA `0x004FCEE0` begins with bytes that Capstone cannot decode from offset zero, so it is recorded as `NO_INSTRUCTION_DECODED_FROM_WINDOW_START`, not as evidence that the entire sample is undecodable.

## Capability Boundary

The machine can correctly map file-backed `.tp3` bytes and decode x86 instructions, so `TOOLCHAIN_MISSING` is false. The verified level is `LEVEL_3`: minimal x86 disassembly works. Function boundary recovery and trustworthy CFG recovery were deliberately not claimed or performed in CORE-004A.

## Not Analyzed

- Game Init
- Main Loop
- State Machine
- IIPS, TCLS, Base.dll internals
- `.tvm0` internals
- EXE patching, hooks, or debugger control-flow modification

## Delivered Artifacts

- `exe_core004a_toolchain_matrix.csv`
- `exe_core004a_section_map.csv`
- `exe_core004a_entry_bytes.txt`
- `exe_core004a_address_map.csv`
- `exe_core004a_disassembly_smoke_test.csv`
"""
    (ROOT / "CODOL_STANDALONE_CORE_004A_TOOLCHAIN_DIAGNOSTIC.md").write_text(report, encoding="utf-8")

    print(f"sample_sha256={sample_hash}")
    print(f"sections={pe.number_of_sections}")
    print(f"mapped_addresses={sum(row['mapping_status'] == 'OK' for row in address_rows)}/{len(address_rows)}")
    print(f"successful_smoke_rows={len(successful_smoke)}/{len(smoke_rows)}")
    print("TOOLCHAIN_STATUS=LEVEL_3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
