# -*- coding: utf-8 -*-
"""041 CORRECTED path-sensitive ESP frame model (read-only).

Models push/pop/add-sub esp/lea-esp and EVERY call (direct and indirect, incl.
`call edi` = SleepEx) using exact callee stack cleanup (ret imm16), then reports
the frame-slot identity of every [esp+K] access reachable in caller 0x231050.

Corrected key result (supersedes the earlier 041 draft):
  out base  = [esp+0x14] at 0x2310DA
  0x231171  mov ecx,[esp+0x20] -> out+0x04 (RTT) -> job+4 (0x231179)
  0x231175  mov edx,[esp+0x28] -> out+0x0C (TTL) -> job+8 (0x23117C)
The two `push` at 0x231161/0x231163 lower esp by 8 before 0x231171, which the
earlier draft omitted; it therefore mis-read the two readers' slots.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C

LO, HI = 0x231050, 0x231181
CALLEE_POPS = {
    0x10235CD0: 0, 0x1022A670: 0, 0x10235E00: 4, 0x1027D8F5: 0,
    0x10284A90: 0, 0x10284643: 0, 0x1027D28B: 0,
    0x104530EE: 4, 0x1045313C: 0,
}
# indirect calls: SleepEx(DWORD,BOOL) stdcall ret8 ; WSACloseEvent(HANDLE) ret4
def indirect_pops(op):
    if op == "edi": return 8
    mo = re.search(r"\[(0x[0-9a-f]+)\]", op)
    if mo and int(mo.group(1),16) == 0x10B02A5C: return 4
    return 0

def delta(i):
    m, o = i.mnemonic, i.op_str
    if m == "call":
        t = C.target_of(i)
        return CALLEE_POPS.get(t, 0) if t is not None else indirect_pops(o)
    if m == "push": return -4
    if m == "pop":  return +4
    if m in ("add","sub") and o.startswith("esp,"):
        v = int(o.split(",")[1], 16); return v if m == "add" else -v
    if m == "lea" and o.startswith("esp,"):
        mo = re.search(r"esp \+ (0x[0-9a-f]+)", o)
        if mo: return int(mo.group(1), 16)
    return 0

def succ(rva, i):
    nxt = rva + i.size; t = C.target_of(i); m = i.mnemonic
    tgt = (t - C.IB) if t is not None else None
    if m == "jmp": return [tgt] if tgt is not None else [nxt]
    if m.startswith("j"): return [nxt, tgt] if tgt is not None else [nxt]
    if m in ("ret","leave"): return []
    return [nxt]

def run():
    insns = {}; rva = LO
    while rva < HI:
        i = C.dis_at(rva, 15)
        if i is None: break
        insns[rva] = i; rva += i.size
    esp = {}; done = set(); work = [(LO, 0)]
    while work:
        r, e = work.pop()
        if (r, e) in done or r not in insns: continue
        done.add((r, e)); esp.setdefault(r, set()).add(e)
        ne = e + delta(insns[r])
        for s in succ(r, insns[r]):
            if s is not None and LO <= s < HI: work.append((s, ne))
    return insns, esp

def slot_rel(insns, esp, a, out_base):
    outs = set()
    for m in re.finditer(r"esp \+ (0x[0-9a-f]+)", insns[a].op_str):
        k = int(m.group(1), 16)
        for e in esp[a]: outs.add(e + k - out_base)
    return outs

def main():
    insns, esp = run()
    out_base = sorted(esp[0x2310DA])[0] + 0x14
    rows = ["RVA\tMNEMONIC\tOP_STR\tESP_SET\tSLOT_ABS\tREL_TO_OUT"]
    for a in sorted(esp):
        for m in re.finditer(r"esp \+ (0x[0-9a-f]+)", insns[a].op_str):
            k = int(m.group(1), 16)
            for e in sorted(esp[a]):
                rows.append("%08x\t%s\t%s\t%s\t%d\t%d" % (
                    a, insns[a].mnemonic, insns[a].op_str, sorted(esp[a]), e + k, (e + k) - out_base))
    p = os.path.join(C.EV, "caller_frame_model.tsv")
    open(p, "w", encoding="utf-8", newline="").write("\n".join(rows) + "\n")
    print("out base (abs slot) =", out_base, " reachable_insns =", len(esp))
    for a, lbl in [(0x2310DA,"out base"),(0x2310DF,"this=&D"),(0x231112,"D+0 socket"),
                   (0x231129,"D+4 event"),(0x231139,"D+0xC buf"),(0x231171,"reader1"),
                   (0x231175,"reader2")]:
        print("  %-16s %08x rel=%s" % (lbl, a, sorted(slot_rel(insns, esp, a, out_base))))
    print("wrote", p)

if __name__ == "__main__":
    main()
