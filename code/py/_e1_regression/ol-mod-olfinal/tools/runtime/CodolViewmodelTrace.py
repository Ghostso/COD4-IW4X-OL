#!/usr/bin/env python3
"""Trace CODOL first-person viewmodel construction and scene submission."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


IMAGE_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_MODEL_CANDIDATES = (
    "viewhands_tf141",
    "viewmodel_base_viewhands",
    "viewmodel_default",
    "viewmodel_usa_marine",
)


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


def build_script(
    max_samples: int,
    model_candidates: tuple[str, ...] = DEFAULT_MODEL_CANDIDATES,
) -> str:
    template = r"""
'use strict';

const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
const addresses = {
    get_viewmodel_weapon: module.base.add(0x2C680),
    update_view_weapon_anim: module.base.add(0x15C5F0),
    update_character_viewmodel: module.base.add(0x1593E0),
    resolve_character_models: module.base.add(0xC7A0),
    transform_character_selection: module.base.add(0xC980),
    unpack_character_selection: module.base.add(0xCBD0),
    convert_client_info: module.base.add(0x11BC80),
    resolve_xmodel: module.base.add(0x6A3120),
    change_viewmodel_dobj: module.base.add(0x1587E0),
    add_view_weapon: module.base.add(0x15C8A0),
    add_player_weapon: module.base.add(0x15BF90),
    add_dobj_to_scene: module.base.add(0xF5990),
    validate_scene_dobj: module.base.add(0x248EC0),
    create_client_dobj: module.base.add(0x19E610),
    is_modular_model_key: module.base.add(0x2E610),
    add_modular_models: module.base.add(0x2E800),
    get_modular_definition_index: module.base.add(0x2E650),
    build_modular_model_table: module.base.add(0x2DC10),
    resolve_base_models: module.base.add(0x307A50),
    resolve_attachment_models: module.base.add(0x307DE0),
    find_item_definition_by_name: module.base.add(0x184470),
    db_find_xasset_header: module.base.add(0x9E7D0),
    get_config_string: module.base.add(0xF9850),
    get_hud_weapon_name: module.base.add(0x156D10),
    update_hud_weapon_flags: module.base.add(0x1D7370),
    hud_utility_update: module.base.add(0x1D7500)
};
const activeLocalClientIndex = module.base.add(0x7417BA8);
const encodedCgameGlobals = module.base.add(0x1619510);
const encodedDobjTableIndex = module.base.add(0x7417BB8);
const weaponVariantTable = module.base.add(0x13F5A40);
const weaponInfoTable = module.base.add(0x1615C78);
const nativeWeaponDefinitionTable = module.base.add(0x13F5A40);
const characterModelRecords = module.base.add(0x13CD29C);
const cachedHudWeaponName = module.base.add(0x8E53A8);
const hudWeaponBlocked = module.base.add(0x8E5394);
const hudWeaponVisible = module.base.add(0x8E5395);
const hudWeaponInteractive = module.base.add(0x8E5396);
const configStringTypes = module.base.add(0x29F7DA0);
const dynamicConfigStringOffsets = module.base.add(0x756F2DC);
const dynamicConfigStringBuffer = module.base.add(0x7576124);
const cgamePointerXor = 0xFBB2C97A;
const dobjTablePointerXor = 0x39641402;
const maxSamples = __MAX_SAMPLES__;
const modelCandidateNames = __MODEL_CANDIDATES__;
const dbFindXAssetHeader = new NativeFunction(
    addresses.db_find_xasset_header,
    'pointer',
    ['int', 'pointer', 'bool']
);
const getConfigString = new NativeFunction(
    addresses.get_config_string,
    'pointer',
    ['int'],
    'fastcall'
);
const getModularDefinitionIndex = new NativeFunction(
    addresses.get_modular_definition_index,
    'int',
    ['pointer']
);
const modelCandidatePointers = modelCandidateNames.map((name) => ({
    name: name,
    pointer: Memory.allocUtf8String(name)
}));
let modelCandidates = null;

const counts = {
    get_viewmodel_weapon: 0,
    update_view_weapon_anim: 0,
    update_character_viewmodel: 0,
    resolve_character_models: 0,
    resolve_character_models_nonzero: 0,
    transform_character_selection: 0,
    unpack_character_selection: 0,
    convert_client_info: 0,
    resolve_character_xmodel: 0,
    change_viewmodel_dobj: 0,
    change_viewmodel_dobj_from_character: 0,
    add_view_weapon: 0,
    add_player_weapon: 0,
    create_client_dobj: 0,
    create_client_dobj_nonnull: 0,
    add_dobj_to_scene: 0,
    add_viewmodel_dobj_to_scene: 0,
    add_viewmodel_dobj_to_scene_nonnull: 0,
    validate_viewmodel_scene_dobj: 0,
    validate_viewmodel_scene_dobj_accepted: 0,
    is_modular_model_key: 0,
    add_modular_models: 0,
    add_modular_models_succeeded: 0,
    build_modular_model_table: 0,
    resolve_base_models: 0,
    resolve_attachment_models: 0,
    get_hud_weapon_name: 0,
    update_hud_weapon_flags: 0,
    hud_utility_update: 0
};
const weaponIndexReturns = {};
const hudWeaponNameReturns = {};
const samples = [];
const sampleKeys = new Set();
const characterSamples = [];
const characterSampleKeys = new Set();
const convertedClientInfos = new Map();
const itemSlotsByName = {};

