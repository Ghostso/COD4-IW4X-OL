# -*- coding: utf-8 -*-
"""Characterise what the runtime image dump actually contains.

Mapping: module preferred base 0x00400000, dump base VA 0x00994000
         => dump offset D corresponds to RVA 0x594000 + D
"""
import math
import os

RUNS = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
DUMP = os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_best.bin")
REFS = [
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_t002.90s.bin"),
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_114204\engine\engine_t015.70s.bin"),
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_112143\engine\engine_t002.26s.bin"),
    os.path.join(RUNS, r"ENGINE_DUMP_20260925_112143\engine\engine_t017.43s.bin"),
]
RVA_BASE = 0x594000


def entropy(buf):
    counts = [0] * 256
    for b in buf:
        counts[b] += 1
    n = len(buf)
    e = 0.0
    for c in counts:
        if c:
            p = c / n
            e -= p * math.log2(p)
    return e


with open(DUMP, "rb") as fh:
    best = fh.read()
print("dump", os.path.basename(DUMP), "size 0x%X" % len(best))

others = []
for p in REFS:
    if os.path.exists(p):
        with open(p, "rb") as fh:
            others.append((os.path.basename(p), fh.read()))

print("")
print("changed-byte count vs later samples (stability):")
for name, blob in others:
    if len(blob) != len(best):
        print("  %s length mismatch" % name)
        continue
    diff = sum(1 for a, b in zip(best, blob) if a != b)
    print("  %-24s differing bytes %d" % (name, diff))

print("")
print("per-64KB region profile of the best dump:")
zeros_spans = []
cur = None
for off in range(0, len(best), 0x10000):
    chunk = best[off:off + 0x10000]
    nz = sum(1 for b in chunk if b)
    e = entropy(chunk) if nz else 0.0
    flag = ""
    if nz == 0:
        flag = "ALLZERO"
        if cur is None:
            cur = off
    else:
        if cur is not None:
            zeros_spans.append((cur, off))
            cur = None
    print("  off 0x%08X  rva 0x%08X  nonzero %8d  entropy %6.3f  %s" % (
        off, RVA_BASE + off, nz, e, flag))
if cur is not None:
    zeros_spans.append((cur, len(best)))
print("")
print("all-zero spans in dump offset:")
for a, b in zeros_spans:
    print("  0x%08X..0x%08X  (rva 0x%08X..0x%08X)" % (a, b, RVA_BASE + a, RVA_BASE + b))
