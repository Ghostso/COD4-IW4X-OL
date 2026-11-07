#!/usr/bin/env python3
"""Read-only scan of a running CODOL client's readable memory for ASCII strings."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_STRINGS = (
    "custom1",
    "changeclass_marines",
    "changeclass_opfor",
    "class0",
)

AGENT_SOURCE = r"""
'use strict';

function asciiPattern(value) {
    return Array.from(value, character =>
        character.charCodeAt(0).toString(16).padStart(2, '0')
    ).join(' ');
}

function readableRanges() {
    // Frida treats the protection string as required permissions. A single
    // r-- query therefore includes readable writable/executable ranges too.
    return Process.enumerateRanges({ protection: 'r--', coalesce: true });
}

function rangeFile(range) {
    if (range.file === undefined || range.file === null) return null;
    return {
        path: range.file.path,
        offset: range.file.offset,
        size: range.file.size,
    };
}

function moduleAt(address) {
    const module = Process.findModuleByAddress(address);
    if (module === null) return null;
    return {
        name: module.name,
        path: module.path,
        base: module.base.toString(),
        offset: address.sub(module.base).toUInt32(),
    };
}

function nearbyAscii(range, address, needleLength, contextBytes) {
    const hitOffset = address.sub(range.base).toUInt32();
    const startOffset = Math.max(0, hitOffset - contextBytes);
    const requested = contextBytes * 2 + needleLength;
    const length = Math.min(requested, range.size - startOffset);
    if (length <= 0) return [];

    const bytes = new Uint8Array(range.base.add(startOffset).readByteArray(length));
    const strings = [];
    let index = 0;
    while (index < bytes.length) {
        if (bytes[index] < 0x20 || bytes[index] > 0x7e) {
            ++index;
            continue;
        }
        const begin = index;
        while (index < bytes.length && bytes[index] >= 0x20 && bytes[index] <= 0x7e) ++index;
        if (index - begin < 4) continue;
        const value = String.fromCharCode.apply(null, bytes.slice(begin, index));
        const stringAddress = range.base.add(startOffset + begin);
        strings.push({
            address: stringAddress.toString(),
            relative_to_hit: stringAddress.sub(address).toInt32(),
            value: value,
        });
    }
    return strings;
}

