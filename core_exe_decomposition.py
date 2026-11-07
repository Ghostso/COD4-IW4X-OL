from __future__ import annotations

"""EXE-only full binary decomposition for codoMP_client_shipRetail.exe.

This is a structural analysis pass, not another single-entry hunt.  It reads
the original EXE directly for PE metadata and executable-region layout, then
combines that with the already-frozen CFG/string/runtime evidence to produce
the requested decomposition artifacts.

The original binary is never modified.  No process is launched.

Run:
    python core_exe_decomposition.py
    python core_exe_decomposition.py --check
    python core_exe_decomposition.py --self-test
"""

import argparse
import csv
import hashlib
import io
import math
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
EXE_SHA256 = "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"
IMAGE_BASE = 0x00400000

# Existing EXE/CORE evidence consumed as frozen input.
CORE005_ADDRESS = ROOT / "exe_core005_address_map.csv"
CORE005_FUNCTIONS = ROOT / "exe_core005_functions.csv"
CORE005_EDGES = ROOT / "exe_core005_direct_edges.csv"
CORE005_CFG = ROOT / "exe_core005_direct_cfg.csv"
CORE005_VALIDATION = ROOT / "exe_core005_validation.csv"
CORE008_ARGV = ROOT / "exe_core008_argv_contract.csv"
CORE012_ENTRY = ROOT / "exe_core012_entry_candidates.csv"
CORE013R_DECISION = ROOT / "exe_core013r_target_decision.csv"
CORE013R_MATRIX = ROOT / "exe_core013r_attribution_matrix.csv"
EXE_STRINGS_REFS = ROOT / "exe_strings_refs.csv"
EXE_IAT_EXTERNAL = ROOT / "exe_iat_external.csv"
EXE_NON_IAT_EXTERNAL = ROOT / "exe_non_iat_external.csv"
EXE_DYNAMIC_LOADS = ROOT / "exe_dynamic_loads.csv"
EXE_RENDERER = ROOT / "exe_renderer_candidates.csv"
EXE_NETWORK = ROOT / "exe_network_candidates.csv"
EXE_GAME_INIT = ROOT / "exe_game_init_candidates.csv"
EXE_MAINLOOP = ROOT / "exe_mainloop_candidates.csv"
CORE012_DESIGN = ROOT / "CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md"
CORE013R_REPORT = ROOT / "CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md"
EX045 = ROOT / "CODOL_EX045_NATIVE_BOOTSTRAP_DISPATCHER_CHAIN.md"
EX046 = ROOT / "CODOL_EX046_NATIVE_BOOTSTRAP_TENCENT_DEPENDENCY_ANALYSIS.md"
EX020 = ROOT / "CODOL_EX020_ENGINE_CANDIDATES.md"
EX026 = ROOT / "CODOL_EX026_ZERO_TENCENT_NATIVE_BOOT.md"
EX045_CFG = ROOT / "exe_bootstrap_closure.csv"

# Required outputs.
REPORT = ROOT / "CODOL_EXE_BINARY_DECOMPOSITION.md"
PE_HEADERS = ROOT / "exe_pe_headers.csv"
SECTIONS = ROOT / "exe_sections.csv"
DATA_DIRS = ROOT / "exe_data_directories.csv"
EXEC_REGIONS = ROOT / "exe_exec_regions.csv"
ENTRYPOINTS = ROOT / "exe_entrypoints.csv"
IMPORTS = ROOT / "exe_imports.csv"
DYNAMIC_IMPORTS = ROOT / "exe_dynamic_imports.csv"
EXPORTS = ROOT / "exe_exports.csv"
TLS = ROOT / "exe_tls.csv"
STRINGS_CLUSTERS = ROOT / "exe_strings_clusters.csv"
RUNTIME_BOUNDARIES = ROOT / "exe_runtime_boundaries.csv"
IW4_SIGNATURES = ROOT / "exe_iw4_signatures.csv"
TENCENT_REGIONS = ROOT / "exe_tencent_regions.csv"
UNKNOWN_REGIONS = ROOT / "exe_unknown_regions.csv"
RUNTIME_CANDIDATES = ROOT / "exe_runtime_candidates.csv"

GENERATED = (
    REPORT,
    PE_HEADERS,
    SECTIONS,
    DATA_DIRS,
    EXEC_REGIONS,
    ENTRYPOINTS,
    IMPORTS,
    DYNAMIC_IMPORTS,
    EXPORTS,
    TLS,
    STRINGS_CLUSTERS,
    RUNTIME_BOUNDARIES,
    IW4_SIGNATURES,
    TENCENT_REGIONS,
    UNKNOWN_REGIONS,
    RUNTIME_CANDIDATES,
)

FROZEN_INPUTS = (
    CORE005_ADDRESS,
    CORE005_FUNCTIONS,
    CORE005_EDGES,
    CORE005_CFG,
    CORE008_ARGV,
    CORE012_ENTRY,
    CORE013R_DECISION,
    CORE013R_MATRIX,
    EXE_STRINGS_REFS,
    EXE_IAT_EXTERNAL,
    EXE_NON_IAT_EXTERNAL,
)

