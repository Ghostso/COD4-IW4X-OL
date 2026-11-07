#!/usr/bin/env python3
"""Exercise CODOL's native binding-action input path on the main thread."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from CodolCaptureEvidence import (
    OPAQUE_DATA_KEY,
    RAW_SAMPLE_FORMAT,
    RAW_SAMPLE_SCHEMA_VERSION,
    capture_summary,
    is_plain_int,
    load_raw_sample_checkpoint,
    opaque_sample_details,
    summarize_raw_sample_checkpoint,
    write_json_atomic as write_json_checkpoint,
)
from CodolFridaRuntime import configure_frida_runtime
from CodolInputScenario import (
    ACTION_NAMES,
    load_scenario_document,
    normalize_scenario,
    scenario_duration_seconds,
    single_action_scenario,
)

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
PLUGIN_NAME = "CodolGameServer.Localnet32"
COM_FRAME_RVA = 0x19E000
EXECUTE_BINDING_ACTION_RVA = 0x60870
BINDING_ACTION_TABLE_RVA = 0x8E1CC0
BINDING_ACTION_COUNT = 100
PARSE_SNAPSHOT_RVA = 0x6D170
PARSE_PLAYERSTATE_RVA = 0x1A4230
READ_DELTA_FIELDS_RVA = 0x1A34F0
OBJECTIVE_FIELDS_RVA = 0x856A78
PLAYERSTATE_STATS_RVA = 0x1A463F
PLAYERSTATE_OBJECTIVE_PRESENCE_RVA = 0x1A51A6
PARSE_SERVER_MESSAGE_RVA = 0x6E6A0
PACKET_EVENT_RVA = 0x67520
COM_ERROR_RVA = 0x197D20
CG_ENTITY_UPDATE_RVA = 0x11AD90
CG_ENTITY_SECURE_ORIGIN_KEY_RVA = 0x8E514C
MSG_READ_DELTA_ENTITY_RVA = 0x1A3670
CL_PARSE_PACKET_ENTITIES_RVA = 0x6C2F0
ACTIVE_LOCAL_CLIENT_INDEX_RVA = 0x7417BA8
ACTIVE_CG_ENTITY_INDEX_RVA = ACTIVE_LOCAL_CLIENT_INDEX_RVA + 8
ENCODED_CGAME_GLOBALS_RVA = 0x1619510
CGAME_POINTER_XOR = 0xFBB2C97A
CG_ENTITY_POINTER_XOR = 0x2168F672
CG_ENTITY_STRIDE = 0x238
CG_ENTITY_COUNT = 2048
CLIENT_PLAYER_STATE_SIZE = 0x4D0
NATIVE_SAMPLE_CAPACITY = 4096


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


class RawSampleCheckpoint:
    def __init__(self, path: Path, scenario: dict[str, Any]) -> None:
        self.path = path
        self.blob_path = path.with_suffix(".bin")
        self.persisted_sample_count = 0
        self.persisted_blob_size = 0
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "record": "header",
            "format": RAW_SAMPLE_FORMAT,
            "schema_version": RAW_SAMPLE_SCHEMA_VERSION,
            "scenario": normalize_scenario(scenario),
            "blob_file": self.blob_path.name,
        }
        with self.blob_path.open("xb") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        with self.path.open("x", encoding="utf-8", newline="\n") as stream:
            self._write_records(stream, [header])

    @staticmethod
    def _write_records(stream: Any, records: list[dict[str, Any]]) -> None:
        stream.write(
            "".join(
                json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                for record in records
            )
        )
        stream.flush()
        os.fsync(stream.fileno())

    def checkpoint(self, samples: list[dict[str, Any]]) -> None:
        with self.lock:
            if len(samples) < self.persisted_sample_count:
                raise ValueError("raw sample checkpoint cannot discard persisted samples")
            pending: list[dict[str, Any]] = []
            pending_blobs: list[bytes] = []
            blob_offset = self.persisted_blob_size
            for index in range(self.persisted_sample_count, len(samples)):
                sample = dict(samples[index])
                opaque_data = sample.pop(OPAQUE_DATA_KEY, None)
                if opaque_data is not None:
                    if not isinstance(opaque_data, (bytes, bytearray, memoryview)):
                        raise ValueError("opaque sample evidence must be bytes")
                    blob = bytes(opaque_data)
                    sample["opaque_evidence"] = {
                        "offset": blob_offset,
                        "size": len(blob),
                        "sha256": hashlib.sha256(blob).hexdigest(),
                    }
                    pending_blobs.append(blob)
                    blob_offset += len(blob)
                pending.append(
                    {
                        "record": "sample",
                        "index": index,
                        "sample": sample,
                    }
                )
            if not pending:
                return
            with self.blob_path.open("r+b") as stream:
                stream.seek(0, os.SEEK_END)
                actual_size = stream.tell()
                if actual_size < self.persisted_blob_size:
                    raise ValueError("raw sample blob checkpoint was truncated")
                if actual_size != self.persisted_blob_size:
                    stream.truncate(self.persisted_blob_size)
                for blob in pending_blobs:
                    stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                self._write_records(stream, pending)
            self.persisted_sample_count = len(samples)
            self.persisted_blob_size = blob_offset

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "path": str(self.path),
                "format": RAW_SAMPLE_FORMAT,
                "schema_version": RAW_SAMPLE_SCHEMA_VERSION,
                "persisted_sample_count": self.persisted_sample_count,
                "blob_path": str(self.blob_path),
                "persisted_blob_size": self.persisted_blob_size,
            }


def build_script(
    action: str,
    local_client: int,
    hold_seconds: float,
    observe_seconds: float,
    sample_interval: float,
    trace_parser: bool = True,
) -> str:
    return build_scenario_script(
        single_action_scenario(action, hold_seconds, observe_seconds),
        local_client,
        sample_interval,
        legacy_action=action,
        legacy_hold_seconds=hold_seconds,
        legacy_observe_seconds=observe_seconds,
        trace_parser=trace_parser,
    )


def build_scenario_script(
    scenario: dict[str, Any],
    local_client: int,
    sample_interval: float,
    *,
    legacy_action: str | None = None,
    legacy_hold_seconds: float | None = None,
    legacy_observe_seconds: float | None = None,
    trace_parser: bool = True,
) -> str:
    scenario = normalize_scenario(scenario)
    action_bindings = {
        action: {
            "down_name": ACTION_NAMES[action][0],
            "up_name": ACTION_NAMES[action][1],
            "key_code": ACTION_NAMES[action][2],
        }
        for action in dict.fromkeys(event["action"] for event in scenario["events"])
    }
    legacy_armed_fields = ""
    if legacy_action is not None:
        down_name, up_name, key_code = ACTION_NAMES[legacy_action]
        legacy_armed_fields = f"""
    action: {json.dumps(legacy_action)},
    down_name: {json.dumps(down_name)},
    down_action: actionBindings[{json.dumps(legacy_action)}].down_action,
    up_name: {json.dumps(up_name)},
    up_action: actionBindings[{json.dumps(legacy_action)}].up_action,
    key_code: {key_code},
    hold_seconds: {legacy_hold_seconds},
    observe_seconds: {legacy_observe_seconds},"""
    parser_hooks = f"""
