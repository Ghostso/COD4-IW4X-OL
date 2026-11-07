# EX-060 TASK 3/4/6: xref search for 0x8189FEC and WIN_IIPS_INIT_ERROR.
import os
import re
import struct
from collections import OrderedDict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (
    X86_OP_IMM, X86_OP_MEM, X86_OP_REG,
    X86_REG_EIP,
)

TARGET_VA = 0x8189FEC


def scan_image(path, label):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    data = open(path, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase
    print("=" * 78)
    print("%s  %s" % (label, path))
    print("  image base 0x%X  size 0x%X" % (base, pe.OPTIONAL_HEADER.SizeOfImage))
    print("  sha256 %s" % __import__("hashlib").sha256(data).hexdigest())
    hits = []
    needle = struct.pack("<I", TARGET_VA)
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    print("  raw occurrences of little-endian %08X : %d" % (TARGET_VA, len(hits)))
    # map raw offsets to sections + RVA
    for off in hits:
        sec = None
        for s in pe.sections:
            if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                sec = s
                break
        if sec is None:
            print("     raw 0x%X  (no section)" % off)
            continue
        rva = sec.VirtualAddress + (off - sec.PointerToRawData)
        nm = sec.Name.decode(errors="replace").rstrip("\x00")
        print("     raw 0x%X  %s  RVA 0x%X  VA 0x%X" % (off, nm, rva, base + rva))
    return pe, data


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        (os.path.join(root, "工具", "EX035_DIR", "codoMP_client_shipRetail.exe"),
         "CODOL_EXE"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "iips.dll"), "iips.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSHostApp.exe"),
         "IIPSHostApp.exe"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSHost.dll"),
         "IIPSHost.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSVFS.dll"),
         "IIPSVFS.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSCheck.dll"),
         "IIPSCheck.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSStats.dll"),
         "IIPSStats.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSRepair.dll"),
         "IIPSRepair.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "IIPSLaunchRestore.dll"),
         "IIPSLaunchRestore.dll"),
        (os.path.join(root, "工具", "EX035_DIR", "IIPS", "iips_policymsg.dll"),
         "iips_policymsg.dll"),
        (os.path.join(root, "TenProxy.dll"), "TenProxy.dll"),
        (os.path.join(root, "GbSpy.dll"), "GbSpy.dll"),
    ]
    for path, label in candidates:
        if not os.path.exists(path):
            print("MISSING %s -> %s" % (label, path))
            continue
        try:
            scan_image(path, label)
        except Exception as e:
            print("ERROR %s : %r" % (label, e))


if __name__ == "__main__":
    main()
