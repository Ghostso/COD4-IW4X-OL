#!/usr/bin/env python3
"""Build a BO1/IW4/CODOL script builtin ownership matrix from primary files."""

from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Iterable


@dataclasses.dataclass(frozen=True)
class TableSpec:
    name: str
    vm: str
    kind: str
    family: str
    va: int
    count: int
    stride: int
    has_type: bool


BO1_TABLES = (
    TableSpec("server_functions", "server", "function", "generic", 0x00E08510, 383, 12, True),
    TableSpec("server_methods", "server", "method", "generic", 0x00E09708, 234, 12, True),
    TableSpec("server_player_methods", "server", "method", "player", 0x00CB4540, 154, 12, False),
    TableSpec("server_script_entity_methods", "server", "method", "script_entity", 0x00CC8550, 18, 12, False),
    TableSpec("server_vehicle_methods", "server", "method", "vehicle", 0x00CC8E30, 89, 12, False),
    TableSpec("server_hud_methods", "server", "method", "hud", 0x00CB8480, 26, 12, False),
    TableSpec("server_helicopter_methods", "server", "method", "helicopter", 0x00CBFFA0, 27, 12, False),
    TableSpec("server_actor_methods", "server", "method", "actor", 0x00D359D8, 77, 12, False),
    TableSpec("client_functions", "client", "function", "generic", 0x00E038B0, 154, 12, True),
    TableSpec("client_project_functions", "client", "function", "project", 0x00E04080, 26, 12, True),
    TableSpec("client_methods", "client", "method", "generic", 0x00C8A6A0, 111, 12, True),
    TableSpec("client_project_methods", "client", "method", "project", 0x00C8E660, 29, 12, True),
)

RESOLVER_PRIORITY = {
    "server_functions": 0,
    "server_player_methods": 0,
    "server_script_entity_methods": 1,
    "server_vehicle_methods": 2,
    "server_hud_methods": 3,
    "server_helicopter_methods": 4,
    "server_actor_methods": 5,
    "server_methods": 6,
    "client_functions": 0,
    "client_project_functions": 1,
    "client_methods": 0,
    "client_project_methods": 1,
}

P0_NAMES = {
    "allowads",
    "allowjump",
    "allowsprint",
    "clearperks",
    "delete",
    "disableweapons",
    "enableweapons",
    "finishplayerdamage",
    "freezecontrols",
    "getvelocity",
    "giveweapon",
    "isonground",
    "setmodel",
    "setorigin",
    "setperk",
    "setplayerangles",
    "setspawnweapon",
    "setweaponammoclip",
    "setweaponammostock",
    "spawn",
    "suicide",
    "switchtoweapon",
    "takeallweapons",
    "takeweapon",
    "unsetperk",
}

P1_NAMES = {
    "iprintln",
    "iprintlnbold",
    "newclienthudelem",
    "newhudelem",
    "newteamhudelem",
    "playfx",
    "playfxontag",
    "playsound",
    "setclientdvar",
    "setclientdvars",
    "setrank",
    "setscore",
}

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CALL_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
ASCII_C_STRING_RE = re.compile(rb"(?<![\x20-\x7E])(?P<value>[\x20-\x7E]{1,256})\0")
FUNCTION_DEFINITION_RE = re.compile(
    r"(?m)^\s*(?:[A-Za-z_][\w\\/]*::)?([A-Za-z_]\w*)\s*"
    r"\([^;{}\n]*\)\s*\{"
)


@dataclasses.dataclass(frozen=True)
class Section:
    name: str
    virtual_address: int
    virtual_size: int
    raw_offset: int
    raw_size: int
    characteristics: int


