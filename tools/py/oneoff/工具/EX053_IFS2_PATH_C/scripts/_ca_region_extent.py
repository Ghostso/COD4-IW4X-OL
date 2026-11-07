import pathlib,struct,collections
D=pathlib.Path("codoMP_client_shipRetail.exe").read_bytes();IB=0x400000
def rd(va):
 o=0x594000+(va-0xCA8000)
 return struct.unpack_from("<I",D,o)[0]
for name,a,b in [("ref_region",0xCA8000,0xCA8760),("exact_template",0xCA8000,0xCA876C),("512dwords",0xCA8000,0xCA8800),("next_array",0xCA876C,0xCA8800)]:
 vals=[rd(x) for x in range(a,b,4)]
 ptr=[v for v in vals if IB<=v<IB+0xE659000]
 sent=[v for v in vals if 0x80000000<=v<=0x8fffffff]
 zero=[v for v in vals if v==0]
 print(name,"dwords",len(vals),"ptr",len(ptr),"sent",len(sent),"zero",len(zero),"unique",len(set(vals)))
vals=[rd(x) for x in range(0xCA8000,0xCA876C,4)]
targets=[v for v in vals if IB<=v<IB+0xE659000]
print("targets",len(targets),"unique",len(set(targets)),"min",hex(min(targets)),"max",hex(max(targets)))
for v in targets[:20]:
 o=0x594000+((v-IB)-0x8A8000)
 if 0<=o+4<=len(D): print(hex(v),"off",hex(o),"raw",D[o:o+16].hex(),"dwords",["%08X"%struct.unpack_from("<I",D,o+j)[0] for j in range(0,16,4)])

