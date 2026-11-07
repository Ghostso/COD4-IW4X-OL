# -*- coding: utf-8 -*-
"""045: locate IMPORT_DESCRIPTORs / confirm section#1 ordinal ILT is the IAT of the call sites."""
import sys, struct
sys.stdout.reconfigure(encoding="utf-8")
EXE=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
exe=open(EXE,"rb").read(); img=open(IMG,"rb").read()
print("exe len",hex(len(exe)),"img len",hex(len(img)))
# section#1
S1_VA=0x8a8000; S1_VS=0x16da70; EXE_S1_RAW=0x594000; IMG_S1_RAW=0x8a8000
def exe_off(rva): return EXE_S1_RAW+(rva-S1_VA) if S1_VA<=rva<S1_VA+S1_VS else None
def img_off(rva): return IMG_S1_RAW+(rva-S1_VA) if S1_VA<=rva<S1_VA+S1_VS else None
# find dwords equal to candidate ILT RVAs in the whole exe
def find_dw(blob,val,limit=8):
    pat=struct.pack("<I",val); out=[]; s=0
    while True:
        j=blob.find(pat,s)
        if j<0: break
        out.append(j); s=j+1
        if len(out)>=limit: break
    return out
print("\n== on-disk EXE: dword refs to candidate ILT/IAT RVAs ==")
for rva in (0x8A8370,0x8A84D4,0x8A8534,0x8A84E8,0x8A84E4,0x8A853C):
    print("  RVA %08X refs@ %s"%(rva, ["%X"%x for x in find_dw(exe,rva)]))
# print the ILT block on disk near 0x8A84B4..0x8A8560 with ordinal names
pe_ords={3:"closesocket",4:"connect",5:"getpeername",6:"getsockname",7:"getsockopt",1:"accept",2:"bind",8:"htonl",9:"htons",10:"ioctlsocket",12:"inet_ntoa",13:"listen",14:"ntohl",15:"ntohs",16:"recv",17:"recvfrom",18:"select",19:"send",20:"sendto",21:"setsockopt",22:"shutdown",23:"socket",52:"gethostbyname",57:"gethostname",111:"WSAGetLastError",112:"WSASetLastError",115:"WSAStartup",116:"WSACleanup",151:"__WSAFDIsSet"}
print("\n== on-disk ILT/IAT block, section#1, RVA 0x8A84B4..0x8A8560 ==")
for rva in range(0x8A84B4,0x8A8560,4):
    o=exe_off(rva)
    if o is None: continue
    v=struct.unpack("<I",exe[o:o+4])[0]
    io=img_off(rva); iv=struct.unpack("<I",img[io:io+4])[0] if io is not None else None
    tag=""
    if v>=0x80000000: tag="ordinal %d = %s"%(v&0xffff, pe_ords.get(v&0xffff,"?"))
    print("  RVA %08X  disk=%08X %-28s img=%08X"%(rva,v,tag,iv if iv is not None else 0))
