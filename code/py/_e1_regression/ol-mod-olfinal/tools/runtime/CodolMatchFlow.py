#!/usr/bin/env python3
"""Drive CODOL's native quick-match and ready flow, then observe allocation."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import threading
import time
from ctypes import wintypes

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


GAME_WINDOW_CLASS = "CODO"

# EVERY ADDRESS AND EVERY STRUCT OFFSET BELOW IS PER BUILD, and this file drives the client by
# CALLING ITS OWN FUNCTIONS, so a stale entry is not a failed lookup -- it is a call through a
# wrong pointer into a live game process.
#
# The 1649370 column was derived in the CODOL-main tree and the evidence for each entry is in
# re/olfinal/matchflow-1649370.json.  Three things are worth knowing before editing it:
#
#  * The room manager GREW between the builds.  Its fields did not move by a common delta --
#    ROOM_SINGLETON -> ROOM_MATCH_CALLBACKS is +0xEC on 3.3.3.3 and +0x120 here -- so the four
#    room globals were each ported independently rather than derived from the first.
#  * The profile blob moved too, and not uniformly: three of its fields moved +0x8010 and
#    PUBLIC_PROFILE_PARSED_OFFSET moved +0x8014.  Assuming one delta would be four bytes wrong.
#  * CBUF_ADD_TEXT is INLINED on 1649370 -- 67 call sites, no out-of-line copy -- so it has no
#    address at all.  It, COMMAND_LIST_HEAD and CINEMATIC_DVAR_SLOT are used only by
#    maybeSkipIntro, which --no-skip-intro turns off.  None is set for this build, and
#    apply_build() refuses --skip-intro rather than letting a null pointer be called.
BUILDS = {
    "3.3.3.3": {
        "IMAGE_NAME": "codoMP_client_shipRetail.exe",
        "QUICK_MATCH_RVA": 0x2F2C10,
        "QUICK_MATCH_CALLBACK_RVA": 0x8E5794,
        "GET_READY_STATE_RVA": 0x2E5320,
        "START_GAME_RVA": 0x2E4A20,
        "ROOM_SINGLETON_RVA": 0x74B0708,
        "STRING_INIT_RVA": 0x6382C0,
        "STRING_ASSIGN_RVA": 0x638390,
        "CONNECTION_STATE_RVA": 0x162E7EC,
        "MATCH_CONFIG_PRIMARY_RVA": 0x7409CA4,
        "MATCH_CONFIG_SECONDARY_RVA": 0x162A52C,
        "ROOM_SERVICE_RVA": 0x74B070C,
        "ROOM_MATCH_CALLBACKS_RVA": 0x74B07F4,
        "ROOM_MATCH_LIST_PRIMARY_RVA": 0x74B0800,
        "ROOM_MATCH_LIST_SECONDARY_RVA": 0x74B0804,
        "CBUF_ADD_TEXT_RVA": 0x18D840,
        "COMMAND_LIST_HEAD_RVA": 0x2A0111C,
        "CINEMATIC_DVAR_SLOT_RVA": 0x2A8AA4C,
        "LOBBY_LOGON_STATE_RVA": 0x8D7000,
        "LOBBY_CONNECTION_SLOT_RVA": 0x8FAFE0,
        "PROFILE_MANAGER_RVA": 0xC55BD80,
        "PUBLIC_PROFILE_OFFSET": 16,
        "PROFILE_REQUIRED_CHUNK_MASK": 0x07FFFFFF,
        "PROFILE_CHUNK_MASK_OFFSET": 32892,
        "PROFILE_OPERATION_OFFSET": 116,
        "PROFILE_STATE_9084_OFFSET": 36996,
        "PROFILE_DIRTY_FLAGS_OFFSET": 36997,
        "PUBLIC_PROFILE_PARSED_OFFSET": 37144,
        "CURRENT_CHARACTER_GET_RVA": 0x28A0E0,
        "CHARACTER_SLOT_GET_RVA": 0x193370,
        "CURRENT_CHARACTER_SELECT_ITEM_RVA": 0x289FF0,
        "PUBLIC_PROFILE_UPLOAD_POLL_RVA": 0x192350,
        # Room-manager field offsets. These are struct LAYOUT, not addresses, and they are just as
        # per-build as the RVAs -- the room manager grew between these two versions.
        "ROOM_ACTIVE_OFFSET": 608,
        "ROOM_PLAYER_COUNT_OFFSET": 63256,
        "ROOM_SELECTION_KIND_OFFSET": 63280,
        "ROOM_GAME_TYPE_OFFSET": 63284,
        "ROOM_MAP_NAME_OFFSET": 63288,
        "ROOM_PLAYLIST_SLOT_OFFSET": 63292,
        "ROOM_CAPACITY_OFFSET": 63294,
        "ROOM_ROTATION_INDEX_OFFSET": 63324,
        # Vtable SLOT for the room's setReady, as a byte offset. Slot indexes do not transfer
        # either: this vtable has 75 entries on 3.3.3.3 and 88 on 1649370.
        "ROOM_READY_VTABLE_OFFSET": 0x74,
    },
    "1649370": {
        "IMAGE_NAME": "out.exe",
        "QUICK_MATCH_RVA": 0x23E510,
        "QUICK_MATCH_CALLBACK_RVA": 0xA69CAC,
        "GET_READY_STATE_RVA": 0x2302D0,
        "START_GAME_RVA": 0x22F840,
        "ROOM_SINGLETON_RVA": 0x7EE13FC,
        "STRING_INIT_RVA": 0x775A40,
        "STRING_ASSIGN_RVA": 0x775B10,
        "CONNECTION_STATE_RVA": 0x72446B0,
        "MATCH_CONFIG_PRIMARY_RVA": 0x7E69818,
        "MATCH_CONFIG_SECONDARY_RVA": 0x2F06D68,
        "ROOM_SERVICE_RVA": 0x7EE1400,
        "ROOM_MATCH_CALLBACKS_RVA": 0x7EE151C,
        "ROOM_MATCH_LIST_PRIMARY_RVA": 0x7EE1528,
        "ROOM_MATCH_LIST_SECONDARY_RVA": 0x7EE152C,
        "CBUF_ADD_TEXT_RVA": None,
        "COMMAND_LIST_HEAD_RVA": None,
        # PROBABLE, not confirmed: one witness at run 43 depth 2, ratio 0.91 gap 0.31. It was
        # originally left absent on the belief that the cinematic dvar only served maybeSkipIntro --
        # which was WRONG. readCinematicActive also feeds frontendReady, so leaving it unset made
        # cinematic_active permanently null and frontendReady permanently false, and QuickMatch was
        # never invoked at all: the flow sat in waiting_frontend until it timed out.
        "CINEMATIC_DVAR_SLOT_RVA": 0x2FD64AC,
        "LOBBY_LOGON_STATE_RVA": 0xA59D20,
        "LOBBY_CONNECTION_SLOT_RVA": 0xA85C68,
        "PROFILE_MANAGER_RVA": 0xE14BC48,
        "PUBLIC_PROFILE_OFFSET": 16,
        "PROFILE_REQUIRED_CHUNK_MASK": 0x07FFFFFF,
        "PROFILE_CHUNK_MASK_OFFSET": 0x1008C,
        "PROFILE_OPERATION_OFFSET": 116,
        "PROFILE_STATE_9084_OFFSET": 0x11094,
        "PROFILE_DIRTY_FLAGS_OFFSET": 0x11095,
        "PUBLIC_PROFILE_PARSED_OFFSET": 0x1112C,
        "CURRENT_CHARACTER_GET_RVA": 0x2B87C0,
        "CHARACTER_SLOT_GET_RVA": 0x10FF30,
        "CURRENT_CHARACTER_SELECT_ITEM_RVA": 0x2B8700,
        "PUBLIC_PROFILE_UPLOAD_POLL_RVA": 0x10ED70,
        # Measured, not inferred, by aligning the functions that reference each one: the whole
        # 0xF7xx booking block moves +0xEC0 and the active flag moves +0x18. The active flag is
        # corroborated twice -- it is the same `mgr+632` host flag an earlier live session read in
        # StartMatch's gate. Reading these at the 3.3.3.3 offsets is not a subtle error: the room
        # reports player_count 0 on a populated room, and `active` lands on a neighbouring byte, so
        # the flow refuses to QuickMatch over a room that is not really there.
        "ROOM_ACTIVE_OFFSET": 632,
        "ROOM_PLAYER_COUNT_OFFSET": 67032,
        "ROOM_SELECTION_KIND_OFFSET": 67056,
        "ROOM_GAME_TYPE_OFFSET": 67060,
        "ROOM_MAP_NAME_OFFSET": 67064,
        "ROOM_PLAYLIST_SLOT_OFFSET": 67068,
        "ROOM_CAPACITY_OFFSET": 67070,
        "ROOM_ROTATION_INDEX_OFFSET": 67100,
        # 0x74 is slot 29, and this vtable grew from 75 entries to 88, so the index moved. The
        # Needleman-Wunsch alignment of the two vtables -- the same one that resolved
        # GET_READY_STATE, and that reproduces the known slot 13 -> 15 = StartMatch = vtable+60 --
        # maps slot 29 -> slot 33, which is 0x84. Calling 0x74 here reaches an unrelated method:
        # it returned a pointer-looking value and the room's ready flag never changed.
        "ROOM_READY_VTABLE_OFFSET": 0x84,
    },
}

DEFAULT_BUILD = os.environ.get("CODOL_CLIENT_BUILD") or "3.3.3.3"

# Constants absent on the selected build, by name. They are bound to 0 rather than left as None
# because build_script() interpolates them straight into JavaScript, where `None` is a
# ReferenceError that kills the whole script -- including every constant that IS correct. Zero is
# safe precisely because the only code that reads them is behind --skip-intro, which apply_build
# refuses to enable on a build that lacks them.
ABSENT_CONSTANTS: set[str] = set()


def _bind(name: str) -> None:
    for key, value in BUILDS[name].items():
        if value is None:
            ABSENT_CONSTANTS.add(key)
            globals()[key] = 0
        else:
            ABSENT_CONSTANTS.discard(key)
            globals()[key] = value


_bind(DEFAULT_BUILD)


def apply_build(name: str, skip_intro: bool) -> None:
    """Rebind the module-level constants for one build, before build_script() reads them."""
    if name not in BUILDS:
        raise SystemExit(f"unknown build {name!r}; known: {', '.join(BUILDS)}")
    _bind(name)
    missing = sorted(ABSENT_CONSTANTS)
    if skip_intro and missing:
        raise SystemExit(
            f"build {name} has no address for {', '.join(missing)} -- pass "
            f"--no-skip-intro. On 1649370 Cbuf_AddText is inlined at 67 sites and has no "
            f"out-of-line copy to call; skipping the intro is the only thing that needed it.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Running client process ID")
    parser.add_argument(
        "--build", default=DEFAULT_BUILD, choices=sorted(BUILDS),
        help="which client build's addresses to use (env CODOL_CLIENT_BUILD)")
    parser.add_argument(
        "--action",
        choices=("status", "frontend", "match", "ready", "resume", "allocate", "full"),
        default="status",
    )
    parser.add_argument("--playlist-id", type=int, default=26)
    parser.add_argument("--max-player", type=int, default=6)
    parser.add_argument("--match-type", type=int, default=1)
    parser.add_argument("--map", default="")
    parser.add_argument("--mode", default="")
    parser.add_argument(
        "--force-client-allocation",
        action="store_true",
        help=(
            "directly invoke CODOL's client allocation entry after ready; by default full "
            "waits for the client to enter it naturally"
        ),
    )
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--window-timeout", type=float, default=20.0)
    parser.add_argument("--frontend-stable-seconds", type=float, default=2.0)
    parser.add_argument(
        "--character-index",
        type=int,
        help=(
            "before QuickMatch, select and persist one native CODOL character slot "
            "after PublicProfile is ready"
        ),
    )
    parser.add_argument(
        "--skip-intro",
        action=argparse.BooleanOptionalAction,
        # Defaults to whether THIS build can do it at all. 1649370 has no out-of-line Cbuf_AddText
        # to call -- it is inlined at 67 sites -- so the intro simply plays out there. Defaulting to
        # True regardless would make every 1649370 invocation fail an argument check for a
        # convenience feature, while 3.3.3.3 keeps the behaviour it has always had.
        default=BUILDS[DEFAULT_BUILD]["CBUF_ADD_TEXT_RVA"] is not None,
        help="queue CODOL's native 'autocinematic none' command while startup videos play",
    )
    return parser.parse_args()


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


def select_game_window(
    windows: list[tuple[int, int, str]],
) -> tuple[int, int] | None:
    matches = [
        (hwnd, thread_id)
        for hwnd, thread_id, class_name in windows
        if class_name.casefold() == GAME_WINDOW_CLASS.casefold()
    ]
    return matches[0] if matches else None


def find_window(pid: int, timeout_seconds: float) -> tuple[int, int]:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds
    while True:
        windows: list[tuple[int, int, str]] = []

        @callback_type
        def visit(hwnd: int, _lparam: int) -> bool:
            owner_pid = wintypes.DWORD()
            thread_id = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if owner_pid.value == pid and user32.IsWindowVisible(hwnd):
                class_name = ctypes.create_unicode_buffer(256)
                if user32.GetClassNameW(hwnd, class_name, len(class_name)):
                    windows.append((int(hwnd), int(thread_id), class_name.value))
            return True

        if not user32.EnumWindows(visit, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        match = select_game_window(windows)
        if match is not None:
            return match
        if time.monotonic() >= deadline:
            raise SystemExit(
                f"PID {pid} has no visible {GAME_WINDOW_CLASS} game window after "
                f"{timeout_seconds:.1f} seconds."
            )
        time.sleep(0.1)


def build_script(args: argparse.Namespace, window_thread_id: int) -> str:
    return f"""
