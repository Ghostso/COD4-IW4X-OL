import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for rva in (0x77E90,0x77F00,0x78000):
    fo=None
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            fo=s.PointerToRawData+(rva-s.VirtualAddress)
    print('\n=== rva %08X ==='%rva)
    for ins in md.disasm(data[fo:fo+220], ib+rva):
        print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
        if ins.mnemonic=='ret': break
