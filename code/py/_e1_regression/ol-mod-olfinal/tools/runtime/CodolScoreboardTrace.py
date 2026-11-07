#!/usr/bin/env python3
"""Observe CODOL scoreboard command, mirror, and Scaleform boundaries."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime


configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
ACTIVE_LOCAL_CLIENT_INDEX_RVA = 0x7417BA8
ENCODED_CGAME_GLOBALS_RVA = 0x1619510
CGAME_POINTER_XOR = 0xFBB2C97A
CG_SERVER_COMMAND_RVA = 0x17D560
CG_UPDATE_SCORE_RVA = 0x178CC0
CG_COPY_SCOREBOARD_TO_UI_RVA = 0x1788F0
CG_POPULATE_SCOREBOARD_UI_RVA = 0x1C3870
CG_SCORE_VIEW_UPDATE_SCORE_RVA = 0x1D64C0
CG_SCORE_VIEW_TIMER_SUBTRACT_RVA = 0x1D6651
CG_SCORE_VIEW_INITIALIZE_RVA = 0x1D58E0
CG_SCORE_VIEW_UPDATE_RVA = 0x1D6ED0
CG_VIEW_MANAGER_UPDATE_RVA = 0x2BA0D0
CG_INGAME_GFX_INITIALIZE_RVA = 0x2BB1F0
CG_REGISTER_COMMON_AS_FUNCTIONS_RVA = 0x2A27C0
CG_REGISTER_SCORE_VIEW_AS_FUNCTION_RVA = 0x2A9A20
CG_REGISTER_SANDD_VIEW_AS_FUNCTION_RVA = 0x2A9B80
CG_SANDD_VIEW_INITIALIZE_RVA = 0x1D4A40
CG_SANDD_VIEW_BUILD_STATE_RVA = 0x1D4C90
DVAR_FIND_VAR_RVA = 0x232440
DVAR_SET_VARIANT_RVA = 0x232150
DVAR_SET_FROM_STRING_RVA = 0x234500
CL_SYSTEM_INFO_CHANGED_RVA = 0x06D860
CL_GET_CONFIG_STRING_RVA = 0x0F9850
CG_SCORE_VIEW_READY_RVA = 0xB1F3394
CG_SANDD_VIEW_READY_RVA = 0xB1F30A8
CG_SANDD_MODE_GATE_RVA = 0x8E5397
CGAME_SCORE_COUNT_OFFSET = 0xBC868
CGAME_AXIS_SCORE_OFFSET = 0xBC870
CGAME_ALLIES_SCORE_OFFSET = 0xBC874
CGAME_CLIENT_INFO_BASE_OFFSET = 0x15DEA8
CGAME_CLIENT_INFO_STRIDE = 0x3B8
CGAME_CLIENT_INFO_NAME_POINTER_OFFSET = 0x0C
CGAME_CLIENT_INFO_NAME_LENGTH_OFFSET = 0x70
CGAME_CLIENT_INFO_NAME_KEY_RVA = 0x8E4708
UI_SCORE_COUNT_RVA = 0x2B25368
UI_AXIS_SCORE_RVA = 0x2B25320
UI_ALLIES_SCORE_RVA = 0x2B25324
PLAYLIST_ENTRY_ZERO_RVA = 0x2DFE618
PLAYLIST_ENTRY_STRIDE = 15272
PLAYLIST_RULES_OFFSET = 320
PLAYLIST_PRESENT_OFFSET = 15000
PLAYLIST_ENABLED_OFFSET = 15069
PLAYLIST_RULE_FILTER_A_RVA = 0x1632368
PLAYLIST_RULE_FILTER_B_RVA = 0x16323C4
CONFIGSTRING_DVAR_NAME_BASE = 24
CONFIGSTRING_DVAR_VALUE_BASE = 344
CONFIGSTRING_DVAR_COUNT = 320
PLAYER_NAME_CONFIGSTRING_BASE = 1975
PLAYER_NAME_CONFIGSTRING_COUNT = 18


def build_script(
    playlist_slot: int = 26,
    playlist_raw_index: int = 133,
    install_observers: bool = True,
    install_systeminfo_observers: bool = False,
) -> str:
    observers_enabled = str(install_observers).lower()
    systeminfo_observers_enabled = str(install_systeminfo_observers).lower()
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const activeLocalClientIndex = module.base.add({ACTIVE_LOCAL_CLIENT_INDEX_RVA});
const encodedCgameGlobals = module.base.add({ENCODED_CGAME_GLOBALS_RVA});
const playlistEntryZero = module.base.add({PLAYLIST_ENTRY_ZERO_RVA});
const counts = {{
    server_command: 0,
    update_score: 0,
    copy_scoreboard_to_ui: 0,
    populate_scoreboard_ui: 0,
    score_view_initialize: 0,
    score_view_update: 0,
    view_manager_update: 0,
    score_view_update_score: 0,
    ingame_gfx_initialize: 0,
    register_common_as_functions: 0,
    register_score_view_as_function: 0,
    register_sandd_view_as_function: 0,
    sandd_view_initialize: 0,
    sandd_view_build_state: 0
}};
const last = {{}};
let scoreViewTimer = null;
let sanddViewState = null;
const systeminfoTimeline = [];
const targetSysteminfoDvars = new Set([
    'ui_scorelimit', 'ui_timelimit', 'ui_halftime'
]);

function readU32(address) {{ try {{ return address.readU32(); }} catch (_) {{ return null; }} }}
function readS32(address) {{ try {{ return address.readS32(); }} catch (_) {{ return null; }} }}
function readU8(address) {{ try {{ return address.readU8(); }} catch (_) {{ return null; }} }}
function readUtf8(address) {{
    try {{ return address.isNull() ? null : address.readUtf8String(); }} catch (_) {{ return null; }}
}}

function readCStringHex(address, maximum = 64) {{
    try {{
        if (address.isNull()) return null;
        const bytes = [];
        for (let offset = 0; offset < maximum; ++offset) {{
            const value = address.add(offset).readU8();
            if (value === 0) break;
            bytes.push(value.toString(16).padStart(2, '0'));
        }}
        return bytes.join('');
    }} catch (_) {{ return null; }}
}}

function readPlaylistSlot(slot) {{
    let ordinal = 0;
    for (let rawIndex = 0; rawIndex < 256; ++rawIndex) {{
        const entry = playlistEntryZero.add(rawIndex * {PLAYLIST_ENTRY_STRIDE});
        const present = readU32(entry.add({PLAYLIST_PRESENT_OFFSET}));
        const enabled = readU8(entry.add({PLAYLIST_ENABLED_OFFSET}));
        if (!present || !enabled) continue;
        if (ordinal === slot) {{
            const words = [];
            for (let offset = {PLAYLIST_PRESENT_OFFSET} - 8;
                 offset <= {PLAYLIST_PRESENT_OFFSET} + 20; offset += 4) {{
                words.push({{ offset: offset, value: readU32(entry.add(offset)) }});
            }}
            return {{
                slot: slot,
                raw_index: rawIndex,
                address: entry.toString(),
                name: readUtf8(entry),
                rules: readUtf8(entry.add({PLAYLIST_RULES_OFFSET})),
                present_raw: present,
                enabled_raw: enabled,
                words_near_present: words
            }};
        }}
        ++ordinal;
    }}
    return {{ slot: slot, raw_index: null, enabled_count: ordinal }};
}}

function readPlaylistCatalog() {{
    const entries = [];
    for (let rawIndex = 0; rawIndex < 256; ++rawIndex) {{
        const entry = playlistEntryZero.add(rawIndex * {PLAYLIST_ENTRY_STRIDE});
        const present = readU32(entry.add({PLAYLIST_PRESENT_OFFSET}));
        const enabled = readU8(entry.add({PLAYLIST_ENABLED_OFFSET}));
        if (!present || !enabled) continue;
        entries.push({{
            slot: entries.length,
            raw_index: rawIndex,
            name: readUtf8(entry),
            rules: readUtf8(entry.add({PLAYLIST_RULES_OFFSET})),
            present_raw: present
        }});
    }}
    return entries;
}}

function readPlaylistRaw(rawIndex) {{
    const entry = playlistEntryZero.add(rawIndex * {PLAYLIST_ENTRY_STRIDE});
    return {{
        raw_index: rawIndex,
        address: entry.toString(),
        name: readUtf8(entry),
        rules: readUtf8(entry.add({PLAYLIST_RULES_OFFSET})),
        present_raw: readU32(entry.add({PLAYLIST_PRESENT_OFFSET})),
        enabled_raw: readU8(entry.add({PLAYLIST_ENABLED_OFFSET}))
    }};
}}

function readDvarNameFromPointerSlot(rva) {{
    try {{
        const dvar = module.base.add(rva).readPointer();
        return {{ address: dvar.toString(), name: readUtf8(dvar.readPointer()) }};
    }} catch (error) {{
        return {{ error: error.message }};
    }}
}}

const dvarFindVar = new NativeFunction(
    module.base.add({DVAR_FIND_VAR_RVA}), 'pointer', ['pointer']);
const clGetConfigString = new NativeFunction(
    module.base.add({CL_GET_CONFIG_STRING_RVA}), 'pointer', ['uint'], 'fastcall');

function readDvar(name) {{
    try {{
        const dvar = dvarFindVar(Memory.allocUtf8String(name));
        if (dvar.isNull()) return null;
        const type = dvar.add(8).readU8();
        const current = dvar.add(12);
        let value = current.readU32();
        if (type === 0) value = current.readU8() !== 0;
        else if (type === 1) value = current.readFloat();
        else if (type === 5) value = current.readS32();
        else if (type === 6) {{
            const index = current.readU32();
            const count = dvar.add(60).readU32();
            const values = dvar.add(64).readPointer();
            value = index < count && !values.isNull()
                ? readUtf8(values.add(index * Process.pointerSize).readPointer())
                : index;
        }} else if (type === 7) {{
            value = readUtf8(current.readPointer());
        }}
        return {{
            address: dvar.toString(),
            flags: dvar.add(4).readU16(),
            type: type,
            value: value
        }};
    }} catch (error) {{
        return {{ error: error.message }};
    }}
}}

function readDvarAt(dvar) {{
    try {{
        if (dvar.isNull()) return null;
        const name = readUtf8(dvar.readPointer());
        if (name === null) return null;
        const result = readDvar(name);
        if (result !== null) result.name = name;
        return result;
    }} catch (_) {{
        return null;
    }}
}}

function targetDvarValues() {{
    return {{
        ui_scorelimit: readDvar('ui_scorelimit'),
        ui_timelimit: readDvar('ui_timelimit'),
        ui_halftime: readDvar('ui_halftime')
    }};
}}

function readTargetConfigStringDvarPairs() {{
    const pairs = [];
    for (let slot = 0; slot < {CONFIGSTRING_DVAR_COUNT}; ++slot) {{
        const nameIndex = {CONFIGSTRING_DVAR_NAME_BASE} + slot;
        const name = readUtf8(clGetConfigString(nameIndex));
        if (name === null || !targetSysteminfoDvars.has(name)) continue;
        const valueIndex = {CONFIGSTRING_DVAR_VALUE_BASE} + slot;
        pairs.push({{
            slot: slot,
            name_index: nameIndex,
            value_index: valueIndex,
            name: name,
            value: readUtf8(clGetConfigString(valueIndex))
        }});
    }}
    return pairs;
}}

function readPlayerNameConfigStrings() {{
    const values = [];
    for (let clientNum = 0; clientNum < {PLAYER_NAME_CONFIGSTRING_COUNT}; ++clientNum) {{
        const address = clGetConfigString(
            {PLAYER_NAME_CONFIGSTRING_BASE} + clientNum);
        const valueHex = readCStringHex(address);
        if (valueHex !== null && valueHex.length !== 0) {{
            values.push({{
                client_num: clientNum,
                value: readUtf8(address),
                value_hex: valueHex
            }});
        }}
    }}
    return values;
}}

function appendSysteminfoEvent(event) {{
    if (systeminfoTimeline.length >= 256) return;
    event.timestamp_ms = Date.now();
    systeminfoTimeline.push(event);
}}

function currentCgame() {{
    const localClient = readU32(activeLocalClientIndex);
    if (localClient === null || localClient > 15) return null;
    const encoded = readU32(encodedCgameGlobals.add(localClient * 4));
    if (encoded === null) return null;
    const value = ptr((encoded ^ {CGAME_POINTER_XOR}) >>> 0);
    return readU32(value) === null ? null : value;
}}

function rotateLeft32(value, count) {{
    return ((value << count) | (value >>> (32 - count))) >>> 0;
}}

function readClientInfoName(source) {{
    try {{
        const length = readU32(source.add({CGAME_CLIENT_INFO_NAME_LENGTH_OFFSET}));
        if (length === null || length > 64) return null;
        if (length === 0) return '';
        const encrypted = source.add(
            {CGAME_CLIENT_INFO_NAME_POINTER_OFFSET}).readPointer();
        if (encrypted.isNull()) return null;
        const key = module.base.add({CGAME_CLIENT_INFO_NAME_KEY_RVA});
        const fullWordBytes = (length >>> 2) * 4;
        const bytes = [];
        let offset = 0;
        while (offset + 4 <= length) {{
            const decoded = rotateLeft32(
                (encrypted.add(offset).readU32() ^ key.add(offset).readU32()) >>> 0,
                16);
            bytes.push(
                decoded & 0xFF,
                (decoded >>> 8) & 0xFF,
                (decoded >>> 16) & 0xFF,
                (decoded >>> 24) & 0xFF);
            offset += 4;
        }}
        while (offset < length) {{
            const value = encrypted.add(offset).readU8() ^
                key.add(fullWordBytes + offset).readU8();
            bytes.push(((value << 4) | (value >>> 4)) & 0xFF);
            ++offset;
        }}
        return String.fromCharCode.apply(null, bytes);
    }} catch (_) {{ return null; }}
}}

function readScoreboardClientSources(cgame) {{
    if (cgame === null) return [];
    const clients = [];
    for (let clientNum = 0; clientNum < 19; ++clientNum) {{
        const source = cgame.add({CGAME_CLIENT_INFO_BASE_OFFSET} +
            clientNum * {CGAME_CLIENT_INFO_STRIDE});
        const connected = readS32(source);
        if (!connected) continue;
        clients.push({{
            client_num: clientNum,
            connected: connected,
            team: readS32(source.add(8)),
            name_length: readU32(source.add({CGAME_CLIENT_INFO_NAME_LENGTH_OFFSET})),
            name: readClientInfoName(source)
        }});
    }}
    return clients;
}}

function sample(reason) {{
    const cgame = currentCgame();
    return {{
        reason: reason,
        timestamp_ms: Date.now(),
        cgame: cgame === null ? null : {{
            address: cgame.toString(),
            score_count: readS32(cgame.add({CGAME_SCORE_COUNT_OFFSET})),
            axis_score: readS32(cgame.add({CGAME_AXIS_SCORE_OFFSET})),
            allies_score: readS32(cgame.add({CGAME_ALLIES_SCORE_OFFSET})),
            client_sources: readScoreboardClientSources(cgame)
        }},
        ui: {{
            score_count: readS32(module.base.add({UI_SCORE_COUNT_RVA})),
            axis_score: readS32(module.base.add({UI_AXIS_SCORE_RVA})),
            allies_score: readS32(module.base.add({UI_ALLIES_SCORE_RVA})),
            score_view_ready: readU32(module.base.add({CG_SCORE_VIEW_READY_RVA})),
            sandd_view_ready: readU32(module.base.add({CG_SANDD_VIEW_READY_RVA}))
        }},
        dvars: {{
            g_gametype: readDvar('g_gametype'),
            ui_gametype: readDvar('ui_gametype'),
            ui_enable_hudkit: readDvar('ui_enable_hudkit'),
            ui_played_mapname: readDvar('ui_played_mapname'),
            ui_scorelimit: readDvar('ui_scorelimit'),
            ui_timelimit: readDvar('ui_timelimit'),
            ui_halftime: readDvar('ui_halftime')
        }},
        serverinfo_configstring: readUtf8(clGetConfigString(0)),
        systeminfo_configstring: readUtf8(clGetConfigString(1)),
        player_name_configstrings: readPlayerNameConfigStrings(),
        target_configstring_dvar_pairs: readTargetConfigStringDvarPairs(),
        playlist: readPlaylistSlot({playlist_slot}),
        playlist_catalog: readPlaylistCatalog(),
        playlist_raw: readPlaylistRaw({playlist_raw_index}),
        playlist_rule_filters: [
            readDvarNameFromPointerSlot({PLAYLIST_RULE_FILTER_A_RVA}),
            readDvarNameFromPointerSlot({PLAYLIST_RULE_FILTER_B_RVA})
        ]
    }};
}}

function observe(name, rva) {{
    Interceptor.attach(module.base.add(rva), {{
        onEnter() {{
            counts[name] += 1;
            this.before = sample(name + ':enter');
        }},
        onLeave() {{
            last[name] = {{ before: this.before, after: sample(name + ':leave') }};
        }}
    }});
}}

if ({observers_enabled}) {{
observe('server_command', {CG_SERVER_COMMAND_RVA});
observe('update_score', {CG_UPDATE_SCORE_RVA});
observe('copy_scoreboard_to_ui', {CG_COPY_SCOREBOARD_TO_UI_RVA});
observe('populate_scoreboard_ui', {CG_POPULATE_SCOREBOARD_UI_RVA});
observe('score_view_initialize', {CG_SCORE_VIEW_INITIALIZE_RVA});
observe('score_view_update', {CG_SCORE_VIEW_UPDATE_RVA});
observe('view_manager_update', {CG_VIEW_MANAGER_UPDATE_RVA});
observe('score_view_update_score', {CG_SCORE_VIEW_UPDATE_SCORE_RVA});
observe('ingame_gfx_initialize', {CG_INGAME_GFX_INITIALIZE_RVA});
observe('register_common_as_functions', {CG_REGISTER_COMMON_AS_FUNCTIONS_RVA});
observe('register_score_view_as_function', {CG_REGISTER_SCORE_VIEW_AS_FUNCTION_RVA});
observe('register_sandd_view_as_function', {CG_REGISTER_SANDD_VIEW_AS_FUNCTION_RVA});
observe('sandd_view_initialize', {CG_SANDD_VIEW_INITIALIZE_RVA});

Interceptor.attach(module.base.add({CG_SANDD_VIEW_BUILD_STATE_RVA}), {{
    onEnter() {{
        counts.sandd_view_build_state += 1;
        this.output = this.context.edi;
        this.cgame = this.context.esi;
        const teamSource = this.cgame.add(0x16bd50);
        const enemySource = this.cgame.add(0x16bd5c);
        this.before = {{
            cgame: this.cgame.toString(),
            mode_gate: readU8(module.base.add({CG_SANDD_MODE_GATE_RVA})),
            blocked_state: readS32(this.cgame.add(0xc6fe8)),
            team_source_pointer: readU32(teamSource),
            team_source_score: readU8(teamSource.add(4)),
            enemy_source_pointer: readU32(enemySource),
            enemy_source_score: readU8(enemySource.add(4))
        }};
    }},
    onLeave() {{
        sanddViewState = {{
            before: this.before,
            output: {{
                team_score: readS32(this.output),
                enemy_score: readS32(this.output.add(4)),
                visible: readU8(this.output.add(8))
            }}
        }};
    }}
}});

Interceptor.attach(module.base.add({CG_SCORE_VIEW_TIMER_SUBTRACT_RVA}), {{
    onEnter() {{
        const clientTime = readS32(this.context.esi.add(0xec));
        const snapshotTime = readS32(this.context.eax.add(0x352c));
        scoreViewTimer = {{
            timestamp_ms: Date.now(),
            client_active: this.context.esi.toString(),
            snapshot: this.context.eax.toString(),
            client_time: clientTime,
            snapshot_time: snapshotTime,
            elapsed_ms: clientTime === null || snapshotTime === null
                ? null
                : clientTime - snapshotTime
        }};
    }}
}});
}}

if ({systeminfo_observers_enabled}) {{
let lastPolledValues = JSON.stringify(targetDvarValues());
appendSysteminfoEvent({{
    event: 'armed',
    values: targetDvarValues(),
    systeminfo: readUtf8(clGetConfigString(1))
}});

Interceptor.attach(module.base.add({CL_SYSTEM_INFO_CHANGED_RVA}), {{
    onEnter() {{
        appendSysteminfoEvent({{
            event: 'systeminfo_enter',
            thread_id: Process.getCurrentThreadId(),
            values: targetDvarValues(),
            systeminfo: readUtf8(clGetConfigString(1))
        }});
    }},
    onLeave() {{
        appendSysteminfoEvent({{
            event: 'systeminfo_leave',
            thread_id: Process.getCurrentThreadId(),
            values: targetDvarValues(),
            systeminfo: readUtf8(clGetConfigString(1))
        }});
    }}
}});

Interceptor.attach(module.base.add({DVAR_SET_FROM_STRING_RVA}), {{
    onEnter() {{
        const dvar = this.context.esi;
        const state = readDvarAt(dvar);
        this.target = state !== null && targetSysteminfoDvars.has(state.name);
        if (!this.target) return;
        this.dvar = dvar;
        appendSysteminfoEvent({{
            event: 'set_from_string_enter',
            thread_id: Process.getCurrentThreadId(),
            caller_rva: this.returnAddress.sub(module.base).toString(),
            dvar: state,
            requested_value: readUtf8(this.context.esp.add(4).readPointer()),
            source: readS32(this.context.esp.add(8))
        }});
    }},
    onLeave(retval) {{
        if (!this.target) return;
        appendSysteminfoEvent({{
            event: 'set_from_string_leave',
            thread_id: Process.getCurrentThreadId(),
            dvar: readDvarAt(this.dvar),
            return_value: retval.toString()
        }});
    }}
}});

Interceptor.attach(module.base.add({DVAR_SET_VARIANT_RVA}), {{
    onEnter(args) {{
        const state = readDvarAt(args[0]);
        this.target = state !== null && targetSysteminfoDvars.has(state.name);
        if (!this.target) return;
        this.dvar = args[0];
        appendSysteminfoEvent({{
            event: 'set_variant_enter',
            thread_id: Process.getCurrentThreadId(),
            caller_rva: this.returnAddress.sub(module.base).toString(),
            dvar: state,
            source: args[5].toInt32(),
            variant_words: [
                args[1].toString(), args[2].toString(),
                args[3].toString(), args[4].toString()
            ]
        }});
    }},
    onLeave(retval) {{
        if (!this.target) return;
        appendSysteminfoEvent({{
            event: 'set_variant_leave',
            thread_id: Process.getCurrentThreadId(),
            dvar: readDvarAt(this.dvar),
            return_value: retval.toString()
        }});
    }}
}});

setInterval(function () {{
    const values = targetDvarValues();
    const encoded = JSON.stringify(values);
    if (encoded === lastPolledValues) return;
    lastPolledValues = encoded;
    appendSysteminfoEvent({{ event: 'poll_change', values: values }});
}}, 100);
}}

rpc.exports = {{
    capture() {{
        return {{
            ok: true,
            pid: Process.id,
            module_base: module.base.toString(),
            counts: {{ ...counts }},
            last: {{ ...last }},
            score_view_timer: scoreViewTimer,
            sandd_view_state: sanddViewState,
            systeminfo_timeline: systeminfoTimeline.slice(),
            current: sample('capture')
        }};
    }}
}};
"""


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    current = result.get("current", {})
    cgame = current.get("cgame") or {}
    ui = current.get("ui") or {}
    score_fields = ("score_count", "axis_score", "allies_score")
    comparable = all(cgame.get(field) is not None and ui.get(field) is not None for field in score_fields)
    return {
        "server_command_count": result.get("counts", {}).get("server_command", 0),
        "update_score_count": result.get("counts", {}).get("update_score", 0),
        "copy_scoreboard_to_ui_count": result.get("counts", {}).get("copy_scoreboard_to_ui", 0),
        "populate_scoreboard_ui_count": result.get("counts", {}).get("populate_scoreboard_ui", 0),
        "score_view_initialize_count": result.get("counts", {}).get("score_view_initialize", 0),
        "score_view_update_count": result.get("counts", {}).get("score_view_update", 0),
        "view_manager_update_count": result.get("counts", {}).get("view_manager_update", 0),
        "score_view_update_score_count": result.get("counts", {}).get("score_view_update_score", 0),
        "ingame_gfx_initialize_count": result.get("counts", {}).get("ingame_gfx_initialize", 0),
        "register_common_as_functions_count": result.get("counts", {}).get("register_common_as_functions", 0),
        "register_score_view_as_function_count": result.get("counts", {}).get("register_score_view_as_function", 0),
        "register_sandd_view_as_function_count": result.get("counts", {}).get("register_sandd_view_as_function", 0),
        "sandd_view_initialize_count": result.get("counts", {}).get("sandd_view_initialize", 0),
        "sandd_view_build_state_count": result.get("counts", {}).get("sandd_view_build_state", 0),
        "score_view_elapsed_ms": (result.get("score_view_timer") or {}).get("elapsed_ms"),
        "score_mirror_comparable": comparable,
        "score_mirror_equal": comparable and all(cgame[field] == ui[field] for field in score_fields),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=12.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--playlist-slot", type=int, default=26)
    parser.add_argument("--playlist-raw-index", type=int, default=133)
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="read current state without installing function hooks",
    )
    parser.add_argument(
        "--systeminfo-trace",
        action="store_true",
        help="trace only native systeminfo application and target dvar changes",
    )
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if not 0 <= args.playlist_slot <= 255:
        parser.error("--playlist-slot must be between 0 and 255")
    if not 0 <= args.playlist_raw_index <= 255:
        parser.error("--playlist-raw-index must be between 0 and 255")
    if args.sample_only and args.systeminfo_trace:
        parser.error("--sample-only and --systeminfo-trace are mutually exclusive")

    device = frida.get_local_device()
    session = device.attach(args.pid)
    try:
        script = session.create_script(
            build_script(
                args.playlist_slot,
                args.playlist_raw_index,
                install_observers=not args.sample_only and not args.systeminfo_trace,
                install_systeminfo_observers=args.systeminfo_trace,
            )
        )
        script.load()
        time.sleep(args.seconds)
        result = script.exports_sync.capture()
    finally:
        session.detach()
    result["summary"] = summarize(result)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