'use strict';

const module = Process.getModuleByName('{IMAGE_NAME}');
const roomSlot = module.base.add({ROOM_SINGLETON_RVA});
const quickMatchAddress = module.base.add({QUICK_MATCH_RVA});
const quickMatchCallback = module.base.add({QUICK_MATCH_CALLBACK_RVA});
const getReadyAddress = module.base.add({GET_READY_STATE_RVA});
const startGameAddress = module.base.add({START_GAME_RVA});
const stringInitAddress = module.base.add({STRING_INIT_RVA});
const stringAssignAddress = module.base.add({STRING_ASSIGN_RVA});
const connectionState = module.base.add({CONNECTION_STATE_RVA});
const matchConfigPrimarySlot = module.base.add({MATCH_CONFIG_PRIMARY_RVA});
const matchConfigSecondarySlot = module.base.add({MATCH_CONFIG_SECONDARY_RVA});
const roomServiceSlot = module.base.add({ROOM_SERVICE_RVA});
const roomMatchCallbacksSlot = module.base.add({ROOM_MATCH_CALLBACKS_RVA});
const roomMatchListPrimarySlot = module.base.add({ROOM_MATCH_LIST_PRIMARY_RVA});
const roomMatchListSecondarySlot = module.base.add({ROOM_MATCH_LIST_SECONDARY_RVA});
const cbufAddTextAddress = module.base.add({CBUF_ADD_TEXT_RVA});
const commandListHead = module.base.add({COMMAND_LIST_HEAD_RVA});
const cinematicDvarSlot = module.base.add({CINEMATIC_DVAR_SLOT_RVA});
const lobbyLogonState = module.base.add({LOBBY_LOGON_STATE_RVA});
const lobbyConnectionSlot = module.base.add({LOBBY_CONNECTION_SLOT_RVA});
const profileManager = module.base.add({PROFILE_MANAGER_RVA});
const currentCharacterGetAddress = module.base.add({CURRENT_CHARACTER_GET_RVA});
const characterSlotGetAddress = module.base.add({CHARACTER_SLOT_GET_RVA});
const currentCharacterSelectItemAddress = module.base.add({CURRENT_CHARACTER_SELECT_ITEM_RVA});
const publicProfileUploadPollAddress = module.base.add({PUBLIC_PROFILE_UPLOAD_POLL_RVA});
const backendModule = Process.findModuleByName('Alwaysoffline.Localnet32');
const requestInventoryRefreshAddress = backendModule === null
    ? null
    : backendModule.findExportByName('CODOL_RequestInventoryRefresh');

