# -*- coding: utf-8 -*-
"""
_m3_resourceloader.py - mainline: disassemble IIPSHost.dll ResourceLoader::Start
(the function containing the policy-server log refs and the listen-to-pipe refs)
and trace its callees up to the named-pipe creation.

Key VAs found by _m2:
  policy "start"   log ref  0x10025A56
  policy "failed"  log ref  0x10025AA6
  policy "end"     log ref  0x10025ACC
  pipe "start"     log ref  0x10026861
  pipe "failed"    log ref  0x100268B5
  pipe "succeed"   log ref  0x100268DC
Read-only.
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

    def string_at(self, va, limit=160):
        try:
            o = self.off(va)
        except Exception:
            return ""
        if o < 0 or o >= len(self.blob):
            return ""
        out = []
        for b in self.blob[o:o + limit]:
            if b == 0:
                break
            if 32 <= b < 127:
                out.append(chr(b))
            else:
                return ""
        return "".join(out) if len(out) >= 3 else ""

    def dis(self, va, length, label="", maxn=400):
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
                    s = self.string_at(int(ins.op_str, 16))
                    if s:
                        extra += "   ; -> %r" % s
                except Exception:
                    pass
            # immediate push of a string pointer
            if ins.mnemonic == "push" and re.match(r"^0x1[0-9a-f]{7}$", ins.op_str):
                s = self.string_at(int(ins.op_str, 16))
                if s:
                    extra = "   ; str=%r" % s
            print("  %08X  %-20s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, extra))
            n += 1
            if n >= maxn:
                print("  ... truncated")
                break

    def find_func_start(self, va, back=0x400):
        """walk back for a prologue or a preceding ret/int3 padding run"""
        o = self.off(va)
        lo = max(self.off(self.tlo), o - back)
        seg = self.blob[lo:o]
        # find last occurrence of 'ret' followed by padding
        best = None
        for m in re.finditer(rb"\xc3(\xcc{2,}|\x90{2,})", seg):
            best = m.end()
        if best is not None:
            return self.va_of_fileoff(lo + best)
        # fallback: prologue
        for m in re.finditer(rb"\x55\x8b\xec|\x6a\xff\x68|\x81\xec", seg[::-1]):
            pass
        return None

    def callers_of(self, target):
        hits = []
        for m in re.finditer(b"\xE8....", self.blob):
            off = m.start()
            va = self.va_of_fileoff(off)
            if va is None or not (self.tlo <= va < self.thi):
                continue
            rel = struct.unpack_from("<i", self.blob, off + 1)[0]
            if va + 5 + rel == target:
                hits.append(va)
        return hits


def part1_start_fn(pe):
    title("PART 1  the function containing the ResourceLoader policy/pipe logs")
    start = pe.find_func_start(0x10025A56, 0x600)
    print("  nearest function start below 0x10025A56: %s" % (
        ("0x%08X" % start) if start else "UNKNOWN"))
    lo = start if start else 0x10025800
    pe.dis(lo, 0x100268E0 - lo + 0x60, "ResourceLoader::Start candidate", 500)


def main():
    pe = Pe(HOST)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("IIPSHost.dll base=0x%08X" % pe.ib)
    if which in ("all", "1"):
        part1_start_fn(pe)


if __name__ == "__main__":
    main()