traceMessageParser(parseSnapshot, 'snapshot', function (_) {{
    return this.context.ecx;
}});
traceMessageParser(parsePlayerState, 'playerstate', function (_) {{
    return this.context.esi;
}});
tracePlayerstateMilestone(playerstateStats, 'stats');
tracePlayerstateMilestone(playerstateObjectivePresence, 'objective_presence');
Interceptor.attach(readDeltaFields, {{
    onEnter(_) {{
        const stack = this.context.esp;
        const fields = readPointer(stack, 0x18);
        const numFields = readU32(stack, 0x14);
        const indexBits = readU32(stack, 0x1c);
        parserSummary.delta_fields_enter_count++;
        parserSummary.delta_fields_last_call = {{
            fields: fields === null ? null : fields.toString(),
            fields_preferred: fields === null ? null : normalizeModuleAddress(fields),
            num_fields: numFields,
            index_bits: indexBits,
            caller: this.returnAddress.toString(),
            caller_preferred: normalizeModuleAddress(this.returnAddress)
        }};
        if (numFields === 6) {{
            parserSummary.delta_fields_six_field_count++;
            parserSummary.delta_fields_last_six_field_call =
                parserSummary.delta_fields_last_call;
        }}
        if (fields !== null && fields.equals(objectiveFields))
            parserSummary.delta_fields_objective_table_count++;
        this.objectiveDeltaFieldsCall = fields !== null &&
            fields.equals(objectiveFields) && numFields === 6 && indexBits === 1;
        if (!this.objectiveDeltaFieldsCall) return;

        this.msg = readPointer(stack, 0x04);
        this.readcountBefore = readU32(this.msg, 0x1c);
        this.overflowBefore = readU32(this.msg, 0);
        this.objectiveThreadId = Process.getCurrentThreadId();
        parserSummary.objective_enter_count++;
        parserSummary.objective_last_thread_id = this.objectiveThreadId;
        parserSummary.objective_last_readcount_before = this.readcountBefore;
        parserSummary.objective_last_overflow_before = this.overflowBefore;
    }},
    onLeave(_) {{
        if (!this.objectiveDeltaFieldsCall) return;
        const readcountAfter = readU32(this.msg, 0x1c);
        const overflowAfter = readU32(this.msg, 0);
        parserSummary.objective_leave_count++;
        parserSummary.objective_last_readcount_after = readcountAfter;
        parserSummary.objective_last_overflow_after = overflowAfter;
        if (this.readcountBefore !== null && readcountAfter !== null) {{
            const delta = readcountAfter - this.readcountBefore;
            parserSummary.objective_last_readcount_delta = delta;
            parserSummary.objective_max_readcount_delta = Math.max(
                parserSummary.objective_max_readcount_delta, delta);
        }}
        if (!this.overflowBefore && overflowAfter) {{
            parserSummary.objective_overflow_transitions++;
            if (parserSummary.objective_first_overflow === null) {{
                parserSummary.objective_first_overflow = {{
                    enter_count: parserSummary.objective_enter_count,
                    leave_count: parserSummary.objective_leave_count,
                    readcount_before: this.readcountBefore,
                    readcount_after: readcountAfter,
                    thread_id: this.objectiveThreadId
                }};
            }}
        }}
    }}
}});
Interceptor.attach(parseServerMessage, {{
    onEnter(_) {{
        this.msg = this.context.edi;
        this.overflowBefore = readU32(this.msg, 0);
        parserSummary.server_message_enter_count++;
    }},
    onLeave(_) {{
        parserSummary.server_message_leave_count++;
        const overflowAfter = readU32(this.msg, 0);
        if (overflowAfter) parserSummary.overflow_events++;
        if (!this.overflowBefore && overflowAfter &&
            parserSummary.entity_first_overflow === null) {{
            parserSummary.entity_first_overflow = {{
                packet_sequence: parserSummary.entity_delta_packet_sequence,
                readcount: readU32(this.msg, 0x1c),
                bit: readU32(this.msg, 0x20),
                split_start: readU32(this.msg, 0x14),
                split_length: readU32(this.msg, 0x18),
                recent: parserSummary.entity_delta_recent.slice()
            }};
            send({{
                ok: false,
                event: 'entity-parser-overflow',
                timestamp_ms: Date.now(),
                failure: parserSummary.entity_first_overflow
            }});
        }}
    }}
}});
Interceptor.attach(packetEvent, {{
    onLeave(retval) {{
        parserSummary.packet_event_leave_count++;
        if (retval.toInt32() === 1) parserSummary.accepted_packet_count++;
        else parserSummary.rejected_packet_count++;
    }}
}});
""" if trace_parser else ""

    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const comFrame = module.base.add({COM_FRAME_RVA});
const executeBindingAction = new NativeFunction(
    module.base.add({EXECUTE_BINDING_ACTION_RVA}),
    'void',
    ['int', 'int', 'int'],
    'thiscall');
const actionTable = module.base.add({BINDING_ACTION_TABLE_RVA});
const parseSnapshot = module.base.add({PARSE_SNAPSHOT_RVA});
const parsePlayerState = module.base.add({PARSE_PLAYERSTATE_RVA});
const readDeltaFields = module.base.add({READ_DELTA_FIELDS_RVA});
const objectiveFields = module.base.add({OBJECTIVE_FIELDS_RVA});
const playerstateStats = module.base.add({PLAYERSTATE_STATS_RVA});
const playerstateObjectivePresence =
    module.base.add({PLAYERSTATE_OBJECTIVE_PRESENCE_RVA});
const parseServerMessage = module.base.add({PARSE_SERVER_MESSAGE_RVA});
const packetEvent = module.base.add({PACKET_EVENT_RVA});
const comError = module.base.add({COM_ERROR_RVA});
const cgEntityUpdate = module.base.add({CG_ENTITY_UPDATE_RVA});
const cgEntitySecureOriginKey =
    module.base.add({CG_ENTITY_SECURE_ORIGIN_KEY_RVA});
const msgReadDeltaEntity = module.base.add({MSG_READ_DELTA_ENTITY_RVA});
const clParsePacketEntities = module.base.add({CL_PARSE_PACKET_ENTITIES_RVA});
const activeLocalClientIndex = module.base.add({ACTIVE_LOCAL_CLIENT_INDEX_RVA});
const activeCgEntityIndex = module.base.add({ACTIVE_CG_ENTITY_INDEX_RVA});
const encodedCgameGlobals = module.base.add({ENCODED_CGAME_GLOBALS_RVA});
const localClient = {local_client};
const scenario = {json.dumps(scenario, separators=(",", ":"))};
const actionBindingSpecs = {json.dumps(action_bindings, separators=(",", ":"))};
const sampleIntervalMilliseconds = {sample_interval * 1000.0};
let phase = 'arming';
let scenarioStartedAt = 0;
let nextScenarioEvent = 0;
let busy = false;
let sampleSequence = 0;
let lastSampleAt = 0;
const activeActions = new Map();
const scenarioTiming = {{
    dispatched_event_group_count: 0,
    overdue_event_group_count: 0,
    max_event_drift_ms: 0,
    valid: true
}};
const parserSummary = {{
    snapshot_enter_count: 0,
    snapshot_leave_count: 0,
    playerstate_enter_count: 0,
    playerstate_leave_count: 0,
    playerstate_last_readcount_before: null,
    playerstate_last_readcount_after: null,
    playerstate_last_readable_bytes: null,
    playerstate_stats_count: 0,
    playerstate_stats_last_readcount: null,
    playerstate_stats_last_overflow: null,
    playerstate_objective_presence_count: 0,
    playerstate_objective_presence_last_readcount: null,
    playerstate_objective_presence_last_overflow: null,
    server_message_enter_count: 0,
    server_message_leave_count: 0,
    packet_event_leave_count: 0,
    accepted_packet_count: 0,
    rejected_packet_count: 0,
    overflow_events: 0,
    inner_overflow_observations: 0,
    delta_fields_enter_count: 0,
    delta_fields_six_field_count: 0,
    delta_fields_objective_table_count: 0,
    delta_fields_last_call: null,
    delta_fields_last_six_field_call: null,
    objective_enter_count: 0,
    objective_leave_count: 0,
    objective_overflow_transitions: 0,
    objective_last_thread_id: null,
    objective_last_readcount_before: null,
    objective_last_readcount_after: null,
    objective_last_readcount_delta: null,
    objective_max_readcount_delta: 0,
    objective_last_overflow_before: null,
    objective_last_overflow_after: null,
    objective_first_overflow: null,
    com_error_count: 0,
    last_com_error_format: null,
    last_com_error_argument: null,
    entity_secure_origin_call_count: 0,
    entity_secure_origin_invalid_target_count: 0,
    entity_secure_origin_last_call: null,
    entity_delta_count: 0,
    entity_delta_invalid_number_count: 0,
    entity_delta_packet_sequence: 0,
    entity_delta_recent: [],
    entity_first_overflow: null
}};

const plugin = Process.findModuleByName({json.dumps(PLUGIN_NAME)});
let getWorldPlayerSampleV1 = null;
if (plugin !== null) {{
    try {{
        getWorldPlayerSampleV1 = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerSampleV1'),
            'bool', ['uint32', 'pointer', 'uint32']);
    }} catch (_) {{}}
}}

function resolveAction(name) {{
    for (let index = 1; index < {BINDING_ACTION_COUNT}; ++index) {{
        const namePointer = actionTable.add(index * Process.pointerSize).readPointer();
        if (!namePointer.isNull() && namePointer.readUtf8String() === name)
            return index;
    }}
    throw new Error('binding action not found: ' + name);
}}

function readU32(pointer, offset) {{
    try {{ return pointer.add(offset).readU32(); }} catch (_) {{ return null; }}
}}

function readPointer(pointer, offset) {{
    try {{ return pointer.add(offset).readPointer(); }} catch (_) {{ return null; }}
}}

function readString(pointer) {{
    if (pointer === null || pointer.isNull()) return null;
    try {{ return pointer.readCString(); }} catch (_) {{ return null; }}
}}

function normalizeModuleAddress(address) {{
    if (address.compare(module.base) < 0 ||
        address.compare(module.base.add(module.size)) >= 0)
        return null;
    return ptr('0x400000').add(address.sub(module.base)).toString();
}}

function captureBacktrace(context) {{
    try {{
        return Thread.backtrace(context, Backtracer.ACCURATE).map((address) => ({{
            address: address.toString(),
            preferred_address: normalizeModuleAddress(address),
            symbol: DebugSymbol.fromAddress(address).toString()
        }}));
    }} catch (_) {{
        return Thread.backtrace(context, Backtracer.FUZZY).map((address) => ({{
            address: address.toString(),
            preferred_address: normalizeModuleAddress(address),
            symbol: DebugSymbol.fromAddress(address).toString()
        }}));
    }}
}}

function captureX86Registers(context) {{
    const result = {{}};
    for (const name of ['eip', 'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'esp', 'ebp']) {{
        try {{ result[name] = context[name].toString(); }} catch (_) {{}}
    }}
    return result;
}}

Process.setExceptionHandler(function (details) {{
    // OutputDebugString and the MSVC runtime use expected system exceptions.
    // Keep the handler passive, but do not let those events bury real faults.
    if (details.type !== 'system') {{
        send({{
            ok: false,
            event: 'process-exception',
            timestamp_ms: Date.now(),
            type: details.type,
            address: details.address.toString(),
            preferred_address: normalizeModuleAddress(details.address),
            memory: details.memory === undefined ? null : {{
                operation: details.memory.operation,
                address: details.memory.address.toString()
            }},
            thread_id: Process.getCurrentThreadId(),
            registers: captureX86Registers(details.context),
            backtrace: captureBacktrace(details.context)
        }});
    }}
    return false;
}});

function readEntityStateSummary(base) {{
    return {{
        number: readU32(base, 0),
        e_type: readU32(base, 0x04),
        e_flags: readU32(base, 0x08),
        position_trajectory_type: readU32(base, 0x0c),
        position_trajectory_time: readU32(base, 0x10),
        position_trajectory_duration: readU32(base, 0x14),
        angle_trajectory_type: readU32(base, 0x30),
        angle_trajectory_time: readU32(base, 0x34),
        angle_trajectory_duration: readU32(base, 0x38),
        movement_dir: readU32(base, 0x5c),
        unknown_a0: readU32(base, 0xa0),
        solid: readU32(base, 0xa4),
        ground_entity_num: readU32(base, 0xa8),
        event_sequence: readU32(base, 0xac),
        events: [0, 1, 2, 3].map(function (index) {{
            const offset = 0xb0 + index * 8;
            return {{
                event: readU32(base, offset),
                parameter: readU32(base, offset + 4)
            }};
        }}),
        packed_weapon: readU32(base, 0xd0),
        torso_anim: readU32(base, 0xd4),
        legs_anim: readU32(base, 0xd8)
    }};
}}

function currentCgEntityArray() {{
    const pointerTableIndex = readU32(activeCgEntityIndex, 0);
    if (pointerTableIndex === null || pointerTableIndex > 15) return null;
    const encoded = readU32(encodedCgameGlobals, pointerTableIndex * 4);
    if (encoded === null) return null;
    const entities = ptr((encoded ^ {CG_ENTITY_POINTER_XOR}) >>> 0);
    return readU32(entities, 0) === null ? null : entities;
}}

// Entity delta tracing is intentionally excluded from low-interference input
// probes. Detaching several high-frequency hooks while packet parsing is active
// can destabilize the target process and is unrelated to input dispatch.
if ({str(trace_parser).lower()}) {{
Interceptor.attach(clParsePacketEntities, {{
    onEnter(args) {{
        parserSummary.entity_delta_packet_sequence++;
        parserSummary.entity_delta_recent = [];
    }}
}});

Interceptor.attach(msgReadDeltaEntity, {{
    onEnter(args) {{
        this.message = args[0];
        this.destination = args[3];
        this.entry = {{
            number: args[4].toInt32(),
            readcount_before: readU32(args[0], 0x1c),
            bit_before: readU32(args[0], 0x20),
            baseline: readEntityStateSummary(args[2])
        }};
    }},
    onLeave(result) {{
        this.entry.removed = result.toInt32() === 1;
        this.entry.readcount_after = readU32(this.message, 0x1c);
        this.entry.bit_after = readU32(this.message, 0x20);
        this.entry.decoded = readEntityStateSummary(this.destination);
        parserSummary.entity_delta_count++;
        parserSummary.entity_delta_recent.push(this.entry);
        if (parserSummary.entity_delta_recent.length > 512)
            parserSummary.entity_delta_recent.shift();
        if (this.entry.number < 0 || this.entry.number > 2047) {{
            parserSummary.entity_delta_invalid_number_count++;
            send({{
                ok: false,
                event: 'entity-delta-invalid-number',
                timestamp_ms: Date.now(),
                packet_sequence: parserSummary.entity_delta_packet_sequence,
                entry: this.entry,
                recent: parserSummary.entity_delta_recent
            }});
        }}
    }}
}});

Interceptor.attach(cgEntityUpdate, {{
    onEnter(args) {{
        const entity = args[0];
        const entityArray = currentCgEntityArray();
        let entityNumber = null;
        if (entityArray !== null) {{
            const byteOffset = entity.sub(entityArray).toInt32();
            if (byteOffset >= 0 &&
                byteOffset < {CG_ENTITY_STRIDE * CG_ENTITY_COUNT} &&
                byteOffset % {CG_ENTITY_STRIDE} === 0) {{
                entityNumber = byteOffset / {CG_ENTITY_STRIDE};
            }}
        }}
        const encodedTarget = readU32(entity, 0x18);
        const encodedTargetSalt = readU32(entity, 0x1c);
        const key = readU32(cgEntitySecureOriginKey, 0);
        const originFieldAddress = entity.add(0x1c).toUInt32();
        const target = encodedTarget === null || key === null
            ? ptr(0) : ptr((encodedTarget ^ key ^ originFieldAddress) >>> 0);
        let executable = false;
        try {{
            const range = Process.findRangeByAddress(target);
            executable = range !== null && range.protection.indexOf('x') !== -1;
        }} catch (_) {{}}
        const call = {{
            entity: entity.toString(),
            entity_array: entityArray === null ? null : entityArray.toString(),
            entity_number: entityNumber,
            caller: this.returnAddress.toString(),
            caller_preferred: normalizeModuleAddress(this.returnAddress),
            target: target.toString(),
            target_preferred: normalizeModuleAddress(target),
            target_executable: executable,
            encoded_origin_function: encodedTarget,
            encoded_origin_function_salt: encodedTargetSalt,
            secure_origin_key: key,
            current_state: readEntityStateSummary(entity.add(0x74)),
            next_state: readEntityStateSummary(entity.add(0xf0)),
            thread_id: Process.getCurrentThreadId()
        }};
        parserSummary.entity_secure_origin_call_count++;
        parserSummary.entity_secure_origin_last_call = call;
        if (!executable) {{
            parserSummary.entity_secure_origin_invalid_target_count++;
            send({{
                ok: false,
                event: 'entity-secure-origin-invalid-target',
                timestamp_ms: Date.now(),
                call: call
            }});
        }}
    }}
}});
}}

function traceMessageParser(address, name, locateMessage) {{
    Interceptor.attach(address, {{
        onEnter(args) {{
            this.msg = locateMessage.call(this, args);
            parserSummary[name + '_enter_count']++;
            if (name === 'playerstate') {{
                parserSummary.playerstate_last_readcount_before =
                    readU32(this.msg, 0x1c);
                const splitStart = readU32(this.msg, 0x14);
                const splitLength = readU32(this.msg, 0x18);
                parserSummary.playerstate_last_readable_bytes =
                    splitStart === null || splitLength === null
                        ? null : splitStart + splitLength;
            }}
        }},
        onLeave(_) {{
            parserSummary[name + '_leave_count']++;
            if (name === 'playerstate')
                parserSummary.playerstate_last_readcount_after =
                    readU32(this.msg, 0x1c);
            if (readU32(this.msg, 0)) parserSummary.inner_overflow_observations++;
        }}
    }});
}}

function tracePlayerstateMilestone(address, name) {{
    Interceptor.attach(address, {{
        onEnter(_) {{
            const msg = this.context.esi;
            parserSummary['playerstate_' + name + '_count']++;
            parserSummary['playerstate_' + name + '_last_readcount'] =
                readU32(msg, 0x1c);
            parserSummary['playerstate_' + name + '_last_overflow'] =
                readU32(msg, 0);
        }}
    }});
}}

{parser_hooks}
Interceptor.attach(comError, {{
    onEnter(args) {{
        parserSummary.com_error_count++;
        parserSummary.last_com_error_format = readString(args[1]);
        parserSummary.last_com_error_argument = args[2].toInt32();
        send({{
            ok: false,
            event: 'com-error',
            timestamp_ms: Date.now(),
            caller: this.returnAddress.toString(),
            error_code: args[0].toInt32(),
            format: parserSummary.last_com_error_format,
            first_argument: parserSummary.last_com_error_argument
        }});
    }}
}});

const actionBindings = {{}};
for (const [name, spec] of Object.entries(actionBindingSpecs)) {{
    const downAction = resolveAction(spec.down_name);
    const upAction = spec.up_name === null ? null : resolveAction(spec.up_name);
    if (upAction !== null && upAction !== downAction + 1)
        throw new Error('binding action pair is not adjacent: ' + name);
    actionBindings[name] = {{
        down_action: downAction,
        up_action: upAction,
        key_code: spec.key_code
    }};
}}

function dispatch(actionName, transition, eventIndex, eventName) {{
    const binding = actionBindings[actionName];
    if (binding === undefined)
        throw new Error('scenario action was not resolved: ' + actionName);
    let actionId = binding.down_action;
    if (transition === 'up' || transition === 'release') {{
        if (binding.up_action === null)
            throw new Error('momentary action cannot be released: ' + actionName);
        actionId = binding.up_action;
    }} else if (transition === 'down') {{
        activeActions.set(actionName, binding);
    }}
    executeBindingAction(localClient, actionId, binding.key_code);
    if (transition === 'up' || transition === 'release')
        activeActions.delete(actionName);
    send({{
        ok: true,
        event: eventName,
        pid: Process.id,
        source: 'client-native-forced',
        thread_id: Process.getCurrentThreadId(),
        local_client: localClient,
        key_code: binding.key_code,
        action_id: actionId,
        action: actionName,
        transition: transition,
        scenario_event_index: eventIndex,
        scenario_elapsed_ms: scenarioStartedAt === 0 ? 0 : Date.now() - scenarioStartedAt
    }});
}}

function releaseActiveActions(eventName) {{
    for (const [actionName, binding] of Array.from(activeActions.entries())) {{
        try {{
            executeBindingAction(localClient, binding.up_action, binding.key_code);
            send({{
                ok: true,
                event: eventName,
                source: 'client-native-forced',
                action: actionName,
                transition: 'up',
                action_id: binding.up_action,
                key_code: binding.key_code
            }});
        }} catch (_) {{}}
        activeActions.delete(actionName);
    }}
}}

function currentCgame() {{
    const clientIndex = readU32(activeLocalClientIndex, 0);
    if (clientIndex === null || clientIndex > 15) return null;
    const encoded = readU32(encodedCgameGlobals, clientIndex * 4);
    if (encoded === null) return null;
    const cgame = ptr((encoded ^ {CGAME_POINTER_XOR}) >>> 0);
    return readU32(cgame, 0) === null ? null : cgame;
}}

function readOpaqueBytes(address, size) {{
    if (address === null || address.isNull()) return null;
    try {{ return address.readByteArray(size); }} catch (_) {{ return null; }}
}}

function readVec3(address, offset) {{
    try {{
        return [0, 1, 2].map(function(index) {{
            return address.add(offset + index * 4).readFloat();
        }});
    }} catch (_) {{
        return null;
    }}
}}

function readWorldPlayerSample() {{
    if (getWorldPlayerSampleV1 === null) return null;
    const sample = Memory.alloc({NATIVE_SAMPLE_CAPACITY});
    if (!getWorldPlayerSampleV1(localClient, sample, {NATIVE_SAMPLE_CAPACITY}))
        return null;
    const structSize = readU32(sample, 0);
    const schemaVersion = readU32(sample, 4);
    if (structSize === null || structSize < 8 || structSize > {NATIVE_SAMPLE_CAPACITY} ||
        schemaVersion === null)
        return null;
    const data = readOpaqueBytes(sample, structSize);
    if (data === null) return null;
    return {{
        kind: 'server-world-player-sample-v1',
        schema_version: schemaVersion,
        data: data
    }};
}}

function collectOpaqueEvidence() {{
    const chunks = [];
    const serverSample = readWorldPlayerSample();
    if (serverSample !== null) chunks.push(serverSample);
    const cgame = currentCgame();
    if (cgame !== null) {{
        const predicted = readOpaqueBytes(cgame, {CLIENT_PLAYER_STATE_SIZE});
        if (predicted !== null) chunks.push({{
            kind: 'client-predicted-playerstate',
            data: predicted
        }});
        const snapshot = readPointer(cgame, 0x3578);
        const snapshotState = readOpaqueBytes(snapshot, {CLIENT_PLAYER_STATE_SIZE});
        if (snapshotState !== null) chunks.push({{
            kind: 'client-snapshot-playerstate',
            data: snapshotState
        }});
    }}
    let totalSize = 0;
    const segments = [];
    for (const chunk of chunks) {{
        const size = chunk.data.byteLength;
        const segment = {{ kind: chunk.kind, offset: totalSize, size: size }};
        if (chunk.schema_version !== undefined)
            segment.schema_version = chunk.schema_version;
        segments.push(segment);
        totalSize += size;
    }}
    if (totalSize === 0) return {{ segments: [], data: null }};
    const combined = new Uint8Array(totalSize);
    for (let index = 0; index < chunks.length; ++index)
        combined.set(new Uint8Array(chunks[index].data), segments[index].offset);
    return {{ segments: segments, data: combined.buffer }};
}}

function collectStateProjection() {{
    const worldSampleCommandTimeOffset = 64;
    const worldSampleOriginOffset = 68;
    const worldSampleVelocityOffset = 80;
    const worldSampleProjectionSize = worldSampleVelocityOffset + 12;
    const clientPlayerStateOriginOffset = 0x1C;
    const projection = {{
        server: null,
        predicted: null,
        snapshot: null
    }};
    if (getWorldPlayerSampleV1 !== null) {{
        const sample = Memory.alloc({NATIVE_SAMPLE_CAPACITY});
        if (getWorldPlayerSampleV1(localClient, sample, {NATIVE_SAMPLE_CAPACITY}) &&
            readU32(sample, 0) >= worldSampleProjectionSize) {{
            projection.server = {{
                command_time: readU32(sample, worldSampleCommandTimeOffset),
                origin: readVec3(sample, worldSampleOriginOffset),
                velocity: readVec3(sample, worldSampleVelocityOffset)
            }};
        }}
    }}
    const cgame = currentCgame();
    if (cgame !== null) {{
        projection.predicted = {{
            command_time: readU32(cgame, 0),
            origin: readVec3(cgame, clientPlayerStateOriginOffset)
        }};
        const snapshot = readPointer(cgame, 0x3578);
        if (snapshot !== null) projection.snapshot = {{
            command_time: readU32(snapshot, 0),
            origin: readVec3(snapshot, clientPlayerStateOriginOffset)
        }};
    }}
    return projection;
}}

function sampleServer(force) {{
    const now = Date.now();
    if (!force && now - lastSampleAt < sampleIntervalMilliseconds) return;
    lastSampleAt = now;
    const evidence = collectOpaqueEvidence();
    send({{
        ok: true,
        event: 'server-sample',
        source: 'client-native-forced',
        sequence: sampleSequence++,
        timestamp_ms: now,
        phase: phase,
        scenario_event_index: nextScenarioEvent,
        scenario_elapsed_ms: scenarioStartedAt === 0 ? 0 : Date.now() - scenarioStartedAt,
        parser_summary: parserSummary,
        state_projection: collectStateProjection(),
        opaque_evidence_segments: evidence.segments
    }}, evidence.data);
}}

function finish(event, error) {{
    if (phase === 'done') return;
    phase = 'done';
    send({{
        ok: event === 'completed',
        event: event,
        source: 'client-native-forced',
        timestamp_ms: Date.now(),
        parser_summary: parserSummary,
        scenario_timing: scenarioTiming,
        error: error
    }});
}}

function complete() {{
    if (phase === 'done') return;
    releaseActiveActions('input-up-at-completion');
    sampleServer(true);
    finish('completed', null);
}}

function abort(reason) {{
    if (phase === 'done') return;
    releaseActiveActions('input-up-after-request');
    sampleServer(true);
    finish('aborted', reason);
}}

function fail(error) {{
    if (phase === 'done') return;
    releaseActiveActions('input-up-after-error');
    finish('error', error.stack || error.message);
}}

function runScenarioFrame() {{
    if (phase === 'pending-start') {{
        scenarioStartedAt = Date.now();
        phase = 'running';
    }}
    if (phase === 'release-requested') {{
        abort('release requested before scenario completion');
        return;
    }}
    if (phase !== 'running' && phase !== 'observing') return;

    const elapsed = Date.now() - scenarioStartedAt;
    if (nextScenarioEvent < scenario.events.length &&
        scenario.events[nextScenarioEvent].at_ms <= elapsed) {{
        const eventAt = scenario.events[nextScenarioEvent].at_ms;
        const drift = Math.max(0, elapsed - eventAt);
        scenarioTiming.max_event_drift_ms = Math.max(
            scenarioTiming.max_event_drift_ms, drift);
        while (nextScenarioEvent < scenario.events.length &&
            scenario.events[nextScenarioEvent].at_ms === eventAt) {{
            const eventIndex = nextScenarioEvent++;
            const event = scenario.events[eventIndex];
            const eventName = event.transition === 'activate'
                ? 'input-activate'
                : event.transition === 'down'
                ? 'input-down'
                : event.transition === 'release'
                ? 'input-release'
                : 'input-up';
            dispatch(event.action, event.transition, eventIndex, eventName);
        }}
        ++scenarioTiming.dispatched_event_group_count;
        sampleServer(true);
        if (nextScenarioEvent < scenario.events.length &&
            scenario.events[nextScenarioEvent].at_ms <= elapsed) {{
            ++scenarioTiming.overdue_event_group_count;
            scenarioTiming.valid = false;
        }}
    }}
    if (nextScenarioEvent === scenario.events.length)
        phase = 'observing';
    if (nextScenarioEvent === scenario.events.length &&
        elapsed >= scenario.duration_ms)
        complete();
}}

Interceptor.attach(comFrame, {{
    onEnter(_args) {{
        if (phase === 'done' || busy)
            return;
        busy = true;
        try {{
            runScenarioFrame();
            if (phase === 'running' || phase === 'observing')
                sampleServer(false);
        }} catch (error) {{
            fail(error);
        }} finally {{
            busy = false;
        }}
    }}
}});

phase = 'pending-start';

rpc.exports = {{
    requestrelease() {{
        if (phase !== 'done')
            phase = 'release-requested';
        return phase;
    }}
}};

send({{
    ok: true,
    event: 'armed',
    pid: Process.id,
    source: 'client-native-forced',
    module_base: module.base.toString(),
    module_path: module.path,
    plugin_path: plugin === null ? null : plugin.path,
    execute_binding_action: module.base.add({EXECUTE_BINDING_ACTION_RVA}).toString(),
    action_bindings: actionBindings,
    scenario: scenario,
{legacy_armed_fields}
    local_client: localClient,
    sample_interval: {sample_interval},
    server_sampling: {{
        plugin_loaded: plugin !== null,
        world_player_sample_v1: getWorldPlayerSampleV1 !== null,
        opaque_client_playerstate: true
    }},
    exception_handler: true,
    parser_trace: {str(trace_parser).lower()}
}});
"""


