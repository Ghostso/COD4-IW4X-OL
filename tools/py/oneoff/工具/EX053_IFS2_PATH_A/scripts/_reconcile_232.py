import pathlib,struct,collections
D=pathlib.Path("codoMP_client_shipRetail.exe").read_bytes(); IB=0x400000; BASE=0xCA8000; RAW=0x594000
def rd(slot): return struct.unpack_from("<I",D,RAW+(slot-BASE))[0]
def low2(vals): return dict(sorted(collections.Counter(v&3 for v in vals).items()))
refs=[]
for o in range(len(D)-6):
    if D[o]==0xFF and D[o+1] in (0x15,0x25):
        v=struct.unpack_from("<I",D,o+2)[0]
        if BASE<=v<=0xCA8800: refs.append((v,o,D[o+1]))
slots=[v for v,o,op in refs]
print("raw_ff_refs",len(refs),"unique_slots",len(set(slots)),"minmax",hex(min(slots)),hex(max(slots)))
print("raw_ref_slot_low2",low2(slots),"slot_values_low2",low2([rd(s) for s in slots]))
print("unique_slot_values_unique",len(set(rd(s) for s in slots)),"of",len(set(slots)))
for n in [231,232,233,472,475,512]:
    vals=[rd(BASE+4*i) for i in range(n)]
    print("first",n,"low2",low2(vals),"inimage",sum(IB<=v<IB+0xE659000 for v in vals),"unique",len(set(vals)))
want={0:108,1:3,2:115,3:6}
hits=[]
for start in range(0,512):
    for n in range(1,513-start):
        vals=[rd(BASE+4*i) for i in range(start,start+n)]
        if low2(vals)==want and all(0xA13000<=v<0xA15300 for v in vals): hits.append((start,n))
print("matching_contiguous_ranges",hits[:20],"count",len(hits))
for label,ss in [("unique_raw_ff",sorted(set(slots))),("all_raw_ff",slots)]:
    vals=[rd(s) for s in ss]
    print(label,"count",len(vals),"unique",len(set(vals)),"low2",low2(vals),"minmax",hex(min(vals)),hex(max(vals)),"inwin",sum(0xA13000<=v<0xA15300 for v in vals))
