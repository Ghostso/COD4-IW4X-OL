# -*- coding: utf-8 -*-
"""044 Phase B: type-field / compare / dispatch extraction. READ-ONLY."""
import _cfg, _common as c, os, json, capstone

FUNCS = [(0x87C110, "0x87C110", "netbuffer decoder #1"),
         (0x87D5A0, "0x87D5A0", "netbuffer decoder #2"),
         (0x87ED70, "0x87ED70", "helper A"),
         (0x87EDB0, "0x87EDB0", "helper B")]

def mem_ops(ins):
    out = []
    for op in ins.operands:
        if op.type == capstone.x86.X86_OP_MEM:
            m = op.mem
            base = ins.reg_name(m.base) if m.base else None
            idx = ins.reg_name(m.index) if m.index else None
            out.append(dict(base=base, index=idx, scale=m.scale, disp=m.disp))
    return out

out = []
def P(s=""): out.append(s)

summary = {}
for entry, name, desc in FUNCS:
    seen, cfg = _cfg.recursive_cfg(entry)
    addrs = sorted(seen)
    P("=" * 80)
    P("%s  %s   insns=%d  span=%08x..%08x" % (name, desc, len(seen), addrs[0], addrs[-1]))
    P("-" * 80)

    # 1. any memory operand with disp == 8 (the "[ebx+8]"-family "type/kind" field)
    P("  [1] memory operands with disp==+8 (type/kind-field candidates):")
    n8 = 0
    for a in addrs:
        ins = seen[a]
        for mo in mem_ops(ins):
            if mo["disp"] == 8:
                n8 += 1
                P("      %08x  %-28s  base=%s idx=%s disp=+8" % (a, "%s %s" % (ins.mnemonic, ins.op_str), mo["base"], mo["index"]))
    if n8 == 0:
        P("      (none)")
    P("")

    # 2. all cmp/test/sub-cascade dispatch candidates
    P("  [2] compare/test instructions (operand view):")
    for a in addrs:
        ins = seen[a]
        if ins.mnemonic in ("cmp", "test"):
            P("      %08x  %-30s" % (a, "%s %s" % (ins.mnemonic, ins.op_str)))
    P("")

    # 3. indirect call/jmp
    P("  [3] indirect CALL/JMP:")
    ind = _cfg.indirect_flow(seen)
    if not ind:
        P("      (none)")
    for a, m, ops, b in ind:
        P("      %08x  %-6s %-28s bytes=%s" % (a, m, ops, b))
    P("")

    # 4. direct calls out
    P("  [4] direct calls:")
    for t, sites in sorted(_cfg.direct_calls(seen).items()):
        P("      -> %08x x%d  %s" % (t, len(sites), ["%x" % s for s in sites]))
    P("")

    summary[name] = dict(insns=len(seen), span=[addrs[0], addrs[-1]],
                         n_disp8=n8, n_indirect=len(ind),
                         calls={("%08x" % t): len(s) for t, s in _cfg.direct_calls(seen).items()})

c.w(os.path.join(c.EV, "b02_types.txt"), "\n".join(out))
c.w(os.path.join(c.EV, "b02_types.json"), json.dumps(summary, indent=1))
# also dump full recursive disasm of each function
for entry, name, desc in FUNCS:
    seen, cfg = _cfg.recursive_cfg(entry)
    lines = ["# full recursive disasm %s %s" % (name, desc)]
    for a in sorted(seen):
        ins = seen[a]
        lines.append(c.dis_text(ins))
    c.w(os.path.join(c.EV, "dis_full_%s.txt" % name.replace("0x", "")), "\n".join(lines))
print("\n".join(out[:200]))
print("... (truncated)")