function readU32(address) {
    try { return address.readU32(); } catch (_) { return null; }
}

function readI32(address) {
    try { return address.readS32(); } catch (_) { return null; }
}

function readU8(address) {
    try { return address.readU8(); } catch (_) { return null; }
}

function readU16(address) {
    try { return address.readU16(); } catch (_) { return null; }
}

function readFloat(address) {
    try {
        const value = address.readFloat();
        return Number.isFinite(value) ? value : null;
    } catch (_) {
        return null;
    }
}

function readPointer(address) {
    try { return address.readPointer(); } catch (_) { return null; }
}

function readCStringPointer(address) {
    const value = readPointer(address);
    if (value === null || value.isNull()) return null;
    try { return value.readCString(); } catch (_) { return null; }
}

function readConfigString(index) {
    if (index === null || index <= 0 || index > 0x3ff) return null;
    try {
        const value = getConfigString(index + 2051);
        return value.isNull() ? null : value.readCString();
    } catch (_) {
        return null;
    }
}

function readRawConfigString(index) {
    if (index < 0 || index >= 0x1B92) return null;
    try {
        const value = getConfigString(index);
        return value.isNull() ? null : value.readCString();
    } catch (_) {
        return null;
    }
}

function readDynamicConfigString(index) {
    if (index < 0 || index >= 0x1B92) return null;
    try {
        const offset = dynamicConfigStringOffsets.add(index * 4).readU32();
        const value = dynamicConfigStringBuffer.add(offset).readCString();
        return value.length === 0 ? null : value;
    } catch (_) {
        return null;
    }
}

function scanWeaponConfigStrings() {
    const result = [];
    for (let weaponIndex = 1; weaponIndex < 900; ++weaponIndex) {
        const value = readRawConfigString(5443 + weaponIndex);
        const dynamicValue = readDynamicConfigString(5443 + weaponIndex);
        if ((value !== null && value.length !== 0) || dynamicValue !== null) {
            result.push({
                weapon_index: weaponIndex,
                config_string_index: 5443 + weaponIndex,
                config_string_type: readU8(configStringTypes.add(5443 + weaponIndex)),
                config_string: value,
                dynamic_config_string: dynamicValue,
                definition: readWeaponDefinition(weaponIndex)
            });
        }
    }
    return result;
}

function readHudState() {
    return {
        cached_weapon_name: readCStringPointer(cachedHudWeaponName),
        weapon_blocked: readU8(hudWeaponBlocked),
        weapon_visible: readU8(hudWeaponVisible),
        weapon_interactive: readU8(hudWeaponInteractive)
    };
}

function scanViewmodelConfigStrings() {
    const result = [];
    for (let index = 1; index <= 0x3ff; ++index) {
        const value = readConfigString(index);
        if (value !== null && value.length !== 0) {
            result.push({ index: index, config_string: value });
        }
    }
    return result;
}

function queryModelCandidates() {
    if (modelCandidates !== null) return;
    modelCandidates = modelCandidatePointers.map((candidate) => {
        let model = null;
        try { model = dbFindXAssetHeader(4, candidate.pointer, false); } catch (_) {}
        return {
            name: candidate.name,
            model: model === null || model.isNull() ? null : readModel(model)
        };
    });
}

function pointerText(value) {
    return value === null ? null : value.toString();
}

function readModel(model) {
    if (model === null || model.isNull()) return null;
    let name = null;
    try {
        const nameAddress = model.readPointer();
        if (!nameAddress.isNull()) name = nameAddress.readCString();
    } catch (_) {}
    return { address: model.toString(), name: name };
}

function readCharacterCustomization(clientNum) {
    if (clientNum === null || clientNum < 0 || clientNum >= 18
        || !convertedClientInfos.has(clientNum)) return null;
    const clientRecord = convertedClientInfos.get(clientNum);
    const selectionIds = clientRecord.add(924);
    return {
        address: clientRecord.toString(),
        client_num: clientNum,
        provisional_marker: readU32(clientRecord.add(908)),
        faction: readU32(clientRecord.add(912)),
        female: readU32(clientRecord.add(916)),
        color: readU32(clientRecord.add(920)),
        selection_ids: Array.from(
            { length: 11 },
            (_, index) => readU16(selectionIds.add(index * 2))
        )
    };
}

function readCharacterModelRecord(modelIndex) {
    if (modelIndex === null || modelIndex <= 0 || modelIndex > 0xffff)
        return { model_index: modelIndex, source_name: null };
    const source = readPointer(characterModelRecords.add((modelIndex - 1) * 16));
    let sourceName = null;
    if (source !== null && !source.isNull()) {
        try { sourceName = source.readCString(); } catch (_) {}
    }
    return {
        model_index: modelIndex,
        source: pointerText(source),
        source_name: sourceName
    };
}

function readTransform(address) {
    return Array.from({ length: 9 }, (_, index) => readFloat(address.add(index * 4)));
}

