#!/usr/bin/env python3
"""Trace CODOL session admission and disconnects without changing game state."""

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


def build_script() -> str:
    return r"""
'use strict';

const module = Process.mainModule;
const cbufAddText = module.base.add(0x18D840);
const packetEvent = module.base.add(0x67520);
const decodeMessage = module.base.add(0x6BF80);
const parseGameState = module.base.add(0x6DEA0);
const parseSnapshot = module.base.add(0x6D170);
// Current 3.19.26.22 IDB: sub_4F82E0, the variadic Com_Error entry.  The old
// 0x197D20 RVA belongs to a different image revision.
const comError = module.base.add(0xF82E0);
const codolUnhandledExceptionFilter = module.base.add(0x23C820);
// These addresses come from the current 3.19.26.22 out.exe IDB.  The older
// client probe used globals from a different image revision, which read zero
// throughout a real join and concealed the disconnect transition.
const connectionStates = module.base.add(0x72446B0);
const encodedClientConnection = module.base.add(0x2F1C0C8);
const setConnectionState = module.base.add(0x1BE030);
const disconnectCommand = module.base.add(0x1AA610);
const demoDisconnectCommand = module.base.add(0x1AAD70);
const disconnectKeepSession = module.base.add(0x204390);
const connectFromParty = module.base.add(0x1C8150);
const completeDisconnect = module.base.add(0x1C0FD0);
const configStringValidator = module.base.add(0x114540);

const unavailableHooks = [];
function safeAttach(name, address, callbacks) {
    try {
        Interceptor.attach(address, callbacks);
        return true;
    } catch (error) {
        const failure = { name: name, address: address.toString(), error: String(error) };
        unavailableHooks.push(failure);
        send(Object.assign({ event: 'hook_unavailable' }, failure));
        return false;
    }
}

function readU32(address, offset) {
    try { return address.add(offset || 0).readU32(); } catch (_) { return null; }
}

function readPointer(address, offset) {
    try { return address.add(offset || 0).readPointer(); } catch (_) { return null; }
}

function readString(address) {
    try {
        if (address === null || address.isNull()) return null;
        return address.readCString();
    } catch (_) {
        return null;
    }
}

function readReliableState() {
    const encoded = readU32(encodedClientConnection, 0);
    if (encoded === null) return null;
    const clientConnection = ptr((encoded ^ 0xD362501F) >>> 0);
    return {
        address: clientConnection.toString(),
        reliable_sequence: readU32(clientConnection, 0x140),
        reliable_acknowledge: readU32(clientConnection, 0x144),
        server_message_sequence: readU32(clientConnection, 0x40148)
    };
}

function readJoinState() {
    return {
        connection_state: readU32(connectionStates, 0),
        reliable: readReliableState()
    };
}

function captureBacktrace(context) {
    try {
        return Thread.backtrace(context, Backtracer.ACCURATE)
            .slice(0, 24)
            .map(address => {
                const owner = Process.findModuleByAddress(address);
                return owner === null
                    ? address.toString()
                    : owner.name + '+' + address.sub(owner.base).toString();
            });
    } catch (error) {
        return ['<backtrace failed: ' + error.message + '>'];
    }
}

// CA_ACTIVE only lasts for about a second on the failing Wetwork join.  The
// transition back to CA_DISCONNECTED bypasses the normal state setter, so arm
// a per-thread hardware write watchpoint only after CA_ACTIVE is observed.
// This catches direct stores and bulk clears without perturbing the earlier
// admission handshake.
let stateWatchpointArmed = false;
let stateWatchpointCaptured = false;
let watchedThreadIds = [];

function unsetStateWatchpoints() {
    const failures = [];
    for (const thread of Process.enumerateThreads()) {
        try {
            thread.unsetHardwareWatchpoint(0);
        } catch (error) {
            failures.push({ thread_id: thread.id, error: String(error) });
        }
    }
    watchedThreadIds = [];
    return failures;
}

function armStateWatchpoints() {
    if (stateWatchpointArmed || stateWatchpointCaptured)
        return;

    const armed = [];
    const failures = [];
    for (const thread of Process.enumerateThreads()) {
        try {
            thread.setHardwareWatchpoint(0, connectionStates, 4, 'w');
            armed.push(thread.id);
        } catch (error) {
            failures.push({ thread_id: thread.id, error: String(error) });
        }
    }
    watchedThreadIds = armed;
    stateWatchpointArmed = armed.length !== 0;
    send({
        event: 'state_watchpoint_armed',
        timestamp_ms: Date.now(),
        address: connectionStates.toString(),
        thread_ids: armed,
        failures: failures,
        state: readJoinState()
    });
}

Process.setExceptionHandler(details => {
    if (!stateWatchpointArmed || stateWatchpointCaptured)
        return false;
    if (details.type !== 'single-step' && details.type !== 'breakpoint')
        return false;

    stateWatchpointCaptured = true;
    stateWatchpointArmed = false;
    const pc = details.context.pc;
    let instructionBytes = null;
    try {
        instructionBytes = Array.from(new Uint8Array(
            pc.sub(24).readByteArray(56))).map(value =>
                value.toString(16).padStart(2, '0')).join('');
    } catch (_) {}
    const memory = details.memory === undefined ? null : {
        operation: details.memory.operation,
        address: details.memory.address.toString()
    };
    const armedThreadIds = watchedThreadIds.slice();
    const unsetFailures = unsetStateWatchpoints();
    send({
        event: 'state_watchpoint_hit',
        timestamp_ms: Date.now(),
        exception_type: details.type,
        exception_address: details.address.toString(),
        pc: pc.toString(),
        pc_rva: pc.sub(module.base).toString(),
        thread_id: Process.getCurrentThreadId(),
        memory: memory,
        instruction_window_start: pc.sub(24).toString(),
        instruction_window_hex: instructionBytes,
        watched_thread_ids: armedThreadIds,
        unset_failures: unsetFailures,
        state: readJoinState(),
        backtrace: captureBacktrace(details.context)
    });
    return true;
});

// Verify the API against every existing thread before asking for a live join.
// The probe immediately removes each test point while the client is idle.
const watchpointCapability = [];
for (const thread of Process.enumerateThreads()) {
    try {
        thread.setHardwareWatchpoint(0, connectionStates, 4, 'w');
        thread.unsetHardwareWatchpoint(0);
        watchpointCapability.push({ thread_id: thread.id, available: true });
    } catch (error) {
        watchpointCapability.push({
            thread_id: thread.id,
            available: false,
            error: String(error)
        });
    }
}

safeAttach('cbuf_add_text', cbufAddText, {
    onEnter(_) {
        const returnAddress = this.context.esp.readPointer();
        const owner = Process.findModuleByAddress(returnAddress);
        send({
            event: 'cbuf_command',
            timestamp_ms: Date.now(),
            thread_id: Process.getCurrentThreadId(),
            local_client: this.context.ecx.toInt32(),
            command: readString(this.context.eax),
            return_address: returnAddress.toString(),
            caller_module: owner === null ? null : owner.name,
            caller_rva: owner === null ? null : returnAddress.sub(owner.base).toString(),
            state: readJoinState()
        });
    }
});

safeAttach('packet_event', packetEvent, {
    onLeave(retval) {
        send({
            event: 'packet_event_leave',
            timestamp_ms: Date.now(),
            accepted: retval.toInt32(),
            state: readJoinState()
        });
    }
});

safeAttach('decode_message', decodeMessage, {
    onEnter(args) { this.size = args[1].toInt32(); },
    onLeave(_) {
        send({
            event: 'decode_message',
            timestamp_ms: Date.now(),
            size: this.size,
            state: readJoinState()
        });
    }
});

safeAttach('parse_gamestate', parseGameState, {
    onEnter(_) {
        send({ event: 'parse_gamestate_enter', timestamp_ms: Date.now(), state: readJoinState() });
    },
    onLeave(_) {
        send({ event: 'parse_gamestate_leave', timestamp_ms: Date.now(), state: readJoinState() });
    }
});

safeAttach('parse_snapshot', parseSnapshot, {
    onEnter(_) {
        this.msg = this.context.ecx;
        send({
            event: 'parse_snapshot_enter',
            timestamp_ms: Date.now(),
            readcount: readU32(this.msg, 28),
            bit: readU32(this.msg, 32),
            overflowed: readU32(this.msg, 0),
            state: readJoinState()
        });
    },
    onLeave(_) {
        send({
            event: 'parse_snapshot_leave',
            timestamp_ms: Date.now(),
            readcount: readU32(this.msg, 28),
            bit: readU32(this.msg, 32),
            overflowed: readU32(this.msg, 0),
            state: readJoinState()
        });
    }
});

safeAttach('com_error', comError, {
    onEnter(args) {
        const values = [];
        for (let index = 2; index < 7; ++index) {
            values.push({ raw: args[index].toString(), string: readString(args[index]) });
        }
        send({
            event: 'com_error',
            timestamp_ms: Date.now(),
            code: args[0].toInt32(),
            format: readString(args[1]),
            arguments: values,
            state: readJoinState(),
            backtrace: captureBacktrace(this.context)
        });
    }
});

safeAttach('configstring_validator', configStringValidator, {
    onEnter(args) {
        const index = args[0].toInt32();
        let typeByte = null;
        try { typeByte = module.base.add(0x73D8250).add(index).readU8(); }
        catch (_) {}
        send({
            event: 'configstring_validate',
            timestamp_ms: Date.now(),
            index: index,
            value: readString(args[1]),
            type_byte: typeByte,
            accepted: typeByte === null || typeByte === 0x15 || typeByte >= 0x17,
            return_address: this.returnAddress.sub(module.base).toString(),
            state: readJoinState()
        });
    }
});

safeAttach('unhandled_exception_filter', codolUnhandledExceptionFilter, {
    onEnter(args) {
        const exceptionPointers = args[0];
        const exceptionRecord = readPointer(exceptionPointers, 0);
        const contextRecord = readPointer(exceptionPointers, 4);
        const exceptionAddress = exceptionRecord === null ? null : readU32(exceptionRecord, 12);
        send({
            event: 'unhandled_exception',
            timestamp_ms: Date.now(),
            exception_code: exceptionRecord === null ? null : readU32(exceptionRecord, 0),
            exception_address: exceptionAddress === null
                ? null
                : ptr(exceptionAddress).sub(module.base).toString(),
            eip: contextRecord === null ? null : readU32(contextRecord, 184),
            state: readJoinState(),
            backtrace: captureBacktrace(this.context)
        });
    }
});

safeAttach('set_connection_state', setConnectionState, {
    onEnter(_) {
        this.localClient = this.context.eax.toInt32();
        this.newState = this.context.edi.toInt32();
        this.oldState = readU32(connectionStates, this.localClient * 32);
        send({
            event: 'connection_state_write',
            timestamp_ms: Date.now(),
            local_client: this.localClient,
            old_state: this.oldState,
            new_state: this.newState,
            return_address: this.returnAddress.sub(module.base).toString(),
            backtrace: captureBacktrace(this.context)
        });
    },
    onLeave(_) {
        send({
            event: 'connection_state_written',
            timestamp_ms: Date.now(),
            local_client: this.localClient,
            observed_state: readU32(connectionStates, this.localClient * 32)
        });
    }
});

function traceDisconnectEntry(name, address) {
    safeAttach(name, address, {
        onEnter(_) {
            send({
                event: 'disconnect_path',
                timestamp_ms: Date.now(),
                path: name,
                return_address: this.returnAddress.sub(module.base).toString(),
                state: readJoinState(),
                backtrace: captureBacktrace(this.context)
            });
        }
    });
}

traceDisconnectEntry('disconnect_command', disconnectCommand);
traceDisconnectEntry('demo_disconnect_command', demoDisconnectCommand);
traceDisconnectEntry('disconnect_keep_session', disconnectKeepSession);
traceDisconnectEntry('connect_from_party', connectFromParty);
traceDisconnectEntry('complete_disconnect', completeDisconnect);

const processExitHooks = [];
const hookedProcessExitAddresses = new Set();
function traceProcessExit(moduleName, exportName, argumentReader) {
    const owner = Process.findModuleByName(moduleName);
    if (owner === null) return;
    const address = owner.findExportByName(exportName);
    if (address === null || hookedProcessExitAddresses.has(address.toString())) return;
    hookedProcessExitAddresses.add(address.toString());
    const installed = safeAttach('process_exit_' + owner.name + '_' + exportName, address, {
        onEnter(args) {
            let details = {};
            try { details = argumentReader(args); }
            catch (error) { details = { argument_error: error.message }; }
            send({
                event: 'process_exit_called',
                timestamp_ms: Date.now(),
                api_module: owner.name,
                api: exportName,
                details: details,
                state: readJoinState(),
                backtrace: captureBacktrace(this.context)
            });
        }
    });
    if (installed) {
        processExitHooks.push({ module: owner.name, name: exportName, address: address.toString() });
    }
}

for (const moduleName of ['kernel32.dll', 'KernelBase.dll']) {
    traceProcessExit(moduleName, 'ExitProcess', args => ({ exit_code: args[0].toUInt32() }));
    traceProcessExit(moduleName, 'TerminateProcess', args => ({
        process_handle: args[0].toString(),
        exit_code: args[1].toUInt32()
    }));
}
traceProcessExit('ntdll.dll', 'RtlExitUserProcess', args => ({ exit_code: args[0].toUInt32() }));
traceProcessExit('ntdll.dll', 'NtTerminateProcess', args => ({
    process_handle: args[0].toString(),
    exit_code: args[1].toUInt32()
}));

let previousState = JSON.stringify(readJoinState());
setInterval(() => {
    const state = readJoinState();
    if (state.connection_state === 10)
        armStateWatchpoints();
    const encoded = JSON.stringify(state);
    if (encoded === previousState) return;
    previousState = encoded;
    send({ event: 'join_state_change', timestamp_ms: Date.now(), state: state });
}, 100);

send({
    event: 'ready',
    join_only: true,
    pid: Process.id,
    module_base: module.base.toString(),
    cbuf_add_text: cbufAddText.toString(),
    packet_event: packetEvent.toString(),
    decode_message: decodeMessage.toString(),
    parse_gamestate: parseGameState.toString(),
    parse_snapshot: parseSnapshot.toString(),
    com_error: comError.toString(),
    configstring_validator: configStringValidator.toString(),
    set_connection_state: setConnectionState.toString(),
    connection_states: connectionStates.toString(),
    encoded_client_connection: encodedClientConnection.toString(),
    hardware_watchpoints: watchpointCapability,
    unavailable_hooks: unavailableHooks,
    process_exit_hooks: processExitHooks,
    state: readJoinState()
});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--cbuf-log", type=Path, required=True)
    args = parser.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.cbuf_log.parent.mkdir(parents=True, exist_ok=True)
    stopped = Event()

    def append(path: Path, event: str, **payload: Any) -> None:
        record = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            **payload,
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    device = frida.get_local_device()
    session = device.attach(args.pid)
    script = session.create_script(build_script())

    def on_message(message: dict[str, Any], _data: bytes | None) -> None:
        if message.get("type") != "send":
            append(args.log, "frida_message", message=message)
            return
        raw = message.get("payload")
        payload = dict(raw) if isinstance(raw, dict) else {}
        event = str(payload.pop("event", "message"))
        append(args.log, event, **payload)
        if event in {"ready", "cbuf_command"}:
            append(args.cbuf_log, event, **payload)

    def on_detached(reason: str, crash: Any) -> None:
        append(args.log, "detached", reason=reason, crash=crash)
        stopped.set()

    script.on("message", on_message)
    session.on("detached", on_detached)
    script.load()
    append(args.log, "attached", pid=args.pid, duration=args.duration)
    deadline = time.monotonic() + args.duration
    try:
        while time.monotonic() < deadline and not stopped.wait(0.1):
            pass
    except KeyboardInterrupt:
        append(args.log, "interrupted")
    finally:
        try:
            script.unload()
        except Exception:
            pass
        try:
            session.detach()
        except Exception:
            pass
        append(args.log, "stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
