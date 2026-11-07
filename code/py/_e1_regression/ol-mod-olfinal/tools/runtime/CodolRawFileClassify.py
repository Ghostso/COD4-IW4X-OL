#!/usr/bin/env python3
"""Classify dumped CODOL RawFile payloads by content rather than filename."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


COMPILED_GSC_MAGIC = b"\x80GSC\r\n\x00"
KNOWN_MAGICS = (
    (COMPILED_GSC_MAGIC, "gsc-tool-compiled"),
    (b"IWCB000", "codol-const-baseline"),
    (b"GFX", "scaleform-gfx"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"DDS ", "dds"),
    (b"RIFF", "riff"),
    (b"OggS", "ogg"),
    (b"PK\x03\x04", "zip"),
    (b"\x1f\x8b", "gzip"),
    (b"BZh", "bzip2"),
    (b"7z\xbc\xaf\x27\x1c", "7zip"),
    (b"MZ", "pe"),
    (b"\x7fELF", "elf"),
)

GSC_FUNCTION_RE = re.compile(
    r"(?m)^\s*(?:[A-Za-z_]\w*::)?[A-Za-z_]\w*\s*\([^;{}\n]*\)\s*\{"
)
GSC_FEATURES = (
    ("include", re.compile(r"(?m)^\s*#include\s+[^\s;]+\s*;")),
    ("namespace_call", re.compile(r"[A-Za-z_][\w\\/]*::[A-Za-z_]\w*\s*\(")),
    ("level_or_self", re.compile(r"\b(?:level|self)\.")),
    ("thread", re.compile(r"\bthread\s+[A-Za-z_]\w*\s*\(")),
    ("notify", re.compile(r"\b(?:notify|endon|waittill)\s*\(")),
    ("gsc_block_comment", re.compile(r"/#|#/")),
)
ANIMATION_SCRIPT_FEATURES = (
    ("character_animation_banner", re.compile(r"Character\s+Animation\s+Script", re.I)),
    ("animations_section", re.compile(r"(?m)^\s*ANIMATIONS\s*$")),
    ("defines_section", re.compile(r"(?m)^\s*DEFINES\s*$")),
    ("state_declaration", re.compile(r"(?m)^\s*STATE\s+\w+", re.I)),
    ("animation_set", re.compile(r"(?m)^\s*set\s+\w+\s+\w+\s*=", re.I)),
)


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = collections.Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def ascii_printable_ratio(data: bytes) -> float:
    if not data:
        return 1.0
    printable = sum(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in data)
    return printable / len(data)


def decode_text(data: bytes) -> tuple[str | None, str | None, float | None]:
    encodings: tuple[str, ...]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    elif data.startswith(b"\xef\xbb\xbf"):
        encodings = ("utf-8-sig",)
    else:
        encodings = ("utf-8",)

    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not text:
            return text, encoding, 1.0
        printable = sum(character.isprintable() or character in "\t\r\n" for character in text)
        ratio = printable / len(text)
        if "\x00" not in text and ratio >= 0.85:
            return text, encoding, ratio
    return None, None, None


def identify_magic(data: bytes) -> str | None:
    for prefix, name in KNOWN_MAGICS:
        if data.startswith(prefix):
            return name
    if len(data) >= 2:
        header = (data[0] << 8) | data[1]
        if data[0] == 0x78 and header % 31 == 0:
            return "zlib"
    return None


def matched_features(text: str, features: tuple[tuple[str, re.Pattern[str]], ...]) -> list[str]:
    return [name for name, pattern in features if pattern.search(text)]


def classify_payload(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "size": len(data),
        "first_bytes_hex": data[:32].hex().upper(),
        "entropy": round(shannon_entropy(data), 6),
        "ascii_printable_ratio": round(ascii_printable_ratio(data), 6),
        "known_magic": identify_magic(data),
    }
    if not data:
        result.update(
            classification="empty",
            script_candidate_confidence="unlikely",
            classification_reasons=["zero_length"],
        )
        return result

    if data.startswith(COMPILED_GSC_MAGIC):
        result.update(
            classification="known_compiled_gsc_magic",
            script_candidate_confidence="high",
            classification_reasons=["gsc_tool_header"],
            compiled_gsc_version=data[len(COMPILED_GSC_MAGIC)] if len(data) > 7 else None,
        )
        return result

    text, encoding, unicode_ratio = decode_text(data)
    if text is not None:
        gsc_features = matched_features(text, GSC_FEATURES)
        animation_features = matched_features(text, ANIMATION_SCRIPT_FEATURES)
        function_definition = bool(GSC_FUNCTION_RE.search(text))
        result.update(
            text_encoding=encoding,
            unicode_printable_ratio=round(unicode_ratio or 0.0, 6),
            gsc_features=gsc_features,
            animation_script_features=animation_features,
        )
        if function_definition and gsc_features:
            result.update(
                classification="gsc_source",
                script_candidate_confidence="high",
                classification_reasons=["function_definition", *gsc_features],
            )
        elif len(animation_features) >= 2:
            result.update(
                classification="engine_script_text",
                script_candidate_confidence="high",
                classification_reasons=animation_features,
            )
        else:
            result.update(
                classification="other_text",
                script_candidate_confidence="possible",
                classification_reasons=["readable_text_without_known_script_grammar"],
            )
        return result

    magic = result["known_magic"]
    result.update(
        classification="binary",
        script_candidate_confidence="unlikely" if magic else "unknown",
        classification_reasons=[f"known_non_script_magic:{magic}" if magic else "unknown_binary_magic"],
    )
    return result


def classify_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = source.get("assets")
    if not isinstance(assets, list):
        raise ValueError("manifest does not contain an assets list")

    classified: list[dict[str, Any]] = []
    missing_payloads: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("output"), str):
            continue
        name = asset.get("name")
        relative = asset["output"]
        payload_path = (manifest_path.parent / relative).resolve()
        try:
            payload_path.relative_to(manifest_path.parent)
        except ValueError as error:
            raise ValueError(f"payload escapes manifest directory: {relative}") from error
        if not payload_path.is_file():
            missing_payloads.append(str(name or relative))
            continue
        data = payload_path.read_bytes()
        entry = {
            "name": name,
            "output": relative,
            "sha256": hashlib.sha256(data).hexdigest().upper(),
            **classify_payload(data),
        }
        expected_hash = asset.get("sha256")
        entry["manifest_hash_matches"] = not expected_hash or entry["sha256"] == expected_hash
        classified.append(entry)

    counts = collections.Counter(entry["classification"] for entry in classified)
    confidence_counts = collections.Counter(
        entry["script_candidate_confidence"] for entry in classified
    )
    return {
        "schema_version": 1,
        "classified_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_manifest": str(manifest_path),
        "asset_count": len(classified),
        "missing_payloads": missing_payloads,
        "classification_counts": dict(sorted(counts.items())),
        "script_candidate_confidence_counts": dict(sorted(confidence_counts.items())),
        "assets": classified,
        "limitations": [
            "Unknown binary magic does not prove that a payload is not a CODOL script.",
            "Text grammar detection is conservative and does not establish VM compatibility.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="RawFile dump directory or manifest.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = args.input / "manifest.json" if args.input.is_dir() else args.input
    report = classify_manifest(manifest)
    output = (args.output or manifest.with_name("classification.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)

    counts = report["classification_counts"]
    summary = ", ".join(f"{name}={count}" for name, count in counts.items())
    print(f"Classified RawFiles: {report['asset_count']}; {summary}")
    print(f"Saved report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
