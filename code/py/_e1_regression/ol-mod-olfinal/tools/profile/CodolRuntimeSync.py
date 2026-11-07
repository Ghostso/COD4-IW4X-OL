#!/usr/bin/env python3
"""Queue CODOL profile and inventory reloads through the runtime plugin."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


TARGET_NAME = "codoMP_client_shipRetail.exe"
PLUGIN_NAME = "Alwaysoffline.Localnet32"

STATE_NAMES = {
    1: "idle",
    2: "queued",
    3: "in_flight",
    4: "succeeded",
    5: "failed",
}


class RuntimeSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncResult:
    target: str
    generation: int
    state: str
    error_code: int


AGENT_SOURCE = r"""
'use strict';

const plugin = Process.findModuleByName('Alwaysoffline.Localnet32');
if (plugin === null) throw new Error('Alwaysoffline.Localnet32 is not loaded');

const requestProfile = new NativeFunction(
    plugin.getExportByName('CODOL_RequestProfileReload'), 'uint', ['uint']);
const getProfileStatus = new NativeFunction(
    plugin.getExportByName('CODOL_GetProfileReloadStatus'),
    'bool', ['uint', 'pointer', 'pointer', 'pointer']);
const requestInventory = new NativeFunction(
    plugin.getExportByName('CODOL_RequestInventoryRefresh'), 'uint', []);
const getInventoryStatus = new NativeFunction(
    plugin.getExportByName('CODOL_GetInventoryRefreshStatus'),
    'bool', ['pointer', 'pointer', 'pointer']);

function readStatus(reader) {
    const generation = Memory.alloc(4);
    const state = Memory.alloc(4);
    const error = Memory.alloc(4);
    if (!reader(generation, state, error)) throw new Error('runtime synchronization is unavailable');
    return {
        generation: generation.readU32(),
        state: state.readU32(),
        error: error.readU32()
    };
}

rpc.exports = {
    request(target) {
        if (target === 'inventory') return requestInventory();
        if (target === 'public') return requestProfile(1);
        if (target === 'private') return requestProfile(2);
        throw new Error('unknown synchronization target: ' + target);
    },
    status(target) {
        if (target === 'inventory') return readStatus(getInventoryStatus);
        const kind = target === 'public' ? 1 : target === 'private' ? 2 : 0;
        if (kind === 0) throw new Error('unknown synchronization target: ' + target);
        return readStatus((generation, state, error) =>
            getProfileStatus(kind, generation, state, error));
    }
};
"""


def _find_pid(device: Any) -> int | None:
    matches = [
        process.pid
        for process in device.enumerate_processes()
        if process.name.casefold() == TARGET_NAME.casefold()
    ]
    return max(matches) if matches else None


def synchronize(targets: list[str], timeout: float = 15.0) -> list[SyncResult]:
    if not targets:
        return []
    try:
        import frida
    except ImportError as error:
        raise RuntimeSyncError("Frida is required for live synchronization") from error

    device = frida.get_local_device()
    pid = _find_pid(device)
    if pid is None:
        raise RuntimeSyncError(f"{TARGET_NAME} is not running")

    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    try:
        script.load()
        results: list[SyncResult] = []
        for target in targets:
            generation = int(script.exports_sync.request(target))
            if generation == 0:
                raise RuntimeSyncError(f"{target} reload is unavailable")
            deadline = time.monotonic() + timeout
            while True:
                status = script.exports_sync.status(target)
                state = int(status["state"])
                current_generation = int(status["generation"])
                error_code = int(status["error"])
                if current_generation == generation and state == 4:
                    results.append(SyncResult(target, generation, "succeeded", error_code))
                    break
                if current_generation == generation and state == 5:
                    raise RuntimeSyncError(
                        f"{target} reload failed with DW error {error_code}"
                    )
                if time.monotonic() >= deadline:
                    state_name = STATE_NAMES.get(state, f"unknown_{state}")
                    raise RuntimeSyncError(
                        f"{target} reload timed out in state {state_name}"
                    )
                time.sleep(0.1)
        return results
    except frida.Error as error:
        raise RuntimeSyncError(str(error)) from error
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        session.detach()
