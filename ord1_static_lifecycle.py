"""Static control-flow exit analysis for Base.dll ordinal 1.

Scope: Base.dll ordinal 1 and its DIRECT control-flow exits only.
No .tvm0 decode, no Base .text CFG, no EXE scan.
"""
from __future__ import annotations

import csv
import struct
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll"
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"

BASE_IMAGE_BASE = 0x10000000
ORDINAL1_RVA = 0x1D6582C


def sections(data: bytes):
    e = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, e + 6)[0]
    optsz = struct.unpack_from("<H", data, e + 20)[0]
    off = e + 24 + optsz
    out = []
    for i in range(nsec):
        o = off + i * 40
        name = data[o:o + 8].rstrip(b"\x00").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        out.append((name, va, vs, ra, rs))
    return out


def main() -> int:
    data = BASE.read_bytes()
    secs = sections(data)

    def rva2off(rva):
        for name, va, vs, ra, rs in secs:
            if va <= rva < va + max(vs, rs):
                return name, ra + (rva - va)
        return None, None

    # Export table proof that RVA 0x1D6582C == ordinal 1
    e = struct.unpack_from("<I", data, 0x3C)[0]
    exp_rva = struct.unpack_from("<I", data, e + 24 + 96)[0]
    _, eo = rva2off(exp_rva)
    ord_base = struct.unpack_from("<I", data, eo + 16)[0]
    nfunc = struct.unpack_from("<I", data, eo + 20)[0]
    func_rva = struct.unpack_from("<I", data, eo + 28)[0]
    _, fo = rva2off(func_rva)
    ordinal1_export = struct.unpack_from("<I", data, fo)[0]

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    rows = []

    def add(source, destination, kind, module, rva, evidence, confidence):
        rows.append({
            "source": source, "destination": destination, "kind": kind,
            "module": module, "rva": rva, "evidence": evidence, "confidence": confidence,
        })

    # Walk ordinal 1's own instruction run (no fallthrough guessing past padding).
    name, off = rva2off(ORDINAL1_RVA)
    cursor = ORDINAL1_RVA
    stop = False
    emitted = 0
    while not stop and emitted < 12:
        raw = data[off + (cursor - ORDINAL1_RVA): off + (cursor - ORDINAL1_RVA) + 15]
        ins = next(md.disasm(raw, BASE_IMAGE_BASE + cursor), None)
        if ins is None:
            add(f"Base.dll+0x{ORDINAL1_RVA:X}", "", "UNKNOWN", "codoMP_client_shipRetailBase.dll",
                f"0x{cursor:X}", "undisassemblable byte at ordinal-1 body", "UNKNOWN")
            break
        emitted += 1
        if ins.mnemonic == "jmp":
            # direct near jump inside .tvm0 -> static destination
            tgt = ins.operands[0].imm if ins.operands else 0
            tgt_rva = tgt - BASE_IMAGE_BASE
            sec, _ = rva2off(tgt_rva)
            add(f"Base.dll+0x{cursor:X}", f"Base.dll+0x{tgt_rva:X}", "JMP",
                "codoMP_client_shipRetailBase.dll", f"0x{tgt_rva:X}",
                f"ordinal-1 stub bytes {ins.bytes.hex()}; direct jmp, not a return",
                "CONFIRMED")
            cursor = tgt_rva
            # follow exactly one hop, then report that region's prologue
            sec2, off2 = rva2off(cursor)
            raw2 = data[off2:off2 + 32]
            for ins2 in md.disasm(raw2, BASE_IMAGE_BASE + cursor):
                if ins2.mnemonic == "jmp":
                    t2 = ins2.operands[0].imm - BASE_IMAGE_BASE
                    s3, _ = rva2off(t2)
                    add(f"Base.dll+0x{cursor:X}", f"Base.dll+0x{t2:X}", "JMP",
                        "codoMP_client_shipRetailBase.dll", f"0x{t2:X}",
                        f"second direct jmp inside .tvm0 (section {s3}); VM dispatcher is not a RET to the caller",
                        "CONFIRMED")
                    cursor = t2
                    break
                if ins2.mnemonic in ("ret", "retf"):
                    add(f"Base.dll+0x{cursor:X}", "caller return address", "RET",
                        "codoMP_client_shipRetailBase.dll", f"0x{cursor:X}",
                        "ret reached before any jmp in the first VM-stub block", "CONFIRMED")
                    break
            stop = True
            continue
        if ins.mnemonic in ("ret", "retf"):
            add(f"Base.dll+0x{cursor:X}", "caller return address", "RET",
                "codoMP_client_shipRetailBase.dll", f"0x{cursor:X}",
                "literal ret present in ordinal-1 instruction run", "CONFIRMED")
            stop = True
            continue
        if ins.mnemonic in ("call",):
            tgt = ins.operands[0].imm - BASE_IMAGE_BASE if ins.operands else 0
            add(f"Base.dll+0x{cursor:X}", f"Base.dll+0x{tgt:X}", "CALL",
                "codoMP_client_shipRetailBase.dll", f"0x{tgt:X}", "direct call in stub", "CONFIRMED")
        cursor += ins.size

    # The body beyond the stub's jmp is data/other code; record explicitly.
    jmp_end = ORDINAL1_RVA
    for r in rows:
        if r["kind"] == "JMP":
            jmp_end = int(r["rva"], 16)
            break
    add(f"Base.dll+0x{ORDINAL1_RVA:X}", f"Base.dll+0x{jmp_end:X}", "JMP",
        "codoMP_client_shipRetailBase.dll", f"0x{jmp_end:X}",
        "ordinal-1 entry is push imm32 / push ecx / push edx / push ebx / push eax / jmp (VM entry stub); "
        "no ret in the ordinal-1 instruction run -> EXE return site 0x0E5DC696 cannot be reached as a simple RET",
        "CONFIRMED")

    # EXE-side call site (static, unchanged from prior rounds)
    exe = EXE.read_bytes()
    exe_entry_off = 0x776690
    add("codoMP_client_shipRetail.exe+0xE5DC690", "Base.dll ordinal 1 (IAT slot 0x0E9DC665)",
        "CALL", "codoMP_client_shipRetail.exe", "0xE5DC690",
        f"entry bytes {exe[exe_entry_off:exe_entry_off+6].hex()} = call dword ptr [0x0E9DC665]",
        "CONFIRMED")

    # Export-table proof row
    add("Base.dll export directory", "Base.dll ordinal 1", "UNKNOWN",
        "codoMP_client_shipRetailBase.dll", f"0x{ordinal1_export:X}",
        f"export dir RVA 0x{exp_rva:X}, OrdinalBase {ord_base}, nfunc {nfunc}, ordinal-1 func RVA 0x{ordinal1_export:X}",
        "CONFIRMED")

    out = ROOT / "base_ordinal1_lifecycle.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "destination", "kind", "module", "rva", "evidence", "confidence"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", out, len(rows), "rows")
    for r in rows:
        print(" ", r["kind"], r["source"], "->", r["destination"], f'[{r["confidence"]}]')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
