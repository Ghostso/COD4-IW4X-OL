# EX-060 TASK 2: is +0x96E9 statically reachable from +0x9860?
import json
from collections import deque, OrderedDict

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, COND_JMP, callsite_info


def reach_bb(fn, entry):
    seen = set()
    q = deque([entry])
    while q:
        b = q.popleft()
        if b in seen or b not in fn.bbs:
            continue
        seen.add(b)
        for s, k in fn.bbs[b].succ:
            q.append(s)
    return seen


def bb_of(fn, rva):
    for start, b in fn.bbs.items():
        if b.insns and b.insns[0] <= rva <= b.insns[-1]:
            return start
    return None


def path_to(fn, entry, target, limit=64):
    """BFS shortest path entry -> BB containing target."""
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


def main():
    img = Image(DLL)
    imports = build_imports(img)

    fn = Function(img, 0x9860, "InitInGameApp").run().build_bbs()
    print("InitInGameApp: insns=%d bbs=%d" % (len(fn.insns), len(fn.bbs)))

    reach = reach_bb(fn, 0x9860)
    print("reachable BBs from 0x9860: %d of %d" % (len(reach), len(fn.bbs)))

    # Direct call to 0x9570 is at 0x99D2
    call = 0x99D2
    cb = bb_of(fn, call)
    print("\ncall 0x10009570 at 0x%X is in BB 0x%X, reachable=%s" % (
        call, cb, cb in reach))

    # From 0x9570's internal, is 0x96E9 reachable?  Already proven by
    # ex060_reach.py: yes, all 24 BBs reachable.
    print("\n--- call-graph path from InitInGameApp to initIfsLib ---")
    p = path_to(fn, 0x9860, 0x99D2)
    if p:
        print("  BB path: " + " -> ".join("0x%X" % x for x in p))

    # ---- Now the sub-function call graph reachable from 0x9860
    print("\n--- direct calls made by InitInGameApp (reachable BBs only) ---")
    for rva, insn in fn.insns.items():
        if not insn.mnemonic.startswith("call"):
            continue
        b = bb_of(fn, rva)
        if b not in reach:
            continue
        ci = callsite_info(fn, rva, insn, img, imports)
        if ci.get("kind") == "direct":
            print("  +0x%X -> sub_%X" % (rva, ci["target_rva"]))
        elif ci.get("kind") == "iat":
            print("  +0x%X -> IAT %s!%s" % (rva, ci["dll"], ci["import"]))
        else:
            print("  +0x%X -> %s %s" % (
                rva, ci.get("kind"), ci.get("mem") or ci.get("reg")))

    print("\n--- BB 0x99BA (the initIfsLib call site) ---")
    for rva in fn.bbs[0x99BA].insns:
        insn = fn.insns[rva]
        print("   %08X  %-20s %s %s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str))
    print("   succ:", fn.bbs[0x99BA].succ)

    print("\n--- BB 0x99DB (initIfsLib failure path) ---")
    for rva in fn.bbs[0x99DB].insns:
        insn = fn.insns[rva]
        print("   %08X  %-20s %s %s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str))
    print("   succ:", fn.bbs[0x99DB].succ)

    # all exit points
    print("\n--- all 'ret' BBs in InitInGameApp ---")
    for start, b in fn.bbs.items():
        if b.kind == "ret":
            insn = fn.insns[b.insns[-1]]
            print("   0x%X  %s %s   reachable=%s" % (
                start, insn.mnemonic, insn.op_str, start in reach))

    # tail exits via jmp to out-of-range
    print("\n--- BBs with unconditional jmp to a non-recovered target ---")
    for start, b in fn.bbs.items():
        if b.kind == "jmp":
            for s, k in b.succ:
                if s not in fn.bbs:
                    print("   0x%X -> 0x%X (not in function)" % (start, s))

    print("\n--- BBs whose last insn is 'jmp reg' / indirect (tails) ---")
    for start, b in fn.bbs.items():
        if b.kind == "indirect":
            insn = fn.insns[b.insns[-1]]
            print("   0x%X  %s %s  reachable=%s" % (
                start, insn.mnemonic, insn.op_str, start in reach))


if __name__ == "__main__":
    main()
