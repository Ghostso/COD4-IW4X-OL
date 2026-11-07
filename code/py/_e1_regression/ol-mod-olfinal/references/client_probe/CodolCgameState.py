#!/usr/bin/env python3
"""Read CODOL's active cgame snapshot and player state without modifying it."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


IMAGE_NAME = "codoMP_client_shipRetail.exe"


def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested
    matches = [
        process.pid
        for process in device.enumerate_processes()
        if process.name.lower() == IMAGE_NAME.lower()
    ]
    if len(matches) != 1:
        raise SystemExit(f"Expected one {IMAGE_NAME} process, found {len(matches)}.")
    return matches[0]


def build_script() -> str:
    return r"""
'use strict';

const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
const clientIndex = module.base.add(0x7417BA8).readU32();
const cgameEncoded = module.base.add(0x1619510 + clientIndex * 4).readU32();
const cgame = ptr(cgameEncoded ^ 0xFBB2C97A);
const clientActiveEncoded = module.base.add(0x162E838).readU32();
const clientActive = ptr(clientActiveEncoded ^ 0x6891D1C7);
const weaponVariantTable = module.base.add(0x13F5A40);

function readU32(base, offset) {
    try { return base.add(offset).readU32(); } catch (_) { return null; }
}

function readI32(base, offset) {
    try { return base.add(offset).readS32(); } catch (_) { return null; }
}

function readU16(base, offset) {
    try { return base.add(offset).readU16(); } catch (_) { return null; }
}

function readU8(base, offset) {
    try { return base.add(offset).readU8(); } catch (_) { return null; }
}

function readFloat(base, offset) {
    try { return base.add(offset).readFloat(); } catch (_) { return null; }
}

function readHex(base, offset, size) {
    try {
        const bytes = new Uint8Array(base.add(offset).readByteArray(size));
        return Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    } catch (_) {
        return null;
    }
}

function readVec3(base, offset) {
    return [
        readFloat(base, offset),
        readFloat(base, offset + 4),
        readFloat(base, offset + 8)
    ];
}

function readAxis(base, offset) {
    return [
        readVec3(base, offset),
        readVec3(base, offset + 12),
        readVec3(base, offset + 24)
    ];
}

function readHeldWeapons(base) {
    const weapons = [];
    for (let index = 0; index < 15; ++index) {
        weapons.push({
            weapon_asset_index: readU32(base, 0x2A4 + index * 4),
            state_flags: [
                readU8(base, 0x2E0 + index * 5),
                readU8(base, 0x2E1 + index * 5),
                readU8(base, 0x2E2 + index * 5),
                readU8(base, 0x2E3 + index * 5),
                readU8(base, 0x2E4 + index * 5)
            ]
        });
    }
    return weapons;
}

function readWeaponHands(base) {
    return [0, 1].map(hand => {
        const offset = 0x26C + hand * 28;
        return {
            animation: readU16(base, offset),
            time: readI32(base, offset + 4),
            delay: readI32(base, offset + 8),
            state: readU8(base, offset + 16)
        };
    });
}

function readAmmoClips(base) {
    const clips = [];
    for (let index = 0; index < 15; ++index) {
        const offset = 0x3DC + index * 12;
        clips.push({
            clip_index: readI32(base, offset),
            count: [readI32(base, offset + 4), readI32(base, offset + 8)]
        });
    }
    return clips;
}

function readAmmoPools(base) {
    const pools = [];
    for (let index = 0; index < 15; ++index) {
        const offset = 0x364 + index * 8;
        pools.push({
            ammo_index: readI32(base, offset),
            count: readI32(base, offset + 4)
        });
    }
    return pools;
}

function readWeaponVariant(weaponAssetIndex) {
    if (weaponAssetIndex === null || weaponAssetIndex <= 0 || weaponAssetIndex > 0x3ff) {
        return null;
    }
    let definition = ptr(0);
    try { definition = weaponVariantTable.add(weaponAssetIndex * 4).readPointer(); } catch (_) {}
    if (definition.isNull()) return null;
    return {
        address: definition.toString(),
        weapon_asset_index: weaponAssetIndex,
        selection_kind_0488: readI32(definition, 0x488),
        ammo_index: readI32(definition, 0x6B8),
        clip_index: readI32(definition, 0x6C0),
        linked_weapon_asset_index: readI32(definition, 0xD24),
        selection_requires_ammo: readU8(definition, 0xD7F),
        ammo_lookup_extra_gate: readU8(definition, 0xD83),
        selection_marks_linked_weapon: readU8(definition, 0xD96)
    };
}

