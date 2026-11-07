import pefile,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
# disassemble backwards context around 0x63E33 from a likely function start
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.SizeOfRawData:
            return s.PointerToRawData+(rva-s.VirtualAddress)
# 0x63E33 is a separate func "set key"(ecx=this, [esp+0xc]=keyptr)
# find its callers via indirect: search for 'push imm' or mov to [obj+0x4c]
# instead: search for the literal 0x4c store pattern and 0x50 copy pattern
start=rva2fo(0x63CC0)
print('=== 0x63CC0..0x63E90 ===')
for ins in md.disasm(data[start:start+0x1D0], ib+0x63CC0):
    print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