rpc.exports = {
    ranges() {
        return readableRanges().map(range => ({
            base: range.base.toString(),
            size: range.size,
            protection: range.protection,
            file: rangeFile(range),
        }));
    },
    scanRange(rangeBaseValue, rangeSize, scanOffset, scanSize, needles, contextBytes) {
        const range = {
            base: ptr(rangeBaseValue),
            size: rangeSize,
        };
        const scanBase = range.base.add(scanOffset);
        const results = [];
        for (const needle of needles) {
            const hits = [];
            let matches = [];
            try {
                matches = Memory.scanSync(scanBase, scanSize, asciiPattern(needle));
            } catch (_) {
                results.push({ needle: needle, hits: hits });
                continue;
            }
            for (const match of matches) {
                hits.push({
                    address: match.address.toString(),
                    module: moduleAt(match.address),
                    nearby_ascii: nearbyAscii(range, match.address, needle.length, contextBytes),
                });
            }
            results.push({ needle: needle, hits: hits });
        }
        return results;
    }
};
"""


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


def default_output(repository: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return repository / ".runtime" / "memory-strings" / f"{stamp}.json"


def address_value(value: str) -> int:
    try:
        result = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid address or size: {value!r}") from error
    if result < 0:
        raise argparse.ArgumentTypeError("address and size values must be non-negative")
    return result


def clip_ranges(
    ranges: list[dict[str, Any]], range_start: int | None, range_size: int | None
) -> list[dict[str, Any]]:
    if range_start is None and range_size is None:
        return ranges
    if range_start is None or range_size is None:
        raise ValueError("range start and size must be specified together")
    range_end = range_start + range_size
    clipped: list[dict[str, Any]] = []
    for entry in ranges:
        entry_start = int(entry["base"], 16)
        entry_end = entry_start + entry["size"]
        overlap_start = max(entry_start, range_start)
        overlap_end = min(entry_end, range_end)
        if overlap_start >= overlap_end:
            continue
        overlap = dict(entry)
        overlap["source_base"] = entry["base"]
        overlap["source_size"] = entry["size"]
        overlap["base"] = f"0x{overlap_start:x}"
        overlap["size"] = overlap_end - overlap_start
        if entry.get("file") is not None:
            overlap["file"] = dict(entry["file"])
            overlap["file"]["offset"] += overlap_start - entry_start
            overlap["file"]["size"] = overlap["size"]
        clipped.append(overlap)
    return clipped


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("strings", nargs="*", default=list(DEFAULT_STRINGS))
    parser.add_argument("--pid", type=int)
    parser.add_argument("--context-bytes", type=int, default=192)
    parser.add_argument("--max-matches", type=int, default=64)
    parser.add_argument("--chunk-mib", type=int, default=16)
    parser.add_argument("--progress-seconds", type=float, default=5.0)
    parser.add_argument(
        "--range-start",
        type=address_value,
        help="Only scan the address interval beginning at this value (decimal or 0x-prefixed)",
    )
    parser.add_argument(
        "--range-size",
        type=address_value,
        help="Size in bytes of the interval selected by --range-start",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.strings:
        parser.error("at least one string is required")
    if not 0 <= args.context_bytes <= 4096:
        parser.error("--context-bytes must be between 0 and 4096")
    if not 1 <= args.max_matches <= 4096:
        parser.error("--max-matches must be between 1 and 4096")
    if not 1 <= args.chunk_mib <= 256:
        parser.error("--chunk-mib must be between 1 and 256")
    if args.progress_seconds <= 0:
        parser.error("--progress-seconds must be positive")
    if (args.range_start is None) != (args.range_size is None):
        parser.error("--range-start and --range-size must be specified together")
    if args.range_size == 0:
        parser.error("--range-size must be positive")
    for value in args.strings:
        try:
            encoded = value.encode("ascii")
        except UnicodeEncodeError:
            parser.error(f"string is not ASCII: {value!r}")
        if not encoded:
            parser.error("empty strings are not supported")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    errors: list[dict[str, Any]] = []
    script.on("message", lambda message, _data: errors.append(message) if message.get("type") == "error" else None)
    script.load()
    try:
        all_ranges: list[dict[str, Any]] = script.exports_sync.ranges()
        ranges = clip_ranges(all_ranges, args.range_start, args.range_size)
        if not ranges:
            raise RuntimeError("the requested address interval contains no readable memory")
        ranges.sort(key=lambda entry: (entry["file"] is None, int(entry["base"], 16)))
        total_bytes = sum(entry["size"] for entry in ranges)
        scanned_bytes = 0
        chunk_bytes = args.chunk_mib * 1024 * 1024
        overlap = max(len(value) for value in args.strings) - 1
        hits_by_needle: dict[str, list[dict[str, Any]]] = {value: [] for value in args.strings}
        seen_by_needle: dict[str, set[str]] = {value: set() for value in args.strings}
        truncated = {value: False for value in args.strings}
        next_progress = time.monotonic() + args.progress_seconds
        print(
            f"Scanning {len(ranges)} readable ranges "
            f"({total_bytes / (1024 * 1024):.1f} MiB) in {args.chunk_mib} MiB chunks...",
            flush=True,
        )
        for range_entry in ranges:
            range_size = range_entry["size"]
            for offset in range(0, range_size, chunk_bytes):
                primary_size = min(chunk_bytes, range_size - offset)
                scan_size = min(primary_size + overlap, range_size - offset)
                active_needles = [value for value in args.strings if not truncated[value]]
                if active_needles:
                    chunk_results = script.exports_sync.scan_range(
                        range_entry["base"],
                        range_size,
                        offset,
                        scan_size,
                        active_needles,
                        args.context_bytes,
                    )
                    for result in chunk_results:
                        needle = result["needle"]
                        for hit in result["hits"]:
                            address = hit["address"]
                            if address in seen_by_needle[needle]:
                                continue
                            seen_by_needle[needle].add(address)
                            if len(hits_by_needle[needle]) >= args.max_matches:
                                truncated[needle] = True
                                break
                            hit["range"] = range_entry
                            hits_by_needle[needle].append(hit)
                scanned_bytes += primary_size
                now = time.monotonic()
                if now >= next_progress:
                    hit_count = sum(len(hits) for hits in hits_by_needle.values())
                    print(
                        f"progress: {scanned_bytes / (1024 * 1024):.1f}/"
                        f"{total_bytes / (1024 * 1024):.1f} MiB, {hit_count} hit(s)",
                        flush=True,
                    )
                    next_progress = now + args.progress_seconds
        results = [
            {"needle": value, "hits": hits_by_needle[value], "truncated": truncated[value]}
            for value in args.strings
        ]
    finally:
        script.unload()
        session.detach()

    if errors:
        raise RuntimeError("; ".join(str(error) for error in errors))

    output = (args.output or default_output(repository)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "pid": pid,
        "target": TARGET_NAME,
        "context_bytes": args.context_bytes,
        "max_matches_per_string": args.max_matches,
        "chunk_mib": args.chunk_mib,
        "requested_range": (
            {"start": f"0x{args.range_start:x}", "size": args.range_size}
            if args.range_start is not None
            else None
        ),
        "readable_range_count": len(ranges),
        "readable_bytes_scanned": scanned_bytes,
        "results": results,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for result in results:
        suffix = " (truncated)" if result["truncated"] else ""
        print(f"{result['needle']}: {len(result['hits'])} hit(s){suffix}", flush=True)
        for hit in result["hits"]:
            owner = hit["module"]["name"] if hit["module"] else "private/unmapped"
            print(f"  {hit['address']} {hit['range']['protection']} {owner}", flush=True)
    print(f"Saved read-only memory scan: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