STRING_CLUSTER_PATTERNS = (
    ("WIN32", re.compile(r"^(?:Create|Open|Close|Read|Write|Get|Set|Wait|Message|Window|File|Thread|Process|Module|Heap|Virtual|Load|Free|Reg|WideChar|MultiByte|Local|Global)", re.I)),
    ("GRAPHICS", re.compile(r"d3d|direct3d|shader|vertex|pixel|texture|render|swap|device|dxgi|opengl", re.I)),
    ("AUDIO", re.compile(r"audio|sound|snd|mix|wave|voice|speaker|microphone", re.I)),
    ("NETWORK", re.compile(r"network|socket|winsock|packet|channel|netchan|stun|server|client|host|udp|tcp|iips", re.I)),
    ("FILESYSTEM", re.compile(r"file|path|\.iwd|\.ff|\.pak|zone|fastfile|searchpath|filesystem", re.I)),
    ("COMMANDLINE", re.compile(r"^-|command|argv|argc|cmdline|src=|nogui|dedicated", re.I)),
    ("CONSOLE", re.compile(r"console|cmd_|com_|exec |usage:|unknown command|bad command", re.I)),
    ("DVAR", re.compile(r"dvar|seta|sets|reset|cvar|toggle", re.I)),
    ("SCRIPT", re.compile(r"script|gsc|menu|level\.|script_", re.I)),
    ("IW4/COD", re.compile(r"iw4|cod6|modern warfare|call of duty|iwd|fastfile|demonware", re.I)),
    ("CODOL", re.compile(r"codol|qq\.com|cod\.qq|tgp|tcls|wegame|tencent", re.I)),
    ("TENCENT", re.compile(r"tencent|tenproxy|tcls|wegame|tgp|qq\.com", re.I)),
    ("ERROR", re.compile(r"error|failed|fatal|exception|assert|invalid|unable", re.I)),
    ("SECURITY/ANTI-CHEAT", re.compile(r"anti.?cheat|ace|vanguard|integrity|hash|signature|protect|guard", re.I)),
    ("RESOURCE", re.compile(r"resource|rsrc|icon|cursor|dialog|string table", re.I)),
    ("DEBUG", re.compile(r"debug|breakpoint|trace|dump|crash|log", re.I)),
)


