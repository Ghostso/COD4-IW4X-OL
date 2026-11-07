# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
SLOTS={"0xCA84E0":"send","0xCA84E4":"recv","0xCA84E8":"select","0xCA8518":"sendto",
       "0xCA851C":"recvfrom","0xCA853C":"WSAGetLastError","0xCA8548":"socket",
       "0xCA8554":"bind","0xCA8558":"setsockopt","0xCA852C":"getsockopt",
       "0xCA84F0":"connect","0xCA8544":"closesocket","0xCA8540":"ioctlsocket",
       "0xCA84FC":"listen","0xCA8500":"accept","0xCA84D8":"getsockname","0xCA84EC":"getpeername"}
print("=== targeted IAT slot usage ===")
for hexv,name in SLOTS.items():
    v=int(hexv,16)
    sites=[]
    for i in range(0x1000,0x8a7000-6):
        if C._img[i]==0xFF and C._img[i+1] in (0x15,0x25):
            if struct.unpack_from("<I",C._img,i+2)[0]==v:
                sites.append((i,"call" if C._img[i+1]==0x15 else "jmp"))
    print("  [%-16s] VA 0x%s : %d site(s) %s"%(name,hexv,len(sites),", ".join("0x%X"%a for a,_ in sites)))
