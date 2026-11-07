#!/usr/bin/env python3
"""Dump loaded CODOL glass_map and fx_map ownership from a live process."""

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
DB_GET_ALL_XASSET_OF_TYPE_RVA = 0x09ED90
GLASS_MAP_ASSET_TYPE = 17
FX_MAP_ASSET_TYPE = 20
CLIENT_FX_GLASS_SYSTEM_RVA = 0x257200C
MAXIMUM_GLASS_PIECES = 1024


AGENT_SOURCE = r"""
'use strict';

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

function pointerString(pointer) {
    return pointer.isNull() ? null : pointer.toString();
}

function readName(asset, kind) {
    if (asset.isNull()) throw new Error(kind + ' asset is null');
    const name = asset.readPointer();
    if (name.isNull()) throw new Error(kind + ' asset name is null');
    const text = name.readUtf8String();
    if (!text || text.length > 4096)
        throw new Error(kind + ' asset name is invalid');
    return text;
}

function glassSystemMetadata(system) {
    const definitionCount = system.add(8).readU32();
    const initPieceCount = system.add(20).readU32();
    if (initPieceCount > 1024)
        throw new Error('FxGlassSystem initPieceCount is invalid: ' + initPieceCount);
    const initialPieceStates = system.add(92).readPointer();
    if (initPieceCount && initialPieceStates.isNull())
        throw new Error('FxGlassSystem initialPieceStates is null');
    const pieces = [];
    for (let index = 0; index < initPieceCount; ++index) {
        const piece = initialPieceStates.add(index * 52);
        const values = [];
        for (let offset = 0; offset != 48; offset += 4)
            values.push(piece.add(offset).readFloat());
        if (!values.every(Number.isFinite))
            throw new Error('FxGlassInitPieceState has non-finite geometry at ' + index);
        const defIndex = piece.add(48).readU8();
        if (defIndex >= definitionCount)
            throw new Error('FxGlassInitPieceState defIndex is invalid at ' + index + ': ' + defIndex);
        pieces.push({
            piece_index: index,
            quat: values.slice(0, 4),
            origin: values.slice(4, 7),
            radius: values[7],
            tex_coord_origin: values.slice(8, 10),
            support_mask: piece.add(40).readU32(),
            area_x2: values[11],
            def_index: defIndex,
            vert_count: piece.add(49).readU8(),
            fan_data_count: piece.add(50).readU8(),
            padding: piece.add(51).readU8(),
        });
    }
    return {
        address: system.toString(),
        time: system.readS32(),
        previous_time: system.add(4).readS32(),
        definition_count: definitionCount,
        piece_limit: system.add(12).readU32(),
        piece_word_count: system.add(16).readU32(),
        initial_piece_count: initPieceCount,
        cell_count: system.add(24).readU32(),
        active_piece_count: system.add(28).readU32(),
        first_free_piece: system.add(32).readU32(),
        geometry_limit: system.add(36).readU32(),
        geometry_count: system.add(40).readU32(),
        initial_geometry_count: system.add(44).readU32(),
        definitions: pointerString(system.add(48).readPointer()),
        piece_places: pointerString(system.add(52).readPointer()),
        piece_states: pointerString(system.add(56).readPointer()),
        piece_dynamics: pointerString(system.add(60).readPointer()),
        geometry: pointerString(system.add(64).readPointer()),
        in_use_bits: pointerString(system.add(68).readPointer()),
        cell_bits: pointerString(system.add(72).readPointer()),
        visibility: pointerString(system.add(76).readPointer()),
        link_origins: pointerString(system.add(80).readPointer()),
        half_thickness: pointerString(system.add(84).readPointer()),
        lighting_handles: pointerString(system.add(88).readPointer()),
        initial_piece_states: pointerString(initialPieceStates),
        initial_pieces: pieces,
        initial_geometry: pointerString(system.add(96).readPointer()),
        needs_compaction: system.add(100).readU8(),
        initial_count: system.add(101).readU8(),
        effect_chance_accumulator: system.add(104).readFloat(),
        last_piece_deletion_time: system.add(108).readS32(),
    };
}

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
    dumpGlass(moduleName, getAllRva, glassType, fxType, runtimeRva, maximumPieces) {
        const module = Process.getModuleByName(moduleName);
        if (Process.arch !== 'ia32')
            throw new Error('CODOL glass dumper requires the 32-bit client');
        const getAllAddress = module.base.add(getAllRva >>> 0);
        const getAllThunk = executableThunk([
            0x8b, 0x7c, 0x24, 0x04,
            0xff, 0x74, 0x24, 0x08,
            0xb8, ...u32Bytes(getAllAddress),
            0xff, 0xd0,
            0x83, 0xc4, 0x04,
            0xc3,
        ]);
        const getAll = new NativeFunction(getAllThunk, 'int', ['pointer', 'int']);

        function enumerate(type) {
            const count = getAll(ptr(0), type | 0);
            if (count < 0 || count > 4096)
                throw new Error('asset count is invalid for type ' + type + ': ' + count);
            const output = Memory.alloc(Math.max(count, 1) * Process.pointerSize);
            const written = getAll(output, type | 0);
            if (written < 0 || written > count)
                throw new Error('asset count changed for type ' + type + ': ' + written);
            const assets = [];
            for (let index = 0; index < written; ++index)
                assets.push(output.add(index * Process.pointerSize).readPointer());
            return assets;
        }

        const glassMaps = enumerate(glassType).map((asset) => {
            const data = asset.add(4).readPointer();
            if (data.isNull()) throw new Error('glass_map data is null');
            const pieces = data.readPointer();
            const pieceCount = data.add(4).readU32();
            const nameCount = data.add(12).readU32();
            if (pieceCount > (maximumPieces >>> 0))
                throw new Error('glass_map pieceCount is invalid: ' + pieceCount);
            if (pieceCount && pieces.isNull())
                throw new Error('glass_map pieces are null');
            if (nameCount > 4096)
                throw new Error('glass_map nameCount is invalid: ' + nameCount);
            const states = [];
            for (let index = 0; index < pieceCount; ++index) {
                const piece = pieces.add(index * 12);
                states.push({
                    damage_taken: piece.readU16(),
                    collapse_time: piece.add(2).readU16(),
                    last_state_change_time: piece.add(4).readS32(),
                    impact_direction: piece.add(8).readU8(),
                    impact_position: [piece.add(9).readS8(), piece.add(10).readS8()],
                    padding: piece.add(11).readU8(),
                });
            }
            return {
                address: asset.toString(),
                name: readName(asset, 'glass_map'),
                data: data.toString(),
                pieces: pointerString(pieces),
                piece_count: pieceCount,
                damage_to_weaken: data.add(8).readU16(),
                damage_to_destroy: data.add(10).readU16(),
                glass_name_count: nameCount,
                glass_names: pointerString(data.add(16).readPointer()),
                piece_states: states,
            };
        });

        const fxMaps = enumerate(fxType).map((asset) => ({
            address: asset.toString(),
            name: readName(asset, 'fx_map'),
            glass_system: glassSystemMetadata(asset.add(4)),
        }));
        return {
            glass_maps: glassMaps,
            fx_maps: fxMaps,
            runtime_glass_system: glassSystemMetadata(module.base.add(runtimeRva >>> 0)),
        };
    },
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--allow-unknown-image", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

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
        image_sha256 = sha256_file(Path(module["path"]))
        if image_sha256 != EXPECTED_IMAGE_SHA256 and not args.allow_unknown_image:
            raise RuntimeError(
                f"unsupported client image {image_sha256}; expected {EXPECTED_IMAGE_SHA256}"
            )
        result: dict[str, Any] = script.exports_sync.dump_glass(
            TARGET_NAME,
            DB_GET_ALL_XASSET_OF_TYPE_RVA,
            GLASS_MAP_ASSET_TYPE,
            FX_MAP_ASSET_TYPE,
            CLIENT_FX_GLASS_SYSTEM_RVA,
            MAXIMUM_GLASS_PIECES,
        )
    finally:
        script.unload()
        session.detach()
    if errors:
        raise RuntimeError(f"Frida agent failed: {errors[-1]}")

    payload = {
        "schema": "codol-glass-assets-v1",
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pid": pid,
        "module": module,
        "image_sha256": image_sha256,
        **result,
    }
    output = args.output
    if output is None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output = repository / ".runtime" / "glass" / f"pid-{pid}-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(
        f"glass_maps={len(result['glass_maps'])} fx_maps={len(result['fx_maps'])} "
        f"runtime_initial_pieces={result['runtime_glass_system']['initial_piece_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