function readModularModelTable(definition) {
    if (definition === null || definition.isNull()) return null;
    const attachmentCount = readU8(definition.add(0x91));
    const modelCount = readU8(definition.add(0x92));
    if (attachmentCount === null || attachmentCount > 15
        || modelCount === null || modelCount > 16) return null;
    const attachments = [];
    for (let index = 0; index < attachmentCount; ++index) {
        const nameObject = readPointer(definition.add(0xEC8 + index * 4));
        const name = nameObject === null || nameObject.isNull()
            ? null
            : readCStringPointer(nameObject);
        attachments.push({
            index: index,
            name: name,
            slot: name === null || itemSlotsByName[name] === undefined
                ? null
                : itemSlotsByName[name]
        });
    }
    const models = [];
    for (let index = 0; index < modelCount; ++index) {
        models.push({
            index: index,
            tag: readU16(definition.add(0xF48 + index * 2)),
            world_model: readModel(readPointer(definition.add(0xF68 + index * 4))),
            view_model: readModel(readPointer(definition.add(0xFAC + index * 4))),
            transform: readTransform(definition.add(0xFF0 + index * 36))
        });
    }
    return {
        attachment_count: attachmentCount,
        model_count: modelCount,
        attachments: attachments,
        models: models
    };
}

function currentCgame() {
    const clientIndex = readU32(activeLocalClientIndex);
    if (clientIndex === null) return null;
    const encoded = readU32(encodedCgameGlobals.add(clientIndex * 4));
    if (encoded === null) return null;
    return ptr((encoded ^ cgamePointerXor) >>> 0);
}

function currentDobjTable() {
    const index = readU32(encodedDobjTableIndex);
    if (index === null) return null;
    const encoded = readU32(encodedCgameGlobals.add(index * 4));
    if (encoded === null) return null;
    return ptr((encoded ^ dobjTablePointerXor) >>> 0);
}

function readHeldWeapon(ps, weaponIndex) {
    if (ps === null || ps.isNull() || weaponIndex <= 0) return null;
    for (let index = 0; index < 15; ++index) {
        const asset = readU32(ps.add(0x2A4 + index * 4));
        if (asset !== weaponIndex) continue;
        const entry = ps.add(0x2E0 + index * 5);
        const unknownState = [];
        for (let flag = 1; flag < 5; ++flag)
            unknownState.push(readU8(entry.add(flag)));
        return {
            slot: index,
            held_before: readU8(entry),
            unknown_state: unknownState
        };
    }
    return null;
}

function readWeaponDefinition(weaponIndex) {
    if (weaponIndex <= 0 || weaponIndex > 0x3ff) return null;
    const definition = readPointer(weaponVariantTable.add(weaponIndex * 4));
    if (definition === null || definition.isNull()) return null;
    const info = weaponInfoTable.add(weaponIndex * 16);
    const modelKey = readCStringPointer(definition);
    let nativeDefinitionIndex = null;
    if (modelKey !== null && modelKey.startsWith('*')) {
        const modelKeyPointer = readPointer(definition);
        if (modelKeyPointer !== null && !modelKeyPointer.isNull()) {
            try {
                const candidate = getModularDefinitionIndex(modelKeyPointer);
                if (candidate >= 0 && candidate <= 0x3ff)
                    nativeDefinitionIndex = candidate;
            } catch (_) {}
        }
    }
    const nativeDefinition = nativeDefinitionIndex === null
        ? null
        : nativeWeaponDefinitionTable.add(
            (34720 + 1173 * nativeDefinitionIndex) * 4);
    return {
        address: definition.toString(),
        native_definition_index: nativeDefinitionIndex,
        native_definition_address: pointerText(nativeDefinition),
        model_key: modelKey,
        uses_modular_model_table: modelKey !== null && modelKey.startsWith('*'),
        right_gun_model: readModel(readPointer(definition.add(0x10))),
        left_gun_model: readModel(readPointer(definition.add(0x14))),
        model_0x28: readModel(readPointer(definition.add(0x28))),
        // CODREF(bg_update_player_dobj): CG_AttachWeaponWorldModel
        // 0x00445460 reads these exact WeaponDef offsets. Keep offset-derived
        // labels until their CODOL asset members are named independently.
        model_0x2c: readModel(readPointer(definition.add(0x2C))),
        pre_modular_root_model_0x30: readModel(readPointer(definition.add(0x30))),
        model_0x34: readModel(readPointer(definition.add(0x34))),
        weapon_server_field_candidates: {
            damage_block_i32: Array.from(
                { length: 24 },
                (_, index) => readI32(definition.add(0x6C8 + index * 4))),
            range_block_f32: Array.from(
                { length: 32 },
                (_, index) => readFloat(definition.add(0xB80 + index * 4))),
            i32_0x6d8: readI32(definition.add(0x6D8)),
            i32_0x6dc: readI32(definition.add(0x6DC)),
            i32_0x6e0: readI32(definition.add(0x6E0)),
            i32_0x6e4: readI32(definition.add(0x6E4)),
            i32_0x6e8: readI32(definition.add(0x6E8)),
            i32_0x6ec: readI32(definition.add(0x6EC)),
            i32_0x6f0: readI32(definition.add(0x6F0)),
            i32_0xbd0: readI32(definition.add(0xBD0)),
            i32_0xbd4: readI32(definition.add(0xBD4)),
            i32_0xbd8: readI32(definition.add(0xBD8)),
            f32_0xbdc: readFloat(definition.add(0xBDC)),
            f32_0xbe0: readFloat(definition.add(0xBE0))
        },
        definition_flag_0xd81: readU8(definition.add(0xD81)),
        definition_flag_0xd82: readU8(definition.add(0xD82)),
        definition_flag_0xd83: readU8(definition.add(0xD83)),
        cached_models: [
            readModel(readPointer(info.add(4))),
            readModel(readPointer(info.add(8))),
            readModel(readPointer(info.add(12)))
        ],
        modular_model_table: nativeDefinition === null
            ? null
            : readModularModelTable(nativeDefinition)
    };
}

