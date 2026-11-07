#!/usr/bin/env python3
"""Probe native CODOL locational point-trace ownership for one server DObj."""

from __future__ import annotations

import argparse
import json
import threading

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"


def build_script(model_name: str, prepare_pose: bool) -> str:
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const frame = module.base.add(0x19E000);
const calcTraceExtents = module.base.add(0x18C200);
const pointTraceToEntities = module.base.add(0x18D790);
const dobjGeomTracelinePartBits = module.base.add(0x2469A0);
const dobjCalcSkel = module.base.add(0x247F70);
const gEntities = module.base.add(0x26B3410);
const serverDObjMap = module.base.add(0x2A8D050);
const serverDObjInUse = module.base.add(0x2A8E050);
const serverDObjPool = module.base.add(0x2A8E850);
const animConditionBaseSlot = module.base.add(0x7417B80);
const animScriptDataSlot = module.base.add(0x7417B84);
const targetModel = {json.dumps(model_name)};
const prepareTargetPose = {str(prepare_pose).lower()};
const entitySize = 0x2C8;
let completed = false;

function modelName(model) {{
    try {{
        if (model.isNull()) return null;
        const name = model.readPointer();
        return name.isNull() ? null : name.readCString();
    }} catch (_) {{
        return null;
    }}
}}

function findTarget() {{
    for (let entityNum = 18; entityNum < 2046; ++entityNum) {{
        const slot = gEntities.add(entityNum * entitySize);
        if (slot.add(0x113).readU8() === 0 || slot.add(0x110).readU8() === 0 ||
            slot.add(4).readU32() !== 6)
            continue;
        const dobjIndex = serverDObjMap.add(entityNum * 2).readU16();
        if (dobjIndex === 0 || serverDObjInUse.add(dobjIndex).readU8() === 0)
            continue;
        const dobj = serverDObjPool.add(dobjIndex * 0xCC);
        if (dobj.add(9).readU8() !== 1) continue;
        const models = dobj.add(0xC0).readPointer();
        if (models.isNull()) continue;
        const name = modelName(models.readPointer());
        if (name === targetModel)
            return {{ entityNum, slot, dobjIndex, name, model: models.readPointer() }};
    }}
    return null;
}}

const thunk = Memory.alloc(Process.pageSize);
const calc = calcTraceExtents.toUInt32();
const point = pointTraceToEntities.toUInt32();
thunk.writeByteArray([
    0x56,                         // push esi
    0x8B, 0x74, 0x24, 0x08,       // mov esi,[esp+8]
    0xB8, calc & 0xFF, (calc >>> 8) & 0xFF,
        (calc >>> 16) & 0xFF, (calc >>> 24) & 0xFF,
    0xFF, 0xD0,                   // call calcTraceExtents
    0x5E,                         // pop esi
    0x8B, 0x4C, 0x24, 0x08,       // mov ecx,[esp+8]
    0x8B, 0x44, 0x24, 0x04,       // mov eax,[esp+4]
    0x50,                         // push eax
    0xB8, point & 0xFF, (point >>> 8) & 0xFF,
        (point >>> 16) & 0xFF, (point >>> 24) & 0xFF,
    0xFF, 0xD0,                   // call pointTraceToEntities
    0x83, 0xC4, 0x04,             // add esp,4
    0xC2, 0x08, 0x00              // ret 8
]);
Memory.protect(thunk, Process.pageSize, 'r-x');
const invoke = new NativeFunction(thunk, 'void', ['pointer', 'pointer'], 'stdcall');

const poseThunk = Memory.alloc(Process.pageSize);
const geom = dobjGeomTracelinePartBits.toUInt32();
const skel = dobjCalcSkel.toUInt32();
poseThunk.writeByteArray([
    0x56,                         // push esi
    0x8B, 0x74, 0x24, 0x0C,       // mov esi,[esp+12] partBits
    0xFF, 0x74, 0x24, 0x08,       // push [esp+8] dobj
    0xB8, geom & 0xFF, (geom >>> 8) & 0xFF,
        (geom >>> 16) & 0xFF, (geom >>> 24) & 0xFF,
    0xFF, 0xD0,                   // call geom parts
    0x83, 0xC4, 0x04,
    0x5E,
    0x8B, 0x4C, 0x24, 0x08,       // mov ecx,[esp+8] partBits
    0xFF, 0x74, 0x24, 0x04,       // push [esp+4] dobj
    0xB8, skel & 0xFF, (skel >>> 8) & 0xFF,
        (skel >>> 16) & 0xFF, (skel >>> 24) & 0xFF,
    0xFF, 0xD0,
    0x83, 0xC4, 0x04,
    0xC2, 0x08, 0x00
]);
Memory.protect(poseThunk, Process.pageSize, 'r-x');
const preparePoseNative = new NativeFunction(
    poseThunk, 'void', ['pointer', 'pointer'], 'stdcall');

function readVec(address) {{
    return [address.readFloat(), address.add(4).readFloat(), address.add(8).readFloat()];
}}

function writeVec(address, values) {{
    address.writeFloat(values[0]);
    address.add(4).writeFloat(values[1]);
    address.add(8).writeFloat(values[2]);
}}

