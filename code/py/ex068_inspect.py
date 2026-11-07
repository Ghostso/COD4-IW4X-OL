#!/usr/bin/env python3
"""Small JSON inspector used by EX-068. Read-only."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent
MODULES = {
    "codo": ROOT / "COD OL" / "codoMP_client_shipRetail.exe",
    "base": ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll",
    "proxy": ROOT / "COD OL" / "TenProxy.dll",
    "clientbase": ROOT / "COD OL" / "TCLS" / "ClientBase.dll",
    "client": ROOT / "COD OL" / "TCLS" / "Client.exe",
    "tcls": ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll",
    "core": ROOT / "WeGame" / "tcls" / "tcls_core.exe",
}

LOADER_NAMES = {
    "LoadLibraryA",
    "LoadLibraryW",
    "LoadLibraryExA",
    "LoadLibraryExW",
    "GetProcAddress",
    "LdrLoadDll",
}


def string_hits(image: PEImage, needle: bytes, limit: int) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    start = 0
    while len(hits) < limit:
        pos = image.data.find(needle, start)
        if pos < 0:
            break
        pair = image.raw_to_rva(pos)
        if pair is not None:
            section = image.section_for_rva(pair[0])
            hits.append(
                {
                    "rva": pair[0],
                    "section": section.name if section else "",
                    "refs": image.immediate_refs(image.va(pair[0])),
                }
            )
        start = pos + 1
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--string", action="append", default=[])
    parser.add_argument("--rva", action="append", type=lambda x: int(x, 0), default=[])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    image = PEImage(MODULES[args.module])
    result: dict[str, object] = {
        "module": args.module,
        "path": str(image.path),
        "base": image.base,
        "size": image.size,
        "entry": image.entry,
        "sections": [
            {
                "name": section.name,
                "rva": section.rva,
                "vsize": section.vsize,
                "raw": section.raw,
                "raw_size": section.raw_size,
                "flags": section.characteristics,
            }
            for section in image.sections
        ],
        "loader_imports": [
            {"iat_rva": iat, "dll": dll, "name": name}
            for iat, (dll, name) in image.imports.items()
            if name in LOADER_NAMES
        ],
        "strings": {},
        "rvа_data": {},
    }
    for value in args.string:
        result["strings"][value] = string_hits(
            image, value.encode("utf-8"), args.limit
        )
    for rva in args.rva:
        result["rvа_data"][hex(rva)] = {
            "section": (
                image.section_for_rva(rva).name
                if image.section_for_rva(rva)
                else ""
            ),
            "raw": image.rva_to_raw(rva),
            "bytes": image.read(rva, 0x80).hex(),
            "u32": list(struct.unpack("<32I", image.read(rva, 0x80)))
            if len(image.read(rva, 0x80)) == 0x80
            else [],
        }
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
