# EX-060: recover CFG for CNIFS::initIfsLib (+0x9570) and
# CNIFS::InitInGameApp (+0x9860).
import json
import os
import sys

from ex060_iips_cfg import Image, DLL, build_imports, build_exports, sha256
from ex060_cfg_engine import Function, callsite_info


def dump_fn(img, imports, entry, name, extra_entries=()):
    fn = Function(img, entry, name, extra_entries).run().build_bbs()
    print("=" * 78)
    print("FUNCTION %s  RVA 0x%X" % (name, entry))
    print("instructions=%d  bbs=%d" % (len(fn.insns), len(fn.bbs)))
    print("=" * 78)
    for rva, b in fn.bbs.items():
        print("\n-- BB 0x%X  kind=%s  insns=%d" % (rva, b.kind, len(b.insns)))
        for ir in b.insns:
            insn = fn.insns[ir]
            mark = ""
            if insn.mnemonic.startswith("call"):
                ci = callsite_info(fn, ir, insn, img, imports)
                if ci.get("kind") == "iat":
                    mark = "   ; IAT %s!%s" % (ci["dll"], ci["import"])
                elif ci.get("kind") == "direct":
                    mark = "   ; -> sub_%X" % ci["target_rva"]
                else:
                    mark = "   ; %s %s" % (
                        ci.get("kind"), ci.get("mem") or ci.get("reg") or "")
            # annotate string references
            if insn.mnemonic in ("push", "mov", "lea") and insn.operands:
                op = insn.operands[0]
                if op.type == 2:  # X86_OP_IMM
                    t = op.imm - img.base
                    s = img.cstr(t, 96) if img.is_mapped(t) else None
                    if s and len(s) > 3 and all(
                        32 <= c < 127 or c in (9, 10, 13) for c in s
                    ):
                        mark += '   ; "%s"' % s.decode(errors="replace")
            print("   %08X  %-22s %s %s%s" % (
                insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if b.succ:
            print("   succ: " + ", ".join(
                "0x%X(%s)" % (s, k) for s, k in b.succ))
    # callsite summary
    print("\n--- CALLSITES in %s ---" % name)
    for rva, insn in fn.insns.items():
        if insn.mnemonic.startswith("call"):
            ci = callsite_info(fn, rva, insn, img, imports)
            print("  0x%X -> %s" % (rva, json.dumps(ci, sort_keys=True)))
    return fn


def main():
    img = Image(DLL)
    imports = build_imports(img)
    print("iips.dll sha256", sha256(DLL))
    print("image base", hex(img.base), "size", hex(img.size))

    fn_init = dump_fn(img, imports, 0x9570, "CNIFS__initIfsLib")
    print("\n\n")
    fn_ingame = dump_fn(img, imports, 0x9860, "CNIFS__InitInGameApp")


if __name__ == "__main__":
    main()
