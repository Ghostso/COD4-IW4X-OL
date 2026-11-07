#!/usr/bin/env python3
"""Trace CODOL quick-match and ready actions without modifying game state."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from threading import Event
from typing import Any

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
const quickMatchHandler = module.base.add(0x2AD510);
const quickMatchStart = module.base.add(0x2F2C10);
const setReadyHandler = module.base.add(0x2B2230);
const roomObjectSlot = module.base.add(0x74B0708);

function readU8(pointer, offset) {
    try { return pointer.add(offset).readU8(); } catch (_) { return null; }
}

function readPointer(pointer, offset) {
    try { return pointer.add(offset).readPointer(); } catch (_) { return null; }
}

function readHex(pointer, size) {
    try {
        const data = pointer.readByteArray(size);
        if (data === null) return null;
        return Array.from(new Uint8Array(data), value => value.toString(16).padStart(2, '0')).join('');
    } catch (_) {
        return null;
    }
}

function readGameString(object, offset) {
    const value = readPointer(object, offset);
    if (value === null || value.isNull()) return '';
    try { return value.readUtf8String(); } catch (_) { return null; }
}

function roomState() {
    const room = readPointer(roomObjectSlot, 0);
    if (room === null || room.isNull()) {
        return { room: null, vtable: null, set_ready_target: null };
    }
    const vtable = readPointer(room, 0);
    const target = vtable === null || vtable.isNull() ? null : readPointer(vtable, 0x74);
    return {
        room: room.toString(),
        vtable: vtable === null ? null : vtable.toString(),
        set_ready_target: target === null ? null : target.toString()
    };
}

Interceptor.attach(quickMatchHandler, {
    onEnter(args) {
        send({
            event: 'quick_match_handler',
            thread_id: Process.getCurrentThreadId(),
            action_args: args[0].toString(),
            room_state: roomState()
        });
    }
});

Interceptor.attach(quickMatchStart, {
    onEnter(args) {
        const config = args[2];
        send({
            event: 'quick_match_start',
            thread_id: Process.getCurrentThreadId(),
            match_type: args[0].toInt32(),
            callback: args[1].toString(),
            config: config.toString(),
            config_hex: readHex(config, 16),
            mode: readGameString(config, 0),
            map: readGameString(config, 4),
            playlist_id: readU8(config, 8),
            league: readU8(config, 9),
            max_player: readU8(config, 10),
            room_state: roomState()
        });
    }
});

Interceptor.attach(setReadyHandler, {
    onEnter(args) {
        const actionArgs = args[0];
        const value = readPointer(actionArgs, 16);
        send({
            event: 'set_ready',
            thread_id: Process.getCurrentThreadId(),
            action_args: actionArgs.toString(),
            value_object: value === null ? null : value.toString(),
            ready: value === null ? null : readU8(value, 16),
            room_state: roomState()
        });
    }
});

send({
    event: 'ready',
    module_base: module.base.toString(),
    quick_match_handler: quickMatchHandler.toString(),
    quick_match_start: quickMatchStart.toString(),
    set_ready_handler: setReadyHandler.toString(),
    room_object_slot: roomObjectSlot.toString(),
    room_state: roomState()
});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=300.0)
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
            payload = message.get("payload", {})
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
