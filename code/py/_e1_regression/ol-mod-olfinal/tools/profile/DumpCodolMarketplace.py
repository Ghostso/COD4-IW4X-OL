"""Dump CODOL's loaded marketplace containers from a running client.

The tool is read-only. It uses the fixed layouts recovered from the QA build's
IDA database and records both representative entries and entries matching known
32-bit identifiers. Raw output belongs under diagnostics and is not committed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


PROCESS_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_NEEDLES = (197, 649, 1127, 1554, 23556, 25286, 10036)


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Attach to an explicit CODOL process")
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Include the first N records from each container in addition to matches",
    )
    parser.add_argument(
        "--needle",
        type=int,
        action="append",
        dest="needles",
        help="32-bit value to locate in every loaded record; may be repeated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repository / "diagnostics" / "marketplace" / f"runtime_catalog_{stamp}.json",
    )
    return parser.parse_args()


def select_process(device: frida.core.Device, requested_pid: int | None) -> frida.core.Process:
    if requested_pid is not None:
        for process in device.enumerate_processes():
            if process.pid == requested_pid:
                return process
        raise RuntimeError(f"process {requested_pid} is not running")

    matches = [
        process
        for process in device.enumerate_processes()
        if process.name.casefold() == PROCESS_NAME.casefold()
    ]
    if not matches:
        raise RuntimeError(f"{PROCESS_NAME} is not running")
    return max(matches, key=lambda process: process.pid)


def main() -> int:
    args = parse_args()
    if args.limit < 0:
        print("--limit must be non-negative", file=sys.stderr)
        return 2

    device = frida.get_local_device()
    try:
        process = select_process(device, args.pid)
        session = device.attach(process.pid)
        source = Path(__file__).with_name("codol_marketplace_dump.js").read_text(encoding="utf-8")
        script = session.create_script(source)
        script.load()
        needles = args.needles if args.needles is not None else list(DEFAULT_NEEDLES)
        snapshot = script.exports_sync.snapshot({"limit": args.limit, "needles": needles})
    except (frida.Error, RuntimeError) as error:
        print(f"Marketplace dump failed: {error}", file=sys.stderr)
        return 1
    finally:
        if "script" in locals():
            try:
                script.unload()
            except frida.InvalidOperationError:
                pass
        if "session" in locals():
            try:
                session.detach()
            except frida.InvalidOperationError:
                pass

    snapshot["captured_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot["needles"] = needles
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"Marketplace runtime dump: {output}")
    print(f"Process: {process.name} ({process.pid})")
    print(f"State: {snapshot['marketplace_state']}")
    for name, layout in snapshot["layouts"].items():
        print(
            f"  {name}: count={layout['count']} stride={layout['stride']} "
            f"selected={len(layout['records'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
