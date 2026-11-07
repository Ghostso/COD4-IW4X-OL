# -*- coding: utf-8 -*-
"""
_m2_hostapp_deps.py - mainline: resolve what the pre-pipe gate function
IIPSHost.dll:0x1000F370 actually does, and who calls it.

Read-only. Uses pefile + capstone.
"""
import os
import re
import struct
import sys

import capstone
import pefile

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
HOST = os.path.join(ROOT, "COD OL", "IIPS", "IIPSHost.dll")

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def find_all(blob, needle):
    out, s = [], 0
    while True:
        i = blob.find(needle, s)
        if i < 0:
            return out
        out.append(i)
        s = i + 1


def title(t):
    print("")
    print("#" * 78)
    print("# " + t)
    print("#" * 78)


class Pe(object):
    def __init__(self, path):
        self.path = path
        self.pe = pefile.PE(path, fast_load=True)
        self.pe.parse_data_directories()
        self.blob = load(path)
        self.ib = self.pe.OPTIONAL_HEADER.ImageBase
        self.iat = {}
        if hasattr(self.pe, "DIRECTORY_ENTRY_IMPORT"):
            for imp in self.pe.DIRECTORY_ENTRY_IMPORT:
                for f in imp.imports:
                    if f.name:
                        self.iat[f.address] = f.name.decode("latin1")
        self.text = [s for s in self.pe.sections if b".text" in s.Name][0]
        self.tlo = self.ib + self.text.VirtualAddress
        self.thi = self.tlo + self.text.SizeOfRawData

    def off(self, va):
        return self.pe.get_offset_from_rva(va - self.ib)

    def va_of_fileoff(self, off):
        for s in self.pe.sections:
            if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                return self.ib + s.VirtualAddress + (off - s.PointerToRawData)
        return None

    def name(self, va):
        return self.iat.get(va, "")

    def dis(self, va, length, label="", maxn=300):
        print("---- %s  0x%08X (+%d) ----" % (label, va, length))
        o = self.off(va)
        n = 0
        for ins in MD.disasm(self.blob[o:o + length], va):
            extra = ""
            m = re.search(r"\[(0x[0-9a-fA-F]+)\]", ins.op_str)
            if m:
                nm = self.name(int(m.group(1), 16))
                if nm:
                    extra = "   ; " + nm
            if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
                try:
                    dst = int(ins.op_str, 16)
                    s = self.string_at(dst)
                    if s:
                        extra += "   ; -> %r" % s
                except Exception:
                    pass
            print("  %08X  %-20s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
            n += 1
            if n >= maxn:
                print("  ... truncated")
                break

    def string_at(self, va, limit=120):
        try:
            o = self.off(va)
        except Exception:
            return ""
        out = []
        for b in self.blob[o:o + limit]:
            if b == 0:
                break
            if 32 <= b < 127:
                out.append(chr(b))
            else:
                return ""
        if len(out) >= 3:
            return "".join(out)
        return ""

    def callers_of(self, target):
        hits = []
        for m in re.finditer(b"\xE8....", self.blob):
            off = m.start()
            va = self.va_of_fileoff(off)
            if va is None or not (self.tlo <= va < self.thi):
                continue
            rel = struct.unpack_from("<i", self.blob, off + 1)[0]
            dst = va + 5 + rel
            if dst == target:
                hits.append(va)
        return hits

    def refs_to_string(self, s):
        hits = find_all(self.blob, s)
        out = []
        for h in hits:
            va = self.va_of_fileoff(h)
            if va is None:
                continue
            for r in find_all(self.blob, struct.pack("<I", va)):
                rva = self.va_of_fileoff(r)
                if rva is not None:
                    out.append((s, va, rva))
        return out


def part1_gate(pe):
    title("PART 1  gate function 0x1000F370 (called before any named pipe is created)")
    # 0x1000F370 .. 0x1000F5A0 (next known function starts there)
    pe.dis(0x1000F370, 0x230, "gate 0x1000F370", 400)


def part2_callers(pe):
    title("PART 2  callers of gate 0x1000F370")
    callers = pe.callers_of(0x1000F370)
    print("  direct callers: %d %s" % (len(callers), " ".join("0x%08X" % v for v in callers)))
    for c in callers[:6]:
        start = max(pe.tlo, c - 0x80)
        pe.dis(start, c - start + 0x40, "caller context", 80)


def part3_gate_strings(pe):
    title("PART 3  strings/data referenced by the gate function and its callees")
    # collect direct absolute refs and call targets in the gate window
    start, end = 0x1000F370, 0x1000F5A0
    o0, o1 = pe.off(start), pe.off(end)
    blob = pe.blob[o0:o1]
    targets = set()
    for ins in MD.disasm(blob, start):
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            try:
                targets.add(int(ins.op_str, 16))
            except Exception:
                pass
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0:
                targets.add(op.mem.disp & 0xFFFFFFFF)
    print("  direct branch/data targets in gate:")
    for t in sorted(targets):
        s = pe.string_at(t)
        nm = pe.name(t)
        print("    0x%08X  %s%s" % (
            t, ("str=%r " % s) if s else "", ("import=%s" % nm) if nm else ""))
    print("")
    print("  known log strings and xrefs:")
    for s in (b"[ResourceLoader::Start()][connect to policy server start][policySvrAddr %s]",
              b"[ResourceLoader::Start()][connect to policy server end][policySvrAddr %s]",
              b"[ResourceLoader::Start()][connect to policy server failed][policySvrAddr %s]",
              b"[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe start]",
              b"[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe succeed]",
              b"[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe failed]"):
        refs = pe.refs_to_string(s)
        print("   %r" % s)
        if not refs:
            print("      (no direct dword xref)")
        for _, sva, rva in refs:
            print("      str VA 0x%08X  ref VA 0x%08X" % (sva, rva))


def part4_imports(pe):
    title("PART 4  imports most likely involved in the gate")
    wanted = (
        "WSAStartup", "socket", "connect", "send", "recv", "closesocket",
        "gethostbyname", "getaddrinfo", "inet_addr", "GetPrivateProfileStringA",
        "GetPrivateProfileIntA", "CreateFileW", "ReadFile", "CreateDirectoryW",
        "CreateProcessA", "CreateProcessW", "GetModuleFileNameA", "GetModuleFileNameW",
    )
    for nm in wanted:
        slots = [a for a, n in pe.iat.items() if n == nm]
        if not slots:
            continue
        for slot in slots:
            refs = []
            for r in find_all(pe.blob, struct.pack("<I", slot)):
                va = pe.va_of_fileoff(r)
                if va is not None and pe.tlo <= va < pe.thi:
                    refs.append(va)
            print("  %-28s slot 0x%08X  code refs %d  %s" % (
                nm, slot, len(refs), " ".join("0x%08X" % v for v in refs[:12])))


def main():
    pe = Pe(HOST)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("IIPSHost.dll base=0x%08X size=%d" % (pe.ib, len(pe.blob)))
    if which in ("all", "1"):
        part1_gate(pe)
    if which in ("all", "2"):
        part2_callers(pe)
    if which in ("all", "3"):
        part3_gate_strings(pe)
    if which in ("all", "4"):
        part4_imports(pe)


if __name__ == "__main__":
    main()