def prepare_opaque_sample(
    payload: dict[str, Any],
    data: bytes | None,
    expected_sequence: int,
) -> tuple[dict[str, Any], list[str]]:
    sample = dict(payload)
    if data is not None:
        sample[OPAQUE_DATA_KEY] = bytes(data)
    errors: list[str] = []
    sequence = sample.get("sequence")
    if not is_plain_int(sequence) or sequence != expected_sequence:
        errors.append(
            f"server sample sequence {sequence!r} does not match "
            f"expected {expected_sequence}"
        )
    errors.extend(
        f"server sample {expected_sequence} opaque evidence: {error}"
        for error in opaque_sample_details(sample)["errors"]
    )
    return sample, errors


def _record_terminal_payload(
    result: dict[str, object],
    payload: dict[str, Any],
    failure_latched: bool,
) -> None:
    event = payload.get("event")
    if failure_latched:
        result["late_terminal_event"] = event
        for key in ("parser_summary", "scenario_timing"):
            if key in payload:
                result[key] = payload[key]
        return
    result.update(payload)
    result["final_event"] = event
    result["ok"] = event == "completed"


def write_result_checkpoint(
    output: Path,
    result: dict[str, object],
    samples: list[dict[str, Any]],
    raw_samples: RawSampleCheckpoint | None = None,
) -> None:
    def write() -> None:
        if raw_samples is not None:
            raw_samples.checkpoint(samples)
        payload = {
            **result,
            "capture_summary": capture_summary(samples),
            "output": str(output),
        }
        if raw_samples is not None:
            payload["raw_samples"] = raw_samples.status()
        write_json_checkpoint(output, payload)

    if raw_samples is None:
        write()
    else:
        with raw_samples.lock:
            write()


