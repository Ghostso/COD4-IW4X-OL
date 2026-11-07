# EX-063 TASK G/H/J: search EXE + known modules for the manager vtable
# 0x1003934C and for slot-1 dispatch of sub_197F0.
import json
import os
import struct
from collections import OrderedDict

import pefile

VT_VA = 0x1003934C
SLOT1_VA = 0x100197F0
SLOT0_VA = 0x10012480

MODULES = [
    ("codoMP_client_shipRetail.exe", r"工具\EX035_DIR\codoMP_client_shipRetail.exe"),
    ("codoMP_client_shipRetailBase.dll", r"工具\EX035_DIR\codoMP_client_shipRetailBase.dll"),
    ("TenProxy.dll", r"工具\EX035_DIR\TenProxy.dll"),
    ("GbSpy.dll", r"工具\EX035_DIR\GbSpy.dll"),
    ("GameRpcs.dll", r"工具\EX035_DIR\GameRpcs.dll"),
    ("TenRpcs.dll", r"工具\EX035_DIR\TenRpcs.dll"),
    ("GDPLoader.dll", r"工具\EX035_DIR\GDPLoader.dll"),
    ("GDPImpl.dll", r"工具\EX035_DIR\GDPImpl.dll"),
    ("GDPCODOTrail.dll", r"工具\EX035_DIR\GDPCODOTrail.dll"),
    ("GameDataPlatformServer.dll", r"工具\EX035_DIR\GameDataPlatformServer.dll"),
    ("PolicyProbe.dll", r"工具\EX035_DIR\PolicyProbe.dll"),
    ("TCJ.dll", r"工具\EX035_DIR\TCJ.dll"),
    ("GCloudVoice.dll", r"工具\EX035_DIR\GCloudVoice.dll"),
    ("VSDDrvDll.dll", r"工具\EX035_DIR\VSDDrvDll.dll"),
    ("BugTrace.dll", r"工具\EX035_DIR\BugTrace.dll"),
    ("TenSLX.dll", r"工具\EX035_DIR\TenSLX.dll"),
    ("TenSp.dll", r"工具\EX035_DIR\TenSp.dll"),
    ("iips.dll", r"工具\EX035_DIR\IIPS\iips.dll"),
    ("IIPSHost.dll", r"工具\EX035_DIR\IIPS\IIPSHost.dll"),
    ("IIPSHostApp.exe", r"工具\EX035_DIR\IIPS\IIPSHostApp.exe"),
    ("IIPSVFS.dll", r"工具\EX035_DIR\IIPS\IIPSVFS.dll"),
    ("IIPSCheck.dll", r"工具\EX035_DIR\IIPS\IIPSCheck.dll"),
    ("IIPSStats.dll", r"工具\EX035_DIR\IIPS\IIPSStats.dll"),
    ("IIPSRepair.dll", r"工具\EX035_DIR\IIPS\IIPSRepair.dll"),
    ("IIPSLaunchRestore.dll", r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"),
    ("iips_policymsg.dll", r"工具\EX035_DIR\IIPS\iips_policymsg.dll"),
]


def main():
    print("=" * 78)
    print("TASK H: cross-module search for the manager vtable / slot-1 target")
    print("=" * 78)
    print("  targets: 0x%X (manager vt), 0x%X (slot1), 0x%X (slot0)"
          % (VT_VA, SLOT1_VA, SLOT0_VA))
    print()

    for label, path in MODULES:
        if not os.path.exists(path):
            print("  %-32s MISSING" % label)
            continue
        data = open(path, "rb").read()
        try:
            pe = pefile.PE(path, fast_load=True)
            base = pe.OPTIONAL_HEADER.ImageBase
            size = pe.OPTIONAL_HEADER.SizeOfImage
        except Exception as e:
            print("  %-32s PE parse error %r" % (label, e))
            continue
        hits = {}
        for nm, va in (("vt", VT_VA), ("slot1", SLOT1_VA), ("slot0", SLOT0_VA)):
            n = data.count(va.to_bytes(4, "little"))
            if n:
                hits[nm] = n
        # also 32-bit absolute of the vtable RVA (unlikely)
        rva = VT_VA - 0x10000000
        n_rva = data.count(rva.to_bytes(4, "little"))
        print("  %-32s base 0x%08X  size 0x%X  %s  vt_rva_hits=%d" % (
            label, base, size,
            (" ".join("%s=%d" % kv for kv in sorted(hits.items())))
            if hits else "(no hits)", n_rva))


if __name__ == "__main__":
    main()