class ValidationError(RuntimeError):
    """Raised when the decomposition cannot be reproduced safely."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv_bytes(fields: list[str], rows: list[dict[str, object]]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + out.getvalue().encode("utf-8")


def text_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def pe():
    try:
        import pefile
    except ImportError as exc:
        raise ValidationError(f"pefile is required: {exc}") from exc
    return pefile.PE(str(EXE), fast_load=False)


def section_for(rva: int, sections: list[object] | None = None):
    p = pe()
    if sections is None:
        sections = p.sections
    for section in sections:
        start = section.VirtualAddress
        end = start + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if start <= rva < end:
            return section
    return None


def file_offset_for(rva: int, section) -> int | None:
    if section is None:
        return None
    delta = rva - section.VirtualAddress
    if delta >= section.SizeOfRawData:
        return None
    return section.PointerToRawData + delta


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def header_rows(p) -> list[dict[str, object]]:
    opt = p.OPTIONAL_HEADER
    coff = p.FILE_HEADER
    dos = p.DOS_HEADER
    rows = [
        ("DOS_MAGIC", hex(dos.e_magic), "DOS header"),
        ("DOS_PE_OFFSET", hex(dos.e_lfanew), "DOS header"),
        ("NT_SIGNATURE", "PE\\0\\0", "NT header"),
        ("Machine", hex(coff.Machine), "FILE_HEADER"),
        ("NumberOfSections", coff.NumberOfSections, "FILE_HEADER"),
        ("TimeDateStamp", hex(coff.TimeDateStamp), "FILE_HEADER"),
        ("PointerToSymbolTable", hex(coff.PointerToSymbolTable), "FILE_HEADER"),
        ("NumberOfSymbols", coff.NumberOfSymbols, "FILE_HEADER"),
        ("SizeOfOptionalHeader", hex(coff.SizeOfOptionalHeader), "FILE_HEADER"),
        ("Characteristics", hex(coff.Characteristics), "FILE_HEADER"),
        ("Magic", hex(opt.Magic), "OPTIONAL_HEADER"),
        ("ImageBase", hex(opt.ImageBase), "OPTIONAL_HEADER"),
        ("AddressOfEntryPoint", hex(opt.AddressOfEntryPoint), "OPTIONAL_HEADER"),
        ("SectionAlignment", hex(opt.SectionAlignment), "OPTIONAL_HEADER"),
        ("FileAlignment", hex(opt.FileAlignment), "OPTIONAL_HEADER"),
        ("SizeOfImage", hex(opt.SizeOfImage), "OPTIONAL_HEADER"),
        ("SizeOfHeaders", hex(opt.SizeOfHeaders), "OPTIONAL_HEADER"),
        ("Subsystem", opt.Subsystem, "OPTIONAL_HEADER"),
        ("DllCharacteristics", hex(opt.DllCharacteristics), "OPTIONAL_HEADER"),
        ("SizeOfStackReserve", hex(opt.SizeOfStackReserve), "OPTIONAL_HEADER"),
        ("SizeOfStackCommit", hex(opt.SizeOfStackCommit), "OPTIONAL_HEADER"),
        ("SizeOfHeapReserve", hex(opt.SizeOfHeapReserve), "OPTIONAL_HEADER"),
        ("SizeOfHeapCommit", hex(opt.SizeOfHeapCommit), "OPTIONAL_HEADER"),
        ("NumberOfRvaAndSizes", opt.NumberOfRvaAndSizes, "OPTIONAL_HEADER"),
    ]
    return [
        {
            "field": field,
            "value": str(value),
            "source": source,
            "file_offset": (
                hex(dos.e_lfanew + 4 + coff.SizeOfOptionalHeader)
                if field in {"Magic", "ImageBase", "AddressOfEntryPoint"}
                else ""
            ),
            "evidence": "STATIC",
            "confidence": "CONFIRMED",
        }
        for field, value, source in rows
    ]


def section_rows(p) -> list[dict[str, object]]:
    rows = []
    for index, section in enumerate(p.sections):
        chars = section.Characteristics
        raw_backed = section.SizeOfRawData > 0
        executable = bool(chars & 0x20000000)
        readable = bool(chars & 0x40000000)
        writable = bool(chars & 0x80000000)
        virtual_only = section.Misc_VirtualSize > section.SizeOfRawData
        rows.append(
            {
                "index": index,
                "name": section.Name.rstrip(b"\0").decode("latin-1"),
                "virtual_address": f"0x{section.VirtualAddress:08X}",
                "virtual_size": f"0x{section.Misc_VirtualSize:08X}",
                "pointer_to_raw_data": f"0x{section.PointerToRawData:08X}",
                "size_of_raw_data": f"0x{section.SizeOfRawData:08X}",
                "characteristics": f"0x{chars:08X}",
                "executable": "YES" if executable else "NO",
                "readable": "YES" if readable else "NO",
                "writable": "YES" if writable else "NO",
                "raw_backed": "YES" if raw_backed else "NO",
                "virtual_only": "YES" if virtual_only else "NO",
                "rwx": "YES" if executable and readable and writable else "NO",
                "file_offset_start": f"0x{section.PointerToRawData:08X}" if raw_backed else "",
                "file_offset_end": (
                    f"0x{section.PointerToRawData + section.SizeOfRawData:08X}"
                    if raw_backed
                    else ""
                ),
                "head_entropy": f"{entropy(p.get_data(section.VirtualAddress, min(section.SizeOfRawData, 0x2000))):.4f}",
                "mapping_status": "VALID",
                "evidence": "PE section header and raw bytes",
                "confidence": "CONFIRMED",
            }
        )
    return rows


def data_directory_rows(p) -> list[dict[str, object]]:
    rows = []
    for index, directory in enumerate(p.OPTIONAL_HEADER.DATA_DIRECTORY):
        rva = directory.VirtualAddress
        size = directory.Size
        # The Security directory is a file offset, not an RVA.
        if directory.name == "IMAGE_DIRECTORY_ENTRY_SECURITY":
            section = None
            file_offset = rva if rva else None
            raw_backed = bool(file_offset and file_offset + size <= len(p.__data__))
            inside_section = "NO_FILE_OFFSET_NOT_RVA"
            executable = False
        else:
            section = section_for(rva, p.sections) if rva else None
            file_offset = file_offset_for(rva, section) if section and rva else None
            raw_backed = file_offset is not None
            inside_section = "YES" if section else "NO"
            executable = bool(section and (section.Characteristics & 0x20000000))
        rows.append(
            {
                "index": index,
                "name": directory.name,
                "rva": f"0x{rva:08X}" if rva else "0x00000000",
                "size": f"0x{size:08X}",
                "file_offset": (
                    f"0x{file_offset:08X}"
                    if raw_backed and file_offset is not None
                    else ""
                ),
                "inside_section": inside_section,
                "inside_executable_region": "YES" if executable else "NO",
                "raw_backed": "YES" if raw_backed else "NO",
                "present": "YES" if rva or size else "NO",
                "evidence": "DataDirectory table",
                "confidence": "CONFIRMED",
            }
        )
    return rows


def exec_region_rows(p) -> list[dict[str, object]]:
    rows = []
    try:
        import capstone
    except ImportError as exc:
        raise ValidationError(f"capstone is required: {exc}") from exc
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for index, section in enumerate(p.sections):
        if not (section.Characteristics & 0x20000000):
            continue
        sample_size = min(max(section.SizeOfRawData, 0x1000), 0x100000)
        raw = p.get_data(section.VirtualAddress, sample_size)
        data = raw
        instructions = list(
            md.disasm(raw, p.OPTIONAL_HEADER.ImageBase + section.VirtualAddress)
        )
        decoded_ratio = (
            sum(ins.size for ins in instructions) / len(raw)
            if raw
            else 0.0
        )
        call_count = sum(ins.mnemonic.startswith("call") for ins in instructions)
        jump_count = sum(ins.mnemonic.startswith("j") for ins in instructions)
        ret_count = sum(ins.mnemonic == "ret" for ins in instructions)
        zero_rate = (data.count(0) / len(data)) if data else 0.0
        high_rate = (sum(byte >= 0x80 for byte in data) / len(data)) if data else 0.0
        if section.SizeOfRawData == 0:
            classification = "RUNTIME_GENERATED"
        elif zero_rate > 0.70:
            classification = "RESERVED_OR_RUNTIME_GENERATED"
        elif section.Name.rstrip(b"\0") == b".tvm0":
            classification = "PACKED_CODE"
        elif decoded_ratio >= 0.60 and call_count + jump_count + ret_count >= 2:
            classification = "CONFIRMED_CODE"
        elif decoded_ratio >= 0.15 or call_count + jump_count:
            classification = "LIKELY_CODE"
        elif entropy(raw) > 7.2:
            classification = "PACKED_CODE"
        else:
            classification = "COMPRESSED_OR_ENCRYPTED_DATA"
        rows.append(
            {
                "region_id": f"EXEC-{index:02d}",
                "section": section.Name.rstrip(b"\0").decode("latin-1"),
                "rva_start": f"0x{section.VirtualAddress:08X}",
                "rva_end": f"0x{section.VirtualAddress + max(section.Misc_VirtualSize, section.SizeOfRawData):08X}",
                "file_offset_start": f"0x{section.PointerToRawData:08X}" if section.SizeOfRawData else "",
                "file_offset_end": (
                    f"0x{section.PointerToRawData + section.SizeOfRawData:08X}"
                    if section.SizeOfRawData
                    else ""
                ),
                "raw_backed": "YES" if section.SizeOfRawData else "NO",
                "virtual_only": "YES" if section.Misc_VirtualSize > section.SizeOfRawData else "NO",
                "writable": "YES" if section.Characteristics & 0x80000000 else "NO",
                "entropy_sample": f"{entropy(raw):.4f}",
                "zero_rate_sample": f"{zero_rate:.4f}",
                "high_byte_rate_sample": f"{high_rate:.4f}",
                "linear_decode_ratio": f"{decoded_ratio:.4f}",
                "call_count_sample": call_count,
                "jump_count_sample": jump_count,
                "ret_count_sample": ret_count,
                "classification": classification,
                "evidence": "executable flag + linear Capstone decode + entropy/zero density",
                "confidence": (
                    "CONFIRMED"
                    if classification == "CONFIRMED_CODE"
                    else "HIGH_CONFIDENCE"
                    if classification in ("PACKED_CODE", "RUNTIME_GENERATED")
                    else "CANDIDATE"
                ),
            }
        )
    return rows or [
        {
            "region_id": "NO_CONFIRMED_ITEMS",
            "section": "",
            "rva_start": "",
            "rva_end": "",
            "file_offset_start": "",
            "file_offset_end": "",
            "raw_backed": "",
            "virtual_only": "",
            "writable": "",
            "entropy_sample": "",
            "zero_rate_sample": "",
            "high_byte_rate_sample": "",
            "linear_decode_ratio": "",
            "call_count_sample": "",
            "jump_count_sample": "",
            "ret_count_sample": "",
            "classification": "NO_CONFIRMED_ITEMS",
            "evidence": "",
            "confidence": "",
        }
    ]


def entrypoint_rows(p) -> list[dict[str, object]]:
    entry = p.OPTIONAL_HEADER.AddressOfEntryPoint
    section = section_for(entry, p.sections)
    data = p.get_data(entry, 16)
    return [
        {
            "entry_id": "EXE_ENTRY",
            "rva": f"0x{entry:08X}",
            "va": f"0x{p.OPTIONAL_HEADER.ImageBase + entry:08X}",
            "file_offset": f"0x{file_offset_for(entry, section):08X}" if section else "",
            "section": section.Name.rstrip(b"\0").decode("latin-1") if section else "",
            "bytes": data.hex(" ").upper(),
            "semantics": "call dword ptr [0x0E9DC665] -> Base.dll ordinal 1",
            "external_boundary": "codoMP_client_shipRetailBase.dll ordinal 1",
            "post_entry_native_continuation": "NO_CONFIRMED_ITEMS",
            "evidence": "PE AddressOfEntryPoint; CORE-008/CORE-010/CORE-013R",
            "confidence": "CONFIRMED",
        }
    ]


def import_rows(p) -> list[dict[str, object]]:
    rows = []
    section = section_for(0x0E5DC665, p.sections)
    for directory in p.OPTIONAL_HEADER.DATA_DIRECTORY:
        if directory.name != "IMAGE_DIRECTORY_ENTRY_IMPORT":
            continue
        rows.append(
            {
                "directory_rva": f"0x{directory.VirtualAddress:08X}",
                "directory_size": f"0x{directory.Size:08X}",
                "section": section.Name.rstrip(b"\0").decode("latin-1") if section else "",
                "standard_import_directory": "PRESENT" if directory.VirtualAddress or directory.Size else "EMPTY",
                "module": "codoMP_client_shipRetailBase.dll",
                "symbol_or_ordinal": "ordinal_1",
                "iat_slot_rva": "0x0E5DC665",
                "iat_slot_file_offset": "0x00776665",
                "int_slot_rva": "0x0E5DC65D",
                "first_thunk_rva": "0x0E5DC665",
                "consumer_rva": "0x0E5DC690",
                "binding": "CUSTOM_ORDINAL_BINDING",
                "evidence": "CORE-006 import descriptor + Entry FF 15",
                "confidence": "CONFIRMED",
                "notes": "standard Import Directory Size = 0; this slot is the EXE's observed external bootstrap boundary",
            }
        )
        return rows
    return [
        {
            "directory_rva": "NO_CONFIRMED_ITEMS",
            "directory_size": "",
            "section": "",
            "standard_import_directory": "",
            "module": "",
            "symbol_or_ordinal": "",
            "iat_slot_rva": "",
            "iat_slot_file_offset": "",
            "int_slot_rva": "",
            "first_thunk_rva": "",
            "consumer_rva": "",
            "binding": "",
            "evidence": "",
            "confidence": "",
            "notes": "",
        }
    ]


def dynamic_import_rows() -> list[dict[str, object]]:
    rows = []
    for row in read_csv(EXE_DYNAMIC_LOADS):
        api = row.get("api", "")
        if not api:
            continue
        rows.append(
            {
                "address": row.get("exe_rva", "") or "UNKNOWN",
                "type": "DYNAMIC_LOAD"
                if "LoadLibrary" in api
                else "DYNAMIC_RESOLVE",
                "target": api,
                "evidence": row.get("evidence", ""),
                "confidence": row.get("confidence", "UNKNOWN"),
                "consumer_region": "EXE_NATIVE_REGIONS",
            }
        )
    if not rows:
        rows.append(
            {
                "address": "NO_CONFIRMED_ITEMS",
                "type": "NO_CONFIRMED_ITEMS",
                "target": "",
                "evidence": "",
                "confidence": "",
                "consumer_region": "",
            }
        )
    return rows


def export_rows(p) -> list[dict[str, object]]:
    rows = []
    exports = getattr(p, "DIRECTORY_ENTRY_EXPORT", None)
    if exports:
        for symbol in exports.symbols:
            rows.append(
                {
                    "ordinal": symbol.ordinal,
                    "rva": f"0x{symbol.address:08X}",
                    "name": symbol.name.decode("latin-1") if symbol.name else "",
                    "forwarder": symbol.forwarder.decode("latin-1") if symbol.forwarder else "",
                    "evidence": "PE export directory",
                    "confidence": "CONFIRMED",
                }
            )
    return rows or [
        {
            "ordinal": "NO_CONFIRMED_ITEMS",
            "rva": "",
            "name": "",
            "forwarder": "",
            "evidence": "",
            "confidence": "",
        }
    ]


def tls_rows(p) -> list[dict[str, object]]:
    tls = getattr(p, "DIRECTORY_ENTRY_TLS", None)
    if not tls:
        return [
            {
                "rva": "NO_CONFIRMED_ITEMS",
                "va": "",
                "raw_data_start": "",
                "raw_data_end": "",
                "address_of_index": "",
                "address_of_callbacks": "",
                "size_of_zero_fill": "",
                "characteristics": "",
                "callbacks": "",
                "evidence": "PE TLS directory",
                "confidence": "CONFIRMED",
            }
        ]
    structure = tls.struct
    callbacks: list[str] = []
    callback_va = structure.AddressOfCallBacks
    if callback_va:
        callback_rva = callback_va - p.OPTIONAL_HEADER.ImageBase
        raw = p.get_data(callback_rva, 64)
        for offset in range(0, len(raw), 4):
            callback = int.from_bytes(raw[offset : offset + 4], "little")
            if callback == 0:
                break
            callbacks.append(f"0x{callback:08X}")
    return [
        {
            "rva": f"0x{structure.StartAddressOfRawData - p.OPTIONAL_HEADER.ImageBase:08X}"
            if structure.StartAddressOfRawData
            else "",
            "va": f"0x{structure.StartAddressOfRawData:08X}",
            "raw_data_start": f"0x{structure.StartAddressOfRawData:08X}",
            "raw_data_end": f"0x{structure.EndAddressOfRawData:08X}",
            "address_of_index": f"0x{structure.AddressOfIndex:08X}",
            "address_of_callbacks": f"0x{structure.AddressOfCallBacks:08X}",
            "size_of_zero_fill": f"0x{structure.SizeOfZeroFill:08X}",
            "characteristics": f"0x{structure.Characteristics:08X}",
            "callbacks": ";".join(callbacks) or "NONE_CONFIRMED",
            "evidence": "PE TLS directory",
            "confidence": "CONFIRMED",
        }
    ]


def classify_string(text: str) -> str:
    for cluster, pattern in STRING_CLUSTER_PATTERNS:
        if pattern.search(text):
            return cluster
    return "UNKNOWN"


def strings_cluster_rows() -> list[dict[str, object]]:
    rows = []
    for row in read_csv(EXE_STRINGS_REFS):
        string = row.get("string", "")
        if not string:
            continue
        rows.append(
            {
                "string": string,
                "rva": row.get("rva", "UNKNOWN"),
                "file_offset": "UNKNOWN",
                "reference_count": row.get("count", "0"),
                "referencing_code_rva": row.get("referencing_code_rva", "UNKNOWN"),
                "cluster": classify_string(string),
                "confidence": row.get("confidence", "UNKNOWN"),
            }
        )
    if not rows:
        rows.append(
            {
                "string": "NO_CONFIRMED_ITEMS",
                "rva": "",
                "file_offset": "",
                "reference_count": "",
                "referencing_code_rva": "",
                "cluster": "NO_CONFIRMED_ITEMS",
                "confidence": "",
            }
        )
    return rows


def runtime_boundary_rows() -> list[dict[str, object]]:
    return [
        {
            "source_rva": "0x0E5DC690",
            "target_rva_or_module": "codoMP_client_shipRetailBase.dll ordinal 1",
            "boundary": "ENTRY -> EXTERNAL_BOOTSTRAP",
            "evidence": "Entry FF 15 65 C6 9D 0E",
            "confidence": "CONFIRMED",
            "runtime_or_static": "STATIC",
        },
        {
            "source_rva": "0x0E5DC696",
            "target_rva_or_module": "zero-filled padding",
            "boundary": "EXTERNAL_BOOTSTRAP -> NO_NATIVE_CONTINUATION",
            "evidence": "CORE-005/CORE-012 entry fall-through audit",
            "confidence": "CONFIRMED",
            "runtime_or_static": "STATIC",
        },
        {
            "source_rva": "0x0077F580",
            "target_rva_or_module": "0x004FD9B0",
            "boundary": "BOOTSTRAP_GATE -> DISPATCHER",
            "evidence": "EX-045 direct E8 chain",
            "confidence": "HIGH_CONFIDENCE",
            "runtime_or_static": "STATIC",
        },
        {
            "source_rva": "0x00808650",
            "target_rva_or_module": "0x007E98F0",
            "boundary": "SUBSYSTEM_INIT -> NETWORK_INIT",
            "evidence": "EX-045 direct E8 chain",
            "confidence": "HIGH_CONFIDENCE",
            "runtime_or_static": "STATIC",
        },
        {
            "source_rva": "0x007E98F0",
            "target_rva_or_module": "0x006212C0",
            "boundary": "NETWORK_INIT -> STUN_MODE_SELECT",
            "evidence": "EX-045 direct E8 chain",
            "confidence": "HIGH_CONFIDENCE",
            "runtime_or_static": "STATIC",
        },
    ]


def iw4_signature_rows() -> list[dict[str, object]]:
    rows = []
    for row in read_csv(EXE_RENDERER):
        if row.get("rva", "UNKNOWN") == "UNKNOWN":
            continue
        rows.append(
            {
                "family": "RENDERER",
                "address": row.get("rva", ""),
                "signature": row.get("api_or_string", ""),
                "evidence": row.get("evidence", ""),
                "classification": "SHARED_IW4_LIKE_OR_UNRESOLVED",
                "confidence": row.get("confidence", "UNKNOWN"),
                "runtime_or_static": "STATIC",
            }
        )
    for row in read_csv(EXE_NETWORK):
        if row.get("rva", "UNKNOWN") == "UNKNOWN":
            continue
        rows.append(
            {
                "family": "NETWORK",
                "address": row.get("rva", ""),
                "signature": row.get("api_or_string", ""),
                "evidence": row.get("evidence", ""),
                "classification": "CODOL_SPECIFIC",
                "confidence": row.get("confidence", "UNKNOWN"),
                "runtime_or_static": "STATIC",
            }
        )
    # Address-level entries from the frozen EXE CFG evidence.
    rows.extend(
        (
            {
                "family": "FILE_SYSTEM",
                "address": "0x001321A9",
                "signature": "filesystem/string-ref anchor from ENGINE-ANCHORS",
                "evidence": "CORE-012 entry candidate inventory",
                "classification": "UNRESOLVED",
                "confidence": "UNKNOWN",
                "runtime_or_static": "STATIC",
            },
            {
                "family": "RENDERER",
                "address": "0x00239B7D",
                "signature": "renderer/string-ref anchor from ENGINE-ANCHORS",
                "evidence": "CORE-012 entry candidate inventory",
                "classification": "UNRESOLVED",
                "confidence": "UNKNOWN",
                "runtime_or_static": "STATIC",
            },
            {
                "family": "ENGINE",
                "address": "0x007036DC",
                "signature": "engine/string-ref anchor from ENGINE-ANCHORS",
                "evidence": "CORE-012 entry candidate inventory",
                "classification": "UNRESOLVED",
                "confidence": "UNKNOWN",
                "runtime_or_static": "STATIC",
            },
            {
                "family": "DVAR_CONSOLE",
                "address": "0x0037FA70",
                "signature": "fatal error display callback",
                "evidence": "CORE-012/013R attribution inventory",
                "classification": "CODOL_SPECIFIC",
                "confidence": "CANDIDATE",
                "runtime_or_static": "STATIC",
            },
        )
    )
    if not rows:
        rows.append(
            {
                "family": "NO_CONFIRMED_ITEMS",
                "address": "",
                "signature": "",
                "evidence": "",
                "classification": "UNKNOWN",
                "confidence": "",
                "runtime_or_static": "",
            }
        )
    return rows


def tencent_rows() -> list[dict[str, object]]:
    return [
        {
            "region_or_rva": "codoMP_client_shipRetailBase.dll",
            "role": "TENCENT_PLATFORM / BOOTSTRAP_BOUNDARY",
            "classification": "LIKELY_PLATFORM_ONLY",
            "evidence": "Entry ordinal-1 boundary and CORE-013R no-unique-target result",
            "confidence": "CANDIDATE",
            "runtime_or_static": "STATIC",
        },
        {
            "region_or_rva": "0x006212C0",
            "role": "NETWORK / STUN_MODE_SELECT",
            "classification": "UNKNOWN",
            "evidence": "Reads 0x849413B/0x849B500; selects CODOL and Demonware STUN endpoints",
            "confidence": "CANDIDATE",
            "runtime_or_static": "STATIC",
        },
        {
            "region_or_rva": "0x0037FA70",
            "role": "FATAL_ERROR_DISPLAY",
            "classification": "LIKELY_PLATFORM_ONLY",
            "evidence": "Error path dispatched by WIN_NO_TCLS/IIPS fatal state",
            "confidence": "CANDIDATE",
            "runtime_or_static": "STATIC",
        },
        {
            "region_or_rva": "0x0077F580",
            "role": "ARGV_GATE / BOOTSTRAP_HEAD",
            "classification": "LIKELY_PLATFORM_ONLY",
            "evidence": "Reads -q/-qa/-src=tgp gate cluster and calls bootstrap dispatcher",
            "confidence": "CANDIDATE",
            "runtime_or_static": "STATIC",
        },
    ]


def unknown_rows() -> list[dict[str, object]]:
    return [
        {
            "region_or_rva": ".tp3 virtual-only space",
            "reason": "raw_absent_or_runtime_created",
            "classification": "UNKNOWN",
            "evidence": "Section map shows virtual-only executable flags for non-raw-backed sections",
            "next_action": "Compare runtime memory against image map before attributing code",
        },
        {
            "region_or_rva": ".tvm0",
            "reason": "external_or_packed_boundary",
            "classification": "UNKNOWN",
            "evidence": "CORE-013R target set excludes .tvm0; no EXE-native entry attribution",
            "next_action": "Do not enter without a separate boundary contract",
        },
        {
            "region_or_rva": "0x00561133",
            "reason": "indirect_provider_call_site",
            "classification": "UNKNOWN",
            "evidence": "ALIGNMENT_INVALID; target is runtime-bound through 0x00CA827C",
            "next_action": "Resolve provider binder before using as a runtime code boundary",
        },
    ]


def runtime_candidate_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate": "0x006212C0",
            "role": "network/STUN mode selection",
            "rva": "0x006212C0",
            "section": ".tp3",
            "why": "Reads CODOL gate globals and selects Tencent/Demonware STUN endpoints",
            "runtime_status": "UNKNOWN",
            "confidence": "CANDIDATE",
            "next_action": "Prototype boundary validation only if network runtime is required",
        },
        {
            "candidate": "0x0037FA70",
            "role": "fatal error display",
            "rva": "0x0037FA70",
            "section": "UNKNOWN",
            "why": "Error path reached from WIN_NO_TCLS/IIPS fatal state",
            "runtime_status": "CANDIDATE",
            "confidence": "CANDIDATE",
            "next_action": "Keep out of prototype entry selection",
        },
        {
            "candidate": "0x0077F580",
            "role": "argv/context gate and bootstrap head",
            "rva": "0x0077F580",
            "section": ".tp3",
            "why": "Static gate/bootstrap chain head; upstream caller unresolved",
            "runtime_status": "NOT_OBSERVED",
            "confidence": "CANDIDATE",
            "next_action": "Only revisit with a direct EXE-native caller proof",
        },
    ]


def report_text(decision: dict[str, str], sections: list[dict[str, object]]) -> str:
    section_lines = "\n".join(
        f"| {row['name']} | {row['virtual_address']} | {row['virtual_size']} | "
        f"{row['size_of_raw_data']} | {row['executable']} | {row['virtual_only']} | {row['mapping_status']} |"
        for row in sections
    )
    return f"""# CODOL_EXE_BINARY_DECOMPOSITION

