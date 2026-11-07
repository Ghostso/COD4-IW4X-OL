#!/usr/bin/env python3
"""Record CODOL native mouse scaling, final usercmds, and camera state."""

from __future__ import annotations

import argparse
import ctypes
import json
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
PLUGIN_NAME = "CodolGameServer.Localnet32"
RAW_MOUSE_RVA = 0x5F090
SCALED_MOUSE_RVA = 0x5F120
CREATE_CMD_RVA = 0x60070
ACTIVE_LOCAL_CLIENT_INDEX_RVA = 0x7417BA8
ENCODED_CGAME_GLOBALS_RVA = 0x1619510
ENCODED_CLIENT_ACTIVE_RVA = 0x162E838
CGAME_POINTER_XOR = 0xFBB2C97A
CLIENT_ACTIVE_POINTER_XOR = 0x6891D1C7

DVAR_RVAS = {
    "horizontal_sensitivity": 0x162A540,
    "vertical_sensitivity": 0x162E790,
    "mouse_accel": 0x162E7C4,
    "m_pitch": 0x162A568,
    "m_yaw_candidate": 0x162A560,
    "m_filter": 0x162E820,
}


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


def build_script() -> str:
    dvar_rvas = json.dumps(DVAR_RVAS, separators=(",", ":"))
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const rawMouse = module.base.add({RAW_MOUSE_RVA});
const scaledMouse = module.base.add({SCALED_MOUSE_RVA});
const createCmd = module.base.add({CREATE_CMD_RVA});
const activeLocalClientIndex = module.base.add({ACTIVE_LOCAL_CLIENT_INDEX_RVA});
const encodedCgameGlobals = module.base.add({ENCODED_CGAME_GLOBALS_RVA});
const encodedClientActive = module.base.add({ENCODED_CLIENT_ACTIVE_RVA});
const dvarRvas = {dvar_rvas};
const mouseByThread = new Map();
let sequence = 0;

function readU8(address) {{ try {{ return address.readU8(); }} catch (_) {{ return null; }} }}
function readS8(address) {{ try {{ return address.readS8(); }} catch (_) {{ return null; }} }}
function readU16(address) {{ try {{ return address.readU16(); }} catch (_) {{ return null; }} }}
function readU32(address) {{ try {{ return address.readU32(); }} catch (_) {{ return null; }} }}
function readS32(address) {{ try {{ return address.readS32(); }} catch (_) {{ return null; }} }}
function readFloat(address) {{ try {{ return address.readFloat(); }} catch (_) {{ return null; }} }}
function readPointer(address) {{ try {{ return address.readPointer(); }} catch (_) {{ return null; }} }}
function readVec3(address) {{
    return [readFloat(address), readFloat(address.add(4)), readFloat(address.add(8))];
}}

function threadMouseState() {{
    const threadId = Process.getCurrentThreadId();
    let state = mouseByThread.get(threadId);
    if (state === undefined) {{
        state = {{ raw_output_edx: null, raw_output_esi: null, scaled_0: null, scaled_1: null }};
        mouseByThread.set(threadId, state);
    }}
    return state;
}}

function readDvar(rva) {{
    const dvar = readPointer(module.base.add(rva));
    if (dvar === null || dvar.isNull()) return null;
    return {{
        address: dvar.toString(),
        current_u32: readU32(dvar.add(12)),
        current_float: readFloat(dvar.add(12))
    }};
}}

function clientActive() {{
    const encoded = readU32(encodedClientActive);
    if (encoded === null) return null;
    const value = ptr((encoded ^ {CLIENT_ACTIVE_POINTER_XOR}) >>> 0);
    return readU32(value) === null ? null : value;
}}

function currentCgame() {{
    const localClient = readU32(activeLocalClientIndex);
    if (localClient === null || localClient > 15) return null;
    const encoded = readU32(encodedCgameGlobals.add(localClient * 4));
    if (encoded === null) return null;
    const value = ptr((encoded ^ {CGAME_POINTER_XOR}) >>> 0);
    return readU32(value) === null ? null : value;
}}

