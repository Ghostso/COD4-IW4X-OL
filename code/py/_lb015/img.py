# -*- coding: utf-8 -*-
"""Helper for LISTENER-BRIDGE-BATTLE-015 static analysis.
Runtime image: image_best.bin (base 0x400000). Also cross-check fresh dump.
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG_PATH = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
            r"\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x400000
_IMG = open(IMG_PATH, "rb").read()
MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True

def read(va, n):
    return _IMG[va - BASE: va - BASE + n]

def dword(va):
    return struct.unpack_from("<I", _IMG, va - BASE)[0]

def sword(va):
    return struct.unpack_from("<i", _IMG, va - BASE)[0]

def byte(va):
    return _IMG[va - BASE]

def is_code(v):
    return 0x401000 <= v < 0xE65000

def dis(va, n=None, count=None):
    if n is None:
        n = count * 8
    code = read(va, n)
    return list(MD.disasm(code, va))

def show(va, count=40):
    for ins in dis(va, count=count):
        print("  %08X  %-24s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic + " " + ins.op_str))

def dword_refs(value):
    pat = struct.pack("<I", value)
    out = []
    s = 0
    while True:
        i = _IMG.find(pat, s)
        if i < 0:
            return out
        out.append(BASE + i)
        s = i + 1

def call_rel32_hits(target):
    out = []
    for i in range(0, len(_IMG) - 5):
        if _IMG[i] == 0xE8:
            rel = struct.unpack_from("<i", _IMG, i + 1)[0]
            if BASE + i + 5 + rel == target:
                out.append(BASE + i)
    return out

def vtable_slots(vt, n=64):
    return [dword(vt + 4 * i) for i in range(n)]
