import struct
def info(p):
    d = open(p,"rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    mach = struct.unpack_from("<H", d, pe+4)[0]
    nsec = struct.unpack_from("<H", d, pe+6)[0]
    optsz = struct.unpack_from("<H", d, pe+20)[0]
    ch = struct.unpack_from("<H", d, pe+22)[0]
    print("%-58s size=%-8d machine=0x%04X sections=%d opthdr=%d chars=0x%04X" % (p, len(d), mach, nsec, optsz, ch))
info(r"backups\FROZEN_20261002_222802\A_observer_out\AboProbe.dll")
info(r"restore_iips_contract_001\observer2\out\AboProbe.dll.mine_20261003")