const quickMatch = new NativeFunction(
    quickMatchAddress, 'pointer', ['int', 'pointer', 'pointer']);
const getReady = new NativeFunction(getReadyAddress, 'int', ['pointer'], 'thiscall');
const startGame = new NativeFunction(
    startGameAddress, 'void', ['pointer', 'int', 'int', 'int'], 'thiscall');
const stringInit = new NativeFunction(stringInitAddress, 'pointer', ['pointer'], 'thiscall');
const stringAssign = new NativeFunction(
    stringAssignAddress, 'pointer', ['pointer', 'pointer'], 'thiscall');
const currentCharacterGet = new NativeFunction(currentCharacterGetAddress, 'int', []);
const characterSlotGet = new NativeFunction(
    characterSlotGetAddress, 'int', ['int', 'int']);
const currentCharacterSelectItemThunk = Memory.alloc(Process.pageSize);
const currentCharacterSelectItemTarget = currentCharacterSelectItemAddress.toUInt32();
currentCharacterSelectItemThunk.writeByteArray([
    0x57,
    0x8B, 0x7C, 0x24, 0x08,
    0xB8,
    currentCharacterSelectItemTarget & 0xFF,
    (currentCharacterSelectItemTarget >>> 8) & 0xFF,
    (currentCharacterSelectItemTarget >>> 16) & 0xFF,
    (currentCharacterSelectItemTarget >>> 24) & 0xFF,
    0xFF, 0xD0,
    0x5F,
    0xC2, 0x04, 0x00
]);
Memory.protect(currentCharacterSelectItemThunk, Process.pageSize, 'r-x');
const currentCharacterSelectItem = new NativeFunction(
    currentCharacterSelectItemThunk, 'void', ['int'], 'stdcall');
