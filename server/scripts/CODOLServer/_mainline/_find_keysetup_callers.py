import pefile,struct,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            return s.PointerToRawData+(rva-s.VirtualAddress)
# find function start before 0x63E33
fo=rva2fo(0x63E33)
start=fo
for i in range(fo,max(0,fo-0x400),-1):
    if data[i:i+3]==b'\x55\x8b\xec':
        start=i; break
srva=None
for s in pe.sections:
    if s.PointerToRawData<=start<s.PointerToRawData+s.SizeOfRawData:
        srva=s.VirtualAddress+(start-s.PointerToRawData)
print('key-setup func start rva=%08X'%srva)
print('--- disasm ---')
for ins in md.disasm(data[start:start+260], ib+srva):
    print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
    if ins.mnemonic=='ret': break
print()
target=ib+srva
print('callers:')
for s in pe.sections:
    if not (s.Characteristics & 0x20000000): continue
    sec=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    for i in range(len(sec)-5):
        if sec[i]!=0xE8: continue
        rel=struct.unpack_from('<i',sec,i+1)[0]
        src=s.VirtualAddress+i
        dst=ib+src+5+rel
        if dst==target:
            print('  caller rva=%08X'%src)
