# EX-060 static IIPS CFG closure.
# Read-only analysis of iips.dll. No target modification.
import hashlib
import json
import os
import re
import struct
import sys
from collections import OrderedDict, defaultdict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

DLL = os.path.join("工具", "EX035_DIR", "IIPS", "iips.dll")
IMAGE_BASE = 0x10000000  # placeholder, replaced by real PE base

OUT = OrderedDict()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Image:
    def __init__(self, path):
        self.path = path
        self.pe = pefile.PE(path)
        self.data = open(path, "rb").read()
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.sections = []
        for s in self.pe.sections:
            self.sections.append(
                dict(
                    name=s.Name.decode(errors="replace").rstrip("\x00"),
                    va=s.VirtualAddress,
                    vsize=s.Misc_VirtualSize,
                    raw=s.PointerToRawData,
                    rawsize=s.SizeOfRawData,
                    chars=s.Characteristics,
                )
            )
        self.by_rva = bytearray(self.size)
        for s in self.sections:
            n = min(s["vsize"], s["rawsize"])
            self.by_rva[s["va"] : s["va"] + n] = self.data[
                s["raw"] : s["raw"] + n
            ]

    def read(self, rva, n):
        return bytes(self.by_rva[rva : rva + n])

    def is_code(self, rva):
        for s in self.sections:
            if s["chars"] & 0x20000000:
                if s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"]):
                    return True
        return False

    def is_mapped(self, rva):
        return 0 <= rva < self.size and any(
            s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"])
            for s in self.sections
        )

    def rva_to_raw(self, rva):
        for s in self.sections:
            if s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"]):
                off = s["raw"] + (rva - s["va"])
                if 0 <= off < len(self.data):
                    return off
        return None

    def cstr(self, rva, limit=512):
        off = self.rva_to_raw(rva)
        if off is None:
            return None
        end = self.data.find(b"\x00", off, off + limit)
        if end < 0:
            return None
        return self.data[off:end]


def build_imports(img):
    """name -> list of (rva_of_iat_slot, dll, import_name)"""
    by_addr = {}
    for d in img.pe.DIRECTORY_ENTRY_IMPORT:
        for imp in d.imports:
            name = imp.name.decode() if imp.name else "ord%d" % imp.ordinal
            by_addr[imp.address - img.base] = (d.dll.decode(), name)
    return by_addr


def build_exports(img):
    out = {}
    if not hasattr(img.pe, "DIRECTORY_ENTRY_EXPORT"):
        return out
    for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name:
            out[e.name.decode()] = e.address
    return out


def main_spike():
    img = Image(DLL)
    print("base", hex(img.base), "size", hex(img.size))
    print("sha256", sha256(DLL))
    for s in img.sections:
        print(" ", s["name"], hex(s["va"]), hex(s["vsize"]))
    imps = build_imports(img)
    print("import slots:", len(imps))
    exps = build_exports(img)
    print("exports:", len(exps))
    for k, v in list(exps.items())[:40]:
        print("  ", k, hex(v))
    # sanity: disassemble at 0x9860
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for start in (0x9570, 0x9860, 0x96E9, 0x977C, 0x97A5, 0x97CC, 0x97D3):
        print("\n== rva", hex(start))
        code = img.read(start, 64)
        for ins in md.disasm(code, img.base + start):
            print("   %08X  %-24s %s %s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            if ins.address - img.base >= start + 48:
                break


if __name__ == "__main__":
    main_spike()
