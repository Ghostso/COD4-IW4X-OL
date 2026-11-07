#!/usr/bin/env python3
"""Enable, disable, or inspect the in-process CODOL server core."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
PLUGIN_NAME = "CodolGameServer.Localnet32"
FRIDA_ATTACH_ERRORS = (
    frida.InvalidOperationError,
    frida.OperationCancelledError,
    frida.PermissionDeniedError,
    frida.ProcessNotFoundError,
    frida.ProcessNotRespondingError,
    frida.ProtocolError,
    frida.ServerNotRunningError,
    frida.TimedOutError,
    frida.TransportError,
)
CLIENT_INGRESS_ARGUMENT_TYPES = ["uint32", *("pointer",) * 14, "uint32"]
CLIENT_USERCMD_ARGUMENT_TYPES = ["uint32", *("pointer",) * 10]
CLIENT_REJECT_ARGUMENT_TYPES = [
    "uint32", *("pointer",) * 6, "uint32", "pointer", "uint32", "pointer"
]
CLIENT_RELIABLE_COMMAND_ARGUMENT_TYPES = [
    "uint32", "pointer", "pointer", "uint32", "pointer"
]
CLIENT_MENU_RESPONSE_ARGUMENT_TYPES = [
    "uint32", "pointer", "pointer", "pointer",
    "pointer", "uint32", "pointer", "pointer", "uint32", "pointer"
]
CLIENT_GAMEPLAY_ARGUMENT_TYPES = [
    "uint32", "pointer", "pointer", "pointer", "uint32", "pointer"
]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--enable", action="store_true")
    actions.add_argument("--disable", action="store_true")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument("--watch-log", type=Path)
    parser.add_argument("--watch-interval", type=float, default=2.0)
    parser.add_argument("--watch-seconds", type=float, default=0.0)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--map-name")
    parser.add_argument("--game-type")
    parser.add_argument("--config-string-checksum", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--checksum-feed", type=lambda value: int(value, 0), default=0)
    parser.add_argument(
        "--damage-entity-num",
        type=lambda value: int(value, 0),
        action="append",
        default=[],
    )
    args = parser.parse_args()

    if bool(args.map_name) != bool(args.game_type):
        parser.error("--map-name and --game-type must be supplied together")
    if args.sample_seconds < 0:
        parser.error("--sample-seconds must be non-negative")
    if args.watch_interval <= 0:
        parser.error("--watch-interval must be positive")
    if args.watch_seconds < 0:
        parser.error("--watch-seconds must be non-negative")
    if args.stop_file is not None and args.watch_log is None:
        parser.error("--stop-file requires --watch-log")
    for name, value in (
        ("--config-string-checksum", args.config_string_checksum),
        ("--checksum-feed", args.checksum_feed),
    ):
        if not 0 <= value <= 0xFFFFFFFF:
            parser.error(f"{name} must fit in uint32")
    if any(not 0 <= value < 2048 for value in args.damage_entity_num):
        parser.error("every --damage-entity-num must be in [0, 2048)")

    action = "enable" if args.enable else "disable" if args.disable else "status"
    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    done = threading.Event()
    result: dict[str, Any] = {}
    try:
        session = device.attach(pid)
    except FRIDA_ATTACH_ERRORS as error:
        print(json.dumps({
            "ok": False,
            "pid": pid,
            "action": action,
            "error": f"failed to attach to target: {error}",
        }, ensure_ascii=False, indent=2))
        return 2
    source = f"""
