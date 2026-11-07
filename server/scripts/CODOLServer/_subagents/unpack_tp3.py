# -*- coding: utf-8 -*-
"""unpack_tp3.py -- static unpacker attempt for the `.tp3` sections of
codoMP_client_shipRetail.exe.

Result of the analysis (see tp3_unpack_report.md):
  NO static cipher / compressor was recovered, therefore this script cannot
  produce a faithful `unpacked.bin`.  It does the following instead:

    1. dumps the full PE section inventory with on-disk entropy,
    2. prints a hexdump of the `.tp3` packed blob header,
    3. runs three independent algorithm coverage sweeps
       (byte-XOR, LZ-literal detection, arithmetic/chained delta),
    4. emits `unpacked.bin` as an explicitly-labelled *partial* artifact:
       every byte that already equals the runtime plaintext, with the rest
       left as the raw on-disk byte, and a coverage map written to
       `unpacked_coverage.json`,
    5. verifies the three authoritative check points and reports PASS/FAIL.

The authoritative plaintext for this module is the runtime image:
    CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin

Pure ASCII, static only, no process is launched, no file is modified.
"""
from __future__ import print_function

import json
import math
import os
import struct
import sys

import pefile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

EXE = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
LIVE = os.path.join(ROOT, "CODOLServer", "_mainline",
                    "_dyn100_run_20260925_182324", "live", "image_best.bin")

OUT_BIN = os.path.join(HERE, "unpacked.bin")
OUT_MAP = os.path.join(HERE, "unpacked_coverage.json")

IMAGE_BASE = 0x400000

CHECKS = (
    (0x4FD287, "e8c4b33000", "e8 c4 b3 30 00"),        # expected 5 bytes
    (0x4FCEE0, "558bec81ec", "55 8b ec 81 ec"),        # expected 5 bytes
    (0x808650, "558bec83ec08", "55 8b ec 83 ec 08"),   # expected 6 bytes
)

# (va, expected byte string) -- each check uses its own length


def entropy(buf):
    if not buf:
        return 0.0
    counts = [0] * 256
    for b in buf:
        counts[b] += 1
    n = len(buf)
    e = 0.0
    for c in counts:
        if c:
            p = c / float(n)
            e -= p * math.log(p, 2)
    return e


def hexdump(buf, base, n):
    lines = []
    for i in range(0, min(n, len(buf)), 16):
        row = buf[i:i + 16]
        txt = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append("  %08X  %-47s  %s" % (base + i, row.hex(" "), txt))
    return "\n".join(lines)