function readPlayerState(ps) {
    if (ps === null || ps.isNull()) return null;
    const weaponFlags = readU32(ps.add(0x348));
    const currentWeapon = readU32(ps.add(0x340));
    const offhandWeapon = readU32(ps.add(0x32C));
    const selectedWeapon = weaponFlags !== null && (weaponFlags & 2) !== 0
        ? offhandWeapon
        : currentWeapon;
    return {
        address: ps.toString(),
        pm_type: readI32(ps.add(4)),
        other_flags: readU32(ps.add(0x10)),
        render_flags_0xf0: readU32(ps.add(0xF0)),
        client_num_0x144: readU32(ps.add(0x144)),
        viewmodel_index_0x148: readU32(ps.add(0x148)),
        viewmodel_config_string: readConfigString(readU32(ps.add(0x148))),
        right_weapon_anim: readU32(ps.add(0x26C)),
        right_weapon_time: readI32(ps.add(0x270)),
        right_weapon_delay: readI32(ps.add(0x274)),
        right_weapon_state: readU32(ps.add(0x27C)),
        current_weapon: currentWeapon,
        offhand_weapon: offhandWeapon,
        weapon_flags: weaponFlags,
        combat_knife_stats_index: readU32(ps.add(0x33C)),
        selected_viewmodel_weapon: selectedWeapon,
        held_weapon: readHeldWeapon(ps, selectedWeapon || 0),
        weapon_definition: readWeaponDefinition(selectedWeapon || 0)
    };
}

function readDobjTable() {
    const table = currentDobjTable();
    if (table === null || table.isNull()) return null;
    const entries = [];
    for (let hand = 0; hand < 2; ++hand) {
        const entry = table.add(hand * 24);
        const dobj = readPointer(entry);
        entries.push({
            hand: hand,
            address: entry.toString(),
            dobj: pointerText(dobj),
            xanim_tree: dobj === null || dobj.isNull()
                ? null
                : pointerText(readPointer(dobj)),
            object_0x04: pointerText(readPointer(entry.add(4))),
            value_0x08: readU32(entry.add(8)),
            value_0x0c: readU32(entry.add(12)),
            value_0x10: readU32(entry.add(16)),
            dirty: readU32(entry.add(20))
        });
    }
    return { address: table.toString(), entries: entries };
}

function captureState() {
    const cgame = currentCgame();
    return {
        cgame: pointerText(cgame),
        unknown_cgame_0xbd74d: cgame === null ? null : readU8(cgame.add(0xBD74D)),
        player_state: readPlayerState(cgame),
        dobj_table: readDobjTable(),
        hud: readHudState(),
        model_candidates: modelCandidates
    };
}

function addSample(kind, value) {
    if (samples.length >= maxSamples) return;
    const key = kind + ':' + JSON.stringify(value);
    if (sampleKeys.has(key)) return;
    sampleKeys.add(key);
    samples.push({ kind: kind, value: value });
}

function addCharacterSample(kind, value) {
    if (characterSamples.length >= maxSamples) return;
    const key = kind + ':' + JSON.stringify(value);
    if (characterSampleKeys.has(key)) return;
    characterSampleKeys.add(key);
    characterSamples.push({ kind: kind, value: value });
}

function inFunction(address, start, size) {
    return address.compare(start) >= 0 && address.compare(start.add(size)) < 0;
}

Interceptor.attach(addresses.get_viewmodel_weapon, {
    onEnter(_) {
        counts.get_viewmodel_weapon += 1;
        this.ps = this.context.eax;
        this.caller = this.returnAddress;
    },
    onLeave(retval) {
        const value = retval.toInt32();
        weaponIndexReturns[value] = (weaponIndexReturns[value] || 0) + 1;
        if (inFunction(this.caller, addresses.add_view_weapon, 0x19E)
            || inFunction(this.caller, addresses.update_view_weapon_anim, 0x2AB)
            || inFunction(this.caller, addresses.add_player_weapon, 0x630)) {
            addSample('viewmodel_weapon', {
                caller: this.caller.toString(),
                result: value,
                player_state: readPlayerState(this.ps)
            });
        }
    }
});

Interceptor.attach(addresses.get_hud_weapon_name, {
    onEnter(_) {
        counts.get_hud_weapon_name += 1;
    },
    onLeave(retval) {
        let name = null;
        if (!retval.isNull()) {
            try { name = retval.readCString(); } catch (_) {}
        }
        const key = name === null ? '<null>' : name;
        hudWeaponNameReturns[key] = (hudWeaponNameReturns[key] || 0) + 1;
    }
});

Interceptor.attach(addresses.update_hud_weapon_flags, {
    onEnter(_) {
        counts.update_hud_weapon_flags += 1;
        this.before = readHudState();
    },
    onLeave(_) {
        addSample('hud_weapon_flags', {
            before: this.before,
            after: readHudState()
        });
    }
});

Interceptor.attach(addresses.hud_utility_update, {
    onEnter(_) {
        counts.hud_utility_update += 1;
    }
});

