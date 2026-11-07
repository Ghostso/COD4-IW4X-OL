import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            return s.PointerToRawData+(rva-s.VirtualAddress)
for rva in (0x85340,0x85346,0x85310):
    fo=rva2fo(rva)
    print('\n=== rva %08X ==='%rva)
    n=0
    for ins in md.disasm(data[fo:fo+160], ib+rva):
        print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
        n+=1
        if n>=25 or ins.mnemonic=='ret': break
