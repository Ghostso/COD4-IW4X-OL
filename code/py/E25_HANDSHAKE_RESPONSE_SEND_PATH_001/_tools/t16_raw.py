import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def raw_calls(rva, nbytes, tag):
    print("="*78); print(tag,"RVA %06X"%rva)
    o=img.off(rva); blob=img.d[o:o+nbytes]
    for j in range(len(blob)):
        if blob[j] in (0xe8,) and j+4<len(blob):
            rel=struct.unpack_from("<i",blob,j+1)[0]
            trva=(rva+j+5+rel)&0xffffffff
            print("  %06X E8 -> RVA %06X sec=%s"%(rva+j,trva,img.sec(trva)))
raw_calls(0x6AA230,0x100,"0x6AA230")
raw_calls(0x6AA7B0,0x1C0,"0x6AA7B0")