const publicProfileUploadPoll = new NativeFunction(
    publicProfileUploadPollAddress, 'void', []);
const targetCharacterIndex = {json.dumps(args.character_index)};

const modeObject = Memory.alloc(4);
const mapObject = Memory.alloc(4);
const config = Memory.alloc(16);
const modeText = Memory.allocUtf8String({json.dumps(args.mode)});
const mapText = Memory.allocUtf8String({json.dumps(args.map)});
let stringsInitialized = false;
let phase = '{args.action}';
let busy = false;
let complete = false;
let forcingAllocation = false;
let lastFrontendWait = 0;
let lastDriveAt = 0;
let frontendReadySince = null;
let readyAttempts = 0;
let introSkipAttempts = 0;
let lastIntroSkipAttempt = 0;
let matchAttempts = 0;
let characterSelectionApplied = false;
let lastProfileUploadPoll = 0;
let stalledProfileSince = null;
let profileRecoveryAttempted = false;

function readableAddress(address, requiredSize) {{
    const range = Process.findRangeByAddress(address.add(requiredSize - 1));
    return range !== null && range.protection.indexOf('r') !== -1;
}}

function executableAddress(address) {{
    const range = Process.findRangeByAddress(address);
    return range !== null && range.protection.indexOf('x') !== -1;
}}

function dependencyState(slot, requiredSize, virtualOffsets) {{
    try {{
        const address = slot.readPointer();
        if (address.isNull()) return {{ address: address.toString(), readable: false }};
        const state = {{
            address: address.toString(),
            readable: readableAddress(address, requiredSize)
        }};
        if (!state.readable || virtualOffsets === undefined) return state;
        const vtable = address.readPointer();
        state.vtable = vtable.toString();
        state.methods_ready = !vtable.isNull() && virtualOffsets.every(offset => {{
            if (!readableAddress(vtable.add(offset), Process.pointerSize)) return false;
            const target = vtable.add(offset).readPointer();
            return !target.isNull() && executableAddress(target);
        }});
        return state;
    }} catch (error) {{
        return {{ address: null, readable: false, error: error.message }};
    }}
}}

function quickMatchReadiness() {{
    const clientConnectionState = connectionState.readU32();
    const dependencies = {{
        primary_config: dependencyState(matchConfigPrimarySlot, 16),
        secondary_config: dependencyState(matchConfigSecondarySlot, 12),
        room: dependencyState(roomSlot, 63325, [0x54, 0x74]),
        room_service: dependencyState(roomServiceSlot, 32, [0x10, 0x18, 0x1c]),
        match_callbacks: dependencyState(roomMatchCallbacksSlot, 16),
        match_list_primary: dependencyState(roomMatchListPrimarySlot, 16),
        match_list_secondary: dependencyState(roomMatchListSecondarySlot, 16)
    }};
    return {{
        ready: Object.values(dependencies).every(item =>
            item.readable && item.methods_ready !== false),
        connection_state: clientConnectionState,
        dependencies: dependencies
    }};
}}

function readCinematicActive() {{
    try {{
        const dvar = cinematicDvarSlot.readPointer();
        if (dvar.isNull() || !readableAddress(dvar, 16)) return null;
        return dvar.add(12).readU32() !== 0;
    }} catch (_) {{
        return null;
    }}
}}

