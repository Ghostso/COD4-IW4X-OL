#!/usr/bin/env python3
"""Summarize the existing AFD JSONL captures without guessing gameplay semantics."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = [
    ROOT / "工具" / "EX035_DIR" / "Logs" / "game2.jsonl",
    ROOT / "工具" / "EX035_DIR" / "Logs" / "game3.jsonl",
    ROOT / "工具" / "EX035_DIR" / "Logs" / "t4.jsonl",
]


def load(path: Path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "api" in value:
                rows.append(value)
    return rows


def endpoint(row):
    address = row.get("addr") or {}
    ip = address.get("ip")
    port = address.get("port")
    if ip is None or port is None:
        return None
    return f"{ip}:{port}"


def classify(ep: str | None) -> str:
    if not ep:
        return "unresolved"
    ip, _, port = ep.rpartition(":")
    if ip.startswith("127.") or ip == "::1":
        return "localhost/CEF-or-test"
    if port == "8081":
        return "QOS/telemetry candidate; not gameplay-confirmed"
    if port in {"80", "443"}:
        return "HTTP(S)/bootstrap candidate; not gameplay-confirmed"
    return "unknown external endpoint"


def render(paths: list[Path]) -> str:
    out: list[str] = [
        "# CODOL Capture Reproduction Report",
        "",
        "This report summarizes existing AFD ETW JSONL captures. The captures contain metadata only; payload is null and no gameplay endpoint is confirmed.",
        "",
        "## Capture Matrix",
        "",
        "| File | Events | PIDs | Payload availability |",
        "| --- | ---: | --- | --- |",
    ]
    all_rows = []
    for path in paths:
        if not path.exists():
            continue
        rows = load(path)
        all_rows.extend(rows)
        pids = sorted({str(row.get("pid")) for row in rows if row.get("pid") is not None})
        payloads = sum(1 for row in rows if row.get("payload") not in (None, ""))
        out.append(f"| `{path}` | {len(rows)} | {', '.join(pids) or 'none'} | {payloads} non-null records |")

    endpoints = collections.Counter()
    api_counts = collections.Counter()
    lengths = collections.Counter()
    for row in all_rows:
        api_counts[row.get("api", "unknown")] += 1
        ep = endpoint(row)
        if ep:
            endpoints[ep] += 1
        if row.get("len") is not None:
            lengths[(row.get("api"), row["len"])] += 1

    out.extend(["", "## Observed Endpoints", "", "| Endpoint | Records | Classification |", "| --- | ---: | --- |"])
    for ep, count in endpoints.most_common():
        out.append(f"| `{ep}` | {count} | {classify(ep)} |")

    out.extend(["", "## API Counts", "", "| API | Count |", "| --- | ---: |"])
    for api, count in api_counts.most_common():
        out.append(f"| `{api}` | {count} |")

    out.extend(["", "## Length Fingerprints", "", "| API | Length | Count |", "| --- | ---: | ---: |"])
    for (api, length), count in lengths.most_common():
        out.append(f"| `{api}` | {length} | {count} |")

    out.extend([
        "",
        "## Verdict",
        "",
        "- UDP `:8081` traffic is a QOS/telemetry candidate, supported by the `tqos.gamesafe.qq.com` DNS evidence and one-way `sendto` pattern. It is not a recovered game-server protocol.",
        "- TCP `:80`/`:443` traffic is HTTP(S)/bootstrap traffic in the captured startup window. It is not a recovered gameplay protocol.",
        "- The captures contain no payload bytes and no call stacks, so no opcode, framing, authentication exchange, game-server address, or response rule can be implemented from them honestly.",
        "- Static RTTI names such as `MatchMaking_FIND_SERVERS_Query` and `dwRoomMessage*` prove compiled protocol-shaped types exist, but not that they were instantiated or sent in these runs.",
    ])
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULTS)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    text = render(args.paths)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
