#!/usr/bin/env python3
"""Validate and report the CODOL gameplay source-evidence audit."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


STATUSES = {
    "in_progress",
    "reviewed_partial",
    "reviewed_project_boundary",
    "reviewed_complete",
}
MARKER_PREFIXES = ("CODREF", "CODDIFF", "OLMOD", "TODO(CODOL)")
COVERAGES = {"symbol", "function", "full_file"}
BLOCK_CLASSIFICATIONS = {
    "native_reference",
    "codol_difference",
    "project_boundary",
    "todo",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scoped_files(root: Path, scope: dict[str, Any]) -> set[str]:
    included: set[str] = set()
    for pattern in scope.get("include", []):
        included.update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )
    for pattern in scope.get("exclude", []):
        included.difference_update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )
    return included


def validate(
    root: Path,
    catalog: dict[str, Any],
    matrix: dict[str, Any],
) -> tuple[list[str], set[str], set[str], Counter[str], int, int]:
    errors: list[str] = []
    require(catalog.get("schema_version") == 1, "schema_version must be 1", errors)
    require(
        catalog.get("catalog_id") == "codol_gameplay_source_audit",
        "catalog_id is invalid",
        errors,
    )
    scope = catalog.get("scope")
    require(isinstance(scope, dict), "scope must be an object", errors)
    if not isinstance(scope, dict):
        return errors, set(), set(), Counter(), 0, 0
    for key in ("include", "exclude"):
        require(
            isinstance(scope.get(key), list)
            and all(isinstance(item, str) and item for item in scope[key]),
            f"scope.{key} must be an array of non-empty strings",
            errors,
        )

    files = scoped_files(root, scope)
    require(bool(files), "scope does not select any files", errors)
    matrix_ids = {
        entry.get("id")
        for entry in matrix.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    reviews = catalog.get("reviews")
    require(isinstance(reviews, list), "reviews must be an array", errors)
    if not isinstance(reviews, list):
        return errors, files, set(), Counter(), 0, 0

    seen: set[tuple[str, str]] = set()
    touched_files: set[str] = set()
    fully_audited_files: set[str] = set()
    statuses: Counter[str] = Counter()
    function_audits = 0
    audited_blocks = 0
    for index, review in enumerate(reviews):
        prefix = f"reviews[{index}]"
        require(isinstance(review, dict), f"{prefix} must be an object", errors)
        if not isinstance(review, dict):
            continue
        path = review.get("path")
        symbol = review.get("symbol")
        status = review.get("status")
        # Schema-1 catalogs predate coverage tracking. Treat their entries as
        # symbol-only evidence so old reviews cannot silently claim a whole
        # file was inspected.
        coverage = review.get("coverage", "symbol")
        marker = review.get("marker")
        ids = review.get("matrix_ids")
        require(isinstance(path, str) and path in files, f"{prefix}.path is outside scope", errors)
        require(isinstance(symbol, str) and bool(symbol), f"{prefix}.symbol is invalid", errors)
        require(status in STATUSES, f"{prefix}.status is invalid", errors)
        require(coverage in COVERAGES, f"{prefix}.coverage is invalid", errors)
        require(
            isinstance(marker, str)
            and marker.startswith(MARKER_PREFIXES),
            f"{prefix}.marker is invalid",
            errors,
        )
        require(
            isinstance(ids, list) and bool(ids) and all(item in matrix_ids for item in ids),
            f"{prefix}.matrix_ids contains an unknown function-matrix id",
            errors,
        )
        for field in ("evidence", "remaining"):
            require(
                isinstance(review.get(field), str) and bool(review[field].strip()),
                f"{prefix}.{field} must be non-empty",
                errors,
            )
        if isinstance(path, str) and isinstance(symbol, str):
            key = (path, symbol)
            require(key not in seen, f"duplicate review for {path}:{symbol}", errors)
            seen.add(key)
            touched_files.add(path)
            if coverage == "full_file":
                fully_audited_files.add(path)
            if status in STATUSES:
                statuses[status] += 1
            source_path = root / path
            if source_path.is_file():
                source = source_path.read_text(encoding="utf-8")
                require(symbol in source, f"{prefix}.symbol is not present in {path}", errors)
                if isinstance(marker, str):
                    require(marker in source, f"{prefix}.marker is not present in {path}", errors)
                if coverage == "function":
                    function_audits += 1
                    function_source = ""
                    function_range = review.get("range")
                    require(
                        isinstance(function_range, dict),
                        f"{prefix}.range is required for function coverage",
                        errors,
                    )
                    if isinstance(function_range, dict):
                        start_anchor = function_range.get("start")
                        end_anchor = function_range.get("end")
                        require(
                            isinstance(start_anchor, str) and bool(start_anchor),
                            f"{prefix}.range.start is invalid",
                            errors,
                        )
                        require(
                            isinstance(end_anchor, str) and bool(end_anchor),
                            f"{prefix}.range.end is invalid",
                            errors,
                        )
                        if isinstance(start_anchor, str) and isinstance(end_anchor, str):
                            start_index = source.find(start_anchor)
                            end_index = source.find(end_anchor, max(0, start_index + 1))
                            require(
                                start_index >= 0,
                                f"{prefix}.range.start is not present in {path}",
                                errors,
                            )
                            require(
                                end_index > start_index,
                                f"{prefix}.range.end does not follow range.start in {path}",
                                errors,
                            )
                            if start_index >= 0 and end_index > start_index:
                                function_source = source[start_index:end_index]

                    blocks = review.get("blocks")
                    require(
                        isinstance(blocks, list) and bool(blocks),
                        f"{prefix}.blocks is required for function coverage",
                        errors,
                    )
                    block_ids: set[str] = set()
                    if isinstance(blocks, list):
                        for block_index, block in enumerate(blocks):
                            block_prefix = f"{prefix}.blocks[{block_index}]"
                            require(
                                isinstance(block, dict),
                                f"{block_prefix} must be an object",
                                errors,
                            )
                            if not isinstance(block, dict):
                                continue
                            block_id = block.get("id")
                            classification = block.get("classification")
                            block_marker = block.get("marker")
                            require(
                                isinstance(block_id, str) and bool(block_id),
                                f"{block_prefix}.id is invalid",
                                errors,
                            )
                            if isinstance(block_id, str):
                                require(
                                    block_id not in block_ids,
                                    f"{prefix} has duplicate block id {block_id}",
                                    errors,
                                )
                                block_ids.add(block_id)
                            require(
                                classification in BLOCK_CLASSIFICATIONS,
                                f"{block_prefix}.classification is invalid",
                                errors,
                            )
                            require(
                                isinstance(block_marker, str)
                                and block_marker.startswith(MARKER_PREFIXES),
                                f"{block_prefix}.marker is invalid",
                                errors,
                            )
                            if isinstance(block_marker, str):
                                require(
                                    block_marker in function_source,
                                    f"{block_prefix}.marker is not present in the audited function range",
                                    errors,
                                )
                            for field in ("evidence", "remaining"):
                                require(
                                    isinstance(block.get(field), str)
                                    and bool(block[field].strip()),
                                    f"{block_prefix}.{field} must be non-empty",
                                    errors,
                                )
                            audited_blocks += 1

    return (
        errors,
        files - fully_audited_files,
        touched_files - fully_audited_files,
        statuses,
        function_audits,
        audited_blocks,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).with_name("catalogs") / "codol_gameplay_source_audit.json",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path(__file__).with_name("catalogs") / "codol_server_function_matrix.json",
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    try:
        catalog = load_json(args.catalog)
        matrix = load_json(args.matrix)
    except (OSError, json.JSONDecodeError) as error:
        print(f"source audit: {error}", file=sys.stderr)
        return 1

    errors, incomplete, partial, statuses, function_audits, audited_blocks = validate(
        root, catalog, matrix
    )
    if args.require_complete and incomplete:
        errors.append(f"{len(incomplete)} scoped files remain incompletely audited")
    if errors:
        for error in errors:
            print(f"source audit: {error}", file=sys.stderr)
        return 1

    print(
        "CODOL gameplay source audit valid: "
        f"reviews={sum(statuses.values())}, "
        f"fully_audited_files={len(scoped_files(root, catalog['scope'])) - len(incomplete)}, "
        f"partially_audited_files={len(partial)}, "
        f"untouched_files={len(incomplete - partial)}, "
        f"function_audits={function_audits}, "
        f"audited_blocks={audited_blocks}, "
        + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items()))
    )
    if incomplete:
        print("Incomplete file audit inventory:")
        for path in sorted(incomplete):
            state = "partial" if path in partial else "untouched"
            print(f"  [{state}] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
