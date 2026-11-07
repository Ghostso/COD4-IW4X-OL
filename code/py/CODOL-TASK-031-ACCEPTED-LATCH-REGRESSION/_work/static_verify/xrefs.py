import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
targets = {0x632680:"accepted parser",0x632070:"mmstart ctor",0x631E90:"ctor arg helper",0x631E50:"post ctor",0x62F6C0:"retry/reset",0x6292B0:"?",0x634340:"latch consumer fn",0x60C3C678-0x60000000+0x400000:"strncmp?"}
# E8 rel32 xrefs
def call_xrefs(t):
    res=[]
    for i in range(len(d)-5):
        if d[i]==0xE8:
            rel=struct.unpack_from("<i",d,i+1)[0]
            va=i+BASE
            if (va+5+rel)&0xffffffff==t:
                res.append(va)
    return res
for t,name in [(0x632680,"accepted parser 0x632680"),(0x632070,"mmstart ctor 0x632070"),(0x631E90,"0x631E90"),(0x631E50,"0x631E50"),(0x62F6C0,"0x62F6C0")]:
    x=call_xrefs(t)
    print("%-28s callers: %s" % (name, ", ".join("%08X"%a for a in x) or "NONE"))
print()
# imm32 references (push imm / mov reg,imm / vtable entries)
def imm_xrefs(t):
    res=[]
    tb=struct.pack("<I",t)
    start=0
    while True:
        i=d.find(tb,start)
        if i<0: break
        res.append(i+BASE)
        start=i+1
    return res
for t,name in [(0x632680,"0x632680"),(0x632070,"0x632070"),(0x634340,"0x634340"),(0x634402,"0x634402")]:
    x=imm_xrefs(t)
    print("%-12s imm32 refs (%d): %s" % (name, len(x), ", ".join("%08X"%a for a in x[:40])))
