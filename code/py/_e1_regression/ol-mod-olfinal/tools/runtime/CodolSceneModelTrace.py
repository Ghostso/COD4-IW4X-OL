#!/usr/bin/env python3
"""Trace CODOL client/server DObj models and client scene submission."""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
ADD_WORLD_DOBJ_TO_SCENE_RVA = 0xF5620
ADD_VIEW_DOBJ_TO_SCENE_RVA = 0xF5990
DOBJ_CREATE_RVA = 0x2450B0
DOBJ_CALC_POSE_RVA = 0x513C0
DOBJ_CALC_MODEL_HIERARCHY_RVA = 0x2478F0
DOBJ_CALC_SKEL_MAIN_THREAD_RVA = 0x247EA0
DOBJ_CALC_SKEL_WORKER_THREAD_RVA = 0x247F20
DOBJ_CALC_SKEL_RVA = 0x247F70
DOBJ_CALC_ANIM_RVA = 0x24F850
CLIENT_DOBJ_CREATE_RVA = 0x19E610
CLIENT_DOBJ_MAP_RVA = 0x2AF4858
CLIENT_DOBJ_POOL_RVA = 0x2A8E850
SERVER_DOBJ_MAP_RVA = 0x2A8D050
SERVER_DOBJ_IN_USE_RVA = 0x2A8E050
SERVER_DOBJ_POOL_RVA = 0x2A8E850
BG_UPDATE_PLAYER_DOBJ_RVA = 0xB700
BG_PLAYER_ANIMATION_RVA = 0xB5D0
WORLD_CHARACTER_MODEL_RESOLVE_RVA = 0xC980
WORLD_CHARACTER_MODEL_NAME_TABLE_RVA = 0x13CD298
WORLD_CHARACTER_MODEL_SLOT_BASES_RVA = 0x13E02E4
CHARACTER_MODEL_TABLE_ENTRY_SIZE = 16
NATIVE_LERP_FRAME_SET_KEY_RVA = 0x8E5154
NATIVE_LERP_FRAME_GET_KEY_RVA = 0x8E5158
ENCODED_CLIENT_STATE_RVA = 0x1619510
ACTIVE_CLIENT_ENTITY_STATE_INDEX_RVA = 0x7417BB0
CLIENT_ENTITY_STATE_XOR = 0x2168F672
MSG_READ_DELTA_ENTITY_RVA = 0x1A3670
MSG_READ_DELTA_FIELD_RVA = 0x1A27F0
POSE_ORIGIN_XOR_KEY_RVA = 0x8E5150


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


def build_script(duration_seconds: float, pose_entity: int = 0) -> str:
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const addWorldDObjToScene = module.base.add({ADD_WORLD_DOBJ_TO_SCENE_RVA});
const addViewDObjToScene = module.base.add({ADD_VIEW_DOBJ_TO_SCENE_RVA});
const dobjCreate = module.base.add({DOBJ_CREATE_RVA});
const dobjCalcPose = module.base.add({DOBJ_CALC_POSE_RVA});
const dobjCalcModelHierarchy = module.base.add({DOBJ_CALC_MODEL_HIERARCHY_RVA});
const dobjCalcSkelMainThread = module.base.add({DOBJ_CALC_SKEL_MAIN_THREAD_RVA});
const dobjCalcSkelWorkerThread = module.base.add({DOBJ_CALC_SKEL_WORKER_THREAD_RVA});
const dobjCalcSkel = module.base.add({DOBJ_CALC_SKEL_RVA});
const dobjCalcAnim = module.base.add({DOBJ_CALC_ANIM_RVA});
const clientDObjCreate = module.base.add({CLIENT_DOBJ_CREATE_RVA});
const clientDObjMap = module.base.add({CLIENT_DOBJ_MAP_RVA});
const clientDObjPool = module.base.add({CLIENT_DOBJ_POOL_RVA});
const serverDObjMap = module.base.add({SERVER_DOBJ_MAP_RVA});
const serverDObjInUse = module.base.add({SERVER_DOBJ_IN_USE_RVA});
const serverDObjPool = module.base.add({SERVER_DOBJ_POOL_RVA});
const bgUpdatePlayerDObj = module.base.add({BG_UPDATE_PLAYER_DOBJ_RVA});
const bgPlayerAnimation = module.base.add({BG_PLAYER_ANIMATION_RVA});
const worldCharacterModelResolve = module.base.add({WORLD_CHARACTER_MODEL_RESOLVE_RVA});
const worldCharacterModelNameTable = module.base.add({WORLD_CHARACTER_MODEL_NAME_TABLE_RVA});
const worldCharacterModelSlotBases = module.base.add({WORLD_CHARACTER_MODEL_SLOT_BASES_RVA});
const nativeLerpFrameSetKey = module.base.add({NATIVE_LERP_FRAME_SET_KEY_RVA});
const nativeLerpFrameGetKey = module.base.add({NATIVE_LERP_FRAME_GET_KEY_RVA});
const encodedClientState = module.base.add({ENCODED_CLIENT_STATE_RVA});
const activeClientEntityStateIndex = module.base.add({ACTIVE_CLIENT_ENTITY_STATE_INDEX_RVA});
const msgReadDeltaEntity = module.base.add({MSG_READ_DELTA_ENTITY_RVA});
const msgReadDeltaField = module.base.add({MSG_READ_DELTA_FIELD_RVA});
const poseOriginXorKey = module.base.add({POSE_ORIGIN_XOR_KEY_RVA});
const counts = new Map();
const createCounts = new Map();
const wrapperCounts = new Map();
const entityByDObj = new Map();
const serverEntityByDObj = new Map();
const poseEntity = {pose_entity};
let calls = 0;
let creates = 0;
let wrapperCreates = 0;
let invalidDObjs = 0;
const existingDObjs = [];
const existingServerDObjs = [];
const playerDObjUpdates = [];
const playerAnimationUpdates = [];
const dobjCalcPoseUpdates = [];
const dobjCalcSkelUpdates = [];
const dobjCalcSkelRawSamples = [];
const dobjCalcSkelWrapperUpdates = [];
const dobjCalcAnimUpdates = [];
const dobjCalcHierarchyUpdates = [];
let dobjCalcSkelRawCalls = 0;
let dobjCalcSkelMainThreadCalls = 0;
let dobjCalcSkelWorkerThreadCalls = 0;
let dobjCalcAnimCalls = 0;
let dobjCalcHierarchyCalls = 0;
const worldCharacterModelResolutions = [];
const scriptMoverEntities = [];
const scriptMoverDeltaEntities = [];
const scriptMoverModelFields = [];
const scriptMoverSubmissionStates = new Map();
const submissionEntityByThread = new Map();
const poseOrigins = new Map();

