import struct, glob, os
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
print("dump size=0x%X covers 0x%X..0x%X"%(len(d),base,base+len(d)))
targets={
 "DW_DNS_ERROR":0x00DE08D8,
 "DW_DNS_COMPLETE":0x00DE08E8,
 "DW_ACCOUNT_ERROR":0x00DE08F8,
 "DW_LOBBY_ERROR":0x00DE0928,
 "DW_LOBBY_CONNECTED":0x00DE0938,
 "DW_LOGON_ERROR":0x00DE098C,
 "dwLogonStart":0x00DE08C8,
 "CONNECTING_FAILED":0x00DE0640,
 "DW_DUPLICATE_LOGIN":0x00DE0610,
}
for name,va in targets.items():
    le=struct.pack("<I",va)
    hits=[]; i=0
    while True:
        j=d.find(le,i)
        if j<0: break
        hits.append(base+j); i=j+1
    print("  %-22s VA 0x%08X  引用数=%d  %s"%(name,va,len(hits),[hex(x) for x in hits[:6]]))
