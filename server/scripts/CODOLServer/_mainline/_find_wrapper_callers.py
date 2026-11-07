import pefile,struct,capstone
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for wrapper in (0x7A780,0x7AA80,0x78250):
    target=ib+wrapper
    print('\n===== callers of wrapper %08X ====='%target)
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
                fo=s.PointerToRawData+i
                lo=max(0,fo-80)
                for ins in md.disasm(data[lo:fo+32], ib+(src-(fo-lo))):
                    print('    %08X %-20s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
