#!/usr/bin/env python3
"""Trace CODOL client netchan acceptance without modifying game behavior."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from threading import Event
from typing import Any

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
        raise RuntimeError(f"expected one {IMAGE_NAME} process, found {len(matches)}")
    return matches[0]


def build_asset_watch_script() -> str:
    return r"""
'use strict';

// The preserved OLFinal executable may keep its retail image name or be
// distributed as out.exe.  All RVAs below belong to the main executable, so
// bind to that module instead of depending on its filename.
const module = Process.mainModule;
const weaponGroupRoot = module.base.add(0x29F7D50);
const uiViewerShow = module.base.add(0xB184C53);
const weaponRegistryCount = module.base.add(0x7417B88);
const dbIsZoneLoaded = module.base.add(0xA0820);
const commonZoneState = {
    patch_common_mp: null,
    common_mp: null,
    patch_localized_common_mp: null,
    localized_common_mp: null
};

function readPointer(address) {
    try { return address.readPointer(); } catch (_) { return null; }
}

function readU32(address) {
    try { return address.readU32(); } catch (_) { return null; }
}

function readU8(address) {
    try { return address.readU8(); } catch (_) { return null; }
}

function readString(address) {
    try { return address.isNull() ? null : address.readUtf8String(); } catch (_) { return null; }
}

function currentState() {
    const value = readPointer(weaponGroupRoot);
    return {
        value: value === null ? null : value.toString(),
        ui_viewer_show: readU8(uiViewerShow),
        weapon_registry_count: readU32(weaponRegistryCount),
        common_zone_state: Object.assign({}, commonZoneState)
    };
}

Interceptor.attach(dbIsZoneLoaded, {
    onEnter(args) {
        const name = readString(args[0]);
        this.zoneName = name !== null && Object.prototype.hasOwnProperty.call(commonZoneState, name)
            ? name
            : null;
    },
    onLeave(retval) {
        if (this.zoneName !== null) commonZoneState[this.zoneName] = retval.toInt32() !== 0;
    }
});

let previousValue = currentState().value;
setInterval(() => {
    const state = currentState();
    if (state.value === previousValue) return;
    send({
        event: 'weapon_group_root_value',
        previous_value: previousValue,
        ...state
    });
    previousValue = state.value;
}, 100);

send({
    event: 'ready',
    asset_watch_only: true,
    observation: 'read-only-poll',
    pid: Process.id,
    module_base: module.base.toString(),
    weapon_group_root: weaponGroupRoot.toString(),
    ...currentState()
});
"""


def build_script(trace_entity: int | None = None) -> str:
    source = r"""
'use strict';

// The preserved OLFinal executable may keep its retail image name or be
// distributed as out.exe.  All RVAs below belong to the main executable, so
// bind to that module instead of depending on its filename.
const module = Process.mainModule;
const nativeInterceptorAttach = Interceptor.attach.bind(Interceptor);
function safeAttach(address, callbacks) {
    try {
        return nativeInterceptorAttach(address, callbacks);
    } catch (error) {
        send({
            event: 'hook_unavailable',
            address: address.toString(),
            error: String(error)
        });
        return null;
    }
}
const cbufAddText = module.base.add(0x18D840);
const packetEvent = module.base.add(0x67520);
const netchanProcess = module.base.add(0x1A5960);
const decodeMessage = module.base.add(0x6BF80);
const parseServerMessage = module.base.add(0x6E6A0);
const parseGameState = module.base.add(0x6DEA0);
const parseConfigStrings = module.base.add(0x6DB20);
const storeRawConfigString = module.base.add(0x6DAA0);
const parseSnapshot = module.base.add(0x6D170);
const parsePlayerState = module.base.add(0x1A4230);
const parseMatchState = module.base.add(0x6D060);
const parsePacketClients = module.base.add(0x6CC60);
const parsePacketEntities = module.base.add(0x6C2F0);
const parsePacketAux = module.base.add(0x6C840);
const readDeltaField = module.base.add(0x1A27F0);
const readDeltaEntity = module.base.add(0x1A3670);
const readFieldIndex = module.base.add(0x1A3250);
const readBit = module.base.add(0xC370);
const readBits = module.base.add(0x1A13A0);
const readPrimitive5A14E0 = module.base.add(0x1A14E0);
const readPrimitive5A1580 = module.base.add(0x1A1580);
const playerStateFields = module.base.add(0x855F70);
const playerStateFieldCount = 235;
const playerStateFieldSize = 12;
const parsePlayerStateEnd = module.base.add(0x1A5407);
const comError = module.base.add(0x197D20);
const codolUnhandledExceptionFilter = module.base.add(0x23C820);
const configChecksumCompare = module.base.add(0x6E06B);
const expectedConfigChecksum = module.base.add(0x29F7D90);
const configChecksumInitialized = module.base.add(0x29F9934);
const connectionState = module.base.add(0x162E7EC);
const encodedClientConnection = module.base.add(0x162A538);
const encodedClientActive = module.base.add(0x162E838);
const localClientIndex = module.base.add(0x7417BA8);
const encodedCgameTable = module.base.add(0x1619510);
const weaponVariantTable = module.base.add(0x13F5A40);
const weaponRegistryCount = module.base.add(0x7417B88);
const weaponRegistryReset = module.base.add(0x2C370);
const weaponResolver = module.base.add(0x2C5C0);
const cgameInit = module.base.add(0x45730);
const cgSelectWeapon = module.base.add(0x162260);
const cgRespawn = module.base.add(0x4EE10);
const cgRespawnTransition = module.base.add(0x128216);
const clSetUserCmdWeapons = module.base.add(0xF93C0);
const clFinishMove = module.base.add(0x5F940);
const clExecuteBindingAction = module.base.add(0x60870);