class PE32Image:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.data = self.path.read_bytes()
        if len(self.data) < 0x40 or self.data[:2] != b"MZ":
            raise ValueError(f"not a PE image: {self.path}")
        pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise ValueError(f"invalid PE signature: {self.path}")
        file_header = pe_offset + 4
        section_count = struct.unpack_from("<H", self.data, file_header + 2)[0]
        optional_size = struct.unpack_from("<H", self.data, file_header + 16)[0]
        optional = file_header + 20
        magic = struct.unpack_from("<H", self.data, optional)[0]
        if magic != 0x10B:
            raise ValueError(f"expected PE32 optional header, got 0x{magic:X}: {self.path}")
        self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
        self.size_of_headers = struct.unpack_from("<I", self.data, optional + 60)[0]
        section_table = optional + optional_size
        sections: list[Section] = []
        for index in range(section_count):
            offset = section_table + index * 40
            raw_name = self.data[offset : offset + 8].split(b"\0", 1)[0]
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", self.data, offset + 8
            )
            characteristics = struct.unpack_from("<I", self.data, offset + 36)[0]
            sections.append(
                Section(
                    raw_name.decode("ascii", errors="replace"),
                    virtual_address,
                    virtual_size,
                    raw_offset,
                    raw_size,
                    characteristics,
                )
            )
        self.sections = tuple(sections)

    def va_to_offset(self, va: int) -> int:
        rva = va - self.image_base
        if rva < 0:
            raise ValueError(f"VA 0x{va:08X} precedes image base")
        if rva < self.size_of_headers and rva < len(self.data):
            return rva
        for section in self.sections:
            extent = max(section.virtual_size, section.raw_size)
            if section.virtual_address <= rva < section.virtual_address + extent:
                delta = rva - section.virtual_address
                if delta >= section.raw_size:
                    raise ValueError(f"VA 0x{va:08X} lies in zero-filled section tail")
                offset = section.raw_offset + delta
                if offset >= len(self.data):
                    raise ValueError(f"VA 0x{va:08X} maps outside file")
                return offset
        raise ValueError(f"VA 0x{va:08X} is not mapped by a PE section")

    def offset_to_va(self, offset: int) -> int | None:
        if 0 <= offset < self.size_of_headers:
            return self.image_base + offset
        for section in self.sections:
            if section.raw_offset <= offset < section.raw_offset + section.raw_size:
                return self.image_base + section.virtual_address + offset - section.raw_offset
        return None

    def section_for_va(self, va: int) -> Section | None:
        rva = va - self.image_base
        for section in self.sections:
            if section.virtual_address <= rva < section.virtual_address + max(
                section.virtual_size, section.raw_size
            ):
                return section
        return None

    def read_u32(self, va: int) -> int:
        return struct.unpack_from("<I", self.data, self.va_to_offset(va))[0]

    def read_c_string(self, va: int, maximum: int = 256) -> str:
        offset = self.va_to_offset(va)
        end = self.data.find(b"\0", offset, min(len(self.data), offset + maximum + 1))
        if end < 0:
            raise ValueError(f"unterminated string at VA 0x{va:08X}")
        value = self.data[offset:end]
        if not value or any(byte < 0x20 or byte > 0x7E for byte in value):
            raise ValueError(f"invalid ASCII builtin name at VA 0x{va:08X}")
        return value.decode("ascii")


def extract_table(image: PE32Image, spec: TableSpec) -> list[dict[str, Any]]:
    registrations: list[dict[str, Any]] = []
    for index in range(spec.count):
        entry_va = spec.va + index * spec.stride
        name_va = image.read_u32(entry_va)
        handler_va = image.read_u32(entry_va + 4)
        if not name_va or not handler_va:
            raise ValueError(f"{spec.name}[{index}] contains a null pointer")
        name = image.read_c_string(name_va)
        handler_section = image.section_for_va(handler_va)
        if handler_section is None or not handler_section.characteristics & 0x20000000:
            raise ValueError(
                f"{spec.name}[{index}] handler 0x{handler_va:08X} is not executable"
            )
        registrations.append(
            {
                "index": index,
                "name": name,
                "normalized_name": name.lower(),
                "entry_va": f"0x{entry_va:08X}",
                "name_va": f"0x{name_va:08X}",
                "handler_va": f"0x{handler_va:08X}",
                "type": image.read_u32(entry_va + 8) if spec.has_type else None,
            }
        )
    return registrations