function preferredAddress(address) {{
    if (address.compare(module.base) < 0 ||
        address.compare(module.base.add(module.size)) >= 0)
        return address.toString();
    return ptr('0x400000').add(address.sub(module.base)).toString();
}}

function modelName(model) {{
    try {{
        if (model.isNull()) return null;
        const name = model.readPointer();
        return name.isNull() ? null : name.readCString();
    }} catch (_) {{
        return null;
    }}
}}

function readDObjModels(dobj) {{
    let modelCount;
    try {{ modelCount = dobj.add(9).readU8(); }} catch (_) {{ return null; }}
    if (modelCount === 0 || modelCount > 32) return null;
    let models;
    try {{ models = dobj.add(0xC0).readPointer(); }} catch (_) {{ return null; }}
    if (models.isNull()) return null;
    const names = [];
    for (let index = 0; index < modelCount; ++index) {{
        let model;
        try {{ model = models.add(index * Process.pointerSize).readPointer(); }}
        catch (_) {{ return null; }}
        const name = modelName(model);
        if (name === null) return null;
        names.push(name);
    }}
    return names;
}}

function readDObjPoseSummary(dobj) {{
    const summary = {{}};
    try {{
        const boneCount = dobj.add(10).readU8();
        const epoch = dobj.add(148).readU32();
        const matrices = dobj.add(152).readPointer();
        summary.bone_count = boneCount;
        summary.epoch = epoch;
        summary.matrices = matrices.toString();
        if (boneCount === 0 || boneCount > 255 || matrices.isNull())
            return summary;
        const minimum = [Infinity, Infinity, Infinity];
        const maximum = [-Infinity, -Infinity, -Infinity];
        const samples = [];
        let finiteCount = 0;
        let nonzeroTranslationCount = 0;
        let finiteQuaternionCount = 0;
        let nonzeroQuaternionCount = 0;
        let nonzeroTransWeightCount = 0;
        for (let index = 0; index < boneCount; ++index) {{
            const matrix = matrices.add(index * 32);
            const quaternion = [
                matrix.readFloat(),
                matrix.add(4).readFloat(),
                matrix.add(8).readFloat(),
                matrix.add(12).readFloat()
            ];
            const translation = [
                matrix.add(16).readFloat(),
                matrix.add(20).readFloat(),
                matrix.add(24).readFloat()
            ];
            const transWeight = matrix.add(28).readFloat();
            if (quaternion.every(Number.isFinite)) {{
                finiteQuaternionCount++;
                if (quaternion.some(value => Math.abs(value) > 0.0001))
                    nonzeroQuaternionCount++;
            }}
            if (translation.every(Number.isFinite)) {{
                finiteCount++;
                for (let axis = 0; axis < 3; ++axis) {{
                    minimum[axis] = Math.min(minimum[axis], translation[axis]);
                    maximum[axis] = Math.max(maximum[axis], translation[axis]);
                }}
                if (translation.some(value => Math.abs(value) > 0.0001))
                    nonzeroTranslationCount++;
            }}
            if (Number.isFinite(transWeight) && Math.abs(transWeight) > 0.0001)
                nonzeroTransWeightCount++;
            if (samples.length < 8) samples.push({{
                quaternion: quaternion,
                translation: translation,
                trans_weight: transWeight
            }});
        }}
        summary.finite_quaternion_count = finiteQuaternionCount;
        summary.nonzero_quaternion_count = nonzeroQuaternionCount;
        summary.finite_translation_count = finiteCount;
        summary.nonzero_translation_count = nonzeroTranslationCount;
        summary.nonzero_trans_weight_count = nonzeroTransWeightCount;
        summary.translation_min = finiteCount ? minimum : null;
        summary.translation_max = finiteCount ? maximum : null;
        summary.matrix_samples = samples;
    }} catch (error) {{
        summary.error = error.message;
    }}
    return summary;
}}

function readPartBits(address) {{
    const values = [];
    for (let index = 0; index < 8; ++index)
        values.push(address.add(index * 4).readU32());
    return values;
}}

function readDObjPartBits(dobj) {{
    const result = {{}};
    try {{
        result.bits_0014 = readPartBits(dobj.add(0x14));
        result.bits_0034 = readPartBits(dobj.add(0x34));
        result.bits_0054 = readPartBits(dobj.add(0x54));
        result.bits_0074 = readPartBits(dobj.add(0x74));
    }} catch (error) {{
        result.error = error.message;
    }}
    return result;
}}

function readDObjBindPoseSummary(dobj) {{
    const result = [];
    try {{
        const modelCount = dobj.add(9).readU8();
        const models = dobj.add(0xC0).readPointer();
        for (let modelIndex = 0; modelIndex < modelCount; ++modelIndex) {{
            const model = models.add(modelIndex * Process.pointerSize).readPointer();
            const boneCount = model.add(4).readU8();
            const rootBoneCount = model.add(5).readU8();
            const translations = model.add(0x38).readPointer();
            let finiteCount = 0;
            let nonzeroCount = 0;
            const samples = [];
            if (!translations.isNull() && rootBoneCount <= boneCount) {{
                for (let bone = 0; bone < boneCount - rootBoneCount; ++bone) {{
                    const value = [
                        translations.add(bone * 12).readFloat(),
                        translations.add(bone * 12 + 4).readFloat(),
                        translations.add(bone * 12 + 8).readFloat()
                    ];
                    if (value.every(Number.isFinite)) {{
                        finiteCount++;
                        if (value.some(component => Math.abs(component) > 0.0001))
                            nonzeroCount++;
                    }}
                    if (samples.length < 4) samples.push(value);
                }}
            }}
            result.push({{
                model: modelName(model),
                bone_count: boneCount,
                root_bone_count: rootBoneCount,
                translations: translations.toString(),
                finite_translation_count: finiteCount,
                nonzero_translation_count: nonzeroCount,
                translation_samples: samples
            }});
        }}
    }} catch (error) {{
        result.push({{error: error.message}});
    }}
    return result;
}}

