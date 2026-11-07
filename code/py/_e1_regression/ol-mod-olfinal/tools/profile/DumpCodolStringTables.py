#!/usr/bin/env python3
"""Dump selected CODOL StringTable assets from a running client."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_TABLES = (
    "mp/coMarketplaceItems.csv",
    "mp/badgeTable.csv",
    "mp/callsignBackground.csv",
)

AGENT_SOURCE = r"""
'use strict';

const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
const DB_FindXAssetHeader = new NativeFunction(
    module.base.add(0x9E7D0),
    'pointer',
    ['int', 'pointer', 'int']
);

function dumpStringTable(name) {
    const table = DB_FindXAssetHeader(0x25, Memory.allocUtf8String(name), 1);
    if (table.isNull()) throw new Error('StringTable not found: ' + name);

    const columnCount = table.add(4).readS32();
    const rowCount = table.add(8).readS32();
    const values = table.add(12).readPointer();
    if (columnCount <= 0 || columnCount > 256 || rowCount < 0 || rowCount > 100000 || values.isNull()) {
        throw new Error('Unexpected StringTable layout: ' + name);
    }

    const rows = [];
    for (let rowIndex = 0; rowIndex < rowCount; ++rowIndex) {
        const row = [];
        for (let columnIndex = 0; columnIndex < columnCount; ++columnIndex) {
            const cell = values.add((rowIndex * columnCount + columnIndex) * 8);
            const value = cell.readPointer();
            row.push(value.isNull() ? '' : value.readCString());
        }
        rows.push(row);
    }
    return { name: name, column_count: columnCount, row_count: rowCount, rows: rows };
}

function candidateCsvName(address) {
    const valid = value =>
        (value >= 0x30 && value <= 0x39) ||
        (value >= 0x41 && value <= 0x5a) ||
        (value >= 0x61 && value <= 0x7a) ||
        value === 0x2f || value === 0x5c || value === 0x2e ||
        value === 0x5f || value === 0x2d;
    let start = address;
    for (let count = 0; count < 255; ++count) {
        const previous = start.sub(1).readU8();
        if (!valid(previous)) break;
        start = start.sub(1);
    }
    const length = address.sub(start).toInt32() + 4;
    if (length < 5 || length > 259) return null;
    try {
        return start.readUtf8String(length);
    } catch (_) {
        return null;
    }
}

function discoverStringTables() {
    const candidates = new Map();
    for (const protection of ['r--', 'rw-', 'r-x']) {
        const ranges = Process.enumerateRanges({ protection: protection, coalesce: true });
        for (const range of ranges) {
            let matches = [];
            try {
                matches = Memory.scanSync(range.base, range.size, '2e 63 73 76 00');
            } catch (_) {
                continue;
            }
            for (const match of matches) {
                const name = candidateCsvName(match.address);
                if (name !== null) candidates.set(name.toLowerCase(), name.replace(/\\/g, '/'));
            }
        }
    }

    const tables = [];
    for (const name of Array.from(candidates.values()).sort()) {
        let table = ptr(0);
        try {
            table = DB_FindXAssetHeader(0x25, Memory.allocUtf8String(name), 0);
        } catch (_) {
            continue;
        }
        if (table.isNull()) continue;
        const columnCount = table.add(4).readS32();
        const rowCount = table.add(8).readS32();
        if (columnCount <= 0 || columnCount > 256 || rowCount < 0 || rowCount > 100000) continue;
        tables.push({ name: name, column_count: columnCount, row_count: rowCount });
    }
    return tables;
}

rpc.exports = {
    dump(name) {
        return dumpStringTable(name);
    },
    discover() {
        return discoverStringTables();
    }
};
"""


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help=f"Defaults to the newest {TARGET_NAME}")
    parser.add_argument("--table", action="append", dest="tables", help="May be specified more than once")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discover every loaded StringTable by validating in-memory CSV names",
    )
    parser.add_argument(
        "--name-filter",
        help="Case-insensitive substring applied to discovered table names",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Record discovered names and dimensions without dumping table rows",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def find_pid(device: frida.core.Device) -> int | None:
    matches = [process for process in device.enumerate_processes() if process.name.lower() == TARGET_NAME.lower()]
    return max(matches, key=lambda process: process.pid).pid if matches else None


def safe_filename(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_")


def write_table(directory: Path, table: dict[str, Any]) -> None:
    stem = safe_filename(table["name"])
    with (directory / stem).open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(table["rows"])
    (directory / f"{stem}.json").write_text(json.dumps(table, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    device = frida.get_local_device()
    pid = args.pid or find_pid(device)
    if pid is None:
        print(f"No running {TARGET_NAME} was found.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (args.output_dir or args.repository / "diagnostics" / "stringtables" / stamp).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    errors: list[str] = []
    script.on("message", lambda message, _data: errors.append(str(message)) if message.get("type") == "error" else None)
    script.load()
    try:
        discovered: list[dict[str, Any]] = []
        if args.discover:
            discovered = script.exports_sync.discover()
            if args.name_filter:
                query = args.name_filter.casefold()
                discovered = [entry for entry in discovered if query in entry["name"].casefold()]
            names = [entry["name"] for entry in discovered]
        else:
            names = args.tables or list(DEFAULT_TABLES)

        metadata = {
            "pid": pid,
            "target": TARGET_NAME,
            "discovered": args.discover,
            "name_filter": args.name_filter,
            "tables": [],
        }
        for entry in discovered:
            print(f"{entry['name']}: {entry['row_count']} rows x {entry['column_count']} columns")
        if args.metadata_only:
            metadata["tables"] = discovered
            (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            names = []

        for name in names:
            table = script.exports_sync.dump(name)
            write_table(output_dir, table)
            metadata["tables"].append({
                "name": table["name"],
                "column_count": table["column_count"],
                "row_count": table["row_count"],
            })
            if not args.discover:
                print(f"{table['name']}: {table['row_count']} rows x {table['column_count']} columns")
        (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    finally:
        script.unload()
        session.detach()

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Dumped StringTables to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