def raw_sample_checkpoint_path(output: Path) -> Path:
    return output.with_suffix(".samples.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=tuple(ACTION_NAMES))
    parser.add_argument(
        "--scenario",
        type=Path,
        help="Run a versioned JSON action timeline instead of one positional action",
    )
    parser.add_argument(
        "--scenario-sha256",
        help="Require --scenario bytes to match this parent-recorded SHA-256",
    )
    parser.add_argument("--pid", type=int)
    parser.add_argument("--local-client", type=int, default=0)
    parser.add_argument("--hold-seconds", type=float, default=1.0)
    parser.add_argument("--observe-seconds", type=float, default=1.0)
    parser.add_argument("--sample-interval", type=float, default=0.05)
    parser.add_argument(
        "--no-parser-trace", action="store_true",
        help="avoid packet/parser hooks for low-interference input smoke tests",
    )
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--summarize-raw",
        type=Path,
        help="Validate a saved raw-sample checkpoint without attaching",
    )
    args = parser.parse_args()
    if args.summarize_raw is not None:
        if (
            args.action is not None
            or args.scenario is not None
            or args.scenario_sha256 is not None
        ):
            parser.error("--summarize-raw cannot be combined with an action or --scenario")
        try:
            offline_result = summarize_raw_sample_checkpoint(args.summarize_raw)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        if args.output is not None:
            output = args.output.resolve()
            if output == args.summarize_raw.resolve():
                parser.error("--output cannot overwrite the raw sample checkpoint")
            offline_result["output"] = str(output)
            write_json_checkpoint(output, offline_result)
        print(json.dumps(offline_result, ensure_ascii=False, indent=2))
        return 0
    if (args.action is None) == (args.scenario is None):
        parser.error("provide exactly one positional action or --scenario")
    if args.scenario_sha256 is not None and args.scenario is None:
        parser.error("--scenario-sha256 requires --scenario")
    if not 0 <= args.local_client < 2:
        parser.error("--local-client must be 0 or 1")
    if args.hold_seconds < 0:
        parser.error("--hold-seconds cannot be negative")
    if args.observe_seconds < 0:
        parser.error("--observe-seconds cannot be negative")
    if args.sample_interval <= 0:
        parser.error("--sample-interval must be positive")
    try:
        if args.scenario is not None:
            scenario, scenario_document = load_scenario_document(args.scenario)
            scenario_source_sha256 = hashlib.sha256(scenario_document).hexdigest()
            if (
                args.scenario_sha256 is not None
                and scenario_source_sha256 != args.scenario_sha256.casefold()
            ):
                parser.error(
                    "--scenario SHA-256 does not match the parent-recorded snapshot"
                )
        else:
            assert args.action is not None
            scenario = single_action_scenario(
                args.action, args.hold_seconds, args.observe_seconds
            )
            scenario_source_sha256 = None
    except ValueError as error:
        parser.error(str(error))
    scenario_seconds = scenario_duration_seconds(scenario)
    if args.timeout is None:
        args.timeout = max(10.0, scenario_seconds + 5.0)
    if args.timeout <= scenario_seconds:
        parser.error("--timeout must exceed the scenario duration")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    output = args.output.resolve() if args.output is not None else None
    raw_samples = (
        RawSampleCheckpoint(raw_sample_checkpoint_path(output), scenario)
        if output is not None
        else None
    )
    session = device.attach(pid)
    done = threading.Event()
    result: dict[str, object] = {
        "events": [],
        "process_exited": False,
        "capture_integrity_ok": True,
        "capture_errors": [],
        "scenario": scenario,
        "scenario_source": (
            str(args.scenario.resolve()) if args.scenario is not None else "legacy-action"
        ),
        "scenario_source_sha256": scenario_source_sha256,
    }
    samples: list[dict[str, Any]] = []
    last_checkpoint = 0.0
    timeout_latched = False
    capture_failure_latched = False
    state_lock = threading.RLock()
    script = session.create_script(
        build_scenario_script(
            scenario,
            args.local_client,
            args.sample_interval,
            legacy_action=args.action,
            legacy_hold_seconds=(args.hold_seconds if args.action is not None else None),
            legacy_observe_seconds=(
                args.observe_seconds if args.action is not None else None
            ),
            trace_parser=not args.no_parser_trace,
        )
    )

    def latch_capture_error(message: str) -> None:
        nonlocal capture_failure_latched
        capture_failure_latched = True
        errors = result["capture_errors"]
        assert isinstance(errors, list)
        if message not in errors:
            errors.append(message)
        result["capture_integrity_ok"] = False
        result["ok"] = False

    def checkpoint(force: bool = False) -> None:
        nonlocal last_checkpoint
        with state_lock:
            if output is None:
                return
            now = time.monotonic()
            if not force and now - last_checkpoint < 0.25:
                return
            write_result_checkpoint(output, result, samples, raw_samples)
            last_checkpoint = now

    def on_message(message: dict, _data: bytes | None) -> None:
        if message.get("type") == "error":
            with state_lock:
                description = str(
                    message.get("description")
                    or message.get("stack")
                    or "Frida script error"
                )
                latch_capture_error(description)
                result.update(
                    final_event="script-error",
                    error=description,
                )
                checkpoint(force=True)
                done.set()
            return
        payload = message.get("payload", message)
        if not isinstance(payload, dict):
            return
        with state_lock:
            if payload.get("event") == "server-sample":
                sample, sample_errors = prepare_opaque_sample(
                    payload, _data, len(samples)
                )
                for error in sample_errors:
                    latch_capture_error(error)
                samples.append(sample)
                result["last_sample_phase"] = sample.get("phase")
                parser_summary = sample.get("parser_summary")
                if isinstance(parser_summary, dict):
                    result["parser_summary"] = parser_summary
                checkpoint()
                return
            events = result["events"]
            assert isinstance(events, list)
            events.append(payload)
            event = payload.get("event")
            if event == "armed":
                result.update(payload)
                checkpoint(force=True)
            elif event in {"input-up", "input-up-after-error"}:
                result["final_event"] = event
                checkpoint(force=True)
            elif event in {"completed", "aborted", "error"}:
                _record_terminal_payload(result, payload, timeout_latched)
                if capture_failure_latched:
                    result["ok"] = False
                checkpoint(force=True)
                done.set()

    def on_detached(reason: str, crash: object | None) -> None:
        with state_lock:
            if done.is_set():
                return
            result.update(
                ok=False,
                final_event="process-detached",
                process_exited=reason == "process-terminated",
                detach_reason=reason,
                crash=None if crash is None else str(crash),
            )
            checkpoint(force=True)
            done.set()

    def wait_for_terminal(timeout_seconds: float) -> bool:
        return done.wait(timeout_seconds)

    session.on("detached", on_detached)
    script.on("message", on_message)
    try:
        script.load()
        if not wait_for_terminal(args.timeout):
            release_requested = False
            with state_lock:
                if not done.is_set():
                    timeout_latched = True
                    release_requested = True
                    result.update(
                        ok=False,
                        final_event="timeout-release-requested",
                        error="timed out waiting for the input action; release was requested",
                    )
                    checkpoint(force=True)
            if release_requested:
                try:
                    script.exports_sync.requestrelease()
                except frida.InvalidOperationError:
                    pass
                if not wait_for_terminal(2.0):
                    with state_lock:
                        if not done.is_set():
                            result.update(
                                ok=False,
                                final_event="timeout-release-pending",
                                error=(
                                    "timed out waiting for input release on the client "
                                    "main thread"
                                ),
                            )
                            checkpoint(force=True)
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass

    with state_lock:
        if result.get("process_exited"):
            result["process_alive_after_observation"] = False
        else:
            try:
                result["process_alive_after_observation"] = any(
                    process.pid == pid for process in device.enumerate_processes()
                )
            except frida.Error as error:
                result["process_alive_after_observation"] = False
                result["process_check_error"] = str(error)
        if not result["process_alive_after_observation"]:
            result["process_exited"] = True
            result["ok"] = False
        result["capture_summary"] = capture_summary(samples)
        if output is not None:
            result["output"] = str(output)
            checkpoint(force=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") and result.get("final_event") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
