# -*- coding: utf-8 -*-
"""Correct recursive CFG for 32-bit x86 in the recovered image. READ-ONLY."""
import _common as c

def section_end(rva):
    s = c.img_section_of(rva)
    return s["raw"] + s["rsize"] if s else rva

def recursive_cfg(entry, hard_end=None, limit=200000):
    """Recursive-descent disasm following direct branches. Returns (seen, cfg).
    seen: addr -> CsInsn ; cfg: addr -> list[(succ_addr, kind)]"""
    end = section_end(entry)
    if hard_end is not None:
        end = min(end, hard_end)
    work = [entry]
    seen = {}
    cfg = {}
    while work:
        a = work.pop()
        if a in seen or not (entry <= a < end):
            continue
        while entry <= a < end:
            if a in seen:
                break
            ins = c.idis_at(a, 16)
            if ins is None:
                break
            seen[a] = ins
            m, ops, nxt = ins.mnemonic, ins.op_str, a + ins.size
            succ = []
            direct_t = None
            if ops.startswith("0x"):
                try:
                    direct_t = int(ops.split()[0], 16) - c.IMG_IB
                except ValueError:
                    direct_t = None
            if m.startswith("ret"):
                pass
            elif m == "jmp":
                if direct_t is not None:
                    succ.append((direct_t, "jmp")); work.append(direct_t)
                # indirect jmp -> terminator, unknown target
            elif m == "call":
                if direct_t is not None:
                    cfg.setdefault(a, [])
                succ.append((nxt, "fall"))   # call returns
            elif m.startswith("j"):
                if direct_t is not None:
                    succ.append((direct_t, "jcc")); work.append(direct_t)
                succ.append((nxt, "fall")); work.append(nxt)
            elif m in ("int3", "hlt", "ud2"):
                pass
            else:
                succ.append((nxt, "next"))
            cfg[a] = succ
            # stop linear block at control-flow terminators
            if m.startswith("ret") or m == "jmp" or m in ("int3", "hlt", "ud2") or m.startswith("j"):
                break
            a = nxt
            if len(seen) > limit:
                break
    return seen, cfg

def direct_calls(seen):
    out = {}
    for a, ins in seen.items():
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                t = int(ins.op_str.split()[0], 16) - c.IMG_IB
            except ValueError:
                continue
            out.setdefault(t, []).append(a)
    return out

def indirect_flow(seen):
    out = []
    for a, ins in seen.items():
        if ins.mnemonic in ("call", "jmp") and not ins.op_str.startswith("0x"):
            out.append((a, ins.mnemonic, ins.op_str, ins.bytes.hex()))
    return out

def basic_blocks(entry, seen, cfg):
    """Return list of (start,end_exclusive,term_kind,targets)."""
    starts = {entry}
    for a, succs in cfg.items():
        for (t, k) in succs:
            if k in ("jcc", "jmp"):
                starts.add(t)
        if len(succs) > 1:
            starts.add(succs[-1][0])
    blocks = []
    for s in sorted(starts):
        if s not in seen:
            continue
        a = s
        addrs = []
        while a in seen:
            addrs.append(a)
            ins = seen[a]
            succs = cfg.get(a, [])
            term = None
            if ins.mnemonic.startswith("ret"):
                term = "ret"
            elif ins.mnemonic == "jmp":
                term = "jmp"
            elif ins.mnemonic.startswith("j"):
                term = "jcc"
            if term:
                break
            nxt = a + ins.size
            if nxt in starts or nxt not in seen:
                break
            a = nxt
        if addrs:
            blocks.append((addrs[0], addrs[-1] + seen[addrs[-1]].size, term, [t for t, k in cfg.get(addrs[-1], [])]))
    return blocks