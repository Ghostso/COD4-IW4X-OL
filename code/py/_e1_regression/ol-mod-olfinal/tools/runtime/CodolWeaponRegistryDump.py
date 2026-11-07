#!/usr/bin/env python3
"""Read the CODOL weapon/attachment model registry from one live process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"

AGENT_SOURCE = r"""
'use strict';

const RVAS = {
    weaponDefinitions: 0x13f5a40,
    weaponCount: 0x7417b88,
    attachmentModelCount: 0x13f5a3c,
    perWeaponMappingCounts: 0x13f5848,
    attachmentModelDefinitions: 0x13f7a48,
    attachmentMappings: 0x13f8248,
    noneAttachmentModelIndex: 0x1417648,
};
const BASE_WEAPON_COUNT = 500;
const MAPPINGS_PER_WEAPON = 64;

function readWeaponName(definitions, index) {
    try {
        const definition = definitions.add(index * 4).readPointer();
        if (definition.isNull()) return null;
        const name = definition.readPointer();
        if (name.isNull()) return null;
        return name.readUtf8String(512);
    } catch (_) {
        return null;
    }
}

rpc.exports = {
    dump(moduleName, requestedWeaponIndex, includeAll) {
        const module = Process.getModuleByName(moduleName);
        const base = module.base;
        const definitions = base.add(RVAS.weaponDefinitions);
        const mappingCounts = base.add(RVAS.perWeaponMappingCounts);
        const modelDefinitions = base.add(RVAS.attachmentModelDefinitions);
        const mappings = base.add(RVAS.attachmentMappings);
        const weaponCount = base.add(RVAS.weaponCount).readU32();
        const attachmentModelCount = base.add(RVAS.attachmentModelCount).readU16();
        const noneModel = base.add(RVAS.noneAttachmentModelIndex).readU16();
        const records = [];
        let weaponsWithMappings = 0;
        let totalMappings = 0;
        for (let weaponIndex = 0; weaponIndex < BASE_WEAPON_COUNT; ++weaponIndex) {
            const count = mappingCounts.add(weaponIndex).readU8();
            if (count !== 0) ++weaponsWithMappings;
            totalMappings += count;
            if (!includeAll && weaponIndex !== requestedWeaponIndex) continue;
            if (includeAll && count === 0 && weaponIndex !== requestedWeaponIndex) continue;
            const entries = [];
            const boundedCount = Math.min(count, MAPPINGS_PER_WEAPON);
            for (let mappingIndex = 0; mappingIndex < boundedCount; ++mappingIndex) {
                const raw = mappings.add(
                    (weaponIndex * MAPPINGS_PER_WEAPON + mappingIndex) * 4
                ).readU32();
                entries.push({
                    raw: raw,
                    attachment_index: raw & 0xffff,
                    model_index: raw >>> 16,
                    model_pointer: modelDefinitions.add((raw >>> 16) * 4)
                        .readPointer().toString(),
                });
            }
            records.push({
                weapon_index: weaponIndex,
                weapon_name: readWeaponName(definitions, weaponIndex),
                mapping_count: count,
                count_in_bounds: count <= MAPPINGS_PER_WEAPON,
                mappings: entries,
            });
        }
        return {
            module: {
                name: module.name,
                path: module.path,
                base: module.base.toString(),
                size: module.size,
            },
            weapon_count: weaponCount,
            attachment_model_count: attachmentModelCount,
            none_attachment_model_index: noneModel,
            none_attachment_model_pointer:
                modelDefinitions.add(noneModel * 4).readPointer().toString(),
            base_weapon_capacity: BASE_WEAPON_COUNT,
            mappings_per_weapon: MAPPINGS_PER_WEAPON,
            weapons_with_mappings: weaponsWithMappings,
            total_mapping_count: totalMappings,
            records: records,
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


def validate_dump(payload: dict[str, Any]) -> None:
    if payload.get("base_weapon_capacity") != 500:
        raise RuntimeError("unexpected base weapon capacity")
    if payload.get("mappings_per_weapon") != 64:
        raise RuntimeError("unexpected per-weapon mapping capacity")
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError("registry dump did not return records")
    if any(not record.get("count_in_bounds") for record in records):
        raise RuntimeError("registry contains an out-of-bounds mapping count")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--weapon-index", type=int, default=-1)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.weapon_index < -1 or args.weapon_index >= 500:
        parser.error("--weapon-index must be -1 or 0..499")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    script.load()
    try:
        payload = script.exports_sync.dump(
            TARGET_NAME, args.weapon_index, args.all
        )
        validate_dump(payload)
        document = {"pid": pid, **payload}
        rendered = json.dumps(document, indent=2, ensure_ascii=True)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
