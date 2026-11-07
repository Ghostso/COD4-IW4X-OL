
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
for va,base_rva,label in [(0x40271c,0x271c,'JT_26C8'),(0x406d00,0x6d00,'JT_5FEE'),(0x40e6a8,0xe6a8,'JT_E455'),(0x40e9fc,0xe9fc,'JT_E752'),(0x40ec68,0xec68,'JT_EAA5')]:
    lines.append('===== %s tableVA=%#x =====' % (label,va))
    # table is in .text at VA (rva = va - imagebase)
    rva=va-im.ib
    for i in range(0,16):
        b=im.read_rva(rva+i*4,4)
        if len(b)<4: break
        tgt=struct.unpack('<I',b)[0]
        lines.append('idx=%d raw=%#x target=%#x' % (i,tgt,tgt))
open(os.path.join(OUT,'f_jump_tables.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
