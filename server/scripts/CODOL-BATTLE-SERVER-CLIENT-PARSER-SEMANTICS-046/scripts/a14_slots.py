# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
ORD={1:"accept",2:"bind",3:"closesocket",4:"connect",5:"getpeername",6:"getsockname",
 7:"getsockopt",10:"ioctlsocket",12:"inet_ntoa",13:"listen",14:"ntohl",15:"ntohs",
 16:"recv",17:"recvfrom",18:"select",19:"send",20:"sendto",21:"setsockopt",22:"shutdown",
 23:"socket",52:"gethostbyname",111:"WSAGetLastError",115:"WSAStartup",116:"WSACleanup",
 151:"__WSAFDIsSet",112:"ord112",57:"ord57",8:"htonl",9:"htons"}
print("=== all call/jmp dword ptr [0xCA84xx..0xCA86xx]  (indirect via socket IAT) ===")
rows=[]
for i in range(0x1000,0x8a7000-6):
    if C._img[i]==0xFF and C._img[i+1] in (0x15,0x25):
        v=struct.unpack_from("<I",C._img,i+2)[0]
        if 0xCA8400<=v<0xCA8700:
            rva=v-IB; ordn=None
            # read ordinal from disk exe
            import pefile
            rows.append((i, "call" if C._img[i+1]==0x15 else "jmp", v, rva))
from collections import defaultdict
d=defaultdict(list)
for i,k,v,rva in rows: d[rva].append((i,k))
import pefile
pe=pefile.PE(data=C._exe, fast_load=False)
def r2r(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+(rva-s.VirtualAddress)
    return None
for rva in sorted(d):
    ro=r2r(rva); v=struct.unpack_from("<I",C._exe,ro)[0] if ro is not None else 0
    name=ORD.get(v&0xffff,"?") if (v>>31) else "?"
    print("  VA 0x%08X %-12s : %d sites %s"%(rva+IB,name,len(d[rva]),", ".join("0x%X(%s)"%(a,k) for a,k in d[rva])))
print()
print("=== WRITE slots usage (send/sendto) ===")
for i in range(0x1000,0x8a7000-6):
    if C._img[i]==0xFF and C._img[i+1]==0x15:
        v=struct.unpack_from("<I",C._img,i+2)[0]
        if v in (0xCA84E0,0xCA8518):
            print("  0x%08X -> %s"%(i, ORD[19 if v==0xCA84E0 else 20]))
