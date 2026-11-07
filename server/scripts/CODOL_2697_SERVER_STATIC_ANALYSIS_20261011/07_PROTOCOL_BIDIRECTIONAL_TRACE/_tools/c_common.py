# c_common.py - client-side static analysis helpers (Phase E, static only)
import json, io, sys, bisect, struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CLIENT_CAND = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
CLIENT_EXE  = r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
CLIENT_BASE = r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetailBase.dll"
ROOM_DLL    = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll"
LOOP_DLL    = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll"
EDIR = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE"

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = True

class Image:
    def __init__(self, path, name=None):
        self.path = path
        self.name = name or path.rsplit("\\", 1)[-1]
        self.data = open(path, "rb").read()
        self.pe = pefile.PE(data=self.data, fast_load=True)
        self.ib = self.pe.OPTIONAL_HEADER.ImageBase
        self.sections = []
        for s in self.pe.sections:
            nm = s.Name.rstrip(b"\x00").decode("latin1")
            self.sections.append((nm, s.VirtualAddress, s.Misc_VirtualSize,
                                  s.PointerToRawData, s.SizeOfRawData))
    def sec_of(self, rva):
        for nm, va, vsz, ptr, rsz in self.sections:
            if rsz == 0:
                continue
            if va <= rva < va + rsz:
                return (nm, va, vsz, ptr, rsz)
        return None
    def read_rva(self, rva, n):
        s = self.sec_of(rva)
        if not s: return b""
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        return self.data[off:off+n]
    def cstr(self, rva, maxlen=512):
        s = self.sec_of(rva)
        if not s: return None
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        end = self.data.find(b"\x00", off, off+maxlen)
        if end < 0:
            end = off+maxlen
        return self.data[off:end].decode("latin1", "replace")
    def disasm(self, rva, end_rva=None, count=None):
        s = self.sec_of(rva)
        if not s: return []
        nm, va, vsz, ptr, rsz = s
        off = ptr + (rva - va)
        if end_rva is None:
            end_rva = rva + (0x2000 if count is None else count*16)
        code = self.data[off:off+(end_rva-rva)]
        out = []
        for ins in _md.disasm(code, self.ib+rva):
            out.append(ins)
            if ins.address - self.ib >= end_rva-1:
                break
        return out

def load(path=CLIENT_CAND, name=None):
    return Image(path, name)

def show(im, rva, end_rva=None, n=None):
    for ins in im.disasm(rva, end_rva=end_rva, count=n):
        print("  %08x  %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))