'use strict';
try {{
    const plugin = Process.findModuleByName({json.dumps(PLUGIN_NAME)});
    if (plugin === null) throw new Error({json.dumps(PLUGIN_NAME)} + ' is not loaded');
    // The launch wrapper may copy the retail executable to `out.exe`. Frida's
    // first module is always the process image, so use it instead of requiring
    // the original filename for these fixed executable offsets.
    const clientModule = Process.enumerateModules()[0];
    const clientConnectionState = clientModule.base.add(0x162E7EC);
    function nativeBacktrace(context) {{
        return Thread.backtrace(context, Backtracer.ACCURATE)
            .slice(0, 20)
            .map(function(address) {{
                return {{
                    address: address.toString(),
                    symbol: DebugSymbol.fromAddress(address).toString()
                }};
            }});
    }}
    const exceptionCounts = {{}};
    Process.setExceptionHandler(function(details) {{
        const signature = details.type + ':' + details.address.toString();
        const count = (exceptionCounts[signature] || 0) + 1;
        exceptionCounts[signature] = count;
        const context = {{}};
        for (const name of [
            'eip', 'esp', 'ebp', 'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi'
        ]) {{
            if (details.context[name] !== undefined)
                context[name] = details.context[name].toString();
        }}
        if (count <= 3) {{
            send({{
                ok: true,
                event: 'process_exception',
                exception: {{
                    type: details.type,
                    address: details.address.toString(),
                    count: count,
                    memory: details.memory === undefined ? null : {{
                        operation: details.memory.operation,
                        address: details.memory.address.toString()
                    }},
                    context: context,
                    backtrace: nativeBacktrace(details.context)
                }}
            }});
        }}
        return false;
    }});
    for (const exportName of [
        'ExitProcess', 'TerminateProcess', 'RaiseFailFastException',
        'RtlExitUserProcess'
    ]) {{
        const address = Module.findGlobalExportByName(exportName);
        if (address === null) continue;
        Interceptor.attach(address, {{
            onEnter(args) {{
                send({{
                    ok: true,
                    event: 'process_termination_call',
                    function: exportName,
                    argument0: args[0].toString(),
                    argument1: args[1].toString(),
                    backtrace: nativeBacktrace(this.context)
                }});
            }}
        }});
    }}
    const setEnabled = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerSetEnabled'),
        'bool',
        ['bool']
    );
    const getStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetStatus'),
        'bool',
        ['pointer', 'pointer', 'pointer']
    );
    const getNetworkStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetNetworkStatus'),
        'bool',
        ['pointer']
    );
    const getNetchanStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetNetchanStatus'),
        'bool',
        ['pointer', 'pointer', 'pointer']
    );
    let getConnectionlessDiagnostics = null;
    try {{
        getConnectionlessDiagnostics = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetConnectionlessDiagnosticsV1'),
            'bool',
            Array(9).fill('pointer').concat(['uint32', 'pointer'])
        );
    }} catch (_) {{}}
    let getClientIngressStatus = null;
    try {{
        getClientIngressStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientIngressStatus'),
            'bool',
            {json.dumps(CLIENT_INGRESS_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    let getClientGameStateStage = null;
    try {{
        getClientGameStateStage = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientGameStateStage'),
            'bool', ['uint32', 'pointer']
        );
    }} catch (_) {{}}
    let getClientLoadingStatus = null;
    try {{
        getClientLoadingStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientLoadingStatus'),
            'bool', ['uint32', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getClientUserCmdStatus = null;
    try {{
        getClientUserCmdStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientUserCmdStatus'),
            'bool',
            {json.dumps(CLIENT_USERCMD_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    let getClientRejectStatus = null;
    try {{
        getClientRejectStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientRejectStatus'),
            'bool',
            {json.dumps(CLIENT_REJECT_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    let getClientReliableCommandStatus = null;
    try {{
        getClientReliableCommandStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientReliableCommandStatus'),
            'bool',
            {json.dumps(CLIENT_RELIABLE_COMMAND_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    let getClientMenuResponseStatus = null;
    try {{
        getClientMenuResponseStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientMenuResponseStatus'),
            'bool',
            {json.dumps(CLIENT_MENU_RESPONSE_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    let getClientGameplayStatus = null;
    try {{
        getClientGameplayStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetClientGameplayStatus'),
            'bool',
            {json.dumps(CLIENT_GAMEPLAY_ARGUMENT_TYPES)}
        );
    }} catch (_) {{}}
    const getSessionStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetSessionStatus'),
        'bool',
        ['pointer']
    );
    let getDedicatedSessionConsumptionStatus = null;
    try {{
        getDedicatedSessionConsumptionStatus = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetDedicatedSessionConsumptionStatus'),
            'bool',
            [
                'pointer', 'pointer', 'pointer', 'pointer', 'pointer',
                'pointer', 'pointer', 'pointer', 'pointer'
            ]
        );
    }} catch (_) {{}}
    let getLoadoutPreparationStatus = null;
    try {{
        getLoadoutPreparationStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetLoadoutPreparationStatus'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getGameStateConfigurationStatus = null;
    try {{
        getGameStateConfigurationStatus = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetGameStateConfigurationStatus'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getLoadoutResolveFailure = null;
    try {{
        getLoadoutResolveFailure = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetLoadoutResolveFailure'),
            'bool',
            ['pointer']
        );
    }} catch (_) {{}}
    let getRegisteredCharacterStatus = null;
    try {{
        getRegisteredCharacterStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetRegisteredCharacterStatus'),
            'bool',
            ['pointer']
        );
    }} catch (_) {{}}
    let getRegisteredCharacterPresentation = null;
    try {{
        getRegisteredCharacterPresentation = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetRegisteredCharacterPresentation'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'uint32']
        );
    }} catch (_) {{}}
    const loadoutResolveFailureNames = [
        'none',
        'staged_slot',
        'native_resolver_unavailable',
        'item_name',
        'base_weapon_lookup',
        'base_weapon_resolver',
        'default_attachments',
        'equipped_attachment_name',
        'equipped_attachment_slot',
        'attachment_merge',
        'attachment_lookup',
        'attachment_capacity',
        'modular_weapon_resolver',
        'weapon_definition',
        'modular_weapon_dependency',
        'attachment_model_resolution'
    ];
    const configureGameState = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerConfigureGameState'),
        'bool',
        ['pointer', 'pointer', 'uint32', 'uint32']
    );
    const getGameStateStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetGameStateStatus'),
        'bool',
        ['pointer', 'pointer']
    );
    let getLoadingStatus = null;
    try {{
        getLoadingStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetLoadingStatus'),
            'bool',
            ['pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getGameStateReadinessStatus = null;
    try {{
        getGameStateReadinessStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetGameStateReadinessStatus'),
            'bool',
            ['pointer']
        );
    }} catch (_) {{}}
    let getSnapshotStatus = null;
    try {{
        getSnapshotStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetSnapshotStatus'),
            'bool',
            ['pointer']
        );
    }} catch (_) {{}}
    let getSnapshotDeltaStatus = null;
    try {{
        getSnapshotDeltaStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetSnapshotDeltaStatus'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldStatus = null;
    try {{
        getWorldStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldStatus'),
            'bool',
            ['pointer']
        );
    }} catch (_) {{}}
    let getSdStatusV1 = null;
    try {{
        getSdStatusV1 = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetSdStatusV1'),
            'bool',
            Array(18).fill('pointer')
        );
    }} catch (_) {{}}
    let getWorldObjectiveStatusV1 = null;
    try {{
        getWorldObjectiveStatusV1 = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldObjectiveStatusV1'),
            'bool',
            ['uint32', ...Array(7).fill('pointer')]
        );
    }} catch (_) {{}}
    let getEntityDamageStatusV1 = null;
    try {{
        getEntityDamageStatusV1 = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetEntityDamageStatusV1'),
            'bool',
            ['uint32', ...Array(7).fill('pointer')]
        );
    }} catch (_) {{}}
    let getWorldClientThinkStatus = null;
    try {{
        getWorldClientThinkStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldClientThinkStatus'),
            'bool',
            ['uint32', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldPredictableEventStatusV1 = null;
    try {{
        getWorldPredictableEventStatusV1 = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetWorldPredictableEventStatusV1'),
            'bool',
            [
                'uint32', 'pointer', 'pointer', 'pointer', 'pointer',
                'pointer', 'pointer', 'pointer'
            ]
        );
    }} catch (_) {{}}
    let getWorldBulletExecutionStatusV1 = null;
    try {{
        getWorldBulletExecutionStatusV1 = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetWorldBulletExecutionStatusV1'),
            'bool',
            ['uint32', ...Array(11).fill('pointer')]
        );
    }} catch (_) {{}}
    let getWorldBulletExecutionStatusV2 = null;
    try {{
        getWorldBulletExecutionStatusV2 = new NativeFunction(
            plugin.getExportByName(
                'CODOL_GameServerGetWorldBulletExecutionStatusV2'),
            'bool',
            ['uint32', ...Array(13).fill('pointer')]
        );
    }} catch (_) {{}}
    let getWorldEventStatus = null;
    try {{
        getWorldEventStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldEventStatus'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldEventWeaponStatus = null;
    try {{
        getWorldEventWeaponStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldEventWeaponStatus'),
            'bool',
            ['pointer', 'pointer', 'pointer', 'uint32', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldPlayerStatus = null;
    try {{
        getWorldPlayerStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerStatus'),
            'bool',
            [
                'uint32', 'pointer', 'pointer', 'pointer',
                'pointer', 'pointer', 'pointer', 'pointer'
            ]
        );
    }} catch (_) {{}}
    let getWorldPlayerSampleV2 = null;
    try {{
        getWorldPlayerSampleV2 = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerSampleV2'),
            'bool',
            ['uint32', 'pointer', 'uint32']
        );
    }} catch (_) {{}}
    let getWorldPlayerPmoveStatus = null;
    try {{
        getWorldPlayerPmoveStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerPmoveStatus'),
            'bool',
            ['uint32', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldPlayerViewHeightStatus = null;
    try {{
        getWorldPlayerViewHeightStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerViewHeightStatus'),
            'bool',
            ['uint32', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    let getWorldPlayerHealthStatus = null;
    try {{
        getWorldPlayerHealthStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerHealthStatus'),
            'bool',
            [
                'uint32', 'pointer', 'pointer', 'pointer',
                'pointer', 'pointer', 'pointer'
            ]
        );
    }} catch (_) {{}}
    let getWorldPlayerWeaponStatus = null;
    try {{
        getWorldPlayerWeaponStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldPlayerWeaponStatus'),
            'bool',
            [
                'uint32', 'pointer', 'pointer', 'pointer', 'pointer', 'pointer',
                'pointer', 'pointer', 'pointer', 'pointer', 'pointer'
            ]
        );
    }} catch (_) {{}}
    let getWorldResolvedLoadoutStatus = null;
    try {{
        getWorldResolvedLoadoutStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetWorldResolvedLoadoutStatus'),
            'bool',
            ['uint32', 'pointer', 'pointer']
        );
    }} catch (_) {{}}
    const getConstantConfigStringStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetConstantConfigStringStatus'),
        'bool',
        ['pointer', 'pointer']
    );
    const getTransportStatus = new NativeFunction(
        plugin.getExportByName('CODOL_GameServerGetTransportStatus'),
        'bool',
        ['pointer', 'pointer', 'pointer', 'pointer', 'pointer']
    );
    let getTransportTimingStatus = null;
    try {{
        getTransportTimingStatus = new NativeFunction(
            plugin.getExportByName('CODOL_GameServerGetTransportTimingStatus'),
            'bool',
            ['pointer', 'pointer']
        );
    }} catch (_) {{}}

    function hexBytes(pointer, size) {{
        if (size <= 0) return '';
        const bytes = pointer.readByteArray(size);
        if (bytes === null) return '';
        return Array.from(
            new Uint8Array(bytes),
            value => value.toString(16).padStart(2, '0')
        ).join('');
    }}

    function clientIngress() {{
        if (getClientIngressStatus === null) return [];
        const clients = [];
        for (let clientNum = 0; clientNum < 18; ++clientNum) {{
            const state = Memory.alloc(4);
            const lastPacketTime = Memory.alloc(4);
            const incomingSequence = Memory.alloc(4);
            const outgoingSequence = Memory.alloc(4);
            const messageAcknowledge = Memory.alloc(4);
            const reliableAcknowledge = Memory.alloc(4);
            const lastClientReliableSequence = Memory.alloc(4);
            const deltaMessage = Memory.alloc(4);
            const lastMoveCommandCount = Memory.alloc(4);
            const acceptedPackets = Memory.alloc(4);
            const duplicatePackets = Memory.alloc(4);
            const rejectedPackets = Memory.alloc(4);
            const decodedCommandsSize = Memory.alloc(4);
            const decodedCommandsPrefix = Memory.alloc(64);
            if (!getClientIngressStatus(
                    clientNum,
                    state,
                    lastPacketTime,
                    incomingSequence,
                    outgoingSequence,
                    messageAcknowledge,
                    reliableAcknowledge,
                    lastClientReliableSequence,
                    deltaMessage,
                    lastMoveCommandCount,
                    acceptedPackets,
                    duplicatePackets,
                    rejectedPackets,
                    decodedCommandsSize,
                    decodedCommandsPrefix,
                    64)) {{
                continue;
            }}
            const decodedSize = decodedCommandsSize.readU32();
            let lastReliableCommand = null;
            let lastReject = null;
            if (getClientRejectStatus !== null) {{
                const rejectSequence = Memory.alloc(4);
                const rejectServerId = Memory.alloc(4);
                const rejectMessageAcknowledge = Memory.alloc(4);
                const rejectReliableAcknowledge = Memory.alloc(4);
                const rejectDecodedCommandsSize = Memory.alloc(4);
                const rejectDecodedCommandsPrefix = Memory.alloc(64);
                const rejectReason = Memory.alloc(1025);
                const rejectReasonLength = Memory.alloc(4);
                if (getClientRejectStatus(
                        clientNum,
                        rejectSequence,
                        rejectServerId,
                        rejectMessageAcknowledge,
                        rejectReliableAcknowledge,
                        rejectDecodedCommandsSize,
                        rejectDecodedCommandsPrefix,
                        64,
                        rejectReason,
                        1025,
                        rejectReasonLength)) {{
                    const decodedSize = rejectDecodedCommandsSize.readU32();
                    const reasonLength = rejectReasonLength.readU32();
                    lastReject = {{
                        sequence: rejectSequence.readU32(),
                        server_id: rejectServerId.readU32(),
                        message_acknowledge: rejectMessageAcknowledge.readU32(),
                        reliable_acknowledge: rejectReliableAcknowledge.readU32(),
                        decoded_commands_size: decodedSize,
                        decoded_commands_prefix_hex: hexBytes(
                            rejectDecodedCommandsPrefix, Math.min(decodedSize, 64)),
                        reason: rejectReason.readUtf8String(Math.min(reasonLength, 1024)),
                        reason_length: reasonLength
                    }};
                }}
            }}
            if (getClientReliableCommandStatus !== null) {{
                const reliableSequence = Memory.alloc(4);
                const reliableCommand = Memory.alloc(1025);
                const reliableCommandLength = Memory.alloc(4);
                if (getClientReliableCommandStatus(
                        clientNum,
                        reliableSequence,
                        reliableCommand,
                        1025,
                        reliableCommandLength)) {{
                    const commandLength = reliableCommandLength.readU32();
                    lastReliableCommand = {{
                        sequence: reliableSequence.readU32(),
                        command: reliableCommand.readUtf8String(Math.min(commandLength, 1024)),
                        command_length: commandLength
                    }};
                }}
            }}
            let lastMenuResponse = null;
            if (getClientMenuResponseStatus !== null) {{
                const menuSequence = Memory.alloc(4);
                const menuServerId = Memory.alloc(4);
                const menuIndex = Memory.alloc(4);
                const menuName = Memory.alloc(1025);
                const menuNameLength = Memory.alloc(4);
                const menuResponse = Memory.alloc(1025);
                const menuResponseLength = Memory.alloc(4);
                if (getClientMenuResponseStatus(
                        clientNum,
                        menuSequence,
                        menuServerId,
                        menuIndex,
                        menuName,
                        1025,
                        menuNameLength,
                        menuResponse,
                        1025,
                        menuResponseLength)) {{
                    const nameLength = menuNameLength.readU32();
                    const responseLength = menuResponseLength.readU32();
                    lastMenuResponse = {{
                        sequence: menuSequence.readU32(),
                        server_id: menuServerId.readU32(),
                        menu_index: menuIndex.readU32(),
                        menu_name: menuName.readUtf8String(Math.min(nameLength, 1024)),
                        menu_name_length: nameLength,
                        response: menuResponse.readUtf8String(Math.min(responseLength, 1024)),
                        response_length: responseLength
                    }};
                }}
            }}
            let lastUserCmd = null;
            if (getClientUserCmdStatus !== null) {{
                const commandTime = Memory.alloc(4);
                const buttons = Memory.alloc(4);
                const angle0 = Memory.alloc(4);
                const angle1 = Memory.alloc(4);
                const angle2 = Memory.alloc(4);
                const weapon = Memory.alloc(4);
                const offHandIndex = Memory.alloc(4);
                const lastWeaponAltModeSwitch = Memory.alloc(4);
                const forwardMove = Memory.alloc(4);
                const rightMove = Memory.alloc(4);
                if (getClientUserCmdStatus(
                        clientNum,
                        commandTime,
                        buttons,
                        angle0,
                        angle1,
                        angle2,
                        weapon,
                        offHandIndex,
                        lastWeaponAltModeSwitch,
                        forwardMove,
                        rightMove)) {{
                    const rawAngles = [
                        angle0.readU32(), angle1.readU32(), angle2.readU32()
                    ];
                    lastUserCmd = {{
                        command_time: commandTime.readU32(),
                        buttons: buttons.readU32(),
                        angles: rawAngles,
                        view_angles: rawAngles.map(value => value * 360.0 / 65536.0),
                        weapon: weapon.readU32(),
                        off_hand_index: offHandIndex.readU32(),
                        last_weapon_alt_mode_switch: lastWeaponAltModeSwitch.readU32(),
                        forward_move: forwardMove.readS32(),
                        right_move: rightMove.readS32()
                    }};
                }}
            }}
            let gameplay = null;
            if (getClientGameplayStatus !== null) {{
                const gameplayState = Memory.alloc(4);
                const loadoutSequence = Memory.alloc(4);
                const selectedLoadout = Memory.alloc(1025);
                const selectedLoadoutLength = Memory.alloc(4);
                if (getClientGameplayStatus(
                        clientNum,
                        gameplayState,
                        loadoutSequence,
                        selectedLoadout,
                        1025,
                        selectedLoadoutLength)) {{
                    const value = gameplayState.readU32();
                    const loadoutLength = selectedLoadoutLength.readU32();
                    gameplay = {{
                        value: value,
                        name: ['inactive', 'waiting_for_loadout', 'playing'][value] || 'unknown',
                        loadout_sequence: loadoutSequence.readU32(),
                        selected_loadout: selectedLoadout.readUtf8String(
                            Math.min(loadoutLength, 1024)),
                        selected_loadout_length: loadoutLength
                    }};
                }}
            }}
            let gameStateStage = null;
            if (getClientGameStateStage !== null) {{
                const stage = Memory.alloc(4);
                if (getClientGameStateStage(clientNum, stage))
                    gameStateStage = stage.readU32();
            }}
            let loading = null;
            if (getClientLoadingStatus !== null) {{
                const received = Memory.alloc(4);
                const required = Memory.alloc(4);
                const complete = Memory.alloc(4);
                const stage = Memory.alloc(4);
                const message = Memory.alloc(4);
                const generation = Memory.alloc(8);
                const generationActive = Memory.alloc(4);
                if (getClientLoadingStatus(
                    clientNum, received, required, complete, stage, message,
                    generation, generationActive)) {{
                    loading = {{
                        profile_received_mask: received.readU32(),
                        profile_required_mask: required.readU32(),
                        profile_complete: complete.readU32() !== 0,
                        gamestate_stage: stage.readU32(),
                        gamestate_message: message.readU32(),
                        session_generation: generation.readU64().toString(),
                        generation_active: generationActive.readU32() !== 0
                    }};
                }}
            }}
            clients.push({{
                client_num: clientNum,
                state: state.readU32(),
                gamestate_stage: gameStateStage,
                loading: loading,
                last_packet_time: lastPacketTime.readU32(),
                incoming_sequence: incomingSequence.readU32(),
                outgoing_sequence: outgoingSequence.readU32(),
                message_acknowledge: messageAcknowledge.readU32(),
                reliable_acknowledge: reliableAcknowledge.readU32(),
                last_client_reliable_sequence: lastClientReliableSequence.readU32(),
                delta_message: deltaMessage.readS32(),
                last_move_command_count: lastMoveCommandCount.readU32(),
                accepted_packets: acceptedPackets.readU32(),
                duplicate_packets: duplicatePackets.readU32(),
                rejected_packets: rejectedPackets.readU32(),
                last_reject: lastReject,
                decoded_commands_size: decodedSize,
                decoded_commands_prefix_hex: hexBytes(
                    decodedCommandsPrefix, Math.min(decodedSize, 64)),
                last_reliable_command: lastReliableCommand,
                last_menu_response: lastMenuResponse,
                last_usercmd: lastUserCmd,
                gameplay: gameplay
            }});
        }}
        return clients;
    }}

    function worldPlayers() {{
        if (getWorldPlayerStatus === null) return [];
        const players = [];
        for (let clientNum = 0; clientNum < 18; ++clientNum) {{
            const commandTime = Memory.alloc(4);
            const origin = Memory.alloc(12);
            const velocity = Memory.alloc(12);
            const groundEntityNum = Memory.alloc(4);
            const gravity = Memory.alloc(4);
            const speed = Memory.alloc(4);
            const moveSpeedScaleMultiplier = Memory.alloc(4);
            if (!getWorldPlayerStatus(
                    clientNum,
                    commandTime,
                    origin,
                    velocity,
                    groundEntityNum,
                    gravity,
                    speed,
                    moveSpeedScaleMultiplier))
                continue;
            let viewAngles = null;
            if (getWorldPlayerSampleV2 !== null) {{
                const sample = Memory.alloc(352);
                if (getWorldPlayerSampleV2(clientNum, sample, 352)) {{
                    viewAngles = Array.from(
                        {{ length: 3 }},
                        (_, index) => sample.add(196 + index * 4).readFloat());
                }}
            }}
            let pmove = null;
            if (getWorldPlayerPmoveStatus !== null) {{
                const pmTime = Memory.alloc(4);
                const pmFlags = Memory.alloc(4);
                const jumpTime = Memory.alloc(4);
                const jumpOriginZ = Memory.alloc(4);
                if (getWorldPlayerPmoveStatus(
                        clientNum, pmTime, pmFlags, jumpTime, jumpOriginZ)) {{
                    pmove = {{
                        pm_time: pmTime.readU32(),
                        pm_flags: pmFlags.readU32(),
                        jump_time: jumpTime.readU32(),
                        jump_origin_z: jumpOriginZ.readFloat()
                    }};
                }}
            }}
            let clientThink = null;
            if (getWorldClientThinkStatus !== null) {{
                const lastAttemptedCommandTime = Memory.alloc(4);
                const lastCommittedCommandTime = Memory.alloc(4);
                const failureStage = Memory.alloc(4);
                const failureCount = Memory.alloc(4);
                if (getWorldClientThinkStatus(
                        clientNum,
                        lastAttemptedCommandTime,
                        lastCommittedCommandTime,
                        failureStage,
                        failureCount)) {{
                    const failureStageNames = [
                        'none',
                        'not_playing',
                        'spawned_this_frame',
                        'non_increasing_command_time',
                        'invalid_input_state',
                        'native_pmove_unavailable',
                        'native_pmove_rejected',
                        'invalid_pmove_output',
                        'native_playerstate_projection',
                        'native_command_time_mismatch',
                        'weapon_movement_rejected',
                        'invalid_weapon_movement_output',
                        'entitystate_conversion',
                        'post_conversion_projection',
                        'entitystate_decode',
                        'predictable_event_decode',
                        'converted_state_mismatch',
                        'client_events_rejected',
                        'final_projection',
                        'final_state_mismatch',
                        'native_pmove_invalid_binding',
                        'native_pmove_invalid_command',
                        'native_pmove_wrong_thread',
                        'native_pmove_reentrant_call',
                        'native_pmove_handler_slot_busy',
                        'native_pmove_anim_condition_install_failed',
                        'native_pmove_non_increasing_command_time',
                        'native_pmove_slice_limit_exceeded',
                        'native_pmove_command_time_not_advanced',
                        'native_pmove_native_exception',
                        'native_pmove_handler_restore_failed',
                        'native_pmove_trace_failed',
                        'native_pmove_anim_condition_restore_failed',
                        'native_pmove_invalid_output'
                    ];
                    const stage = failureStage.readU32();
                    clientThink = {{
                        last_attempted_command_time:
                            lastAttemptedCommandTime.readU32(),
                        last_committed_command_time:
                            lastCommittedCommandTime.readU32(),
                        failure_stage_code: stage,
                        failure_stage: stage < failureStageNames.length
                            ? failureStageNames[stage]
                            : 'unknown',
                        failure_count: failureCount.readU32()
                    }};
                }}
            }}
            let health = null;
            let predictableEvents = null;
            if (getWorldPredictableEventStatusV1 !== null) {{
                const commandTime = Memory.alloc(4);
                const oldSequence = Memory.alloc(4);
                const currentSequence = Memory.alloc(4);
                const count = Memory.alloc(4);
                const events = Memory.alloc(16);
                const eventParameters = Memory.alloc(16);
                const handlerResult = Memory.alloc(4);
                if (getWorldPredictableEventStatusV1(
                        clientNum,
                        commandTime,
                        oldSequence,
                        currentSequence,
                        count,
                        events,
                        eventParameters,
                        handlerResult)) {{
                    const eventCount = Math.min(count.readU32(), 4);
                    predictableEvents = {{
                        command_time: commandTime.readU32(),
                        old_sequence: oldSequence.readS32(),
                        current_sequence: currentSequence.readS32(),
                        count: eventCount,
                        events: Array.from({{ length: eventCount }}, (_, index) => ({{
                            event: events.add(index * 4).readS32(),
                            parameter: eventParameters.add(index * 4).readS32()
                        }})),
                        handler_result: handlerResult.readU32()
                    }};
                }}
            }}
            let bulletExecution = null;
            if (getWorldBulletExecutionStatusV2 !== null) {{
                const commandTime = Memory.alloc(4);
                const start = Memory.alloc(12);
                const end = Memory.alloc(12);
                const fraction = Memory.alloc(4);
                const values = Array.from({{ length: 9 }}, () => Memory.alloc(4));
                if (getWorldBulletExecutionStatusV2(
                        clientNum,
                        commandTime,
                        start,
                        end,
                        fraction,
                        ...values)) {{
                    const optionalEntity = values[1].readU32();
                    bulletExecution = {{
                        command_time: commandTime.readU32(),
                        start: Array.from(
                            {{ length: 3 }}, (_, index) =>
                                start.add(index * 4).readFloat()),
                        end: Array.from(
                            {{ length: 3 }}, (_, index) =>
                                end.add(index * 4).readFloat()),
                        fraction: fraction.readFloat(),
                        hit_type: values[0].readU32(),
                        hit_entity_num: optionalEntity === 2047
                            ? null
                            : optionalEntity,
                        model_index: values[2].readU32(),
                        part_name: values[3].readU32(),
                        part_group: values[4].readU32(),
                        surface_flags: values[5].readU32(),
                        player_damage_staged: values[6].readU32() !== 0,
                        entity_damage_staged: values[7].readU32() !== 0,
                        result: values[8].readU32()
                    }};
                }}
            }} else if (getWorldBulletExecutionStatusV1 !== null) {{
                const commandTime = Memory.alloc(4);
                const start = Memory.alloc(12);
                const end = Memory.alloc(12);
                const fraction = Memory.alloc(4);
                const values = Array.from({{ length: 7 }}, () => Memory.alloc(4));
                if (getWorldBulletExecutionStatusV1(
                        clientNum,
                        commandTime,
                        start,
                        end,
                        fraction,
                        ...values)) {{
                    const optionalEntity = values[1].readU32();
                    bulletExecution = {{
                        command_time: commandTime.readU32(),
                        start: Array.from(
                            {{ length: 3 }}, (_, index) =>
                                start.add(index * 4).readFloat()),
                        end: Array.from(
                            {{ length: 3 }}, (_, index) =>
                                end.add(index * 4).readFloat()),
                        fraction: fraction.readFloat(),
                        hit_type: values[0].readU32(),
                        hit_entity_num: optionalEntity === 2047
                            ? null
                            : optionalEntity,
                        part_group: values[2].readU32(),
                        surface_flags: values[3].readU32(),
                        player_damage_staged: values[4].readU32() !== 0,
                        entity_damage_staged: values[5].readU32() !== 0,
                        result: values[6].readU32()
                    }};
                }}
            }}
            if (getWorldPlayerHealthStatus !== null) {{
                const currentHealth = Memory.alloc(4);
                const maxHealth = Memory.alloc(4);
                const damageEvent = Memory.alloc(4);
                const damageYaw = Memory.alloc(4);
                const damagePitch = Memory.alloc(4);
                const damageCount = Memory.alloc(4);
                if (getWorldPlayerHealthStatus(
                        clientNum,
                        currentHealth,
                        maxHealth,
                        damageEvent,
                        damageYaw,
                        damagePitch,
                        damageCount)) {{
                    health = {{
                        current: currentHealth.readU32(),
                        maximum: maxHealth.readU32(),
                        damage_event: damageEvent.readU32(),
                        damage_yaw: damageYaw.readU32(),
                        damage_pitch: damagePitch.readU32(),
                        damage_count: damageCount.readU32()
                    }};
                }}
            }}
            let viewHeight = null;
            if (getWorldPlayerViewHeightStatus !== null) {{
                const current = Memory.alloc(4);
                const target = Memory.alloc(4);
                const lerpTarget = Memory.alloc(4);
                const lerpTime = Memory.alloc(4);
                const lerpDown = Memory.alloc(4);
                if (getWorldPlayerViewHeightStatus(
                        clientNum,
                        current,
                        target,
                        lerpTarget,
                        lerpTime,
                        lerpDown)) {{
                    viewHeight = {{
                        current: current.readFloat(),
                        target: target.readS32(),
                        lerp_target: lerpTarget.readS32(),
                        lerp_time: lerpTime.readS32(),
                        lerp_down: lerpDown.readU32() !== 0
                    }};
                }}
            }}
            let resolvedLoadout = null;
            if (getWorldResolvedLoadoutStatus !== null) {{
                const primaryWeaponAssetIndex = Memory.alloc(4);
                const secondaryWeaponAssetIndex = Memory.alloc(4);
                if (getWorldResolvedLoadoutStatus(
                        clientNum,
                        primaryWeaponAssetIndex,
                        secondaryWeaponAssetIndex)) {{
                    resolvedLoadout = {{
                        primary_weapon_asset_index: primaryWeaponAssetIndex.readU32(),
                        secondary_weapon_asset_index: secondaryWeaponAssetIndex.readU32()
                    }};
                }}
            }}
            let weapon = null;
            if (getWorldPlayerWeaponStatus !== null) {{
                const currentWeaponAssetIndex = Memory.alloc(4);
                const weaponTime = Memory.alloc(4);
                const weaponDelay = Memory.alloc(4);
                const weaponState = Memory.alloc(4);
                const weaponAnim = Memory.alloc(4);
                const clipAmmo = Memory.alloc(4);
                const weaponType = Memory.alloc(4);
                const fireType = Memory.alloc(4);
                const definitionFireDelay = Memory.alloc(4);
                const definitionFireTime = Memory.alloc(4);
                if (getWorldPlayerWeaponStatus(
                        clientNum,
                        currentWeaponAssetIndex,
                        weaponTime,
                        weaponDelay,
                        weaponState,
                        weaponAnim,
                        clipAmmo,
                        weaponType,
                        fireType,
                        definitionFireDelay,
                        definitionFireTime)) {{
                    weapon = {{
                        current_weapon_asset_index: currentWeaponAssetIndex.readU32(),
                        weapon_time: weaponTime.readS32(),
                        weapon_delay: weaponDelay.readS32(),
                        weapon_state: weaponState.readU32(),
                        weapon_anim: weaponAnim.readU32(),
                        clip_ammo: clipAmmo.readU32(),
                        weapon_type: weaponType.readU32(),
                        fire_type: fireType.readU32(),
                        definition_fire_delay: definitionFireDelay.readU32(),
                        definition_fire_time: definitionFireTime.readU32()
                    }};
                }}
            }}
            players.push({{
                client_num: clientNum,
                command_time: commandTime.readU32(),
                view_angles: viewAngles,
                origin: [
                    origin.readFloat(),
                    origin.add(4).readFloat(),
                    origin.add(8).readFloat()
                ],
                velocity: [
                    velocity.readFloat(),
                    velocity.add(4).readFloat(),
                    velocity.add(8).readFloat()
                ],
                ground_entity_num: groundEntityNum.readU32(),
                gravity: gravity.readU32(),
                speed: speed.readU32(),
                move_speed_scale_multiplier: moveSpeedScaleMultiplier.readFloat(),
                view_height: viewHeight,
                health: health,
                resolved_loadout: resolvedLoadout,
                weapon: weapon,
                pmove: pmove,
                client_think: clientThink,
                predictable_events: predictableEvents,
                bullet_execution: bulletExecution
            }});
        }}
        return players;
    }}

    function status() {{
        const enabled = Memory.alloc(4);
        const frameNumber = Memory.alloc(4);
        const serverTime = Memory.alloc(4);
        if (!getStatus(enabled, frameNumber, serverTime)) {{
            return {{
                installed: false,
                client_connection_state: clientConnectionState.readU32(),
                binding_prefixes: {{
                    com_frame: hexBytes(clientModule.base.add(0x19E000), 9),
                    db_find_xasset_header: hexBytes(clientModule.base.add(0x09E7D0), 9),
                    msg_init: hexBytes(clientModule.base.add(0x1A1140), 9),
                    msg_write_bits: hexBytes(clientModule.base.add(0x1A11E0), 9),
                    msg_write_string: hexBytes(clientModule.base.add(0x1A12B0), 9),
                    ccs_initialize: hexBytes(clientModule.base.add(0x1850B0), 9)
                }}
            }};
        }}
        const connectedClients = Memory.alloc(4);
        const netchanPacketsReceived = Memory.alloc(4);
        const netchanPacketsDropped = Memory.alloc(4);
        const reliableCommandsReceived = Memory.alloc(4);
        const sessionConfigured = Memory.alloc(4);
        const queuedSessionRequestId = Memory.alloc(8);
        const processedSessionRequestId = Memory.alloc(8);
        const sessionConsumeStage = Memory.alloc(4);
        const sessionFailedClassIndex = Memory.alloc(4);
        const sessionRequestedClassMask = Memory.alloc(4);
        const sessionResolvedClassMask = Memory.alloc(4);
        const sessionCharacterFailure = Memory.alloc(4);
        const sessionCharacterRecordIndex = Memory.alloc(4);
        const sessionCharacterItemId = Memory.alloc(4);
        const loadoutAttemptCount = Memory.alloc(4);
        const loadoutCurrentCharacter = Memory.alloc(4);
        const loadoutResolvedClassMask = Memory.alloc(4);
        const loadoutRegisteredClassMask = Memory.alloc(4);
        const loadoutPrepared = Memory.alloc(4);
        const loadoutPreparedCharacter = Memory.alloc(4);
        const loadoutRegisteredCharacter = Memory.alloc(4);
        const loadoutResolveFailure = Memory.alloc(4);
        const gameStateConfigureAttemptCount = Memory.alloc(4);
        const gameStateConfigureStage = Memory.alloc(4);
        const gameStateConfigureFailedClassIndex = Memory.alloc(4);
        const gameStateConfigureRegisteredClassMask = Memory.alloc(4);
        const gameStateConfigureFirstDynamicWeapon = Memory.alloc(4);
        const gameStateConfigured = Memory.alloc(4);
        const gameStateMessagesSent = Memory.alloc(4);
        const activeClients = Memory.alloc(4);
        const gameStateUpdatesReceived = Memory.alloc(4);
        const clientsReadyForGameState = Memory.alloc(4);
        const snapshotMessagesSent = Memory.alloc(4);
        const fullSnapshotMessagesSent = Memory.alloc(4);
        const deltaSnapshotMessagesSent = Memory.alloc(4);
        const messageAcknowledge = Memory.alloc(4);
        const outgoingSequence = Memory.alloc(4);
        const worldSpawnConfigured = Memory.alloc(4);
        const constantConfigStringsInitialized = Memory.alloc(4);
        const constantConfigStringChecksum = Memory.alloc(4);
        const transportBound = Memory.alloc(4);
        const transportPort = Memory.alloc(4);
        const packetsReceived = Memory.alloc(4);
        const packetsSent = Memory.alloc(4);
        const lastSocketError = Memory.alloc(4);
        const lastPacketReceivedTime = Memory.alloc(4);
        const lastPacketSentTime = Memory.alloc(4);
        if (!getNetworkStatus(connectedClients))
            throw new Error('CODOL_GameServerGetNetworkStatus failed');
        if (!getNetchanStatus(
                netchanPacketsReceived,
                netchanPacketsDropped,
                reliableCommandsReceived))
            throw new Error('CODOL_GameServerGetNetchanStatus failed');
        let connectionless = null;
        if (getConnectionlessDiagnostics !== null) {{
            const values = Array.from({{length: 8}}, () => Memory.alloc(4));
            const reason = Memory.alloc(1025);
            const reasonLength = Memory.alloc(4);
            if (!getConnectionlessDiagnostics(
                    ...values, reason, 1025, reasonLength))
                throw new Error('CODOL_GameServerGetConnectionlessDiagnosticsV1 failed');
            const length = reasonLength.readU32();
            connectionless = {{
                handled: values[0].readU32(),
                connected: values[1].readU32(),
                rejected: values[2].readU32(),
                last_connected_ipv4: values[3].readU32(),
                last_connected_port: values[4].readU32(),
                last_connected_client_slot: values[5].readU32(),
                last_rejected_ipv4: values[6].readU32(),
                last_rejected_port: values[7].readU32(),
                last_rejected_reason: reason.readUtf8String(Math.min(length, 1024)),
                last_rejected_reason_length: length
            }};
        }}
        if (!getSessionStatus(sessionConfigured))
            throw new Error('CODOL_GameServerGetSessionStatus failed');
        let sessionConsumption = null;
        if (getDedicatedSessionConsumptionStatus !== null) {{
            if (!getDedicatedSessionConsumptionStatus(
                    queuedSessionRequestId,
                    processedSessionRequestId,
                    sessionConsumeStage,
                    sessionFailedClassIndex,
                    sessionRequestedClassMask,
                    sessionResolvedClassMask,
                    sessionCharacterFailure,
                    sessionCharacterRecordIndex,
                    sessionCharacterItemId))
            {{
                throw new Error(
                    'CODOL_GameServerGetDedicatedSessionConsumptionStatus failed');
            }}
            const stage = sessionConsumeStage.readU32();
            const characterFailure = sessionCharacterFailure.readU32();
            sessionConsumption = {{
                queued_request_id: queuedSessionRequestId.readU64().toNumber(),
                processed_request_id: processedSessionRequestId.readU64().toNumber(),
                stage_code: stage,
                stage: [
                    'none',
                    'queued',
                    'processing',
                    'map_asset_load',
                    'waiting_for_map_assets',
                    'configstring_generation_reset',
                    'waiting_for_client_readiness',
                    'waiting_for_configstring_generation',
                    'constant_configstrings_initialization',
                    'weapon_registry_unavailable',
                    'weapon_registry_initialization',
                    'character_presentation',
                    'weapon_loadout',
                    'configure_booking',
                    'accepted',
                    'world_initialization'
                ][stage] || 'unknown',
                failed_class_index: sessionFailedClassIndex.readS32(),
                requested_class_mask: sessionRequestedClassMask.readU32(),
                resolved_class_mask: sessionResolvedClassMask.readU32(),
                character_failure_code: characterFailure,
                character_failure: [
                    'none',
                    'invalid_request',
                    'item_name',
                    'selection',
                    'base_item_definition',
                    'character_definition_table',
                    'character_definition',
                    'viewmodel_configstring',
                    'constant_configstrings'
                ][characterFailure] || 'unknown',
                character_record_index:
                    sessionCharacterRecordIndex.readU32() === 0xffffffff
                        ? null
                        : sessionCharacterRecordIndex.readU32(),
                character_item_id: sessionCharacterItemId.readU32()
            }};
        }}
        let loadoutPreparation = null;
        if (getLoadoutPreparationStatus !== null) {{
            if (!getLoadoutPreparationStatus(
                    loadoutAttemptCount,
                    loadoutCurrentCharacter,
                    loadoutResolvedClassMask,
                    loadoutRegisteredClassMask,
                    loadoutPrepared,
                    loadoutPreparedCharacter))
            {{
                throw new Error('CODOL_GameServerGetLoadoutPreparationStatus failed');
            }}
            loadoutPreparation = {{
                attempt_count: loadoutAttemptCount.readU32(),
                current_character: loadoutCurrentCharacter.readS32(),
                resolved_class_mask: loadoutResolvedClassMask.readU32(),
                registered_class_mask: loadoutRegisteredClassMask.readU32(),
                prepared: loadoutPrepared.readU32() !== 0,
                prepared_character: loadoutPreparedCharacter.readS32(),
                failure_code: null,
                failure: null,
                registered_character: null
            }};
            if (getLoadoutResolveFailure !== null) {{
                loadoutResolveFailure.writeU32(0);
                if (!getLoadoutResolveFailure(loadoutResolveFailure))
                    throw new Error('CODOL_GameServerGetLoadoutResolveFailure failed');
                const failureCode = loadoutResolveFailure.readU32();
                loadoutPreparation.failure_code = failureCode;
                loadoutPreparation.failure = failureCode < loadoutResolveFailureNames.length
                    ? loadoutResolveFailureNames[failureCode]
                    : 'unknown';
            }}
            if (getRegisteredCharacterStatus !== null) {{
                loadoutRegisteredCharacter.writeS32(-1);
                if (!getRegisteredCharacterStatus(loadoutRegisteredCharacter)) {{
                    throw new Error(
                        'CODOL_GameServerGetRegisteredCharacterStatus failed');
                }}
                loadoutPreparation.registered_character =
                    loadoutRegisteredCharacter.readS32();
            }}
            if (getRegisteredCharacterPresentation !== null) {{
                const characterIndex = Memory.alloc(4);
                const female = Memory.alloc(4);
                const color = Memory.alloc(4);
                const viewmodelIndex = Memory.alloc(4);
                const selectionIds = Memory.alloc(11 * 2);
                if (getRegisteredCharacterPresentation(
                        characterIndex,
                        female,
                        color,
                        viewmodelIndex,
                        selectionIds,
                        11)) {{
                    loadoutPreparation.registered_character_presentation = {{
                        character_index: characterIndex.readU32(),
                        female: female.readU32() !== 0,
                        color: color.readU32(),
                        viewmodel_index: viewmodelIndex.readU32(),
                        selection_ids: Array.from(
                            {{ length: 11 }},
                            (_, index) => selectionIds.add(index * 2).readU16())
                    }};
                }} else {{
                    loadoutPreparation.registered_character_presentation = null;
                }}
            }}
        }}
        let gameStateConfiguration = null;
        if (getGameStateConfigurationStatus !== null) {{
            if (!getGameStateConfigurationStatus(
                    gameStateConfigureAttemptCount,
                    gameStateConfigureStage,
                    gameStateConfigureFailedClassIndex,
                    gameStateConfigureRegisteredClassMask,
                    gameStateConfigureFirstDynamicWeapon))
            {{
                throw new Error(
                    'CODOL_GameServerGetGameStateConfigurationStatus failed');
            }}
            const stage = gameStateConfigureStage.readU32();
            gameStateConfiguration = {{
                attempt_count: gameStateConfigureAttemptCount.readU32(),
                stage_code: stage,
                stage: [
                    'none',
                    'processing',
                    'invalid_checksum',
                    'map_center_unavailable',
                    'character_unavailable',
                    'prepared_loadout_mismatch',
                    'dynamic_weapon_range_unavailable',
                    'primary_dependency_registration',
                    'primary_weapon_registration',
                    'secondary_dependency_registration',
                    'secondary_weapon_registration',
                    'character_changed',
                    'server_commit',
                    'accepted',
                    'dynamic_weapon_registry_unavailable',
                    'dynamic_weapon_registry_registration',
                    'mini_map_unavailable',
                    'objective_material_unavailable'
                ][stage] || 'unknown',
                failed_class_index:
                    gameStateConfigureFailedClassIndex.readS32(),
                registered_class_mask:
                    gameStateConfigureRegisteredClassMask.readU32(),
                first_dynamic_weapon_asset_index:
                    gameStateConfigureFirstDynamicWeapon.readU32()
            }};
        }}
        if (!getGameStateStatus(gameStateConfigured, gameStateMessagesSent))
            throw new Error('CODOL_GameServerGetGameStateStatus failed');
        activeClients.writeU32(0);
        gameStateUpdatesReceived.writeU32(0);
        if (getLoadingStatus !== null &&
            !getLoadingStatus(activeClients, gameStateUpdatesReceived))
            throw new Error('CODOL_GameServerGetLoadingStatus failed');
        clientsReadyForGameState.writeU32(0);
        if (getGameStateReadinessStatus !== null &&
            !getGameStateReadinessStatus(clientsReadyForGameState))
            throw new Error('CODOL_GameServerGetGameStateReadinessStatus failed');
        snapshotMessagesSent.writeU32(0);
        if (getSnapshotStatus !== null && !getSnapshotStatus(snapshotMessagesSent))
            throw new Error('CODOL_GameServerGetSnapshotStatus failed');
        fullSnapshotMessagesSent.writeU32(0);
        deltaSnapshotMessagesSent.writeU32(0);
        messageAcknowledge.writeU32(0);
        outgoingSequence.writeU32(0);
        if (getSnapshotDeltaStatus !== null && !getSnapshotDeltaStatus(
                fullSnapshotMessagesSent,
                deltaSnapshotMessagesSent,
                messageAcknowledge,
                outgoingSequence))
            throw new Error('CODOL_GameServerGetSnapshotDeltaStatus failed');
        worldSpawnConfigured.writeU32(0);
        if (getWorldStatus !== null && !getWorldStatus(worldSpawnConfigured))
            throw new Error('CODOL_GameServerGetWorldStatus failed');
        let sdStatus = null;
        if (getSdStatusV1 !== null) {{
            const values = Array.from({{ length: 18 }}, () => Memory.alloc(4));
            if (!getSdStatusV1(...values))
                throw new Error('CODOL_GameServerGetSdStatusV1 failed');
            const optionalClient = (value) => value === 0xffffffff ? null : value;
            const siteCode = values[15].readU32();
            const winner = values[4].readU32();
            const endReason = values[5].readU32();
            const phase = values[7].readU32();
            sdStatus = {{
                round: {{
                    configured: values[0].readU32() !== 0,
                    armed: values[1].readU32() !== 0,
                    completed: values[2].readU32() !== 0,
                    rounds_played: values[3].readU32(),
                    winner_code: winner,
                    winner: ['none', 'tf', 'sc'][winner] || 'unknown',
                    end_reason_code: endReason,
                    end_reason: [
                        'none', 'attackers_eliminated', 'defenders_eliminated',
                        'simultaneous_elimination', 'bomb_defused', 'bomb_exploded',
                        'time_limit'
                    ][endReason] || 'unknown'
                }},
                bomb: {{
                    configured: values[6].readU32() !== 0,
                    phase_code: phase,
                    phase: [
                        'inactive', 'available', 'carried', 'dropped',
                        'planted', 'defused', 'exploded'
                    ][phase] || 'unknown',
                    carrier_client_num: optionalClient(values[12].readU32()),
                    planter_client_num: optionalClient(values[13].readU32()),
                    defuser_client_num: optionalClient(values[14].readU32()),
                    planted_site: siteCode ? String.fromCharCode(siteCode) : null,
                    phase_start_server_time: values[16].readU32(),
                    planted_server_time: values[17].readU32()
                }},
                teams: {{
                    attackers: values[8].readU32(),
                    defenders: values[9].readU32(),
                    attackers_alive: values[10].readU32(),
                    defenders_alive: values[11].readU32()
                }}
            }};
        }}
        const objectiveStatuses = [];
        if (getWorldObjectiveStatusV1 !== null) {{
            const objectiveClients = worldPlayers().map((player) => player.client_num);
            for (const objectiveClient of objectiveClients) {{
                const values = Array.from({{ length: 7 }}, () => Memory.alloc(4));
                if (getWorldObjectiveStatusV1(objectiveClient, ...values)) {{
                    objectiveStatuses.push({{
                        client_num: objectiveClient,
                        active_count: values[0].readU32(),
                        slots: [0, 1, 2].map((index) => ({{
                            state: values[1 + index * 2].readU32(),
                            icon: values[2 + index * 2].readU32()
                        }}))
                    }});
                }}
            }}
        }}
        const entityDamageStatuses = [];
        const damageEntityNums = {json.dumps(args.damage_entity_num)};
        if (getEntityDamageStatusV1 !== null) {{
            for (const damageEntityNum of damageEntityNums) {{
                const values = Array.from({{ length: 7 }}, () => Memory.alloc(4));
                if (getEntityDamageStatusV1(damageEntityNum, ...values)) {{
                    const kind = values[1].readU32();
                    entityDamageStatuses.push({{
                        entity_num: damageEntityNum,
                        generation: values[0].readU32(),
                        kind_code: kind,
                        kind: ['generic', 'destructible'][kind] || 'unknown',
                        health: values[2].readS32(),
                        can_take_damage: values[3].readU32() !== 0,
                        cannot_die: values[4].readU32() !== 0,
                        stage_index: values[5].readU32(),
                        model_index: values[6].readU32()
                    }});
                }}
            }}
        }}
        const entityDamageStatus = entityDamageStatuses.length > 0
            ? entityDamageStatuses[0]
            : null;
        let worldLastEvent = null;
        if (getWorldEventStatus !== null) {{
            const eventSequence = Memory.alloc(4);
            const eventType = Memory.alloc(4);
            const eventServerTime = Memory.alloc(4);
            const eventClientNum = Memory.alloc(4);
            const eventSpawnSequence = Memory.alloc(4);
            const eventSpawnGeneration = Memory.alloc(4);
            if (getWorldEventStatus(
                    eventSequence,
                    eventType,
                    eventServerTime,
                    eventClientNum,
                    eventSpawnSequence,
                    eventSpawnGeneration)) {{
                const type = eventType.readU32();
                worldLastEvent = {{
                    sequence: eventSequence.readU32(),
                    type: type,
                    name: {{
                        1: 'client_spawned',
                        2: 'client_disconnected',
                        3: 'weapon_switch_started'
                    }}[type] || 'unknown',
                    server_time: eventServerTime.readU32(),
                    client_num: eventClientNum.readU32(),
                    spawn_sequence: eventSpawnSequence.readU32(),
                    spawn_generation: eventSpawnGeneration.readU32()
                }};
                if (type === 3 && getWorldEventWeaponStatus !== null) {{
                    const weaponEventSequence = Memory.alloc(4);
                    const weaponAssetIndex = Memory.alloc(4);
                    const weaponName = Memory.alloc(1025);
                    const weaponNameLength = Memory.alloc(4);
                    if (getWorldEventWeaponStatus(
                            weaponEventSequence,
                            weaponAssetIndex,
                            weaponName,
                            1025,
                            weaponNameLength) &&
                        weaponEventSequence.readU32() === worldLastEvent.sequence) {{
                        const nameLength = weaponNameLength.readU32();
                        worldLastEvent.weapon_asset_index = weaponAssetIndex.readU32();
                        worldLastEvent.weapon_name = weaponName.readUtf8String(
                            Math.min(nameLength, 1024));
                    }}
                }}
            }}
        }}
        if (!getConstantConfigStringStatus(
                constantConfigStringsInitialized,
                constantConfigStringChecksum))
            throw new Error('CODOL_GameServerGetConstantConfigStringStatus failed');
        if (!getTransportStatus(
                transportBound,
                transportPort,
                packetsReceived,
                packetsSent,
                lastSocketError))
            throw new Error('CODOL_GameServerGetTransportStatus failed');
        lastPacketReceivedTime.writeU32(0);
        lastPacketSentTime.writeU32(0);
        if (getTransportTimingStatus !== null && !getTransportTimingStatus(
                lastPacketReceivedTime, lastPacketSentTime))
            throw new Error('CODOL_GameServerGetTransportTimingStatus failed');
        return {{
            installed: true,
            enabled: enabled.readU32() !== 0,
            client_connection_state: clientConnectionState.readU32(),
            frame_number: frameNumber.readU32(),
            server_time: serverTime.readU32(),
            connected_clients: connectedClients.readU32(),
            netchan_packets_received: netchanPacketsReceived.readU32(),
            netchan_packets_dropped: netchanPacketsDropped.readU32(),
            reliable_commands_received: reliableCommandsReceived.readU32(),
            connectionless: connectionless,
            session_configured: sessionConfigured.readU32() !== 0,
            session_consumption: sessionConsumption,
            loadout_preparation: loadoutPreparation,
            gamestate_configuration: gameStateConfiguration,
            gamestate_configured: gameStateConfigured.readU32() !== 0,
            gamestate_messages_sent: gameStateMessagesSent.readU32(),
            clients_ready_for_gamestate: clientsReadyForGameState.readU32(),
            active_clients: activeClients.readU32(),
            gamestate_updates_received: gameStateUpdatesReceived.readU32(),
            snapshot_messages_sent: snapshotMessagesSent.readU32(),
            full_snapshot_messages_sent: fullSnapshotMessagesSent.readU32(),
            delta_snapshot_messages_sent: deltaSnapshotMessagesSent.readU32(),
            message_acknowledge: messageAcknowledge.readU32(),
            outgoing_sequence: outgoingSequence.readU32(),
            client_ingress: clientIngress(),
            world_players: worldPlayers(),
            world_spawn_configured: worldSpawnConfigured.readU32() !== 0,
            sd: sdStatus,
            objectives: objectiveStatuses,
            entity_damage: entityDamageStatus,
            entity_damages: entityDamageStatuses,
            world_last_event: worldLastEvent,
            constant_configstrings_initialized:
                constantConfigStringsInitialized.readU32() !== 0,
            constant_configstring_checksum: constantConfigStringChecksum.readU32(),
            transport_bound: transportBound.readU32() !== 0,
            transport_port: transportPort.readU32(),
            packets_received: packetsReceived.readU32(),
            packets_sent: packetsSent.readU32(),
            last_packet_received_time: lastPacketReceivedTime.readU32(),
            last_packet_sent_time: lastPacketSentTime.readU32(),
            last_socket_error: lastSocketError.readU32()
        }};
    }}

    const action = {json.dumps(action)};
    const configureRequested = {json.dumps(bool(args.map_name))};
    if (configureRequested) {{
        const mapName = Memory.allocUtf8String({json.dumps(args.map_name or "")});
        const gameType = Memory.allocUtf8String({json.dumps(args.game_type or "")});
        if (!configureGameState(
                mapName,
                gameType,
                {args.config_string_checksum},
                {args.checksum_feed}))
            throw new Error('CODOL_GameServerConfigureGameState failed');
    }}
    if (action === 'enable' && !setEnabled(1))
        throw new Error('CODOL_GameServerSetEnabled(true) failed');
    if (action === 'disable' && !setEnabled(0))
        throw new Error('CODOL_GameServerSetEnabled(false) failed');
    const before = status();
    let sampleIndex = 0;
    function emitStatus() {{
        send({{
            ok: true,
            pid: Process.id,
            action: action,
            sample_index: sampleIndex++,
            before: before,
            after: status()
        }});
    }}
    if ({json.dumps(args.watch_log is not None)}) {{
        emitStatus();
        setInterval(emitStatus, {max(1, int(args.watch_interval * 1000))});
    }} else {{
        setTimeout(emitStatus, {max(0, int(args.sample_seconds * 1000))});
    }}
}} catch (error) {{
    send({{ ok: false, error: error.stack || error.message }});
}}
"""
    script = session.create_script(source)

    def on_message(message: dict[str, Any], _data: bytes | None) -> None:
        payload = message.get("payload", message)
        if isinstance(payload, dict):
            if payload.get("ok") is False:
                result.clear()
                result.update(payload)
            if "before" in payload and "after" in payload:
                result.clear()
                result.update(payload)
            if args.watch_log is not None:
                args.watch_log.parent.mkdir(parents=True, exist_ok=True)
                row = {
                    "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "phase": "watch",
                    "returncode": 0 if payload.get("ok") else 2,
                    "payload": payload,
                }
                with args.watch_log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=True) + "\n")
        if args.watch_log is None or (
            isinstance(payload, dict) and payload.get("ok") is False
        ):
            done.set()

    def on_detached(reason: str, crash: Any = None) -> None:
        if args.watch_log is not None:
            args.watch_log.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "phase": "watch",
                "event": "detached",
                "reason": reason,
                "crash": str(crash) if crash is not None else None,
            }
            with args.watch_log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=True) + "\n")
        elif not result:
            result.update({
                "ok": False,
                "pid": pid,
                "action": action,
                "error": f"target detached before status sample: {reason}",
                "crash": str(crash) if crash is not None else None,
            })
        done.set()

    script.on("message", on_message)
    session.on("detached", on_detached)
    try:
        script.load()
        if args.watch_log is None:
            if not done.wait(args.sample_seconds + 10.0):
                raise TimeoutError("timed out waiting for plugin status")
        else:
            deadline = None if args.watch_seconds <= 0 else time.monotonic() + args.watch_seconds
            while not done.wait(0.2):
                if args.stop_file is not None and args.stop_file.exists():
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    break
    except KeyboardInterrupt:
        pass
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
