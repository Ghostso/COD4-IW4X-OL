#!/usr/bin/env python3
"""Inspect and compare CODOL Profiles2 Publicprofile payloads."""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path


TYPE_U32 = 0x08
TYPE_U64 = 0x0A
TYPE_BLOB = 0x13
PROFILE_SIZE = 0x8000


class ProfileError(ValueError):
    pass


@dataclass
class ProfileMetadata:
    path: str
    stored_size: int
    optional_user_id: int | None
    compressed: bool
    format_version: int
    outer_crc32: int
    blob_size: int
    profile_size: int
    embedded_crc32: int
    calculated_crc32: int
    crc_valid: bool
    trailing_size: int


@dataclass
class LoadedProfile:
    metadata: ProfileMetadata
    data: bytes
    trailing: bytes


def read_u32(data: bytes, cursor: int) -> tuple[int, int]:
    if cursor + 5 > len(data) or data[cursor] != TYPE_U32:
        raise ProfileError(f"expected typed uint32 at file offset 0x{cursor:X}")
    return struct.unpack_from("<I", data, cursor + 1)[0], cursor + 5


def read_u64(data: bytes, cursor: int) -> tuple[int, int]:
    if cursor + 9 > len(data) or data[cursor] != TYPE_U64:
        raise ProfileError(f"expected typed uint64 at file offset 0x{cursor:X}")
    return struct.unpack_from("<Q", data, cursor + 1)[0], cursor + 9


def load_profile(path: Path) -> LoadedProfile:
    stored = path.read_bytes()
    cursor = 0
    optional_user_id = None
    if stored[:1] == bytes([TYPE_U64]):
        optional_user_id, cursor = read_u64(stored, cursor)

    compressed_value, cursor = read_u32(stored, cursor)
    format_version, cursor = read_u32(stored, cursor)
    outer_crc32, cursor = read_u32(stored, cursor)
    if cursor >= len(stored) or stored[cursor] != TYPE_BLOB:
        raise ProfileError(f"expected typed blob at file offset 0x{cursor:X}")
    cursor += 1
    blob_size, cursor = read_u32(stored, cursor)
    blob_end = cursor + blob_size
    if blob_end > len(stored):
        raise ProfileError(
            f"blob declares {blob_size} bytes but only {len(stored) - cursor} remain"
        )
    blob = stored[cursor:blob_end]

    compressed = compressed_value != 0
    try:
        profile = zlib.decompress(blob) if compressed else blob
    except zlib.error as error:
        raise ProfileError(f"zlib decompression failed: {error}") from error
    if len(profile) != PROFILE_SIZE:
        raise ProfileError(
            f"decoded profile is 0x{len(profile):X} bytes, expected 0x{PROFILE_SIZE:X}"
        )

    embedded_crc32 = struct.unpack_from("<I", profile, 0)[0]
    calculated_crc32 = zlib.crc32(profile[4:]) & 0xFFFFFFFF
    metadata = ProfileMetadata(
        path=str(path.resolve()),
        stored_size=len(stored),
        optional_user_id=optional_user_id,
        compressed=compressed,
        format_version=format_version,
        outer_crc32=outer_crc32,
        blob_size=blob_size,
        profile_size=len(profile),
        embedded_crc32=embedded_crc32,
        calculated_crc32=calculated_crc32,
        crc_valid=(outer_crc32 == embedded_crc32 == calculated_crc32),
        trailing_size=len(stored) - blob_end,
    )
    return LoadedProfile(metadata=metadata, data=profile, trailing=stored[blob_end:])


def expand_inputs(values: list[str]) -> list[Path]:
    result: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            result.extend(sorted(item for item in path.iterdir() if item.is_file()))
        else:
            result.append(path)
    return result


def difference_runs(left: bytes, right: bytes, start: int = 4) -> list[tuple[int, int]]:
    changed = [index for index in range(start, min(len(left), len(right))) if left[index] != right[index]]
    if not changed:
        return []
    runs: list[tuple[int, int]] = []
    run_start = previous = changed[0]
    for index in changed[1:]:
        if index != previous + 1:
            runs.append((run_start, previous + 1))
            run_start = index
        previous = index
    runs.append((run_start, previous + 1))
    return runs


def scalar_view(data: bytes, start: int, end: int) -> dict[str, int]:
    result: dict[str, int] = {}
    size = end - start
    if size == 1:
        result["u8"] = data[start]
    if size <= 2 and start + 2 <= len(data):
        result["u16le"] = struct.unpack_from("<H", data, start)[0]
    if size <= 4 and start + 4 <= len(data):
        result["u32le"] = struct.unpack_from("<I", data, start)[0]
    return result


def build_region_comparison(left: bytes, right: bytes, start: int = 0) -> dict[str, object]:
    runs = difference_runs(left, right, start=start)
    return {
        "changed_byte_count": sum(end - start for start, end in runs),
        "changed_run_count": len(runs),
        "runs": [
            {
                "start": start,
                "end": end,
                "size": end - start,
                "baseline_hex": left[start:end].hex(),
                "candidate_hex": right[start:end].hex(),
                "baseline_scalar": scalar_view(left, start, end),
                "candidate_scalar": scalar_view(right, start, end),
            }
            for start, end in runs
        ],
    }


def build_comparison(baseline: LoadedProfile, candidate: LoadedProfile) -> dict[str, object]:
    return {
        "baseline": baseline.metadata.path,
        "candidate": candidate.metadata.path,
        "decoded": build_region_comparison(baseline.data, candidate.data, start=4),
        "trailing": build_region_comparison(baseline.trailing, candidate.trailing),
    }


