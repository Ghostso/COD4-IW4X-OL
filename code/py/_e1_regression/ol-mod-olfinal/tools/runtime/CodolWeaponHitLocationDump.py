#!/usr/bin/env python3
"""Locate plausible CODOL weapon hit-location multiplier tables read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
EXPECTED_IMAGE_SHA256 = "E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B"


AGENT_SOURCE = r"""
'use strict';

const WEAPON_DEFINITIONS_RVA = 0x13f5a40;
const WEAPON_COUNT_RVA = 0x7417b88;
const HIT_LOCATION_COUNT = 21;
const SCAN_START = 0x800;
const SCAN_END = 0xd80;

function readable(address, size) {
    const range = Process.findRangeByAddress(address);
    if (range === null || range.protection.indexOf('r') === -1) return false;
    return address.add(size).compare(range.base.add(range.size)) <= 0;
}

function readName(definition) {
    try {
        const address = definition.readPointer();
        if (address.isNull() || !readable(address, 1)) return null;
        const name = address.readUtf8String(512);
        return name && name.length <= 511 ? name : null;
    } catch (_) {
        return null;
    }
}

function readMultipliers(address) {
    if (address.isNull() || !readable(address, HIT_LOCATION_COUNT * 4))
        return null;
    const values = [];
    let positive = 0;
    let different = false;
    for (let index = 0; index < HIT_LOCATION_COUNT; ++index) {
        const value = address.add(index * 4).readFloat();
        if (!Number.isFinite(value) || value < 0.0 || value > 20.0)
            return null;
        if (value > 0.0) ++positive;
        if (index && Math.abs(value - values[0]) > 0.0001) different = true;
        values.push(value);
    }
    if (positive < 16 || !different) return null;
    return values;
}

rpc.exports = {
    dump(moduleName, sampleLimit) {
        const module = Process.getModuleByName(moduleName);
        if (Process.arch !== 'ia32')
            throw new Error('CODOL weapon dumper requires the 32-bit client');
        const definitions = module.base.add(WEAPON_DEFINITIONS_RVA);
        const weaponCount = module.base.add(WEAPON_COUNT_RVA).readU32();
        if (weaponCount === 0 || weaponCount > 1024)
            throw new Error('invalid weapon count: ' + weaponCount);

        const weapons = [];
        for (let index = 1; index < weaponCount && weapons.length < sampleLimit; ++index) {
            const definition = definitions.add(index * 4).readPointer();
            if (definition.isNull() || !readable(definition, 4))
                continue;
            weapons.push({
                index: index,
                name: readName(definition),
                definition: definition,
            });
        }

        const candidates = [];
        for (let offset = SCAN_START; offset <= SCAN_END - 4; offset += 4) {
            for (const mode of ['pointer', 'inline']) {
                const records = [];
                for (const weapon of weapons) {
                    let table = weapon.definition.add(offset);
                    if (mode === 'pointer') {
                        if (!readable(table, 4)) continue;
                        table = table.readPointer();
                    }
                    const values = readMultipliers(table);
                    if (values !== null) {
                        records.push({
                            weapon_index: weapon.index,
                            weapon_name: weapon.name,
                            definition: weapon.definition.toString(),
                            table: table.toString(),
                            values: values,
                        });
                    }
                }
                if (weapons.length >= 3 && records.length >= 3) {
                    candidates.push({
                        offset: offset,
                        offset_hex: '0x' + offset.toString(16),
                        mode: mode,
                        match_count: records.length,
                        records: records,
                    });
                }
            }
        }
        return {
            module: { name: module.name, path: module.path, base: module.base.toString() },
            weapon_count: weaponCount,
            sampled_weapon_count: weapons.length,
            hit_location_count: HIT_LOCATION_COUNT,
            candidates: candidates,
        };
    },
};
"""


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested
    matches = [
        process.pid
        for process in device.enumerate_processes()
        if process.name.casefold() == TARGET_NAME.casefold()
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {TARGET_NAME} process, found {len(matches)}; pass --pid"
        )
    return matches[0]


def validate(payload: dict[str, Any]) -> None:
    module = payload.get("module")
    if not isinstance(module, dict):
        raise RuntimeError("missing module metadata")
    path = Path(str(module.get("path", "")))
    if image_sha256(path) != EXPECTED_IMAGE_SHA256:
        raise RuntimeError("active CODOL image hash does not match the supported build")
    if payload.get("hit_location_count") != 21:
        raise RuntimeError("unexpected hit-location count")
    if not isinstance(payload.get("candidates"), list):
        raise RuntimeError("missing candidate list")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--sample-limit", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 3 <= args.sample_limit <= 64:
        parser.error("--sample-limit must be between 3 and 64")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    script.load()
    try:
        payload = script.exports_sync.dump(TARGET_NAME, args.sample_limit)
        validate(payload)
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