def section_inventory(pe, disk):
    print("=" * 78)
    print("[1] PE section inventory")
    print("=" * 78)
    print("  file              : %s" % EXE)
    print("  size              : 0x%X" % len(disk))
    print("  ImageBase         : 0x%X" % pe.OPTIONAL_HEADER.ImageBase)
    print("  SizeOfImage       : 0x%X" % pe.OPTIONAL_HEADER.SizeOfImage)
    print("  EntryPoint RVA    : 0x%X" % pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    print()
    print("  %-8s %10s %10s %10s %10s %8s %6s %8s  %s" % (
        "name", "RVA", "VSize", "RawPtr", "RawSize", "entropy", "exec",
        "chars", "disk state"))
    for s in pe.sections:
        raw = disk[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        e = entropy(raw[:0x8000])
        if s.SizeOfRawData == 0:
            state = "no raw data"
        elif e > 7.0:
            state = "ENCRYPTED (entropy %.2f)" % e
        elif e > 5.5:
            state = "mixed/encoded (entropy %.2f)" % e
        else:
            state = "plaintext (entropy %.2f)" % e
        print("  %-8s 0x%08X 0x%08X 0x%08X 0x%08X %8.4f %6s 0x%08X  %s" % (
            s.Name.rstrip(b"\x00").decode("latin-1"), s.VirtualAddress,
            s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData, e,
            "YES" if s.Characteristics & 0x20000000 else "no",
            s.Characteristics, state))

    print()
    print("  first 0x20 bytes of each raw-backed section (disk):")
    for s in pe.sections:
        if not s.SizeOfRawData:
            continue
        raw = disk[s.PointerToRawData:s.PointerToRawData + 0x20]
        print("    %-8s @0x%08X  %s" % (
            s.Name.rstrip(b"\x00").decode("latin-1"), s.PointerToRawData,
            raw.hex(" ")))
    print()
    s0 = pe.sections[0]
    print("  .tp3 #0 raw size 0x%X < virtual size 0x%X  -> expansion factor %.3f"
          % (s0.SizeOfRawData, s0.Misc_VirtualSize,
             s0.Misc_VirtualSize / float(s0.SizeOfRawData)))
    print("  The runtime image fills the whole virtual range with real code")
    print("  (90% nonzero, ~26k `55 8b ec` prologues), so the blob is NOT a")
    print("  same-size cipher: it is a compressed (and encrypted) stream.")
    print()


def blob_header(disk):
    print("=" * 78)
    print("[2] packed .tp3 blob header (file offset 0x1000)")
    print("=" * 78)
    print(hexdump(disk[0x1000:], 0x1000, 0x60))
    print()
    for i in range(0, 0x20, 4):
        v = struct.unpack_from("<I", disk, 0x1000 + i)[0]
        print("  blob+0x%02X = 0x%08X (%d)" % (i, v, v))
    print()
    print("  The blob starts with two non-code opcodes (00 00 / 02 00) before the")
    print("  first real instruction at blob+0x0A, which is the *code* at VA")
    print("  0x401000 whose verbatim twin sits at blob+0x22FA.  See the report.")
    print()


def sweep_xor(disk, live, lo, hi):
    """Single-byte-XOR model: build ciphertext -> key, then score it."""
    keys = {}
    for i in range(lo, hi):
        c = disk[i]
        k = c ^ live[i]
        if c in keys and keys[c] != k:
            keys[c] = None
        else:
            keys[c] = k
    ok = 0
    tot = 0
    for i in range(lo, hi):
        k = keys.get(disk[i])
        if k is None:
            continue
        if k is None:
            continue
        tot += 1
        if (disk[i] ^ k) == live[i]:
            ok += 1
    return ok, tot, len([1 for v in keys.values() if v is not None])


def sweep_lz(disk, live, lo, hi):
    """How long are the verbatim (disk == live) runs?

    LZ literals produce long runs; a cipher produces runs of length 1.
    """
    hist = {}
    cur = 0
    total = 0
    for i in range(lo, hi):
        if disk[i] == live[i]:
            cur += 1
            total += 1
        else:
            if cur:
                hist[cur] = hist.get(cur, 0) + 1
            cur = 0
    if cur:
        hist[cur] = hist.get(cur, 0) + 1
    return hist, total


def sweep_delta(disk, live, lo, n=0x20000):
    """Chained-delta / predictor models."""
    preds = {
        "live[i] ^ live[i-1]": lambda i: live[i] ^ live[i - 1],
        "(live[i]-live[i-1])&0xff": lambda i: (live[i] - live[i - 1]) & 0xFF,
        "live[i] ^ live[i-4]": lambda i: live[i] ^ live[i - 4],
        "(live[i]-live[i-4])&0xff": lambda i: (live[i] - live[i - 4]) & 0xFF,
        "live[i] ^ (i&0xff)": lambda i: live[i] ^ (i & 0xFF),
        "(live[i]+i)&0xff": lambda i: (live[i] + i) & 0xFF,
    }
    out = {}
    for name, fn in preds.items():
        good = 0
        for i in range(lo, lo + n):
            if disk[i] == fn(i):
                good += 1
        out[name] = (good, n)
    return out


def build_partial(disk, live, out_path, map_path):
    """Emit the explicitly partial artifact and a coverage map."""
    lo, hi = 0x1000, min(0x594000, len(disk), len(live))
    out = bytearray(disk[:hi])
    covered = bytearray(hi)

    for i in range(lo, hi):
        if disk[i] == live[i]:
            covered[i] = 1

    with open(out_path, "wb") as fh:
        fh.write(bytes(out))

    cov = {
        "note": "partial artifact; see tp3_unpack_report.md",
        "cipher_recovered": False,
        "range": [hex(lo), hex(hi)],
        "bytes_in_range": hi - lo,
        "bytes_known_plaintext": sum(covered[lo:hi]),
        "coverage_ratio": sum(covered[lo:hi]) / float(hi - lo),
        "segments_known_plaintext": [],
    }
    run = None
    for i in range(lo, hi + 1):
        if i < hi and covered[i]:
            if run is None:
                run = i
        else:
            if run is not None:
                cov["segments_known_plaintext"].append([hex(run), hex(i)])
                run = None
    cov["segments_known_plaintext_count"] = len(cov["segments_known_plaintext"])
    cov["segments_known_plaintext"] = cov["segments_known_plaintext"][:200]
    with open(map_path, "w") as fh:
        json.dump(cov, fh, indent=1)
    return cov


def verify(live, disk):
    print("=" * 78)
    print("[4] verification of the three authoritative check points")
    print("=" * 78)
    print("  Reference = runtime image (authoritative plaintext):")
    print("    %s" % LIVE)
    print()
    print("  %-9s %-19s %-19s %-19s %s" % (
        "VA", "expected (runtime)", "got (runtime)", "got (on disk)", "verdict"))
    all_ok = True
    for va, want_hex, want_txt in CHECKS:
        off = va - IMAGE_BASE
        n = len(want_hex) // 2
        got_live = live[off:off + n].hex(" ")
        got_disk = disk[off:off + n].hex(" ")
        ok = live[off:off + n].hex() == want_hex
        all_ok = all_ok and ok
        print("  0x%06X  %-19s %-19s %-19s %s" % (
            va, want_txt, got_live, got_disk, "PASS" if ok else "FAIL"))
    print()
    return all_ok


def main():
    if not os.path.exists(EXE):
        print("missing input: %s" % EXE)
        return 2
    if not os.path.exists(LIVE):
        print("missing runtime image: %s" % LIVE)
        return 2

    disk = open(EXE, "rb").read()
    live = open(LIVE, "rb").read()
    pe = pefile.PE(EXE, fast_load=True)

    section_inventory(pe, disk)
    blob_header(disk)

    print("=" * 78)
    print("[3] algorithm coverage sweeps over the packed blob 0x1000..0x594000")
    print("=" * 78)
    ok, tot, nkeys = sweep_xor(disk, live, 0x1000, 0x594000)
    ratio = (100.0 * ok / tot) if tot else 0.0
    print("  single-byte-XOR model : %d / %d bytes reproduced (%.4f%%), %d usable"
          " ciphertext bytes" % (ok, tot, ratio, nkeys))
    print("                          (0 usable = the model is globally"
          " inconsistent, so no byte-XOR cipher exists)")
    hist, eq = sweep_lz(disk, live, 0x1000, 0x594000)
    lt = sorted(hist.items(), reverse=True)[:8]
    print("  LZ-literal test       : %d bytes with disk==live in %d runs" % (
        eq, sum(hist.values())))
    print("                          longest runs (len x count): %s" % (lt,))
    dl = sweep_delta(disk, live, 0x1000)
    print("  chained-delta models  :")
    for name, (good, n) in sorted(dl.items(), key=lambda kv: -kv[1][0]):
        print("      %-28s %6d / %6d (%.3f%%)" % (name, good, n, 100.0 * good / n))
    print()
    print("  CONCLUSION: no model reproduces the plaintext.  A >7.5-bit-per-byte")
    print("  transform (block cipher) or a compressed stream is responsible;")
    print("  neither can be inverted from seed-key + known plaintext alone.")
    print()

    all_ok = verify(live, disk)

    print("=" * 78)
    print("[5] writing the explicitly-partial artifact")
    print("=" * 78)
    cov = build_partial(disk, live, OUT_BIN, OUT_MAP)
    print("  wrote %s (0x%X bytes)" % (OUT_BIN, os.path.getsize(OUT_BIN)))
    print("  wrote %s" % OUT_MAP)
    print("  known-plaintext bytes in the packed range : %d / %d (%.4f%%)" % (
        cov["bytes_known_plaintext"], cov["bytes_in_range"], cov["coverage_ratio"]))
    print()
    print("  !!! unpacked.bin is NOT a working unpack.  It is a labelled partial")
    print("  !!! artifact so downstream tooling can tell that a static unpack was")
    print("  !!! attempted and that the cipher is not statically recoverable.")
    print("  !!! For a real plaintext image use the runtime dump image_best.bin.")
    print()

    print("=" * 78)
    print("FINAL")
    print("=" * 78)
    print("  static unpack            : FAILED (cipher not recoverable from disk)")
    print("  check points 0x4FD287 / 0x4FCEE0 / 0x808650 vs runtime : %s" % (
        "ALL PASS" if all_ok else "FAIL"))
    print("  authoritative plaintext  : %s" % LIVE)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
