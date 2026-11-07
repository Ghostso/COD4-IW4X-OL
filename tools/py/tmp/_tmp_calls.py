import struct, sys, json, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im = Img(); IB = im.IB
# build call map over .text
n,sva,vs,rp,rs,x = [s for s in im.secs if s[0]=='.text'][0]
d = im.d[rp:rp+rs]
calls = {}
for i in range(len(d)-5):
    if d[i] in (0xe8,):
        rel = struct.unpack_from('<i', d, i+1)[0]
        tgt = (IB+sva+i+5+rel) & 0xffffffff
        calls.setdefault(tgt, []).append(IB+sva+i)
json.dump({hex(k):[hex(v) for v in vs] for k,vs in calls.items()}, open(r'_tmp_calls.json','w'))
print("call sites", sum(len(v) for v in calls.values()), "targets", len(calls))
for t in (0xC5B13C,0xC5B144):
    print(hex(t), "not a call target")
for f in (0xAA9CE0,0xAA8D70,0xAA8BF0,0xBA13D0,0xBA0D20,0xC78040,0xC73800,0xC73760,0xC737A0,0xA87830,0xA881A0):
    cl = calls.get(f, [])
    print("func %08X callers %d" % (f, len(cl)), [hex(c) for c in cl[:12]])
PY
