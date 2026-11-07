# EX-060: earliest conditional gates on the path 0x9860 -> 0x9570 -> 0x96E9.
import json
from collections import deque

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, callsite_info


def bb_of(fn, rva):
    for start, b in fn.bbs.items():
        if b.insns and b.insns[0] <= rva <= b.insns[-1]:
            return start
    return None


def path_to(fn, entry, target, limit=128):
    tgt = bb_of(fn, target)
    q = deque([(entry, [entry])])
    seen = {entry}
    while q:
        b, path = q.popleft()
        if b == tgt:
            return path
        if len(path) > limit:
            continue
        for s, k in fn.bbs[b].succ:
            if s not in seen and s in fn.bbs:
                seen.add(s)
                q.append((s, path + [s]))
    return None


def show_bbs(fn, path, title):
    print("=" * 74)
    print(title)
    print("=" * 74)
    for b in path:
        blk = fn.bbs[b]
        print("\n-- BB 0x%X (%s) --" % (b, blk.kind))
        for r in blk.insns:
            insn = fn.insns[r]
            print("   %08X  %-20s %s %s" % (
                insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str))
        print("   succ: %s" % (blk.succ,))


def main():
    img = Image(DLL)
    imports = build_imports(img)
    fn = Function(img, 0x9860, "InitInGameApp").run().build_bbs()
    p = path_to(fn, 0x9860, 0x99D2)
    show_bbs(fn, p, "SHORTEST BB PATH 0x9860 -> call@0x99D2 (initIfsLib)")

    print()
    print()
    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()
    p2 = path_to(fi, 0x9570, 0x96E9)
    show_bbs(fi, p2, "SHORTEST BB PATH 0x9570 -> 0x96E9 (LoadLibraryW)")

    print()
    print()
    print("=" * 74)
    print("GATES on the path to LoadLibraryW")
    print("=" * 74)
    gates = [
        (0x95D0, "[ebp+0x60] == 0 ?  (CreateIFSLibDll slot empty)"),
        (0x95DA, "[esp+0xb8] == 0 ?  (initIfsLib arg; ctor/state flag)"),
        (0x9649, "path-string construction (std::string SSO check)"),
        (0x9690, "[esp+0x14] != 0 -> operator delete"),
        (0x96A1, "path concat: string + L\"ifs...\" + dll name"),
        (0x96DE, "SSO check"),
        (0x96E8, "push arg; call LoadLibraryW"),
    ]
    for gate, desc in gates:
        b = bb_of(fi, gate)
        if b is None:
            print("  gate 0x%X : NOT FOUND" % gate)
            continue
        blk = fi.bbs[b]
        term = fi.insns[blk.insns[-1]]
        print("  gate 0x%X : BB 0x%X  %-52s term=%s %s" % (
            gate, b, desc, term.mnemonic, term.op_str))
        print("                          succ=%s" % (blk.succ,))

    print()
    print("=" * 74)
    print("STRING CONSTANTS used on the path")
    print("=" * 74)
    for rva in (0x34904, 0x34908, 0x34920, 0x34964, 0x34974, 0x349b4,
                0x349e4, 0x349f8, 0x34a34):
        s = img.cstr(rva, 200)
        print("  0x%05X : %r" % (rva, s))
        w = img.read(rva, 160)
        try:
            ws = w.decode("utf-16-le").split("\x00")[0]
            if ws and len(ws) > 2:
                print("            utf16: %r" % ws)
        except Exception:
            pass

    print()
    print("=" * 74)
    print("sub_94C0 (called at 0x960B, right before the LoadLibraryW arg build)")
    print("=" * 74)
    sub = Function(img, 0x94C0, "sub_94C0").run().build_bbs()
    for rva, insn in list(sub.insns.items())[:60]:
        mark = ""
        if insn.mnemonic.startswith("call") or insn.mnemonic == "call":
            ci = callsite_info(sub, rva, insn, img, imports)
            mark = "   ; " + json.dumps(
                {k: v for k, v in ci.items() if k in ("kind", "dll", "import", "target_rva", "reg")})
        if insn.operands:
            op = insn.operands[0]
            if op.type == 2:
                t = op.imm - img.base
                if img.is_mapped(t):
                    cs = img.cstr(t, 64)
                    if cs and len(cs) > 2:
                        mark += '   ; "%s"' % cs.decode(errors="replace")
        print("   %08X  %-20s %s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))


if __name__ == "__main__":
    main()
