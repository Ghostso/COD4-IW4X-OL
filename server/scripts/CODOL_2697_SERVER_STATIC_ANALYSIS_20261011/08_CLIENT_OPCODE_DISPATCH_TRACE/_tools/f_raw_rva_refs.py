
import sys, os, struct, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
lines.append('SHA256 '+hashlib.sha256(im.data).hexdigest())
lines.append('ImageBase %#x' % im.ib)
for rva in (0xA2E50,0xA2D90,0x1AC1D0,0x1ACB00):
    # E8 target = raw RVA
    hits=[]
    for nm,va,vsz,ptr,rsz in im.sections:
        if nm not in ('.text','.tvm0','.rimp'): continue
        for i in range(ptr,ptr+rsz-4):
            if im.data[i]!=0xE8: continue
            rel=struct.unpack_from('<i',im.data,i+1)[0]
            src=im.ib+va+(i-ptr)
            if src+5+rel==rva: hits.append((nm,va+(i-ptr),i,src))
    lines.append('E8_RAW_TARGET %#x -> %s' % (rva,repr(hits)))
    # absolute dword = raw RVA
    b=struct.pack('<I',rva); res=[]; st=0
    while True:
        j=im.data.find(b,st)
        if j<0: break
        for nm,va,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=j<ptr+rsz:
                res.append((nm,va+j-ptr,j)); break
        st=j+1
    lines.append('DWORD_RAW %#x -> %s' % (rva,repr(res)))
open(os.path.join(OUT,'f_raw_rva_refs.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
