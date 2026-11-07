#!/usr/bin/env python3
"""Queue a command through CODOL's native client command buffer."""

from __future__ import annotations

import argparse
import json
import threading
import time

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
CBUF_ADD_TEXT_RVA = 0x18D840
COMMAND_LIST_HEAD_RVA = 0x2A0111C
CONNECTION_STATE_RVA = 0x162E7EC


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


def build_script(
    command: str,
    local_client: int,
    observe_seconds: float,
) -> str:
    command = command.rstrip("\n") + "\n"
    return f"""
'use strict';
try {{
    const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
    const target = module.base.add({CBUF_ADD_TEXT_RVA});
    const connectionState = module.base.add({CONNECTION_STATE_RVA});
    const command = {json.dumps(command)};
    const commandName = command.trim().split(/\\s+/, 1)[0];
    const commandText = Memory.allocUtf8String(command);
    let commandNode = module.base.add({COMMAND_LIST_HEAD_RVA}).readPointer();
    let commandHandler = null;
    for (let index = 0; !commandNode.isNull() && index < 8192; ++index) {{
        const namePointer = commandNode.add(4).readPointer();
        if (!namePointer.isNull() && namePointer.readUtf8String() === commandName) {{
            commandHandler = commandNode.add(8).readPointer();
            break;
        }}
        commandNode = commandNode.readPointer();
    }}
    if (commandHandler !== null && !commandHandler.isNull() && {observe_seconds} > 0) {{
        Interceptor.attach(commandHandler, {{
            onEnter(_args) {{
                send({{
                    ok: true,
                    event: 'handler-entered',
                    command_name: commandName,
                    command_handler: commandHandler.toString(),
                    thread_id: Process.getCurrentThreadId()
                }});
            }}
        }});
    }}
    const thunk = Memory.alloc(Process.pageSize);
    const targetValue = target.toUInt32();
    thunk.writeByteArray([
        0x8B, 0x44, 0x24, 0x04,
        0x8B, 0x4C, 0x24, 0x08,
        0xBA,
        targetValue & 0xFF,
        (targetValue >>> 8) & 0xFF,
        (targetValue >>> 16) & 0xFF,
        (targetValue >>> 24) & 0xFF,
        0xFF, 0xD2,
        0xC3
    ]);
    Memory.protect(thunk, Process.pageSize, 'r-x');
    // Frida owns the cdecl call frame. A stdcall thunk corrupts the return
    // context when invoked from an Interceptor callback on this x86 client.
    const invoke = new NativeFunction(thunk, 'void', ['pointer', 'int']);

    send({{
        ok: true,
        event: 'armed',
        pid: Process.id,
        connection_state: connectionState.readU32(),
        command: command.slice(0, -1)
    }});
    if (connectionState.readU32() !== 10)
        throw new Error('active-world connection state changed before dispatch');
    invoke(commandText, {local_client});
    send({{
        ok: true,
        event: 'invoked',
        pid: Process.id,
        source: 'frida-script-load',
        target: target.toString(),
        thread_id: Process.getCurrentThreadId(),
        connection_state: connectionState.readU32(),
        local_client: {local_client},
        command: command.slice(0, -1),
        command_name: commandName,
        command_node: commandNode.isNull() ? null : commandNode.toString(),
        command_handler: commandHandler === null || commandHandler.isNull()
            ? null
            : commandHandler.toString()
    }});
}} catch (error) {{
    send({{ ok: false, event: 'error', source: 'setup', error: error.stack || error.message }});
}}
"""


def build_state_observer_script() -> str:
    return f"""
'use strict';
const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const connectionState = module.base.add({CONNECTION_STATE_RVA});
function reportState() {{
    send({{
        event: 'connection-state',
        state: connectionState.readU32()
    }});
}}
reportState();
setInterval(reportState, 50);
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--local-client", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--stable-seconds",
        type=float,
        default=5.0,
        help="require continuous active-world client state before dispatch",
    )
    parser.add_argument(
        "--observe-seconds",
        type=float,
        default=0.0,
        help="keep the Frida session attached and count native command-handler calls",
    )
    args = parser.parse_args()
    if not 0 <= args.local_client < 2:
        parser.error("--local-client must be 0 or 1")
    if not args.command or "\0" in args.command:
        parser.error("command must be non-empty and cannot contain NUL")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.stable_seconds < 0 or args.stable_seconds >= args.timeout:
        parser.error("--stable-seconds must be non-negative and less than --timeout")
    if args.observe_seconds < 0:
        parser.error("--observe-seconds cannot be negative")

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    session = device.attach(pid)
    done = threading.Event()
    state_changed = threading.Event()
    result: dict[str, object] = {}
    observed_state: int | None = None

    observer = session.create_script(build_state_observer_script())

    def on_state(message: dict, _data: bytes | None) -> None:
        nonlocal observed_state
        payload = message.get("payload", message)
        if isinstance(payload, dict) and payload.get("event") == "connection-state":
            observed_state = int(payload["state"])
            state_changed.set()

    observer.on("message", on_state)
    deadline = time.monotonic() + args.timeout
    ready_since: float | None = None
    try:
        observer.load()
        while time.monotonic() < deadline:
            state_changed.wait(min(0.1, max(0.0, deadline - time.monotonic())))
            state_changed.clear()
            now = time.monotonic()
            if observed_state == 10:
                if ready_since is None:
                    ready_since = now
                if now - ready_since >= args.stable_seconds:
                    break
            else:
                ready_since = None
        else:
            raise TimeoutError("timed out waiting for stable active-world client state")
    finally:
        observer.unload()

    source = build_script(args.command, args.local_client, args.observe_seconds)
    script = session.create_script(source)

    def on_message(message: dict, _data: bytes | None) -> None:
        payload = message.get("payload", message)
        if isinstance(payload, dict):
            if payload.get("event") == "handler-entered":
                result["handler_dispatch_count"] = (
                    int(result.get("handler_dispatch_count", 0)) + 1
                )
                result["handler_thread_id"] = payload.get("thread_id")
            elif payload.get("event") in {"invoked", "error"}:
                result.update(payload)
                done.set()

    script.on("message", on_message)
    try:
        script.load()
        done.wait(max(0.0, deadline - time.monotonic()))
        if not done.is_set():
            raise TimeoutError("timed out waiting for game-thread command dispatch")
        if result.get("ok") and args.observe_seconds:
            time.sleep(args.observe_seconds)
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