function readClientWeaponSelection() {
    const weapon = readU16(clientActive, 0x3608);
    const mappedOffHand = weapon === null
        ? null
        : readU16(cgame, 0xBD01C + weapon * 2);
    return {
        client_active: clientActive.toString(),
        client_active_encoded: '0x' + clientActiveEncoded.toString(16),
        weapon_select: readU32(cgame, 0xBD00C),
        last_weapon_for_alt: readU32(cgame, 0xBD750),
        cgame_user_cmd_weapon: weapon,
        cgame_user_cmd_off_hand_index: mappedOffHand,
        cgame_user_cmd_last_weapon_for_alt: readU16(clientActive, 0x360C)
    };
}

function readSnapshot(snapshot) {
    if (snapshot.isNull()) return null;
    const entityCount = readI32(snapshot, 0x3530);
    const auxiliaryCount = readI32(snapshot, 0x3534);
    const clientCount = readI32(snapshot, 0x3538);
    const fourthCount = readI32(snapshot, 0x353C);
    return {
        address: snapshot.toString(),
        snap_flags: readU32(snapshot, 0x3524),
        ping: readI32(snapshot, 0x3528),
        server_time: readI32(snapshot, 0x352C),
        message_num: readI32(snapshot, 0x5479C),
        entity_count: entityCount,
        client_count: clientCount,
        auxiliary_count: auxiliaryCount,
        fourth_count: fourthCount,
        player_state: {
            command_time: readI32(snapshot, 0x000),
            pm_type: readI32(snapshot, 0x004),
            pm_time: readI32(snapshot, 0x008),
            pm_flags: readU32(snapshot, 0x00C),
            other_flags: readU32(snapshot, 0x010),
            origin: [
                readFloat(snapshot, 0x01C),
                readFloat(snapshot, 0x020),
                readFloat(snapshot, 0x024)
            ],
            client_num: readI32(snapshot, 0x130),
            legs_anim: readU16(snapshot, 0x0D0),
            weapon_hands: readWeaponHands(snapshot),
            current_weapon_asset_index: readU32(snapshot, 0x340),
            held_weapons: readHeldWeapons(snapshot),
            ammo_clips: readAmmoClips(snapshot),
            ammo_pools: readAmmoPools(snapshot),
            damage_event: readU32(snapshot, 0x1B4),
            damage_yaw: readU32(snapshot, 0x1B8),
            damage_pitch: readU32(snapshot, 0x1BC),
            damage_count: readU32(snapshot, 0x1C0),
            stats: {
                health: readI32(snapshot, 0x190),
                dead_yaw: readI32(snapshot, 0x194),
                max_health: readI32(snapshot, 0x198),
                spawn_count: readI32(snapshot, 0x19C)
            },
            health: readU32(snapshot, 0x1C4),
            max_health: readU32(snapshot, 0x1CC),
            shellshock_index: readU32(snapshot, 0x5AC),
            shellshock_time: readU32(snapshot, 0x5B0),
            shellshock_duration: readU32(snapshot, 0x5B4),
            spawn_generation: readI32(snapshot, 0x19C),
            unk_0144: readI32(snapshot, 0x144),
            viewangles: [
                readFloat(snapshot, 0x14C),
                readFloat(snapshot, 0x150),
                readFloat(snapshot, 0x154)
            ],
            view_height_target: readI32(snapshot, 0x158),
            view_height_current: readFloat(snapshot, 0x15C),
            velocity: readVec3(snapshot, 0x028),
            moving_platform_entity_num: readU32(snapshot, 0x044),
            remote_eyes_entity_num: readU32(snapshot, 0x048),
            remote_eyes_tagname: readU32(snapshot, 0x04C),
            remote_control_entity_num: readU32(snapshot, 0x050),
            remote_turret_entity_num: readU32(snapshot, 0x054),
            ground_entity_num: readU32(snapshot, 0x0AC),
            view_entity_num: readU32(snapshot, 0x1F0),
            link_entity_num: readU32(snapshot, 0x200),
            gravity: readI32(snapshot, 0x090),
            player_size_scale: readFloat(snapshot, 0x098),
            speed: readI32(snapshot, 0x09C),
            delta_angles: readVec3(snapshot, 0x0A0),
            view_height_lerp_time: readI32(snapshot, 0x160),
            view_height_lerp_target: readI32(snapshot, 0x164),
            view_height_lerp_down: readI32(snapshot, 0x168),
            prefix_hex: readHex(snapshot, 0, 0x1A0)
        },
        first_entity_hex: entityCount > 0 ? readHex(snapshot, 0xE5C0, 0x110) : null,
        first_auxiliary_hex: auxiliaryCount > 0 ? readHex(snapshot, 0x525C0, 0x134) : null,
        first_client_hex: clientCount > 0 ? readHex(snapshot, 0x53C9C, 0x58) : null
    };
}