function readLobbyState() {{
    let connection = ptr(0);
    let connectionStatus = null;
    try {{
        connection = lobbyConnectionSlot.readPointer();
        if (!connection.isNull() && readableAddress(connection, 0x1f8))
            connectionStatus = connection.add(0x1f4).readS32();
    }} catch (_) {{}}
    let logonState = null;
    try {{ logonState = lobbyLogonState.readS32(); }} catch (_) {{}}
    return {{
        logon_state: logonState,
        logged_on: logonState === 4 || logonState === 6,
        connection: connection.isNull() ? null : connection.toString(),
        connection_status: connectionStatus
    }};
}}

function readPublicProfileState() {{
    const profile = profileManager.add({PUBLIC_PROFILE_OFFSET});
    try {{
        const chunkMask = profile.add({PROFILE_CHUNK_MASK_OFFSET}).readU32();
        const operation = profile.add({PROFILE_OPERATION_OFFSET}).readS32();
        const state9084 = profile.add({PROFILE_STATE_9084_OFFSET}).readU8();
        const dirtyFlags = profile.add({PROFILE_DIRTY_FLAGS_OFFSET}).readU8();
        const parsed = profile.add({PUBLIC_PROFILE_PARSED_OFFSET}).readU8() !== 0;
        const requiredChunksComplete = chunkMask === {PROFILE_REQUIRED_CHUNK_MASK};
        return {{
            address: profile.toString(),
            chunk_mask: '0x' + chunkMask.toString(16),
            required_chunks_complete: requiredChunksComplete,
            operation: operation,
            state_9084: state9084,
            dirty_flags: dirtyFlags,
            parsed: parsed,
            ready: requiredChunksComplete && operation === 0 && parsed
        }};
    }} catch (error) {{
        return {{ address: profile.toString(), ready: false, error: error.message }};
    }}
}}

function readCurrentCharacter(publicProfile) {{
    if (!publicProfile.ready) return null;
    try {{
        const value = currentCharacterGet();
        return value >= 0 && value < 12 ? value : null;
    }} catch (_) {{
        return null;
    }}
}}

// OLMOD(section-48-input-probe): the twelve characterClasses[<character>].slots[<n>]
// values, read HERE rather than from the game-server dll.
//
// The dll's own attempt at this call dies -- roster line, then a 3000ms frame-thread
// stall, then 0xc0000005 -- and section 65n could not attribute it, because the same
// stall and the same crash frame also appear in runs where that call never executed.
// This harness already calls characterSlotGet successfully on this build every single
// run, in applyTargetCharacter below. So the measurement moves to the harness that
// works instead of the one that does not.
//
// Read-only, never throws, and gated on publicProfile.ready for the same reason
// readCurrentCharacter is: sub_50FF30's own null check does not catch a null profile
// (v2 = manager + 160; if (!v2) passes when manager is 0).
function readCharacterSlots(publicProfile, characterIndex) {{
    if (!publicProfile.ready || characterIndex === null) return null;
    // NINE. The first version read 0..11 and the last three THREW every time -- which is
    // how the width was measured, and then it became a cost: three caught access
    // violations per poll is expensive enough in Frida that the flow armed and never
    // invoked quick match inside its 45s budget. The measurement is done; stop paying for
    // it. The try/catch stays because a call that faults must not take the flow down.
    const slots = [];
    for (let slot = 0; slot < 9; slot += 1) {{
        try {{
            slots.push(characterSlotGet(characterIndex, slot));
        }} catch (error) {{
            slots.push(null);
        }}
    }}
    return slots;
}}

function applyTargetCharacter(state) {{
    if (targetCharacterIndex === null
        || !state.public_profile_ready)
        return state;
    if (state.current_character_index !== targetCharacterIndex) {{
        if (state.active)
            throw new Error('refusing to change character while a room is active');
        const targetCharacterItemId = characterSlotGet(targetCharacterIndex, 0);
        if (targetCharacterItemId <= 0)
            throw new Error(
                'target character slot has no native item: ' + targetCharacterIndex);
        currentCharacterSelectItem(targetCharacterItemId);
        const observed = currentCharacterGet();
        if (observed !== targetCharacterIndex)
            throw new Error(
                'current character selection did not persist: expected '
                + targetCharacterIndex + ', observed ' + observed);
        if (!characterSelectionApplied) {{
            characterSelectionApplied = true;
            send({{
                type: 'character_selected',
                source: 'client-native-forced',
                requested_character_index: targetCharacterIndex,
                requested_character_item_id: targetCharacterItemId,
                observed_character_index: observed,
                selector_target: currentCharacterSelectItemAddress.toString()
            }});
        }}
        state = roomState();
    }}
    const now = Date.now();
    if (state.public_profile.operation === 0
        && state.public_profile.dirty_flags !== 0
        && now - lastProfileUploadPoll >= 1000) {{
        lastProfileUploadPoll = now;
        publicProfileUploadPoll();
        send({{
            type: 'public_profile_upload_polled',
            source: 'client-native-forced',
            target: publicProfileUploadPollAddress.toString(),
            state: roomState()
        }});
        state = roomState();
    }}
    return roomState();
}}

function findCommandHandler(commandName) {{
    try {{
        let node = commandListHead.readPointer();
        for (let index = 0; !node.isNull() && index < 8192; ++index) {{
            const name = node.add(4).readPointer();
            if (!name.isNull() && name.readUtf8String() === commandName)
                return node.add(8).readPointer();
            node = node.readPointer();
        }}
    }} catch (_) {{}}
    return ptr(0);
}}

