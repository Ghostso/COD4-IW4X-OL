#!/usr/bin/env python3
"""Read-only, path-complete inventory for the CODOL server audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "CODOL_ANALYSIS_20261020"

DEFAULT_SCOPES = ["."]

FIRST_ROUND_EXCLUDES = {
    ".git",
    "__pycache__",
    "CoD4x_Server-21.2",
    "IW4X",
    "CODOL_ANALYSIS_20261020",
}

EXCLUDED_PARTS = {".git", "__pycache__"}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in EXCLUDED_PARTS and not (Path(current) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(current) / name
            if not path.is_symlink():
                yield path


def extension_of(path: Path) -> str:
    return path.suffix.lower() or "<none>"


def coarse_class(rel: str, ext: str) -> str:
    lower = rel.lower()
    if ext in {".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".py", ".lua", ".gsc"}:
        return "source"
    if ext in {".exe", ".dll", ".sys", ".ocx", ".o", ".lib", ".obj", ".pdb"}:
        return "binary"
    if ext in {
        ".ff", ".iwd", ".zone", ".pak", ".bin", ".slot0", ".slot1", ".slot2",
        ".slot3", ".slot4", ".slot5", ".slot6", ".slot7", ".slot8", ".slot9",
        ".slot10", ".slot11", ".slot12", ".slot13",
    }:
        return "capture_or_asset"
    if ext in {".log", ".txt", ".csv", ".tsv", ".jsonl", ".json", ".md", ".html"}:
        return "evidence_or_text"
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".gif"}:
        return "media"
    if ext in {".cfg", ".ini", ".toml", ".yaml", ".yml", ".xml"}:
        return "configuration"
    if "reference" in lower or "docs/references" in lower:
        return "reference"
    return "other"


def path_label(rel: str) -> str:
    lower = rel.lower()
    if rel.startswith("COD OL/"):
        return "codol-3.19-client"
    if rel.startswith("CoD4x_Server-21.2/"):
        return "cod4x-21.2"
    if rel.startswith("IW4X/iw4x-client/"):
        return "iw4x-client-source"
    if rel.startswith("DEV-BOOKING/_lineage021/iw4x-rawfiles/"):
        return "iw4x-raw-assets"
    if rel.startswith("CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/"):
        return "codol-2697-derived-analysis"
    if rel.startswith("CODOL-BATTLE-SERVER-") or rel.startswith("CODOL-COMBAT-"):
        return "codol-battle-server-audit-evidence"
    if rel.startswith("E") and len(rel) > 4 and rel[1:3].isdigit():
        return "codol-client-reverse-evidence"
    if rel.startswith("CLIENT-DEMONWARE-") or rel.startswith("CODOL-DEMONWARE-"):
        return "codol-demonware-evidence"
    if rel.startswith("CODOL-KEYFLOW-"):
        return "codol-keyflow-evidence"
    if rel.startswith("CODOL-TARGET-"):
        return "codol-target-evidence"
    if rel.startswith("DEV-BOOKING/"):
        return "codol-booking-evidence"
    if rel.startswith("run_codol_001/"):
        return "codol-frozen-run-evidence"
    if rel.startswith("PROJECT_CHAIN_COPY_"):
        return "codol-frozen-chain-copy"
    if rel.startswith("_map_extract/"):
        return "codol-map-assets"
    if rel.startswith("DEMO_GOLDEN_BACKUP_20261015/"):
        return "codol-demo-evidence"
    if rel.startswith("CODOL_NATIVE_BATTLE_CHAIN_20261019/"):
        return "codol-native-battle-evidence"
    if rel.startswith("CODOL_LOCAL_ENGINE_CHAIN_20261019/"):
        return "codol-local-engine-evidence"
    if rel.startswith("CODOL_RUNTIME_COD_20261019/"):
        return "codol-runtime-cod"
    if rel.startswith("CODOL_ISOLATED_SANDBOX_20261019/"):
        return "codol-isolated-sandbox"
    if rel.startswith("REF_LOBBY_KIT_CAP009/"):
        return "codol-control-plane-copy"
    if rel.startswith("CODOLServer/"):
        return "codol-control-plane-archive"
    if rel.startswith("backup_reverse_engineering/"):
        return "codol-reverse-backup"
    if rel.startswith("backups/"):
        return "codol-backup"
    if rel.startswith("CODOLLauncher/"):
        return "codol-launcher"
    if rel.startswith("WeGame") or rel.startswith("COD8/"):
        return "codol-platform-reference"
    if rel.startswith("analysis_logs/") or rel.startswith("_rev_analysis/"):
        return "codol-analysis-log"
    if rel.startswith("REF_LOBBY_KIT/mem_linear_"):
        return "historical-memory-slice"
    if rel.startswith("REF_LOBBY_KIT/mem_marketplace/"):
        return "marketplace-memory-slice"
    if rel.startswith("REF_LOBBY_KIT/mem_"):
        return "reverse-memory-slice"
    if "/run_" in lower or lower.startswith("ref_lobby_kit/run_"):
        return "historical-run-capture"
    if rel.startswith("EARLY_SERVER_ANALYSIS/"):
        return "codol-1.1.1.13-reference"
    if rel.startswith("_e1_regression/ol-mod-olfinal/"):
        return "codol-3.3.3.3-reference"
    if rel.startswith("CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047/"):
        return "codol-server-foundation-047"
    if rel.startswith("CODOL-Combat-Server-v0.1/"):
        return "codol-server-prototype-v0.1"
    if rel.startswith("REF_LOBBY_KIT/"):
        return "codol-frozen-control-plane"
    if rel.startswith("CODOL_VERIFIED_GOLDEN_20261019/"):
        return "codol-protected-golden"
    return "codol-other-workspace"


def build_inventory(
    scopes: list[str], force_hash: bool
) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    by_size: dict[int, list[Path]] = defaultdict(list)
    missing: list[str] = []

    for scope in scopes:
        root = (ROOT / scope).resolve()
        try:
            root.relative_to(ROOT.resolve())
        except ValueError:
            missing.append(scope + " [outside workspace root]")
            continue
        if not root.exists():
            missing.append(scope)
            continue
        candidates = [root] if root.is_file() else iter_files(root)
        for path in candidates:
            rel = path.relative_to(ROOT).as_posix()
            if scopes == ["."] and rel.split("/", 1)[0] in FIRST_ROUND_EXCLUDES:
                continue
            stat = path.stat()
            by_size[stat.st_size].append(path)
            rows.append(
                {
                    "scope": scope,
                    "path": rel,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "extension": extension_of(path),
                    "coarse_class": coarse_class(rel, extension_of(path)),
                    "object_label": path_label(rel),
                }
            )

    hashes: dict[str, str] = {}
    duplicate_groups: dict[str, list[str]] = defaultdict(list)
    deferred: list[str] = []
    for size, paths in by_size.items():
        if size == 0:
            for path in paths:
                hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                    b""
                ).hexdigest().upper()
            continue
        if False and len(paths) == 1 and not force_hash and size > 32 * 1024 * 1024:
            deferred.extend(path.relative_to(ROOT).as_posix() for path in paths)
            continue
        for index, path in enumerate(paths):
            rel = path.relative_to(ROOT).as_posix()
            digest = sha256_file(path)
            hashes[rel] = digest
            duplicate_groups[digest].append(rel)
            if index % 500 == 0:
                print(f"hash {rel}", file=sys.stderr)

    for row in rows:
        rel = str(row["path"])
        digest = hashes.get(rel, "")
        row["sha256"] = digest
        row["duplicate_count"] = (
            len(duplicate_groups.get(digest, [])) if digest else 0
        )
        row["status"] = (
            "INVENTORIED_HASHED"
            if digest
            else "INVENTORIED_HASH_DEFERRED_NONDUPLICATE_OVER_32M"
        )

    duplicate_bytes = 0
    duplicate_paths = 0
    for paths in duplicate_groups.values():
        if len(paths) > 1:
            duplicate_paths += len(paths)
            duplicate_bytes += sum(
                (ROOT / rel).stat().st_size for rel in paths
            ) - (ROOT / paths[0]).stat().st_size

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "root": str(ROOT),
        "scopes": scopes,
        "missing_scopes": missing,
        "files": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "unique_hashed_contents": len(duplicate_groups),
        "hashed_paths": len(hashes),
        "hash_deferred_paths": len(deferred),
        "duplicate_paths": duplicate_paths,
        "duplicate_bytes": duplicate_bytes,
        "by_scope": dict(Counter(str(row["scope"]) for row in rows)),
        "by_class": dict(Counter(str(row["coarse_class"]) for row in rows)),
        "by_label": dict(Counter(str(row["object_label"]) for row in rows)),
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "scope", "path", "size", "mtime_ns", "extension", "coarse_class",
        "object_label", "sha256", "duplicate_count", "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", action="append", dest="scopes")
    parser.add_argument("--force-hash", action="store_true")
    parser.add_argument("--output-prefix", default="AUDIT_FILE_INVENTORY")
    args = parser.parse_args()

    scopes = args.scopes or DEFAULT_SCOPES
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory_rows, summary = build_inventory(scopes, args.force_hash)
    write_csv(OUT_DIR / f"{args.output_prefix}.csv", inventory_rows)
    (OUT_DIR / f"{args.output_prefix}.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