function readU32(pointer, offset) {
    try { return pointer.add(offset).readU32(); } catch (_) { return null; }
}

function readS32(pointer, offset) {
    try { return pointer.add(offset).readS32(); } catch (_) { return null; }
}

function readU16(pointer, offset) {
    try { return pointer.add(offset).readU16(); } catch (_) { return null; }
}

function readU8(pointer, offset) {
    try { return pointer.add(offset).readU8(); } catch (_) { return null; }
}

function readFloat(pointer, offset) {
    try { return pointer.add(offset).readFloat(); } catch (_) { return null; }
}

function readPointer(pointer, offset) {
    try { return pointer.add(offset).readPointer(); } catch (_) { return null; }
}

function readHex(pointer, size) {
    try {
        const data = pointer.readByteArray(size);
        if (data === null) return null;
        return Array.from(new Uint8Array(data), value => value.toString(16).padStart(2, '0')).join('');
    } catch (_) {
        return null;
    }
}

function readString(pointer) {
    if (pointer === null || pointer.isNull()) return null;
    try { return pointer.readCString(); } catch (_) { return null; }
}

function readClientActive() {
    const encoded = readU32(encodedClientActive, 0);
    return encoded === null ? null : ptr((encoded ^ 0x6891D1C7) >>> 0);
}

function readCgame() {
    const clientIndex = readU32(localClientIndex, 0);
    if (clientIndex === null || clientIndex > 15) return null;
    const encoded = readU32(encodedCgameTable, clientIndex * 4);
    return encoded === null ? null : ptr((encoded ^ 0xFBB2C97A) >>> 0);
}

function readWeaponVariant(weaponAssetIndex) {
    if (weaponAssetIndex === null || weaponAssetIndex <= 0 || weaponAssetIndex > 0x3ff) {
        return null;
    }
    const definition = readPointer(weaponVariantTable, weaponAssetIndex * 4);
    if (definition === null || definition.isNull()) return null;
    return {
        address: definition.toString(),
        weapon_asset_index: weaponAssetIndex,
        selection_kind_0488: readS32(definition, 0x488),
        ammo_index: readS32(definition, 0x6B8),
        clip_index: readS32(definition, 0x6C0),
        linked_weapon_asset_index: readS32(definition, 0xD24),
        selection_requires_ammo: readU8(definition, 0xD7F)
    };
}

function readWeaponSelectionState(candidateWeapon) {
    const cgame = readCgame();
    const clientActive = readClientActive();
    if (cgame === null || clientActive === null) return null;
    const weapon = readU16(clientActive, 0x3608);
    return {
        cgame: cgame.toString(),
        client_active: clientActive.toString(),
        weapon_select: readU32(cgame, 0xBD00C),
        current_weapon_asset_index: readU32(cgame, 0x340),
        spawn_generation: readU8(cgame, 0x19C),
        held_weapon_asset_indexes: Array.from(
            { length: 15 },
            (_, index) => readU32(cgame, 0x2A4 + index * 4)
        ),
        cgame_user_cmd_weapon: weapon,
        cgame_user_cmd_off_hand_index: weapon === null
            ? null
            : readU16(cgame, 0xBD01C + weapon * 2),
        cgame_user_cmd_last_weapon_for_alt: readU16(clientActive, 0x360C),
        candidate_weapon_variant: readWeaponVariant(candidateWeapon)
    };
}

function readRespawnState(playerState) {
    return {
        address: playerState.toString(),
        pm_type: readS32(playerState, 0x004),
        other_flags: readU32(playerState, 0x010),
        client_num: readS32(playerState, 0x130),
        spawn_generation: readU8(playerState, 0x19C)
    };
}

let lastRespawnTransitionKey = null;
safeAttach(cgRespawnTransition, {
    onEnter(_) {
        const cgame = readCgame();
        const oldState = readRespawnState(this.context.eax);
        const newState = readRespawnState(this.context.ebx);
        const transition = {
            map_restart: cgame === null ? null : readS32(cgame, 0xAE4D0),
            old_state: oldState,
            new_state: newState,
            generation_changed:
                oldState.spawn_generation !== newState.spawn_generation,
            client_changed: oldState.client_num !== newState.client_num,
            player_flag_changed:
                ((oldState.other_flags ^ newState.other_flags) & 0x1000) !== 0
        };
        const key = JSON.stringify([
            transition.map_restart,
            oldState.pm_type,
            oldState.other_flags,
            oldState.client_num,
            oldState.spawn_generation,
            newState.pm_type,
            newState.other_flags,
            newState.client_num,
            newState.spawn_generation
        ]);
        if (key === lastRespawnTransitionKey) return;
        lastRespawnTransitionKey = key;
        send({
            event: 'cg_respawn_transition',
            timestamp_ms: Date.now(),
            ...transition
        });
    }
});

safeAttach(cgRespawn, {
    onEnter(args) {
        this.localClient = this.context.eax.toInt32();
        this.spectate = args[0].toInt32();
        this._returnAddress = this.context.esp.readPointer();
        this.before = readWeaponSelectionState(null);
    },
    onLeave(_) {
        send({
            event: 'cg_respawn',
            timestamp_ms: Date.now(),
            local_client: this.localClient,
            spectate: this.spectate,
            return_address: this._returnAddress.sub(module.base).toString(),
            before: this.before,
            after: readWeaponSelectionState(null)
        });
    }
});

safeAttach(cgSelectWeapon, {
    onEnter(args) {
        this.candidateWeapon = args[0].toUInt32();
        this.before = readWeaponSelectionState(this.candidateWeapon);
    },
    onLeave(retval) {
        send({
            event: 'cg_select_weapon',
            timestamp_ms: Date.now(),
            candidate_weapon: this.candidateWeapon,
            result: retval.toInt32(),
            before: this.before,
            after: readWeaponSelectionState(this.candidateWeapon)
        });
    }
});