Interceptor.attach(addresses.update_view_weapon_anim, {
    onEnter(_) {
        counts.update_view_weapon_anim += 1;
        queryModelCandidates();
        if (counts.update_view_weapon_anim <= 2)
            addSample('update_view_weapon_anim', captureState());
    }
});

Interceptor.attach(addresses.update_character_viewmodel, {
    onEnter(_) {
        counts.update_character_viewmodel += 1;
        this.viewmodelContext = readPointer(this.context.esp.add(4));
        this.playerState = readPointer(this.context.esp.add(8));
        this.clientNum = this.playerState === null || this.playerState.isNull()
            ? null
            : readI32(this.playerState.add(0x144));
        addCharacterSample('update_character_viewmodel_enter', {
            viewmodel_context: pointerText(this.viewmodelContext),
            player_state: pointerText(this.playerState),
            customization: readCharacterCustomization(this.clientNum)
        });
    },
    onLeave(_) {
        addCharacterSample('update_character_viewmodel_leave', {
            customization: readCharacterCustomization(this.clientNum),
            dobj_table: readDobjTable()
        });
    }
});

Interceptor.attach(addresses.resolve_character_models, {
    onEnter(_) {
        counts.resolve_character_models += 1;
        this.selectionIds = this.context.ecx;
        this.output = this.context.edi;
        this.input = Array.from(
            { length: 11 },
            (_, index) => readU16(this.selectionIds.add(index * 2))
        );
    },
    onLeave(retval) {
        const count = retval.toInt32();
        if (count > 0) counts.resolve_character_models_nonzero += 1;
        const models = [];
        if (this.output !== null && !this.output.isNull()) {
            for (let index = 0; index < Math.min(Math.max(count, 0), 11); ++index)
                models.push(readCharacterModelRecord(readU16(this.output.add(index * 2))));
        }
        addCharacterSample('resolve_character_models', {
            selection_ids: this.input,
            model_count: count,
            models: models
        });
    }
});

Interceptor.attach(addresses.unpack_character_selection, {
    onEnter(_) {
        counts.unpack_character_selection += 1;
        this.output = readPointer(this.context.esp.add(4));
        this.netState = readPointer(this.context.esp.add(8));
    },
    onLeave(retval) {
        addCharacterSample('unpack_character_selection', {
            result: retval.toInt32(),
            net_state: pointerText(this.netState),
            packed_selection_fields: this.netState === null || this.netState.isNull()
                ? null
                : [
                    readU32(this.netState.add(24)),
                    readU32(this.netState.add(28)),
                    readU32(this.netState.add(32))
                ],
            provisional_marker: this.netState === null || this.netState.isNull()
                ? null : readU32(this.netState.add(292)),
            faction: this.netState === null || this.netState.isNull()
                ? null : readU32(this.netState.add(296)),
            female: this.netState === null || this.netState.isNull()
                ? null : readU32(this.netState.add(300)),
            color: this.netState === null || this.netState.isNull()
                ? null : readU32(this.netState.add(304)),
            selection_ids: this.output === null || this.output.isNull()
                ? null
                : Array.from(
                    { length: 11 },
                    (_, index) => readU16(this.output.add(index * 2))
                )
        });
    }
});

Interceptor.attach(addresses.convert_client_info, {
    onEnter(_) {
        counts.convert_client_info += 1;
        this.netState = this.context.ecx;
        this.output = this.context.esi;
        this.clientNum = this.netState.isNull() ? null : readI32(this.netState);
    },
    onLeave(retval) {
        if (retval.toInt32() === 0 || this.clientNum === null
            || this.clientNum < 0 || this.clientNum >= 18 || this.output.isNull()) return;
        convertedClientInfos.set(this.clientNum, this.output);
        addCharacterSample('convert_client_info', {
            result: retval.toInt32(),
            net_state: this.netState.toString(),
            output: this.output.toString(),
            customization: readCharacterCustomization(this.clientNum)
        });
    }
});

Interceptor.attach(addresses.transform_character_selection, {
    onEnter(_) {
        counts.transform_character_selection += 1;
        this.faction = this.context.eax.toUInt32();
        this.output = readPointer(this.context.esp.add(4));
        this.input = readPointer(this.context.esp.add(8));
        this.female = readI32(this.context.esp.add(12));
        this.color = readI32(this.context.esp.add(16));
        this.inputValues = this.input === null || this.input.isNull()
            ? null
            : Array.from(
                { length: 11 },
                (_, index) => readU16(this.input.add(index * 2))
            );
    },
    onLeave(retval) {
        addCharacterSample('transform_character_selection', {
            result: retval.toInt32(),
            faction: this.faction,
            female: this.female,
            color: this.color,
            input_selection_ids: this.inputValues,
            output_selection_ids: this.output === null || this.output.isNull()
                ? null
                : Array.from(
                    { length: 11 },
                    (_, index) => readU16(this.output.add(index * 2))
                )
        });
    }
});

Interceptor.attach(addresses.resolve_xmodel, {
    onEnter(_) {
        this.fromCharacter = inFunction(
            this.returnAddress,
            addresses.update_character_viewmodel,
            0x232
        );
        if (!this.fromCharacter) return;
        counts.resolve_character_xmodel += 1;
        this.source = readPointer(this.context.esp.add(4));
        this.sourceName = null;
        if (this.source !== null && !this.source.isNull()) {
            try { this.sourceName = this.source.readCString(); } catch (_) {}
        }
    },
    onLeave(retval) {
        if (!this.fromCharacter) return;
        addCharacterSample('resolve_character_xmodel', {
            source: pointerText(this.source),
            source_name: this.sourceName,
            model: readModel(retval)
        });
    }
});