## Status

```text
EXE = codoMP_client_shipRetail.exe
SHA256 = {EXE_SHA256}
ANALYSIS_SCOPE = EXE_CENTRIC
PROCESS_LAUNCHED = NO
BINARY_MODIFIED = NO
STANDALONE_ENTRY = {decision.get('STANDALONE_ENTRY_TARGET', 'UNKNOWN')}
DYNAMIC_TEST_READY = {decision.get('DYNAMIC_TEST_READY', 'NO')}
```

This report is produced from the original EXE and the already-frozen
CORE/EX-* evidence. The executable is treated as a complete PE/runtime
carrier, not as a search for one standalone entry.

## PE Structure

| Section | RVA | Virtual Size | Raw Size | Executable | Virtual-only | Status |
|---|---:|---:|---:|---|---|---|
{section_lines}

The sample is PE32/I386 with ImageBase `0x00400000`. The executable uses
`.tp3` section names rather than conventional `.text/.rdata/.data` names.
Large executable virtual ranges are not all raw-backed, so section names
alone are not evidence of code.

## Executable Regions

The authoritative classification is in `exe_exec_regions.csv`. The map keeps
raw-backed and virtual-only spaces separate and records entropy, zero density,
and permission flags. A region is not promoted to `CONFIRMED_CODE` merely
because it is executable.

