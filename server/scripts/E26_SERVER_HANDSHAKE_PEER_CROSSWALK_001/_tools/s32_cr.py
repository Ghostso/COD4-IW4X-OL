import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
for label,p in [("SERVER",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"),
                ("CLIENT",r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")]:
    im=Img(p); IB=im.IB
    pat=b"challengeResponse"
    print("=== %s challengeResponse hits ==="%label)
    i=0
    while True:
        j=im.d.find(pat,i)
        if j<0: break
        sec=None; rva=None
        for nm,va,vs,rp,rs,x in im.secs:
            if rp<=j<rp+rs: sec=nm; rva=va+(j-rp); break
        print("  fileoff %X sec=%s VA=%08X RVA=%06X"%(j,sec,(IB+rva) if rva else 0,rva or 0))
        # find code xrefs (push imm32 of the VA)
        if rva:
            va=IB+rva
            refs=[]; k=0
            while True:
                m=im.d.find(struct.pack("<I",va),k)
                if m<0: break
                for nm2,va2,vs2,rp2,rs2,x2 in im.secs:
                    if rp2<=m<rp2+rs2:
                        if nm2 in ('.text','.tvm0'): refs.append((nm2,hex(va2+(m-rp2))))
                        break
                k=m+1
            print("        code refs:",refs[:8])
        i=j+1
