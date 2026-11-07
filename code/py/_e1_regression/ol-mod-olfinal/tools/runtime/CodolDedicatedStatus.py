#!/usr/bin/env python3
"""Read dedicated gameplay state through the loopback control protocol."""

from __future__ import annotations

import argparse
import json
import socket
import struct
import time
from typing import Any


FRAME_MAGIC = 0x43444C4F
STATUS_MAGIC = 0x5352444F
PROTOCOL_VERSION = 2
QUERY_GAMEPLAY_STATUS = 6
ACCEPTED = 0
MAXIMUM_PAYLOAD = 16 * 1024
NONE_CLIENT = 0xFFFFFFFF
CLIENT_THINK_FAILURE_STAGES = (
    "none", "not_playing", "spawned_this_frame",
    "non_increasing_command_time", "invalid_input_state",
    "native_pmove_unavailable", "native_pmove_rejected",
    "invalid_pmove_output", "native_playerstate_projection",
    "native_command_time_mismatch", "weapon_movement_rejected",
    "invalid_weapon_movement_output", "entitystate_conversion",
    "post_conversion_projection", "entitystate_decode",
    "predictable_event_decode", "converted_state_mismatch",
    "client_events_unsupported", "client_events_rejected",
    "final_projection", "final_state_mismatch", "invalid_client_impacts",
    "native_pmove_invalid_binding", "native_pmove_invalid_command",
    "native_pmove_wrong_thread", "native_pmove_reentrant_call",
    "native_pmove_handler_slot_busy",
    "native_pmove_anim_condition_install_failed",
    "native_pmove_non_increasing_command_time",
    "native_pmove_slice_limit_exceeded",
    "native_pmove_command_time_not_advanced",
    "native_pmove_native_exception", "native_pmove_handler_restore_failed",
    "native_pmove_trace_failed", "native_pmove_anim_condition_restore_failed",
    "native_pmove_invalid_output",
)


def checksum(payload: bytes) -> int:
    value = 2166136261
    for byte in payload:
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def receive_exact(stream: socket.socket, size: int) -> bytes:
    output = bytearray()
    while len(output) < size:
        chunk = stream.recv(size - len(output))
        if not chunk:
            raise RuntimeError("dedicated control closed the response early")
        output.extend(chunk)
    return bytes(output)


def submit(host: str, port: int, timeout: float) -> bytes:
    request_id = time.monotonic_ns() & 0xFFFFFFFFFFFFFFFF
    header = struct.pack(
        "<IHHIQI",
        FRAME_MAGIC,
        PROTOCOL_VERSION,
        QUERY_GAMEPLAY_STATUS,
        0,
        request_id,
        checksum(b""),
    )
    with socket.create_connection((host, port), timeout=timeout) as stream:
        stream.settimeout(timeout)
        stream.sendall(header)
        response = receive_exact(stream, 24)
        magic, version, status, size, response_id, expected_checksum = (
            struct.unpack("<IHHIQI", response)
        )
        if magic != FRAME_MAGIC or version != PROTOCOL_VERSION:
            raise RuntimeError("dedicated control returned an incompatible frame")
        if response_id != request_id or size > MAXIMUM_PAYLOAD:
            raise RuntimeError("dedicated control returned an invalid response header")
        payload = receive_exact(stream, size)
        if checksum(payload) != expected_checksum:
            raise RuntimeError("dedicated control response checksum mismatch")
        if status != ACCEPTED:
            raise RuntimeError(f"dedicated rejected gameplay status query: {status}")
        return payload


def optional_client(value: int) -> int | None:
    return None if value == NONE_CLIENT else value


