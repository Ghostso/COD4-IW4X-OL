import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
for rva in (0xCB83E0,0xCB83E8,0xCB83E0-4,0xCB83E8-4):
    print(hex(rva),im.cstr(rva,80))
for name,va in (("E0",0xCB83E0),("E8",0xCB83E8)):
    b=struct.pack("<I",va); st=0; hits=[]
    while True:
        j=im.data.find(b,st)
        if j<0: break
        for nm,sva,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=j<ptr+rsz: hits.append((nm,sva+j-ptr,j)); break
        st=j+1
    print(name,hits)
