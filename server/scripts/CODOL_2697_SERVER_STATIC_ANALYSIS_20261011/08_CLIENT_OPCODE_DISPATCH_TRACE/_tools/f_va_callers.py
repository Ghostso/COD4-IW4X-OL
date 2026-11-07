
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
def find_e8(target_va, secs=('.text','.tvm0','.rimp')):
    hits=[]
    for nm,va,vsz,ptr,rsz in im.sections:
        if nm not in secs: continue
        for off in range(ptr,ptr+rsz-4):
            if im.data[off]!=0xE8: continue
            rel=struct.unpack_from('<i',im.data,off+1)[0]
            src=im.ib+va+(off-ptr)
            if src+5+rel==target_va: hits.append((nm,va+(off-ptr),off,src))
    return hits
# VA form targets
for va in (0x5AC1D0,0x5ACB00,0x5AC670,0x5AC980,0x4A2E50,0x4A2D90):
    lines.append('VA %#x E8=%s' % (va,repr(find_e8(va))))
open(os.path.join(OUT,'f_va_callers.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
