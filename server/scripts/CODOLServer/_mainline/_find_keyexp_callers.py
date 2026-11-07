import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def fo2rva(fo):
    for s in pe.sections:
        if s.PointerToRawData<=fo<s.PointerToRawData+s.SizeOfRawData:
            return s.VirtualAddress+(fo-s.PointerToRawData)
# find all prologues that reference 0x100da4b4 (T-table)
import struct
needle=struct.pack('<I',0x100da4b4)
print('refs to T-table 0x100da4b4:')
for s in pe.sections:
    if not (s.Characteristics & 0x20000000): continue
    sec=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    i=0; n=0
    while True:
        i=sec.find(needle,i)
        if i<0: break
        print('  rva=%08X'%(s.VirtualAddress+i)); i+=1; n+=1
        if n>25: break
print()
# disassemble around AEStables to find the key expansion caller(s)
# find calls to 0x10078258 (key expansion entry)
target=ib+0x78258
print('callers of KeyExpansion 0x10078258:')
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
