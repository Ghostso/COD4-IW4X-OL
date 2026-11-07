import pefile,struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read(); pe=pefile.PE(p,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
for va in (0x10063E33,0x1007A780,0x1007AA80,0x10078250):
    needle=struct.pack('<I',va)
    offs=[]
    i=0
    while True:
        i=data.find(needle,i)
        if i<0: break
        offs.append(i); i+=1
    print('VA %08X pointer occurrences:'%va)
    for o in offs[:20]:
        rva=None
        for s in pe.sections:
            if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:
                rva=s.VirtualAddress+(o-s.PointerToRawData)
                sec=s.Name.decode(errors='replace').strip('\x00')
                break
        print('  off=%X rva=%s sec=%s ctx=%s'%(o,('%08X'%rva) if rva else '?',sec,data[o-16:o+32].hex(' ')))