function readPlayerState(address) {{
    if (address === null || address.isNull()) return null;
    return {{
        command_time: readU32(address),
        pm_type: readU8(address.add(4)),
        pm_time: readU32(address.add(8)),
        pm_flags: readU32(address.add(12)),
        origin: readVec3(address.add(0x1C)),
        velocity: readVec3(address.add(0x28)),
        delta_angles: readVec3(address.add(0xA0)),
        ladder_vector: readVec3(address.add(0xB0)),
        viewangles: readVec3(address.add(0x14C)),
        weapon_position_fraction: readFloat(address.add(0x34C)),
        weapon_time: [readS32(address.add(0x270)), readS32(address.add(0x28C))],
        weapon_delay: [readS32(address.add(0x274)), readS32(address.add(0x290))],
        weapon_state: [readS32(address.add(0x27C)), readS32(address.add(0x298))],
        weapon_anim: [readU32(address.add(0x26C)), readU32(address.add(0x288))]
    }};
}}

function readCameraState() {{
    const cgame = currentCgame();
    if (cgame === null) return null;
    const snapshot = readPointer(cgame.add(0x3578));
    const nextSnapshot = readPointer(cgame.add(0x357C));
    return {{
        cgame_time: readS32(cgame),
        predicted: readPlayerState(cgame),
        snapshot: readPlayerState(snapshot),
        next_snapshot: readPlayerState(nextSnapshot),
        refdef_vieworg: readVec3(cgame.add(0xAE504)),
        refdef_viewangles: readVec3(cgame.add(0xB2688))
    }};
}}

function readUserCmd(command) {{
    if (command === null || command.isNull()) return null;
    let tail = null;
    try {{
        tail = Array.from(new Uint8Array(command.add(36).readByteArray(8)))
            .map(value => value.toString(16).padStart(2, '0')).join('');
    }} catch (_) {{}}
    return {{
        address: command.toString(),
        command_time: readU32(command),
        buttons: readU32(command.add(4)),
        angles: [readU32(command.add(8)), readU32(command.add(12)), readU32(command.add(16))],
        weapon: readU16(command.add(20)),
        last_weapon_alt_mode_switch: readU16(command.add(22)),
        offhand_index: readU16(command.add(24)),
        forward_move: readS8(command.add(26)),
        right_move: readS8(command.add(27)),
        conditional_angle: readFloat(command.add(28)),
        conditional_byte: readU8(command.add(32)),
        conditional_eleven_bits: readU16(command.add(34)),
        unrecovered_tail_hex: tail
    }};
}}

Interceptor.attach(rawMouse, {{
    onEnter(_) {{
        this.outputEdx = this.context.edx;
        this.outputEsi = this.context.esi;
    }},
    onLeave(_) {{
        const state = threadMouseState();
        state.raw_output_edx = readFloat(this.outputEdx);
        state.raw_output_esi = readFloat(this.outputEsi);
    }}
}});

Interceptor.attach(scaledMouse, {{
    onEnter(args) {{
        this.output0 = args[0];
        this.output1 = args[1];
    }},
    onLeave(_) {{
        const state = threadMouseState();
        state.scaled_0 = readFloat(this.output0);
        state.scaled_1 = readFloat(this.output1);
    }}
}});

Interceptor.attach(createCmd, {{
    onEnter(args) {{
        this.command = this.context.eax;
        this.localClient = args[0].toInt32();
    }},
    onLeave(retval) {{
        const state = threadMouseState();
        const active = clientActive();
        const dvars = {{}};
        for (const [name, rva] of Object.entries(dvarRvas)) dvars[name] = readDvar(rva);
        send({{
            event: 'look_sample',
            source: 'client-native-observed',
            sequence: sequence++,
            timestamp_ms: Date.now(),
            thread_id: Process.getCurrentThreadId(),
            local_client: this.localClient,
            mouse: {{ ...state }},
            fov_sensitivity_scale: active === null ? null : readFloat(active.add(13840)),
            client_viewangles: active === null ? null : readVec3(active.add(13904)),
            dvars: dvars,
            usercmd: readUserCmd(retval.isNull() ? this.command : retval),
            camera: readCameraState()
        }});
        mouseByThread.delete(Process.getCurrentThreadId());
    }}
}});

send({{
    event: 'armed',
    source: 'client-native-observed',
    pid: Process.id,
    module_base: module.base.toString(),
    raw_mouse: rawMouse.toString(),
    scaled_mouse: scaledMouse.toString(),
    create_cmd: createCmd.toString(),
    raw_axis_semantics: 'register outputs preserved until runtime correlation',
    scaled_axis_semantics: 'scaled_0 feeds yaw/side path; scaled_1 feeds pitch/forward path'
}});
"""


def build_dedicated_script(sample_interval_ms: int) -> str:
    return f"""