function readDObjCalculationState(dobj, requestedPartBits) {{
    const clientEntity = entityByDObj.get(dobj.toString());
    const serverEntity = serverEntityByDObj.get(dobj.toString());
    return {{
        dobj: dobj.toString(),
        owner_kind: clientEntity === undefined ?
            (serverEntity === undefined ? null : 'server') : 'client',
        owner_entity: clientEntity === undefined ?
            (serverEntity === undefined ? null : serverEntity) : clientEntity,
        scale: dobj.add(0xC8).readFloat(),
        models: readDObjModels(dobj),
        requested_part_bits: requestedPartBits,
        part_bits: readDObjPartBits(dobj),
        pose: readDObjPoseSummary(dobj),
        bind_pose: readDObjBindPoseSummary(dobj)
    }};
}}

function readCStringPointer(pointerAddress) {{
    try {{
        const value = pointerAddress.readPointer();
        return value.isNull() ? null : value.readCString();
    }} catch (_) {{
        return null;
    }}
}}

function readCStringPointerArray(base, count) {{
    const values = [];
    for (let index = 0; index < count; ++index) {{
        values.push(readCStringPointer(base.add(index * Process.pointerSize)));
    }}
    return values;
}}

function worldCharacterModelName(slot, modelId) {{
    if (modelId === 0) return null;
    try {{
        const slotBase = worldCharacterModelSlotBases.add(slot * 4).readU16();
        const absoluteIndex = slotBase + modelId - 1;
        return readCStringPointer(worldCharacterModelNameTable
            .add(absoluteIndex * {CHARACTER_MODEL_TABLE_ENTRY_SIZE}));
    }} catch (_) {{
        return null;
    }}
}}

function readLerpFrameAccessors(characterInfo, frameOffset) {{
    const frame = characterInfo.add(frameOffset);
    const encodedSet = frame.add(0x1c).readU32();
    const encodedGet = frame.add(0x20).readU32();
    const setKey = nativeLerpFrameSetKey.readU32();
    const getKey = nativeLerpFrameGetKey.readU32();
    const setTarget = (encodedSet ^ setKey ^ frame.add(0x20).toUInt32()) >>> 0;
    const getTarget = (encodedGet ^ getKey ^ frame.add(0x1c).toUInt32()) >>> 0;
    return {{
        encoded_set: encodedSet,
        encoded_get: encodedGet,
        set_target: ptr(setTarget).toString(),
        get_target: ptr(getTarget).toString()
    }};
}}

function scanExistingClientDObjs() {{
    for (let entityIndex = 0; entityIndex < 4096; ++entityIndex) {{
        let dobjIndex;
        try {{ dobjIndex = clientDObjMap.add(entityIndex * 2).readU16(); }}
        catch (_) {{ break; }}
        if (dobjIndex === 0 || dobjIndex >= 2048) continue;
        const dobj = clientDObjPool.add(dobjIndex * 0xCC);
        const models = readDObjModels(dobj);
        if (models === null) {{ invalidDObjs++; continue; }}
        entityByDObj.set(dobj.toString(), entityIndex);
        existingDObjs.push({{
            entity_index: entityIndex,
            entity_handle: (entityIndex + 1) & 0xFFFF,
            dobj_index: dobjIndex,
            dobj: dobj.toString(),
            model_count: models.length,
            models: models,
            scale: dobj.add(0xC8).readFloat(),
            pose: readDObjPoseSummary(dobj),
            part_bits: readDObjPartBits(dobj)
        }});
    }}
}}

function scanExistingServerDObjs() {{
    for (let entityIndex = 0; entityIndex < 2046; ++entityIndex) {{
        let dobjIndex;
        let inUse;
        try {{
            dobjIndex = serverDObjMap.add(entityIndex * 2).readU16();
            inUse = dobjIndex < 2048
                ? serverDObjInUse.add(dobjIndex).readU8()
                : 0;
        }} catch (_) {{ break; }}
        if (dobjIndex === 0 || dobjIndex >= 2048 || inUse === 0) continue;
        const dobj = serverDObjPool.add(dobjIndex * 0xCC);
        const models = readDObjModels(dobj);
        if (models === null) {{ invalidDObjs++; continue; }}
        serverEntityByDObj.set(dobj.toString(), entityIndex);
        existingServerDObjs.push({{
            entity_index: entityIndex,
            dobj_index: dobjIndex,
            dobj: dobj.toString(),
            model_count: models.length,
            models: models,
            scale: dobj.add(0xC8).readFloat(),
            pose: readDObjPoseSummary(dobj),
            part_bits: readDObjPartBits(dobj),
            bind_pose: readDObjBindPoseSummary(dobj)
        }});
    }}
}}

function isRequestedPoseEntity(dobj) {{
    const key = dobj.toString();
    return entityByDObj.get(key) === poseEntity ||
        serverEntityByDObj.get(key) === poseEntity;
}}

function readDObjOwner(dobj) {{
    const key = dobj.toString();
    const clientEntity = entityByDObj.get(key);
    const serverEntity = serverEntityByDObj.get(key);
    return {{
        dobj: key,
        owner_kind: clientEntity === undefined ?
            (serverEntity === undefined ? null : 'server') : 'client',
        owner_entity: clientEntity === undefined ?
            (serverEntity === undefined ? null : serverEntity) : clientEntity
    }};
}}

function readHierarchyStage(dobj, model, modelStart, calculationBits) {{
    const result = readDObjOwner(dobj);
    result.model = modelName(model);
    result.model_start_bone = modelStart;
    result.calculation_bits = calculationBits;
    try {{
        result.model_bone_count = model.add(4).readU8();
        result.model_root_bone_count = model.add(5).readU8();
        result.bind_translations = model.add(0x38).readPointer().toString();
        result.pose = readDObjPoseSummary(dobj);
    }} catch (error) {{
        result.error = error.message;
    }}
    return result;
}}

