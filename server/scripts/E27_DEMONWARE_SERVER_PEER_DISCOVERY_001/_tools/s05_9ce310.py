import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
print("=== client VA 0x9CE310 (claimed bdLobbyConnection::getMessageToDispatch) ===")
for i in im.dis(0x9CE310-IB,0x80): print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
# search for the DEADBEEF compare (EF BE AD DE or 3D EF BE AD DE = cmp eax,0xDEADBEEF)
pat=struct.pack("<I",0xDEADBEEF)
hits=[]; st=0
while True:
    j=im.d.find(pat,st)
    if j<0: break
    for nm,va,vs,rp,rs,x in im.secs:
        if rp<=j<rp+rs: hits.append((nm,hex(va+(j-rp)))); break
    st=j+1
print("client DEADBEEF occurrences:",hits)
for nm,hr in hits:
    rva=int(hr,16)
    if nm in ('.text','.tvm0'):
        for i in im.dis(rva-8,0x20):
            if i.address-IB<=rva<=i.address-IB+8:
                pass
        print("  context",hr)
        for i in im.dis(rva-10,0x1C): print("     %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
