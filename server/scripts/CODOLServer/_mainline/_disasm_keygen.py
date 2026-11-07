import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            return s.PointerToRawData+(rva-s.VirtualAddress)
for rva in (0x626C0,0x63140,0x649E0,0x641E0):
    print('\n===== disasm rva=%08X ====='%rva)
    fo=rva2fo(rva)
    n=0
    for ins in md.disasm(data[fo:fo+500], ib+rva):
        print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
        n+=1
        if n>=70 or ins.mnemonic=='ret': break
