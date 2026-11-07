"""S3: locate the IIPS policy protocol TDR descriptors and constants."""
import re
import struct
import sys

import pefile

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\工具\EX035_DIR\IIPS\iips_policymsg.dll"

NAMES = [
    "cs_policy_msg", "CS_POLICY_MSG_MAGIC", "CS_POLICY_MSG_ENCLEN",
    "CS_POLICY_MSG_REQ", "CS_POLICY_MSG_RES",
    "Version", "Magic", "PkgLen", "CmdID", "BusID",
    "MaxPreDLSpeed", "MaxConnNum", "MaxDLSpeed", "MaxRealTimeULSpeed",
    "MaxPreULSpeed", "MaxInGamePreULSpeed", "NeedUploadBitmap",
    "ReportIntervalMs", "ReportUploadSpeedBytePerSecond",
    "HeadLen", "BodyLen", "EncryptLen", "EncryptBuffer",
    "Res1", "Res2", "Res3",
]


def main():
    data = open(PATH, "rb").read()
    pe = pefile.PE(PATH)
    base = pe.OPTIONAL_HEADER.ImageBase
    secs = [(s.Name.rstrip(b"\x00").decode("latin1"), s.VirtualAddress,
             s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections]
    print("imagebase=%08X" % base)
    for s in secs:
        print("  %-8s va=%06X vs=%06X raw=%06X rsz=%06X" % s)

    def off2rva(o):
        for _n, va, _vs, rp, rs in secs:
            if rp <= o < rp + rs:
                return va + (o - rp)
        return None

    print()
    print("--- name -> VA and 32-bit references ---")
    for n in NAMES:
        o = data.find(n.encode() + b"\x00")
        if o < 0:
            print("  %-34s NOT FOUND" % n)
            continue
        r = off2rva(o)
        va = base + r if r is not None else None
        refs = [m.start() for m in
                re.finditer(re.escape(struct.pack("<I", va)), data)] if va else []
        print("  %-34s off=%05X rva=%05X va=%08X refs=%d %s"
              % (n, o, r, va, len(refs),
                 " ".join("%05X" % x for x in refs[:6])))

    print()
    print("--- magic string context ---")
    mo = data.find(b"iips#policy!@#$%")
    print("  off=%X rva=%X" % (mo, off2rva(mo)))
    print("  bytes:", data[mo - 16:mo + 32])
    return 0


if __name__ == "__main__":
    sys.exit(main())