let lastSetUserCmdWeaponsKey = null;
safeAttach(clSetUserCmdWeapons, {
    onEnter(_) {
        const weapon = this.context.ecx.toUInt32();
        const lastWeaponForAlt = this.context.edx.toUInt32();
        const state = readWeaponSelectionState(weapon);
        const key = JSON.stringify([
            weapon,
            lastWeaponForAlt,
            state === null ? null : state.current_weapon_asset_index,
            state === null ? null : state.cgame_user_cmd_weapon
        ]);
        if (key === lastSetUserCmdWeaponsKey) return;
        lastSetUserCmdWeaponsKey = key;
        send({
            event: 'cl_set_usercmd_weapons',
            timestamp_ms: Date.now(),
            weapon: weapon,
            last_weapon_for_alt: lastWeaponForAlt,
            state: state
        });
    }
});

let lastFinishMoveKey = null;
// This input-finalization routine begins with an instruction sequence that some
// Frida builds cannot relocate.  Weapon/input telemetry is supplementary to the
// join trace, so do not let it prevent the packet, Cbuf, and Com_Error hooks from
// arming.
try {
safeAttach(clFinishMove, {
    onEnter(_) {
        this.cmd = this.context.esi;
    },
    onLeave(_) {
        const command = {
            command_time: readU32(this.cmd, 0x00),
            weapon: readU16(this.cmd, 0x14),
            off_hand_index: readU16(this.cmd, 0x16),
            last_weapon_alt_mode_switch: readU16(this.cmd, 0x18)
        };
        const state = readWeaponSelectionState(command.weapon);
        const key = JSON.stringify([
            command.weapon,
            command.off_hand_index,
            command.last_weapon_alt_mode_switch,
            state === null ? null : state.current_weapon_asset_index
        ]);
        if (key === lastFinishMoveKey) return;
        lastFinishMoveKey = key;
        send({
            event: 'cl_finish_move_weapon',
            timestamp_ms: Date.now(),
            command: command,
            state: state
        });
    }
});
} catch (error) {
    send({
        event: 'hook_unavailable',
        hook: 'cl_finish_move',
        address: clFinishMove.toString(),
        error: String(error)
    });
}

function isForcedCbufThunk(returnAddress) {
    try {
        const start = returnAddress.sub(15);
        const data = start.readByteArray(18);
        if (data === null) return false;
        const bytes = new Uint8Array(data);
        const expectedTarget = cbufAddText.toUInt32();
        const encodedTarget = (
            bytes[9] |
            (bytes[10] << 8) |
            (bytes[11] << 16) |
            (bytes[12] << 24)
        ) >>> 0;
        return bytes[0] === 0x8B && bytes[1] === 0x44 &&
            bytes[2] === 0x24 && bytes[3] === 0x04 &&
            bytes[4] === 0x8B && bytes[5] === 0x4C &&
            bytes[6] === 0x24 && bytes[7] === 0x08 &&
            bytes[8] === 0xBA && encodedTarget === expectedTarget &&
            bytes[13] === 0xFF && bytes[14] === 0xD2 &&
            bytes[15] === 0xC2 && bytes[16] === 0x08 && bytes[17] === 0x00;
    } catch (_) {
        return false;
    }
}

function classifyCbufCaller(returnAddress) {
    const callerModule = Process.findModuleByAddress(returnAddress);
    if (callerModule !== null) {
        const isClientModule = callerModule.name.toLowerCase() === module.name.toLowerCase();
        return {
            kind: isClientModule ? 'client-module' : 'external-module',
            evidence_source: isClientModule
                ? 'natural-client-caller'
                : 'external-module-caller',
            module_name: callerModule.name,
            module_path: callerModule.path,
            module_base: callerModule.base.toString(),
            module_rva: returnAddress.sub(callerModule.base).toString()
        };
    }
    const range = Process.findRangeByAddress(returnAddress);
    const forcedThunk = isForcedCbufThunk(returnAddress);
    return {
        kind: forcedThunk
            ? 'frida-forced-thunk'
            : (range !== null && range.protection.indexOf('x') !== -1
                ? 'anonymous-executable'
                : 'unknown'),
        evidence_source: forcedThunk ? 'client-native-forced' : 'unattributed',
        range_base: range === null ? null : range.base.toString(),
        range_size: range === null ? null : range.size,
        range_protection: range === null ? null : range.protection
    };
}

safeAttach(cbufAddText, {
    onEnter(_) {
        const returnAddress = this.context.esp.readPointer();
        const commandPointer = this.context.eax;
        send({
            event: 'cbuf_command',
            timestamp_ms: Date.now(),
            thread_id: Process.getCurrentThreadId(),
            local_client: this.context.ecx.toInt32(),
            command_pointer: commandPointer.toString(),
            command: readString(commandPointer),
            return_address: returnAddress.toString(),
            caller: classifyCbufCaller(returnAddress)
        });
    }
});

function readReliableState() {
    const encoded = readU32(encodedClientConnection, 0);
    if (encoded === null) return null;
    const clientConnection = ptr((encoded ^ 0xD362501F) >>> 0);
    return {
        address: clientConnection.toString(),
        reliable_sequence: readU32(clientConnection, 0x140),
        reliable_acknowledge: readU32(clientConnection, 0x144),
        server_message_sequence: readU32(clientConnection, 0x40148)
    };
}

