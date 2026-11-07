#!/usr/bin/env python3
"""Dump the CODOL 3.3.3.3 playerstate netfield table from a live client."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
EXPECTED_IMAGE_SHA256 = "E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B"
# IDA preferred VA 0x00C55F70 minus image base 0x00400000.
PLAYERSTATE_TABLE_RVA = 0x855F70
PLAYERSTATE_FIELD_COUNT = 235
NETFIELD_ENTRY_SIZE = 12


AGENT_SOURCE = r"""
'use strict';

rpc.exports = {
    moduleInfo(moduleName) {
        const module = Process.getModuleByName(moduleName);
        return {
            name: module.name,
            path: module.path,
            base: module.base.toString(),
            size: module.size,
        };
    },
    dumpTable(moduleName, tableRva, fieldCount, entrySize) {
        const module = Process.getModuleByName(moduleName);
        const table = module.base.add(tableRva);
        const tableBytes = fieldCount * entrySize;
        if (table.compare(module.base) < 0 ||
            table.add(tableBytes).compare(module.base.add(module.size)) > 0) {
            throw new Error('netfield table is outside the client module');
        }

        const entries = [];
        for (let index = 0; index < fieldCount; ++index) {
            const address = table.add(index * entrySize);
            entries.push({
                index: index,
                address: address.toString(),
                offset: address.readS32(),
                bits: address.add(4).readS32(),
                change_hint: address.add(8).readS32(),
            });
        }
        return {
            table_address: table.toString(),
            entries: entries,
        };
    },
};
"""


def parse_int(value: str) -> int:
    return int(value, 0)


def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested
    matches = [
        process.pid
        for process in device.enumerate_processes()
        if process.name.casefold() == TARGET_NAME.casefold()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {TARGET_NAME} process, found {len(matches)}")
    return matches[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_entries(
    entries: list[dict[str, Any]],
    count: int,
    maximum_change_hint: int = 3,
) -> None:
    if len(entries) != count:
        raise RuntimeError(f"expected {count} netfields, received {len(entries)}")
    for index, entry in enumerate(entries):
        if entry.get("index") != index:
            raise RuntimeError(f"netfield index mismatch at entry {index}")
        offset = entry.get("offset")
        bits = entry.get("bits")
        hint = entry.get("change_hint")
        if not isinstance(offset, int) or not 0 <= offset < 0x10000:
            raise RuntimeError(f"implausible offset at netfield {index}: {offset!r}")
        if not isinstance(bits, int) or not -0x1000 < bits <= 64:
            raise RuntimeError(f"implausible bit encoding at netfield {index}: {bits!r}")
        if not isinstance(hint, int) or not 0 <= hint <= maximum_change_hint:
            raise RuntimeError(f"implausible change hint at netfield {index}: {hint!r}")


def default_output(repository: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return repository / ".runtime" / "netfields" / f"playerstate-{stamp}.json"


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--table-rva", type=parse_int, default=PLAYERSTATE_TABLE_RVA)
    parser.add_argument("--field-count", type=int, default=PLAYERSTATE_FIELD_COUNT)
    parser.add_argument("--entry-size", type=int, default=NETFIELD_ENTRY_SIZE)
    parser.add_argument(
        "--maximum-change-hint",
        type=int,
        default=3,
        help="Upper bound for the selected table; entityState tables use values above 3",
    )
    parser.add_argument("--allow-unknown-image", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.field_count <= 4096:
        parser.error("--field-count must be between 1 and 4096")
    if args.entry_size != NETFIELD_ENTRY_SIZE:
        parser.error(f"--entry-size must be {NETFIELD_ENTRY_SIZE} for the recovered layout")
    if args.table_rva < 0:
        parser.error("--table-rva must be non-negative")
    if not 0 <= args.maximum_change_hint <= 0xFF:
        parser.error("--maximum-change-hint must be between 0 and 255")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    errors: list[dict[str, Any]] = []
    script.on(
        "message",
        lambda message, _data: errors.append(message)
        if message.get("type") == "error"
        else None,
    )
    script.load()
    try:
        module: dict[str, Any] = script.exports_sync.module_info(TARGET_NAME)
        image_path = Path(module["path"])
        image_sha256 = sha256_file(image_path)
        if image_sha256 != EXPECTED_IMAGE_SHA256 and not args.allow_unknown_image:
            raise RuntimeError(
                f"unsupported client image {image_sha256}; expected {EXPECTED_IMAGE_SHA256} "
                "(use --allow-unknown-image only for an explicitly reviewed build)"
            )
        table: dict[str, Any] = script.exports_sync.dump_table(
            TARGET_NAME,
            args.table_rva,
            args.field_count,
            args.entry_size,
        )
    finally:
        script.unload()
        session.detach()

    if errors:
        raise RuntimeError("; ".join(str(error) for error in errors))
    entries: list[dict[str, Any]] = table["entries"]
    validate_entries(entries, args.field_count, args.maximum_change_hint)

    output = (args.output or default_output(repository)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "pid": pid,
        "target": TARGET_NAME,
        "image": {
            "path": str(image_path),
            "base": module["base"],
            "size": module["size"],
            "sha256": image_sha256,
            "expected_sha256": EXPECTED_IMAGE_SHA256,
        },
        "table": {
            "rva": args.table_rva,
            "address": table["table_address"],
            "entry_size": args.entry_size,
            "field_count": args.field_count,
            "maximum_change_hint": args.maximum_change_hint,
        },
        "entries": entries,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("index offset bits hint address")
    for entry in entries:
        print(
            f"{entry['index']:>5} {entry['offset']:>6} {entry['bits']:>4} "
            f"{entry['change_hint']:>4} {entry['address']}"
        )
    print(f"Saved read-only playerstate netfield dump: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
