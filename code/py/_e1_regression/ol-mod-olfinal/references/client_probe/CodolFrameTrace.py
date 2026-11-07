#!/usr/bin/env python3
"""Measure CODOL rendering and snapshot cadence with low-overhead hooks."""

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


def build_script() -> str:
    return r"""
'use strict';

const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
// Names remain intentionally descriptive until their exact symbols are recovered.
const heavyPeriodicTick = module.base.add(0x124890);
const preSnapshotStage = module.base.add(0x51E60);
const frameDispatch = module.base.add(0x704C0);
const frameBody = module.base.add(0x703D0);
const frameDispatchLock = module.base.add(0x7417BDC);
const frameDispatchGateA = module.base.add(0x743F7BC);
const frameDispatchGateB = module.base.add(0x162E848);
const frameDispatchGateC = module.base.add(0x74B0A44);
const frameDispatchGateD = module.base.add(0x2A8CFBC);
const maxFpsDvarSlot = module.base.add(0x2A8CFE8);
const secondaryFpsDvarSlot = module.base.add(0x2A8CFAC);
const frameTimescale = module.base.add(0x8DCD3C);
const globalTimescale = module.base.add(0x2A8A974);
const fixedTimeDvarSlot = module.base.add(0x2A8A98C);
const timescaleDvarASlot = module.base.add(0x2A8A998);
const timescaleDvarBSlot = module.base.add(0x2A8CFC0);
const cgameStageAddresses = {
    process_snapshots: module.base.add(0x1249D2),
    add_packet_entities: module.base.add(0x128C83),
    player_state: module.base.add(0x12B250),
    view_anim: module.base.add(0x12D74F),
    view_values: module.base.add(0x12D76D)
};
const viewValuesComplete = module.base.add(0x12E1B7);
const activeLocalClientIndex = module.base.add(0x7417BA8);
const encodedCgameGlobals = module.base.add(0x1619510);
const cgamePointerXor = 0xFBB2C97A;
const postSnapshotGate = module.base.add(0x12639E);
const serverLoadingMap = module.base.add(0x13CD282);
const getForegroundWindow = new NativeFunction(
    Module.getGlobalExportByName('GetForegroundWindow'),
    'pointer',
    []
);
const getWindowThreadProcessId = new NativeFunction(
    Module.getGlobalExportByName('GetWindowThreadProcessId'),
    'uint32',
    ['pointer', 'pointer']
);

let devicePresents = 0;
let swapChainPresents = 0;
let endScenes = 0;
let heavyPeriodicTicks = 0;
let heavyPeriodicTotalMs = 0;
let heavyPeriodicMaxMs = 0;
let heavyPeriodicReturns = { zero: 0, nonzero: 0 };
let preSnapshotStages = 0;
let frameDispatches = 0;
let frameBodies = 0;
let frameDispatchCallers = {};
let cgameStages = {};
let postSnapshotGates = {};
let postSnapshotGateState = null;
let viewStateSamples = 0;
let viewStateTransitions = 0;
let viewState = null;
let previousViewStateKey = null;
let previousCameraPose = null;
let twoFramesAgoCameraPose = null;
let anomalousCameraTransitions = 0;
let previous = Date.now();
let previousRefdefDelta = null;
let previousRefdefStep = null;
let previousRefdefAngles = null;
let previousRefdefAngleStep = null;
let previousNextSnapshotTime = null;

function emptyCameraDiagnostics() {
    return {
        samples: 0,
        playing_samples: 0,
        alternating_frames: 0,
        angle_alternating_frames: 0,
        origin_alternating_frames: 0,
        large_angle_steps: 0,
        max_origin_step: 0,
        max_angle_step: 0,
        max_axis_length_error: 0,
        max_axis_dot: 0,
        min_abs_axis_determinant: 1,
        playing_height_sum: 0,
        min_playing_height: null,
        max_playing_height: null,
        tilted_samples: 0
    };
}

let cameraDiagnostics = emptyCameraDiagnostics();

function emptyPredictionDiagnostics() {
    return {
        samples: 0,
        snapshot_advances: 0,
        snapshot_time_regressions: 0,
        discontinuities: 0,
        snapshot_gap_min_ms: null,
        snapshot_gap_max_ms: null,
        predicted_to_snap_sum: 0,
        predicted_to_snap_max: 0,
        predicted_to_next_sum: 0,
        predicted_to_next_max: 0,
        snap_to_next_sum: 0,
        snap_to_next_max: 0,
        predicted_to_snap_angle_sum: 0,
        predicted_to_snap_angle_max: 0,
        predicted_to_next_angle_sum: 0,
        predicted_to_next_angle_max: 0,
        snap_to_next_angle_sum: 0,
        snap_to_next_angle_max: 0,
        snapshot_frame_steps: 0,
        snapshot_frame_step_sum: 0,
        snapshot_frame_step_max: 0,
        other_frame_steps: 0,
        other_frame_step_sum: 0,
        other_frame_step_max: 0,
        snapshot_frame_accelerations: 0,
        snapshot_frame_acceleration_sum: 0,
        snapshot_frame_acceleration_max: 0,
        other_frame_accelerations: 0,
        other_frame_acceleration_sum: 0,
        other_frame_acceleration_max: 0,
        snapshot_frame_angle_steps: 0,
        snapshot_frame_angle_step_sum: 0,
        snapshot_frame_angle_step_max: 0,
        other_frame_angle_steps: 0,
        other_frame_angle_step_sum: 0,
        other_frame_angle_step_max: 0,
        snapshot_frame_angle_accelerations: 0,
        snapshot_frame_angle_acceleration_sum: 0,
        snapshot_frame_angle_acceleration_max: 0,
        other_frame_angle_accelerations: 0,
        other_frame_angle_acceleration_sum: 0,
        other_frame_angle_acceleration_max: 0,
        snapshot_direction_reversals: 0,
        other_direction_reversals: 0
    };
}

let predictionDiagnostics = emptyPredictionDiagnostics();

Interceptor.attach(heavyPeriodicTick, {
    onEnter(_) {
        heavyPeriodicTicks += 1;
        this.startedAt = Date.now();
    },
    onLeave(retval) {
        const elapsed = Date.now() - this.startedAt;
        heavyPeriodicTotalMs += elapsed;
        heavyPeriodicMaxMs = Math.max(heavyPeriodicMaxMs, elapsed);
        if (retval.toInt32() === 0) heavyPeriodicReturns.zero += 1;
        else heavyPeriodicReturns.nonzero += 1;
    }
});

for (const [name, address] of Object.entries(cgameStageAddresses)) {
    cgameStages[name] = 0;
    Interceptor.attach(address, {
        onEnter(_) { cgameStages[name] += 1; }
    });
}

Interceptor.attach(postSnapshotGate, {
    onEnter(_) {
        const cgameGlob = this.context.esi;
        const renderScreen = readU32(cgameGlob.add(0x356C));
        const renderFallback = readU32(cgameGlob.add(0xC6FE8));
        let nextSnap = ptr(0);
        let snapFlags = null;
        try {
            nextSnap = cgameGlob.add(0x357C).readPointer();
            if (!nextSnap.isNull()) snapFlags = nextSnap.add(0x3524).readU32();
        } catch (_) {}
        const loadingMap = readU8(serverLoadingMap);
        let reason = 'passed';
        if (renderScreen === 0 && renderFallback === 0) reason = 'render_screen';
        else if (nextSnap.isNull()) reason = 'no_next_snapshot';
        else if (snapFlags !== null && (snapFlags & 0xA) !== 0) reason = 'snapshot_flags';
        else if (loadingMap !== 0) reason = 'server_loading_map';
        postSnapshotGates[reason] = (postSnapshotGates[reason] || 0) + 1;
        postSnapshotGateState = {
            cgame_glob: cgameGlob.toString(),
            render_screen: renderScreen,
            render_fallback: renderFallback,
            next_snapshot: nextSnap.toString(),
            snapshot_flags: snapFlags,
            server_loading_map: loadingMap,
            reason: reason
        };
    }
});

Interceptor.attach(preSnapshotStage, {
    onEnter(_) { preSnapshotStages += 1; }
});

Interceptor.attach(frameDispatch, {
    onEnter(_) {
        frameDispatches += 1;
        const caller = this.returnAddress.sub(module.base).toString();
        frameDispatchCallers[caller] = (frameDispatchCallers[caller] || 0) + 1;
    }
});

Interceptor.attach(frameBody, {
    onEnter(_) { frameBodies += 1; }
});

function readU32(address) {
    try { return address.readU32(); } catch (_) { return null; }
}

function readU8(address) {
    try { return address.readU8(); } catch (_) { return null; }
}

function readFloat(address) {
    try { return address.readFloat(); } catch (_) { return null; }
}

function readI32(address) {
    try { return address.readS32(); } catch (_) { return null; }
}

function readPointer(address) {
    try { return address.readPointer(); } catch (_) { return null; }
}

function readVec3(address) {
    return [readFloat(address), readFloat(address.add(4)), readFloat(address.add(8))];
}

function finiteVec3(value) {
    return value !== null && value.length === 3 && value.every(Number.isFinite);
}

function vecDistance(a, b) {
    if (!finiteVec3(a) || !finiteVec3(b)) return 0;
    const x = a[0] - b[0];
    const y = a[1] - b[1];
    const z = a[2] - b[2];
    return Math.sqrt(x * x + y * y + z * z);
}

function vecSubtract(a, b) {
    if (!finiteVec3(a) || !finiteVec3(b)) return null;
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function angleDistance(a, b) {
    if (!finiteVec3(a) || !finiteVec3(b)) return 0;
    let result = 0;
    for (let index = 0; index < 3; ++index) {
        let delta = Math.abs(a[index] - b[index]) % 360;
        if (delta > 180) delta = 360 - delta;
        result = Math.max(result, delta);
    }
    return result;
}

function dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function length(a) {
    return Math.sqrt(dot(a, a));
}

function axisDeterminant(axis) {
    return axis[0][0] * (axis[1][1] * axis[2][2] - axis[1][2] * axis[2][1])
        - axis[0][1] * (axis[1][0] * axis[2][2] - axis[1][2] * axis[2][0])
        + axis[0][2] * (axis[1][0] * axis[2][1] - axis[1][1] * axis[2][0]);
}

function readSnapshotPlayerState(snapshot) {
    if (snapshot === null || snapshot.isNull()) return null;
    return {
        address: snapshot.toString(),
        server_time: readI32(snapshot.add(0x352C)),
        offset_0x1c: readVec3(snapshot.add(0x1C)),
        offset_0x24: readVec3(snapshot.add(0x24)),
        delta_angles: readVec3(snapshot.add(0xA0)),
        viewangles: readVec3(snapshot.add(0x14C))
    };
}

function captureViewState() {
    const clientIndex = readU32(activeLocalClientIndex);
    if (clientIndex === null) return null;
    const encoded = readU32(encodedCgameGlobals.add(clientIndex * 4));
    if (encoded === null) return null;
    const cgame = ptr((encoded ^ cgamePointerXor) >>> 0);
    const snap = readPointer(cgame.add(0x3578));
    const nextSnap = readPointer(cgame.add(0x357C));
    const refdefViewaxis = [
        readVec3(cgame.add(0xAE510)),
        readVec3(cgame.add(0xAE51C)),
        readVec3(cgame.add(0xAE528))
    ];
    return {
        client_index: clientIndex,
        cgame: cgame.toString(),
        time: readI32(cgame),
        offset_0x1c: readVec3(cgame.add(0x1C)),
        offset_0x24: readVec3(cgame.add(0x24)),
        predicted_pm_type: readI32(cgame.add(0x4)),
        predicted_pm_time: readI32(cgame.add(0x8)),
        predicted_pm_flags: readU32(cgame.add(0xC)),
        predicted_flags_0x10: readU32(cgame.add(0x10)),
        predicted_flags_0x14: readU32(cgame.add(0x14)),
        predicted_origin: readVec3(cgame.add(0x1C)),
        predicted_player_size_scale: readFloat(cgame.add(0x98)),
        predicted_ground_entity_num: readU32(cgame.add(0xAC)),
        predicted_gravity: readI32(cgame.add(0x90)),
        predicted_jump_time: readI32(cgame.add(0xBC)),
        predicted_jump_origin_z: readFloat(cgame.add(0xC0)),
        predicted_velocity: readVec3(cgame.add(0x28)),
        predicted_view_entity_num: readU32(cgame.add(0x1F0)),
        predicted_link_entity_num: readU32(cgame.add(0x200)),
        predicted_delta_angles: readVec3(cgame.add(0xA0)),
        predicted_viewangles: readVec3(cgame.add(0x14C)),
        predicted_view_height: readFloat(cgame.add(0x15C)),
        refdef_vieworg: readVec3(cgame.add(0xAE504)),
        refdef_viewaxis: refdefViewaxis,
        refdef_viewangles: readVec3(cgame.add(0xB2688)),
        camera_mode: readU8(cgame.add(0xB26B8)),
        camera_reference: readU32(cgame.add(0xAE4D4)),
        snap: readSnapshotPlayerState(snap),
        next_snap: readSnapshotPlayerState(nextSnap)
    };
}

function updateCameraDiagnostics(current) {
    const pose = {
        origin: current.refdef_vieworg,
        angles: current.refdef_viewangles
    };
    ++cameraDiagnostics.samples;
    if (previousCameraPose !== null) {
        const originStep = vecDistance(pose.origin, previousCameraPose.origin);
        const angleStep = angleDistance(pose.angles, previousCameraPose.angles);
        cameraDiagnostics.max_origin_step = Math.max(
            cameraDiagnostics.max_origin_step,
            originStep
        );
        cameraDiagnostics.max_angle_step = Math.max(
            cameraDiagnostics.max_angle_step,
            angleStep
        );
        if (angleStep >= 5) {
            ++cameraDiagnostics.large_angle_steps;
            if (anomalousCameraTransitions < 64) {
                send({
                    event: 'camera_transition',
                    origin_step: originStep,
                    angle_step: angleStep,
                    previous: previousCameraPose,
                    current: pose,
                    predicted_origin: current.predicted_origin,
                    predicted_viewangles: current.predicted_viewangles,
                    snap: current.snap,
                    next_snap: current.next_snap
                });
                ++anomalousCameraTransitions;
            }
        }
    }
    if (previousCameraPose !== null && twoFramesAgoCameraPose !== null) {
        const originReturns = vecDistance(pose.origin, twoFramesAgoCameraPose.origin) <= 0.05;
        const angleReturns = angleDistance(pose.angles, twoFramesAgoCameraPose.angles) <= 0.1;
        const originDiffers = vecDistance(pose.origin, previousCameraPose.origin) >= 0.25;
        const angleDiffers = angleDistance(pose.angles, previousCameraPose.angles) >= 0.5;
        if (originReturns && originDiffers)
            ++cameraDiagnostics.origin_alternating_frames;
        if (angleReturns && angleDiffers)
            ++cameraDiagnostics.angle_alternating_frames;
        if ((originReturns && originDiffers) || (angleReturns && angleDiffers))
            ++cameraDiagnostics.alternating_frames;
    }
    twoFramesAgoCameraPose = previousCameraPose;
    previousCameraPose = pose;

    const axis = current.refdef_viewaxis;
    if (axis !== null && axis.length === 3 && axis.every(finiteVec3)) {
        for (const row of axis) {
            cameraDiagnostics.max_axis_length_error = Math.max(
                cameraDiagnostics.max_axis_length_error,
                Math.abs(length(row) - 1)
            );
        }
        cameraDiagnostics.max_axis_dot = Math.max(
            cameraDiagnostics.max_axis_dot,
            Math.abs(dot(axis[0], axis[1])),
            Math.abs(dot(axis[0], axis[2])),
            Math.abs(dot(axis[1], axis[2]))
        );
        cameraDiagnostics.min_abs_axis_determinant = Math.min(
            cameraDiagnostics.min_abs_axis_determinant,
            Math.abs(axisDeterminant(axis))
        );
    }

    if (current.predicted_pm_type === 0
        && finiteVec3(current.predicted_origin)
        && finiteVec3(current.refdef_vieworg)) {
        const height = current.refdef_vieworg[2] - current.predicted_origin[2];
        ++cameraDiagnostics.playing_samples;
        cameraDiagnostics.playing_height_sum += height;
        cameraDiagnostics.min_playing_height = cameraDiagnostics.min_playing_height === null
            ? height
            : Math.min(cameraDiagnostics.min_playing_height, height);
        cameraDiagnostics.max_playing_height = cameraDiagnostics.max_playing_height === null
            ? height
            : Math.max(cameraDiagnostics.max_playing_height, height);
    }
    if (finiteVec3(current.refdef_viewangles)) {
        let roll = Math.abs(current.refdef_viewangles[2]) % 360;
        if (roll > 180) roll = 360 - roll;
        if (roll >= 2) ++cameraDiagnostics.tilted_samples;
    }
}

function updatePredictionDiagnostics(current) {
    if (current.predicted_pm_type !== 0
        || !finiteVec3(current.predicted_origin)
        || current.snap === null
        || current.next_snap === null
        || !finiteVec3(current.snap.offset_0x1c)
        || !finiteVec3(current.next_snap.offset_0x1c)) {
        return;
    }

    ++predictionDiagnostics.samples;
    const predictedToSnap = vecDistance(
        current.predicted_origin,
        current.snap.offset_0x1c
    );
    const predictedToNext = vecDistance(
        current.predicted_origin,
        current.next_snap.offset_0x1c
    );
    const snapToNext = vecDistance(
        current.snap.offset_0x1c,
        current.next_snap.offset_0x1c
    );
    const predictedToSnapAngle = angleDistance(
        current.predicted_viewangles,
        current.snap.viewangles
    );
    const predictedToNextAngle = angleDistance(
        current.predicted_viewangles,
        current.next_snap.viewangles
    );
    const snapToNextAngle = angleDistance(
        current.snap.viewangles,
        current.next_snap.viewangles
    );
    predictionDiagnostics.predicted_to_snap_sum += predictedToSnap;
    predictionDiagnostics.predicted_to_snap_max = Math.max(
        predictionDiagnostics.predicted_to_snap_max,
        predictedToSnap
    );
    predictionDiagnostics.predicted_to_next_sum += predictedToNext;
    predictionDiagnostics.predicted_to_next_max = Math.max(
        predictionDiagnostics.predicted_to_next_max,
        predictedToNext
    );
    predictionDiagnostics.snap_to_next_sum += snapToNext;
    predictionDiagnostics.snap_to_next_max = Math.max(
        predictionDiagnostics.snap_to_next_max,
        snapToNext
    );
    predictionDiagnostics.predicted_to_snap_angle_sum += predictedToSnapAngle;
    predictionDiagnostics.predicted_to_snap_angle_max = Math.max(
        predictionDiagnostics.predicted_to_snap_angle_max,
        predictedToSnapAngle
    );
    predictionDiagnostics.predicted_to_next_angle_sum += predictedToNextAngle;
    predictionDiagnostics.predicted_to_next_angle_max = Math.max(
        predictionDiagnostics.predicted_to_next_angle_max,
        predictedToNextAngle
    );
    predictionDiagnostics.snap_to_next_angle_sum += snapToNextAngle;
    predictionDiagnostics.snap_to_next_angle_max = Math.max(
        predictionDiagnostics.snap_to_next_angle_max,
        snapToNextAngle
    );

    const nextSnapshotTime = current.next_snap.server_time;
    let snapshotAdvanced = false;
    if (Number.isFinite(nextSnapshotTime) && previousNextSnapshotTime !== null) {
        const gap = nextSnapshotTime - previousNextSnapshotTime;
        snapshotAdvanced = gap > 0;
        if (gap < 0) {
            ++predictionDiagnostics.snapshot_time_regressions;
        } else if (gap > 0) {
            ++predictionDiagnostics.snapshot_advances;
            predictionDiagnostics.snapshot_gap_min_ms =
                predictionDiagnostics.snapshot_gap_min_ms === null
                ? gap
                : Math.min(predictionDiagnostics.snapshot_gap_min_ms, gap);
            predictionDiagnostics.snapshot_gap_max_ms =
                predictionDiagnostics.snapshot_gap_max_ms === null
                ? gap
                : Math.max(predictionDiagnostics.snapshot_gap_max_ms, gap);
        }
    }

    const refdefDelta = previousCameraPose === null
        ? null
        : vecSubtract(current.refdef_vieworg, previousCameraPose.origin);
    if (refdefDelta !== null) {
        const step = length(refdefDelta);
        if (step > 128) {
            ++predictionDiagnostics.discontinuities;
            previousRefdefDelta = null;
            previousRefdefStep = null;
            if (Number.isFinite(nextSnapshotTime))
                previousNextSnapshotTime = nextSnapshotTime;
            return;
        }
        const prefix = snapshotAdvanced ? 'snapshot_frame' : 'other_frame';
        ++predictionDiagnostics[prefix + '_steps'];
        predictionDiagnostics[prefix + '_step_sum'] += step;
        predictionDiagnostics[prefix + '_step_max'] = Math.max(
            predictionDiagnostics[prefix + '_step_max'],
            step
        );
        if (previousRefdefStep !== null) {
            const acceleration = Math.abs(step - previousRefdefStep);
            ++predictionDiagnostics[prefix + '_accelerations'];
            predictionDiagnostics[prefix + '_acceleration_sum'] += acceleration;
            predictionDiagnostics[prefix + '_acceleration_max'] = Math.max(
                predictionDiagnostics[prefix + '_acceleration_max'],
                acceleration
            );
        }
        if (previousRefdefDelta !== null && dot(refdefDelta, previousRefdefDelta) < -0.01)
            ++predictionDiagnostics[prefix + '_direction_reversals'];
        previousRefdefDelta = refdefDelta;
        previousRefdefStep = step;
    }

    if (previousRefdefAngles !== null && finiteVec3(current.refdef_viewangles)) {
        const angleStep = angleDistance(current.refdef_viewangles, previousRefdefAngles);
        const prefix = snapshotAdvanced ? 'snapshot_frame' : 'other_frame';
        ++predictionDiagnostics[prefix + '_angle_steps'];
        predictionDiagnostics[prefix + '_angle_step_sum'] += angleStep;
        predictionDiagnostics[prefix + '_angle_step_max'] = Math.max(
            predictionDiagnostics[prefix + '_angle_step_max'],
            angleStep
        );
        if (previousRefdefAngleStep !== null) {
            const acceleration = Math.abs(angleStep - previousRefdefAngleStep);
            ++predictionDiagnostics[prefix + '_angle_accelerations'];
            predictionDiagnostics[prefix + '_angle_acceleration_sum'] += acceleration;
            predictionDiagnostics[prefix + '_angle_acceleration_max'] = Math.max(
                predictionDiagnostics[prefix + '_angle_acceleration_max'],
                acceleration
            );
        }
        previousRefdefAngleStep = angleStep;
    }
    if (finiteVec3(current.refdef_viewangles))
        previousRefdefAngles = current.refdef_viewangles;

    if (Number.isFinite(nextSnapshotTime))
        previousNextSnapshotTime = nextSnapshotTime;
}

Interceptor.attach(viewValuesComplete, {
    onEnter(_) {
        const current = captureViewState();
        if (current === null) return;
        ++viewStateSamples;
        const key = JSON.stringify({
            predicted_origin: current.predicted_origin,
            predicted_viewangles: current.predicted_viewangles,
            refdef_vieworg: current.refdef_vieworg,
            refdef_viewangles: current.refdef_viewangles
        });
        if (previousViewStateKey !== null && key !== previousViewStateKey)
            ++viewStateTransitions;
        previousViewStateKey = key;
        updatePredictionDiagnostics(current);
        updateCameraDiagnostics(current);
        viewState = current;
    }
});

function readDvar(slot) {
    try {
        const dvar = slot.readPointer();
        if (dvar.isNull()) return null;
        let name = null;
        try { name = dvar.readPointer().readCString(); } catch (_) {}
        return {
            address: dvar.toString(),
            name: name,
            current_u32: readU32(dvar.add(12)),
            current_float: readFloat(dvar.add(12))
        };
    } catch (_) {
        return null;
    }
}

function findGameWindow() {
    const enumWindows = new NativeFunction(
        Module.getGlobalExportByName('EnumWindows'),
        'bool',
        ['pointer', 'pointer']
    );
    const isWindowVisible = new NativeFunction(
        Module.getGlobalExportByName('IsWindowVisible'),
        'bool',
        ['pointer']
    );
    let result = ptr(0);
    const callback = new NativeCallback(function(hwnd, _) {
        const ownerPid = Memory.alloc(4);
        getWindowThreadProcessId(hwnd, ownerPid);
        if (ownerPid.readU32() === Process.id && isWindowVisible(hwnd)) {
            result = hwnd;
            return 0;
        }
        return 1;
    }, 'bool', ['pointer', 'pointer']);
    enumWindows(callback, ptr(0));
    return result;
}

function hookD3D9Present() {
    const d3d9 = Process.getModuleByName('d3d9.dll');
    const direct3DCreate9 = new NativeFunction(
        d3d9.getExportByName('Direct3DCreate9'),
        'pointer',
        ['uint32']
    );
    const d3d = direct3DCreate9(32);
    if (d3d.isNull()) throw new Error('Direct3DCreate9 returned null');

    const d3dVtable = d3d.readPointer();
    const createDevice = new NativeFunction(
        d3dVtable.add(16 * Process.pointerSize).readPointer(),
        'int32',
        ['pointer', 'uint32', 'uint32', 'pointer', 'uint32', 'pointer', 'pointer']
    );
    const releaseD3D = new NativeFunction(
        d3dVtable.add(2 * Process.pointerSize).readPointer(),
        'uint32',
        ['pointer']
    );
    const window = findGameWindow();
    if (window.isNull()) throw new Error('could not find the CODOL window');

    const parameters = Memory.alloc(56);
    parameters.writeByteArray(new Uint8Array(56));
    parameters.add(24).writeU32(1); // D3DSWAPEFFECT_DISCARD
    parameters.add(28).writePointer(window);
    parameters.add(32).writeU32(1); // Windowed
    parameters.add(52).writeU32(0x80000000); // D3DPRESENT_INTERVAL_IMMEDIATE
    const deviceOut = Memory.alloc(Process.pointerSize);
    deviceOut.writePointer(ptr(0));
    const result = createDevice(
        d3d,
        0,
        1, // D3DDEVTYPE_HAL
        window,
        0x20, // D3DCREATE_SOFTWARE_VERTEXPROCESSING
        parameters,
        deviceOut
    );
    if (result < 0 || deviceOut.readPointer().isNull()) {
        releaseD3D(d3d);
        throw new Error('IDirect3D9::CreateDevice failed: 0x' + (result >>> 0).toString(16));
    }

    const device = deviceOut.readPointer();
    const deviceVtable = device.readPointer();
    const devicePresent = deviceVtable.add(17 * Process.pointerSize).readPointer();
    const endScene = deviceVtable.add(42 * Process.pointerSize).readPointer();
    const getSwapChain = new NativeFunction(
        deviceVtable.add(14 * Process.pointerSize).readPointer(),
        'int32',
        ['pointer', 'uint32', 'pointer']
    );
    const releaseDevice = new NativeFunction(
        deviceVtable.add(2 * Process.pointerSize).readPointer(),
        'uint32',
        ['pointer']
    );
    Interceptor.attach(devicePresent, {
        onEnter(_) { devicePresents += 1; }
    });
    Interceptor.attach(endScene, {
        onEnter(_) { endScenes += 1; }
    });

    let swapChainPresent = null;
    const swapChainOut = Memory.alloc(Process.pointerSize);
    swapChainOut.writePointer(ptr(0));
    if (getSwapChain(device, 0, swapChainOut) >= 0) {
        const swapChain = swapChainOut.readPointer();
        if (!swapChain.isNull()) {
            const swapChainVtable = swapChain.readPointer();
            swapChainPresent = swapChainVtable.add(3 * Process.pointerSize).readPointer();
            const releaseSwapChain = new NativeFunction(
                swapChainVtable.add(2 * Process.pointerSize).readPointer(),
                'uint32',
                ['pointer']
            );
            Interceptor.attach(swapChainPresent, {
                onEnter(_) { swapChainPresents += 1; }
            });
            releaseSwapChain(swapChain);
        }
    }
    releaseDevice(device);
    releaseD3D(d3d);
    return {
        devicePresent: devicePresent,
        swapChainPresent: swapChainPresent,
        endScene: endScene
    };
}

let d3d9Addresses = null;
let presentError = null;
try {
    d3d9Addresses = hookD3D9Present();
} catch (error) {
    presentError = error.message;
}

setInterval(function() {
    const now = Date.now();
    const elapsed = Math.max(1, now - previous);
    const foregroundPid = Memory.alloc(4);
    foregroundPid.writeU32(0);
    getWindowThreadProcessId(getForegroundWindow(), foregroundPid);
    send({
        event: 'frame_sample',
        elapsed_ms: elapsed,
        device_presents: devicePresents,
        device_present_fps: devicePresents * 1000.0 / elapsed,
        swap_chain_presents: swapChainPresents,
        swap_chain_present_fps: swapChainPresents * 1000.0 / elapsed,
        end_scenes: endScenes,
        end_scene_hz: endScenes * 1000.0 / elapsed,
        heavy_periodic_ticks: heavyPeriodicTicks,
        heavy_periodic_hz: heavyPeriodicTicks * 1000.0 / elapsed,
        heavy_periodic_avg_ms: heavyPeriodicTicks === 0
            ? 0
            : heavyPeriodicTotalMs / heavyPeriodicTicks,
        heavy_periodic_max_ms: heavyPeriodicMaxMs,
        heavy_periodic_returns: heavyPeriodicReturns,
        cgame_stages: cgameStages,
        post_snapshot_gates: postSnapshotGates,
        post_snapshot_gate_state: postSnapshotGateState,
        view_state_samples: viewStateSamples,
        view_state_transitions: viewStateTransitions,
        view_state: viewState,
        camera_diagnostics: {
            ...cameraDiagnostics,
            alternation_ratio: cameraDiagnostics.samples === 0
                ? 0
                : cameraDiagnostics.alternating_frames / cameraDiagnostics.samples,
            playing_height_average: cameraDiagnostics.playing_samples === 0
                ? null
                : cameraDiagnostics.playing_height_sum / cameraDiagnostics.playing_samples,
            tilted_ratio: cameraDiagnostics.samples === 0
                ? 0
                : cameraDiagnostics.tilted_samples / cameraDiagnostics.samples
        },
        prediction_diagnostics: predictionDiagnostics,
        pre_snapshot_stages: preSnapshotStages,
        pre_snapshot_stage_hz: preSnapshotStages * 1000.0 / elapsed,
        frame_dispatches: frameDispatches,
        frame_dispatch_hz: frameDispatches * 1000.0 / elapsed,
        frame_bodies: frameBodies,
        frame_body_hz: frameBodies * 1000.0 / elapsed,
        frame_dispatch_callers: frameDispatchCallers,
        frame_dispatch_gates: {
            lock: readU32(frameDispatchLock),
            gate_a: readU32(frameDispatchGateA),
            gate_b: readU32(frameDispatchGateB),
            gate_c: readU32(frameDispatchGateC),
            gate_d: readU32(frameDispatchGateD)
        },
        frame_pacing: {
            timescale: readFloat(frameTimescale),
            global_timescale: readFloat(globalTimescale),
            fixed_time_dvar: readDvar(fixedTimeDvarSlot),
            timescale_dvar_a: readDvar(timescaleDvarASlot),
            timescale_dvar_b: readDvar(timescaleDvarBSlot),
            max_fps_dvar: readDvar(maxFpsDvarSlot),
            secondary_fps_dvar: readDvar(secondaryFpsDvarSlot)
        },
        foreground_pid: foregroundPid.readU32(),
        game_is_foreground: foregroundPid.readU32() === Process.id
    });
    devicePresents = 0;
    swapChainPresents = 0;
    endScenes = 0;
    heavyPeriodicTicks = 0;
    heavyPeriodicTotalMs = 0;
    heavyPeriodicMaxMs = 0;
    heavyPeriodicReturns = { zero: 0, nonzero: 0 };
    for (const name of Object.keys(cgameStages)) cgameStages[name] = 0;
    postSnapshotGates = {};
    viewStateSamples = 0;
    viewStateTransitions = 0;
    cameraDiagnostics = emptyCameraDiagnostics();
    predictionDiagnostics = emptyPredictionDiagnostics();
    preSnapshotStages = 0;
    frameDispatches = 0;
    frameBodies = 0;
    frameDispatchCallers = {};
    previous = now;
}, 1000);

send({
    event: 'ready',
    module_base: module.base.toString(),
    heavy_periodic_tick: heavyPeriodicTick.toString(),
    cgame_stages: Object.fromEntries(
        Object.entries(cgameStageAddresses).map(([name, address]) => [name, address.toString()])
    ),
    post_snapshot_gate: postSnapshotGate.toString(),
    view_values_complete: viewValuesComplete.toString(),
    pre_snapshot_stage: preSnapshotStage.toString(),
    frame_dispatch: frameDispatch.toString(),
    frame_body: frameBody.toString(),
    device_present: d3d9Addresses === null ? null : d3d9Addresses.devicePresent.toString(),
    swap_chain_present: d3d9Addresses === null || d3d9Addresses.swapChainPresent === null
        ? null
        : d3d9Addresses.swapChainPresent.toString(),
    end_scene: d3d9Addresses === null ? null : d3d9Addresses.endScene.toString(),
    present_error: presentError
});
"""


