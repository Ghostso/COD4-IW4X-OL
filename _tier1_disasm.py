"""Tier-1 static disassembly helper (READ-ONLY).

Disassembles key regions in the decrypted runtime image related to the
marketplace.json resource gate. No game run, no memory writes, no file writes
except stdout.
"""
import struct
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(ROOT, "CODOLServer", "_mainline",
                     "_dyn100_run_20260925_182324", "live", "image_best.bin")


def load():
    with open(IMAGE, "rb") as f:
        return f.read()


def dis_range(data, start_va, end_va):
    off = start_va - BASE
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(data[off:off + end_va - start_va], start_va))


def print_block(title, data, va_lo, va_hi):
    print("=" * 78)
    print(title)
    print("=" * 78)
    off = va_lo - BASE
    if off < 0 or off + (va_hi - va_lo) > len(data):
        print("  [out of range]")
        return
    for ins in dis_range(data, va_lo, va_hi):
        print("  %08X  %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))
    print()


def print_memrefs(data, target_va, label=""):
    """Find instructions that embed *target_va* as an absolute dword."""
    pat = struct.pack("<I", target_va)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    hits = []
    i = data.find(pat)
    while i != -1:
        hits.append(i)
        i = data.find(pat, i + 1)
    if not hits:
        return
    print("=" * 78)
    print("MEMREFS to %08X  %s  (%d hits)" % (target_va, label, len(hits)))
    print("=" * 78)
    for i in hits:
        va = BASE + i
        ctx_va = max(BASE, va - 20)
        ctx_len = va + 4 + 16 - ctx_va
        off = ctx_va - BASE
        try:
            insns = list(md.disasm(data[off:off + ctx_len], ctx_va))
        except Exception:
            continue
        hit = None
        for ins in insns:
            ins_off = ins.address - BASE
            if ins_off <= i < ins_off + ins.size:
                hit = ins
                break
        if not hit:
            continue
        tag = ""
        if "byte" in hit.op_str and hit.mnemonic == "mov":
            tag = "  <-- WRITE"
        elif hit.mnemonic == "cmp" and "byte" in hit.op_str:
            tag = "  <-- CHECK"
        elif hit.mnemonic == "mov":
            tag = "  <-- MOV"
        print("  %08X  %-12s %s%s" % (hit.address, hit.mnemonic,
                                      hit.op_str, tag))
    print()


def find_rel32_callers(data, target_va):
    """Find rel32 call/jmp to *target_va*."""
    results = []
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in range(len(data) - 5):
        if data[i] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", data, i + 1)[0]
            src = BASE + i
            if src + 5 + rel == target_va:
                ctx_va = max(BASE, src - 16)
                ctx_len = src + 5 + 24 - ctx_va
                off = ctx_va - BASE
                try:
                    insns = list(md.disasm(data[off:off + ctx_len], ctx_va))
                except Exception:
                    continue
                results.append((src, insns))
    return results


def main():
    data = load()
    print("image size: %d  base: 0x%X" % (len(data), BASE))
    print()

    # 1. gate write candidates around 0x4A8F55..0x4A8F83
    print_block("GATE writes: 0x4A8F40-0x4A8FA0",
                data, 0x4A8F40, 0x4A8FA0)

    # 2. branch check / call sites region
    print_block("BRANCH gates: 0x4A9800-0x4A9A80",
                data, 0x4A9800, 0x4A9A80)

    # 3. marketplace.json fetch function
    print_block("FETCH_FUNC 0x4A93E0: 0x4A9300-0x4A9440",
                data, 0x4A9300, 0x4A9440)

    # 4. writer/reader at 0x50E000
    print_block("WRITER_FUNC 0x50E000-0x50E260",
                data, 0x50E000, 0x50E260)

    # 5. callers of 0x4A93E0
    callers = find_rel32_callers(data, 0x4A93E0)
    print("=" * 78)
    print("RELATIVE CALLERS of 0x4A93E0 marketplace.json fetcher")
    print("=" * 78)
    for src, insns in callers:
        for ins in insns:
            tag = ""
            if ins.address == src and ins.mnemonic == "call":
                tag = "  <-- CALL TO 0x4A93E0"
            print("  %08X  %-10s %s%s" % (ins.address, ins.mnemonic,
                                          ins.op_str, tag))
        print()

    # 6. memory references to each gate global (original set)
    for g in [0xE60B80, 0xE60B81, 0xE60B82, 0xE60B84,
              0xE60B88, 0xE60B90, 0xE60B98]:
        print_memrefs(data, g)

    # 7. callers of the gate-write site 0x4A8F55
    callers2 = find_rel32_callers(data, 0x4A8F55)
    print("=" * 78)
    print("RELATIVE CALLERS of 0x4A8F55 (gate write site)")
    print("=" * 78)
    for src, insns in callers2:
        for ins in insns:
            tag = ""
            if ins.address == src and ins.mnemonic == "call":
                tag = "  <-- CALL TO 0x4A8F55"
            print("  %08X  %-10s %s%s" % (ins.address, ins.mnemonic,
                                          ins.op_str, tag))
        print()

    # ================================================================
    # CORRECTED ANALYSIS (2026-09-30) — focusing on the REAL gate vars
    # ================================================================
    print("=" * 78)
    print("CORRECTED: dispatch enable + GATE variable traces")
    print("=" * 78)

    # 8. dispatch enable gate at 0x8083B3
    print_block("DISPATCH ENABLE 0x8083B0-0x8083E0",
                data, 0x8083B0, 0x8083E0)

    # 9. GATE=3 writer chain 0x4A7E20
    print_block("GATE=3 WRITER 0x4A7E18-0x4A7E60",
                data, 0x4A7E18, 0x4A7E60)

    # 10. GATE == 3 check sites
    for g in [0x82C4A88, 0x82C4AEC, 0x84ABB2F, 0xE57A5C, 0xC7AF1E0, 0xC7AF440,
              0x84ABA50, 0x849BA3D, 0x33E6A18, 0xC7AF1E0]:
        print_memrefs(data, g)

    # 11. callers of state machine 0x808240
    sm_callers = find_rel32_callers(data, 0x808240)
    print("=" * 78)
    print("RELATIVE CALLERS of 0x808240 (state machine)")
    print("=" * 78)
    for src, insns in sm_callers:
        for ins in insns:
            tag = ""
            if ins.address == src and ins.mnemonic == "call":
                tag = "  <-- CALL TO 0x808240"
            print("  %08X  %-10s %s%s" % (ins.address, ins.mnemonic,
                                          ins.op_str, tag))
        print()

    # 12. state 5 handler 0x7EEBF0
    print_block("STATE 5 HANDLER 0x7EEBF0-0x7EEC95",
                data, 0x7EEBF0, 0x7EEC95)

    # 13. G2F writer at 0x80A36E
    print_block("G2F WRITER 0x80A360-0x80A3A0",
                data, 0x80A360, 0x80A3A0)


if __name__ == "__main__":
    main()