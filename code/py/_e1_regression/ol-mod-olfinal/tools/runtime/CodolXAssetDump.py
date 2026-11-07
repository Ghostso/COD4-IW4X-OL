#!/usr/bin/env python3
"""Inventory CODOL RawFile assets and dump selected payloads from a running client."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
RAWFILE_ASSET_TYPE = 36
DEFAULT_PATTERNS = ("*.gsc", "*.csc", "*.cas")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


AGENT_SOURCE = r"""
'use strict';

const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
const ASSET_TYPE_RAWFILE = 36;
const DB_GET_ALL_XASSET_OF_TYPE = module.base.add(0x9ED90);
const DB_FIND_XASSET_HEADER = module.base.add(0x9E7D0);
const DB_GET_RAW_BUFFER = module.base.add(0xA1620);

if (Process.arch !== 'ia32')
    throw new Error('CODOL RawFile dumper requires the 32-bit client');

function u32Bytes(value) {
    const number = value.toUInt32();
    return [
        number & 0xff,
        (number >>> 8) & 0xff,
        (number >>> 16) & 0xff,
        (number >>> 24) & 0xff,
    ];
}

function executableThunk(bytes) {
    const page = Memory.alloc(Process.pageSize);
    if (!Memory.protect(page, Process.pageSize, 'rwx'))
        throw new Error('unable to make thunk page executable');
    page.writeByteArray(bytes);
    return page;
}

// CODOL passes the output XAssetHeader array in EDI and the type on the stack.
const getAllThunk = executableThunk([
    0x8b, 0x7c, 0x24, 0x04,             // mov edi, [esp+4]
    0xff, 0x74, 0x24, 0x08,             // push [esp+8]
    0xb8, ...u32Bytes(DB_GET_ALL_XASSET_OF_TYPE),
    0xff, 0xd0,                         // call eax
    0x83, 0xc4, 0x04,                   // add esp, 4
    0xc3,                               // ret
]);
const DB_GetAllXAssetOfType = new NativeFunction(
    getAllThunk,
    'int',
    ['pointer', 'int']
);

// CODOL passes RawFile * in ECX; destination and capacity remain stack arguments.
const getRawBufferThunk = executableThunk([
    0x8b, 0x4c, 0x24, 0x04,             // mov ecx, [esp+4]
    0xff, 0x74, 0x24, 0x0c,             // push [esp+0xc] (capacity)
    0xff, 0x74, 0x24, 0x0c,             // push [esp+0xc] (destination)
    0xb8, ...u32Bytes(DB_GET_RAW_BUFFER),
    0xff, 0xd0,                         // call eax
    0x83, 0xc4, 0x08,                   // add esp, 8
    0xc3,                               // ret
]);
const DB_GetRawBuffer = new NativeFunction(
    getRawBufferThunk,
    'void',
    ['pointer', 'pointer', 'int']
);
const DB_FindXAssetHeader = new NativeFunction(
    DB_FIND_XASSET_HEADER,
    'pointer',
    ['int', 'pointer', 'int']
);

function rawFileMetadata(header) {
    if (header.isNull()) throw new Error('null RawFile header');
    const namePointer = header.readPointer();
    const compressedLength = header.add(4).readS32();
    const length = header.add(8).readS32();
    const buffer = header.add(12).readPointer();
    if (namePointer.isNull()) throw new Error('RawFile has a null name');
    if (compressedLength < 0 || length < 0 || compressedLength > 0x40000000 || length > 0x40000000)
        throw new Error('RawFile has implausible lengths');
    if (length > 0 && buffer.isNull()) throw new Error('RawFile has a null buffer');
    const name = namePointer.readCString();
    if (name.length === 0 || name.length > 4096)
        throw new Error('RawFile has an implausible name length');
    return {
        header: header.toString(),
        name: name,
        compressed_length: compressedLength,
        length: length,
        buffer: buffer.toString(),
    };
}

function enumerateRawFiles() {
    const countBefore = DB_GetAllXAssetOfType(ptr(0), ASSET_TYPE_RAWFILE);
    if (countBefore < 0 || countBefore > 500000)
        throw new Error('implausible RawFile count: ' + countBefore);
    const capacity = Math.max(countBefore + 4096, countBefore * 2, 4096);
    const headers = Memory.alloc(capacity * Process.pointerSize);
    const countAfter = DB_GetAllXAssetOfType(headers, ASSET_TYPE_RAWFILE);
    if (countAfter < 0 || countAfter > capacity)
        throw new Error('RawFile count changed beyond reserved capacity: ' + countAfter);

    const assets = [];
    for (let index = 0; index < countAfter; ++index) {
        const enumeratedHeader = headers.add(index * Process.pointerSize).readPointer();
        try {
            const namePointer = enumeratedHeader.readPointer();
            let activeHeader = DB_FindXAssetHeader(ASSET_TYPE_RAWFILE, namePointer, 0);
            if (activeHeader.isNull()) activeHeader = enumeratedHeader;
            const metadata = rawFileMetadata(activeHeader);
            metadata.index = index;
            metadata.enumerated_header = enumeratedHeader.toString();
            assets.push(metadata);
        } catch (error) {
            assets.push({
                index: index,
                enumerated_header: enumeratedHeader.toString(),
                error: String(error),
            });
        }
    }
    return {
        module_base: module.base.toString(),
        count_before: countBefore,
        count_after: countAfter,
        capacity: capacity,
        assets: assets,
    };
}

