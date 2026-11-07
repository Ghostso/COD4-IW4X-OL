#!/usr/bin/env python3
"""Compare two CODOL XAsset manifests without attaching to the game."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


STABLE_METADATA_FIELDS = ("compressed_length", "length", "bytes_written", "sha256")


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), list):
        raise ValueError(f"invalid XAsset manifest: {path}")
    return manifest


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def stable_record(asset: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    record = {"name": asset["name"]}
    for field in STABLE_METADATA_FIELDS:
        if field in asset:
            record[field] = asset[field]
    output = asset.get("output")
    if "sha256" not in record and isinstance(output, str):
        payload = manifest_dir / output
        if payload.is_file():
            record["sha256"] = file_sha256(payload)
    return record


def grouped_assets(manifest: dict[str, Any], manifest_dir: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for asset in manifest["assets"]:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
            continue
        grouped[asset["name"].casefold()].append(stable_record(asset, manifest_dir))
    for records in grouped.values():
        records.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return dict(grouped)


def comparable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [dict(record, name=record["name"].casefold()) for record in records]
    return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))


def diff_manifests(
    before: dict[str, Any],
    after: dict[str, Any],
    before_dir: Path = Path(),
    after_dir: Path = Path(),
) -> dict[str, Any]:
    before_assets = grouped_assets(before, before_dir)
    after_assets = grouped_assets(after, after_dir)
    before_names = set(before_assets)
    after_names = set(after_assets)
    added_keys = sorted(after_names - before_names)
    removed_keys = sorted(before_names - after_names)
    common_keys = sorted(before_names & after_names)
    changed_keys = [
        key
        for key in common_keys
        if comparable_records(before_assets[key]) != comparable_records(after_assets[key])
    ]
    unchanged_count = len(common_keys) - len(changed_keys)

    return {
        "schema_version": 1,
        "before_asset_count": len(before.get("assets", [])),
        "after_asset_count": len(after.get("assets", [])),
        "added_count": len(added_keys),
        "removed_count": len(removed_keys),
        "changed_count": len(changed_keys),
        "unchanged_count": unchanged_count,
        "added": [after_assets[key] for key in added_keys],
        "removed": [before_assets[key] for key in removed_keys],
        "changed": [
            {"name": after_assets[key][0]["name"], "before": before_assets[key], "after": after_assets[key]}
            for key in changed_keys
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    before_path = args.before.resolve()
    after_path = args.after.resolve()
    result = diff_manifests(
        load_manifest(before_path),
        load_manifest(after_path),
        before_path.parent,
        after_path.parent,
    )
    result["before"] = str(before_path)
    result["after"] = str(after_path)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Saved manifest diff: {output}")
    else:
        print(text, end="")
    print(
        f"Added: {result['added_count']}; removed: {result['removed_count']}; "
        f"changed: {result['changed_count']}; unchanged: {result['unchanged_count']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