Interceptor.attach(addresses.change_viewmodel_dobj, {
    onEnter(_) {
        counts.change_viewmodel_dobj += 1;
        this.fromCharacter = inFunction(
            this.returnAddress,
            addresses.update_character_viewmodel,
            0x232
        );
        if (this.fromCharacter) {
            counts.change_viewmodel_dobj_from_character += 1;
            const modelCount = readU32(this.context.esp.add(8));
            const modelIndices = readPointer(this.context.esp.add(12));
            const modelPointers = readPointer(this.context.esp.add(16));
            const models = [];
            if (modelCount !== null
                && modelIndices !== null && !modelIndices.isNull()
                && modelPointers !== null && !modelPointers.isNull()) {
                for (let index = 0; index < Math.min(modelCount, 11); ++index) {
                    models.push({
                        model_index: readU32(modelIndices.add(index * 4)),
                        model: readModel(readPointer(modelPointers.add(index * 4)))
                    });
                }
            }
            addCharacterSample('change_viewmodel_dobj_from_character', {
                caller: this.returnAddress.toString(),
                model_count: modelCount,
                models: models
            });
        }
        addSample('change_viewmodel_dobj_enter', captureState());
    },
    onLeave(_) {
        addSample('change_viewmodel_dobj_leave', captureState());
    }
});

Interceptor.attach(addresses.add_view_weapon, {
    onEnter(_) {
        counts.add_view_weapon += 1;
        if (counts.add_view_weapon <= 2)
            addSample('add_view_weapon', captureState());
    }
});

Interceptor.attach(addresses.add_player_weapon, {
    onEnter(_) {
        const ps = readPointer(this.context.esp.add(4));
        if (ps === null || ps.isNull()) return;
        counts.add_player_weapon += 1;
        const drawGun = readI32(this.context.esp.add(8));
        addSample('add_player_weapon', {
            placement: this.context.ecx.toString(),
            centity: this.context.edx.toString(),
            draw_gun: drawGun,
            player_state: readPlayerState(ps),
            dobj_table: readDobjTable()
        });
    }
});

Interceptor.attach(addresses.create_client_dobj, {
    onEnter(_) {
        this.fromViewmodel = inFunction(
            this.returnAddress,
            addresses.change_viewmodel_dobj,
            0xA32
        );
        if (!this.fromViewmodel) return;
        counts.create_client_dobj += 1;
        const modelList = readPointer(this.context.esp.add(4));
        const modelCount = readI32(this.context.esp.add(8));
        const models = [];
        if (modelList !== null && !modelList.isNull() && modelCount !== null) {
            for (let index = 0; index < Math.min(Math.max(modelCount, 0), 16); ++index) {
                const item = modelList.add(index * 44);
                models.push({
                    index: index,
                    model: readModel(readPointer(item)),
                    bone_name: readU32(item.add(4)),
                    value_0x08: readU32(item.add(8))
                });
            }
        }
        this.createSample = { model_count: modelCount, models: models };
    },
    onLeave(retval) {
        if (!this.fromViewmodel) return;
        if (!retval.isNull()) counts.create_client_dobj_nonnull += 1;
        addSample('create_client_dobj', {
            ...this.createSample,
            result: retval.toString()
        });
    }
});

Interceptor.attach(addresses.add_dobj_to_scene, {
    onEnter(_) {
        counts.add_dobj_to_scene += 1;
        this.fromViewmodel = inFunction(
            this.returnAddress,
            addresses.add_player_weapon,
            0x630
        );
        if (!this.fromViewmodel) return;
        counts.add_viewmodel_dobj_to_scene += 1;
        const dobj = readPointer(this.context.esp.add(4));
        if (dobj !== null && !dobj.isNull())
            counts.add_viewmodel_dobj_to_scene_nonnull += 1;
        addSample('add_viewmodel_dobj_to_scene', {
            caller: this.returnAddress.toString(),
            local_client_or_handle: this.context.ecx.toString(),
            placement_or_origin: this.context.edx.toString(),
            dobj: pointerText(dobj),
            pose: pointerText(readPointer(this.context.esp.add(8))),
            render_flags: readU32(this.context.esp.add(12)),
            dobj_table: readDobjTable()
        });
    }
});

Interceptor.attach(addresses.validate_scene_dobj, {
    onEnter(args) {
        this.fromViewmodel = inFunction(
            this.returnAddress,
            addresses.add_dobj_to_scene,
            0x230
        );
        if (!this.fromViewmodel) return;
        counts.validate_viewmodel_scene_dobj += 1;
        this.dobj = args[0];
    },
    onLeave(retval) {
        if (!this.fromViewmodel) return;
        const accepted = retval.toInt32() & 0xff;
        if (accepted !== 0) counts.validate_viewmodel_scene_dobj_accepted += 1;
        addSample('validate_viewmodel_scene_dobj', {
            dobj: this.dobj.toString(),
            accepted: accepted !== 0
        });
    }
});