function queueClientCommand(command) {{
    const commandText = Memory.allocUtf8String(command.replace(/\\n*$/, '\\n'));
    const thunk = Memory.alloc(Process.pageSize);
    const target = cbufAddTextAddress.toUInt32();
    thunk.writeByteArray([
        0x8B, 0x44, 0x24, 0x04,
        0x8B, 0x4C, 0x24, 0x08,
        0xBA,
        target & 0xFF,
        (target >>> 8) & 0xFF,
        (target >>> 16) & 0xFF,
        (target >>> 24) & 0xFF,
        0xFF, 0xD2,
        0xC3
    ]);
    Memory.protect(thunk, Process.pageSize, 'r-x');
    const invoke = new NativeFunction(thunk, 'void', ['pointer', 'int']);
    invoke(commandText, 0);
}}

function maybeSkipIntro(state) {{
    if (!{str(args.skip_intro).lower()}
        || state.cinematic_active === false
        || state.quick_match_ready !== true)
        return;
    const now = Date.now();
    if (introSkipAttempts >= 2 || now - lastIntroSkipAttempt < 1000)
        return;
    const handler = findCommandHandler('autocinematic');
    ++introSkipAttempts;
    lastIntroSkipAttempt = now;
    const attempt = introSkipAttempts;
    // Do not nest a NativeFunction call inside the window-thread hook. The
    // command buffer has its own native critical section, so defer the enqueue
    // to Frida's worker event loop.
    setTimeout(() => {{
        try {{
            queueClientCommand('autocinematic none');
            send({{
                type: 'intro_skip_invoked',
                attempt: attempt,
                command: 'autocinematic none',
                command_handler: handler.isNull() ? null : handler.toString(),
                state: state
            }});
        }} catch (error) {{
            send({{
                type: 'intro_skip_error',
                attempt: attempt,
                error: error.stack || error.message
            }});
        }}
    }}, 0);
}}

function roomState() {{
    const quickMatch = quickMatchReadiness();
    const lobby = readLobbyState();
    const publicProfile = readPublicProfileState();
    const currentCharacterIndex = readCurrentCharacter(publicProfile);
    const cinematicActive = readCinematicActive();
    let room = ptr(0);
    try {{ room = roomSlot.readPointer(); }} catch (_) {{}}
    if (room.isNull()) {{
        return {{
            room: null,
            active: false,
            player_count: null,
            capacity: null,
            ready: null,
            connection_state: connectionState.readU32(),
            cinematic_active: cinematicActive,
            lobby: lobby,
            lobby_logged_on: lobby.logged_on,
            public_profile: publicProfile,
            public_profile_ready: publicProfile.ready,
            current_character_index: currentCharacterIndex,
            character_slots: readCharacterSlots(publicProfile, currentCharacterIndex),
            quick_match_ready: quickMatch.ready,
            quick_match_dependencies: quickMatch.dependencies
        }};
    }}
    try {{
        const booking = bookingState(room);
        return {{
            room: room.toString(),
            active: room.add({ROOM_ACTIVE_OFFSET}).readU8() !== 0,
            player_count: room.add({ROOM_PLAYER_COUNT_OFFSET}).readU32(),
            capacity: room.add({ROOM_CAPACITY_OFFSET}).readU8(),
            ready: getReady(room),
            booking: booking,
            connection_state: connectionState.readU32(),
            cinematic_active: cinematicActive,
            lobby: lobby,
            lobby_logged_on: lobby.logged_on,
            public_profile: publicProfile,
            public_profile_ready: publicProfile.ready,
            current_character_index: currentCharacterIndex,
            character_slots: readCharacterSlots(publicProfile, currentCharacterIndex),
            quick_match_ready: quickMatch.ready,
            quick_match_dependencies: quickMatch.dependencies
        }};
    }} catch (error) {{
        return {{ room: room.toString(), error: error.message }};
    }}
}}

function initializeConfig() {{
    if (stringsInitialized) return;
    stringInit(modeObject);
    stringInit(mapObject);
    stringAssign(modeObject, modeText);
    stringAssign(mapObject, mapText);
    config.writeByteArray(new Uint8Array(16));
    config.writePointer(modeObject.readPointer());
    config.add(4).writePointer(mapObject.readPointer());
    config.add(8).writeU8({args.playlist_id});
    config.add(9).writeU8(0);
    config.add(10).writeU8({args.max_player});
    stringsInitialized = true;
}}

function readStringObject(address) {{
    try {{
        const text = address.readPointer();
        return text.isNull() ? '' : text.readUtf8String();
    }} catch (_) {{
        return null;
    }}
}}

function bookingState(room) {{
    return {{
        selection_kind: readStringObject(room.add({ROOM_SELECTION_KIND_OFFSET})),
        game_type: readStringObject(room.add({ROOM_GAME_TYPE_OFFSET})),
        map_name: readStringObject(room.add({ROOM_MAP_NAME_OFFSET})),
        playlist_slot: room.add({ROOM_PLAYLIST_SLOT_OFFSET}).readU8(),
        rotation_index: room.add({ROOM_ROTATION_INDEX_OFFSET}).readS8()
    }};
}}