def strip_gsc_non_code(source: str) -> str:
    output = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        pair = source[index : index + 2]
        if state == "code":
            if pair == "//":
                output[index] = output[index + 1] = " "
                state = "line_comment"
                index += 2
                continue
            if pair in ("/*", "/#"):
                output[index] = output[index + 1] = " "
                state = "block_comment_hash" if pair == "/#" else "block_comment"
                index += 2
                continue
            if source[index] in ('"', "'"):
                quote = source[index]
                output[index] = " "
                state = "string"
                index += 1
                continue
        elif state == "line_comment":
            if source[index] == "\n":
                state = "code"
            else:
                output[index] = " "
            index += 1
            continue
        elif state in ("block_comment", "block_comment_hash"):
            close = "#/" if state == "block_comment_hash" else "*/"
            if pair == close:
                output[index] = output[index + 1] = " "
                state = "code"
                index += 2
                continue
            if source[index] != "\n":
                output[index] = " "
            index += 1
            continue
        elif state == "string":
            if source[index] == "\\" and index + 1 < len(source):
                output[index] = " "
                if source[index + 1] != "\n":
                    output[index + 1] = " "
                index += 2
                continue
            if source[index] == quote:
                output[index] = " "
                state = "code"
            elif source[index] != "\n":
                output[index] = " "
            index += 1
            continue
        index += 1
    return "".join(output)


def analyze_script_usage(
    root: Path, names: Iterable[str], extensions: tuple[str, ...] = (".gsc",)
) -> dict[str, dict[str, Any]]:
    normalized_names = sorted({name.lower() for name in names if IDENTIFIER_RE.fullmatch(name)})
    known_names = set(normalized_names)
    usage: dict[str, dict[str, Any]] = {
        name: {"call_count": 0, "file_count": 0, "files": []} for name in normalized_names
    }
    paths = sorted(
        path
        for extension in extensions
        for path in root.rglob(f"*{extension}")
    )
    for path in paths:
        source = path.read_text(encoding="utf-8", errors="replace")
        code = strip_gsc_non_code(source)
        definition_offsets: dict[str, set[int]] = collections.defaultdict(set)
        for match in FUNCTION_DEFINITION_RE.finditer(code):
            definition_offsets[match.group(1).lower()].add(match.start(1))
        relative = path.relative_to(root).as_posix()
        file_counts: collections.Counter[str] = collections.Counter()
        for match in CALL_RE.finditer(code):
            name = match.group("name").lower()
            if name in known_names and match.start("name") not in definition_offsets.get(name, set()):
                file_counts[name] += 1
        for name, count in file_counts.items():
            usage[name]["call_count"] += count
            usage[name]["file_count"] += 1
            usage[name]["files"].append(relative)
    return usage


def analyze_iw4_usage(root: Path, names: Iterable[str]) -> dict[str, dict[str, Any]]:
    return analyze_script_usage(root, names, (".gsc",))


def find_exact_c_strings(
    image: PE32Image, names: Iterable[str]
) -> dict[str, list[dict[str, Any]]]:
    normalized_names = {name.lower() for name in names}
    occurrences: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for match in ASCII_C_STRING_RE.finditer(image.data):
        try:
            name = match.group("value").decode("ascii").lower()
        except UnicodeDecodeError:
            continue
        if name not in normalized_names:
            continue
        offset = match.start("value")
        va = image.offset_to_va(offset)
        occurrences[name].append(
            {
                "file_offset": f"0x{offset:08X}",
                "va": f"0x{va:08X}" if va is not None else None,
            }
        )
    return occurrences


def priority_for(name: str) -> str:
    if name in P0_NAMES:
        return "p0_playable_loop"
    if name in P1_NAMES:
        return "p1_match_feedback"
    return "unclassified"