Interceptor.attach(addresses.find_item_definition_by_name, {
    onEnter(args) {
        this.name = null;
        try { this.name = args[0].readCString(); } catch (_) {}
    },
    onLeave(retval) {
        if (this.name === null || retval.isNull()) return;
        const slot = readU8(retval.add(6));
        if (slot !== null) itemSlotsByName[this.name] = slot;
    }
});

Interceptor.attach(addresses.resolve_base_models, {
    onEnter(args) {
        counts.resolve_base_models += 1;
        this.output = args[0];
    },
    onLeave(retval) {
        if ((retval.toInt32() & 0xff) === 0 || this.output.isNull()) return;
        addSample('resolve_base_models', {
            world_model_name: readCStringPointer(this.output),
            view_model_name: readCStringPointer(this.output.add(4))
        });
    }
});

Interceptor.attach(addresses.resolve_attachment_models, {
    onEnter(args) {
        counts.resolve_attachment_models += 1;
        this.attachmentItemId = args[0].toUInt32();
        this.baseItemId = args[1].toUInt32();
        this.output = args[2];
    },
    onLeave(retval) {
        if ((retval.toInt32() & 0xff) === 0 || this.output.isNull()) return;
        addSample('resolve_attachment_models', {
            attachment_item_id: this.attachmentItemId,
            base_item_id: this.baseItemId,
            world_model_name: readCStringPointer(this.output),
            view_model_name: readCStringPointer(this.output.add(4))
        });
    }
});

Interceptor.attach(addresses.build_modular_model_table, {
    onEnter(args) {
        counts.build_modular_model_table += 1;
        this.definition = args[0];
    },
    onLeave(_) {
        addSample('build_modular_model_table', {
            definition: this.definition.toString(),
            model_key: readCStringPointer(this.definition),
            table: readModularModelTable(this.definition)
        });
    }
});

Interceptor.attach(addresses.is_modular_model_key, {
    onEnter(_) {
        counts.is_modular_model_key += 1;
        this.definition = this.context.eax;
        this.modelKey = readCStringPointer(this.definition);
    },
    onLeave(retval) {
        addSample('is_modular_model_key', {
            definition: this.definition.toString(),
            model_key: this.modelKey,
            result: (retval.toInt32() & 0xff) !== 0
        });
    }
});

Interceptor.attach(addresses.add_modular_models, {
    onEnter(_) {
        counts.add_modular_models += 1;
        this.definition = this.context.eax;
        this.modelList = readPointer(this.context.esp.add(8));
        this.modelCount = readPointer(this.context.esp.add(12));
        this.beforeCount = null;
        if (this.modelCount !== null && !this.modelCount.isNull()) {
            try { this.beforeCount = this.modelCount.readU16(); } catch (_) {}
        }
    },
    onLeave(retval) {
        const succeeded = (retval.toInt32() & 0xff) !== 0;
        if (succeeded) counts.add_modular_models_succeeded += 1;
        let afterCount = null;
        if (this.modelCount !== null && !this.modelCount.isNull()) {
            try { afterCount = this.modelCount.readU16(); } catch (_) {}
        }
        const models = [];
        if (this.modelList !== null && !this.modelList.isNull()
            && this.beforeCount !== null && afterCount !== null) {
            for (let index = this.beforeCount; index < Math.min(afterCount, 32); ++index) {
                const item = this.modelList.add(index * 44);
                models.push({
                    index: index,
                    model: readModel(readPointer(item)),
                    bone_name: readU32(item.add(4)),
                    value_0x08: readU32(item.add(8))
                });
            }
        }
        addSample('add_modular_models', {
            definition: this.definition.toString(),
            model_key: readCStringPointer(this.definition),
            table: readModularModelTable(this.definition),
            result: succeeded,
            model_count_before: this.beforeCount,
            model_count_after: afterCount,
            models: models
        });
    }
});

rpc.exports = {
    snapshot() {
        return {
            pid: Process.id,
            module_base: module.base.toString(),
            addresses: Object.fromEntries(
                Object.entries(addresses).map(([name, address]) => [name, address.toString()])
            ),
            counts: counts,
            weapon_index_returns: weaponIndexReturns,
            hud_weapon_name_returns: hudWeaponNameReturns,
            samples: samples,
            character_samples: characterSamples,
            current_state: captureState(),
            viewmodel_config_strings: scanViewmodelConfigStrings(),
            weapon_count_config_string: readRawConfigString(6800),
            first_dynamic_weapon_config_string_types: Array.from(
                { length: 16 },
                (_, offset) => ({
                    weapon_index: 352 + offset,
                    config_string_type: readU8(configStringTypes.add(5443 + 352 + offset))
                })
            ),
            weapon_config_strings: scanWeaponConfigStrings()
        };
    }
};