function readCommittedPlayerState(playerState) {
    return {
        command_time: readS32(playerState, 0x000),
        pm_type: readS32(playerState, 0x004),
        pm_time: readS32(playerState, 0x008),
        pm_flags: readU32(playerState, 0x00c),
        ground_entity_num: readU32(playerState, 0x0AC),
        gravity: readS32(playerState, 0x090),
        jump_time: readS32(playerState, 0x0BC),
        jump_origin_z: readFloat(playerState, 0x0C0),
        damage_event: readU32(playerState, 0x1B4),
        damage_yaw: readU32(playerState, 0x1B8),
        damage_pitch: readU32(playerState, 0x1BC),
        damage_count: readU32(playerState, 0x1C0),
        health: readU32(playerState, 0x1c4),
        max_health: readU32(playerState, 0x1CC),
        shellshock_index: readU32(playerState, 0x5AC),
        shellshock_time: readU32(playerState, 0x5B0),
        shellshock_duration: readU32(playerState, 0x5B4),
        spawn_generation: readU8(playerState, 0x19c),
        other_flags: readU32(playerState, 0x010),
        view_angles: [
            readFloat(playerState, 0x14c),
            readFloat(playerState, 0x150),
            readFloat(playerState, 0x154)
        ],
        view_height_target: readS32(playerState, 0x158),
        view_height_current: readFloat(playerState, 0x15c),
        origin: [
            readFloat(playerState, 0x01c),
            readFloat(playerState, 0x020),
            readFloat(playerState, 0x024)
        ],
        candidate_offsets: {
            '0x028_f32': readFloat(playerState, 0x028),
            '0x02c_f32': readFloat(playerState, 0x02c),
            '0x018_i32': readS32(playerState, 0x018),
            '0x030_f32': readFloat(playerState, 0x030),
            '0x034_f32': readFloat(playerState, 0x034),
            '0x038_f32': readFloat(playerState, 0x038),
            '0x130_i32': readS32(playerState, 0x130),
            '0x144_i32': readS32(playerState, 0x144)
        }
    };
}

try {
safeAttach(netchanProcess, {
    onEnter(args) {
        this.msg = this.context.edi;
        this.chan = args[0];
        this.incomingBefore = readU32(this.chan, 12);
        const data = readPointer(this.msg, 8);
        const cursize = readU32(this.msg, 20);
        const captureSize = data !== null && cursize !== null ? Math.min(cursize, 64) : 0;
        send({
            event: 'netchan_process_enter',
            msg: this.msg.toString(),
            chan: this.chan.toString(),
            cursize: cursize,
            readcount: readU32(this.msg, 28),
            incoming_sequence: this.incomingBefore,
            packet_hex: captureSize > 0 ? readHex(data, captureSize) : null
        });
    },
    onLeave(retval) {
        send({
            event: 'netchan_process_leave',
            result: retval.toInt32(),
            incoming_before: this.incomingBefore,
            incoming_after: readU32(this.chan, 12),
            readcount: readU32(this.msg, 28)
        });
    }
});
} catch (error) {
    send({
        event: 'hook_unavailable',
        hook: 'netchan_process',
        address: netchanProcess.toString(),
        error: String(error)
    });
}

safeAttach(decodeMessage, {
    onEnter(args) {
        this.data = args[0];
        this.size = args[1].toInt32();
        send({
            event: 'decode_enter',
            size: this.size,
            encoded_hex: this.size > 0 ? readHex(this.data, Math.min(this.size, 64)) : ''
        });
    },
    onLeave(_) {
        send({
            event: 'decode_leave',
            size: this.size,
            decoded_hex: this.size > 0 ? readHex(this.data, Math.min(this.size, 64)) : ''
        });
    }
});

function traceParser(name, address) {
    safeAttach(address, {
        onEnter(_) {
            const msg = this.context.edi;
            const data = readPointer(msg, 8);
            const cursize = readU32(msg, 20);
            const readcount = readU32(msg, 28);
            const remaining = cursize !== null && readcount !== null ? Math.max(0, cursize - readcount) : 0;
            send({
                event: name,
                cursize: cursize,
                readcount: readcount,
                remaining_hex: data !== null && readcount !== null && remaining > 0
                    ? readHex(data.add(readcount), Math.min(remaining, 64))
                    : ''
            });
        }
    });
}

safeAttach(parseServerMessage, {
    onEnter(_) {
        this.msg = this.context.edi;
        const data = readPointer(this.msg, 8);
        const cursize = readU32(this.msg, 20);
        const readcount = readU32(this.msg, 28);
        const remaining = cursize !== null && readcount !== null
            ? Math.max(0, cursize - readcount)
            : 0;
        send({
            event: 'parse_server_message_enter',
            cursize: cursize,
            readcount: readcount,
            remaining_hex: data !== null && readcount !== null && remaining > 0
                ? readHex(data.add(readcount), Math.min(remaining, 64))
                : '',
            reliable: readReliableState()
        });
    },
    onLeave(_) {
        send({
            event: 'parse_server_message_leave',
            overflowed: readU32(this.msg, 0),
            readcount: readU32(this.msg, 28),
            reliable: readReliableState()
        });
    }
});
safeAttach(packetEvent, {
    onLeave(retval) {
        send({
            event: 'packet_event_leave',
            accepted: retval.toInt32(),
            reliable: readReliableState()
        });
    }
});
traceParser('parse_gamestate', parseGameState);

safeAttach(parseConfigStrings, {
    onEnter(_) {
        send({ event: 'parse_configstrings_enter' });
    },
    onLeave(_) {
        send({ event: 'parse_configstrings_leave' });
    }
});

safeAttach(storeRawConfigString, {
    onEnter(args) {
        send({
            event: 'configstring_store',
            index: args[0].toInt32(),
            value: readString(this.context.edi)
        });
    }
});