def build_matrix(
    bo1: PE32Image,
    codol: PE32Image,
    bo1_gsc_root: Path,
    iw4_gsc_root: Path | None,
) -> dict[str, Any]:
    extracted: dict[str, list[dict[str, Any]]] = {}
    by_binding: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for spec in BO1_TABLES:
        registrations = extract_table(bo1, spec)
        extracted[spec.name] = registrations
        for registration in registrations:
            by_binding[(spec.kind, registration["normalized_name"])].append(
                {
                    "table": spec.name,
                    "vm": spec.vm,
                    "kind": spec.kind,
                    "family": spec.family,
                    "handler_va": registration["handler_va"],
                    "type": registration["type"],
                    "table_index": registration["index"],
                    "resolver_priority": RESOLVER_PRIORITY[spec.name],
                }
            )

    bo1_server_names = {
        name
        for (_, name), registrations in by_binding.items()
        if any(registration["vm"] == "server" for registration in registrations)
    }
    bo1_client_names = {
        name
        for (_, name), registrations in by_binding.items()
        if any(registration["vm"] == "client" for registration in registrations)
    }
    bo1_gsc_usage = analyze_script_usage(bo1_gsc_root, bo1_server_names, (".gsc",))
    bo1_csc_usage = analyze_script_usage(bo1_gsc_root, bo1_client_names, (".csc",))
    iw4_usage = (
        analyze_iw4_usage(iw4_gsc_root, {name for _, name in by_binding})
        if iw4_gsc_root is not None
        else {}
    )
    codol_string_occurrences = find_exact_c_strings(
        codol, {name for _, name in by_binding}
    )
    entries: list[dict[str, Any]] = []
    ownership_counts: collections.Counter[str] = collections.Counter()
    for kind, name in sorted(by_binding):
        registrations = by_binding[(kind, name)]
        vms = {entry["vm"] for entry in registrations}
        if vms == {"server"}:
            reference_ownership = "server_only"
            binding_requirement = "server_binding_required_if_script_selected"
        elif vms == {"client"}:
            reference_ownership = "client_only"
            binding_requirement = "client_presentation_or_prediction"
        else:
            reference_ownership = "shared_name"
            binding_requirement = "split_authority_review"
        ownership_counts[reference_ownership] += 1
        occurrences = codol_string_occurrences.get(name, [])
        sorted_registrations = sorted(
            registrations,
            key=lambda registration: (
                registration["vm"],
                registration["resolver_priority"],
                registration["table_index"],
            ),
        )
        effective_registrations = {
            vm: next(
                (
                    registration
                    for registration in sorted_registrations
                    if registration["vm"] == vm
                ),
                None,
            )
            for vm in ("server", "client")
            if vm in vms
        }
        entries.append(
            {
                "id": f"{kind}:{name}",
                "name": name,
                "kind": kind,
                "priority": priority_for(name),
                "reference_ownership": reference_ownership,
                "server_binding_requirement": binding_requirement,
                "bo1_binding": {
                    "server_registered": "server" in vms,
                    "client_registered": "client" in vms,
                    "effective_registrations": effective_registrations,
                    "registrations": sorted_registrations,
                },
                "bo1_scripts": {
                    "usage_granularity": "name_only_function_method_not_disambiguated",
                    "server_gsc": bo1_gsc_usage.get(
                        name, {"call_count": 0, "file_count": 0, "files": []}
                    ),
                    "client_csc": bo1_csc_usage.get(
                        name, {"call_count": 0, "file_count": 0, "files": []}
                    ),
                },
                "cross_version_iw4_scripts": iw4_usage.get(
                    name, {"call_count": 0, "file_count": 0, "files": []}
                ),
                "codol_client_locator": {
                    "exact_c_string_present": bool(occurrences),
                    "exact_c_string_count": len(occurrences),
                    "occurrences": occurrences,
                    "native_match": {
                        "status": "unverified",
                        "function_va": None,
                        "evidence": [],
                    },
                },
            }
        )

    table_summary = []
    for spec in BO1_TABLES:
        registrations = extracted[spec.name]
        table_summary.append(
            {
                **dataclasses.asdict(spec),
                "va": f"0x{spec.va:08X}",
                "extracted_count": len(registrations),
                "unique_name_count": len({item["normalized_name"] for item in registrations}),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "inputs": {
            "bo1_server_exe": str(bo1.path),
            "bo1_server_sha256": hashlib.sha256(bo1.data).hexdigest().upper(),
            "codol_client_exe": str(codol.path),
            "codol_client_sha256": hashlib.sha256(codol.data).hexdigest().upper(),
            "bo1_gsc_root": str(bo1_gsc_root.resolve()),
            "iw4_gsc_root": str(iw4_gsc_root.resolve()) if iw4_gsc_root else None,
        },
        "summary": {
            "bo1_raw_registration_count": sum(len(items) for items in extracted.values()),
            "bo1_unique_binding_count": len(entries),
            "bo1_unique_name_count": len({entry["name"] for entry in entries}),
            "bo1_reference_ownership_counts": dict(sorted(ownership_counts.items())),
            "bo1_gsc_files_scanned": len(list(bo1_gsc_root.rglob("*.gsc"))),
            "bo1_csc_files_scanned": len(list(bo1_gsc_root.rglob("*.csc"))),
            "bo1_gsc_used_server_builtin_name_count": sum(
                usage["call_count"] > 0 for usage in bo1_gsc_usage.values()
            ),
            "bo1_csc_used_client_builtin_name_count": sum(
                usage["call_count"] > 0 for usage in bo1_csc_usage.values()
            ),
            "iw4_gsc_files_scanned": len(list(iw4_gsc_root.rglob("*.gsc")))
            if iw4_gsc_root
            else 0,
            "iw4_cross_version_name_count": sum(
                usage["call_count"] > 0 for usage in iw4_usage.values()
            ),
            "codol_exact_c_string_name_count": len(codol_string_occurrences),
            "p0_binding_count": sum(
                entry["priority"] == "p0_playable_loop" for entry in entries
            ),
        },
        "bo1_tables": table_summary,
        "entries": entries,
        "limitations": [
            "BO1 table membership is authoritative only for the referenced BO1 server build.",
            "Binding identity is kind plus name; function and method entries with the same text are not interchangeable.",
            "Script usage is currently counted by name and therefore does not disambiguate same-name function and method calls.",
            "IW4 usage is limited to the supplied GSC tree and excludes comments, strings, and local definitions.",
            "A CODOL exact C string is only a locator; native_match must be established from CODOL xrefs, disassembly, data flow, or runtime evidence.",
            "Absence of a CODOL string does not prove that equivalent native behavior is absent.",
            "Server-authoritative script behavior needs an ol_game_server binding even when a similarly named client native exists.",
            "Language opcodes such as thread, wait, waittill, notify, and endon are VM semantics rather than ordinary engine builtin registrations.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bo1-exe", type=Path, required=True)
    parser.add_argument("--codol-exe", type=Path, required=True)
    parser.add_argument("--bo1-gsc-root", type=Path, required=True)
    parser.add_argument("--iw4-gsc-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_matrix(
        PE32Image(args.bo1_exe),
        PE32Image(args.codol_exe),
        args.bo1_gsc_root.resolve(),
        args.iw4_gsc_root.resolve() if args.iw4_gsc_root else None,
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    summary = report["summary"]
    print(
        "Built builtin matrix: "
        f"{summary['bo1_raw_registration_count']} BO1 registrations, "
        f"{summary['bo1_unique_binding_count']} unique bindings, "
        f"{summary['bo1_unique_name_count']} unique names, "
        f"{summary['bo1_gsc_used_server_builtin_name_count']} used by BO1 GSC, "
        f"{summary['bo1_csc_used_client_builtin_name_count']} used by BO1 CSC"
    )
    print(f"Saved report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