function readPlayerDObjState(entityState, characterInfo, localClientNum) {{
    const state = {{
        local_client_num: localClientNum,
        entity_state: entityState.toString(),
        character_info: characterInfo.toString()
    }};
    try {{
        state.entity_num = entityState.readU32();
        state.entity_unk_0060 = entityState.add(0x60).readU32();
        state.entity_unk_0064 = entityState.add(0x64).readU32();
        state.entity_anim_state_0068 = entityState.add(0x68).readU32();
        state.entity_anim_state_006c = entityState.add(0x6C).readU32();
        state.entity_weapon_asset_index = entityState.add(0xD0).readU16();
        state.entity_presentation_weapon_asset_index =
            entityState.add(0xD2).readU16();
        state.entity_anim_00d4 = entityState.add(0xD4).readU32();
        state.entity_anim_00d8 = entityState.add(0xD8).readU32();
        state.character_world_model = readCStringPointer(
            characterInfo.add(0x18));
        state.character_attachment_models = readCStringPointerArray(
            characterInfo.add(0x20), 10);
        state.character_attachment_tags = readCStringPointerArray(
            characterInfo.add(0x48), 10);
        state.character_dobj_weapon = characterInfo.add(804).readU32();
        state.character_stowed_weapon = characterInfo.add(808).readU32();
        state.character_weapon_model = characterInfo.add(812).readU8();
        state.character_flag_840 = characterInfo.add(840).readU8();
        state.character_flag_841 = characterInfo.add(841).readU8();
        state.character_dobj_dirty = characterInfo.add(560).readU32();
        state.character_anim_01f4 = characterInfo.add(0x1F4).readU32();
        state.character_anim_01f8 = characterInfo.add(0x1F8).readU32();
        state.character_anim_state_01fc = characterInfo.add(0x1FC).readU32();
        state.character_anim_state_0200 = characterInfo.add(0x200).readU32();
        state.character_anim_scratch_0204 = characterInfo.add(0x204).readU32();
        state.character_anim_scratch_0208 = characterInfo.add(0x208).readU32();
        state.character_legs_lerp_accessors =
            readLerpFrameAccessors(characterInfo, 0x160);
        state.character_torso_lerp_accessors =
            readLerpFrameAccessors(characterInfo, 0x1A0);
        const tree = characterInfo.add(0x320).readPointer();
        state.character_anim_tree = tree.toString();
        state.character_anim_tree_word_0004 = tree.isNull()
            ? null
            : tree.add(4).readU32();
        const map = localClientNum === -1 ? serverDObjMap : clientDObjMap;
        const pool = localClientNum === -1 ? serverDObjPool : clientDObjPool;
        const dobjIndex = map.add(state.entity_num * 2).readU16();
        state.dobj_index = dobjIndex;
        if (dobjIndex !== 0 && dobjIndex < 2048) {{
            const dobj = pool.add(dobjIndex * 0xCC);
            state.dobj = dobj.toString();
            state.models = readDObjModels(dobj);
            state.pose = readDObjPoseSummary(dobj);
        }}
    }} catch (error) {{
        state.error = error.message;
    }}
    return state;
}}

Interceptor.attach(bgUpdatePlayerDObj, {{
    onEnter(args) {{
        this.localClientNum = this.context.edx.toInt32();
        this.entityState = args[1];
        this.characterInfo = args[2];
        this.before = readPlayerDObjState(
            this.entityState, this.characterInfo, this.localClientNum);
    }},
    onLeave(retval) {{
        if (playerDObjUpdates.length >= 128) return;
        playerDObjUpdates.push({{
            return_value: retval.toInt32(),
            before: this.before,
            after: readPlayerDObjState(
                this.entityState, this.characterInfo, this.localClientNum)
        }});
    }}
}});

Interceptor.attach(bgPlayerAnimation, {{
    onEnter(args) {{
        this.localClientNum = args[0].toInt32();
        this.entityState = args[1];
        this.characterInfo = this.context.edi;
    }},
    onLeave(_) {{
        if (playerAnimationUpdates.length >= 128) return;
        playerAnimationUpdates.push(readPlayerDObjState(
            this.entityState, this.characterInfo, this.localClientNum));
    }}
}});

Interceptor.attach(dobjCalcPose, {{
    onEnter(args) {{
        this.dobj = args[1];
        this.requestedPartBits = args[2];
        if (dobjCalcPoseUpdates.length < 128 &&
            isRequestedPoseEntity(this.dobj)) {{
            this.before = readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits));
        }}
    }},
    onLeave(_) {{
        if (dobjCalcPoseUpdates.length >= 128 || this.before === undefined)
            return;
        dobjCalcPoseUpdates.push({{
            before: this.before,
            after: readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits))
        }});
    }}
}});

Interceptor.attach(dobjCalcSkel, {{
    onEnter(args) {{
        this.dobj = args[0];
        this.requestedPartBits = this.context.ecx;
        dobjCalcSkelRawCalls++;
        if (dobjCalcSkelRawSamples.length < 16) {{
            const sample = readDObjOwner(this.dobj);
            sample.caller = preferredAddress(this.returnAddress);
            try {{ sample.requested_part_bits = readPartBits(this.requestedPartBits); }}
            catch (error) {{ sample.error = error.message; }}
            dobjCalcSkelRawSamples.push(sample);
        }}
        if (dobjCalcSkelUpdates.length < 128 &&
            isRequestedPoseEntity(this.dobj)) {{
            this.before = readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits));
        }}
    }},
    onLeave(_) {{
        if (dobjCalcSkelUpdates.length >= 128 || this.before === undefined)
            return;
        dobjCalcSkelUpdates.push({{
            caller: preferredAddress(this.returnAddress),
            before: this.before,
            after: readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits))
        }});
    }}
}});

