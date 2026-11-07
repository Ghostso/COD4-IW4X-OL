# -*- coding: utf-8 -*-
"""Read-only CODOL 3.19 runtime WeaponDef probe.

This tool never attaches to a client and never guesses a final layout.  The
earlier OLFinal RVA block is absent from the 3.19 PE and reads as zero; the
zone-body offsets 0xBB4/0xBCC/0xBF0 were also disproven as final-layout
evidence (they hold animation/bounds data in 3.19 assets).  Therefore this
probe emits an explicit unsupported verdict unless a caller supplies a live,
3.19-derived table address through a future verified adapter.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REJECTED = {
    "olfinal_weapon_table_rva": "0x13F5A40",
    "olfinal_weapon_count_rva": "0x7417B88",
    "zone_body_candidate": ["0xBB4", "0xBCC", "0xBF0"],
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    image = a.image.read_bytes()
    # Verify that the rejected absolute table addresses really are zero in
    # this exact capture.  The capture uses VA - 0x400000 for its linear bytes.
    base = 0x400000
    checks = {}
    for label, va in (("olfinal_weapon_table", 0x17F5A40),
                      ("olfinal_weapon_count", 0x7817B88),
                      ("olfinal_attachment_count", 0x17F5A3C)):
        off = va - base
        checks[label] = {
            "va": f"0x{va:X}",
            "bytes": image[off:off + 16].hex() if 0 <= off < len(image) else None,
            "state": "all-zero" if 0 <= off and off + 16 <= len(image)
                     and image[off:off + 16] == b"\0" * 16 else "not-zero",
        }
    verdict = "runtime-layout-unverified"
    out = {
        "image": str(a.image),
        "image_sha256": sha256(a.image),
        "runtime_layout_verdict": verdict,
        "rejected_evidence": REJECTED,
        "address_checks": checks,
        "reason": ("No 3.19-derived final WeaponDef pointer table is present in "
                   "this capture; emitting zero weapon rows is intentional."),
        "weapons": [],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("verdict", verdict, "checks", {k: v["state"] for k, v in checks.items()})
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
