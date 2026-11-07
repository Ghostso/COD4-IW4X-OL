import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
start_off=0x78258
rva=0x78258  # .text starts at raw 0x1000 -> RVA 0x1000
# correct rva mapping
for s in pe.sections:
    if s.PointerToRawData<=start_off<s.PointerToRawData+s.SizeOfRawData:
        rva=s.VirtualAddress+(start_off-s.PointerToRawData)
print('start rva',hex(rva),'va',hex(ib+rva))
count=0
for ins in md.disasm(data[start_off:start_off+400], ib+rva):
    print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
    count+=1
    if count>=80: break
