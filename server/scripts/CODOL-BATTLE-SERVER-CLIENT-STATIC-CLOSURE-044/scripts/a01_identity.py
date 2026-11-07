# -*- coding: utf-8 -*-
"""044 Phase A: sample identity, hashes, address convention, scope. READ-ONLY."""
import _common as c, os, json

out = []
def P(s=""): out.append(s)

P("# 044 Phase A raw output")
P("workspace = %s" % c.WS)
P("")
P("## full-file SHA-256 (recomputed from raw bytes)")
for tag, path in (("S-DLL", c.DLL), ("S-EXE", c.EXE), ("S-IMG", c.IMG)):
    h = c.sha256_file(path)
    P("%s | %s | %d bytes | sha256=%s" % (tag, path, os.path.getsize(path), h))
P("")

P("## recovered-image section table (byte map)")
for i, s in enumerate(c.IMG_SECS):
    present = min(s["rsize"], max(0, c.IMG_LEN - s["raw"]))
    cover = "FULL" if s["rsize"] >= s["vsize"] else "PARTIAL"
    P("  #%d %-8s VA=%08x VSize=%08x raw=%08x rsize=%08x present=%08x %s" % (
        i, s["name"], s["va"], s["vsize"], s["raw"], s["rsize"], present, cover))
P("  IMG file size = %08x ; SizeOfImage = %08x ; coverage = %.3f%%" % (
    c.IMG_LEN, c.pe_img.OPTIONAL_HEADER.SizeOfImage,
    100.0 * c.IMG_LEN / c.pe_img.OPTIONAL_HEADER.SizeOfImage))
P("")

P("## convention probes: VA == RVA + ImageBase(0x400000) ; file_off == RVA")
for name, va, off, expect in (
        ("gamestateupdate %d", 0x00DB4700, 0x009B4700, b"gamestateupdate %d"),
        ("connectResponse",    0x00DBFF0C, 0x009BFF0C, b"connectResponse"),
        ("CG_ServerCommand:",  0x00DC61AD, 0x009C61AD, b"CG_ServerCommand: "),
        ("; net-buffer NOT",   0x00D9EE98, 0x0099EE98, b"; net-buffer NOT enough")):
    got = c.icstr(off, 60) or b""
    P("  VA=%08x RVA=%08x expect=%r got=%r %s" % (va, off, expect, got[:30],
        "MATCH" if got.startswith(expect) else "FAIL"))
P("")

P("## target function entry bytes (this image)")
for name, rva in (("0x87A890", 0x87A890), ("0x87C110", 0x87C110),
                  ("0x87D5A0", 0x87D5A0), ("0x87ED70", 0x87ED70),
                  ("0x87EDB0", 0x87EDB0), ("0x87BE00", 0x87BE00)):
    b = c.iraw(rva, 8) or b""
    P("  %s bytes=%s in_file=%s" % (name, b.hex(), c.img_in_file(rva)))
P("")

P("## critical out-of-image addresses used by 043")
for name, rva in (("read-API slot A", 0xCA84E8), ("read-API slot B", 0xCA84E4),
                  ("last-error slot", 0xCA853C), ("dispatcher global", 0x76446B0),
                  ("TQOS global", 0x84ABB08), ("/GS cookie", 0xE3F240)):
    P("  %-18s RVA=%08x in_file=%s" % (name, rva, c.img_in_file(rva, 4)))
P("")

P("## E8 direct-call scan for the 4 target entries (sweep present .tp3 #1)")
TARGETS = {0x87A890: "0x87A890 len-writer", 0x87C110: "0x87C110 decoder#1",
           0x87D5A0: "0x87D5A0 decoder#2", 0x87ED70: "0x87ED70 core-get",
           0x87EDB0: "0x87EDB0 core-wcslen"}
sec1 = c.IMG_SECS[0]
A, B = sec1["raw"], sec1["raw"] + min(sec1["rsize"], c.IMG_LEN - sec1["raw"])
n_calls = {}
for t in TARGETS:
    n_calls[t] = []
# linear E8 scan: pattern E8 rel32 -> target = va_of_next + rel32
i = A
while i < B - 5:
    if c._bi[i] == 0xE8:
        rel = int.from_bytes(c._bi[i+1:i+5], "little", signed=True)
        src_va = c.IMG_IB + i
        dst = src_va + 5 + rel
        if dst - c.IMG_IB in TARGETS:
            n_calls[dst - c.IMG_IB].append(i)
        i += 5
    else:
        i += 1
for t, name in TARGETS.items():
    P("  %s sites=%s" % (name, ["0x%x" % x for x in n_calls[t]]))
P("")

P("## image_best.bin copies in workspace (identity trap)")
import hashlib
hits = []
for base, dirs, files in os.walk(c.WS):
    for fn in files:
        if fn.lower() == "image_best.bin":
            fp = os.path.join(base, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            hits.append((c.sha256_file(fp), sz, fp))
from collections import Counter
cnt = Counter(h[0] for h in hits)
P("  total copies = %d ; distinct builds = %d" % (len(hits), len(cnt)))
for h, n in cnt.most_common():
    first = next(x[2] for x in hits if x[0] == h)
    P("    %s x%d  first=%s" % (h[:16] + "...", n, first))
P("  >>> 044 uses ONLY: %s" % c.sha256_file(c.IMG))

c.w(os.path.join(c.EV, "a_identity_and_scope.txt"), "\n".join(out))
print("\n".join(out))