let snap = ptr(0);
let nextSnap = ptr(0);
try { snap = cgame.add(0x3578).readPointer(); } catch (_) {}
try { nextSnap = cgame.add(0x357C).readPointer(); } catch (_) {}

send({
    type: 'cgame_state',
    pid: Process.id,
    module_base: module.base.toString(),
    client_index: clientIndex,
    cgame_encoded: '0x' + cgameEncoded.toString(16),
    cgame: cgame.toString(),
    latest_snapshot_num: readI32(cgame, 0x3570),
    latest_snapshot_time: readI32(cgame, 0x3574),
    client_weapon_selection: readClientWeaponSelection(),
    selected_weapon_variant: readWeaponVariant(readU32(cgame, 0xBD00C)),
    current_weapon_variant: readWeaponVariant(readU32(cgame, 0x340)),
    predicted_player_state: {
        command_time: readI32(cgame, 0x000),
        pm_type: readI32(cgame, 0x004),
        pm_time: readI32(cgame, 0x008),
        pm_flags: readU32(cgame, 0x00C),
        other_flags: readU32(cgame, 0x010),
        origin: readVec3(cgame, 0x01C),
        velocity: readVec3(cgame, 0x028),
        moving_platform_entity_num: readU32(cgame, 0x044),
        remote_eyes_entity_num: readU32(cgame, 0x048),
        remote_eyes_tagname: readU32(cgame, 0x04C),
        remote_control_entity_num: readU32(cgame, 0x050),
        remote_turret_entity_num: readU32(cgame, 0x054),
        ground_entity_num: readU32(cgame, 0x0AC),
        view_entity_num: readU32(cgame, 0x1F0),
        link_entity_num: readU32(cgame, 0x200),
        gravity: readI32(cgame, 0x090),
        player_size_scale: readFloat(cgame, 0x098),
        speed: readI32(cgame, 0x09C),
        delta_angles: readVec3(cgame, 0x0A0),
        legs_anim: readU16(cgame, 0x0D0),
        weapon_hands: readWeaponHands(cgame),
        current_weapon_asset_index: readU32(cgame, 0x340),
        held_weapons: readHeldWeapons(cgame),
        ammo_clips: readAmmoClips(cgame),
        ammo_pools: readAmmoPools(cgame),
        damage_event: readU32(cgame, 0x1B4),
        damage_yaw: readU32(cgame, 0x1B8),
        damage_pitch: readU32(cgame, 0x1BC),
        damage_count: readU32(cgame, 0x1C0),
        stats: {
            health: readI32(cgame, 0x190),
            dead_yaw: readI32(cgame, 0x194),
            max_health: readI32(cgame, 0x198),
            spawn_count: readI32(cgame, 0x19C)
        },
        health: readU32(cgame, 0x1C4),
        max_health: readU32(cgame, 0x1CC),
        shellshock_index: readU32(cgame, 0x5AC),
        shellshock_time: readU32(cgame, 0x5B0),
        shellshock_duration: readU32(cgame, 0x5B4),
        spawn_generation: readI32(cgame, 0x19C),
        viewangles: readVec3(cgame, 0x14C),
        view_height_target: readI32(cgame, 0x158),
        view_height_current: readFloat(cgame, 0x15C),
        view_height_lerp_time: readI32(cgame, 0x160),
        view_height_lerp_target: readI32(cgame, 0x164),
        view_height_lerp_down: readI32(cgame, 0x168)
    },
    refdef: {
        tan_half_fov_x: readFloat(cgame, 0xAE4F8),
        tan_half_fov_y: readFloat(cgame, 0xAE4FC),
        vieworg: readVec3(cgame, 0xAE504),
        viewaxis: readAxis(cgame, 0xAE510),
        viewangles: readVec3(cgame, 0xB2688)
    },
    shellshock: {
        parms: readU32(cgame, 0xBDB68),
        start_time: readI32(cgame, 0xBDB6C),
        duration: readI32(cgame, 0xBDB70),
        test_time: readI32(cgame, 0xBDB90),
        test_duration: readI32(cgame, 0xBDB94)
    },
    snap: readSnapshot(snap),
    next_snap: readSnapshot(nextSnap)
});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    done = threading.Event()
    result: dict[str, object] = {}
    session = device.attach(pid)
    script = session.create_script(build_script())

    def on_message(message: dict, data: bytes | None) -> None:
        payload = message.get("payload", message)
        result.update(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        done.set()

    script.on("message", on_message)
    try:
        script.load()
        if not done.wait(args.timeout):
            print(json.dumps({"type": "timeout", "seconds": args.timeout}))
            return 2
        return 0 if result.get("type") == "cgame_state" else 1
    finally:
        script.unload()
        session.detach()


if __name__ == "__main__":
    raise SystemExit(main())
