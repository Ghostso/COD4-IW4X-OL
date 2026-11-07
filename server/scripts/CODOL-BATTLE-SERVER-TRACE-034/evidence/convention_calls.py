import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
print("file size 0x%X" % len(d))
# The probe (CodolNetchanTrace.py) hooks module.base.add(RVA). module.base == ImageBase == 0x400000.
# Find every E8 rel32 whose target equals a given absolute VA, for BOTH interpretations.
def callers_of(target_va, base_hypothesis):
    """base_hypothesis: 'off==VA'  => scanning offset X means VA = X
                        'off==VA-0x400000' => scanning offset X means VA = X+0x400000"""
    out=[]
    for i in range(len(d)-5):
        if d[i]!=0xE8: continue
        rel=struct.unpack_from("<i",d,i+1)[0]
        off_va = i if base_hypothesis=="off==VA" else i+0x400000
        if (off_va+5+rel)&0xffffffff == target_va:
            out.append((off_va,i))
    return out
for tname,tva in [("parsePacketEntities",0x46C2F0),("parseServerMessage",0x46E6A0),
                  ("parseSnapshot",0x46D170),("netchanProcess",0x5A5960),("decodeMessage",0x46BF80)]:
    for hyp in ("off==VA","off==VA-0x400000"):
        c=callers_of(tva,hyp)
        print("%-20s target=%08X  %-14s callers(=call-site VA): %s" % (tname,tva,hyp,
              ", ".join("%08X"%a for a,_ in c[:10]) or "NONE"))
    print()
