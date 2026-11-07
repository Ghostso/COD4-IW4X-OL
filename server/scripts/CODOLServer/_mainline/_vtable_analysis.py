import pefile,struct,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
print('=== vtable @ rva 0x63E84 ===')
for i in range(0,0x40,4):
    v=struct.unpack_from('<I',data,0x63E84+i)[0]
    print('  slot+%02X = %08X'%(i,v))
print()
# find code that references vtable address (0x10063E84)
needle=struct.pack('<I',0x10063E84)
offs=[]; i=0
while True:
    i=data.find(needle,i)
    if i<0: break
    offs.append(i); i+=1
print('refs to vtable VA 10063E84:',['%X'%o for o in offs])
for o in offs[:6]:
    rva=None
    for s in pe.sections:
        if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:
            rva=s.VirtualAddress+(o-s.PointerToRawData)
    print('  ref rva=%s'%(('%08X'%rva) if rva else '?'))
    lo=max(0,o-64)
    for ins in md.disasm(data[lo:o+48], ib+(rva-(o-lo)) if rva else 0):
        print('    %08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