function attachDObjCalcSkelWrapper(address, kind) {{
    Interceptor.attach(address, {{
        onEnter(args) {{
            if (kind === 'main_thread') {{
                dobjCalcSkelMainThreadCalls++;
                this.dobj = args[0];
                this.requestedPartBits = args[1];
            }} else {{
                dobjCalcSkelWorkerThreadCalls++;
                this.dobj = this.context.ecx;
                this.requestedPartBits = args[0];
            }}
            if (dobjCalcSkelWrapperUpdates.length < 64 &&
                isRequestedPoseEntity(this.dobj)) {{
                this.before = readDObjCalculationState(
                    this.dobj, readPartBits(this.requestedPartBits));
            }}
        }},
        onLeave(_) {{
            if (dobjCalcSkelWrapperUpdates.length >= 64 ||
                this.before === undefined)
                return;
            dobjCalcSkelWrapperUpdates.push({{
                kind: kind,
                caller: preferredAddress(this.returnAddress),
                before: this.before,
                after: readDObjCalculationState(
                    this.dobj, readPartBits(this.requestedPartBits))
            }});
        }}
    }});
}}

attachDObjCalcSkelWrapper(dobjCalcSkelMainThread, 'main_thread');
attachDObjCalcSkelWrapper(dobjCalcSkelWorkerThread, 'worker_thread');

Interceptor.attach(dobjCalcAnim, {{
    onEnter(_) {{
        dobjCalcAnimCalls++;
        this.dobj = this.context.edi;
        this.requestedPartBits = this.context.eax;
        this.scratch = this.context.esi;
        if (dobjCalcAnimUpdates.length < 64 &&
            isRequestedPoseEntity(this.dobj)) {{
            this.before = readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits));
        }}
    }},
    onLeave(_) {{
        if (dobjCalcAnimUpdates.length >= 64 || this.before === undefined)
            return;
        dobjCalcAnimUpdates.push({{
            caller: preferredAddress(this.returnAddress),
            scratch: this.scratch.toString(),
            before: this.before,
            after: readDObjCalculationState(
                this.dobj, readPartBits(this.requestedPartBits))
        }});
    }}
}});

Interceptor.attach(dobjCalcModelHierarchy, {{
    onEnter(args) {{
        dobjCalcHierarchyCalls++;
        this.dobj = args[0];
        this.model = args[1];
        this.modelStart = args[3].toInt32();
        this.calculationBits = this.context.eax;
        if (dobjCalcHierarchyUpdates.length < 64 &&
            isRequestedPoseEntity(this.dobj)) {{
            let bits = null;
            try {{ bits = readPartBits(this.calculationBits); }} catch (_) {{}}
            this.before = readHierarchyStage(
                this.dobj, this.model, this.modelStart, bits);
        }}
    }},
    onLeave(_) {{
        if (dobjCalcHierarchyUpdates.length >= 64 ||
            this.before === undefined)
            return;
        let bits = null;
        try {{ bits = readPartBits(this.calculationBits); }} catch (_) {{}}
        dobjCalcHierarchyUpdates.push({{
            caller: preferredAddress(this.returnAddress),
            before: this.before,
            after: readHierarchyStage(
                this.dobj, this.model, this.modelStart, bits)
        }});
    }}
}});

Interceptor.attach(worldCharacterModelResolve, {{
    onEnter(args) {{
        this.faction = this.context.eax.toInt32();
        this.output = args[0];
        this.selectionIds = args[1];
        this.female = args[2].toInt32();
        this.color = args[3].toInt32();
        this.selection = [];
        try {{
            for (let index = 0; index < 11; ++index)
                this.selection.push(this.selectionIds.add(index * 2).readU16());
        }} catch (_) {{
            this.selection = null;
        }}
    }},
    onLeave(retval) {{
        if (worldCharacterModelResolutions.length >= 128) return;
        const count = retval.toInt32();
        const modelIds = [];
        const modelNames = [];
        if (count > 0 && count <= 11) {{
            try {{
                for (let index = 0; index < 11; ++index) {{
                    const modelId = this.output.add(index * 2).readU16();
                    modelIds.push(modelId);
                    modelNames.push(worldCharacterModelName(index, modelId));
                }}
            }} catch (_) {{
                modelIds.length = 0;
                modelNames.length = 0;
            }}
        }}
        worldCharacterModelResolutions.push({{
            faction: this.faction,
            female: this.female,
            color: this.color,
            selection_ids: this.selection,
            model_count: count,
            model_ids: modelIds,
            model_names: modelNames
        }});
    }}
}});

function scanScriptMoverEntities() {{
    let localClient;
    let encoded;
    try {{
        localClient = activeClientEntityStateIndex.readU32();
        if (localClient >= 16) return;
        encoded = encodedClientState.add(localClient * 4).readU32();
    }} catch (_) {{ return; }}
    const entities = ptr((encoded ^ {CLIENT_ENTITY_STATE_XOR}) >>> 0);
    try {{ entities.readU8(); }} catch (_) {{ return; }}
    for (let slot = 0; slot < 2048; ++slot) {{
        const entity = entities.add(slot * 0x238);
        let eType;
        try {{ eType = entity.add(0xF4).readU32(); }} catch (_) {{ break; }}
        if (eType !== 6) continue;
        const dobjIndex = clientDObjMap.add(slot * 2).readU16();
        const dobj = dobjIndex === 0
            ? NULL
            : clientDObjPool.add(dobjIndex * 0xCC);
        scriptMoverEntities.push({{
            slot: slot,
            number: entity.add(0xF0).readU32(),
            e_type: eType,
            e_flags: entity.add(0xF8).readU32(),
            pose_model_or_owner_0xD8: entity.add(0xD8).readU32(),
            pose_flags_0xE4: entity.add(0xE4).readU32(),
            model_index_0x14C: entity.add(0x14C).readU32(),
            attach_entity_0x158: entity.add(0x158).readU32(),
            attach_flags_0x15C: entity.add(0x15C).readU32(),
            render_control_0x160: entity.add(0x160).readU32(),
            dobj_num_bones_0x0A: dobj.isNull() ? null : dobj.add(0x0A).readU8(),
            dobj_flags_0x0B: dobj.isNull() ? null : dobj.add(0x0B).readU8(),
            dobj_scale_0xC8:
                dobj.isNull() ? null : dobj.add(0xC8).readFloat(),
            client_flags_0x204: entity.add(0x204).readU32()
        }});
    }}
}}