let weaponRegistryInitDepth = 0;
safeAttach(weaponRegistryReset, {
    onEnter(_) {
        this.registryCountBefore = readU32(weaponRegistryCount, 0);
        this.caller = classifyCbufCaller(this.returnAddress);
    },
    onLeave(_) {
        send({
            event: 'weapon_registry_reset',
            caller: this.caller,
            registry_count_before: this.registryCountBefore,
            registry_count_after: readU32(weaponRegistryCount, 0)
        });
    }
});

safeAttach(cgameInit, {
    onEnter(_) {
        weaponRegistryInitDepth += 1;
        send({
            event: 'weapon_registry_init_enter',
            registry_count: readU32(weaponRegistryCount, 0)
        });
    },
    onLeave(_) {
        send({
            event: 'weapon_registry_init_leave',
            registry_count: readU32(weaponRegistryCount, 0)
        });
        weaponRegistryInitDepth = Math.max(0, weaponRegistryInitDepth - 1);
    }
});

safeAttach(weaponResolver, {
    onEnter(args) {
        this.weaponName = readString(args[0]);
        this.registryCountBefore = readU32(weaponRegistryCount, 0);
        this.traceWeaponRegistry = this.weaponName !== null &&
            (this.weaponName.startsWith('*') || this.registryCountBefore >= 345);
        if (this.traceWeaponRegistry) {
            this.caller = classifyCbufCaller(this.returnAddress);
        }
    },
    onLeave(retval) {
        if (!this.traceWeaponRegistry) return;
        send({
            event: 'weapon_registry_resolve',
            name: this.weaponName,
            caller: this.caller,
            registry_count_before: this.registryCountBefore,
            result: retval.toInt32(),
            registry_count_after: readU32(weaponRegistryCount, 0)
        });
    }
});

function traceMessageCursor(name, address, locateMessage) {
    safeAttach(address, {
        onEnter(args) {
            this.msg = locateMessage.call(this, args);
            send({
                event: name + '_enter',
                readcount: readU32(this.msg, 28),
                bit: readU32(this.msg, 32),
                overflowed: readU32(this.msg, 0)
            });
        },
        onLeave(_) {
            send({
                event: name + '_leave',
                readcount: readU32(this.msg, 28),
                bit: readU32(this.msg, 32),
                overflowed: readU32(this.msg, 0),
                connection_state: readU32(connectionState, 0)
            });
        }
    });
}

traceMessageCursor('parse_snapshot', parseSnapshot, function(_) { return this.context.ecx; });
traceMessageCursor('parse_matchstate', parseMatchState, function(args) { return args[1]; });
traceMessageCursor('parse_packet_clients', parsePacketClients, function(_) { return this.context.edx; });
traceMessageCursor('parse_packet_entities', parsePacketEntities, function(args) { return args[1]; });
traceMessageCursor('parse_packet_aux', parsePacketAux, function(_) { return this.context.edx; });

safeAttach(parsePlayerState, {
    onEnter(_) {
        this.msg = this.context.esi;
        this.target = this.context.ecx;
        send({
            event: 'parse_playerstate_enter',
            target: this.target.toString(),
            readcount: readU32(this.msg, 28),
            bit: readU32(this.msg, 32),
            overflowed: readU32(this.msg, 0)
        });
    },
    onLeave(_) {
        send({
            event: 'parse_playerstate_leave',
            target: this.target.toString(),
            readcount: readU32(this.msg, 28),
            bit: readU32(this.msg, 32),
            overflowed: readU32(this.msg, 0),
            connection_state: readU32(connectionState, 0),
            player_state: readCommittedPlayerState(this.target)
        });
    }
});

const activeDeltaEntities = new Map();
const activeDeltaFields = new Map();
let deltaFieldTraceBudget = 12;
let deltaEntityTraceBudget = 4;
let representativeScriptMoverTraceBudget = 32;
const representativeEntityNumber = __TRACE_ENTITY__;
let inputFieldTraceBudget = 0;

safeAttach(clExecuteBindingAction, {
    onEnter(_) {
        const stack = this.context.esp;
        const action = readS32(stack, 4);
        const keyCode = readS32(stack, 8);
        inputFieldTraceBudget = 128;
        send({
            event: 'binding_action',
            local_client: this.context.ecx.toInt32(),
            action: action,
            key_code: keyCode,
            field_trace_budget: inputFieldTraceBudget
        });
    }
});

safeAttach(readDeltaEntity, {
    onEnter(_) {
        const stack = this.context.esp;
        const entityNumber = stack.add(20).readS32();
        const traceRepresentative = representativeEntityNumber !== null &&
            entityNumber === representativeEntityNumber &&
            representativeScriptMoverTraceBudget > 0;
        if (deltaEntityTraceBudget <= 0 && !traceRepresentative) {
            this.active = false;
            return;
        }
        this.active = true;
        this._threadId = Process.getCurrentThreadId();
        this.msg = stack.add(4).readPointer();
        this.baseline = stack.add(12).readPointer();
        this.target = stack.add(16).readPointer();
        this.entityNumber = entityNumber;
        this.startBit = readU32(this.msg, 32);
        if (traceRepresentative)
            --representativeScriptMoverTraceBudget;
        else
            --deltaEntityTraceBudget;
        activeDeltaEntities.set(this._threadId, this);
        send({
            event: 'entity_delta_enter',
            entity_number: this.entityNumber,
            bit: this.startBit,
            readcount: readU32(this.msg, 28),
            overflowed: readU32(this.msg, 0),
            baseline_number: readS32(this.baseline, 0),
            baseline_type: readS32(this.baseline, 4),
            baseline_model_index: readU32(this.baseline, 0x5C)
        });
    },
    onLeave(retval) {
        if (!this.active) return;
        const endBit = readU32(this.msg, 32);
        send({
            event: 'entity_delta_leave',
            entity_number: this.entityNumber,
            result: retval.toInt32(),
            start_bit: this.startBit,
            end_bit: endBit,
            consumed_bits: endBit === null || this.startBit === null
                ? null
                : endBit - this.startBit,
            readcount: readU32(this.msg, 28),
            overflowed: readU32(this.msg, 0),
            target_number: readS32(this.target, 0),
            target_type: readS32(this.target, 4),
            target_model_index: readU32(this.target, 0x5C)
        });
        if (activeDeltaEntities.get(this._threadId) === this) {
            activeDeltaEntities.delete(this._threadId);
        }
    }
});

