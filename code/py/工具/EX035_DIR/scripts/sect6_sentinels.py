import pathlib,struct
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); va=0xE5D7000; raw=0x771000; rs=0x6000; IB=0x400000
# all locations in section 6 containing 0x80000001..0x80ffffff dwords, plus byte-level sentinel patterns
vals=[(va+4*i,struct.unpack_from('<I',D,raw+4*i)[0]) for i in range(rs//4)]
for x,v in vals:
 if 0x80000000<=v<=0x8fffffff: print('%08X %08X'%(x,v))
