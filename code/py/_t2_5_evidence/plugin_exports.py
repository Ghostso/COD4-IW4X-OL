"""T-2.5 Stage 1: read the plugin DLL export table (read-only, no process attached).

This is a fact about the FILE on disk. It predicts, but does not replace, the
in-process export lookup that Stage D2 must perform on the loaded module.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
PLUGIN = Path(r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32")

REQUIRED = [
    "CODOL_GameServerSetEnabled",
    "CODOL_GameServerGetStatus",
    "CODOL_GameServerGetNetworkStatus",
    "CODOL_GameServerGetNetchanStatus",
    "CODOL_GameServerGetSessionStatus",
    "CODOL_GameServerConfigureGameState",
    "CODOL_GameServerGetGameStateStatus",
    "CODOL_GameServerGetConstantConfigStringStatus",
    "CODOL_GameServerGetTransportStatus",
]


def read_exports(path: Path):
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("no PE signature")
    coff = pe_offset + 4
    machine, section_count = struct.unpack_from("<HH", data, coff)
    size_of_optional = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    magic = struct.unpack_from("<H", data, optional)[0]
    is_64 = magic == 0x20B
    directory_offset = optional + (0x70 if is_64 else 0x60)
    export_rva, export_size = struct.unpack_from("<II", data, directory_offset)

    sections = []
    section_start = optional + size_of_optional
    for index in range(section_count):
        base = section_start + index * 40
        name = data[base:base + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, base + 8)
        sections.append((name, virtual_address, virtual_size, raw_pointer, raw_size))

    def rva_to_offset(rva):
        for _name, virtual_address, virtual_size, raw_pointer, raw_size in sections:
            if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
                return raw_pointer + (rva - virtual_address)
        return None

    export_offset = rva_to_offset(export_rva)
    if export_offset is None:
        raise ValueError("export directory not mapped")
    number_of_names = struct.unpack_from("<I", data, export_offset + 24)[0]
    address_of_names = struct.unpack_from("<I", data, export_offset + 32)[0]
    names_offset = rva_to_offset(address_of_names)
    names = []
    for index in range(number_of_names):
        name_rva = struct.unpack_from("<I", data, names_offset + index * 4)[0]
        offset = rva_to_offset(name_rva)
        end = data.index(b"\0", offset)
        names.append(data[offset:end].decode("ascii", "replace"))
    return {
        "machine": hex(machine),
        "is_64bit": is_64,
        "export_directory_rva": hex(export_rva),
        "export_count": number_of_names,
        "names": sorted(names),
    }


def main() -> int:
    info = read_exports(PLUGIN)
    present = {name: (name in info["names"]) for name in REQUIRED}
    codol = [name for name in info["names"] if name.startswith("CODOL_")]
    document = {
        "plugin_path": str(PLUGIN),
        "machine": info["machine"],
        "is_64bit": info["is_64bit"],
        "export_count": info["export_count"],
        "codol_export_count": len(codol),
        "required_exports": present,
        "required_present_count": sum(1 for value in present.values() if value),
        "required_missing": [name for name, value in present.items() if not value],
        "codol_exports": codol,
        "note": "FILE-level export table only; Stage D2 must re-verify against the LOADED module.",
    }
    (EVIDENCE / "plugin_export_table.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("machine=" + info["machine"] + " 64bit=" + str(info["is_64bit"]) +
          " exports=" + str(info["export_count"]) + " CODOL_*=" + str(len(codol)))
    print("required present " + str(document["required_present_count"]) + "/9")
    for name in REQUIRED:
        print("  " + ("OK   " if present[name] else "MISS ") + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