'use strict';

const plugin = Process.getModuleByName({json.dumps(PLUGIN_NAME)});
const getSample = new NativeFunction(
    plugin.getExportByName('CODOL_GameServerGetWorldPlayerSampleV2'),
    'bool',
    ['uint32', 'pointer', 'uint32']
);
const buffer = Memory.alloc(352);
let lastFrame = null;
let sequence = 0;

function u32(offset) {{ return buffer.add(offset).readU32(); }}
function s32(offset) {{ return buffer.add(offset).readS32(); }}
function f32(offset) {{ return buffer.add(offset).readFloat(); }}
function vec3(offset) {{ return [f32(offset), f32(offset + 4), f32(offset + 8)]; }}

function sample() {{
    if (!getSample(0, buffer, 352)) return;
    const frame = u32(8);
    if (frame === lastFrame) return;
    lastFrame = frame;
    send({{
        event: 'dedicated_sample',
        source: 'dedicated-authoritative-observed',
        sequence: sequence++,
        timestamp_ms: Date.now(),
        frame_number: frame,
        server_time: u32(12),
        usercmd: {{
            valid: u32(16) !== 0,
            command_time: u32(20),
            buttons: u32(24),
            angles: [u32(28), u32(32), u32(36)],
            weapon: u32(40),
            offhand_index: u32(44),
            last_weapon_alt_mode_switch: u32(48),
            forward_move: s32(52),
            right_move: s32(56)
        }},
        playerstate: {{
            command_time: u32(60),
            origin: vec3(64),
            velocity: vec3(76),
            ground_entity_num: u32(88),
            gravity: u32(92),
            speed: u32(96),
            move_speed_scale_multiplier: f32(100),
            pm_time: u32(104),
            pm_flags: u32(108),
            pm_type: u32(192),
            viewangles: vec3(196),
            delta_angles: vec3(208),
            ladder_vector: vec3(220),
            sprint_button_up_required: u32(232),
            sprint_delay: u32(236),
            last_sprint_start: u32(240),
            last_sprint_end: u32(244),
            sprint_start_max_length: u32(248),
            mantle_yaw: f32(252),
            mantle_timer: u32(256),
            mantle_transition_index: u32(260),
            mantle_flags: u32(264),
            weapon_position_fraction: f32(268),
            weapon_anim: [u32(272), u32(276)],
            weapon_time: [s32(280), s32(284)],
            weapon_delay: [s32(288), s32(292)],
            weapon_state: [u32(296), u32(300)],
            weapon_hand_flags: [u32(304), u32(308)],
            weapon_shot_count: [u32(312), u32(316)],
            torso_timer: u32(320),
            torso_anim: u32(324),
            legs_timer: u32(328),
            legs_anim: u32(332),
            prone_direction: f32(336),
            prone_direction_pitch: f32(340),
            prone_torso_pitch: f32(344),
            bob_cycle: u32(348)
        }}
    }});
}}