function applyRequestedBooking(state) {{
    if (!state.active || {json.dumps(args.map)} === '') return state;
    const room = roomSlot.readPointer();
    const before = bookingState(room);
    if (before.map_name === {json.dumps(args.map)}) return state;
    // QuickMatch accepts a map string, but the 1649370 COOP path replaces it with the
    // survival playlist's default while the room is being formed. StartGame later reads
    // this owned string object when it builds mmstart, so restore the requested campaign
    // map after formation and before the local member is marked ready.
    stringAssign(room.add({ROOM_MAP_NAME_OFFSET}), mapText);
    const after = bookingState(room);
    state.booking = after;
    send({{
        type: 'booking_overridden',
        before: before,
        after: after
    }});
    return state;
}}

function fail(message, state) {{
    complete = true;
    send({{ type: 'error', message: message, state: state || roomState() }});
}}

function invokeReady(room, state) {{
    const vtable = room.readPointer();
    const target = vtable.add({ROOM_READY_VTABLE_OFFSET}).readPointer();
    const setReady = new NativeFunction(target, 'int', ['pointer', 'int'], 'thiscall');
    const result = setReady(room, 1);
    ++readyAttempts;
    send({{
        type: 'ready_invoked',
        target: target.toString(),
        result: result,
        attempt: readyAttempts,
        state: state
    }});
}}

function frontendReady(state) {{
    // `!== true` rather than `=== false`, because a build whose cinematic dvar slot is unknown or
    // wrong reports null, and requiring `false` turns a startup-video guard into a permanent
    // deadlock. A wrong slot that happens to read non-zero still blocks -- but it blocks visibly,
    // with cinematic_active: true in every waiting_frontend message, rather than silently.
    return state.quick_match_ready
        && state.lobby_logged_on
        && state.public_profile_ready
        && state.cinematic_active !== true
        && (targetCharacterIndex === null
            || (state.current_character_index === targetCharacterIndex
                && state.public_profile.dirty_flags === 0));
}}

function maybeRecoverStalledProfile(state) {{
    const profile = state.public_profile;
    const stalled = state.lobby_logged_on
        && state.quick_match_ready
        && state.cinematic_active !== true
        && state.public_profile_ready === false
        && profile !== null
        && profile.operation === 1
        && profile.chunk_mask === '0x0';
    if (!stalled) {{
        stalledProfileSince = null;
        return;
    }}
    const now = Date.now();
    if (stalledProfileSince === null) stalledProfileSince = now;
    if (profileRecoveryAttempted || now - stalledProfileSince < 10000) return;
    profileRecoveryAttempted = true;
    if (requestInventoryRefreshAddress === null) {{
        send({{ type: 'profile_recovery_unavailable' }});
        return;
    }}
    const requestInventoryRefresh = new NativeFunction(
        requestInventoryRefreshAddress, 'uint32', []);
    send({{
        type: 'profile_recovery_requested',
        source: 'backend-export',
        generation: requestInventoryRefresh()
    }});
}}

function invokeQuickMatch(state) {{
    initializeConfig();
    const result = quickMatch({args.match_type}, quickMatchCallback, config);
    ++matchAttempts;
    send({{
        type: 'match_invoked',
        attempt: matchAttempts,
        result: result.toString(),
        playlist_id: {args.playlist_id},
        max_player: {args.max_player},
        thread_id: Process.getCurrentThreadId(),
        frontend_state: state
    }});
}}

function invokeForcedAllocation() {{
    const room = roomSlot.readPointer();
    phase = 'allocating';
    forcingAllocation = true;
    startGame(room, 1, -1, 0);
    // Frida suppresses a nested Interceptor callback on some builds when the
    // NativeFunction call originates inside the window-thread drive hook.
    if (!complete) {{
        complete = true;
        send({{
            type: 'allocation_observed',
            source: 'frida-forced',
            observation: 'native_call_returned',
            thread_id: Process.getCurrentThreadId(),
            room: room.toString(),
            allocate: 1,
            server_index: -1,
            private_match: 0,
            booking: bookingState(room)
        }});
    }}
}}

Interceptor.attach(startGameAddress, {{
    onEnter(args) {{
        if (complete || (phase !== 'wait_allocation' && phase !== 'allocating' && phase !== 'allocate'))
            return;
        const room = this.context.ecx;
        complete = true;
        send({{
            type: 'allocation_observed',
            source: forcingAllocation ? 'frida-forced' : 'client-native',
            thread_id: Process.getCurrentThreadId(),
            room: room.toString(),
            allocate: args[0].toInt32(),
            server_index: args[1].toInt32(),
            private_match: args[2].toInt32(),
            booking: bookingState(room)
        }});
    }}
}});