def decode(payload: bytes) -> dict[str, Any]:
    if len(payload) < 84:
        raise RuntimeError("gameplay status payload is truncated")
    magic, schema, client_count, server_time = struct.unpack_from("<IHHI", payload)
    if magic != STATUS_MAGIC or schema not in (1, 2, 3, 4, 5):
        raise RuntimeError("gameplay status schema is incompatible")
    sd_values = struct.unpack_from("<18I", payload, 12)
    sd_keys = (
        "round_configured", "round_armed", "round_completed", "rounds_played",
        "round_winner", "round_end_reason", "bomb_configured", "bomb_phase",
        "attackers", "defenders", "attackers_alive", "defenders_alive",
        "carrier_client_num", "planter_client_num", "defuser_client_num",
        "planted_site_label", "phase_start_server_time", "planted_server_time",
    )
    sd = dict(zip(sd_keys, sd_values, strict=True))
    for key in ("carrier_client_num", "planter_client_num", "defuser_client_num"):
        sd[key] = optional_client(sd[key])
    if sd["planted_site_label"]:
        sd["planted_site_label"] = chr(sd["planted_site_label"])
    else:
        sd["planted_site_label"] = None

    offset = 84
    clients = []
    for _ in range(client_count):
        if offset + 48 > len(payload):
            raise RuntimeError("gameplay client status is truncated")
        client_num, gameplay_state, team, sequence, acknowledge = struct.unpack_from(
            "<5I", payload, offset
        )
        offset += 20
        transport = None
        if schema >= 2:
            if offset + 68 > len(payload):
                raise RuntimeError("gameplay client transport status is truncated")
            peer_ipv4, peer_port, reserved = struct.unpack_from("<IHH", payload, offset)
            if reserved != 0:
                raise RuntimeError("gameplay client transport status is invalid")
            (
                last_packet_received_time,
                incoming_sequence,
                outgoing_sequence,
                message_acknowledge,
            ) = struct.unpack_from("<4I", payload, offset + 8)
            (
                udp_send_attempts,
                udp_send_succeeded,
                udp_send_failed,
                udp_bytes_sent,
            ) = struct.unpack_from("<4Q", payload, offset + 24)
            last_udp_send_time, last_udp_send_bytes, last_udp_send_error = (
                struct.unpack_from("<IIi", payload, offset + 56)
            )
            offset += 68
            peer_host = socket.inet_ntoa(struct.pack("!I", peer_ipv4))
            transport = {
                "peer": f"{peer_host}:{peer_port}",
                "peer_ipv4": peer_ipv4,
                "peer_port": peer_port,
                "last_packet_received_time": last_packet_received_time,
                "incoming_sequence": incoming_sequence,
                "outgoing_sequence": outgoing_sequence,
                "message_acknowledge": message_acknowledge,
                "udp_send_attempts": udp_send_attempts,
                "udp_send_succeeded": udp_send_succeeded,
                "udp_send_failed": udp_send_failed,
                "udp_bytes_sent": udp_bytes_sent,
                "last_udp_send_time": last_udp_send_time,
                "last_udp_send_bytes": last_udp_send_bytes,
                "last_udp_send_error": last_udp_send_error,
            }
        usercmd = None
        client_think = None
        snapshot_projection = None
        if schema >= 3:
            if offset + 40 > len(payload):
                raise RuntimeError("gameplay diagnostics status is truncated")
            values = struct.unpack_from("<10I", payload, offset)
            offset += 40
            usercmd = {
                "pending_count": values[0],
                "oldest_pending_time": optional_client(values[1]),
                "newest_pending_time": optional_client(values[2]),
                "last_received_time": optional_client(values[3]),
                "last_dispatched_time": optional_client(values[4]),
                "last_executed_time": optional_client(values[5]),
                "last_discarded_time": optional_client(values[6]),
                "discarded_unsupported_count": values[7],
            }
            snapshot_projection = {
                "player_entity_mask": values[8],
                "client_info_mask": values[9],
            }
        if schema >= 4:
            if offset + 56 > len(payload):
                raise RuntimeError("client think diagnostics are truncated")
            values = struct.unpack_from("<12I2i", payload, offset)
            offset += 56
            usercmd["last_discarded_rejected_time"] = optional_client(values[0])
            usercmd["discarded_rejected_count"] = values[1]
            client_think = {
                "last_attempted_command_time": optional_client(values[2]),
                "last_committed_command_time": optional_client(values[3]),
                "failure_stage_code": values[4],
                "failure_stage": (
                    CLIENT_THINK_FAILURE_STAGES[values[4]]
                    if values[4] < len(CLIENT_THINK_FAILURE_STAGES)
                    else "unknown"
                ),
                "failure_count": values[5],
                "command": {
                    "buttons": values[6],
                    "angles": list(values[7:10]),
                    "weapon": values[10],
                    "offhand": values[11],
                    "forward_move": values[12],
                    "right_move": values[13],
                },
            }
        locational = None
        if schema >= 5:
            # The locational hit readout. Frida can never sample this - see
            # DedicatedControl.hpp - so it rides the control socket instead.
            if offset + 84 > len(payload):
                raise RuntimeError("locational hit diagnostics are truncated")
            origin = list(struct.unpack_from("<3f", payload, offset))
            view_angles = list(struct.unpack_from("<3f", payload, offset + 12))
            health, bullet_command_time = struct.unpack_from(
                "<2I", payload, offset + 24)
            bullet_start = list(struct.unpack_from("<3f", payload, offset + 32))
            bullet_end = list(struct.unpack_from("<3f", payload, offset + 44))
            bullet_fraction, = struct.unpack_from("<f", payload, offset + 56)
            (
                hit_type, hit_entity_num, model_index,
                part_name, part_group, result,
            ) = struct.unpack_from("<6I", payload, offset + 60)
            offset += 84
            # The world point the SERVER resolved the hit to. Everything the
            # vertical question needs is this minus the target's own origin.
            hit_point = [
                bullet_start[axis] +
                (bullet_end[axis] - bullet_start[axis]) * bullet_fraction
                for axis in range(3)
            ] if bullet_command_time != 0xFFFFFFFF else None
            locational = {
                "origin": origin,
                "view_angles": view_angles,
                "health": health,
                "bullet": None if bullet_command_time == 0xFFFFFFFF else {
                    "command_time": bullet_command_time,
                    "start": bullet_start,
                    "end": bullet_end,
                    "fraction": bullet_fraction,
                    "hit_type": hit_type,
                    "hit_entity_num":
                        None if hit_entity_num == 2047 else hit_entity_num,
                    "model_index": model_index,
                    "part_name": part_name,
                    "part_group": part_group,
                    "result": result,
                    "hit_point": hit_point,
                },
            }
        objectives = []
        for _ in range(3):
            state, icon = struct.unpack_from("<2I", payload, offset)
            offset += 8
            objectives.append({"state": state, "icon": icon})
        command_count, = struct.unpack_from("<I", payload, offset)
        offset += 4
        if command_count > 128:
            raise RuntimeError("gameplay reliable command count is invalid")
        commands = []
        for _ in range(command_count):
            if offset + 6 > len(payload):
                raise RuntimeError("gameplay reliable command header is truncated")
            command_sequence, command_size = struct.unpack_from("<IH", payload, offset)
            offset += 6
            if command_size > 1023 or offset + command_size > len(payload):
                raise RuntimeError("gameplay reliable command body is invalid")
            command = payload[offset:offset + command_size].decode("utf-8")
            offset += command_size
            commands.append({"sequence": command_sequence, "command": command})
        client = {
            "client_num": client_num,
            "gameplay_state": gameplay_state,
            "team": team,
            "server_reliable_sequence": sequence,
            "server_reliable_acknowledge": acknowledge,
            "objectives": objectives,
            "recent_server_reliable_commands": commands,
        }
        if transport is not None:
            client["transport"] = transport
        if usercmd is not None:
            client["usercmd"] = usercmd
            client["snapshot_projection"] = snapshot_projection
        if client_think is not None:
            client["client_think"] = client_think
        if locational is not None:
            client.update(locational)
        clients.append(client)
    if offset != len(payload):
        raise RuntimeError("gameplay status payload has trailing bytes")
    status = {"server_time": server_time, "sd": sd, "clients": clients}
    annotate_hit_heights(status)
    return status


