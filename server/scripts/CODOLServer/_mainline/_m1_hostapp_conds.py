# -*- coding: utf-8 -*-
"""
_m1_hostapp_conds.py - mainline: pin down the exact preconditions under which
IIPSHostApp / IIPSHost.dll (a) writes IIPS\\HostPid and (b) calls CreateNamedPipeA.

Read-only static analysis (pefile + capstone). Launches nothing.

Known from earlier work (IIPS_PIPELINE_FULL_REVERSE.md):
  IIPSHost.dll  CreateNamedPipeA call site @ 0x1000DBD1
  IIPSHost.dll  pipe name built @ 0x1000DB37  ("\\.\Pipe\" + MD5(lower(url)))
  IIPSHost.dll  ResourceLoader::Start() logs:
      "[ResourceLoader::Start()][connect to policy server start][policySvrAddr %s]"
      "... end / failed"
      "[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe start/succeed/failed]"

Goal: find, in code order, the branch that gates pipe creation, and find who
writes the HostPid file.
"""
import os
import re
import struct
import sys

import capstone
import pefile

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
HOST = os.path.join(ROOT, "COD OL", "IIPS", "IIPSHost.dll")
APP = os.path.join(ROOT, "COD OL", "IIPS", "IIPSHostApp.exe")

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


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

    def off(self, va):
        return self.pe.get_offset_from_rva(va - self.ib)

    def va_of_fileoff(self, off):
        for s in self.pe.sections:
            if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                return self.ib + s.VirtualAddress + (off - s.PointerToRawData)
        return None

    def name(self, va):
        return self.iat.get(va, "")

    def dis(self, va, length, label="", maxn=200):
        print("---- %s  0x%08X (+%d bytes) ----" % (label, va, length))
        o = self.off(va)
        n = 0
        for ins in MD.disasm(self.blob[o:o + length], va):
            extra = ""
            m = re.search(r"\[(0x[0-9a-fA-F]+)\]", ins.op_str)
            if m:
                nm = self.name(int(m.group(1), 16))
                if nm:
                    extra = "   ; " + nm
            print("  %08X  %-22s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
            n += 1
            if n >= maxn:
                print("  ... (truncated)")
                break


def part1_string_hunt(pe):
    title("PART 1  HostPid / policy / pipe strings and their cross references")
    probes = [
        b"HostPid", b"iipslaunch", b"/mode", b"IIPSPolicySvrInfo",
        b"connect to policy server", b"listen to pipe", b"CreateNamedPipe",
        b"MakeSureDirectoryPathExists", b"IIPSHostApp", b"HostPidPath",
        b"policySvrAddr", b"BusinessID", b"HeartbeatInterval",
        b"IIPSHost.ListenThread", b"IIPSHostApp::Start", b"[IIPSHost.ListenThread()]",
    ]
    for p in probes:
        hits = find_all(pe.blob, p)
        if not hits:
            print("  %-30s : none" % p.decode("latin1"))
            continue
        desc = []
        for h in hits[:8]:
            va = pe.va_of_fileoff(h)
            desc.append("file 0x%06X VA %s" % (
                h, ("0x%08X" % va) if va else "-"))
        print("  %-30s : %d  %s" % (p.decode("latin1"), len(hits), " | ".join(desc)))


def part2_xrefs_into_code(pe, needle, label):
    title("PART 2  code references to %s" % label)
    hits = find_all(pe.blob, needle)
    if not hits:
        print("  string not present")
        return
    text = [s for s in pe.pe.sections if b".text" in s.Name][0]
    tlo = pe.ib + text.VirtualAddress
    thi = tlo + text.SizeOfRawData
    for h in hits:
        va = pe.va_of_fileoff(h)
        print("")
        print("  string %r  file 0x%06X  VA %s" % (
            needle[:40].decode("latin1"), h, ("0x%08X" % va) if va else "-"))
        if not va:
            continue
        pat = struct.pack("<I", va)
        fmt_pat = struct.pack("<I", va) + b"\x00\x00\x00\x00"
        refs = [(r, "va") for r in find_all(pe.blob, pat)]
        fmtrefs = find_all(pe.blob, fmt_pat)
        print("    raw dword refs: %d   dword-in-push-imm style: %d"
              % (len(refs), len(fmtrefs)))
        for r, _ in refs[:12]:
            rva = pe.va_of_fileoff(r)
            where = "CODE" if (rva and tlo <= rva < thi) else "data"
            print("      ref file 0x%06X  VA %s  (%s)" % (
                r, ("0x%08X" % rva) if rva else "-", where))
            if rva and tlo <= rva < thi:
                start = max(tlo, rva - 0x60)
                pe.dis(start, rva - start + 0x30, "xref context")


def part3_pipe_site(pe):
    title("PART 3  CreateNamedPipeA call site and the branch that guards it")
    # locate the IAT slot for CreateNamedPipeA
    slot = None
    for addr, nm in pe.iat.items():
        if nm == "CreateNamedPipeA":
            slot = addr
    print("  IAT slot CreateNamedPipeA = %s" % (("0x%08X" % slot) if slot else "NOT IMPORTED"))
    if slot:
        pat = struct.pack("<I", slot)
        refs = find_all(pe.blob, pat)
        print("  call sites (dword refs to IAT slot): %d" % len(refs))
        for r in refs[:6]:
            va = pe.va_of_fileoff(r)
            print("    ref file 0x%06X VA %s" % (r, ("0x%08X" % va) if va else "-"))
    # disassemble the known region around 0x1000DB00..0x1000DD20
    pe.dis(0x1000DA80, 0x2A0, "around known CreateNamedPipeA site 0x1000DBD1")


def part4_waittargets(pe):
    title("PART 4  ListenThread and WaitForMultipleObjects: what is waited on")
    for nm in ("WaitForMultipleObjects", "WaitForSingleObject", "ConnectNamedPipe",
               "CreateNamedPipeA", "CreateFileA", "CreateFileW", "WriteFile"):
        slot = [a for a, n in pe.iat.items() if n == nm]
        if not slot:
            print("  %-26s not imported" % nm)
            continue
        for s in slot:
            refs = find_all(pe.blob, struct.pack("<I", s))
            code_refs = []
            for r in refs:
                va = pe.va_of_fileoff(r)
                if va is not None:
                    code_refs.append(va)
            print("  %-26s slot 0x%08X  refs %d  %s" % (
                nm, s, len(code_refs),
                " ".join("0x%08X" % v for v in code_refs[:10])))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    pe_h = Pe(HOST)
    pe_a = Pe(APP)
    print("IIPSHost.dll  base=0x%08X size=%d" % (pe_h.ib, len(pe_h.blob)))
    print("IIPSHostApp.exe base=0x%08X size=%d" % (pe_a.ib, len(pe_a.blob)))

    if which in ("all", "1"):
        part1_string_hunt(pe_h)
        print("")
        part1_string_hunt(pe_a)
    if which in ("all", "2"):
        part2_xrefs_into_code(pe_h, b"HostPid", "HostPid")
        part2_xrefs_into_code(pe_h, b"connect to policy server", "policy-server log")
        part2_xrefs_into_code(pe_h, b"listen to pipe", "listen-to-pipe log")
    if which in ("all", "3"):
        part3_pipe_site(pe_h)
    if which in ("all", "4"):
        part4_waittargets(pe_h)


if __name__ == "__main__":
    main()