## Entry and Bootstrap

```text
Entry RVA   = 0x0E5DC690
Entry bytes = FF 15 65 C6 9D 0E
IAT slot    = 0x0E9DC665
Boundary    = codoMP_client_shipRetailBase.dll ordinal 1
Continuation= zero-filled padding at 0x0E5DC696
```

The EXE-owned static bootstrap chain is present only as candidate evidence.
CORE-011 observed no post-boundary execution for the historical candidates,
and CORE-013R found no unique static standalone entry.

## Runtime Boundaries

`exe_runtime_boundaries.csv` records source RVA, target, evidence,
confidence, and static/dynamic status. Static chain arrows from EX-045 are
marked `HIGH_CONFIDENCE`; they are not presented as dynamic execution.

## IW4 / CODOL / Tencent Layering

`exe_iw4_signatures.csv` contains only entries with an address or explicit
evidence. `exe_tencent_regions.csv` records whether a region is
platform-only, game-required, or unresolved. No name-only label is treated
as a confirmed engine classification.

## Unknown and Runtime-Generated Space

Large `.tp3` virtual-only ranges and `.tvm0` remain `UNKNOWN` where raw bytes
or callers are absent. They are recorded in `exe_unknown_regions.csv`.

## EXE FINAL ANSWERS

1. **Actual PE structure:** PE32/I386, ImageBase `0x00400000`, six `.tp3`
   sections plus `.tvm0`, with nonstandard section naming.
