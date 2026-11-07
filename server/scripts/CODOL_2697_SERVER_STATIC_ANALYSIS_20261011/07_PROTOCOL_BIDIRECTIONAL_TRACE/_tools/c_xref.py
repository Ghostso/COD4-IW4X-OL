# c_xref.py - client static xref + string locator
import sys, struct, bisect, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import c_common as c

def find_strings(im, needle):
    out=[]; start=0; b=needle if isinstance(needle,bytes) else needle.encode()
    while True:
        i=im.data.find(b,start)
        if i<0: break
        rva=None
        for nm,va,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=i<ptr+rsz:
                rva=va+(i-ptr); break
        out.append((i,rva)); start=i+1
    return out

def va_refs(im, va):
    out=[]
    for nm,va0,vsz,ptr,rsz in im.sections:
        if rsz==0: continue
        d=im.data; base=ptr; end=ptr+rsz-4; i=base
        while True:
            j=d.find(struct.pack('<I',va),i,end)
            if j<0: break
            out.append((nm,va0+(j-ptr))); i=j+1
    return out

def text_call_targets(im):
    """return dict target_rva -> list of call sites (E8 only)"""
    res={}
    for nm,va,vsz,ptr,rsz in im.sections:
        if nm not in ('.text','.tvm0'): continue
        d=im.data
        for i in range(ptr,ptr+rsz-5):
            if d[i]==0xE8:
                rel=struct.unpack_from('<i',d,i+1)[0]
                src=va+(i-ptr); tgt=src+5+rel
                res.setdefault(tgt,[]).append(src)
    return res

def callers(im, target, tbl=None):
    tbl = tbl or text_call_targets(im)
    return tbl.get(target,[])
