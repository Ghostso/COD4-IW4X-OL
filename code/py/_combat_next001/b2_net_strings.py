# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

keywords = ["socket","connect","sendto","recvfrom","bind","WSAStartup","WSASocket",
            "closesocket","getaddrinfo","inet_addr","htons","select","WSAIoctl",
            "ws2_32","WS2_32","UDP","udp","DTLS","ECDH","secp224","natType",
            "28960","getchallenge","mmbook","mmstart","gamestateupdate"]
for k in keywords:
    hits = pe.find_cstr(k)
    print("%-14s %3d hits" % (k, len(hits)))
    for off, va in hits[:6]:
        if va is None: continue
        s = d[off:off+80].split(b"\0")[0]
        sec = pe.section_of(va)
        print("      %08X [%s] %s" % (va, sec.name if sec else "?", s[:70]))