function readModelBounds(model) {{
    const midpoint = readVec(model.add(0x140));
    const halfSize = readVec(model.add(0x14C));
    if (!midpoint.every(Number.isFinite) || !halfSize.every(Number.isFinite) ||
        !halfSize.every(value => value > 0.25 && value < 4096.0) ||
        !midpoint.every(value => Math.abs(value) < 4096.0))
        throw new Error('invalid CODOL XModel bounds');
    return {{ offset: 0x140, midpoint, half_size: halfSize }};
}}

function preparePose(target) {{
    const dobj = serverDObjPool.add(target.dobjIndex * 0xCC);
    const boneCount = dobj.add(10).readU8();
    if (boneCount === 0) throw new Error('target DObj has no bones');
    dobj.add(20).writeByteArray(new Array(136).fill(0));
    const matrices = Memory.alloc((boneCount * 32 + 15) & ~15);
    matrices.writeByteArray(new Array((boneCount * 32 + 15) & ~15).fill(0));
    dobj.add(148).writeU32(0x4F4C0001);
    dobj.add(152).writePointer(matrices);
    const partBits = Memory.alloc(32);
    partBits.writeByteArray(new Array(32).fill(0));
    preparePoseNative(dobj, partBits);
    return {{ bone_count: boneCount, matrices, part_bits: partBits }};
}}

function runTrace(target, bounds, axis) {{
    const boundsMidpoint = bounds.midpoint;
    const boundsHalfSize = bounds.half_size;
    const origin = readVec(target.slot.add(0x148));
    const center = origin.map((value, index) => value + boundsMidpoint[index]);
    const extent = Math.max(boundsHalfSize[axis] * 2.0, 128.0);
    const start = center.slice();
    const end = center.slice();
    start[axis] -= extent;
    end[axis] += extent;

    const ignore = Memory.alloc(12);
    ignore.writeS32(2047);
    ignore.add(4).writeS32(-1);
    ignore.add(8).writeByteArray([1, 1, 1, 0]);
    const priority = Memory.alloc(256);
    priority.writeByteArray([
        1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        3, 3, 3, 3, 3, 3, 3, 0, 201, 3, 3
    ].concat(new Array(234).fill(0)));
    const pointTrace = Memory.alloc(0x58);
    pointTrace.writeByteArray(new Array(0x58).fill(0));
    writeVec(pointTrace.add(0x30), start);
    writeVec(pointTrace.add(0x3C), end);
    pointTrace.add(0x48).writePointer(ignore);
    pointTrace.add(0x4C).writeU32(0x0280E831);
    pointTrace.add(0x50).writeS32(1);
    pointTrace.add(0x54).writePointer(priority);
    const result = Memory.alloc(0x28);
    result.writeByteArray(new Array(0x28).fill(0));
    result.writeFloat(1.0);
    result.add(0x1C).writeU16(2047);
    const previousContext = animConditionBaseSlot.readPointer();
    const serverContext = animScriptDataSlot.readPointer();
    if (serverContext.isNull()) throw new Error('server animation context unavailable');
    animConditionBaseSlot.writePointer(serverContext);
    try {{
        invoke(pointTrace, result);
    }} finally {{
        animConditionBaseSlot.writePointer(previousContext);
    }}
    return {{
        bounds_offset: bounds.offset,
        axis,
        start,
        end,
        fraction: result.readFloat(),
        hit_type: result.add(0x18).readU32(),
        hit_id: result.add(0x1C).readU16(),
        model_index: result.add(0x1E).readU16(),
        part_name: result.add(0x20).readU16(),
        part_group: result.add(0x22).readU16()
    }};
}}

Interceptor.attach(frame, {{
    onEnter() {{
        if (completed) return;
        completed = true;
        try {{
            const target = findTarget();
            if (target === null) {{
                send({{ ok: false, event: 'target_not_found', model: targetModel }});
                return;
            }}
            const bounds = readModelBounds(target.model);
            const pose = prepareTargetPose ? preparePose(target) : {{ bone_count: null }};
            const traces = [0, 1, 2].map(axis => runTrace(target, bounds, axis));
            const hit = traces.find(trace => trace.hit_id === target.entityNum);
            send({{
                ok: hit !== undefined,
                event: 'completed',
                model: target.name,
                entity_num: target.entityNum,
                dobj_index: target.dobjIndex,
                bone_count: pose.bone_count,
                origin: readVec(target.slot.add(0x148)),
                bounds,
                matching_trace: hit || null,
                traces
            }});
        }} catch (error) {{
            send({{ ok: false, event: 'error', error: error.stack || error.message }});
        }}
    }}
}});
send({{ ok: true, event: 'armed', pid: Process.id, model: targetModel }});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--no-prepare-pose", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    device = frida.get_local_device()
    session = device.attach(args.pid)
    script = session.create_script(
        build_script(args.model, prepare_pose=not args.no_prepare_pose)
    )
    done = threading.Event()
    result: dict[str, object] = {}

    def on_message(message: dict[str, object], _data: object) -> None:
        payload = message.get("payload")
        if isinstance(payload, dict):
            print(json.dumps(payload, ensure_ascii=True), flush=True)
            if payload.get("event") != "armed":
                result.update(payload)
                done.set()
        elif message.get("type") == "error":
            result.update({"ok": False, "event": "script_error", "detail": message})
            done.set()

    script.on("message", on_message)
    script.load()
    completed = done.wait(args.timeout)
    script.unload()
    session.detach()
    return 0 if completed and result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
