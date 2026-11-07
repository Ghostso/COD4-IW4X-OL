# -*- coding: utf-8 -*-
import struct, re
import img
IMG = img._IMG; BASE = img.BASE
def findall(s):
    out=[];st=0
    while True:
        i=IMG.find(s,st)
        if i<0:break
        out.append(BASE+i);st=i+1
    return out
def findstr(s):
    # ascii and utf16
    a=findall(s.encode("latin1")); u=findall(s.encode("utf-16le"))
    return a,u
for s in ["WSASocket","WSAStartup","ws2_32","WS2_32","sendto","recvfrom","bind","socket","closesocket","select","WSAEventSelect","PvE","battle","Battle","BATTLE","DTLS","ECDH","secp224","28960","GAME_IP","GAME_PORT"]:
    a,u = findstr(s)
    print("%-12s ascii=%d %s" % (s, len(a), [hex(x) for x in a[:6]]))
    if u: print("             utf16=%d %s" % (len(u), [hex(x) for x in u[:6]]))
