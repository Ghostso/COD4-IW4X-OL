#!/usr/bin/env python3
"""Resolve CODOL marketplace item IDs to native weapon values."""

from __future__ import annotations

import argparse
import ctypes
import json
import threading
from ctypes import wintypes

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
COM_FRAME_RVA = 0x19E000
WEAPON_LOOKUP_RVA = 0x2C4D0
WEAPON_RESOLVER_RVA = 0x2C5C0
ATTACHMENT_LOOKUP_RVA = 0x2C740
DB_FIND_XASSET_HEADER_RVA = 0x9E7D0
WEAPON_SLOT_READ_STAGED_RVA = 0x1945B0
CURRENT_CHARACTER_GET_RVA = 0x28A0E0
CURRENT_WEAPON_CLASS_GET_RVA = 0x3051E0
SELECTED_CLASS_INDEX_RVA = 0x74A046C
CHARACTER_CURRENT_ITEMS_COPY_RVA = 0x168860
CHARACTER_ITEM_DEFINITION_TABLE_RVA = 0x29BBA44
CHARACTER_ITEM_DEFINITION_COUNT_RVA = 0x29BBA48
CHARACTER_ITEM_DECODE_KEY_RVA = 0x8D64C0
CHARACTER_NAME_LOOKUP_RVA = 0xC5F0
CHARACTER_NAME_RANGES_RVA = 0x13CD1BC
CHARACTER_CATEGORY_RANGES_RVA = 0x13E02E4
CHARACTER_VARIANT_RECORDS_RVA = 0x13CD290
CHARACTER_NAME_RECORDS_RVA = 0x13DB2A8
CHARACTER_FACTION_BITS_RVA = 0x13E02A8
CHARACTER_FEMALE_BITS_RVA = 0x13E1758
CHARACTER_COLOR_BITS_RVA = 0x13DB294
CHARACTER_MODEL_RECORDS_RVA = 0x13CD29C
CHARACTER_WIRE_LAYOUT_RVA = 0x13CD0C0
CLIENT_INFO_FIELDS_RVA = 0x855B68
ITEM_DEFINITIONS_RVA = 0x29B8AC4
ITEM_DEFINITION_COUNT_RVA = 0x29B8AC8
ITEM_LOOKUP_RVA = 0x29B8ACC
ITEM_LOOKUP_COUNT_RVA = 0x29B8AD0
ITEM_BUCKET_OFFSETS_RVA = 0x29B8AD4
WEAPON_DEFINITIONS_RVA = 0x13F5A40
ITEM_DEFINITION_SIZE = 40
ITEM_DEFINITION_NAME_OFFSET = 12
CHARACTER_ITEM_DEFINITION_SIZE = 40
ASSET_TYPE_STRINGTABLE = 37
WEAPON_ITEMS_TABLE = "mp/coWeapItemsWEA.csv"
WEAPON_TYPE_OFFSET = 1148
WEAPON_FIRE_TYPE_OFFSET = 1164
WEAPON_AMMO_INDEX_OFFSET = 1720
WEAPON_CLIP_INDEX_OFFSET = 1728
WEAPON_MAX_AMMO_OFFSET = 1732
WEAPON_FIRE_DELAY_OFFSET = 1776
WEAPON_DROP_TIME_OFFSET = 1868
WEAPON_RAISE_TIME_OFFSET = 1872
WEAPON_CLIP_SIZE_OFFSET = 3336
WEAPON_FIRE_TIME_OFFSET = 3344
WEAPON_AMMO_COUNT_CLIP_RELATIVE_OFFSET = 3500


def parse_item_id(value: str) -> int:
    item_id = int(value, 0)
    if not 0 < item_id <= 0xFFFF:
        raise argparse.ArgumentTypeError("item ID must be in range 1..65535")
    return item_id


def parse_loadout(value: str) -> int:
    if not value.startswith("custom") or not value[6:].isdigit():
        raise argparse.ArgumentTypeError("loadout must be custom1..custom5")
    class_index = int(value[6:]) - 1
    if not 0 <= class_index < 5:
        raise argparse.ArgumentTypeError("loadout must be custom1..custom5")
    return class_index


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


