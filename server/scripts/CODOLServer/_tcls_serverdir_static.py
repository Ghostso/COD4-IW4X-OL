"""Read-only static inventory for the CODOL/TCLS ServerDir chain.

The script deliberately does not launch a process, modify a file, or touch
network state. It reports PE metadata, selected strings, ID encodings, and
relevant imports from the local binaries.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
from pathlib import Path

import pefile


ROOT = Path(__file__).resolve().parents[1]

MODULES = {
    "codol-tcls": ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll",
    "codol-dir": ROOT / "COD OL" / "TCLS" / "Tenio" / "Dir.dll",
    "codol-june": ROOT / "COD OL" / "TCLS" / "Tenio" / "June.dll",
    "codol-client": ROOT / "COD OL" / "TCLS" / "Client.exe",
    "codol-tclsclient": ROOT / "COD OL" / "TCLS" / "TCLSClient.dll",
    "codol-clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "wegame-core": ROOT / "WeGame" / "tcls" / "tcls_core.exe",
    "wegame-common": ROOT / "WeGame" / "tcls" / "common.dll",
    "wegame-rail4tcls": ROOT / "WeGame" / "apps" / "Rail" / "rail4tcls.dll",
}

STRING_TERMS = (
    "ServerDir",
    "ServerList",
    "ReadServiceID",
    "ServiceID",
    "Service\\id",
    "CrossSvrID",
    "Cross\\id",
    "server_id",
    "ServerID",
    "ServerName",
    "ServerAppLen",
    "ServerAppData",
    "PlayerSelectedServer",
    "GetSelectedAPPID",
    "OutputNodeTree",
    "virURL",
    "DIRTREERSP",
    "lobbyLandingURL",
    "Get Game Server Info fail",
    "ERROR_INVALID_SERVER_ID",
    "select server failed",
    "Empty tree",
)

ID_VALUES = {
    "gameID=29": 29,
    "ServiceID=715019302": 715019302,
    "CrossSvrID=2102017": 2102017,
}

IMPORT_TERMS = (
    "CreateProcess",
    "CreateFileMapping",
    "OpenFileMapping",
    "MapViewOfFile",
    "LoadLibrary",
    "GetProcAddress",
    "send",
    "recv",
    "connect",
    "sendto",
    "recvfrom",
)


def section_for_offset(pe: pefile.PE, offset: int):
    for section in pe.sections:
        start = section.PointerToRawData
        end = start + section.SizeOfRawData
        if start <= offset < end:
            return section
    return None


def section_name(section) -> str:
    if section is None:
        return "?"
    return section.Name.rstrip(b"\0").decode("ascii", "replace")


def find_all(data: bytes, needle: bytes):
    result = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            return result
        result.append(offset)
        start = offset + 1


def print_strings(path: Path, data: bytes, pe: pefile.PE):
    for term in STRING_TERMS:
        for encoding in ("ascii", "utf-16le"):
            needle = term.encode(encoding)
            for offset in find_all(data, needle):
                rva = pe.get_rva_from_offset(offset)
                print(
                    "  string term={!r} encoding={} raw=0x{:x} rva=0x{:x} section={}".format(
                        term,
                        encoding,
                        offset,
                        rva,
                        section_name(section_for_offset(pe, offset)),
                    )
                )


def print_id_hits(data: bytes):
    for label, value in ID_VALUES.items():
        forms = (
            ("le32", struct.pack("<I", value)),
            ("be32", struct.pack(">I", value)),
            ("ascii", str(value).encode("ascii")),
            ("utf-16le", str(value).encode("utf-16le")),
        )
        hits = []
        for encoding, needle in forms:
            offsets = find_all(data, needle)
            if offsets:
                hits.append((encoding, ["0x{:x}".format(x) for x in offsets]))
        print("  id {} value={} hits={}".format(label, value, hits or "NONE"))


def print_imports(pe: pefile.PE):
    selected = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for descriptor in pe.DIRECTORY_ENTRY_IMPORT:
            dll = descriptor.dll.decode("ascii", "replace")
            for item in descriptor.imports:
                name = item.name.decode("ascii", "replace") if item.name else "ord{}".format(item.ordinal)
                if any(term.lower() in name.lower() for term in IMPORT_TERMS):
                    selected.append("{}!{}".format(dll, name))
    print("  imports={}".format(", ".join(selected) if selected else "NONE"))


def analyze(label: str, path: Path):
    print("\n=== {} ===".format(label))
    if not path.is_file():
        print("  MISSING {}".format(path))
        return
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=False)
    print("  path={}".format(path))
    print("  size={} sha256={}".format(len(data), hashlib.sha256(data).hexdigest()))
    print("  imagebase=0x{:x} entry_rva=0x{:x} machine=0x{:x}".format(
        pe.OPTIONAL_HEADER.ImageBase,
        pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        pe.FILE_HEADER.Machine,
    ))
    print_imports(pe)
    print_id_hits(data)
    print_strings(path, data, pe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "modules",
        nargs="*",
        choices=sorted(MODULES),
        default=sorted(MODULES),
        help="module labels to inspect; default: all known modules",
    )
    args = parser.parse_args()
    for label in args.modules:
        analyze(label, MODULES[label])


if __name__ == "__main__":
    main()