safeAttach(readFieldIndex, {
    onEnter(_) {
        const active = activeDeltaEntities.get(Process.getCurrentThreadId());
        if (active === undefined) {
            this.active = false;
            return;
        }
        const stack = this.context.esp;
        this.active = true;
        this.msg = stack.add(4).readPointer();
        this.width = stack.add(8).readS32();
        this.startBit = readU32(this.msg, 32);
    },
    onLeave(retval) {
        if (!this.active) return;
        const endBit = readU32(this.msg, 32);
        send({
            event: 'entity_field_index',
            width: this.width,
            result: retval.toInt32(),
            start_bit: this.startBit,
            end_bit: endBit,
            consumed_bits: endBit === null || this.startBit === null
                ? null
                : endBit - this.startBit,
            overflowed: readU32(this.msg, 0)
        });
    }
});

safeAttach(readDeltaField, {
    onEnter(_) {
        if (deltaFieldTraceBudget <= 0 && inputFieldTraceBudget <= 0) {
            this.active = false;
            return;
        }
        const stack = this.context.esp;
        const returnAddress = stack.readPointer();
        const activeEntity = activeDeltaEntities.get(Process.getCurrentThreadId());
        const inPlayerState = returnAddress.compare(parsePlayerState) >= 0 &&
            returnAddress.compare(parsePlayerStateEnd) < 0;
        if (!inPlayerState && activeEntity === undefined) {
            this.active = false;
            return;
        }

        const field = this.context.ecx;
        const delta = field.sub(playerStateFields).toInt32();
        if (inPlayerState && (delta < 0 ||
            delta >= playerStateFieldCount * playerStateFieldSize ||
            delta % playerStateFieldSize !== 0)) {
            this.active = false;
            return;
        }

        this.active = true;
        this._threadId = Process.getCurrentThreadId();
        this.msg = stack.add(4).readPointer();
        this.target = this.context.edx;
        this.baseline = stack.add(12).readPointer();
        this.kind = inPlayerState ? 'playerstate' : 'entity';
        this.fieldIndex = inPlayerState ? delta / playerStateFieldSize : null;
        this.fieldAddress = field.sub(module.base).toString();
        this.fieldOffset = readS32(field, 0);
        this.bits = readS32(field, 4);
        this.changeHints = readU32(field, 8);
        this.startBit = readU32(this.msg, 32);
        if (inputFieldTraceBudget > 0) --inputFieldTraceBudget;
        else --deltaFieldTraceBudget;
        activeDeltaFields.set(this._threadId, this);
        send({
            event: this.kind + '_delta_field_enter',
            field_index: this.fieldIndex,
            field_address: this.fieldAddress,
            field_offset: this.fieldOffset,
            bits: this.bits,
            change_hints: this.changeHints,
            return_address: returnAddress.sub(module.base).toString(),
            target_address: this.target.toString(),
            baseline_address: this.baseline.toString(),
            bit: this.startBit,
            readcount: readU32(this.msg, 28),
            target_value_before: readU32(this.target, this.fieldOffset),
            baseline_value: readU32(this.baseline, this.fieldOffset),
            null_baseline: stack.add(16).readU8(),
            context_index: readU32(stack, 20)
        });
    },
    onLeave(_) {
        if (!this.active) return;
        const endBit = readU32(this.msg, 32);
        send({
            event: this.kind + '_delta_field_leave',
            field_index: this.fieldIndex,
            field_address: this.fieldAddress,
            field_offset: this.fieldOffset,
            bits: this.bits,
            start_bit: this.startBit,
            end_bit: endBit,
            consumed_bits: endBit === null || this.startBit === null
                ? null
                : endBit - this.startBit,
            readcount: readU32(this.msg, 28),
            overflowed: readU32(this.msg, 0),
            target_value_after: readU32(this.target, this.fieldOffset)
        });
        if (activeDeltaFields.get(this._threadId) === this) {
            activeDeltaFields.delete(this._threadId);
        }
    }
});

function traceDeltaPrimitive(name, address, locateRequestedBits) {
    safeAttach(address, {
        onEnter(_) {
            const active = activeDeltaFields.get(Process.getCurrentThreadId());
            if (active === undefined) {
                this.active = false;
                return;
            }
            this.active = true;
            this.kind = active.kind;
            this.fieldIndex = active.fieldIndex;
            this.msg = active.msg;
            this.startBit = readU32(this.msg, 32);
            this.requestedBits = locateRequestedBits.call(this);
        },
        onLeave(retval) {
            if (!this.active) return;
            const endBit = readU32(this.msg, 32);
            send({
                event: this.kind + '_delta_primitive',
                primitive: name,
                field_index: this.fieldIndex,
                requested_bits: this.requestedBits,
                start_bit: this.startBit,
                end_bit: endBit,
                consumed_bits: endBit === null || this.startBit === null
                    ? null
                    : endBit - this.startBit,
                result: retval.toUInt32()
            });
        }
    });
}

