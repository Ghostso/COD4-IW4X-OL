
import sys, os
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
for rva in (0xa2e50,0xa2d90,0x1ac1d0,0x1acb00,0x1aca10,0x1ac670,0x1ac980,0x1ac8c0,0x5ac1d0,0x5acb00,0x5aca10,0x5ac670,0x5ac980,0x44c8c0):
    b_rva=im.read_rva(rva,8)
    b_va=im.read_rva(rva+im.ib,8)
    lines.append('%#x  asRVA=%s  asVAplus=%s' % (rva,b_rva.hex(),b_va.hex()))
c_rva=0; c_va=0
for off in range(0x400,0x400+0x7aca00-5):
    if im.data[off]!=0xE8: continue
    rel=int.from_bytes(im.data[off+1:off+5],'little',signed=True)
    src=0x401000+(off-0x400)
    t=src+5+rel
    rr=t-0x400000
    if rr>=0:
        b=im.read_rva(rr,3)
        if b[:3]==bytes.fromhex('558bec'): c_rva+=1
        b2=im.read_rva(rr+0x400000,3)
        if b2[:3]==bytes.fromhex('558bec'): c_va+=1
lines.append('prologue_hits target_as_rva=%d target_as_va_plus=%d' % (c_rva,c_va))
open(os.path.join(OUT,'f_address_basis.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
