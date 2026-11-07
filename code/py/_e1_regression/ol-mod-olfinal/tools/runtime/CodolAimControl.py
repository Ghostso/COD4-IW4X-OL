#!/usr/bin/env python3
"""Aim a live CODOL client with authoritative server-yaw feedback."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


RUNTIME_DIR = Path(__file__).resolve().parent


def angle_delta(target: float, current: float) -> float:
    return (target - current + 180.0) % 360.0 - 180.0


def run_json(arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"command returned invalid JSON ({completed.returncode}): "
            f"{completed.stderr.strip()}"
        ) from error
    if completed.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or completed.stderr.strip())
    return payload


def player_state(server_pid: int, client_num: int) -> dict[str, Any]:
    last_error: RuntimeError | None = None
    for _ in range(3):
        try:
            payload = run_json([
                str(RUNTIME_DIR / "CodolGameServerControl.py"),
                "--pid", str(server_pid),
                "--sample-seconds", "0",
            ])
            break
        except RuntimeError as error:
            last_error = error
            time.sleep(0.1)
    else:
        raise last_error or RuntimeError("server status unavailable")
    players = payload.get("after", {}).get("world_players", [])
    player = next(
        (entry for entry in players if entry.get("client_num") == client_num),
        None,
    )
    if player is None or player.get("view_angles") is None:
        raise RuntimeError(f"server has no authoritative player {client_num} view angles")
    return player


def turn(client_pid: int, action: str, seconds: float) -> None:
    run_json([
        str(RUNTIME_DIR / "CodolClientInput.py"),
        action,
        "--pid", str(client_pid),
        "--hold-seconds", f"{seconds:.4f}",
        "--observe-seconds", "0.12",
        "--timeout", "6",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-pid", type=int, required=True)
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--client-num", type=int, default=0)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--target-yaw", type=float)
    target.add_argument("--target-xy", type=float, nargs=2, metavar=("X", "Y"))
    parser.add_argument("--tolerance", type=float, default=1.0)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-hold-seconds", type=float, default=0.05)
    parser.add_argument("--degrees-per-second", type=float, default=176.0)
    args = parser.parse_args()
    if args.tolerance <= 0 or args.max_steps <= 0:
        parser.error("--tolerance and --max-steps must be positive")
    if args.max_hold_seconds <= 0 or args.degrees_per_second <= 0:
        parser.error("turn timing values must be positive")

    initial = player_state(args.server_pid, args.client_num)
    if args.target_xy is not None:
        origin = initial["origin"]
        target_yaw = math.degrees(math.atan2(
            args.target_xy[1] - origin[1],
            args.target_xy[0] - origin[0],
        ))
    else:
        target_yaw = args.target_yaw
    assert target_yaw is not None

    steps: list[dict[str, Any]] = []
    player = initial
    for _ in range(args.max_steps):
        current = float(player["view_angles"][1])
        error = angle_delta(target_yaw, current)
        if abs(error) <= args.tolerance:
            result = {
                "ok": True,
                "target_yaw": target_yaw,
                "final_yaw": current,
                "error": error,
                "origin": player["origin"],
                "steps": steps,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        action = "turnleft" if error > 0 else "turnright"
        hold = min(args.max_hold_seconds, abs(error) / args.degrees_per_second)
        turn(args.client_pid, action, hold)
        steps.append({
            "yaw": current,
            "error": error,
            "action": action,
            "hold_seconds": hold,
        })
        player = player_state(args.server_pid, args.client_num)

    final_yaw = float(player["view_angles"][1])
    result = {
        "ok": False,
        "error": "target yaw did not converge",
        "target_yaw": target_yaw,
        "final_yaw": final_yaw,
        "remaining_error": angle_delta(target_yaw, final_yaw),
        "steps": steps,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
