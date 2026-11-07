import struct
def info(p):
    d = open(p,"rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    mach = struct.unpack_from("<H", d, pe+4)[0]
    nsec = struct.unpack_from("<H", d, pe+6)[0]
    print("%-46s size=%-7d machine=0x%04X sections=%d" % (p.split("\\")[-1], len(d), mach, nsec))
    # look for ReadyToRun signature
    rtr = d.find(b"RTR0")
    print("    RTR0 signature at:", rtr)
    # count .NET metadata signature
    print("    BSJB at:", d.find(b"BSJB"))
info(r"D:\BaiduNetdiskDownload\使命召唤OL\backups\FROZEN_20261002_222802\A_observer_out\AboProbe.dll")
info(r"D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2\out\AboProbe.dll.mine_20261003")
info(r"D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2\bin\Release\net8.0\win-x86\AboProbe.dll")
