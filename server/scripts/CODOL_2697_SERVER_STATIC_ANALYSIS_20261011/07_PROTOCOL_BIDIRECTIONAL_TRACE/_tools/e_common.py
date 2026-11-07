# e_common.py - shared helpers for phase E bidirectional trace (static only)
import json, io, sys, bisect, re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011"
DATA = ROOT + r"\_data"
EDATA = ROOT + r"\07_PROTOCOL_BIDIRECTIONAL_TRACE\_data"
SRV = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
CLI = r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = True

class Bin:
    def __init__(self, path, syms_json=None):
        self.path = path
        self.data = open(path, "rb").read()
        self.pe = pefile.PE(data=self.data, fast_load=True)
        self.ib = self.pe.OPTIONAL_HEADER.ImageBase
        self.syms = {}
        self.sym_rvas = []
        if syms_json:
            j = json.load(open(syms_json, encoding="utf-8"))
            for s in j["symbols"]:
                self.syms.setdefault(s["name"], s)
            self.sym_rvas = sorted(set(v["rva"] for v in self.syms.values()))
        self.sections = []
        for s in self.pe.sections:
            nm = s.Name.rstrip(b"\x00").decode("latin1")
            self.sections.append((nm, s.VirtualAddress, s.Misc_VirtualSize,
                                  s.PointerToRawData, s.SizeOfRawData))
    def sec_of(self, rva):
        for nm, va, vsz, ptr, rsz in self.sections:
            if va <= rva < va + max(vsz, rsz):
                return (nm, va, vsz, ptr, rsz)
        return None
    def read_rva(self, rva, n):
        s = self.sec_of(rva)
        if not s:
            return b""
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        return self.data[off:off + n]
    def cstr(self, rva, maxlen=256):
        s = self.sec_of(rva)
        if not s:
            return None
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        end = self.data.find(b"\x00", off, off + maxlen)
        if end < 0:
            end = off + maxlen
        try:
            return self.data[off:end].decode("latin1")
        except Exception:
            return None
    def func_bounds(self, rva):
        # returns (start,end) using nearest symbol starts as boundaries
        if not self.sym_rvas:
            return (rva, rva + 0x4000)
        i = bisect.bisect_right(self.sym_rvas, rva) - 1
        if i < 0:
            return (rva, rva + 0x4000)
        start = self.sym_rvas[i]
        nxt = None
        for j in range(i + 1, len(self.sym_rvas)):
            if self.sym_rvas[j] > start:
                nxt = self.sym_rvas[j]
                break
        if nxt is None:
            nxt = start + 0x8000
        if nxt - start > 0x20000:
            nxt = start + 0x20000
        return (start, nxt)
    def disasm(self, rva, count=None, end_rva=None):
        s = self.sec_of(rva)
        if not s:
            return []
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        if end_rva is None:
            end_rva = rva + (0x4000 if count is None else count * 16)
        lim = self.sec_of(end_rva)
        span = end_rva - rva
        code = self.data[off:off + span]
        out = []
        for ins in _md.disasm(code, self.ib + rva):
            out.append(ins)
            if ins.address - self.ib >= end_rva - 1:
                break
        return out
    def name_at(self, rva):
        return self.syms_by_rva.get(rva, "")
    def owner(self, rva):
        if not self.sym_rvas:
            return ""
        i = bisect.bisect_right(self.sym_rvas, rva) - 1
        if i < 0:
            return ""
        return self.sym_rva_name.get(self.sym_rvas[i], "")

def load_bin(path, syms_json=None):
    b = Bin(path, syms_json)
    b.syms_by_rva = {}
    b.sym_rva_name = {}
    for k, v in b.syms.items():
        b.syms_by_rva.setdefault(v["rva"], k)
        b.sym_rva_name.setdefault(v["rva"], k)
    return b

def annotate(b, ins):
    if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
        t = int(ins.op_str, 16) - b.ib
        nm = b.syms_by_rva.get(t, "")
        if nm:
            return "  ; -> %s" % nm
    return ""

def show(b, rva, end_rva=None, n=None, resolve_mem=False):
    for ins in b.disasm(rva, count=n, end_rva=end_rva):
        cm = annotate(b, ins)
        print("  %08x  %-9s %s%s" % (ins.address, ins.mnemonic, ins.op_str, cm))