traceDeltaPrimitive('sub_40C370', readBit, function() { return 1; });
traceDeltaPrimitive('sub_5A13A0', readBits, function() {
    return this.context.esp.add(4).readS32();
});
traceDeltaPrimitive('sub_5A14E0', readPrimitive5A14E0, function() { return null; });
traceDeltaPrimitive('sub_5A1580', readPrimitive5A1580, function() { return 32; });

safeAttach(parseGameState, {
    onLeave(_) {
        send({
            event: 'parse_gamestate_leave',
            connection_state: readU32(module.base, 0x162E7EC)
        });
    }
});

safeAttach(configChecksumCompare, {
    onEnter(_) {
        send({
            event: 'config_checksum_compare',
            expected: readU32(expectedConfigChecksum, 0),
            received: this.context.edi.toUInt32(),
            initialized: readU32(configChecksumInitialized, 0),
            instruction: configChecksumCompare.toString()
        });
    }
});

safeAttach(comError, {
    onEnter(args) {
        const values = [];
        for (let index = 2; index < 7; ++index) {
            values.push({
                raw: args[index].toString(),
                string: readString(args[index])
            });
        }
        let backtrace = [];
        try {
            backtrace = Thread.backtrace(this.context, Backtracer.ACCURATE)
                .slice(0, 20)
                .map(address => address.sub(module.base).toString());
        } catch (error) {
            backtrace = [`<backtrace failed: ${error.message}>`];
        }
        send({
            event: 'com_error',
            code: args[0].toInt32(),
            format: readString(args[1]),
            arguments: values,
            backtrace: backtrace
        });
    }
});

function captureBacktrace(context) {
    try {
        return Thread.backtrace(context, Backtracer.ACCURATE)
            .slice(0, 24)
            .map(address => {
                const owner = Process.findModuleByAddress(address);
                return owner === null
                    ? address.toString()
                    : owner.name + '+' + address.sub(owner.base).toString();
            });
    } catch (error) {
        return [`<backtrace failed: ${error.message}>`];
    }
}

function moduleRelativeAddress(address) {
    if (address === null) return null;
    const owner = Process.findModuleByAddress(address);
    return owner === null
        ? address.toString()
        : owner.name + '+' + address.sub(owner.base).toString();
}

function readFaultStackCandidates(stackPointer) {
    if (stackPointer === null) return [];
    const candidates = [];
    const seen = new Set();
    for (let index = 0; index < 96; ++index) {
        const raw = readU32(stackPointer, index * 4);
        if (raw === null || raw === 0) continue;
        const address = ptr(raw);
        const owner = Process.findModuleByAddress(address);
        if (owner === null) continue;
        const relative = owner.name + '+' + address.sub(owner.base).toString();
        if (seen.has(relative)) continue;
        seen.add(relative);
        candidates.push({ stack_offset: index * 4, address: relative });
        if (candidates.length >= 32) break;
    }
    return candidates;
}

// CODOL installs this top-level filter around the native game thread. Capture the
// original EXCEPTION_POINTERS before its crash reporter converts the fault into exit(-1).
safeAttach(codolUnhandledExceptionFilter, {
    onEnter(args) {
        const exceptionPointers = args[0];
        const exceptionRecord = readPointer(exceptionPointers, 0);
        const contextRecord = readPointer(exceptionPointers, 4);
        const exceptionCode = exceptionRecord === null ? null : readU32(exceptionRecord, 0);
        const exceptionAddressRaw = exceptionRecord === null ? null : readU32(exceptionRecord, 12);
        const parameterCountRaw = exceptionRecord === null ? null : readU32(exceptionRecord, 16);
        const parameterCount = parameterCountRaw === null ? 0 : Math.min(parameterCountRaw, 15);
        const parameters = [];
        if (exceptionRecord !== null) {
            for (let index = 0; index < parameterCount; ++index) {
                parameters.push(readU32(exceptionRecord, 20 + index * 4));
            }
        }
        const eipRaw = contextRecord === null ? null : readU32(contextRecord, 184);
        const espRaw = contextRecord === null ? null : readU32(contextRecord, 196);
        const eip = eipRaw === null ? null : ptr(eipRaw);
        const esp = espRaw === null ? null : ptr(espRaw);
        send({
            event: 'unhandled_exception',
            thread_id: Process.getCurrentThreadId(),
            exception_pointers: exceptionPointers.toString(),
            exception_code: exceptionCode,
            exception_flags: exceptionRecord === null ? null : readU32(exceptionRecord, 4),
            exception_address: exceptionAddressRaw === null
                ? null
                : moduleRelativeAddress(ptr(exceptionAddressRaw)),
            exception_parameters: parameters,
            access_kind: exceptionCode === 0xC0000005 && parameters.length >= 1
                ? parameters[0]
                : null,
            access_address: exceptionCode === 0xC0000005 && parameters.length >= 2
                ? ptr(parameters[1]).toString()
                : null,
            registers: contextRecord === null ? null : {
                eax: readU32(contextRecord, 176),
                ebx: readU32(contextRecord, 164),
                ecx: readU32(contextRecord, 172),
                edx: readU32(contextRecord, 168),
                esi: readU32(contextRecord, 160),
                edi: readU32(contextRecord, 156),
                ebp: readU32(contextRecord, 180),
                esp: espRaw,
                eip: eipRaw,
                eip_relative: moduleRelativeAddress(eip)
            },
            fault_stack_candidates: readFaultStackCandidates(esp),
            handler_backtrace: captureBacktrace(this.context)
        });
    }
});