def consensus_region(groups: tuple[list[bytes], list[bytes]], start: int = 0) -> dict[str, object]:
    left, right = groups
    common_size = min(len(item) for item in left + right)
    left_consensus = bytearray(common_size)
    right_consensus = bytearray(common_size)
    stable = bytearray(common_size)
    for index in range(start, common_size):
        left_values = {item[index] for item in left}
        right_values = {item[index] for item in right}
        if len(left_values) == 1 and len(right_values) == 1 and left_values != right_values:
            left_consensus[index] = next(iter(left_values))
            right_consensus[index] = next(iter(right_values))
            stable[index] = 1

    runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for index in range(start, common_size + 1):
        is_stable = index < common_size and stable[index] != 0
        if is_stable and run_start is None:
            run_start = index
        elif not is_stable and run_start is not None:
            runs.append((run_start, index))
            run_start = None
    return {
        "stable_byte_count": sum(end - begin for begin, end in runs),
        "stable_run_count": len(runs),
        "runs": [
            {
                "start": begin,
                "end": end,
                "size": end - begin,
                "group_a_hex": left_consensus[begin:end].hex(),
                "group_b_hex": right_consensus[begin:end].hex(),
                "group_a_scalar": scalar_view(left_consensus, begin, end),
                "group_b_scalar": scalar_view(right_consensus, begin, end),
            }
            for begin, end in runs
        ],
    }


def build_consensus(profiles: list[LoadedProfile], split: int) -> dict[str, object]:
    left = profiles[:split]
    right = profiles[split:]
    return {
        "group_a": [item.metadata.path for item in left],
        "group_b": [item.metadata.path for item in right],
        "decoded": consensus_region(
            ([item.data for item in left], [item.data for item in right]), start=4
        ),
        "trailing": consensus_region(
            ([item.trailing for item in left], [item.trailing for item in right])
        ),
    }


def print_runs(label: str, region: dict[str, object], left_key: str, right_key: str) -> None:
    count_key = "changed_byte_count" if "changed_byte_count" in region else "stable_byte_count"
    runs_key = "changed_run_count" if "changed_run_count" in region else "stable_run_count"
    print(f"  {label}: {region[count_key]} bytes in {region[runs_key]} runs")
    for run in region["runs"]:
        print(
            f"    0x{run['start']:04X}..0x{run['end'] - 1:04X} ({run['size']}): "
            f"{run[left_key]} -> {run[right_key]}"
        )


def print_human(
    profiles: list[LoadedProfile],
    comparisons: list[dict[str, object]],
    consensus: dict[str, object] | None,
) -> None:
    for profile in profiles:
        item = profile.metadata
        print(f"PROFILE {Path(item.path).name}")
        print(
            f"  stored={item.stored_size} blob={item.blob_size} decoded=0x{item.profile_size:X} "
            f"compressed={item.compressed} version={item.format_version}"
        )
        print(
            f"  crc outer=0x{item.outer_crc32:08X} embedded=0x{item.embedded_crc32:08X} "
            f"calculated=0x{item.calculated_crc32:08X} valid={item.crc_valid} "
            f"trailing={item.trailing_size}"
        )

    for comparison in comparisons:
        print(
            f"\nCOMPARE {Path(str(comparison['baseline'])).name} -> "
            f"{Path(str(comparison['candidate'])).name}"
        )
        print_runs("decoded", comparison["decoded"], "baseline_hex", "candidate_hex")
        print_runs("trailing", comparison["trailing"], "baseline_hex", "candidate_hex")

    if consensus is not None:
        print("\nCONSENSUS group A -> group B")
        print_runs("decoded", consensus["decoded"], "group_a_hex", "group_b_hex")
        print_runs("trailing", consensus["trailing"], "group_a_hex", "group_b_hex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Publicprofile files or directories")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="limit displayed difference runs per comparison (0 means all)",
    )
    parser.add_argument(
        "--consensus-split",
        type=int,
        default=0,
        help="compare stable values in paths before this index against paths after it",
    )
    args = parser.parse_args()

    paths = expand_inputs(args.paths)
    if not paths:
        parser.error("no profile files found")

    profiles: list[LoadedProfile] = []
    for path in paths:
        try:
            profiles.append(load_profile(path))
        except (OSError, ProfileError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            return 1

    comparisons = [build_comparison(profiles[0], item) for item in profiles[1:]]
    consensus = None
    if args.consensus_split:
        if not 0 < args.consensus_split < len(profiles):
            parser.error("--consensus-split must divide the supplied profiles into two groups")
        consensus = build_consensus(profiles, args.consensus_split)
    if args.max_runs > 0:
        for comparison in comparisons:
            comparison["decoded"]["runs"] = comparison["decoded"]["runs"][: args.max_runs]
            comparison["trailing"]["runs"] = comparison["trailing"]["runs"][: args.max_runs]
        if consensus is not None:
            consensus["decoded"]["runs"] = consensus["decoded"]["runs"][: args.max_runs]
            consensus["trailing"]["runs"] = consensus["trailing"]["runs"][: args.max_runs]

    if args.json:
        print(
            json.dumps(
                {
                    "profiles": [asdict(item.metadata) for item in profiles],
                    "comparisons": comparisons,
                    "consensus": consensus,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print_human(profiles, comparisons, consensus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