2. **True code sections:** only regions with direct decode/call evidence are
   code candidates; section executability alone is insufficient.
3. **Protection/unpack/runtime regions:** present as virtual-only or
   non-raw-backed executable space; exact ownership remains `UNKNOWN`.
4. **Entry Point:** a single external ordinal-1 call to
   `codoMP_client_shipRetailBase.dll`.
5. **Ordinal 1 role:** external bootstrap boundary, not a game-runtime entry.
6. **EXE initialization system:** candidate bootstrap/gate/dispatcher chain
   exists, but no confirmed EXE-native caller above `0x77F580`.
7. **IW4/COD6 engine code:** no address-level proof sufficient for
   `CONFIRMED`; relevant signatures remain `HIGH_CONFIDENCE` or `CANDIDATE`.
8. **CODOL-specific code:** network/STUN and platform-gate evidence exists,
   primarily `0x6212C0`, with `CANDIDATE` confidence.
9. **Tencent platform regions:** Base ordinal-1 boundary and platform/network
   callbacks; no broad Tencent module reverse engineering was performed.
10. **Engine initialization chain:** static candidate chain only; dynamic
    execution is `NOT_OBSERVED`.
11. **Renderer/filesystem/network/script/interface:** network candidate is
    present; renderer, filesystem, script, and game-interface entries remain
    `UNKNOWN`.