function installPoseOriginTrace() {{
    if (scriptMoverEntities.length === 0) return;
    const slot = scriptMoverEntities[0].slot;
    try {{
        const localClient = activeClientEntityStateIndex.readU32();
        const stateEncoded = encodedClientState.add(localClient * 4).readU32();
        const entities = ptr((stateEncoded ^ {CLIENT_ENTITY_STATE_XOR}) >>> 0);
        const entity = entities.add(slot * 0x238);
        const encoded = entity.add(0x1C).readU32();
        const key = poseOriginXorKey.readU32();
        const decoder = ptr((key ^ encoded ^ entity.add(0x18).toUInt32()) >>> 0);
        Interceptor.attach(decoder, {{
            onEnter(args) {{
                this.entity = submissionEntityByThread.get(Process.getCurrentThreadId());
                this.output = args[1];
            }},
            onLeave(_) {{
                if (this.entity === undefined || this.output.isNull()) return;
                try {{
                    poseOrigins.set(this.entity, [
                        this.output.readFloat(),
                        this.output.add(4).readFloat(),
                        this.output.add(8).readFloat()
                    ]);
                }} catch (_) {{ invalidDObjs++; }}
            }}
        }});
    }} catch (_) {{ invalidDObjs++; }}
}}

function traceSceneEntry(address, path, locateDObj) {{
    Interceptor.attach(address, {{
    onEnter(args) {{
        calls++;
        let dobj;
        try {{ dobj = locateDObj.call(this, args); }} catch (_) {{
            invalidDObjs++;
            return;
        }}
        if (dobj.isNull()) {{
            invalidDObjs++;
            return;
        }}
        let modelCount;
        try {{ modelCount = dobj.add(9).readU8(); }} catch (_) {{
            invalidDObjs++;
            return;
        }}
        if (modelCount === 0 || modelCount > 32) {{
            invalidDObjs++;
            return;
        }}
        let models;
        try {{ models = dobj.add(0xC0).readPointer(); }} catch (_) {{
            invalidDObjs++;
            return;
        }}
        if (models.isNull()) {{
            invalidDObjs++;
            return;
        }}
        const caller = path + ':' + preferredAddress(this.returnAddress);
        const entityIndex = entityByDObj.get(dobj.toString());
        if (path === 'world') {{
            try {{
                const entity = this.context.esp.add(4).readPointer();
                const number = entity.add(0xF0).readU32();
                submissionEntityByThread.set(Process.getCurrentThreadId(), number);
                if (!scriptMoverSubmissionStates.has(number)) {{
                    scriptMoverSubmissionStates.set(number, {{
                        entity_index: number,
                        angles: [
                            entity.add(0x30).readFloat(),
                            entity.add(0x34).readFloat(),
                            entity.add(0x38).readFloat()
                        ],
                        attach_entity_0x158: entity.add(0x158).readU32(),
                        attach_flags_0x15C: entity.add(0x15C).readU32(),
                        render_control_0x160: entity.add(0x160).readU32(),
                        dobj_num_bones_0x0A: dobj.add(0x0A).readU8(),
                        dobj_flags_0x0B: dobj.add(0x0B).readU8(),
                        dobj_scale_0xC8: dobj.add(0xC8).readFloat()
                    }});
                }}
            }} catch (_) {{ invalidDObjs++; }}
        }}
        for (let index = 0; index < modelCount; ++index) {{
            let model;
            try {{ model = models.add(index * Process.pointerSize).readPointer(); }}
            catch (_) {{ invalidDObjs++; continue; }}
            const name = modelName(model);
            if (name === null) {{ invalidDObjs++; continue; }}
            const owner = entityIndex === undefined ? 'unknown' : entityIndex.toString();
            const key = name + '\\n' + caller + '\\n' + owner;
            counts.set(key, (counts.get(key) || 0) + 1);
        }}
    }}
    }});
}}

Interceptor.attach(dobjCreate, {{
    onEnter(args) {{
        this.dobj = this.context.edi;
        this.modelCount = args[0].toUInt32();
        this.entityHandle = args[2].toUInt32() & 0xFFFF;
        this.caller = preferredAddress(this.returnAddress);
    }},
    onLeave(_) {{
        creates++;
        if (this.dobj.isNull() || this.modelCount === 0 || this.modelCount > 32) {{
            invalidDObjs++;
            return;
        }}
        let models;
        try {{ models = this.dobj.add(0xC0).readPointer(); }} catch (_) {{
            invalidDObjs++;
            return;
        }}
        if (models.isNull()) {{
            invalidDObjs++;
            return;
        }}
        if (this.entityHandle > 0 && this.entityHandle <= 2046) {{
            const entityIndex = this.entityHandle - 1;
            try {{
                const dobjIndex = serverDObjMap.add(entityIndex * 2).readU16();
                if (dobjIndex > 0 && dobjIndex < 2048 &&
                    serverDObjInUse.add(dobjIndex).readU8() !== 0 &&
                    serverDObjPool.add(dobjIndex * 0xCC).equals(this.dobj)) {{
                    serverEntityByDObj.set(this.dobj.toString(), entityIndex);
                }}
            }} catch (_) {{ invalidDObjs++; }}
        }}
        const names = [];
        for (let index = 0; index < this.modelCount; ++index) {{
            let model;
            try {{ model = models.add(index * Process.pointerSize).readPointer(); }}
            catch (_) {{ invalidDObjs++; continue; }}
            const name = modelName(model);
            if (name === null) {{ invalidDObjs++; continue; }}
            names.push(name);
            const key = name + '\\n' + this.caller;
            createCounts.set(key, (createCounts.get(key) || 0) + 1);
        }}
        if (creates <= 1024) {{
            send({{
                event: 'dobj_created',
                sequence: creates,
                timestamp_ms: Date.now(),
                dobj: this.dobj.toString(),
                entity_handle: this.entityHandle,
                caller: this.caller,
                model_count: this.modelCount,
                models: names
            }});
        }}
    }}
}});

