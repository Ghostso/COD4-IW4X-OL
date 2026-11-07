#!/usr/bin/env python3
"""Dump one loaded CODOL 3.3.3.3 MapEnts asset from a live process."""

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
DB_FIND_XASSET_HEADER_RVA = 0x09E7D0
MAP_ENTS_ASSET_TYPE = 19
MAXIMUM_ENTITY_CHARS = 16 * 1024 * 1024
COLLISION_MAP_RVA = 0x029FB000
BRUSH_MODEL_SIZE = 72
MAXIMUM_BRUSH_MODELS = 65536


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
    dumpMapEnts(moduleName, findAssetRva, assetType, assetName, maximumChars) {
        const module = Process.getModuleByName(moduleName);
        const findAsset = new NativeFunction(
            module.base.add(findAssetRva >>> 0),
            'pointer',
            ['int', 'pointer', 'int']);
        const requestedName = Memory.allocUtf8String(assetName);
        const mapEnts = findAsset(assetType | 0, requestedName, 0);
        if (mapEnts.isNull())
            throw new Error('MapEnts asset was not found');

        const storedNamePointer = mapEnts.readPointer();
        const entityStringPointer = mapEnts.add(Process.pointerSize).readPointer();
        const numEntityChars = mapEnts.add(Process.pointerSize * 2).readS32();
        if (storedNamePointer.isNull() || entityStringPointer.isNull())
            throw new Error('MapEnts contains a null pointer');
        if (numEntityChars <= 0 || numEntityChars > (maximumChars >>> 0))
            throw new Error('MapEnts entity string length is invalid: ' + numEntityChars);

        return {
            asset_address: mapEnts.toString(),
            stored_name: storedNamePointer.readUtf8String(),
            entity_string_address: entityStringPointer.toString(),
            num_entity_chars: numEntityChars,
            entity_bytes: Array.from(
                new Uint8Array(entityStringPointer.readByteArray(numEntityChars))),
        };
    },
    dumpBrushModels(moduleName, collisionMapRva, modelSize, maximumModels) {
        const module = Process.getModuleByName(moduleName);
        const collisionMap = module.base.add(collisionMapRva >>> 0);
        const modelCount = collisionMap.add(0x90).readU32();
        const models = collisionMap.add(0x94).readPointer();
        if (modelCount === 0 || modelCount > (maximumModels >>> 0))
            throw new Error('collision brush model count is invalid: ' + modelCount);
        if (models.isNull())
            throw new Error('collision brush model pool is null');

        const result = [];
        for (let index = 0; index < modelCount; ++index) {
            const model = models.add(index * (modelSize >>> 0));
            const leafBrushContents = model.add(0x24).readU32();
            const leafTerrainContents = model.add(0x28).readU32();
            result.push({
                clip_handle: index,
                bounds: {
                    midpoint: [
                        model.readFloat(),
                        model.add(4).readFloat(),
                        model.add(8).readFloat(),
                    ],
                    half_size: [
                        model.add(12).readFloat(),
                        model.add(16).readFloat(),
                        model.add(20).readFloat(),
                    ],
                },
                leaf_brush_contents: leafBrushContents,
                leaf_terrain_contents: leafTerrainContents,
                contents: (leafBrushContents | leafTerrainContents) >>> 0,
            });
        }
        return {
            collision_map_address: collisionMap.toString(),
            model_pool_address: models.toString(),
            model_count: modelCount,
            models: result,
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


def default_output(repository: Path, map_name: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return repository / ".runtime" / "mapents" / f"{map_name}-{stamp}.json"


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_name")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--allow-unknown-image", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.map_name or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        for character in args.map_name
    ):
        parser.error("map_name may contain only ASCII letters, digits, and underscores")

    asset_name = f"maps/mp/{args.map_name}.d3dbsp"
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
                f"unsupported client image {image_sha256}; expected {EXPECTED_IMAGE_SHA256}"
            )
        result: dict[str, Any] = script.exports_sync.dump_map_ents(
            TARGET_NAME,
            DB_FIND_XASSET_HEADER_RVA,
            MAP_ENTS_ASSET_TYPE,
            asset_name,
            MAXIMUM_ENTITY_CHARS,
        )
        brush_models: dict[str, Any] = script.exports_sync.dump_brush_models(
            TARGET_NAME,
            COLLISION_MAP_RVA,
            BRUSH_MODEL_SIZE,
            MAXIMUM_BRUSH_MODELS,
        )
    finally:
        script.unload()
        session.detach()

    if errors:
        raise RuntimeError("; ".join(str(error) for error in errors))
    if len(result["stored_name"]) > 256 or result["stored_name"] != asset_name:
        raise RuntimeError(
            f"asset lookup returned {result['stored_name']!r}, expected {asset_name!r}"
        )

    entity_bytes = bytes(result["entity_bytes"])
    trimmed_entity_bytes = entity_bytes.rstrip(b"\0")
    if not trimmed_entity_bytes or b"\0" in trimmed_entity_bytes:
        null_offsets = [
            index for index, value in enumerate(trimmed_entity_bytes) if value == 0
        ][:16]
        raise RuntimeError(
            "MapEnts entity string is empty or contains embedded nulls; "
            f"length={len(entity_bytes)} first_null_offsets={null_offsets} "
            f"prefix={entity_bytes[:128].hex(' ')}"
        )
    entity_string = trimmed_entity_bytes.decode("utf-8")

    output = (args.output or default_output(repository, args.map_name)).resolve()
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
        },
        "asset": {
            "type": MAP_ENTS_ASSET_TYPE,
            "name": result["stored_name"],
            "address": result["asset_address"],
            "entity_string_address": result["entity_string_address"],
            "num_entity_chars": result["num_entity_chars"],
        },
        "collision_map": brush_models,
        "entity_string": entity_string,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Saved {result['num_entity_chars']} MapEnts bytes from PID {pid}: {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
