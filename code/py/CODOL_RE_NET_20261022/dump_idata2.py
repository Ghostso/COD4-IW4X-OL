import pefile,struct,os
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True)
ib=pe.OPTIONAL_HEADER.ImageBase
def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+(rva-s.VirtualAddress)
    return None
imp=pe.OPTIONAL_HEADER.DATA_DIRECTORY[1]
print('import dir',hex(imp.VirtualAddress),hex(imp.Size))
off=rva2off(imp.VirtualAddress)
data=d[off:off+imp.Size]
print(data[:256].hex())
# parse descriptors
i=0
while i+20<=len(data):
    oft,ts,fc,name,ft=struct.unpack_from('<IIIII',data,i)
    if (oft|ts|fc|name|ft)==0: print('end at',i); break
    print(f'desc {i}: OFT={oft:#x} TS={ts:#x} FC={fc:#x} Name={name:#x} FT={ft:#x}')
    if name:
        no=rva2off(name)
        print('   dll:',d[no:no+64].split(b'\0')[0])
    i+=20
print('\n.idata2 raw head:')
s=[x for x in pe.sections if x.Name.rstrip(b'\0')==b'.idata2'][0]
raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
for j in range(0,min(len(raw),0x800),16):
    print(f'{s.VirtualAddress+j:08x}  {raw[j:j+16].hex(" ")}  {raw[j:j+16].decode("latin1").replace(chr(0),".")}')
