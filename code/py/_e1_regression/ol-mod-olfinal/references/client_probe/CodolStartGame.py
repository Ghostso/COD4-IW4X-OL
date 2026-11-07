#!/usr/bin/env python3
"""Trigger CODOL's recovered room start-game path on the game's UI thread."""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import threading
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


IMAGE_NAME = "codoMP_client_shipRetail.exe"
GET_READY_STATE_RVA = 0x2E5320
START_GAME_RVA = 0x2E4A20
ROOM_SINGLETON_RVA = 0x74B0708


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help=f"Running {IMAGE_NAME} process ID")
    parser.add_argument(
        "--mode",
        choices=("status", "local", "allocate"),
        default="status",
        help=(
            "status only reads the room ready flag; local and allocate directly invoke the "
            "internal start path and may race the normal room state machine"
        ),
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser.parse_args()


def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested
    matches = [
        process
        for process in device.enumerate_processes()
        if process.name.lower() == IMAGE_NAME.lower()
    ]
    if not matches:
        raise SystemExit(f"No running {IMAGE_NAME} process was found.")
    return max(process.pid for process in matches)


def find_window(pid: int) -> tuple[int, int]:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    matches: list[tuple[int, int]] = []

    @callback_type
    def visit(hwnd: int, _lparam: int) -> bool:
        owner_pid = wintypes.DWORD()
        thread_id = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if owner_pid.value == pid and user32.IsWindowVisible(hwnd):
            matches.append((int(hwnd), int(thread_id)))
        return True

    if not user32.EnumWindows(visit, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if not matches:
        raise SystemExit(f"PID {pid} has no visible window.")
    return matches[0]


def main() -> int:
    args = parse_args()
    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    hwnd, window_thread_id = find_window(pid)
    done = threading.Event()
    result: dict[str, object] = {}
    allocate = args.mode == "allocate"

    source = f"""
'use strict';

const module = Process.getModuleByName('{IMAGE_NAME}');
const getReadyState = module.base.add({GET_READY_STATE_RVA});
const startGameAddress = module.base.add({START_GAME_RVA});
const roomSingleton = module.base.add({ROOM_SINGLETON_RVA});
const getReady = new NativeFunction(getReadyState, 'int', ['pointer'], 'thiscall');
const startGame = new NativeFunction(
    startGameAddress,
    'void',
    ['pointer', 'int', 'int', 'int'],
    'thiscall'
);
let fired = false;

const user32 = Process.getModuleByName('user32.dll');

function triggerOnWindowThread() {{
        if (fired || Process.getCurrentThreadId() !== {window_thread_id}) return;
        fired = true;
        try {{
            const room = roomSingleton.readPointer();
            if (room.isNull()) throw new Error('dwRoomImp singleton is null');
            const ready = getReady(room);
            if ('{args.mode}' === 'status') {{
                send({{ type: 'status', ready: ready, room: room.toString() }});
                return;
            }}
            if (ready === 0) throw new Error('local room member is not ready');
            send({{
                type: 'triggering',
                thread_id: Process.getCurrentThreadId(),
                module_base: module.base.toString(),
                room: room.toString(),
                start_game: startGameAddress.toString(),
                ready: ready,
                mode: '{args.mode}'
            }});
            startGame(room, {1 if allocate else 0}, -1, 0);
            send({{ type: 'triggered', mode: '{args.mode}' }});
        }} catch (error) {{
            send({{ type: 'error', message: error.stack || error.message }});
        }}
}}

const messageFunctions = ['PeekMessageA', 'PeekMessageW', 'DispatchMessageA', 'DispatchMessageW'];
for (const name of messageFunctions) {{
    const address = user32.findExportByName(name);
    if (address !== null) Interceptor.attach(address, {{ onEnter: triggerOnWindowThread }});
}}

send({{
    type: 'armed',
    pid: Process.id,
    window_thread_id: {window_thread_id},
    message_functions: messageFunctions,
    mode: '{args.mode}'
}});
"""

    session = device.attach(pid)

    def on_message(message: dict, data: bytes | None) -> None:
        if message.get("type") == "send":
            payload = message.get("payload", {})
        else:
            payload = message
        print(json.dumps(payload, ensure_ascii=False))
        if payload.get("type") in {"status", "triggered", "error"}:
            result.update(payload)
            done.set()

    script = session.create_script(source)
    script.on("message", on_message)
    try:
        script.load()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        if not user32.PostMessageW(hwnd, 0, 0, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        if not done.wait(args.timeout):
            print(json.dumps({"type": "timeout", "seconds": args.timeout}))
            return 2
        return 0 if result.get("type") in {"status", "triggered"} else 1
    finally:
        script.unload()
        session.detach()


if __name__ == "__main__":
    raise SystemExit(main())