Interceptor.attach(clientDObjCreate, {{
    onEnter(args) {{
        this.entityIndex = this.context.eax.toUInt32();
        this.entityHandle = (this.entityIndex + 1) & 0xFFFF;
        this.modelCount = args[1].toUInt32() & 0xFFFF;
        this.caller = preferredAddress(this.returnAddress);
        this.models = [];
        const modelDescriptors = args[0];
        if (modelDescriptors.isNull() || this.modelCount === 0 || this.modelCount > 32) {{
            invalidDObjs++;
            return;
        }}
        for (let index = 0; index < this.modelCount; ++index) {{
            let model;
            try {{ model = modelDescriptors.add(index * 0x2C).readPointer(); }}
            catch (_) {{ invalidDObjs++; continue; }}
            const name = modelName(model);
            if (name === null) {{ invalidDObjs++; continue; }}
            this.models.push(name);
            const key = name + '\\n' + this.caller;
            wrapperCounts.set(key, (wrapperCounts.get(key) || 0) + 1);
        }}
    }},
    onLeave(result) {{
        wrapperCreates++;
        if (!result.isNull()) entityByDObj.set(result.toString(), this.entityIndex);
        if (wrapperCreates <= 1024) {{
            send({{
                event: 'client_dobj_created',
                sequence: wrapperCreates,
                timestamp_ms: Date.now(),
                dobj: result.toString(),
                entity_index: this.entityIndex,
                entity_handle: this.entityHandle,
                caller: this.caller,
                model_count: this.modelCount,
                models: this.models
            }});
        }}
    }}
}});

Interceptor.attach(msgReadDeltaEntity, {{
    onEnter(args) {{
        this.baseline = args[2];
        this.output = args[3];
        this.entityNumber = args[4].toUInt32();
        this.baselineType = 0xffffffff;
        this.baselineModel = 0xffffffff;
        try {{
            if (!this.baseline.isNull()) {{
                this.baselineType = this.baseline.add(4).readU32();
                this.baselineModel = this.baseline.add(0x5C).readU32();
            }}
        }} catch (_) {{}}
    }},
    onLeave(_) {{
        if (scriptMoverDeltaEntities.length >= 1024 || this.output.isNull()) return;
        try {{
            const outputType = this.output.add(4).readU32();
            if (outputType !== 6 && this.baselineType !== 6) return;
            scriptMoverDeltaEntities.push({{
                entity_number: this.entityNumber,
                baseline_type: this.baselineType,
                baseline_model_index: this.baselineModel,
                output_type: outputType,
                output_model_index: this.output.add(0x5C).readU32(),
                output_origin: [
                    this.output.add(0x18).readFloat(),
                    this.output.add(0x1C).readFloat(),
                    this.output.add(0x20).readFloat()
                ]
            }});
        }} catch (_) {{}}
    }}
}});

Interceptor.attach(msgReadDeltaField, {{
    onEnter(args) {{
        this.descriptor = this.context.ecx;
        this.output = this.context.edx;
        this.capture = false;
        try {{
            this.offset = this.descriptor.readU32();
            this.bits = this.descriptor.add(4).readS32();
            if (this.offset !== 0x5C || this.bits !== 10 ||
                scriptMoverModelFields.length >= 1024) return;
            this.capture = true;
            this.before = this.output.add(this.offset).readU32();
        }} catch (_) {{}}
    }},
    onLeave(_) {{
        if (!this.capture) return;
        try {{
            scriptMoverModelFields.push({{
                before: this.before,
                after: this.output.add(this.offset).readU32(),
                descriptor: preferredAddress(this.descriptor),
                caller: preferredAddress(this.returnAddress)
            }});
        }} catch (_) {{}}
    }}
}});

traceSceneEntry(addWorldDObjToScene, 'world', function (_) {{
    return this.context.edx;
}});
traceSceneEntry(addViewDObjToScene, 'view', function (_) {{
    return this.context.esp.add(4).readPointer();
}});

scanExistingClientDObjs();
scanExistingServerDObjs();
scanScriptMoverEntities();
installPoseOriginTrace();

send({{
    event: 'armed',
    pid: Process.id,
    module_base: module.base.toString(),
    dobj_create: dobjCreate.toString(),
    client_dobj_create: clientDObjCreate.toString(),
    existing_client_dobj_count: existingDObjs.length,
    script_mover_entity_count: scriptMoverEntities.length,
    pose_entity: poseEntity,
    add_world_dobj_to_scene: addWorldDObjToScene.toString(),
    add_view_dobj_to_scene: addViewDObjToScene.toString()
}});