def summarize_camera_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = [
        row.get("camera_diagnostics")
        for row in rows
        if row.get("event") == "frame_sample"
        and isinstance(row.get("camera_diagnostics"), dict)
    ]
    prediction_diagnostics = [
        row.get("prediction_diagnostics")
        for row in rows
        if row.get("event") == "frame_sample"
        and isinstance(row.get("prediction_diagnostics"), dict)
    ]
    samples = sum(int(item.get("samples", 0)) for item in diagnostics)
    playing_samples = sum(int(item.get("playing_samples", 0)) for item in diagnostics)
    alternating_frames = sum(int(item.get("alternating_frames", 0)) for item in diagnostics)
    angle_alternating_frames = sum(
        int(item.get("angle_alternating_frames", 0)) for item in diagnostics
    )
    origin_alternating_frames = sum(
        int(item.get("origin_alternating_frames", 0)) for item in diagnostics
    )
    large_angle_steps = sum(int(item.get("large_angle_steps", 0)) for item in diagnostics)
    tilted_samples = sum(int(item.get("tilted_samples", 0)) for item in diagnostics)
    playing_height_sum = sum(float(item.get("playing_height_sum", 0)) for item in diagnostics)
    max_origin_step = max(
        (float(item.get("max_origin_step", 0)) for item in diagnostics),
        default=0.0,
    )
    max_angle_step = max(
        (float(item.get("max_angle_step", 0)) for item in diagnostics),
        default=0.0,
    )
    max_axis_length_error = max(
        (float(item.get("max_axis_length_error", 0)) for item in diagnostics),
        default=0.0,
    )
    max_axis_dot = max(
        (float(item.get("max_axis_dot", 0)) for item in diagnostics),
        default=0.0,
    )
    min_abs_axis_determinant = min(
        (float(item.get("min_abs_axis_determinant", 1)) for item in diagnostics),
        default=1.0,
    )
    alternation_ratio = alternating_frames / samples if samples else 0.0
    tilted_ratio = tilted_samples / samples if samples else 0.0
    playing_height_average = (
        playing_height_sum / playing_samples if playing_samples else None
    )
    alternation_detected = alternating_frames >= 3 and alternation_ratio >= 0.05
    repeated_angle_jumps = large_angle_steps >= 3
    invalid_view_axis = (
        max_axis_length_error > 0.03
        or max_axis_dot > 0.03
        or min_abs_axis_determinant < 0.95
    )
    ground_level_camera = (
        playing_samples >= 10
        and playing_height_average is not None
        and playing_height_average < 32.0
    )
    persistent_roll = samples >= 10 and tilted_ratio >= 0.5
    prediction_samples = sum(
        int(item.get("samples", 0)) for item in prediction_diagnostics
    )
    snapshot_advances = sum(
        int(item.get("snapshot_advances", 0)) for item in prediction_diagnostics
    )
    snapshot_time_regressions = sum(
        int(item.get("snapshot_time_regressions", 0))
        for item in prediction_diagnostics
    )
    discontinuities = sum(
        int(item.get("discontinuities", 0)) for item in prediction_diagnostics
    )

    def total(name: str) -> float:
        return sum(float(item.get(name, 0)) for item in prediction_diagnostics)

    def count(name: str) -> int:
        return sum(int(item.get(name, 0)) for item in prediction_diagnostics)

    def maximum(name: str) -> float:
        return max(
            (float(item.get(name, 0)) for item in prediction_diagnostics),
            default=0.0,
        )

    def average(sum_name: str, count_value: int) -> float | None:
        return total(sum_name) / count_value if count_value else None

    snapshot_frame_steps = count("snapshot_frame_steps")
    other_frame_steps = count("other_frame_steps")
    snapshot_frame_accelerations = count("snapshot_frame_accelerations")
    other_frame_accelerations = count("other_frame_accelerations")
    snapshot_frame_angle_steps = count("snapshot_frame_angle_steps")
    other_frame_angle_steps = count("other_frame_angle_steps")
    snapshot_frame_angle_accelerations = count(
        "snapshot_frame_angle_accelerations"
    )
    other_frame_angle_accelerations = count("other_frame_angle_accelerations")
    snapshot_frame_step_average = average(
        "snapshot_frame_step_sum", snapshot_frame_steps
    )
    other_frame_step_average = average("other_frame_step_sum", other_frame_steps)
    snapshot_frame_acceleration_average = average(
        "snapshot_frame_acceleration_sum", snapshot_frame_accelerations
    )
    other_frame_acceleration_average = average(
        "other_frame_acceleration_sum", other_frame_accelerations
    )
    snapshot_frame_angle_step_average = average(
        "snapshot_frame_angle_step_sum", snapshot_frame_angle_steps
    )
    other_frame_angle_step_average = average(
        "other_frame_angle_step_sum", other_frame_angle_steps
    )
    snapshot_frame_angle_acceleration_average = average(
        "snapshot_frame_angle_acceleration_sum",
        snapshot_frame_angle_accelerations,
    )
    other_frame_angle_acceleration_average = average(
        "other_frame_angle_acceleration_sum", other_frame_angle_accelerations
    )
    snapshot_direction_reversals = count("snapshot_direction_reversals")
    other_direction_reversals = count("other_direction_reversals")
    step_spike = (
        snapshot_frame_steps >= 10
        and other_frame_steps >= 10
        and snapshot_frame_step_average is not None
        and other_frame_step_average is not None
        and snapshot_frame_step_average > other_frame_step_average + 0.25
        and snapshot_frame_step_average > other_frame_step_average * 1.75
    )
    acceleration_spike = (
        snapshot_frame_accelerations >= 10
        and other_frame_accelerations >= 10
        and snapshot_frame_acceleration_average is not None
        and other_frame_acceleration_average is not None
        and snapshot_frame_acceleration_average
        > other_frame_acceleration_average + 0.15
        and snapshot_frame_acceleration_average
        > other_frame_acceleration_average * 1.75
    )
    snapshot_correlated_jitter = (
        snapshot_advances >= 10
        and (snapshot_direction_reversals >= 3 or step_spike or acceleration_spike)
    )
    snapshot_gaps = [
        int(value)
        for item in prediction_diagnostics
        for value in [item.get("snapshot_gap_min_ms")]
        if value is not None
    ]
    snapshot_gap_maxima = [
        int(value)
        for item in prediction_diagnostics
        for value in [item.get("snapshot_gap_max_ms")]
        if value is not None
    ]
    confidence = "high" if samples >= 120 else "medium" if samples >= 30 else "low"
    return {
        "sample_count": samples,
        "playing_sample_count": playing_samples,
        "confidence": confidence,
        "thresholds": {
            "alternation_min_frames": 3,
            "alternation_min_ratio": 0.05,
            "axis_length_error": 0.03,
            "axis_dot": 0.03,
            "axis_min_abs_determinant": 0.95,
            "ground_level_height": 32.0,
            "persistent_roll_degrees": 2.0,
            "persistent_roll_ratio": 0.5,
            "snapshot_jitter_min_advances": 10,
            "snapshot_jitter_min_reversals": 3,
            "snapshot_step_ratio": 1.75,
            "snapshot_step_delta": 0.25,
            "snapshot_acceleration_ratio": 1.75,
            "snapshot_acceleration_delta": 0.15,
        },
        "camera_shake_detected": (
            alternation_detected
            or repeated_angle_jumps
            or snapshot_correlated_jitter
        ),
        "snapshot_correlated_jitter_detected": snapshot_correlated_jitter,
        "invalid_view_axis_detected": invalid_view_axis,
        "ground_level_camera_detected": ground_level_camera,
        "persistent_roll_detected": persistent_roll,
        "alternating_frames": alternating_frames,
        "angle_alternating_frames": angle_alternating_frames,
        "origin_alternating_frames": origin_alternating_frames,
        "large_angle_steps": large_angle_steps,
        "alternation_ratio": alternation_ratio,
        "max_origin_step": max_origin_step,
        "max_angle_step": max_angle_step,
        "max_axis_length_error": max_axis_length_error,
        "max_axis_dot": max_axis_dot,
        "min_abs_axis_determinant": min_abs_axis_determinant,
        "playing_height_average": playing_height_average,
        "tilted_ratio": tilted_ratio,
        "prediction_sample_count": prediction_samples,
        "snapshot_advances": snapshot_advances,
        "snapshot_time_regressions": snapshot_time_regressions,
        "prediction_discontinuities": discontinuities,
        "snapshot_gap_min_ms": min(snapshot_gaps) if snapshot_gaps else None,
        "snapshot_gap_max_ms": max(snapshot_gap_maxima) if snapshot_gap_maxima else None,
        "predicted_to_snap_average": average(
            "predicted_to_snap_sum", prediction_samples
        ),
        "predicted_to_snap_max": maximum("predicted_to_snap_max"),
        "predicted_to_next_average": average(
            "predicted_to_next_sum", prediction_samples
        ),
        "predicted_to_next_max": maximum("predicted_to_next_max"),
        "snap_to_next_average": average("snap_to_next_sum", prediction_samples),
        "snap_to_next_max": maximum("snap_to_next_max"),
        "predicted_to_snap_angle_average": average(
            "predicted_to_snap_angle_sum", prediction_samples
        ),
        "predicted_to_snap_angle_max": maximum("predicted_to_snap_angle_max"),
        "predicted_to_next_angle_average": average(
            "predicted_to_next_angle_sum", prediction_samples
        ),
        "predicted_to_next_angle_max": maximum("predicted_to_next_angle_max"),
        "snap_to_next_angle_average": average(
            "snap_to_next_angle_sum", prediction_samples
        ),
        "snap_to_next_angle_max": maximum("snap_to_next_angle_max"),
        "snapshot_frame_step_average": snapshot_frame_step_average,
        "snapshot_frame_step_max": maximum("snapshot_frame_step_max"),
        "other_frame_step_average": other_frame_step_average,
        "other_frame_step_max": maximum("other_frame_step_max"),
        "snapshot_frame_acceleration_average": (
            snapshot_frame_acceleration_average
        ),
        "snapshot_frame_acceleration_max": maximum(
            "snapshot_frame_acceleration_max"
        ),
        "other_frame_acceleration_average": other_frame_acceleration_average,
        "other_frame_acceleration_max": maximum("other_frame_acceleration_max"),
        "snapshot_frame_angle_step_average": snapshot_frame_angle_step_average,
        "snapshot_frame_angle_step_max": maximum("snapshot_frame_angle_step_max"),
        "other_frame_angle_step_average": other_frame_angle_step_average,
        "other_frame_angle_step_max": maximum("other_frame_angle_step_max"),
        "snapshot_frame_angle_acceleration_average": (
            snapshot_frame_angle_acceleration_average
        ),
        "snapshot_frame_angle_acceleration_max": maximum(
            "snapshot_frame_angle_acceleration_max"
        ),
        "other_frame_angle_acceleration_average": (
            other_frame_angle_acceleration_average
        ),
        "other_frame_angle_acceleration_max": maximum(
            "other_frame_angle_acceleration_max"
        ),
        "snapshot_direction_reversals": snapshot_direction_reversals,
        "other_direction_reversals": other_direction_reversals,
    }


def summarize_camera_log(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return summarize_camera_rows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    script = session.create_script(build_script())
    stopped = Event()
    args.log.parent.mkdir(parents=True, exist_ok=True)

    def record(event: str, **fields: Any) -> None:
        row = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            **fields,
        }
        with args.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True) + "\n")

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "send":
            payload = dict(message.get("payload", {}))
            record(payload.pop("event", "message"), **payload)
        else:
            record("frida_message", message=message)

    script.on("message", on_message)
    session.on("detached", lambda reason, crash=None: stopped.set())
    script.load()
    record("attached", pid=pid, duration=args.duration)
    try:
        stopped.wait(None if args.duration <= 0 else args.duration)
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
    summary_path = args.log.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summarize_camera_log(args.log), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