setInterval(sample, {sample_interval_ms});
send({{
    event: 'dedicated_armed',
    source: 'dedicated-authoritative-observed',
    pid: Process.id,
    plugin_path: plugin.path,
    sample_v2: plugin.getExportByName('CODOL_GameServerGetWorldPlayerSampleV2').toString(),
    sample_interval_ms: {sample_interval_ms}
}});
"""


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    samples = [row for row in rows if row.get("event") == "look_sample"]
    command_times = [
        row["usercmd"].get("command_time")
        for row in samples
        if isinstance(row.get("usercmd"), dict)
        and isinstance(row["usercmd"].get("command_time"), int)
    ]
    mouse_samples = [
        row
        for row in samples
        if isinstance(row.get("mouse"), dict)
        and any(
            isinstance(row["mouse"].get(name), (int, float))
            and row["mouse"].get(name) != 0
            for name in ("raw_output_edx", "raw_output_esi")
        )
    ]
    summary: dict[str, Any] = {
        "sample_count": len(samples),
        "mouse_input_sample_count": len(mouse_samples),
        "command_time_first": command_times[0] if command_times else None,
        "command_time_last": command_times[-1] if command_times else None,
        "command_time_monotonic": all(
            right >= left for left, right in zip(command_times, command_times[1:])
        ),
        "camera_sample_count": sum(isinstance(row.get("camera"), dict) for row in samples),
        "dedicated_sample_count": sum(
            row.get("event") == "dedicated_sample" for row in rows
        ),
    }
    yaw_metrics = summarize_yaw(samples)
    if yaw_metrics:
        summary["yaw_metrics"] = yaw_metrics
    return summary


def _angle_delta(left: float, right: float) -> float:
    delta = (left - right) % 360.0
    if delta > 180.0:
        delta -= 360.0
    return delta


def _axis_value(value: Any, axis: int) -> float | None:
    if not isinstance(value, list) or len(value) <= axis:
        return None
    result = value[axis]
    return float(result) if isinstance(result, (int, float)) else None


def summarize_yaw(samples: list[dict[str, Any]]) -> dict[str, Any]:
    scale_ratios: list[float] = []
    input_residuals: list[float] = []
    predicted_snapshot_errors: list[float] = []
    render_steps: list[float] = []
    sprint_render_steps: list[float] = []
    non_sprint_render_steps: list[float] = []
    mouse_yaw_samples = 0

    previous: dict[str, Any] | None = None
    for sample in samples:
        mouse = sample.get("mouse")
        raw = mouse.get("raw_output_esi") if isinstance(mouse, dict) else None
        scaled = mouse.get("scaled_0") if isinstance(mouse, dict) else None
        if isinstance(raw, (int, float)) and raw != 0 and isinstance(
            scaled, (int, float)
        ):
            mouse_yaw_samples += 1
            scale_ratios.append(float(scaled) / float(raw))
            dvars = sample.get("dvars")
            yaw_dvar = dvars.get("m_yaw_candidate") if isinstance(dvars, dict) else None
            yaw_scale = yaw_dvar.get("current_float") if isinstance(yaw_dvar, dict) else None
            client_yaw = _axis_value(sample.get("client_viewangles"), 1)
            previous_client_yaw = (
                _axis_value(previous.get("client_viewangles"), 1)
                if previous is not None
                else None
            )
            if (
                isinstance(yaw_scale, (int, float))
                and client_yaw is not None
                and previous_client_yaw is not None
            ):
                actual = _angle_delta(client_yaw, previous_client_yaw)
                expected = -float(scaled) * float(yaw_scale)
                input_residuals.append(abs(actual - expected))

        camera = sample.get("camera")
        if isinstance(camera, dict):
            predicted = camera.get("predicted")
            snapshot = camera.get("snapshot")
            predicted_yaw = (
                _axis_value(predicted.get("viewangles"), 1)
                if isinstance(predicted, dict)
                else None
            )
            snapshot_yaw = (
                _axis_value(snapshot.get("viewangles"), 1)
                if isinstance(snapshot, dict)
                else None
            )
            if predicted_yaw is not None and snapshot_yaw is not None:
                predicted_snapshot_errors.append(
                    abs(_angle_delta(predicted_yaw, snapshot_yaw))
                )

            current_refdef_yaw = _axis_value(camera.get("refdef_viewangles"), 1)
            previous_camera = previous.get("camera") if previous is not None else None
            previous_refdef_yaw = (
                _axis_value(previous_camera.get("refdef_viewangles"), 1)
                if isinstance(previous_camera, dict)
                else None
            )
            if current_refdef_yaw is not None and previous_refdef_yaw is not None:
                step = abs(_angle_delta(current_refdef_yaw, previous_refdef_yaw))
                render_steps.append(step)
                pm_flags = predicted.get("pm_flags") if isinstance(predicted, dict) else None
                if isinstance(pm_flags, int) and pm_flags & 0x4000:
                    sprint_render_steps.append(step)
                else:
                    non_sprint_render_steps.append(step)
        previous = sample

    if not scale_ratios and not predicted_snapshot_errors and not render_steps:
        return {}
    return {
        "mouse_yaw_sample_count": mouse_yaw_samples,
        "scaled_yaw_per_raw_min": min(scale_ratios) if scale_ratios else None,
        "scaled_yaw_per_raw_max": max(scale_ratios) if scale_ratios else None,
        "input_projection_residual_max": (
            max(input_residuals) if input_residuals else None
        ),
        "predicted_snapshot_yaw_error_max": (
            max(predicted_snapshot_errors) if predicted_snapshot_errors else None
        ),
        "render_yaw_step_max": max(render_steps) if render_steps else None,
        "sprint_render_yaw_sample_count": len(sprint_render_steps),
        "sprint_render_yaw_step_max": (
            max(sprint_render_steps) if sprint_render_steps else None
        ),
        "non_sprint_render_yaw_step_max": (
            max(non_sprint_render_steps) if non_sprint_render_steps else None
        ),
    }


def _find_window(pid: int) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    result = 0

    @callback_type
    def callback(hwnd: int, _lparam: int) -> bool:
        nonlocal result
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            result = hwnd
            return False
        return True

    user32.EnumWindows(callback, 0)
    return result


def simulate_relative_mouse(
    pid: int,
    dx: int,
    dy: int,
    count: int,
    interval_seconds: float,
    delay_seconds: float,
) -> None:
    if dx == 0 and dy == 0:
        return
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = _find_window(pid)
    if not hwnd:
        raise RuntimeError("could not find the CODOL client window for synthetic input")
    time.sleep(delay_seconds)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.25)
    for _ in range(count):
        # This is an explicitly synthetic trigger. Recording remains observation-only.
        user32.mouse_event(0x0001, dx, dy, 0, 0)
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--dedicated-pid", type=int)
    parser.add_argument("--dedicated-sample-interval", type=float, default=0.02)
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulate-dx", type=int, default=0)
    parser.add_argument("--simulate-dy", type=int, default=0)
    parser.add_argument("--simulate-count", type=int, default=60)
    parser.add_argument("--simulate-interval", type=float, default=0.02)
    parser.add_argument("--simulate-delay", type=float, default=1.0)
    args = parser.parse_args()
    if args.duration <= 0 or args.duration > 3600:
        parser.error("--duration must be in (0, 3600]")
    if args.simulate_count <= 0 or args.simulate_count > 10000:
        parser.error("--simulate-count must be in [1, 10000]")
    if args.simulate_interval < 0 or args.simulate_delay < 0:
        parser.error("synthetic input timing cannot be negative")
    if args.dedicated_sample_interval <= 0 or args.dedicated_sample_interval > 1:
        parser.error("--dedicated-sample-interval must be in (0, 1]")
    if args.output.exists():
        parser.error(f"--output already exists: {args.output}")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    dedicated_session: frida.core.Session | None = None
    dedicated_script: frida.core.Script | None = None
    rows: list[dict[str, Any]] = []
    stopped = threading.Event()
    script = session.create_script(build_script())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_lock = threading.RLock()

    def record(row: dict[str, Any]) -> None:
        with record_lock:
            rows.append(row)
            with args.output.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(
                    json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n"
                )
                stream.flush()

    def on_message(message: dict, _data: bytes | None) -> None:
        if message.get("type") == "error":
            record({"event": "error", "error": message.get("description", "Frida error")})
            stopped.set()
            return
        payload = message.get("payload", message)
        if isinstance(payload, dict):
            record(payload)

    script.on("message", on_message)
    script.load()
    if args.dedicated_pid is not None:
        dedicated_session = device.attach(args.dedicated_pid)
        dedicated_script = dedicated_session.create_script(
            build_dedicated_script(
                max(1, round(args.dedicated_sample_interval * 1000.0))
            )
        )
        dedicated_script.on("message", on_message)
        dedicated_script.load()
    record(
        {
            "event": "attached",
            "pid": pid,
            "duration": args.duration,
            "synthetic_input": {
                "enabled": args.simulate_dx != 0 or args.simulate_dy != 0,
                "source": "win32-mouse_event",
                "dx": args.simulate_dx,
                "dy": args.simulate_dy,
                "count": args.simulate_count,
                "interval_seconds": args.simulate_interval,
            },
        }
    )

    simulator: threading.Thread | None = None
    if args.simulate_dx != 0 or args.simulate_dy != 0:
        simulator = threading.Thread(
            target=simulate_relative_mouse,
            args=(
                pid,
                args.simulate_dx,
                args.simulate_dy,
                args.simulate_count,
                args.simulate_interval,
                args.simulate_delay,
            ),
            daemon=True,
        )
        simulator.start()

    stopped.wait(args.duration)
    if simulator is not None:
        simulator.join(timeout=2.0)
    try:
        script.unload()
    finally:
        session.detach()
    if dedicated_script is not None:
        dedicated_script.unload()
    if dedicated_session is not None:
        dedicated_session.detach()

    summary = {
        "ok": not any(row.get("event") == "error" for row in rows),
        "pid": pid,
        "dedicated_pid": args.dedicated_pid,
        "output": str(args.output),
        **summarize(rows),
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
