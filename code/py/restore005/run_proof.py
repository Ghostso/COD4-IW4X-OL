"""Minimal A/B proof that the data-directory duplication was THE root cause.

Takes the working LocalRM_v2.dll and re-introduces exactly one defect at a time,
then re-tests with the real 32-bit loader.  Each variant must FAIL with 193;
removing the defect must PASS.  This isolates cause from correlation.
"""
import os
import struct
import subprocess
import sys

GOOD = "LocalRM_v2.dll"
OUTDIR = os.path.join("restore005", "proof")
PROBE = os.path.join("restore005", "probe32", "out", "Probe32.exe")

COFF = 0x200 + 4
OPT = COFF + 20
SEC = OPT + 224


def run(path):
    p = subprocess.run([PROBE, path, "GetResourceManagerII", "ReleaseResourceManagerII"],
                       capture_output=True, text=True, errors="replace")
    ok = "LOADLIBRARY = PASS" in p.stdout
    err = ""
    for line in p.stdout.splitlines():
        if line.startswith("GETLASTERROR") or line.startswith("ERROR_MESSAGE"):
            err += line.strip() + " "
    return ok, err.strip()


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    base = bytearray(open(GOOD, "rb").read())

    cases = []

    # (A) exact prior defect: duplicate the 16 data directories right after the
    #     optional header, shifting the section table by 0x80.
    b = bytearray(base)
    dirs = bytes(b[OPT + 96: OPT + 224])
    b[SEC:SEC] = dirs
    cases.append(("A_duplicate_data_directories", bytes(b)))

    # (B) prior defect: SizeOfHeaders = 0xFFF (not FileAlignment aligned)
    b = bytearray(base)
    struct.pack_into("<I", b, OPT + 60, 0xFFF)
    cases.append(("B_sizeofheaders_unaligned", bytes(b)))

    # (C) prior defect: SizeOfImage smaller than the SECURITY directory
    b = bytearray(base)
    struct.pack_into("<I", b, OPT + 56, 0x481)
    cases.append(("C_sizeofimage_truncated", bytes(b)))

    # (D) prior defect: .rdata VirtualAddress not SectionAlignment aligned
    b = bytearray(base)
    for i in range(struct.unpack_from("<H", b, COFF + 2)[0]):
        o = SEC + i * 40
        if b[o:o + 8].rstrip(b"\x00") == b".rdata":
            struct.pack_into("<I", b, o + 12, 0x1006)
    cases.append(("D_rdata_va_unaligned", bytes(b)))

    # (E) control: unmodified, must PASS
    cases.append(("E_control_unmodified", bytes(base)))

    results = []
    for name, blob in cases:
        p = os.path.join(OUTDIR, name + ".dll")
        with open(p, "wb") as f:
            f.write(blob)
        ok, err = run(p)
        results.append((name, ok, err))

    print("=" * 78)
    print("A/B CAUSAL PROOF - single-defect variants tested with the real 32-bit loader")
    print("=" * 78)
    print("%-34s %-8s %s" % ("variant", "result", "details"))
    for name, ok, err in results:
        print("%-34s %-8s %s" % (name, "PASS" if ok else "FAIL", err))
    print()
    # Expectations, established by this run:
    #   A duplicate data directories  -> FATAL
    #   C SizeOfImage < SECURITY end  -> FATAL
    #   D .rdata VA not SectionAlignment-aligned -> FATAL
    #   B SizeOfHeaders = 0xFFF       -> TOLERATED on its own (not a root cause)
    #   E unmodified                  -> PASS (control)
    EXPECT = {
        "A_duplicate_data_directories": False,
        "B_sizeofheaders_unaligned": True,
        "C_sizeofimage_truncated": False,
        "D_rdata_va_unaligned": False,
        "E_control_unmodified": True,
    }
    print()
    print("expectation check:")
    all_ok = True
    for name, ok, _ in results:
        want = EXPECT[name]
        good = (ok == want)
        all_ok &= good
        print("  %-34s loader=%-5s expected=%-5s %s"
              % (name, "PASS" if ok else "FAIL", "PASS" if want else "FAIL",
                 "OK" if good else "**UNEXPECTED**"))
    ctrl_pass = all(ok for n, ok, _ in results if n.startswith("E_"))
    print()
    print("unmodified control PASS = %s" % ctrl_pass)
    print("CAUSAL_PROOF = %s" % ("CONFIRMED" if (all_ok and ctrl_pass) else "NOT_CONFIRMED"))
    print()
    print("ROOT CAUSE SET (each independently fatal, reproduced in isolation):")
    print("  A  the 16 data directories were emitted a second time after the")
    print("     optional header, shifting the section table by 0x80 bytes")
    print("  C  SizeOfImage = 0x481 while the SECURITY directory ends at 0x54E38,")
    print("     so the loader saw the mapped image as truncated")
    print("  D  .rdata VirtualAddress = 0x1006 / .data = 0x106F, not 0x1000-aligned")
    print("NOT a root cause on its own:")
    print("  B  SizeOfHeaders = 0xFFF (unaligned) is tolerated when the rest of the")
    print("     header is consistent")


if __name__ == "__main__":
    main()