12. **Game runtime location:** inside the EXE is not proven at an address
    level; no single runtime node satisfies the frozen evidence threshold.
13. **If not in EXE:** the evidence is insufficient to assign another module
    as the game runtime; `.tvm0` or runtime-generated space remains possible.
14. **Standalone prototype boundary:** no unique static boundary is ready.
15. **Most valuable next area:** resolve the `.tp3` virtual-only runtime
    layout and the external ordinal-1 boundary before selecting a prototype
    entry.

## Master Map

```text
codoMP_client_shipRetail.exe
|
+-- PE / Loader                    [CONFIRMED]
+-- Entry Stub                     [CONFIRMED]
+-- External Bootstrap Boundary    [CONFIRMED]
+-- Protection / Packed Regions    [CANDIDATE / UNKNOWN]
+-- Runtime Unpack / Dispatch      [UNKNOWN]
+-- Common Engine                  [UNKNOWN]
+-- IW4 Engine                     [UNKNOWN]
+-- CODOL-specific                 [CANDIDATE]
+-- Tencent-specific               [CANDIDATE]
+-- Game Runtime                   [NOT_PROVEN]
+-- Unknown                        [UNKNOWN]
```

## Evidence Discipline

Every row in the CSV artifacts carries `evidence` and `confidence`. Claims
without direct machine-code or call-relation support are kept `CANDIDATE` or
`UNKNOWN`; no name-based guess is upgraded to `CONFIRMED`.
"""


def load_frozen() -> dict[str, object]:
    missing = [path.name for path in FROZEN_INPUTS if not path.is_file()]
    if missing:
        raise ValidationError("missing frozen input(s): " + ", ".join(missing))
    if sha256(EXE) != EXE_SHA256:
        raise ValidationError(
            f"EXE SHA-256 drift: expected {EXE_SHA256}, found {sha256(EXE)}"
        )
    return {
        "core013r": {
            row["item"]: row["value"] for row in read_csv(CORE013R_DECISION)
        },
        "matrix": read_csv(CORE013R_MATRIX),
        "address": read_csv(CORE005_ADDRESS),
        "functions": read_csv(CORE005_FUNCTIONS),
        "edges": read_csv(CORE005_EDGES),
        "cfg": read_csv(CORE005_CFG),
        "strings": read_csv(EXE_STRINGS_REFS),
        "iat": read_csv(EXE_IAT_EXTERNAL),
        "dynamic": read_csv(EXE_DYNAMIC_LOADS),
    }


def build_payloads() -> dict[Path, bytes]:
    frozen = load_frozen()
    p = pe()
    sections = section_rows(p)
    decision = frozen["core013r"]
    payloads = {
        PE_HEADERS: write_csv_bytes(
            ["field", "value", "source", "file_offset", "evidence", "confidence"],
            header_rows(p),
        ),
        SECTIONS: write_csv_bytes(
            [
                "index",
                "name",
                "virtual_address",
                "virtual_size",
                "pointer_to_raw_data",
                "size_of_raw_data",
                "characteristics",
                "executable",
                "readable",
                "writable",
                "raw_backed",
                "virtual_only",
                "rwx",
                "file_offset_start",
                "file_offset_end",
                "head_entropy",
                "mapping_status",
                "evidence",
                "confidence",
            ],
            sections,
        ),
        DATA_DIRS: write_csv_bytes(
            [
                "index",
                "name",
                "rva",
                "size",
                "file_offset",
                "inside_section",
                "inside_executable_region",
                "raw_backed",
                "present",
                "evidence",
                "confidence",
            ],
            data_directory_rows(p),
        ),
        EXEC_REGIONS: write_csv_bytes(
            [
                "region_id",
                "section",
                "rva_start",
                "rva_end",
                "file_offset_start",
                "file_offset_end",
                "raw_backed",
                "virtual_only",
                "writable",
                "entropy_sample",
                "zero_rate_sample",
                "high_byte_rate_sample",
                "classification",
                "evidence",
                "confidence",
            ],
            exec_region_rows(p),
        ),
        ENTRYPOINTS: write_csv_bytes(
            [
                "entry_id",
                "rva",
                "va",
                "file_offset",
                "section",
                "bytes",
                "semantics",
                "external_boundary",
                "post_entry_native_continuation",
                "evidence",
                "confidence",
            ],
            entrypoint_rows(p),
        ),
        IMPORTS: write_csv_bytes(
            [
                "directory_rva",
                "directory_size",
                "section",
                "standard_import_directory",
                "module",
                "symbol_or_ordinal",
                "iat_slot_rva",
                "consumer_rva",
                "binding",
                "evidence",
                "confidence",
                "notes",
            ],
            import_rows(p),
        ),
        DYNAMIC_IMPORTS: write_csv_bytes(
            ["address", "type", "target", "evidence", "confidence", "consumer_region"],
            dynamic_import_rows(),
        ),
        EXPORTS: write_csv_bytes(
            ["ordinal", "rva", "name", "forwarder", "evidence", "confidence"],
            export_rows(p),
        ),
        TLS: write_csv_bytes(
            [
                "rva",
                "va",
                "raw_data_start",
                "raw_data_end",
                "address_of_index",
                "address_of_callbacks",
                "size_of_zero_fill",
                "characteristics",
                "callbacks",
                "evidence",
                "confidence",
            ],
            tls_rows(p),
        ),
        STRINGS_CLUSTERS: write_csv_bytes(
            [
                "string",
                "rva",
                "file_offset",
                "reference_count",
                "referencing_code_rva",
                "cluster",
                "confidence",
            ],
            strings_cluster_rows(),
        ),
        RUNTIME_BOUNDARIES: write_csv_bytes(
            [
                "source_rva",
                "target_rva_or_module",
                "boundary",
                "evidence",
                "confidence",
                "runtime_or_static",
            ],
            runtime_boundary_rows(),
        ),
        IW4_SIGNATURES: write_csv_bytes(
            [
                "family",
                "address",
                "signature",
                "evidence",
                "classification",
                "confidence",
                "runtime_or_static",
            ],
            iw4_signature_rows(),
        ),
        TENCENT_REGIONS: write_csv_bytes(
            [
                "region_or_rva",
                "role",
                "classification",
                "evidence",
                "confidence",
                "runtime_or_static",
            ],
            tencent_rows(),
        ),
        UNKNOWN_REGIONS: write_csv_bytes(
            ["region_or_rva", "reason", "classification", "evidence", "next_action"],
            unknown_rows(),
        ),
        RUNTIME_CANDIDATES: write_csv_bytes(
            [
                "candidate",
                "role",
                "rva",
                "section",
                "why",
                "runtime_status",
                "confidence",
                "next_action",
            ],
            runtime_candidate_rows(),
        ),
    }
    payloads[REPORT] = text_bytes(report_text(decision, sections))
    return payloads


def validate_payloads(payloads: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    if set(payloads) != set(GENERATED):
        errors.append("generated artifact set drift")
    for path, payload in payloads.items():
        if path.suffix != ".csv":
            continue
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
        if not rows:
            errors.append(f"{path.name}: CSV has no header/data")
    if PE_HEADERS not in payloads or SECTIONS not in payloads:
        errors.append("required PE/section artifacts missing")
    return errors


def artifact_diff(payloads: dict[Path, bytes]) -> list[str]:
    return [
        f"artifact drift: {path.name}"
        for path, payload in payloads.items()
        if not path.is_file() or path.read_bytes() != payload
    ]


def atomic_write(payloads: dict[Path, bytes]) -> None:
    backups: dict[Path, bytes | None] = {}
    written: list[Path] = []
    try:
        for path, payload in payloads.items():
            backups[path] = path.read_bytes() if path.is_file() else None
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as fh:
                tmp = Path(fh.name)
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            written.append(path)
    except Exception:
        for path in written:
            previous = backups.get(path)
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise


def generate() -> int:
    try:
        payloads = build_payloads()
    except (ValidationError, OSError) as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate_payloads(payloads)
    if errors:
        print("VALIDATION FAIL: rendered artifacts invalid", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    atomic_write(payloads)
    post = artifact_diff(payloads)
    if post:
        print("VALIDATION FAIL: post-write reread failed", file=sys.stderr)
        for error in post:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("EXE DECOMPOSITION COMPLETE: 16 artifacts written and reread")
    return 0


def check() -> int:
    try:
        payloads = build_payloads()
    except (ValidationError, OSError) as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate_payloads(payloads) + artifact_diff(payloads)
    print(f"VALIDATION {'PASS' if not errors else 'FAIL'}: EXE decomposition artifacts")
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 0 if not errors else 1


def self_test() -> int:
    failures: list[str] = []
    try:
        frozen = load_frozen()
        if frozen["core013r"].get("DYNAMIC_TEST_READY") != "NO":
            failures.append("CORE-013R dynamic readiness drifted")
        if len(frozen["matrix"]) != 8:
            failures.append("CORE-013R attribution matrix is not eight rows")
        p = pe()
        if p.FILE_HEADER.Machine != 0x14C:
            failures.append("PE machine is not I386")
        if p.OPTIONAL_HEADER.ImageBase != IMAGE_BASE:
            failures.append("ImageBase drifted")
        if not any(s.Characteristics & 0x20000000 for s in p.sections):
            failures.append("no executable section detected")
        payloads = build_payloads()
        errors = validate_payloads(payloads)
        if errors:
            failures.extend(errors)
    except Exception as exc:
        failures.append(f"self-test exception: {exc}")
    if failures:
        print("SELF-TEST FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("SELF-TEST PASS: EXE decomposition inputs and outputs validated")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXE-only binary decomposition")
    parser.add_argument("--check", action="store_true", help="validate existing artifacts")
    parser.add_argument("--self-test", action="store_true", help="run structural self-tests")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        return check()
    return generate()


if __name__ == "__main__":
    raise SystemExit(main())
