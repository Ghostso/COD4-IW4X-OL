#!/usr/bin/env python3
"""Build a CODOL DW3 service/task ledger from a runtime trace."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SERVICE_NAMES = {
    0x03: "Teams",
    0x06: "BandwidthTest",
    0x08: "Profiles2",
    0x09: "Friends2",
    0x0A: "Storage2",
    0x0C: "TitleUtilities2",
    0x1C: "ContentUnlock2",
    0x1D: "Unknown29",
    0x44: "RichPresence",
    0x47: "Tencent",
    0x50: "Marketplace",
    0x5D: "Unknown93",
    0x66: "Unknown102",
}

TASK_NAMES = {
    (0x06, 0x05): "bandwidthTest",
    (0x08, 0x01): "getPublicInfos",
    (0x08, 0x02): "getPrivateInfo",
    (0x0A, 0x0A): "uploadFile",
    (0x0A, 0x0C): "getFile",
    (0x0A, 0x14): "listAllPublisherFiles",
    (0x0A, 0x15): "getPublisherFile",
    (0x0C, 0x06): "getServerTime",
    (0x44, 0x01): "setInfo",
    (0x47, 0x03): "tLogBatchSend",
    (0x47, 0x04): "registerCodoID",
    (0x47, 0x05): "getAASRecord",
    (0x47, 0x07): "tLog",
    (0x47, 0x0A): "claimRewards",
    (0x47, 0x0F): "tLogBatchSendCompressed",
    (0x50, 0x82): "getBalance",
    (0x50, 0xCB): "getInventory",
}

PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, help="events.jsonl produced by CodolRuntimeTrace.py")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Defaults to an analysis directory beside events.jsonl",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=repository / "docs" / "codol_dw_request_matrix.md",
        help="Generated Markdown ledger path",
    )
    return parser.parse_args()


def event_bytes(event: dict[str, Any]) -> bytes | None:
    preview = event.get("preview_hex")
    if not isinstance(preview, str):
        return None
    try:
        return bytes.fromhex(preview)
    except ValueError:
        return None


def ascii_strings(data: bytes) -> list[str]:
    return [match.group().decode("ascii") for match in PRINTABLE.finditer(data)]


def iso_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_requests(path: Path) -> tuple[list[dict[str, Any]], int]:
    requests: list[dict[str, Any]] = []
    plaintext_response_count = 0
    serialized_response_count = 0
    first_time: dt.datetime | None = None
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            event = json.loads(line)
            if event.get("type") == "dw_lsg_response_plaintext":
                plaintext_response_count += 1
                continue
            if event.get("type") == "dw_lsg_serialized" and event.get("message_type") == 5:
                serialized_response_count += 1
                continue
            if event.get("type") != "dw_lsg_decoded" or event.get("message_type") != 0x85:
                continue
            raw = event_bytes(event)
            if raw is None or len(raw) < 3:
                continue
            timestamp = iso_time(event.get("timestamp") or event.get("recorded_at"))
            if first_time is None and timestamp is not None:
                first_time = timestamp
            elapsed_ms = None
            if first_time is not None and timestamp is not None:
                elapsed_ms = round((timestamp - first_time).total_seconds() * 1000)
            service_id, protocol_version, task_id = raw[:3]
            requests.append({
                "sequence": len(requests) + 1,
                "line": line_number,
                "elapsed_ms": elapsed_ms,
                "service_id": service_id,
                "service_hex": f"0x{service_id:02X}",
                "service_name": SERVICE_NAMES.get(service_id, "Unknown"),
                "protocol_version": protocol_version,
                "task_id": task_id,
                "task_hex": f"0x{task_id:02X}",
                "task_name": TASK_NAMES.get((service_id, task_id), "unknown"),
                "decoded_length": event.get("decoded_length", len(raw)),
                "captured_length": len(raw),
                "strings": ascii_strings(raw[3:]),
                "preview_hex": raw[:48].hex(),
            })
    return requests, plaintext_response_count or serialized_response_count


def aggregate_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for request in requests:
        groups[(request["service_id"], request["task_id"])].append(request)

    rows = []
    for (service_id, task_id), items in groups.items():
        strings: list[str] = []
        for item in items:
            for value in item["strings"]:
                if value not in strings:
                    strings.append(value)
        lengths = [int(item["decoded_length"]) for item in items]
        rows.append({
            "service_id": service_id,
            "service_hex": f"0x{service_id:02X}",
            "service_name": SERVICE_NAMES.get(service_id, "Unknown"),
            "task_id": task_id,
            "task_hex": f"0x{task_id:02X}",
            "task_name": TASK_NAMES.get((service_id, task_id), "unknown"),
            "occurrences": len(items),
            "first_sequence": items[0]["sequence"],
            "min_length": min(lengths),
            "max_length": max(lengths),
            "strings": strings,
            "preview_hex": items[0]["preview_hex"],
        })
    return sorted(rows, key=lambda row: row["first_sequence"])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "service_hex", "service_name", "task_hex", "task_name", "occurrences",
        "first_sequence", "min_length", "max_length", "strings", "preview_hex",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "strings": " | ".join(row["strings"])})


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def evidence_summary(
    values: list[str],
    limit: int = 3,
    service_id: int | None = None,
    task_id: int | None = None,
) -> str:
    summaries = []
    for value in values[:limit]:
        if service_id == 0x47 and task_id in (0x03, 0x07):
            value = value.split("|", 1)[0]
        elif "|" in value:
            value = value.split("|", 1)[0] + "|..."
        elif len(value) > 80:
            value = value[:77] + "..."
        summaries.append(value)
    return "; ".join(summaries) or "-"


def write_markdown(
    path: Path,
    source: Path,
    requests: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    response_count: int,
) -> None:
    lines = [
        "# CODOL DW3 request matrix",
        "",
        f"Generated from `{source}` by `references/client_probe/AnalyzeCodolTrace.py`.",
        "",
        "A request begins with `service_id`, protocol version, then `task_id`. The",
        "captured CODOL flow uses protocol version `3`. Service names are",
        "cross-checked against CODOL revival notes and reference DW3 implementations;",
        "task names remain `unknown` where the 2015 client contract is not confirmed.",
        "",
        f"- Requests: `{len(requests)}`",
        f"- Unique service/task pairs: `{len(rows)}`",
        f"- Serialized responses captured: `{response_count}`",
        "",
        "## Aggregate",
        "",
        "| Service | Task | Name | Count | First | Length | Evidence strings |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for row in rows:
        evidence = evidence_summary(
            row["strings"],
            service_id=row["service_id"],
            task_id=row["task_id"],
        )
        length = str(row["min_length"])
        if row["min_length"] != row["max_length"]:
            length += f"-{row['max_length']}"
        lines.append(
            f"| `{row['service_hex']}` {row['service_name']} | `{row['task_hex']}` | "
            f"{row['task_name']} | {row['occurrences']} | {row['first_sequence']} | "
            f"{length} | {markdown_cell(evidence)} |"
        )

    lines.extend([
        "",
        "## Sequence",
        "",
        "| # | Time ms | Service/task | Length | Evidence strings |",
        "|---:|---:|---|---:|---|",
    ])
    for request in requests:
        evidence = evidence_summary(
            request["strings"],
            limit=2,
            service_id=request["service_id"],
            task_id=request["task_id"],
        )
        elapsed = "-" if request["elapsed_ms"] is None else str(request["elapsed_ms"])
        lines.append(
            f"| {request['sequence']} | {elapsed} | `{request['service_hex']}/{request['task_hex']}` "
            f"{request['service_name']}::{request['task_name']} | {request['decoded_length']} | "
            f"{markdown_cell(evidence)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    events = args.events.resolve()
    if not events.is_file():
        raise SystemExit(f"Trace does not exist: {events}")
    output_dir = (args.output_dir or events.parent / "analysis").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown = args.markdown.resolve()
    markdown.parent.mkdir(parents=True, exist_ok=True)

    requests, response_count = load_requests(events)
    rows = aggregate_requests(requests)
    (output_dir / "dw_requests.json").write_text(
        json.dumps({"source": str(events), "requests": requests, "aggregate": rows}, indent=2),
        encoding="utf-8",
    )
    write_csv(output_dir / "dw_requests.csv", rows)
    try:
        markdown_source = events.relative_to(repository)
    except ValueError:
        markdown_source = events
    write_markdown(markdown, markdown_source, requests, rows, response_count)
    print(f"Parsed {len(requests)} requests across {len(rows)} service/task pairs.")
    print(f"JSON/CSV: {output_dir}")
    print(f"Markdown: {markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