def find_window_thread(pid: int) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    thread_ids: list[int] = []

    @callback_type
    def visit(hwnd: int, _lparam: int) -> bool:
        owner_pid = wintypes.DWORD()
        thread_id = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if owner_pid.value == pid and user32.IsWindowVisible(hwnd):
            thread_ids.append(int(thread_id))
        return True

    if not user32.EnumWindows(visit, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if not thread_ids:
        raise RuntimeError(f"no visible window found for PID {pid}")
    return thread_ids[0]


def build_script(
    item_ids: list[int],
    window_thread_id: int,
    loadout_index: int | None,
    scan_characters: bool,
    scan_all_loadouts: bool,
) -> str:
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const comFrame = module.base.add({COM_FRAME_RVA});
const weaponLookup = new NativeFunction(
    module.base.add({WEAPON_LOOKUP_RVA}), 'uint32', ['pointer']);
const weaponResolver = new NativeFunction(
    module.base.add({WEAPON_RESOLVER_RVA}),
    'uint32', ['pointer', 'pointer']);
const attachmentLookup = new NativeFunction(
    module.base.add({ATTACHMENT_LOOKUP_RVA}), 'uint32', ['pointer']);
const dbFindXAssetHeader = new NativeFunction(
    module.base.add({DB_FIND_XASSET_HEADER_RVA}),
    'pointer', ['int', 'pointer', 'int']);
const weaponItemsTableName = Memory.allocUtf8String({json.dumps(WEAPON_ITEMS_TABLE)});
const attachmentSlotTables = [
    ['mp/coweapitemsbas.csv', 3],
    ['mp/coweapitemscqc.csv', 13],
    ['mp/coweapitemshbs.csv', 4],
    ['mp/coweapitemsiro.csv', 10],
    ['mp/coweapitemsmuz.csv', 2],
    ['mp/coweapitemsrai.csv', 6],
    ['mp/coweapitemsret.csv', 15],
    ['mp/coweapitemssco.csv', 1],
    ['mp/coweapitemssto.csv', 5],
    ['mp/coweapitems/gri.csv', 7],
    ['mp/coweapitems/bip.csv', 8],
    ['mp/coweapitems/sra.csv', 9],
    ['mp/coweapitems/mag.csv', 11],
    ['mp/coweapitems/cam.csv', 12]
];
const currentCharacterGet = new NativeFunction(
    module.base.add({CURRENT_CHARACTER_GET_RVA}), 'int', []);
const currentWeaponClassGet = new NativeFunction(
    module.base.add({CURRENT_WEAPON_CLASS_GET_RVA}), 'int', []);
const selectedClassIndex = module.base.add({SELECTED_CLASS_INDEX_RVA});
const characterCurrentItemsCopy = new NativeFunction(
    module.base.add({CHARACTER_CURRENT_ITEMS_COPY_RVA}), 'void', ['pointer']);
const itemDefinitionsGlobal = module.base.add({ITEM_DEFINITIONS_RVA});
const itemDefinitionCountGlobal = module.base.add({ITEM_DEFINITION_COUNT_RVA});
const itemLookupGlobal = module.base.add({ITEM_LOOKUP_RVA});
const itemLookupCountGlobal = module.base.add({ITEM_LOOKUP_COUNT_RVA});
const itemBucketOffsets = module.base.add({ITEM_BUCKET_OFFSETS_RVA});
const characterItemDefinitionsGlobal = module.base.add(
    {CHARACTER_ITEM_DEFINITION_TABLE_RVA});
const characterItemDefinitionCountGlobal = module.base.add(
    {CHARACTER_ITEM_DEFINITION_COUNT_RVA});
const characterItemDecodeKey = module.base.add({CHARACTER_ITEM_DECODE_KEY_RVA});
const weaponDefinitions = module.base.add({WEAPON_DEFINITIONS_RVA});
const itemIds = {json.dumps(item_ids)};
const loadoutIndex = {json.dumps(loadout_index)};
const scanCharacters = {json.dumps(scan_characters)};
const scanAllLoadouts = {json.dumps(scan_all_loadouts)};
const windowThreadId = {window_thread_id};
let completed = false;
const loadoutScratch = Memory.alloc(Process.pageSize);
let lastReadStagedCall = null;
let readStagedThunkAddress = null;
let readStagedThunkProtected = false;

const lookupCharacterName = new NativeFunction(
    module.base.add({CHARACTER_NAME_LOOKUP_RVA}),
    'uint32', ['pointer'], 'fastcall');
const characterNameRanges = module.base.add({CHARACTER_NAME_RANGES_RVA});
const characterCategoryRanges = module.base.add({CHARACTER_CATEGORY_RANGES_RVA});
const characterVariantRecords = module.base.add({CHARACTER_VARIANT_RECORDS_RVA});
const characterNameRecords = module.base.add({CHARACTER_NAME_RECORDS_RVA});
const characterFactionBits = module.base.add({CHARACTER_FACTION_BITS_RVA});
const characterFemaleBits = module.base.add({CHARACTER_FEMALE_BITS_RVA});
const characterColorBits = module.base.add({CHARACTER_COLOR_BITS_RVA});
const characterModelRecords = module.base.add({CHARACTER_MODEL_RECORDS_RVA});
const characterWireLayout = module.base.add({CHARACTER_WIRE_LAYOUT_RVA});
const clientInfoFields = module.base.add({CLIENT_INFO_FIELDS_RVA});

function makeReadStagedThunk() {{
    const targetValue = module.base.add({WEAPON_SLOT_READ_STAGED_RVA}).toUInt32();
    const thunk = Memory.alloc(Process.pageSize);
    readStagedThunkAddress = thunk;
    thunk.writeByteArray([
        0x8B, 0x44, 0x24, 0x04,
        0x8B, 0x54, 0x24, 0x08,
        0xFF, 0x74, 0x24, 0x0C,
        0xB9,
        targetValue & 0xFF,
        (targetValue >>> 8) & 0xFF,
        (targetValue >>> 16) & 0xFF,
        (targetValue >>> 24) & 0xFF,
        0xFF, 0xD1,
        0x83, 0xC4, 0x04,
        0xC2, 0x0C, 0x00
    ]);
    readStagedThunkProtected = Memory.protect(thunk, Process.pageSize, 'r-x');
    return new NativeFunction(
        thunk, 'int', ['int', 'pointer', 'pointer'], 'stdcall');
}}

const readStaged = makeReadStagedThunk();
let characterDiagnosticStage = 'idle';
let characterDiagnosticContext = null;
Interceptor.attach(module.base.add({WEAPON_SLOT_READ_STAGED_RVA}), {{
    onEnter(_args) {{
        lastReadStagedCall = {{
            eax: this.context.eax.toString(),
            edx: this.context.edx.toString(),
            stack_base: this.context.esp.add(4).readPointer().toString()
        }};
    }}
}});

function resolveItemDefinition(itemId) {{
    const definitions = itemDefinitionsGlobal.readPointer();
    const definitionCount = itemDefinitionCountGlobal.readU32();
    const lookup = itemLookupGlobal.readPointer();
    const lookupCount = itemLookupCountGlobal.readU32();
    const bucket = Math.floor(itemId / 1000);
    const lookupIndex = itemId % 1000 + itemBucketOffsets.add(bucket * 2).readU16();
    if (definitions.isNull() || lookup.isNull() || lookupIndex >= lookupCount)
        return null;
    const definitionIndex = lookup.add(lookupIndex * 2).readU16();
    if (definitionIndex === 0 || definitionIndex >= definitionCount)
        return null;
    return {{
        pointer: definitions.add(definitionIndex * {ITEM_DEFINITION_SIZE}),
        definition_index: definitionIndex,
        definition_count: definitionCount,
        lookup_index: lookupIndex,
        lookup_count: lookupCount
    }};
}}

function resolveWeapon(itemId) {{
    const definition = resolveItemDefinition(itemId);
    if (definition === null)
        return {{ item_id: itemId, found: false, reason: 'item-definition-not-found' }};
    const namePointer = definition.pointer.add({ITEM_DEFINITION_NAME_OFFSET}).readPointer();
    const name = namePointer.isNull() ? null : namePointer.readCString();
    if (name === null || name.length === 0) {{
        return {{
            item_id: itemId,
            found: false,
            reason: 'item-definition-name-empty',
            definition_index: definition.definition_index
        }};
    }}

    // Avoid sub_42C5C0's asset-registration path. Once lookup-only confirms the
    // weapon is loaded, the canonical resolver returns through the same lookup.
    const lookupIndex = weaponLookup(namePointer);
    if (lookupIndex === 0) {{
        return {{
            item_id: itemId,
            found: true,
            internal_name: name,
            definition_index: definition.definition_index,
            weapon_loaded: false,
            weapon_asset_index: 0
        }};
    }}
    const weaponIndex = weaponResolver(namePointer, ptr(0));
    if (weaponIndex !== lookupIndex)
        throw new Error('weapon lookup/resolver mismatch for ' + name);
    return {{
        item_id: itemId,
        found: true,
        internal_name: name,
        definition_index: definition.definition_index,
        weapon_loaded: true,
        weapon_asset_index: weaponIndex,
        metadata: readWeaponMetadata(weaponIndex)
    }};
}}

function readWeaponMetadata(assetIndex) {{
    const definition = weaponDefinitions.add(assetIndex * Process.pointerSize).readPointer();
    if (definition.isNull())
        throw new Error('weapon definition is null for asset ' + assetIndex);
    const clipSize = definition.add({WEAPON_CLIP_SIZE_OFFSET}).readS32();
    const maxAmmoMultiplier = definition.add({WEAPON_MAX_AMMO_OFFSET}).readS32();
    const clipRelative = definition.add(
        {WEAPON_AMMO_COUNT_CLIP_RELATIVE_OFFSET}).readU8() !== 0;
    return {{
        pointer: definition.toString(),
        weapon_type: definition.add({WEAPON_TYPE_OFFSET}).readS32(),
        fire_type: definition.add({WEAPON_FIRE_TYPE_OFFSET}).readS32(),
        ammo_index: definition.add({WEAPON_AMMO_INDEX_OFFSET}).readS32(),
        clip_index: definition.add({WEAPON_CLIP_INDEX_OFFSET}).readS32(),
        clip_size: clipSize,
        max_ammo_multiplier: maxAmmoMultiplier,
        max_ammo: clipRelative ? maxAmmoMultiplier * clipSize : maxAmmoMultiplier,
        ammo_count_clip_relative: clipRelative,
        fire_delay: definition.add({WEAPON_FIRE_DELAY_OFFSET}).readS32(),
        drop_time: definition.add({WEAPON_DROP_TIME_OFFSET}).readS32(),
        raise_time: definition.add({WEAPON_RAISE_TIME_OFFSET}).readS32(),
        fire_time: definition.add({WEAPON_FIRE_TIME_OFFSET}).readS32()
    }};
}}

function resolveAttachment(itemId) {{
    const definition = resolveItemDefinition(itemId);
    if (definition === null)
        throw new Error('attachment item definition not found for ' + itemId);
    const namePointer = definition.pointer.add({ITEM_DEFINITION_NAME_OFFSET}).readPointer();
    const name = namePointer.isNull() ? null : namePointer.readCString();
    if (name === null || name.length === 0)
        throw new Error('attachment item definition name empty for ' + itemId);
    const assetIndex = attachmentLookup(namePointer);
    if (assetIndex === 0 || assetIndex >= 0x3fff)
        throw new Error('invalid attachment asset index ' + assetIndex + ' for ' + name);
    return {{
        item_id: itemId,
        internal_name: name,
        slot: resolveAttachmentModelSlot(name),
        asset_index: assetIndex
    }};
}}

function resolveAttachmentModelSlot(attachmentName) {{
    let result = null;
    for (const [tableName, slot] of attachmentSlotTables) {{
        const table = dbFindXAssetHeader(
            {ASSET_TYPE_STRINGTABLE}, Memory.allocUtf8String(tableName), 0);
        if (table.isNull()) throw new Error('attachment slot table is not loaded: ' + tableName);
        const columnCount = table.add(4).readS32();
        const rowCount = table.add(8).readS32();
        const values = table.add(12).readPointer();
        if (columnCount <= 0 || columnCount > 256 || rowCount <= 0
            || rowCount > 4096 || values.isNull()) {{
            throw new Error('invalid attachment slot table layout: ' + tableName);
        }}
        let found = false;
        for (let rowIndex = 0; rowIndex < rowCount; ++rowIndex) {{
            const namePointer = values.add(rowIndex * columnCount * 8).readPointer();
            const name = namePointer.isNull() ? '' : namePointer.readCString();
            if (name === attachmentName) {{
                found = true;
                break;
            }}
        }}
        if (!found) continue;
        if (result !== null)
            throw new Error('attachment appears in multiple slot tables: ' + attachmentName);
        result = slot;
    }}
    if (result === null)
        throw new Error('attachment slot is unknown: ' + attachmentName);
    return result;
}}

function resolveDefaultAttachments(weaponName) {{
    const table = dbFindXAssetHeader(
        {ASSET_TYPE_STRINGTABLE}, weaponItemsTableName, 0);
    if (table.isNull()) throw new Error('weapon item StringTable is not loaded');
    const columnCount = table.add(4).readS32();
    const rowCount = table.add(8).readS32();
    const values = table.add(12).readPointer();
    if (columnCount < 40 || columnCount > 256 || rowCount <= 0
        || rowCount > 4096 || values.isNull()) {{
        throw new Error('invalid weapon item StringTable layout');
    }}
    let row = null;
    for (let rowIndex = 0; rowIndex < rowCount; ++rowIndex) {{
        const candidate = values.add(rowIndex * columnCount * 8);
        const namePointer = candidate.readPointer();
        const name = namePointer.isNull() ? '' : namePointer.readCString();
        if (name === weaponName) {{
            row = candidate;
            break;
        }}
    }}
    if (row === null) throw new Error('weapon item row not found for ' + weaponName);
    const slotNames = [
        'wea', 'sco', 'muz', 'bas', 'hbs', 'sto', 'rai', 'gri',
        'bip', 'sra', 'iro', 'mag', 'cam', 'cqc', 'rof', 'ret'
    ];
    const defaults = [];
    for (let triple = 0; triple < 10; ++triple) {{
        const column = 10 + triple * 3;
        const readCell = offset => {{
            const value = row.add((column + offset) * 8).readPointer();
            return value.isNull() ? '' : value.readCString();
        }};
        const slotName = readCell(0);
        const internalName = readCell(1);
        const enabled = readCell(2);
        if (slotName.length === 0 && internalName.length === 0
            && enabled.length === 0) continue;
        if (slotName.length !== 0 && internalName.length === 0
            && enabled.length === 0) continue;
        if (enabled === 'n') continue;
        const slot = slotNames.indexOf(slotName);
        if (enabled !== 'y' || slot <= 0 || internalName.length === 0) {{
            throw new Error('invalid default attachment triple for ' + weaponName);
        }}
        const assetIndex = attachmentLookup(Memory.allocUtf8String(internalName));
        if (assetIndex === 0 || assetIndex >= 0x3fff) {{
            throw new Error(
                'invalid default attachment asset index ' + assetIndex
                + ' for ' + weaponName + ':' + internalName);
        }}
        defaults.push({{
            item_id: null,
            internal_name: internalName,
            slot: slot,
            asset_index: assetIndex,
            source: 'weapon-default'
        }});
    }}
    return defaults;
}}

function resolveModularWeapon(weapon, attachmentItemIds) {{
    if (weapon === null || !weapon.weapon_loaded)
        return null;
    const equippedAttachments = attachmentItemIds
        .filter(itemId => itemId !== 0)
        .map(resolveAttachment);
    const equippedSlots = new Set(equippedAttachments.map(attachment => attachment.slot));
    if (equippedSlots.size !== equippedAttachments.length)
        throw new Error('equipped attachment slots are not unique');
    const defaultAttachments = resolveDefaultAttachments(weapon.internal_name);
    const attachments = defaultAttachments
        .filter(attachment => !equippedSlots.has(attachment.slot))
        .concat(equippedAttachments.map(attachment => ({{
            ...attachment,
            source: 'equipped'
        }})));
    if (attachments.length > 15)
        throw new Error('effective attachment count exceeds 4-bit wire limit');
    const modularName = '** ' + weapon.weapon_asset_index + ' 0 0'
        + attachments.map(attachment => ' ' + attachment.asset_index).join('');
    const modularNamePointer = Memory.allocUtf8String(modularName);
    const assetIndex = weaponResolver(modularNamePointer, ptr(0));
    const lookupIndex = weaponLookup(modularNamePointer);
    if (assetIndex === 0 || assetIndex >= 0x400 || lookupIndex !== assetIndex) {{
        throw new Error(
            'invalid modular weapon result for ' + modularName
            + ': resolver=' + assetIndex + ' lookup=' + lookupIndex);
    }}
    return {{
        config_string: modularName,
        base_weapon_asset_index: weapon.weapon_asset_index,
        default_attachment_assets: defaultAttachments,
        equipped_attachment_assets: equippedAttachments,
        attachment_assets: attachments,
        weapon_asset_index: assetIndex,
        metadata: readWeaponMetadata(assetIndex)
    }};
}}

function readLoadoutWeapon(characterIndex, classIndex, weaponSlot, resolveAssets) {{
    const slotIndex = characterIndex * 10 + classIndex * 2 + weaponSlot;
    const attachments = loadoutScratch;
    const baseItem = loadoutScratch.add(24);
    baseItem.writeU32(0);
    attachments.writeByteArray(new Uint8Array(24));
    try {{
        readStaged(slotIndex, attachments, baseItem);
    }} catch (error) {{
        const scratchRange = Process.findRangeByAddress(loadoutScratch);
        const thunkRange = Process.findRangeByAddress(readStagedThunkAddress);
        throw new Error(
            'ReadStaged failed for slot ' + slotIndex
            + ' scratch=' + loadoutScratch
            + ' base=' + baseItem
            + ' protection=' + (scratchRange === null ? 'unmapped' : scratchRange.protection)
            + ' call=' + JSON.stringify(lastReadStagedCall)
            + ' thunk=' + readStagedThunkAddress
            + ' thunk_protected=' + readStagedThunkProtected
            + ' thunk_protection=' + (thunkRange === null ? 'unmapped' : thunkRange.protection)
            + ': ' + (error.stack || error.message));
    }}
    const baseItemId = baseItem.readU32();
    const attachmentItemIds = [];
    for (let index = 0; index < 6; ++index)
        attachmentItemIds.push(attachments.add(index * 4).readU32());
    const weapon = baseItemId === 0 || !resolveAssets
        ? null
        : resolveWeapon(baseItemId);
    return {{
        slot_index: slotIndex,
        base_item_id: baseItemId,
        attachment_item_ids: attachmentItemIds,
        weapon: weapon,
        modular_weapon: resolveAssets
            ? resolveModularWeapon(weapon, attachmentItemIds)
            : null
    }};
}}

function resolveLoadout() {{
    if (loadoutIndex === null) return null;
    const currentCharacterIndex = currentCharacterGet();
    if (currentCharacterIndex < 0 || currentCharacterIndex >= 12)
        throw new Error('invalid current character index ' + currentCharacterIndex);
    const characterIndexes = scanCharacters
        ? Array.from({{ length: 12 }}, (_, index) => index)
        : [currentCharacterIndex];
    const candidates = [];
    for (const characterIndex of characterIndexes) {{
        const primary = readLoadoutWeapon(characterIndex, loadoutIndex, 0, true);
        const secondary = readLoadoutWeapon(characterIndex, loadoutIndex, 1, true);
        if (primary.base_item_id !== 0 && secondary.base_item_id !== 0) {{
            candidates.push({{
                character_index: characterIndex,
                primary: primary,
                secondary: secondary
            }});
        }}
    }}
    return {{
        name: 'custom' + (loadoutIndex + 1),
        class_index: loadoutIndex,
        current_character_index: currentCharacterIndex,
        candidates: candidates
    }};
}}

function readLoadoutInventory() {{
    if (!scanAllLoadouts) return null;
    const currentCharacterIndex = currentCharacterGet();
    const selectedClass = selectedClassIndex.readS32();
    const currentWeaponClass = currentWeaponClassGet();
    const characters = [];
    let populatedClassCount = 0;
    for (let characterIndex = 0; characterIndex < 12; ++characterIndex) {{
        const classes = [];
        for (let classIndex = 0; classIndex < 5; ++classIndex) {{
            const primary = readLoadoutWeapon(
                characterIndex, classIndex, 0, false);
            const secondary = readLoadoutWeapon(
                characterIndex, classIndex, 1, false);
            const populated = primary.base_item_id !== 0
                || secondary.base_item_id !== 0;
            if (populated) ++populatedClassCount;
            classes.push({{
                class_index: classIndex,
                weapon_class_index: characterIndex * 5 + classIndex,
                populated: populated,
                primary: primary,
                secondary: secondary
            }});
        }}
        characters.push({{
            character_index: characterIndex,
            classes: classes
        }});
    }}
    const expectedWeaponClass = currentCharacterIndex * 5 + selectedClass;
    return {{
        current_character_index: currentCharacterIndex,
        selected_class_index: selectedClass,
        current_weapon_class: currentWeaponClass,
        expected_weapon_class: expectedWeaponClass,
        current_selection_consistent:
            currentCharacterIndex >= 0 && currentCharacterIndex < 12
            && selectedClass >= 0 && selectedClass < 5
            && currentWeaponClass === expectedWeaponClass,
        populated_class_count: populatedClassCount,
        characters: characters
    }};
}}

function readCharacterPresentation() {{
    characterDiagnosticStage = 'current-character';
    const characterIndex = currentCharacterGet();
    if (characterIndex < 0 || characterIndex >= 12)
        throw new Error('invalid current character index ' + characterIndex);
    const records = Memory.alloc(12 * 8);
    records.writeByteArray(new Uint8Array(12 * 8));
    characterDiagnosticStage = 'copy-current-items';
    characterCurrentItemsCopy(records);
    characterDiagnosticStage = 'decode-items';
    if (currentCharacterGet() !== characterIndex || records.readU8() === 0)
        throw new Error('current character changed while reading presentation');

    const decodeKey = characterItemDecodeKey.readU32();
    const recordToName = [11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 9];
    const itemRecords = [];
    const internalNames = Array(11).fill(null);
    for (let recordIndex = 0; recordIndex < 12; ++recordIndex) {{
        const record = records.add(recordIndex * 8);
        const present = record.readU8() !== 0;
        if (!present) {{
            itemRecords.push({{ record_index: recordIndex, present: false }});
            continue;
        }}
        const encoded = record.add(4).readU32();
        const mixed = (encoded ^ decodeKey) >>> 0;
        const itemId = ((mixed << 8) | (mixed >>> 24)) >>> 0;
        if (itemId === 0 || itemId > 0xffff) {{
            throw new Error(
                'invalid character item ID at record ' + recordIndex
                + ': encoded=' + encoded + ' key=' + decodeKey
                + ' decoded=' + itemId);
        }}
        const definition = resolveItemDefinition(itemId);
        if (definition === null)
            throw new Error('invalid character item record ' + recordIndex);
        const namePointer = definition.pointer.add(
            {ITEM_DEFINITION_NAME_OFFSET}).readPointer();
        const internalName = namePointer.isNull() ? '' : namePointer.readCString();
        if (internalName.length === 0)
            throw new Error('empty character item name at record ' + recordIndex);
        const nameIndex = recordToName[recordIndex];
        itemRecords.push({{
            record_index: recordIndex,
            present: true,
            item_id: itemId,
            internal_name: internalName,
            selection_name_index: nameIndex < 11 ? nameIndex : null
        }});
        if (nameIndex < 11) internalNames[nameIndex] = internalName;
    }}
    characterDiagnosticContext = {{ item_records: itemRecords }};

    const baseItem = itemRecords[0];
    const baseDefinition = resolveItemDefinition(baseItem.item_id);
    const characterDefinitionIndex = baseDefinition.pointer.add(2).readU16();
    const characterDefinitions = characterItemDefinitionsGlobal.readPointer();
    const characterDefinitionCount = characterItemDefinitionCountGlobal.readU32();
    if (characterDefinitions.isNull()
        || characterDefinitionIndex >= characterDefinitionCount) {{
        throw new Error('invalid character secondary definition');
    }}
    const characterDefinition = characterDefinitions.add(
        characterDefinitionIndex * {CHARACTER_ITEM_DEFINITION_SIZE});
    const female = characterDefinition.add(2).readU8();
    const definitionColorValue = characterDefinition.add(3).readU8();
    // CODREF(character_customization): BuildLocalModelList
    // 0x00569CFA..0x00569D20 maps definition values to wht/cau/yel/blk;
    // 0x0040C4C0 then maps those names to model selector order wht/yel/blk/cau.
    const colorSelectorByDefinitionValue = [0, 3, 1, 2];
    if (female > 1 || definitionColorValue >= colorSelectorByDefinitionValue.length)
        throw new Error('invalid character presentation metadata');
    const color = colorSelectorByDefinitionValue[definitionColorValue];
    if (currentCharacterGet() !== characterIndex)
        throw new Error('current character presentation did not remain stable');

    const rawSelectionIds = [];
    const rawSelectionDiagnostics = [];
    characterDiagnosticStage = 'resolve-raw-selection';
    for (let index = 0; index < internalNames.length; ++index) {{
        const name = internalNames[index];
        if (name === null) {{
            rawSelectionIds.push(0);
            rawSelectionDiagnostics.push({{
                category_index: index,
                internal_name: null,
                selection_id: 0
            }});
            continue;
        }}
        const namePointer = Memory.allocUtf8String(name);
        const nameIndex = lookupCharacterName(namePointer) & 0xffff;
        const categoryBase = characterNameRanges.add(index * 4).readU16();
        const categoryCount = characterNameRanges.add(index * 4 + 2).readU16();
        const selectionId =
            nameIndex !== 0xffff
                && nameIndex >= categoryBase
                && nameIndex < categoryBase + categoryCount
                ? characterNameRecords.add(nameIndex * 8).readU16()
                : 0;
        rawSelectionIds.push(selectionId);
        rawSelectionDiagnostics.push({{
            category_index: index,
            internal_name: name,
            name_index: nameIndex,
            category_base: categoryBase,
            category_count: categoryCount,
            selection_id: selectionId
        }});
    }}

    const nativeVariants = [];
    for (let faction = 0; faction <= 1; ++faction) {{
        for (let variantFemale = 0; variantFemale <= 1; ++variantFemale) {{
            for (let variantColor = 0; variantColor <= 3; ++variantColor) {{
                characterDiagnosticStage = 'transform-selection-'
                    + faction + '-' + variantFemale + '-' + variantColor;
                const factionBit = characterFactionBits.add(faction * 4).readS32();
                const femaleBit = characterFemaleBits.add(variantFemale * 4).readS32();
                const colorBit = characterColorBits.add(variantColor * 4).readS32();
                const requiredMask = (
                    (0x80000000 >>> (factionBit & 31))
                    | (0x80000000 >>> (femaleBit & 31))
                    | (0x80000000 >>> (colorBit & 31))) >>> 0;
                const selectionIds = [];
                const models = [];
                let transformedCount = 0;
                for (let index = 0; index < rawSelectionIds.length; ++index) {{
                    const rawSelectionId = rawSelectionIds[index];
                    const categoryBase = characterCategoryRanges.add(index * 4).readU16();
                    const categoryCount = characterCategoryRanges.add(index * 4 + 2).readU16();
                    let selectionId = 0;
                    if (rawSelectionId !== 0) {{
                        for (let localIndex = 0; localIndex < categoryCount; ++localIndex) {{
                            const record = characterVariantRecords.add(
                                (categoryBase + localIndex) * 16);
                            if (record.readU16() === rawSelectionId
                                && (record.add(4).readU32() & requiredMask) === requiredMask) {{
                                selectionId = localIndex + 1;
                                ++transformedCount;
                                break;
                            }}
                        }}
                    }}
                    selectionIds.push(selectionId);
                    if (selectionId !== 0) {{
                        const modelIndex = categoryBase + selectionId;
                        const source = characterModelRecords.add(
                            (modelIndex - 1) * 16).readPointer();
                        if (!source.isNull()) {{
                            models.push({{
                                model_index: modelIndex,
                                source_name: source.readCString()
                            }});
                        }}
                    }}
                }}
                nativeVariants.push({{
                    faction: faction,
                    female: variantFemale !== 0,
                    color: variantColor,
                    transformed_count: transformedCount,
                    selection_ids: selectionIds,
                    model_count: models.length,
                    models: models
                }});
            }}
        }}
    }}
    characterDiagnosticStage = 'complete';
    return {{
        character_index: characterIndex,
        base_item_id: baseItem.item_id,
        base_internal_name: baseItem.internal_name,
        item_records: itemRecords,
        female: female !== 0,
        definition_color_value: definitionColorValue,
        color_selector: color,
        raw_selection_ids: rawSelectionIds,
        raw_selection_diagnostics: rawSelectionDiagnostics,
        native_variants: nativeVariants
    }};
}}

function readCharacterPresentationDiagnostic() {{
    try {{
        return {{ available: true, ...readCharacterPresentation() }};
    }} catch (error) {{
        return {{
            available: false,
            character_index: currentCharacterGet(),
            stage: characterDiagnosticStage,
            context: characterDiagnosticContext,
            error: error.message
        }};
    }}
}}

function readCharacterWireLayout() {{
    return Array.from({{ length: 21 }}, (_, index) => {{
        const entry = characterWireLayout.add(index * 12);
        return {{
            index: index,
            state_offset: entry.readU32(),
            bit_count: entry.add(4).readS32(),
            value_8: entry.add(8).readU32()
        }};
    }});
}}

function readClientInfoFields() {{
    return Array.from({{ length: 76 }}, (_, index) => {{
        const field = clientInfoFields.add(index * 12);
        return {{
            index: index,
            state_offset: field.readS32(),
            bit_count: field.add(4).readS32(),
            change_hints: field.add(8).readU32()
        }};
    }});
}}

function drive() {{
    if (completed || Process.getCurrentThreadId() !== windowThreadId) return;
    completed = true;
    try {{
        send({{
            ok: true,
            event: 'completed',
            pid: Process.id,
            source: 'client-native-forced',
            thread_id: Process.getCurrentThreadId(),
            module_base: module.base.toString(),
            character_wire_layout: readCharacterWireLayout(),
            client_info_fields: readClientInfoFields(),
            character_presentation: readCharacterPresentationDiagnostic(),
            loadout: resolveLoadout(),
            loadout_inventory: readLoadoutInventory(),
            results: itemIds.map(resolveWeapon)
        }});
    }} catch (error) {{
        send({{
            ok: false,
            event: 'error',
            source: 'client-native-forced',
            error: error.stack || error.message
        }});
    }}
}}

Interceptor.attach(comFrame, {{ onEnter: drive }});
const user32 = Process.getModuleByName('user32.dll');
for (const name of ['PeekMessageA', 'PeekMessageW', 'DispatchMessageA', 'DispatchMessageW']) {{
    const address = user32.findExportByName(name);
    if (address !== null) Interceptor.attach(address, {{ onEnter: drive }});
}}
send({{
    ok: true,
    event: 'armed',
    pid: Process.id,
    window_thread_id: windowThreadId,
    module_base: module.base.toString()
}});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item_ids", nargs="*", type=parse_item_id)
    parser.add_argument("--loadout", type=parse_loadout, metavar="custom1..custom5")
    parser.add_argument(
        "--scan-characters",
        action="store_true",
        help="inspect all 12 character loadout tables instead of only the current character",
    )
    parser.add_argument(
        "--scan-all-loadouts",
        action="store_true",
        help="read all 12 x 5 staged loadouts without resolving or registering weapon assets",
    )
    parser.add_argument("--pid", type=int)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if not args.item_ids and args.loadout is None and not args.scan_all_loadouts:
        parser.error("provide an item ID, --loadout, or --scan-all-loadouts")
    if args.scan_characters and args.loadout is None:
        parser.error("--scan-characters requires --loadout")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    window_thread_id = find_window_thread(pid)
    session = device.attach(pid)
    done = threading.Event()
    result: dict[str, object] = {}
    script = session.create_script(
        build_script(
            args.item_ids,
            window_thread_id,
            args.loadout,
            args.scan_characters,
            args.scan_all_loadouts,
        )
    )

    def on_message(message: dict, _data: bytes | None) -> None:
        payload = message.get("payload", message)
        if not isinstance(payload, dict):
            return
        if message.get("type") == "error":
            result.update(
                {
                    "ok": False,
                    "event": "error",
                    "source": "frida-script",
                    "error": payload.get("description") or payload.get("stack") or str(payload),
                }
            )
            done.set()
        elif payload.get("event") in {"completed", "error"}:
            result.update(payload)
            done.set()

    script.on("message", on_message)
    try:
        script.load()
        if not done.wait(args.timeout):
            raise TimeoutError("timed out waiting for a CODOL main-thread weapon resolution")
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
