# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
# Enumerate the ordinal-slot region 0xCA8400..0xCA8700 in the DISK exe (static ordinal table).
EXE=C._exe
# disk raw mapping for the section containing RVA 0x8A8000
import pefile
pe=pefile.PE(data=EXE, fast_load=False)
def rva_to_raw(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None
ORD={1:"accept",2:"bind",3:"closesocket",4:"connect",5:"getpeername",6:"getsockname",
 7:"getsockopt",8:"htonl",9:"htons",10:"ioctlsocket",11:"inet_addr",12:"inet_ntoa",
 13:"listen",14:"ntohl",15:"ntohs",16:"recv",17:"recvfrom",18:"select",19:"send",
 20:"sendto",21:"setsockopt",22:"shutdown",23:"socket",24:"GetAddrInfoW",111:"WSAGetLastError",
 115:"WSAStartup",116:"WSACleanup",114:"WSASetLastError",52:"gethostbyname",101:"WSAAsyncSelect",
 151:"__WSAFDIsSet",16:"recv"}
print("=== dword slots in RVA 0x8A8400..0x8A8700 (disk EXE, ordinal form) ===")
for rva in range(0x8A8400,0x8A8700,4):
    ro=rva_to_raw(rva)
    if ro is None: continue
    v=struct.unpack_from("<I",EXE,ro)[0]
    if v>>31:
        ordn=v&0xffff
        print("  RVA 0x%06X VA 0x%08X ord=%d (0x%X) %s"%(rva, rva+IB, ordn, ordn, ORD.get(ordn,"?")))
