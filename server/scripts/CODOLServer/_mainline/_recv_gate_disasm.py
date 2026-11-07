"""Disassemble the /auth/ response-reception gate from the good runtime image.

Image: _dyn100_run_20260925_182324\\live\\image_best.bin (VA = off + 0x400000)

Questions answered:
  1. What does 0xAC9100 do (called right before BD state -> 2 at 0xC761AF)?
  2. Full context of the 0xC76184 caller block (what leads to state=2).
  3. The three unexamined vtable slots 0xB99350 / 0xB99610 / 0xB994B0.
  4. Every write to [reg+0x464] in the image (who sets the HTTP status field).
  5. X-TransactionID string VA and every code xref to it (request builder only,
     or also response parser?).

Read-only. ASCII output files only.
"""
import os
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG = os.path.join(
    ROOT, "CODOLServer", "_mainline", "_dyn100_run_20260925_182324",
    "live", "image_best.bin")
OUT = os.path.join(ROOT, "CODOLServer", "_mainline", "_recv_gate")
BASE = 0x400000

md = Cs(CS_ARCH_X86, CS_MODE_32)


def get_bytes(img, va, n):
    o = va - BASE
    if o < 0 or o + n > len(img):
        return None
    return img[o:o + n]


def disasm(img, va, va_end, max_lines=2000):
    lines = []
    cur = va
    while cur < va_end and len(lines) < max_lines:
        b = get_bytes(img, cur, 16)
        if b is None:
            break
        if b == b"\x00" * 16:
            lines.append("00%06X  <zeros>" % cur)
            break
        ins = next(md.disasm_lite(b, cur, count=1), None)
        if ins is None:
            lines.append("00%06X  db 0x%02x" % (cur, b[0]))
            cur += 1
            continue
        addr, size, mnem, op = ins
        raw = b[:size].hex(" ")
        lines.append(("00%06X  %-24s %s %s" % (addr, raw, mnem, op)).rstrip())
        cur += size
    return lines


def write_report(name, lines):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")
    return path


def scan_reg_disp_store(img, disp):
    """mov [reg32+disp32], reg / mov dword [reg32+disp32], imm32  hits."""
    hits = []
    d = struct.pack("<I", disp)
    i = 0
    n = len(img)
    while True:
        i = img.find(d, i, n)
        if i < 0:
            break
        if i >= 2:
            op = img[i - 2]
            modrm = img[i - 1]
            reg = (modrm >> 3) & 7
            mod = (modrm >> 6) & 3
            if op == 0x89 and mod == 2:
                hits.append((BASE + i - 2,
                             "mov [r32+0x%X], reg" % disp))
            elif op == 0xC7 and mod == 2 and reg == 0:
                imm = img[i + 4:i + 8]
                iv = struct.unpack("<I", imm)[0] if len(imm) == 4 else -1
                hits.append((BASE + i - 2,
                             "mov dword [r32+0x%X], 0x%X" % (disp, iv)))
        i += 1
    return hits


def scan_imm32_refs(img, target_va):
    t = struct.pack("<I", target_va)
    hits = []
    i = 0
    n = len(img)
    while True:
        i = img.find(t, i, n)
        if i < 0:
            break
        hits.append(BASE + i)
        i += 1
    return hits



def main():
    os.makedirs(OUT, exist_ok=True)
    img = open(IMG, "rb").read()
    summary = []

    for name, va, size in (("ac9100.txt", 0xAC9100, 0x900),
                           ("ac93b0.txt", 0xAC93B0, 0x400),
                           ("ac95f0.txt", 0xAC95F0, 0x60),
                           ("ad4a70.txt", 0xAD4A70, 0x800)):
        p = write_report(name, disasm(img, va, va + size))
        summary.append("wrote " + p)

    # HTTP status-line parser: locate "HTTP/1." strings and their xrefs.
    lines = ["HTTP/1.x string occurrences and code refs:"]
    i = 0
    n = len(img)
    occ = []
    while True:
        i = img.find(b"HTTP/1.", i, n)
        if i < 0:
            break
        tail = img[i:i + 24].split(b"\x00")[0]
        occ.append((BASE + i, tail))
        lines.append("VA=0x%08X  %r" % (BASE + i, tail.decode("latin1")))
        i += 1
    for sva, _s in occ:
        xrefs = scan_imm32_refs(img, sva)
        lines.append("refs to 0x%08X: %d" % (sva, len(xrefs)))
        for xa in xrefs[:6]:
            lines.append("  --- ref at 0x%08X ---" % xa)
            lines += disasm(img, xa - 0x30, xa + 0x30)
    p = write_report("http11.txt", lines)
    summary.append("wrote %s (%d strings)" % (p, len(occ)))

    p = write_report("c761xx.txt", disasm(img, 0xC76080, 0xC76240))
    summary.append("wrote " + p)

    for va in (0xB99350, 0xB99610, 0xB994B0):
        p = write_report("vt_%x.txt" % va, disasm(img, va, va + 0x200))
        summary.append("wrote " + p)

    hits = scan_reg_disp_store(img, 0x464)
    lines = ["stores to [reg+0x464] candidates:"]
    for va, note in hits:
        lines.append("write at VA=0x%08X  %s" % (va, note))
        lines += disasm(img, max(va - 0x40, BASE), va + 0x20)
        lines.append("-" * 60)
    if len(hits) == 0:
        lines.append("(none)")
    p = write_report("store_464.txt", lines)
    summary.append("wrote %s (%d hits)" % (p, len(hits)))

    needle = b"X-TransactionID: %I64u\x00"
    soff = img.find(needle)
    lines = []
    if soff < 0:
        lines.append("X-TransactionID format string NOT FOUND in image")
    else:
        sva = BASE + soff
        lines.append('"X-TransactionID: %%I64u" VA=0x%08X' % sva)
        xrefs = scan_imm32_refs(img, sva)
        lines.append("imm32 refs to that VA: %d" % len(xrefs))
        for xa in xrefs:
            lines.append("")
            lines.append("=== ref at VA=0x%08X ===" % xa)
            lines += disasm(img, max(xa - 0x60, BASE), xa + 0x20)
    p = write_report("xtransactionid.txt", lines)
    summary.append("wrote " + p)

    lines = ["near-call rel32 targets landing in [0xC76100,0xC761D0):"]
    callees = {}
    i = 0
    n = len(img)
    while True:
        i = img.find(b"\xE8", i, n - 5)
        if i < 0:
            break
        rel = struct.unpack("<i", img[i + 1:i + 5])[0]
        src = BASE + i
        tgt = (src + 5 + rel) & 0xFFFFFFFF
        if 0xC76100 <= tgt < 0xC761D0:
            callees.setdefault(tgt, []).append(src)
        i += 1
    for tgt in sorted(callees):
        for src in callees[tgt]:
            lines.append("call from 0x%08X -> 0x%08X" % (src, tgt))
    for tgt in sorted(callees):
        lines.append("")
        lines.append("=== caller context, target 0x%08X ===" % tgt)
        lines += disasm(img, max(callees[tgt][0] - 0x50, BASE),
                        callees[tgt][0] + 0x10)
    p = write_report("callers_c761xx.txt", lines)
    summary.append("wrote %s (%d targets)" % (p, len(callees)))

    print("\n".join(summary))


if __name__ == "__main__":
    main()