function drive() {{
    const driveNow = Date.now();
    if (complete
        || busy
        || Process.getCurrentThreadId() !== {window_thread_id}
        || driveNow - lastDriveAt < 100) return;
    lastDriveAt = driveNow;
    busy = true;
    try {{
        let state = roomState();
        state = applyTargetCharacter(state);
        maybeSkipIntro(state);
        maybeRecoverStalledProfile(state);
        if (phase === 'status') {{
            complete = true;
            send({{ type: 'status', state: state }});
        }} else if (phase === 'frontend') {{
            if (!frontendReady(state)) {{
                frontendReadySince = null;
                const now = Date.now();
                if (now - lastFrontendWait >= 1000) {{
                    lastFrontendWait = now;
                    send({{ type: 'waiting_frontend', state: state }});
                }}
            }} else if (state.active && state.player_count >= 1) {{
                complete = true;
                send({{
                    type: 'frontend_ready',
                    stable_seconds: 0,
                    resume_action: state.ready === 1 ? 'observe' : 'ready',
                    state: state
                }});
            }} else if (state.active) {{
                frontendReadySince = null;
                const now = Date.now();
                if (now - lastFrontendWait >= 1000) {{
                    lastFrontendWait = now;
                    send({{ type: 'waiting_room_member', state: state }});
                }}
            }} else {{
                const now = Date.now();
                if (frontendReadySince === null) frontendReadySince = now;
                const stableSeconds = (now - frontendReadySince) / 1000;
                if (stableSeconds >= {args.frontend_stable_seconds}) {{
                    complete = true;
                    send({{
                        type: 'frontend_ready',
                        stable_seconds: stableSeconds,
                        state: state
                    }});
                }}
            }}
        }} else if (phase === 'match' || phase === 'full') {{
            if (state.active) {{
                fail('refusing QuickMatch while a room is already active', state);
            }} else if (!frontendReady(state)) {{
                const now = Date.now();
                if (now - lastFrontendWait >= 1000) {{
                    lastFrontendWait = now;
                    send({{ type: 'waiting_frontend', state: state }});
                }}
            }} else {{
                phase = phase === 'full' ? 'wait_room' : 'done';
                invokeQuickMatch(state);
                if (phase === 'done') complete = true;
            }}
        }} else if (phase === 'wait_room') {{
            if (state.active && state.player_count >= 1) {{
                state = applyRequestedBooking(state);
                phase = 'ensure_ready';
            }} else {{
                const now = Date.now();
                if (now - lastFrontendWait >= 1000) {{
                    lastFrontendWait = now;
                    send({{ type: 'waiting_room', state: state }});
                }}
            }}
        }} else if (phase === 'ready') {{
            if (!state.active) fail('cannot set ready without an active room', state);
            else {{
                invokeReady(roomSlot.readPointer(), state);
                complete = true;
            }}
        }} else if (phase === 'resume') {{
            if (!state.active) fail('cannot resume allocation without an active room', state);
            else if (state.player_count >= 1) {{
                state = applyRequestedBooking(state);
                phase = 'ensure_ready';
            }} else {{
                const now = Date.now();
                if (now - lastFrontendWait >= 1000) {{
                    lastFrontendWait = now;
                    send({{ type: 'waiting_room_member', state: state }});
                }}
            }}
        }} else if (phase === 'ensure_ready') {{
            if (!state.active) {{
                fail('room became inactive before ready was committed', state);
            }} else if (state.ready === 1) {{
                send({{ type: 'ready_confirmed', attempts: readyAttempts, state: state }});
                if ({str(args.force_client_allocation).lower()}) {{
                    invokeForcedAllocation();
                }} else {{
                    phase = 'wait_allocation';
                }}
            }} else if (readyAttempts === 0) {{
                invokeReady(roomSlot.readPointer(), state);
            }}
        }} else if (phase === 'wait_allocation' || phase === 'allocate') {{
            if (!state.active) {{
                fail('room became inactive before server allocation', state);
            }} else if (state.ready !== 1) {{
                if (phase === 'allocate') fail('local room member is not ready', state);
                else phase = 'ensure_ready';
            }} else if (phase === 'allocate' || {str(args.force_client_allocation).lower()}) {{
                invokeForcedAllocation();
            }}
        }}
    }} catch (error) {{
        fail(error.stack || error.message);
    }} finally {{
        busy = false;
    }}
}}

const user32 = Process.getModuleByName('user32.dll');
for (const name of ['PeekMessageA', 'PeekMessageW', 'DispatchMessageA', 'DispatchMessageW']) {{
    const address = user32.findExportByName(name);
    if (address !== null) Interceptor.attach(address, {{ onEnter: drive }});
}}

send({{
    type: 'armed',
    action: '{args.action}',
    pid: Process.id,
    module_base: module.base.toString(),
    window_thread_id: {window_thread_id},
    state: roomState()
}});
"""


def main() -> int:
    args = parse_args()
    apply_build(args.build, args.skip_intro)
    if args.frontend_stable_seconds < 0:
        raise SystemExit("--frontend-stable-seconds must be non-negative")
    if args.window_timeout <= 0:
        raise SystemExit("--window-timeout must be positive")
    if args.character_index is not None and not 0 <= args.character_index < 12:
        raise SystemExit("--character-index must be between 0 and 11")
    for name, value in (("playlist ID", args.playlist_id), ("max player", args.max_player)):
        if not 0 <= value <= 255:
            raise SystemExit(f"{name} must fit in one byte")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    hwnd, window_thread_id = find_window(pid, min(args.window_timeout, args.timeout))
    done = threading.Event()
    result: dict[str, object] = {}
    session = device.attach(pid)
    script = session.create_script(build_script(args, window_thread_id))

    def on_message(message: dict, data: bytes | None) -> None:
        payload = message.get("payload", message)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        if payload.get("type") in {"status", "frontend_ready", "error", "allocation_observed"}:
            result.update(payload)
            done.set()
        elif args.action in {"match", "ready"} and payload.get("type", "").endswith("_invoked"):
            result.update(payload)
            done.set()

    script.on("message", on_message)
    try:
        script.load()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        deadline = time.monotonic() + args.timeout
        while not done.is_set() and time.monotonic() < deadline:
            if not user32.PostMessageW(hwnd, 0, 0, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            done.wait(0.1)
        if not done.is_set():
            print(json.dumps({"type": "timeout", "seconds": args.timeout}))
            return 2
        return 0 if result.get("type") != "error" else 1
    finally:
        script.unload()
        session.detach()


if __name__ == "__main__":
    raise SystemExit(main())
