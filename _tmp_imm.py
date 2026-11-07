import struct, sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im = Img()
IB = im.IB
for va in (0xC5B13C, 0xC5B144):
    pat = struct.pack("<I", va)
    n, sva, vs, rp, rs, x = [s for s in im.secs if s[0] == ".text"][0]
    data = im.d[rp:rp+rs]
    hits = []
    i = data.find(pat)
    while i != -1:
        hits.append((sva + i, data[i-5:i+10].hex()))
        i = data.find(pat, i+1)
    print("VA %08X -> .text raw-imm hits: %d" % (va, len(hits)))
    for rva, ctx in hits:
        print("   RVA %06X VA %08X ctx=%s" % (rva, IB+rva, ctx))