send({ event: 'ready', pid: Process.id, module_base: module.base.toString() });
"""
    return (
        template.replace("__MAX_SAMPLES__", str(max_samples))
        .replace(
            "__MODEL_CANDIDATES__",
            json.dumps(model_candidates, ensure_ascii=True),
        )
    )


def diagnose(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload.get("counts")
    counts = counts if isinstance(counts, dict) else {}
    returns = payload.get("weapon_index_returns")
    returns = returns if isinstance(returns, dict) else {}
    hud_returns = payload.get("hud_weapon_name_returns")
    hud_returns = hud_returns if isinstance(hud_returns, dict) else {}
    positive_weapon = any(
        int(value) > 0 and int(count) > 0
        for value, count in returns.items()
    )
    samples = payload.get("samples")
    samples = samples if isinstance(samples, list) else []
    character_samples = payload.get("character_samples")
    character_samples = (
        character_samples if isinstance(character_samples, list) else []
    )
    created_model_names = {
        model.get("model", {}).get("name")
        for sample in samples
        if isinstance(sample, dict) and sample.get("kind") == "create_client_dobj"
        for model in sample.get("value", {}).get("models", [])
        if isinstance(model, dict) and isinstance(model.get("model"), dict)
    }
    placeholder_only = bool(created_model_names) and created_model_names <= {"tag_origin"}
    ac130_names = {
        "killstreak_ac130_mp",
        "ac130_105mm_mp",
        "ac130_40mm_mp",
        "ac130_25mm_mp",
    }
    observed_hud_weapon_names = sorted(
        str(name)
        for name, count in hud_returns.items()
        if int(count) > 0 and name != "<null>"
    )
    resolved_character_model_names = {
        model.get("name")
        for sample in character_samples
        if isinstance(sample, dict)
        and sample.get("kind") == "resolve_character_xmodel"
        for model in [sample.get("value", {}).get("model")]
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    }
    if int(counts.get("add_view_weapon", 0)) <= 0:
        result = "add_view_weapon_not_called"
    elif not positive_weapon:
        result = "viewmodel_weapon_index_not_positive"
    elif int(counts.get("add_player_weapon", 0)) <= 0:
        result = "add_view_weapon_render_gate_blocked"
    elif int(counts.get("add_viewmodel_dobj_to_scene", 0)) <= 0:
        result = "viewmodel_scene_submission_not_reached"
    elif int(counts.get("add_viewmodel_dobj_to_scene_nonnull", 0)) <= 0:
        result = "viewmodel_dobj_missing"
    elif placeholder_only:
        result = "viewmodel_placeholder_only"
    elif (
        int(counts.get("validate_viewmodel_scene_dobj", 0)) > 0
        and int(counts.get("validate_viewmodel_scene_dobj_accepted", 0)) <= 0
    ):
        result = "viewmodel_dobj_rejected_by_scene"
    else:
        result = "viewmodel_submitted_to_scene"
    return {
        "result": result,
        "positive_weapon_index_seen": positive_weapon,
        "dobj_rebuild_seen": int(counts.get("change_viewmodel_dobj", 0)) > 0,
        "dobj_create_seen": int(counts.get("create_client_dobj", 0)) > 0,
        "character_viewmodel_update_seen": int(
            counts.get("update_character_viewmodel", 0)
        ) > 0,
        "character_model_resolver_seen": int(
            counts.get("resolve_character_models", 0)
        ) > 0,
        "character_dobj_rebuild_seen": int(
            counts.get("change_viewmodel_dobj_from_character", 0)
        ) > 0,
        "resolved_character_model_names": sorted(resolved_character_model_names),
        "scene_submission_seen": int(counts.get("add_viewmodel_dobj_to_scene", 0)) > 0,
        "hud_utility_seen": int(counts.get("hud_utility_update", 0)) > 0,
        "observed_hud_weapon_names": observed_hud_weapon_names,
        "ac130_hud_weapon_seen": bool(ac130_names.intersection(observed_hud_weapon_names)),
        "created_model_names": sorted(
            name for name in created_model_names if isinstance(name, str)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--max-samples", type=int, default=64)
    parser.add_argument(
        "--model-candidate",
        action="append",
        dest="model_candidates",
        help="XModel name to query on the viewmodel update thread; repeatable",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args()
    if args.duration < 0:
        parser.error("--duration must be non-negative")
    if args.duration == 0 and args.stop_file is None:
        parser.error("zero --duration requires --stop-file")
    if args.max_samples <= 0:
        parser.error("--max-samples must be positive")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    candidates = tuple(args.model_candidates or DEFAULT_MODEL_CANDIDATES)
    script = session.create_script(build_script(args.max_samples, candidates))
    ready = threading.Event()
    detached = threading.Event()
    messages: list[dict[str, Any]] = []

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "send":
            payload = message.get("payload")
            if isinstance(payload, dict) and payload.get("event") == "ready":
                ready.set()
            if isinstance(payload, dict):
                messages.append(payload)
        else:
            messages.append({"event": "frida_message", "message": message})

    script.on("message", on_message)
    session.on("detached", lambda reason, crash=None: detached.set())
    started = time.monotonic()
    payload: dict[str, Any]
    try:
        script.load()
        if not ready.wait(5.0):
            raise RuntimeError("viewmodel trace did not report ready")
        if args.ready_file is not None:
            args.ready_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.ready_file.with_suffix(args.ready_file.suffix + ".tmp")
            temporary.write_text(
                json.dumps({"ready": True, "pid": pid}) + "\n",
                encoding="utf-8",
            )
            temporary.replace(args.ready_file)
        deadline = time.monotonic() + args.duration if args.duration > 0 else None
        while not detached.is_set():
            if args.stop_file is not None and args.stop_file.is_file():
                break
            if deadline is not None and time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        if detached.is_set():
            raise RuntimeError("client detached during viewmodel trace")
        payload = dict(script.exports_sync.snapshot())
        payload.update(
            ok=True,
            duration_seconds=round(time.monotonic() - started, 3),
            messages=messages,
        )
        payload["diagnosis"] = diagnose(payload)
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass

    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
