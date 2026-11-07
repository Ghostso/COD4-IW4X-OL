#!/usr/bin/env python3
"""Validate the hand-maintained CODOL server function recovery matrix."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {
    "client_shared",
    "embedded_server",
    "server_only",
    "client_only",
    "unknown",
}
IMPLEMENTATION_STATUSES = {"implemented", "partial", "missing", "reference_only", "unknown"}
CONFIDENCE_LEVELS = {"high", "medium", "low", "unknown"}
MAPPING_STATUSES = {
    "confirmed_client_shared",
    "confirmed_embedded_server",
    "not_applicable_server_only",
    "confirmed_client_only",
    "unverified",
}
REFERENCE_MATCHES = {"direct", "analogue", "unverified", "none"}
REFERENCE_KEYS = {"bo1", "ghosts", "bo2"}
ADDRESS_RE = re.compile(r"^0x[0-9A-F]+$")
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

ENTRY_LIST_FIELDS = (
    "callers",
    "callees",
    "constants",
    "fields",
    "data_ownership",
    "differences",
    "missing_dependencies",
    "source_locations",
    "evidence",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_address_pair(
    value: Any,
    path: str,
    errors: list[str],
    *,
    require_mapping_status: bool = False,
) -> None:
    require(isinstance(value, dict), f"{path} must be an object", errors)
    if not isinstance(value, dict):
        return
    address = value.get("address")
    name = value.get("name")
    require(
        (address is None) == (name is None),
        f"{path}.address and {path}.name must both be null or both be present",
        errors,
    )
    if address is not None:
        require(
            isinstance(address, str) and bool(ADDRESS_RE.fullmatch(address)),
            f"{path}.address must be an uppercase hexadecimal VA",
            errors,
        )
        require(isinstance(name, str) and bool(name), f"{path}.name must be non-empty", errors)
    if require_mapping_status:
        require(
            value.get("mapping_status") in MAPPING_STATUSES,
            f"{path}.mapping_status is invalid",
            errors,
        )
    else:
        require(value.get("match") in REFERENCE_MATCHES, f"{path}.match is invalid", errors)


def validate_evidence(value: Any, path: str, errors: list[str]) -> None:
    require(isinstance(value, list) and bool(value), f"{path} must be a non-empty array", errors)
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        require(isinstance(item, dict), f"{item_path} must be an object", errors)
        if not isinstance(item, dict):
            continue
        for key in ("kind", "source", "detail"):
            require(
                isinstance(item.get(key), str) and bool(item[key].strip()),
                f"{item_path}.{key} must be a non-empty string",
                errors,
            )


def validate_entry(entry: Any, index: int, errors: list[str]) -> None:
    path = f"entries[{index}]"
    require(isinstance(entry, dict), f"{path} must be an object", errors)
    if not isinstance(entry, dict):
        return
    identifier = entry.get("id")
    require(
        isinstance(identifier, str) and bool(ID_RE.fullmatch(identifier)),
        f"{path}.id must be stable snake_case",
        errors,
    )
    require(
        isinstance(entry.get("canonical_name"), str) and bool(entry["canonical_name"].strip()),
        f"{path}.canonical_name must be non-empty",
        errors,
    )
    require(entry.get("classification") in CLASSIFICATIONS, f"{path}.classification is invalid", errors)
    require(
        entry.get("implementation_status") in IMPLEMENTATION_STATUSES,
        f"{path}.implementation_status is invalid",
        errors,
    )
    require(entry.get("confidence") in CONFIDENCE_LEVELS, f"{path}.confidence is invalid", errors)
    require(
        isinstance(entry.get("responsibility"), str) and bool(entry["responsibility"].strip()),
        f"{path}.responsibility must be non-empty",
        errors,
    )
    validate_address_pair(entry.get("codol"), f"{path}.codol", errors, require_mapping_status=True)
    references = entry.get("references")
    require(isinstance(references, dict), f"{path}.references must be an object", errors)
    if isinstance(references, dict):
        require(set(references) == REFERENCE_KEYS, f"{path}.references must contain BO1, Ghosts, and BO2", errors)
        for key in sorted(REFERENCE_KEYS):
            validate_address_pair(references.get(key), f"{path}.references.{key}", errors)
            reference = references.get(key)
            if isinstance(reference, dict) and reference.get("match") in {"direct", "analogue"}:
                require(
                    reference.get("address") is not None,
                    f"{path}.references.{key}: mapped references require an address",
                    errors,
                )
    for field in ENTRY_LIST_FIELDS:
        require(isinstance(entry.get(field), list), f"{path}.{field} must be an array", errors)
    validate_evidence(entry.get("evidence"), f"{path}.evidence", errors)
    classification = entry.get("classification")
    codol = entry.get("codol")
    if classification == "embedded_server":
        require(
            isinstance(codol, dict)
            and codol.get("address") is not None
            and codol.get("name") is not None,
            f"{path}: embedded_server entries require a confirmed CODOL address",
            errors,
        )
        require(
            isinstance(codol, dict)
            and codol.get("mapping_status") == "confirmed_embedded_server",
            f"{path}: embedded_server entries require confirmed_embedded_server mapping status",
            errors,
        )
    elif classification == "server_only":
        require(
            isinstance(codol, dict)
            and codol.get("address") is None
            and codol.get("name") is None,
            f"{path}: server_only entries cannot claim a CODOL client address",
            errors,
        )
        require(
            isinstance(codol, dict)
            and codol.get("mapping_status") == "not_applicable_server_only",
            f"{path}: server_only entries require not_applicable_server_only mapping status",
            errors,
        )
    elif classification == "client_shared":
        require(
            isinstance(codol, dict)
            and codol.get("address") is not None
            and codol.get("name") is not None,
            f"{path}: client_shared entries require a confirmed CODOL address",
            errors,
        )
        require(
            isinstance(codol, dict)
            and codol.get("mapping_status") == "confirmed_client_shared",
            f"{path}: client_shared entries require confirmed_client_shared mapping status",
            errors,
        )
    elif classification == "client_only":
        require(
            isinstance(codol, dict)
            and codol.get("address") is not None
            and codol.get("name") is not None,
            f"{path}: client_only entries require a confirmed CODOL address",
            errors,
        )
        require(
            isinstance(codol, dict)
            and codol.get("mapping_status") == "confirmed_client_only",
            f"{path}: client_only entries require confirmed_client_only mapping status",
            errors,
        )
    elif classification == "unknown":
        require(
            isinstance(codol, dict)
            and codol.get("mapping_status") == "unverified",
            f"{path}: unknown entries require unverified mapping status",
            errors,
        )
    if entry.get("confidence") in {"low", "unknown"}:
        require(
            bool(entry.get("differences")) or bool(entry.get("missing_dependencies")),
            f"{path}: low-confidence entries must state an uncertainty or missing dependency",
            errors,
        )


def validate_catalog(catalog: Any) -> list[str]:
    errors: list[str] = []
    require(isinstance(catalog, dict), "catalog root must be an object", errors)
    if not isinstance(catalog, dict):
        return errors
    require(catalog.get("schema_version") == 1, "schema_version must be 1", errors)
    require(catalog.get("catalog_id") == "codol_server_function_matrix", "catalog_id is invalid", errors)
    require(isinstance(catalog.get("reference_builds"), dict), "reference_builds must be an object", errors)
    entries = catalog.get("entries")
    require(isinstance(entries, list) and bool(entries), "entries must be a non-empty array", errors)
    if not isinstance(entries, list):
        return errors
    for index, entry in enumerate(entries):
        validate_entry(entry, index, errors)
    identifiers = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    duplicates = sorted(key for key, count in Counter(identifiers).items() if count > 1)
    require(not duplicates, f"duplicate entry ids: {', '.join(duplicates)}", errors)
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("catalogs") / "codol_server_function_matrix.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to read catalog: {error}", file=sys.stderr)
        return 2
    errors = validate_catalog(catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    classifications = Counter(entry["classification"] for entry in catalog["entries"])
    statuses = Counter(entry["implementation_status"] for entry in catalog["entries"])
    print(
        f"Validated {len(catalog['entries'])} entries; "
        f"classifications={dict(sorted(classifications.items()))}; "
        f"implementation_statuses={dict(sorted(statuses.items()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
