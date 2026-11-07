# -*- coding: utf-8 -*-
"""044 Phase B: recursive CFG + field/compare extraction. READ-ONLY."""
import _common as c, os, struct, json

FUNCS = {
    0x87C110: ("0x87C110", "net-buffer decoder #1"),
    0x87D5A0: ("0x87D5A0", "net-buffer decoder #2"),
    0x87ED70: ("0x87ED70", "shared helper A (candidate core)"),
    0x87EDB0: ("0x87EDB0", "shared helper B (candidate core)"),
}

def section_end(rva):
    s = c.img_section_of(rva)
    return s["raw"] + s["rsize"] if s else rva

def recursive_cfg(entry, hard_end=None):
    """Worklist recursive disassembly. Returns (insns_by_addr, cfg, blocks, terminator)."""
    work = [entry]
    seen = {}
    order = []
    cfg = {}   # addr -> list of successor addrs (fallthrough + direct branch)
    end_of = section_end(entry)
    if hard_end:
        end_of = min(end_of, hard_end)
    while work:
        a = work.pop()
        if a in seen or not (entry <= a < end_of):
            continue
        while entry <= a < end_of:
            if a in seen:
                break
            ins = c.idis_at(a, 16)
            if ins is None:
                break
            seen[a] = ins
            order.append(a)
            m = ins.mnemonic
            ops = ins.op_str
            nxt = a + ins.size
            succ = []
            if m == "ret" or m.startswith("ret"):
                pass
            elif m == "jmp":
                if ops.startswith("0x"):
                    t = int(ops, 16) - c.IMG_IB
                    succ.append(t); work.append(t)
                else:
                    pass  # indirect
            elif m.startswith("j"):
                if ops.startswith("0x"):
                    t = int(ops, 16) - c.IMG_IB
                    succ.append(t); work.append(t)
                succ.append(nxt)
            elif m in ("call",):
                pass
            elif m == "int3":
                pass
            else:
                succ.append(nxt)
            cfg[a] = succ
            if m == "jmp" or (m.startswith("j") and m != "jmp"):
                break  # tail: do not fall through past a jump
            if m.startswith("ret"):
                break
            if m == "int3":
                break
            a = nxt
    blocks = []
    addrs = sorted(seen)
    return seen, cfg, blocks, addrs

out = []
def P(s=""): out.append(s)

report = {}
for entry, (name, desc) in FUNCS.items():
    seen, cfg, _, addrs = recursive_cfg(entry)
    # find max address reached and the terminating ret
    P("=" * 78)
    P("%s  %s" % (name, desc))
    P("  entry=%08x  insns=%d  reachable_end=%08x" % (entry, len(seen), max(addrs) if addrs else 0))
    # area coverage
    lo = min(addrs); hi = max(addrs)
    P("  own-instruction span = %08x..%08x  (span len %d)" % (lo, hi, hi - lo))
    # exits
    exits = []
    for a, ins in seen.items():
        if ins.mnemonic.startswith("ret"):
            exits.append((a, ins.mnemonic))
    P("  ret sites: %s" % ["%08x(%s)" % (a, m) for a, m in sorted(exits)])
    # direct calls
    calls = {}
    for a, ins in seen.items():
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16) - c.IMG_IB
            calls.setdefault(t, []).append(a)
    P("  direct calls: %d distinct targets" % len(calls))
    for t in sorted(calls):
        P("      -> %08x  x%d  from %s" % (t, len(calls[t]), ["%x" % x for x in calls[t]]))
    # indirect call/jmp
    for a, ins in seen.items():
        if ins.mnemonic in ("call", "jmp") and not ins.op_str.startswith("0x"):
            P("  INDIRECT %s at %08x : %s => %s" % (ins.mnemonic, a, ins.bytes.hex(), ins.op_str))
    report[entry] = dict(calls={("%08x" % k): v for k, v in calls.items()}, size=len(seen))
    P("")

c.w(os.path.join(c.EV, "b01_cfg.txt"), "\n".join(out))
c.w(os.path.join(c.EV, "b01_cfg_calls.json"), json.dumps(report, indent=1))
print("\n".join(out))