"""Extract NUL-terminated printable strings from a gamestate sample.

This is a read-only helper for tracing the CODOL gamestate/configstring layout.
It reports nearby bytes so candidate configstring indices can be checked later.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "firingrange-gamestate.bin"


def printable(b: int) -> bool:
    return 32 <= b < 127


def extract(data: bytes):
    rows = []
    i = 0
    while i < len(data):
        if not printable(data[i]):
            i += 1
            continue
        start = i
        while i < len(data) and printable(data[i]):
            i += 1
        if i >= len(data) or data[i] != 0:
            continue
        raw = data[start:i]
        if len(raw) >= 1:
            rows.append({
                "offset": start,
                "length": len(raw),
                "text": raw.decode("latin1"),
                "prev4": data[max(0, start - 4):start].hex(" "),
            })
        i += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    data = args.input.read_bytes()
    rows = extract(data)
    payload = {
        "source": str(args.input),
        "size": len(data),
        "strings": rows,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(f"source={args.input} size={len(data)} strings={len(rows)}")
        for row in rows:
            print(f"0x{row['offset']:04X} prev=[{row['prev4']}] {row['text']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
