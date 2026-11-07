#!/usr/bin/env python3
"""Shared, dependency-free CODOL native-input scenario definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


K_MOUSE1 = 0xC8
K_MOUSE2 = 0xC9
K_LEFTARROW = 0x86
K_RIGHTARROW = 0x87
ACTION_NAMES = {
    "attack": ("+attack", "-attack", K_MOUSE1),
    "ads": ("+speed_throw", "-speed_throw", K_MOUSE2),
    "sprint": ("+breath_sprint", "-breath_sprint", 16),
    "reload": ("+reload", "-reload", ord("R")),
    "forward": ("+forward", "-forward", ord("W")),
    "back": ("+back", "-back", ord("S")),
    "left": ("+moveleft", "-moveleft", ord("A")),
    "right": ("+moveright", "-moveright", ord("D")),
    "turnleft": ("+left", "-left", K_LEFTARROW),
    "turnright": ("+right", "-right", K_RIGHTARROW),
    "jump": ("+gostand", "-gostand", 32),
    "crouch": ("+movedown", "-movedown", ord("C")),
    "prone": ("+prone", "-prone", ord("Z")),
    "weapnext": ("weapnext", None, 0),
    "weapprev": ("weapprev", None, 0),
}

SCENARIO_VERSION = 1
MAX_SCENARIO_EVENTS = 128
MAX_SCENARIO_DURATION_MS = 60_000


def single_action_scenario(
    action: str,
    hold_seconds: float,
    observe_seconds: float,
) -> dict[str, Any]:
    up_name = ACTION_NAMES[action][1]
    events: list[dict[str, Any]] = [
        {
            "at_ms": 0,
            "action": action,
            "transition": "activate" if up_name is None else "down",
        }
    ]
    if up_name is not None:
        events.append(
            {
                # A paired action must survive at least one Com_Frame.  Keeping
                # zero-duration CLI probes valid is useful, but dispatching down
                # and up in the same frame produces no usercmd evidence.
                "at_ms": max(1, round(hold_seconds * 1000.0)),
                "action": action,
                "transition": "up",
            }
        )
    return normalize_scenario(
        {
            "version": SCENARIO_VERSION,
            "name": f"single-{action}",
            "events": events,
            "observe_after_ms": round(observe_seconds * 1000.0),
        }
    )


def load_scenario_document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        document = path.read_bytes()
    except OSError as error:
        raise ValueError(f"could not read scenario {path}: {error}") from error
    try:
        payload = json.loads(document.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError(f"scenario {path} is not valid UTF-8") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"scenario {path} is not valid JSON: line {error.lineno} column {error.colno}"
        ) from error
    return normalize_scenario(payload), document


def load_scenario(path: Path) -> dict[str, Any]:
    scenario, _document = load_scenario_document(path)
    return scenario


def normalize_scenario(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("scenario root must be an object")
    version = payload.get("version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != SCENARIO_VERSION
    ):
        raise ValueError(f"scenario version must be {SCENARIO_VERSION}")
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("scenario name must be a non-empty string")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("scenario events must be a non-empty array")
    if len(events) > MAX_SCENARIO_EVENTS:
        raise ValueError(f"scenario cannot exceed {MAX_SCENARIO_EVENTS} events")

    normalized_events: list[dict[str, Any]] = []
    active_actions: dict[str, int] = {}
    previous_at = -1
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"scenario event {index} must be an object")
        at_ms = event.get("at_ms")
        if not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0:
            raise ValueError(f"scenario event {index} at_ms must be a non-negative integer")
        if at_ms < previous_at:
            raise ValueError("scenario events must be ordered by at_ms")
        if at_ms > MAX_SCENARIO_DURATION_MS:
            raise ValueError(
                f"scenario event {index} exceeds {MAX_SCENARIO_DURATION_MS} ms"
            )
        previous_at = at_ms

        action = event.get("action")
        if action not in ACTION_NAMES:
            raise ValueError(f"scenario event {index} has unknown action {action!r}")
        transition = event.get("transition")
        paired = ACTION_NAMES[action][1] is not None
        allowed = {"down", "release", "up"} if paired else {"activate"}
        if transition not in allowed:
            raise ValueError(
                f"scenario event {index} transition must be one of {sorted(allowed)}"
            )
        if transition == "down":
            if action in active_actions:
                raise ValueError(f"scenario event {index} presses active action {action!r}")
            active_actions[action] = at_ms
        elif transition == "up":
            if action not in active_actions:
                raise ValueError(f"scenario event {index} releases inactive action {action!r}")
            if at_ms <= active_actions[action]:
                raise ValueError(
                    f"scenario event {index} must release action {action!r} "
                    "after its press"
                )
            del active_actions[action]
        elif transition == "release" and action in active_actions:
            raise ValueError(
                f"scenario event {index} must use 'up' for active action {action!r}"
            )
        normalized_events.append(
            {"at_ms": at_ms, "action": action, "transition": transition}
        )

    if active_actions:
        raise ValueError(
            "scenario must explicitly release actions: " + ", ".join(sorted(active_actions))
        )
    observe_after_ms = payload.get("observe_after_ms", 0)
    if (
        not isinstance(observe_after_ms, int)
        or isinstance(observe_after_ms, bool)
        or observe_after_ms < 0
    ):
        raise ValueError("scenario observe_after_ms must be a non-negative integer")
    duration_ms = previous_at + observe_after_ms
    if duration_ms > MAX_SCENARIO_DURATION_MS:
        raise ValueError(f"scenario duration cannot exceed {MAX_SCENARIO_DURATION_MS} ms")
    return {
        "version": SCENARIO_VERSION,
        "name": name.strip(),
        "events": normalized_events,
        "observe_after_ms": observe_after_ms,
        "duration_ms": duration_ms,
    }


def scenario_duration_seconds(scenario: Any) -> float:
    return float(normalize_scenario(scenario)["duration_ms"]) * 0.001
