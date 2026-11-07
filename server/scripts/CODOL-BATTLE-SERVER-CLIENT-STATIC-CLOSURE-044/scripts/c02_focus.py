# -*- coding: utf-8 -*-
"""044 Phase C focus: (1) netbuffer-region jump tables, (2) reg-indirect calls fed by
text-address immediates near the decoders. READ-ONLY."""
import _common as c, os, struct, json, collections

IB = c.IMG_IB
IMG = c._bi
X86 = c.capstone.x86
sec0 = c.IMG_SECS[0]
PLO = sec0["raw"]; PHI = min(sec0["raw"] + sec0["rsize"], c.IMG_LEN)

out = []
def P(s=""): out.append(s)

# decode helper for a single instruction at rva
def one(rva):
    return next(c.md.disasm(IMG[rva:rva+15], IB + rva), None)

# ---------- 1. netbuffer-region jump tables ----------
bases = [0x87228c,0x872c28,0x878598,0x8785a8,0x88528c,0x8853ec,0x8855fc,
         0x885b94,0x885e58,0x886be4,0x886c5c,0x8888bc]
P("## netbuffer-region jump tables (bases found by [reg*4+disp] scan)")
for b in bases:
    vals = []
    for k in range(0, 40):
        v = c.idword(b + 4*k)
        if v is None:
            break
        vals.append(v)
        if not (IB + PLO <= v < IB + PHI):
            break
    P("  base=%08x  n=%d" % (b, len(vals)))
    for k, v in enumerate(vals):
        P("      [%08x] = %08x" % (b + 4*k, v))
    P("")

# ---------- 2. reg-indirect call/jmp whose reg was loaded with a netbuffer-range address ----------
NB_LO, NB_HI = 0x879000, 0x880000   # netfield / netbuffer family
P("## 'mov reg, <imm in 0x879000..0x880000>' followed by an indirect call/jmp on that reg")
hits = []
i = PLO
regmap = {}
REGS = {0xB8:"eax",0xB9:"ecx",0xBA:"edx",0xBB:"ebx",0xBC:"esp",0xBD:"ebp",0xBE:"esi",0xBF:"edi"}
while i < PHI - 5:
    b0 = IMG[i]
    if b0 in REGS:
        v = struct.unpack("<I", IMG[i+1:i+5])[0]
        if IB + NB_LO <= v < IB + NB_HI:
            # look ahead <=12 instructions for call/jmp on that register
            j = i + 5
            steps = 0
            reg = REGS[b0]
            while j < PHI and steps < 12:
                ins = one(j)
                if ins is None: break
                if ins.mnemonic in ("call","jmp") and ins.op_str == reg:
                    hits.append(dict(mov_rva=i, addr_va=v, call_rva=j, mn=ins.mnemonic, reg=reg))
                    break
                if ins.mnemonic in ("call","jmp","ret") or ins.mnemonic.startswith("j"):
                    # stop at any prior control transfer other than a simple non-targeting one
                    if not (ins.mnemonic=="call" and ins.op_str.startswith("0x")):
                        break
                j += ins.size; steps += 1
        i += 5
    else:
        i += 1
for h in hits:
    P("   mov %s, %08x @%08x  ->  %s %s @%08x" % (h["reg"], h["addr_va"], h["mov_rva"],
        h["mn"], h["reg"], h["call_rva"]))
P("   total = %d" % len(hits))
P("")

# ---------- 3. any register-indirect call/jmp anywhere in 0x87C000..0x87F000 (decoder region) ----------
P("## register/indirect CALL/JMP inside the netbuffer decoder region 0x87C000..0x87F000")
region = []
i = 0x87C000
while i < 0x87F000:
    ins = one(i)
    if ins is None:
        i += 1; continue
    if ins.mnemonic in ("call","jmp") and not ins.op_str.startswith("0x"):
        region.append("%08x  %s %s" % (i, ins.mnemonic, ins.op_str))
    i += ins.size
for r in region:
    P("   " + r)
P("   total = %d" % len(region))
P("")

# ---------- 4. are the decoder entries referenced as *relative* displacement from anywhere? already E8 only ----------
P("## recap: E8 direct-call sites into decoder#1 / decoder#2 (whole present text)")
for tgt, nm in ((0x87C110,"decoder#1"), (0x87D5A0,"decoder#2")):
    sites = []
    i = PLO
    while i < PHI - 5:
        if IMG[i] == 0xE8 and (i == PLO or True):
            rel = int.from_bytes(IMG[i+1:i+5], "little", signed=True)
            if IB + i + 5 + rel == IB + tgt:
                sites.append(i)
            i += 1
        else:
            i += 1
    P("   %s: %s" % (nm, ["%x" % s for s in sites]))
P("")

# ---------- 5. E9 tail-jmp into decoders (jmp rel32) ----------
P("## E9 direct-jmp sites into the audited entries (tail-call evidence)")
FOC = {0x87C110:"decoder#1",0x87D5A0:"decoder#2",0x87BE00:"read-primitive",
       0x87BA50:"read-thunk",0x87A890:"len-writer",0x85E6F0:"TQOS"}
res = {}
for tgt, nm in FOC.items():
    s = []
    i = PLO
    while i < PHI - 5:
        if IMG[i] == 0xE9:
            rel = int.from_bytes(IMG[i+1:i+5], "little", signed=True)
            if IB + i + 5 + rel == IB + tgt:
                s.append(i)
            i += 1
        else:
            i += 1
    res[nm] = ["%x" % x for x in s]
    P("   %-14s %s" % (nm, res[nm]))
c.w(os.path.join(c.EV, "c02_focus.json"), json.dumps(dict(nb_jumptables=bases, reg_indirect=hits,
                                                          region_indirect=region, e9=res), indent=1))
c.w(os.path.join(c.EV, "c02_focus.txt"), "\n".join(out))
print("\n".join(out))