rpc.exports = {
    enumerateRawFiles() {
        return enumerateRawFiles();
    },
    emitRawFile(headerValue, maximumBytes) {
        const header = ptr(headerValue);
        const metadata = rawFileMetadata(header);
        if (metadata.length > maximumBytes)
            throw new Error('RawFile exceeds maximum uncompressed size: ' + metadata.name);
        const output = Memory.alloc(Math.max(metadata.length + 1, 1));
        DB_GetRawBuffer(header, output, metadata.length + 1);
        const bytes = metadata.length === 0
            ? new ArrayBuffer(0)
            : output.readByteArray(metadata.length);
        send({ event: 'rawfile', metadata: metadata }, bytes);
        return metadata;
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
    return repository / ".runtime" / "xassets" / stamp


def asset_selected(name: str, patterns: tuple[str, ...], dump_all: bool) -> bool:
    if dump_all:
        return True
    folded = name.casefold()
    return any(fnmatch.fnmatchcase(folded, pattern.casefold()) for pattern in patterns)


def safe_asset_path(name: str, fallback: str) -> Path:
    parts: list[str] = []
    for raw_part in re.split(r"[\\/]+", name):
        if raw_part in ("", ".", ".."):
            continue
        part = re.sub(r'[<>:"|?*\x00-\x1f]', "_", raw_part).rstrip(" .")
        if not part:
            part = "_"
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            part = f"_{part}"
        parts.append(part)
    return Path(*parts) if parts else Path(fallback)


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument(
        "--include",
        action="append",
        dest="patterns",
        help="Case-insensitive asset-name glob; repeatable (default: GSC/CSC/CAS)",
    )
    parser.add_argument("--all", action="store_true", dest="dump_all")
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--max-mib", type=int, default=64)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.max_mib <= 0 or args.max_mib > 1024:
        parser.error("--max-mib must be between 1 and 1024")
    patterns = tuple(args.patterns or DEFAULT_PATTERNS)

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    condition = threading.Condition()
    payloads: dict[str, bytes] = {}
    messages: list[dict[str, Any]] = []

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        with condition:
            if message.get("type") == "send":
                payload = message.get("payload")
                if isinstance(payload, dict) and payload.get("event") == "rawfile":
                    metadata = payload.get("metadata")
                    if isinstance(metadata, dict) and isinstance(metadata.get("header"), str):
                        payloads[metadata["header"]] = bytes(data or b"")
                if isinstance(payload, dict):
                    messages.append(payload)
            else:
                messages.append({"event": "frida_message", "message": message})
            condition.notify_all()

    script.on("message", on_message)
    output = (args.output_dir or default_output(repository)).resolve()
    output.mkdir(parents=True, exist_ok=True)
    inventory: dict[str, Any]
    try:
        script.load()
        time.sleep(0.05)
        agent_errors = [
            entry
            for entry in messages
            if entry.get("event") == "frida_message"
            and isinstance(entry.get("message"), dict)
            and entry["message"].get("type") == "error"
        ]
        if agent_errors:
            raise RuntimeError(f"RawFile agent initialization failed: {agent_errors[-1]}")
        try:
            inventory = dict(script.exports_sync.enumerate_raw_files())
        except frida.RPCException as error:
            raise RuntimeError(
                f"RawFile inventory RPC failed: {error}; agent messages: {messages}"
            ) from error
        assets = inventory.get("assets")
        if not isinstance(assets, list):
            raise RuntimeError("RawFile inventory did not return an asset list")

        seen_paths: set[str] = set()
        selected_count = 0
        dumped_count = 0
        for asset in assets:
            if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
                continue
            selected = asset_selected(asset["name"], patterns, args.dump_all)
            asset["selected"] = selected
            if not selected:
                continue
            selected_count += 1
            if args.list_only:
                asset["dump_status"] = "list_only"
                continue
            if int(asset.get("length", -1)) > args.max_mib * 1024 * 1024:
                asset["dump_status"] = "skipped_size_limit"
                continue

            header = asset.get("header")
            if not isinstance(header, str):
                asset["dump_status"] = "missing_header"
                continue
            try:
                script.exports_sync.emit_raw_file(header, args.max_mib * 1024 * 1024)
                deadline = time.monotonic() + 10.0
                with condition:
                    while header not in payloads and time.monotonic() < deadline:
                        condition.wait(deadline - time.monotonic())
                    data = payloads.pop(header, None)
                if data is None:
                    raise RuntimeError("timed out waiting for RawFile payload")

                relative = safe_asset_path(asset["name"], f"rawfile_{asset['index']}.bin")
                collision_key = str(relative).casefold()
                if collision_key in seen_paths:
                    relative = relative.with_name(f"{relative.name}__{header[2:]}")
                    collision_key = str(relative).casefold()
                seen_paths.add(collision_key)
                destination = output / "files" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                asset["dump_status"] = "dumped"
                asset["output"] = destination.relative_to(output).as_posix()
                asset["bytes_written"] = len(data)
                asset["sha256"] = hashlib.sha256(data).hexdigest().upper()
                dumped_count += 1
            except Exception as error:
                asset["dump_status"] = "error"
                asset["dump_error"] = str(error)
        inventory["selected_count"] = selected_count
        inventory["dumped_count"] = dumped_count
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass

    inventory.update(
        schema_version=1,
        captured_at=dt.datetime.now(dt.UTC).isoformat(),
        pid=pid,
        target=TARGET_NAME,
        asset_type=RAWFILE_ASSET_TYPE,
        patterns=list(patterns),
        dump_all=args.dump_all,
        list_only=args.list_only,
        max_uncompressed_mib=args.max_mib,
        messages=messages,
    )
    manifest = output / "manifest.json"
    temporary = manifest.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest)
    print(
        f"RawFile assets: {inventory.get('count_after', 0)}; "
        f"selected: {inventory.get('selected_count', 0)}; "
        f"dumped: {inventory.get('dumped_count', 0)}",
        flush=True,
    )
    print(f"Saved manifest: {manifest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
