import pefile,struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            return s.PointerToRawData+(rva-s.VirtualAddress)
# constant table near 0x100fcf50
fo=rva2fo(0xfcf50)
print('constant table @ rva fcf50 (va %08X):'%(ib+0xfcf50))
print(data[fo-32:fo+96].hex(' '))
print(repr(data[fo-32:fo+96]))
print()
# floats at 0x100da098 / 0x100da090
for rva,fmt in ((0xda098,'<f'),(0xda090,'<d')):
    f=rva2fo(rva)
    v=struct.unpack_from(fmt,data,f)[0]
    print('const @ %08X = %r'%(ib+rva,v))
print()
# what is 0x10085340 / 0x10085346 (imports?)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        # find thunk rva for these addresses
        pass
print('imports of interest:')
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        nm=imp.name.decode() if imp.name else ''
        if any(k in nm.lower() for k in ('time','rand','srand','queryperf','gettick')):
            print('  %s!%s addr=%08X'%(d.dll.decode(),nm,imp.address))
