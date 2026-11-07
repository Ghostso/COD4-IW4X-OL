#!/usr/bin/env python3
"""Shared persistence and validation for CODOL runtime capture artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from CodolInputScenario import normalize_scenario


RAW_SAMPLE_FORMAT = "codol-client-input-raw-samples"
RAW_SAMPLE_SCHEMA_VERSION = 2
OPAQUE_DATA_KEY = "_opaque_data"


def _replace_with_retry(temporary: Path, output: Path) -> None:
    for attempt in range(20):
        try:
            temporary.replace(output)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    _replace_with_retry(temporary, path)


def is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def opaque_sample_details(sample: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    opaque_data = sample.get(OPAQUE_DATA_KEY)
    evidence = sample.get("opaque_evidence")
    has_evidence = opaque_data is not None or evidence is not None
    data_size: int | None = 0

    if opaque_data is not None:
        if not isinstance(opaque_data, (bytes, bytearray, memoryview)):
            errors.append("opaque data is not bytes")
            data_size = None
        else:
            data_size = len(opaque_data)
        if evidence is not None:
            errors.append("sample contains live and persisted opaque evidence")
    elif evidence is not None:
        if not isinstance(evidence, dict):
            errors.append("opaque evidence descriptor is not an object")
            data_size = None
        else:
            evidence_size = evidence.get("size")
            if not is_plain_int(evidence_size) or evidence_size < 0:
                errors.append("opaque evidence size is invalid")
                data_size = None
            else:
                data_size = evidence_size
    if not has_evidence:
        errors.append("opaque evidence is missing")
    elif data_size == 0:
        errors.append("opaque evidence is empty")

    segments_value = sample.get("opaque_evidence_segments", [])
    if segments_value is None:
        segments: list[Any] = []
    elif not isinstance(segments_value, list):
        errors.append("opaque evidence segments are not an array")
        segments = []
    else:
        segments = segments_value
    if not segments:
        errors.append("opaque evidence segments are empty")

    expected_offset = 0
    latest_envelope: dict[str, Any] | None = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            errors.append(f"segment {index} is not an object")
            continue
        kind = segment.get("kind")
        offset = segment.get("offset")
        size = segment.get("size")
        if not isinstance(kind, str) or not kind:
            errors.append(f"segment {index} kind is invalid")
        if not is_plain_int(offset) or offset != expected_offset:
            errors.append(f"segment {index} offset is not contiguous")
        if not is_plain_int(size) or size < 0:
            errors.append(f"segment {index} size is invalid")
            continue
        if is_plain_int(offset) and offset == expected_offset:
            expected_offset += size
        schema_version = segment.get("schema_version")
        if schema_version is not None and (
            not is_plain_int(schema_version) or schema_version <= 0
        ):
            errors.append(f"segment {index} schema version is invalid")
        if kind == "server-world-player-sample-v1":
            latest_envelope = {
                "kind": kind,
                "struct_size": size,
                "schema_version": schema_version,
            }

    if data_size is not None and expected_offset != data_size:
        errors.append(
            f"segment bytes {expected_offset} do not match opaque bytes {data_size}"
        )

    return {
        "has_evidence": has_evidence,
        "data_size": data_size,
        "segment_count": len(segments),
        "latest_envelope": latest_envelope,
        "errors": errors,
    }


def capture_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    sequences: list[int] = []
    sequence_mismatch_count = 0
    opaque_sample_count = 0
    opaque_byte_count = 0
    opaque_segment_count = 0
    framing_errors: list[str] = []
    latest_envelope: dict[str, Any] | None = None
    latest_parser: dict[str, Any] | None = None
    projected_origins: dict[str, list[list[float]]] = {
        "server": [], "predicted": [], "snapshot": []
    }

    for index, sample in enumerate(samples):
        sequence = sample.get("sequence")
        if is_plain_int(sequence):
            sequences.append(sequence)
            if sequence != index:
                sequence_mismatch_count += 1
        else:
            sequence_mismatch_count += 1

        details = opaque_sample_details(sample)
        if details["has_evidence"]:
            opaque_sample_count += 1
        data_size = details["data_size"]
        if isinstance(data_size, int):
            opaque_byte_count += data_size
        opaque_segment_count += int(details["segment_count"])
        framing_errors.extend(
            f"sample {index}: {error}" for error in details["errors"]
        )

        envelope = details["latest_envelope"]
        if isinstance(envelope, dict):
            latest_envelope = {
                "sample_sequence": sequence if is_plain_int(sequence) else None,
                **envelope,
            }
        parser_summary = sample.get("parser_summary")
        if isinstance(parser_summary, dict):
            latest_parser = parser_summary
        projection = sample.get("state_projection")
        if isinstance(projection, dict):
            for owner in projected_origins:
                state = projection.get(owner)
                origin = state.get("origin") if isinstance(state, dict) else None
                if (
                    isinstance(origin, list) and len(origin) == 3
                    and all(isinstance(value, (int, float)) for value in origin)
                ):
                    projected_origins[owner].append(
                        [float(value) for value in origin]
                    )

    sequence_contiguous = (
        bool(samples)
        and len(sequences) == len(samples)
        and sequence_mismatch_count == 0
    )
    origin_spans = {}
    for owner, origins in projected_origins.items():
        if origins:
            origin_spans[owner] = [
                max(origin[axis] for origin in origins)
                - min(origin[axis] for origin in origins)
                for axis in range(3)
            ]
        else:
            origin_spans[owner] = None

    return {
        "sample_count": len(samples),
        "sequence_observed_count": len(sequences),
        "sequence_first": sequences[0] if sequences else None,
        "sequence_last": sequences[-1] if sequences else None,
        "sequence_contiguous": sequence_contiguous,
        "sequence_mismatch_count": sequence_mismatch_count,
        "opaque_evidence_count": opaque_sample_count,
        "opaque_evidence_bytes": opaque_byte_count,
        "opaque_segment_count": opaque_segment_count,
        "segment_framing_valid": not framing_errors,
        "segment_framing_error_count": len(framing_errors),
        "segment_framing_errors": framing_errors,
        "latest_envelope": latest_envelope,
        "latest_parser_summary": latest_parser,
        "origin_spans": origin_spans,
        "latest_state_projection": next(
            (
                sample.get("state_projection")
                for sample in reversed(samples)
                if isinstance(sample.get("state_projection"), dict)
            ),
            None,
        ),
    }


def load_raw_sample_checkpoint(path: Path) -> dict[str, Any]:
    header: dict[str, Any] | None = None
    samples: list[dict[str, Any]] = []
    incomplete_tail_ignored = False
    missing_final_newline = False
    with path.open("rb") as stream:
        line_number = 0
        while True:
            raw_line = stream.readline()
            if not raw_line:
                break
            line_number += 1
            framed = raw_line.endswith(b"\n")
            try:
                record = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                if not framed:
                    incomplete_tail_ignored = True
                    break
                raise ValueError(
                    f"raw sample checkpoint has an invalid record at line {line_number}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(
                    f"raw sample checkpoint record {line_number} must be an object"
                )
            if line_number == 1:
                if (
                    record.get("record") != "header"
                    or record.get("format") != RAW_SAMPLE_FORMAT
                    or record.get("schema_version") not in {
                        1,
                        RAW_SAMPLE_SCHEMA_VERSION,
                    }
                ):
                    raise ValueError("raw sample checkpoint header is invalid")
                scenario = normalize_scenario(record.get("scenario"))
                header = {**record, "scenario": scenario}
                if not framed:
                    missing_final_newline = True
                    break
                continue
            if record.get("record") != "sample":
                raise ValueError(
                    f"raw sample checkpoint record {line_number} is not a sample"
                )
            if record.get("index") != len(samples):
                raise ValueError(
                    f"raw sample checkpoint index is not contiguous at line {line_number}"
                )
            sample = record.get("sample")
            if not isinstance(sample, dict):
                raise ValueError(
                    f"raw sample checkpoint sample {len(samples)} must be an object"
                )
            samples.append(sample)
            if not framed:
                missing_final_newline = True
                break
    if header is None:
        raise ValueError("raw sample checkpoint is missing its header")
    schema_version = int(header["schema_version"])
    opaque_evidence_count = 0
    opaque_evidence_bytes = 0
    orphan_blob_bytes = 0
    blob_path: Path | None = None
    if schema_version >= 2:
        blob_file = header.get("blob_file")
        if (
            not isinstance(blob_file, str)
            or not blob_file
            or Path(blob_file).name != blob_file
        ):
            raise ValueError("raw sample checkpoint blob_file is invalid")
        blob_path = path.parent / blob_file
        try:
            blob = blob_path.read_bytes()
        except OSError as error:
            raise ValueError(f"could not read raw sample blob {blob_path}: {error}") from error
        expected_offset = 0
        for index, sample in enumerate(samples):
            evidence = sample.get("opaque_evidence")
            if evidence is None:
                continue
            if not isinstance(evidence, dict):
                raise ValueError(f"raw sample {index} opaque evidence is invalid")
            offset = evidence.get("offset")
            size = evidence.get("size")
            digest = evidence.get("sha256")
            if (
                not is_plain_int(offset)
                or offset != expected_offset
                or not is_plain_int(size)
                or size < 0
                or not isinstance(digest, str)
                or len(digest) != 64
                or offset + size > len(blob)
            ):
                raise ValueError(f"raw sample {index} opaque evidence framing is invalid")
            if hashlib.sha256(blob[offset : offset + size]).hexdigest() != digest:
                raise ValueError(f"raw sample {index} opaque evidence hash is invalid")
            expected_offset += size
            opaque_evidence_count += 1
            opaque_evidence_bytes += size
        orphan_blob_bytes = len(blob) - expected_offset
    return {
        "path": str(path.resolve()),
        "format": RAW_SAMPLE_FORMAT,
        "schema_version": schema_version,
        "scenario": header["scenario"],
        "samples": samples,
        "recovered_sample_count": len(samples),
        "incomplete_tail_ignored": incomplete_tail_ignored,
        "missing_final_newline": missing_final_newline,
        "blob_path": None if blob_path is None else str(blob_path.resolve()),
        "opaque_evidence_count": opaque_evidence_count,
        "opaque_evidence_bytes": opaque_evidence_bytes,
        "orphan_blob_bytes": orphan_blob_bytes,
    }


def summarize_raw_sample_checkpoint(path: Path) -> dict[str, Any]:
    recovered = load_raw_sample_checkpoint(path)
    summary = capture_summary(recovered["samples"])
    journal_complete = not recovered["incomplete_tail_ignored"] and not recovered[
        "missing_final_newline"
    ]
    has_blob = recovered["schema_version"] >= 2
    blob_complete = recovered["orphan_blob_bytes"] == 0 if has_blob else None
    integrity_complete = (
        journal_complete
        and blob_complete is not False
        and summary["sequence_contiguous"]
        and summary["segment_framing_valid"]
    )
    return {
        "mode": "offline-raw-summary",
        "recovery_ok": True,
        "integrity_complete": integrity_complete,
        "scenario": recovered["scenario"],
        "raw_samples": {
            "path": recovered["path"],
            "format": recovered["format"],
            "schema_version": recovered["schema_version"],
            "recovered_sample_count": recovered["recovered_sample_count"],
            "incomplete_tail_ignored": recovered["incomplete_tail_ignored"],
            "missing_final_newline": recovered["missing_final_newline"],
            "journal_complete": journal_complete,
            "blob_path": recovered["blob_path"],
            "opaque_evidence_count": recovered["opaque_evidence_count"],
            "opaque_evidence_bytes": recovered["opaque_evidence_bytes"],
            "orphan_blob_bytes": recovered["orphan_blob_bytes"],
            "hashes_valid": True if has_blob else None,
            "blob_complete": blob_complete,
        },
        "capture_summary": summary,
    }