setTimeout(function () {{
    const models = Array.from(counts.entries()).map(([key, count]) => {{
        const parts = key.split('\\n');
        return {{
            name: parts[0],
            caller: parts[1],
            entity_index: parts[2] === 'unknown' ? null : Number(parts[2]),
            count: count
        }};
    }}).sort((left, right) => right.count - left.count ||
        left.name.localeCompare(right.name));
    const createdModels = Array.from(createCounts.entries()).map(([key, count]) => {{
        const separator = key.lastIndexOf('\\n');
        return {{
            name: key.substring(0, separator),
            caller: key.substring(separator + 1),
            count: count
        }};
    }}).sort((left, right) => right.count - left.count ||
        left.name.localeCompare(right.name));
    const wrapperModels = Array.from(wrapperCounts.entries()).map(([key, count]) => {{
        const separator = key.lastIndexOf('\\n');
        return {{
            name: key.substring(0, separator),
            caller: key.substring(separator + 1),
            count: count
        }};
    }}).sort((left, right) => right.count - left.count ||
        left.name.localeCompare(right.name));
    send({{
        event: 'completed',
        calls: calls,
        creates: creates,
        wrapper_creates: wrapperCreates,
        existing_dobjs: existingDObjs,
        existing_server_dobjs: existingServerDObjs,
        player_dobj_updates: playerDObjUpdates,
        player_animation_updates: playerAnimationUpdates,
        dobj_calc_pose_updates: dobjCalcPoseUpdates,
        dobj_calc_skel_updates: dobjCalcSkelUpdates,
        dobj_calc_skel_raw_calls: dobjCalcSkelRawCalls,
        dobj_calc_skel_raw_samples: dobjCalcSkelRawSamples,
        dobj_calc_skel_main_thread_calls: dobjCalcSkelMainThreadCalls,
        dobj_calc_skel_worker_thread_calls: dobjCalcSkelWorkerThreadCalls,
        dobj_calc_skel_wrapper_updates: dobjCalcSkelWrapperUpdates,
        dobj_calc_anim_calls: dobjCalcAnimCalls,
        dobj_calc_anim_updates: dobjCalcAnimUpdates,
        dobj_calc_hierarchy_calls: dobjCalcHierarchyCalls,
        dobj_calc_hierarchy_updates: dobjCalcHierarchyUpdates,
        world_character_model_resolutions: worldCharacterModelResolutions,
        script_mover_entities: scriptMoverEntities,
        script_mover_delta_entities: scriptMoverDeltaEntities,
        script_mover_model_fields: scriptMoverModelFields,
        script_mover_submission_states: Array.from(
            scriptMoverSubmissionStates.values()).map(state => ({{
                ...state,
                pose_origin: poseOrigins.get(state.entity_index) || null
            }})),
        invalid_dobjs: invalidDObjs,
        models: models,
        created_models: createdModels,
        wrapper_models: wrapperModels
    }});
}}, {duration_seconds * 1000.0});
"""


def build_summary(result: dict[str, object]) -> dict[str, object]:
    models = result.get("models")
    existing_dobjs = result.get("existing_dobjs")
    existing_server_dobjs = result.get("existing_server_dobjs")
    player_dobj_updates = result.get("player_dobj_updates")
    player_animation_updates = result.get("player_animation_updates")
    dobj_calc_pose_updates = result.get("dobj_calc_pose_updates")
    dobj_calc_skel_updates = result.get("dobj_calc_skel_updates")
    dobj_calc_skel_wrapper_updates = result.get("dobj_calc_skel_wrapper_updates")
    dobj_calc_anim_updates = result.get("dobj_calc_anim_updates")
    dobj_calc_hierarchy_updates = result.get("dobj_calc_hierarchy_updates")
    world_character_model_resolutions = result.get("world_character_model_resolutions")
    script_movers = result.get("script_mover_entities")
    return {
        "pid": result.get("pid"),
        "ok": bool(result.get("ok")),
        "calls": result.get("calls", 0),
        "creates": result.get("creates", 0),
        "wrapper_creates": result.get("wrapper_creates", 0),
        "existing_dobjs": len(existing_dobjs) if isinstance(existing_dobjs, list) else 0,
        "existing_server_dobjs": (
            len(existing_server_dobjs)
            if isinstance(existing_server_dobjs, list)
            else 0
        ),
        "player_dobj_updates": (
            len(player_dobj_updates)
            if isinstance(player_dobj_updates, list)
            else 0
        ),
        "player_animation_updates": (
            len(player_animation_updates)
            if isinstance(player_animation_updates, list)
            else 0
        ),
        "dobj_calc_pose_updates": (
            len(dobj_calc_pose_updates)
            if isinstance(dobj_calc_pose_updates, list)
            else 0
        ),
        "dobj_calc_skel_updates": (
            len(dobj_calc_skel_updates)
            if isinstance(dobj_calc_skel_updates, list)
            else 0
        ),
        "dobj_calc_skel_raw_calls": result.get("dobj_calc_skel_raw_calls", 0),
        "dobj_calc_skel_main_thread_calls": result.get(
            "dobj_calc_skel_main_thread_calls", 0
        ),
        "dobj_calc_skel_worker_thread_calls": result.get(
            "dobj_calc_skel_worker_thread_calls", 0
        ),
        "dobj_calc_skel_wrapper_updates": (
            len(dobj_calc_skel_wrapper_updates)
            if isinstance(dobj_calc_skel_wrapper_updates, list)
            else 0
        ),
        "dobj_calc_anim_calls": result.get("dobj_calc_anim_calls", 0),
        "dobj_calc_anim_updates": (
            len(dobj_calc_anim_updates)
            if isinstance(dobj_calc_anim_updates, list)
            else 0
        ),
        "dobj_calc_hierarchy_calls": result.get("dobj_calc_hierarchy_calls", 0),
        "dobj_calc_hierarchy_updates": (
            len(dobj_calc_hierarchy_updates)
            if isinstance(dobj_calc_hierarchy_updates, list)
            else 0
        ),
        "world_character_model_resolutions": (
            len(world_character_model_resolutions)
            if isinstance(world_character_model_resolutions, list)
            else 0
        ),
        "script_movers": len(script_movers) if isinstance(script_movers, list) else 0,
        "unique_models": len(models) if isinstance(models, list) else 0,
        "invalid_dobjs": result.get("invalid_dobjs", 0),
        **({"error": result["error"]} if "error" in result else {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--pose-entity", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.duration <= 0 or args.duration > 60:
        parser.error("--duration must be in (0, 60]")
    if args.pose_entity < 0 or args.pose_entity >= 2046:
        parser.error("--pose-entity must be in [0, 2046)")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    done = threading.Event()
    result: dict[str, object] = {"pid": pid, "ok": False}
    create_events: list[dict[str, object]] = []
    wrapper_events: list[dict[str, object]] = []
    script = session.create_script(build_script(args.duration, args.pose_entity))

    def on_message(message: dict, _data: bytes | None) -> None:
        if message.get("type") == "error":
            result["error"] = message.get("description", "Frida script error")
            done.set()
            return
        payload = message.get("payload", message)
        if not isinstance(payload, dict):
            return
        if payload.get("event") == "armed":
            result["armed"] = payload
        elif payload.get("event") == "dobj_created":
            create_events.append(payload)
        elif payload.get("event") == "client_dobj_created":
            wrapper_events.append(payload)
        elif payload.get("event") == "completed":
            result.update(payload, ok=True)
            result["create_events"] = create_events
            result["wrapper_events"] = wrapper_events
            done.set()

    script.on("message", on_message)
    script.load()
    if not done.wait(args.duration + 5.0):
        result["error"] = "capture timed out"
    script.unload()
    session.detach()

    rendered = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if args.output is None:
        print(rendered, end="")
    else:
        print(json.dumps(build_summary(result), ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