def annotate_hit_heights(status: dict[str, Any]) -> None:
    """Resolve each committed hit to a height above the TARGET's own feet.

    That single number is what separates a collapsed hit skeleton from a
    mis-aimed trace, and it cannot be read any other way without attaching
    Frida to the dedicated - which kills it.
    """
    origins = {
        client["client_num"]: client["origin"]
        for client in status["clients"]
        if "origin" in client
    }
    for client in status["clients"]:
        bullet = client.get("bullet")
        if not bullet or bullet["hit_point"] is None:
            continue
        target = bullet["hit_entity_num"]
        if target is None or target not in origins:
            continue
        bullet["hit_height_above_target_feet"] = (
            bullet["hit_point"][2] - origins[target][2]
        )
        bullet["hit_offset_from_target"] = [
            bullet["hit_point"][axis] - origins[target][axis]
            for axis in range(3)
        ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=28961)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--output")
    parser.add_argument("--watch-seconds", type=float, default=0.0)
    parser.add_argument("--interval", type=float, default=0.25)
    arguments = parser.parse_args()
    if arguments.watch_seconds < 0 or arguments.interval <= 0:
        parser.error("--watch-seconds must be non-negative and --interval positive")
    if arguments.watch_seconds:
        deadline = time.monotonic() + arguments.watch_seconds
        stream = (
            open(arguments.output, "w", encoding="utf-8")
            if arguments.output else None
        )
        try:
            while True:
                status = decode(submit(
                    arguments.host, arguments.port, arguments.timeout
                ))
                row = json.dumps(status, ensure_ascii=False, separators=(",", ":"))
                if stream:
                    stream.write(row + "\n")
                    stream.flush()
                else:
                    print(row, flush=True)
                if time.monotonic() >= deadline:
                    break
                time.sleep(arguments.interval)
        finally:
            if stream:
                stream.close()
    else:
        status = decode(submit(arguments.host, arguments.port, arguments.timeout))
        text = json.dumps(status, ensure_ascii=False, indent=2)
        print(text)
        if arguments.output:
            with open(arguments.output, "w", encoding="utf-8") as stream:
                stream.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
