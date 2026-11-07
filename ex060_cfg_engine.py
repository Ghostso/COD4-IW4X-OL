# EX-060 static CFG recovery engine for iips.dll.
# Read only. No patching, no hooks, no runtime modification.
import struct
from collections import OrderedDict, defaultdict

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
    X86_GRP_JUMP,
    X86_GRP_CALL,
    X86_GRP_RET,
    X86_REG_ESP,
    X86_REG_EBP,
    X86_REG_EIP,
)

COND_JMP = {
    "jo", "jno", "js", "jns", "je", "jz", "jne", "jnz", "jb", "jnae", "jc",
    "jnb", "jae", "jnc", "jbe", "jna", "ja", "jnbe", "jl", "jnge", "jge",
    "jnl", "jle", "jng", "jg", "jnle", "jp", "jpe", "jnp", "jpo", "jcxz",
    "jecxz", "jecxz",
}


class Function:
    """Recursive-descent recovered function."""

    def __init__(self, img, entry, name=None, extra_entries=()):
        self.img = img
        self.entry = entry
        self.name = name or ("sub_%X" % entry)
        self.insns = OrderedDict()      # rva -> insn obj
        self.bbs = OrderedDict()        # rva -> BasicBlock
        self.edges = []                 # (src_rva, dst_rva, kind)
        self.calls = []                 # dict per call site
        self.extra_entries = list(extra_entries)

    # ---------------- discovery ----------------
    def run(self, max_insns=20000):
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        md.detail = True

        todo = [self.entry] + self.extra_entries
        seen_starts = set()
        while todo:
            start = todo.pop()
            if start in seen_starts:
                continue
            seen_starts.add(start)
            if not self.img.is_code(start):
                continue
            rva = start
            while True:
                if rva in self.insns:
                    break
                code = self.img.read(rva, 16)
                insn = next(md.disasm(code, self.img.base + rva), None)
                if insn is None:
                    break
                self.insns[rva] = insn
                if len(self.insns) > max_insns:
                    raise RuntimeError("too many instructions")
                m = insn.mnemonic
                # stop conditions
                if m == "ret" or m.startswith("retn") or m == "retf":
                    break
                if m in ("int3", "int", "hlt", "ud2"):
                    break
                if m.startswith("jmp"):
                    # direct or indirect
                    if insn.operands and insn.operands[0].type == X86_OP_IMM:
                        tgt = insn.operands[0].imm - self.img.base
                        if self.img.is_code(tgt):
                            todo.append(tgt)
                    break
                if m.startswith("call") or m == "call":
                    pass
                if m in COND_JMP or m.startswith("j") and m not in ("jmp",):
                    if insn.operands and insn.operands[0].type == X86_OP_IMM:
                        tgt = insn.operands[0].imm - self.img.base
                        if self.img.is_code(tgt):
                            todo.append(tgt)
                    rva = insn.address - self.img.base + insn.size
                    continue
                rva = insn.address - self.img.base + insn.size
        return self

    # ---------------- basic blocks ----------------
    def build_bbs(self):
        starts = set()
        starts.add(self.entry)
        for e in self.extra_entries:
            starts.add(e)
        for rva, insn in self.insns.items():
            m = insn.mnemonic
            if m.startswith("j") or m == "jmp" or m in COND_JMP:
                for op in insn.operands:
                    if op.type == X86_OP_IMM and self.img.is_code(op.imm - self.img.base):
                        starts.add(op.imm - self.img.base)
                nxt = rva + insn.size
                if self.img.is_code(nxt):
                    starts.add(nxt)
        starts = {s for s in starts if s in self.insns}

        # leader selection: entry, jump targets, fallthroughs after
        # terminators, call fallthroughs, and blocks start after a branch.
        leaders = set(starts)
        leaders.add(self.entry)
        ordered = sorted(self.insns.keys())
        for s in starts:
            pass
        # also: any address that is not the sequential next of the previous
        # recovered instruction is a leader
        prev = None
        for rva in ordered:
            if prev is not None:
                prev_insn = self.insns[prev]
                if prev + prev_insn.size != rva:
                    leaders.add(rva)
            prev = rva
        # instruction after any branch/call/ret that is present in insns
        for rva, insn in self.insns.items():
            nxt = rva + insn.size
            if self.img.is_code(nxt) and nxt in self.insns:
                if insn.mnemonic.startswith("j"):
                    leaders.add(nxt)

        leaders = sorted(
            l for l in leaders if l in self.insns
        )
        self.bbs = OrderedDict()
        for i, l in enumerate(leaders):
            end_limit = leaders[i + 1] if i + 1 < len(leaders) else None
            b = BasicBlock(l)
            rva = l
            while True:
                if end_limit is not None and rva == end_limit:
                    break
                insn = self.insns.get(rva)
                if insn is None:
                    break
                b.insns.append(rva)
                m = insn.mnemonic
                term = (
                    m == "ret"
                    or m.startswith("ret")
                    or m.startswith("j")
                    or m in ("int3", "int", "hlt", "ud2")
                )
                rva = rva + insn.size
                if term:
                    break
            self.bbs[l] = b
        for b in self.bbs.values():
            b.finalize(self)
        return self


class BasicBlock:
    def __init__(self, start):
        self.start = start
        self.insns = []
        self.succ = []
        self.pred = []
        self.kind = "normal"   # normal|ret|jmp|cond|indirect
        self.term = None       # terminating insn object

    def finalize(self, fn):
        last_rva = self.insns[-1]
        insn = fn.insns[last_rva]
        self.term = insn
        m = insn.mnemonic
        if m.startswith("ret"):
            self.kind = "ret"
        elif m == "jmp":
            op = insn.operands[0] if insn.operands else None
            if op is not None and op.type == X86_OP_IMM:
                self.kind = "jmp"
                self.succ.append((op.imm - fn.img.base, "jmp"))
            else:
                self.kind = "indirect"
        elif m in COND_JMP or (m.startswith("j") and m != "jmp"):
            self.kind = "cond"
            op = insn.operands[0] if insn.operands else None
            if op is not None and op.type == X86_OP_IMM:
                self.succ.append((op.imm - fn.img.base, "taken"))
            ft = last_rva + insn.size
            if fn.img.is_code(ft):
                self.succ.append((ft, "fallthrough"))
        else:
            self.kind = "normal"
            ft = last_rva + insn.size
            if fn.img.is_code(ft):
                self.succ.append((ft, "fallthrough"))


def callsite_info(fn, rva, insn, img, imports):
    """Classify a call instruction."""
    info = dict(rva=rva, insn="%s %s" % (insn.mnemonic, insn.op_str))
    if not insn.operands:
        info["kind"] = "unknown"
        return info
    op = insn.operands[0]
    if op.type == X86_OP_IMM:
        info["kind"] = "direct"
        info["target_rva"] = op.imm - img.base
    elif op.type == X86_OP_MEM:
        if op.mem.base == 0 and op.mem.index == 0:
            slot = op.mem.disp - img.base
            info["kind"] = "iat"
            info["slot_rva"] = slot
            if slot in imports:
                info["dll"], info["import"] = imports[slot]
        else:
            info["kind"] = "indirect-mem"
            info["mem"] = "%s" % insn.op_str
    else:
        info["kind"] = "indirect-reg"
        info["reg"] = insn.reg_name(op.reg) if op.type == X86_OP_REG else "?"
    return info
