"""Audit an IIPS nifs container against an existing zone directory.

This is a read-only verifier.  It never extracts files, changes the source
container, or changes the target directory.

Usage:
  python -X utf8 CODOLServer/_mainline/ifs_zone_audit.py \
      <container.ifs> <zone_dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


FF_MAGIC = (b"IWff0100", b"IWffu100")
HEADER_SIZE = 0xAC
EXPECTED_META = 0x1CD
NAME_RE = re.compile(rb"client_shipRetail/chinese/([A-Za-z0-9_]+\.ff)")
# Some containers leave one non-name header byte immediately before the list
# name (for example, ``8ff_init_common_marketplace.lst``).  The list token
# itself is still the ordinary ``ff_*.lst`` name.
LIST_RE = re.compile(rb"(ff_[A-Za-z0-9_]+\.lst)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_container(path: Path) -> dict:
    blob = path.read_bytes()
    if blob[:4] != b"nifs":
        raise ValueError("not an nifs container: %r" % (blob[:4],))
    header_len = struct.unpack_from("<I", blob, 4)[0]
    if header_len < HEADER_SIZE or header_len > len(blob):
        raise ValueError("invalid header length: 0x%x" % header_len)

    header = blob[: max(0x3000, header_len)]
    listed = [x.decode("ascii") for x in NAME_RE.findall(header)]
    list_names = [x.decode("ascii") for x in LIST_RE.findall(header)]

    starts = []
    for magic in FF_MAGIC:
        starts.extend(m.start() for m in re.finditer(re.escape(magic), blob))
    starts = sorted(set(starts))
    zones = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(blob)
        magic = blob[start:start + 8]
        meta = None
        if start + 12 <= len(blob):
            meta = struct.unpack_from("<I", blob, start + 8)[0]
        zones.append({
            "index": index,
            "name": listed[index] if index < len(listed) else None,
            "start": start,
            "end": end,
            "size": end - start,
            "magic": magic.decode("ascii", "replace"),
            "metadata": meta,
            "metadata_ok": meta == EXPECTED_META,
            "sha256": sha256_bytes(blob[start:end]),
        })

    return {
        "container": str(path),
        "size": len(blob),
        "header_len": header_len,
        "list_names": list_names,
        "listed_zones": listed,
        "zone_count": len(zones),
        "zones": zones,
    }


def compare_zones(report: dict, zone_dir: Path) -> None:
    report["zone_dir"] = str(zone_dir)
    report["zone_dir_exists"] = zone_dir.is_dir()
    results = []
    for zone in report["zones"]:
        name = zone["name"] or ("blob%d.ff" % zone["index"])
        target = zone_dir / name
        item = {
            "name": name,
            "path": str(target),
            "exists": target.is_file(),
            "container_size": zone["size"],
            "container_sha256": zone["sha256"],
        }
        if target.is_file():
            item["target_size"] = target.stat().st_size
            item["target_sha256"] = sha256_file(target)
            item["exact_match"] = (
                item["target_size"] == zone["size"]
                and item["target_sha256"] == zone["sha256"]
            )
        else:
            item["target_size"] = None
            item["target_sha256"] = None
            item["exact_match"] = False
        results.append(item)
    report["target_zones"] = results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("container", type=Path)
    parser.add_argument("zone_dir", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    report = parse_container(args.container)
    compare_zones(report, args.zone_dir)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0

    print("container: %s" % report["container"])
    print("size: %d  header_len: 0x%x" %
          (report["size"], report["header_len"]))
    print("list: %s" % (", ".join(report["list_names"]) or "<none>"))
    print("zones: %d" % report["zone_count"])
    for zone, target in zip(report["zones"], report["target_zones"]):
        print("  [%d] %s  size=%d  meta=0x%x (%s)" % (
            zone["index"], zone["name"] or "<unnamed>", zone["size"],
            zone["metadata"] if zone["metadata"] is not None else 0,
            "ok" if zone["metadata_ok"] else "bad"))
        print("       target=%s exists=%s exact=%s" % (
            target["path"], target["exists"], target["exact_match"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