const processExitHooks = [];
const hookedProcessExitAddresses = new Set();
function traceProcessExit(moduleName, exportName, argumentReader) {
    const owner = Process.findModuleByName(moduleName);
    if (owner === null) return;
    const address = owner.findExportByName(exportName);
    if (address === null || hookedProcessExitAddresses.has(address.toString())) return;
    hookedProcessExitAddresses.add(address.toString());
    processExitHooks.push({ module: owner.name, name: exportName, address: address.toString() });
    safeAttach(address, {
        onEnter(args) {
            let details = {};
            try { details = argumentReader(args); }
            catch (error) { details = { argument_error: error.message }; }
            send({
                event: 'process_exit_called',
                api_module: owner.name,
                api: exportName,
                address: address.toString(),
                thread_id: Process.getCurrentThreadId(),
                details: details,
                backtrace: captureBacktrace(this.context)
            });
        }
    });
}

for (const moduleName of ['kernel32.dll', 'KernelBase.dll']) {
    traceProcessExit(moduleName, 'ExitProcess', args => ({ exit_code: args[0].toUInt32() }));
    traceProcessExit(moduleName, 'TerminateProcess', args => ({
        process_handle: args[0].toString(),
        exit_code: args[1].toUInt32()
    }));
}
traceProcessExit('ntdll.dll', 'RtlExitUserProcess', args => ({ exit_code: args[0].toUInt32() }));
traceProcessExit('ntdll.dll', 'NtTerminateProcess', args => ({
    process_handle: args[0].toString(),
    exit_code: args[1].toUInt32()
}));
for (const moduleName of ['ucrtbase.dll', 'msvcrt.dll']) {
    traceProcessExit(moduleName, 'exit', args => ({ exit_code: args[0].toUInt32() }));
    traceProcessExit(moduleName, '_exit', args => ({ exit_code: args[0].toUInt32() }));
    traceProcessExit(moduleName, 'abort', _args => ({}));
}

send({
    event: 'ready',
    module_base: module.base.toString(),
    cbuf_add_text: cbufAddText.toString(),
    packet_event: packetEvent.toString(),
    netchan_process: netchanProcess.toString(),
    decode_message: decodeMessage.toString(),
    parse_server_message: parseServerMessage.toString(),
    parse_gamestate: parseGameState.toString(),
    weapon_registry_reset: weaponRegistryReset.toString(),
    weapon_resolver: weaponResolver.toString(),
    cgame_init: cgameInit.toString(),
    read_delta_field: readDeltaField.toString(),
    playerstate_fields: playerStateFields.toString(),
    com_error: comError.toString(),
    unhandled_exception_filter: codolUnhandledExceptionFilter.toString(),
    config_checksum_compare: configChecksumCompare.toString(),
    expected_config_checksum: expectedConfigChecksum.toString(),
    cg_select_weapon: cgSelectWeapon.toString(),
    cg_respawn: cgRespawn.toString(),
    cg_respawn_transition: cgRespawnTransition.toString(),
    cl_set_usercmd_weapons: clSetUserCmdWeapons.toString(),
    cl_finish_move: clFinishMove.toString(),
    process_exit_hooks: processExitHooks,
    reliable: readReliableState()
});
"""
    return source.replace(
        "__TRACE_ENTITY__", "null" if trace_entity is None else str(trace_entity)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=300.0)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument(
        "--cbuf-log",
        type=Path,
        help="Write Cbuf_AddText calls to a separate JSONL stream",
    )
    parser.add_argument(
        "--stop-file",
        type=Path,
        help="Stop cleanly when this file appears; intended for lifecycle orchestrators",
    )
    parser.add_argument(
        "--asset-watch-only",
        action="store_true",
        help="Load only the bounded read-only weapon-group asset probe",
    )
    parser.add_argument(
        "--trace-entity",
        type=int,
        help="Capture up to 32 additional delta reads for one explicit entity number",
    )
    args = parser.parse_args()
    if args.trace_entity is not None and not 0 <= args.trace_entity < 2048:
        parser.error("--trace-entity must be in [0, 2048)")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    source = (
        build_asset_watch_script()
        if args.asset_watch_only
        else build_script(args.trace_entity)
    )
    script = session.create_script(source)
    stopped = Event()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    if args.cbuf_log is not None:
        args.cbuf_log.parent.mkdir(parents=True, exist_ok=True)

    def record_to(path: Path, event: str, **fields: Any) -> None:
        row = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            **fields,
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True) + "\n")

    def record(event: str, **fields: Any) -> None:
        record_to(args.log, event, **fields)

    def record_cbuf(event: str, **fields: Any) -> None:
        if args.cbuf_log is not None:
            record_to(args.cbuf_log, event, **fields)

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "send":
            raw_payload = message.get("payload", {})
            payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}
            event = payload.pop("event", "message")
            if event == "cbuf_command":
                record_cbuf(event, **payload)
            else:
                record(event, **payload)
                if event == "ready":
                    record_cbuf(
                        "ready",
                        pid=pid,
                        module_base=payload.get("module_base"),
                        cbuf_add_text=payload.get("cbuf_add_text"),
                    )
        else:
            record("frida_message", message=message)

    script.on("message", on_message)
    def on_detached(reason: str, crash: Any = None) -> None:
        record("detached", reason=reason, crash=str(crash) if crash is not None else None)
        record_cbuf("detached", reason=reason, crash=str(crash) if crash is not None else None)
        stopped.set()

    session.on("detached", on_detached)
    script.load()
    record("attached", pid=pid, duration=args.duration)
    record_cbuf("attached", pid=pid, duration=args.duration)
    try:
        deadline = None if args.duration <= 0 else time.monotonic() + args.duration
        while not stopped.wait(0.2):
            if args.stop_file is not None and args.stop_file.exists():
                record("stop_requested", stop_file=str(args.stop_file.resolve()))
                break
            if deadline is not None and time.monotonic() >= deadline:
                break
    except KeyboardInterrupt:
        record("interrupted")
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass
        record("stopped")
        record_cbuf("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
