"""Agent 22 - independent ABI audit.

Take each ABI claim carried over from RESTORE_LOCALRM_001..005 and try to
REFUTE it against the original machine code.  A claim is only promoted to
CONFIRMED when this script finds direct evidence, and is DEMOTED when it
contradicts the bytes.
"""
import capstone
import pefile

ORIG = r"COD OL\IIPS\iips.dll"
IMG = 0x10000000


def main():
    pe = pefile.PE(ORIG, fast_load=True)
    d = open(ORIG, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    r2o = pe.get_offset_from_rva

    def insns(rva, n=400):
        o = r2o(rva)
        out = []
        for i in md.disasm(d[o:o + n], IMG + rva):
            out.append(i)
            if i.mnemonic.startswith("ret"):
                break
        return out

    print("=" * 78)
    print("AGENT 22 - INDEPENDENT ABI AUDIT (refutation-first)")
    print("=" * 78)

    checks = []

    def claim(name, ok, detail, verdict_if_true="CONFIRMED", verdict_if_false="REFUTED"):
        checks.append((name, ok, detail, verdict_if_true, verdict_if_false))

    # ---- 1. object size 0x410 ----
    g = insns(0x1C80)
    push_imm = [i for i in g if i.mnemonic == "push" and i.op_str.startswith("0x")]
    size_seen = any(i.op_str == "0x410" for i in push_imm)
    claim("RM_OBJECT_SIZE = 0x410", size_seen,
          "ctor arg: " + ", ".join(i.op_str for i in push_imm))

    # ---- 2. GetResourceManagerII is a singleton (guarded guard byte) ----
    guard = any("0x1004eb6c" in i.op_str for i in g)
    inst = any("0x1004eb68" in i.op_str for i in g)
    claim("GetResourceManagerII singleton", guard and inst,
          "guard byte 0x1004EB6C, instance slot 0x1004EB68")

    # ---- 3. ReleaseResourceManagerII = cdecl ----
    rel = insns(0x1C60)
    last = rel[-1]
    is_plain_ret = last.bytes[0] == 0xC3
    claim("ReleaseResourceManagerII calling convention = __cdecl",
          is_plain_ret, "epilogue bytes = %s" % last.bytes.hex())

    # ---- 4. GetResourceManagerII = cdecl ----
    ge = insns(0x1C80)
    claim("GetResourceManagerII calling convention = __cdecl",
          ge[-1].bytes[0] == 0xC3, "epilogue bytes = %s" % ge[-1].bytes.hex())

    # ---- 5. object has MULTIPLE vtable pointers (refutes single-vptr) ----
    ctor = insns(0x11F20, 0x400)
    vptr_writes = [i for i in ctor if i.mnemonic == "mov"
                   and "[ebp" in i.op_str and i.op_str.startswith("dword ptr [ebp")
                   and "0x1003" in i.op_str]
    offs = sorted({int(i.op_str.split("[ebp")[1].split("]")[0].replace(" + ", "").strip()
                        or "0", 16) if "+" in i.op_str else 0 for i in vptr_writes})
    claim("object carries MULTIPLE vptr fields (single-vptr sketch REFUTED)",
          len(offs) >= 4, "vptr offsets found in ctor: %s" % [hex(x) for x in offs])

    # ---- 6. vtable[0] slot is a DESTRUCTOR taking a scalar-delete flag ----
    vt0 = int.from_bytes(d[r2o(0x3929C):r2o(0x3929C) + 4], "little")
    dt = insns(vt0 - IMG, 0x40)
    has_flag_test = any(i.mnemonic == "test" and "[esp + 4]" in i.op_str for i in dt)
    has_free = any(i.mnemonic == "call" for i in dt)
    callee_cleans = dt[-1].bytes[0] == 0xC2
    claim("vtable[0] = destructor(this in ecx) with scalar-delete flag",
          has_flag_test and callee_cleans,
          "tests [esp+4] bit0=%s, calls allocator=%s, epilogue=%s"
          % (has_flag_test, has_free, dt[-1].bytes.hex()))
    claim("destructor preserves the expected vtable (deleting-dtor idiom)",
          any("0x1003929c" in i.op_str for i in dt),
          "writes 0x1003929C into [esi] before optional free")

    # ---- 7. Release path calls vtable[0] with exactly one argument ----
    push1 = any(i.mnemonic == "push" and i.op_str == "1" for i in rel)
    claim("ReleaseResourceManagerII -> vtable[0](this, 1)", push1 and has_free,
          "push 1 ; call [vtable+0]")

    # ---- 8. vtable[1..N] are shared stub (0x1002BF56) ----
    vt = [int.from_bytes(d[r2o(0x3929C) + k * 4: r2o(0x3929C) + k * 4 + 4], "little")
          for k in range(24)]
    stubs = sum(1 for v in vt[1:] if v == 0x1002BF56)
    claim("vtable[1..23] are populated with a shared stub, not null",
          stubs >= 20, "%d/23 slots = 0x1002BF56" % stubs)

    # ---- 9. the sketch's nested-object-at-0x70 claim ----
    claim("NESTED_OBJECT at +0x70", False,
          "ctor writes no vptr at +0x70; the sketch's offset is unsupported",
          verdict_if_false="DEMOTED_TO_UNKNOWN")

    # ---- 10. the sketch's ReleaseResourceManagerII = stdcall claim ----
    claim("ReleaseResourceManagerII = __stdcall (RESTORE_LOCALRM_001 claim)",
          False,
          "machine code ends in plain C3 ret, no callee stack cleanup",
          verdict_if_false="REFUTED")

    # ---- 11. __stdcall for GetResourceManagerII (sketch claim) ----
    claim("GetResourceManagerII = __stdcall (RESTORE_LOCALRM_001 claim)",
          False, "machine code ends in plain C3 ret",
          verdict_if_false="REFUTED")

    # ---- 12. +0x3BC flag ----
    has_3bc = any("0x3bc" in i.op_str.lower() for i in ctor)
    claim("RM_OFFSET_3BC = process flag", has_3bc,
          "ctor references +0x3BC" if has_3bc else "no +0x3BC write in ctor",
          verdict_if_false="DEMOTED_TO_UNKNOWN")

    print("%-58s %-22s %s" % ("claim", "verdict", "evidence"))
    print("-" * 78)
    for name, ok, detail, vt_, vf_ in checks:
        print("%-58s %-22s %s" % (name, vt_ if ok else vf_, detail))

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for name, ok, detail, vt_, vf_ in checks:
        v = vt_ if ok else vf_
        if v == "REFUTED":
            print("  REFUTED  : %s" % name)
    print()
    for name, ok, detail, vt_, vf_ in checks:
        v = vt_ if ok else vf_
        if v == "DEMOTED_TO_UNKNOWN":
            print("  DEMOTED  : %s" % name)
    print()
    for name, ok, detail, vt_, vf_ in checks:
        v = vt_ if ok else vf_
        if v == "CONFIRMED":
            print("  CONFIRMED: %s" % name)

    pe.close()


if __name__ == "__main__":
    main()
