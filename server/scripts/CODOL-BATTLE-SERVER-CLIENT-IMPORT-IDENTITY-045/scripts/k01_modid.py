# -*- coding: utf-8 -*-
"""045: robust module identification for the two IAT blocks in the recovered image."""
import sys, struct, os, glob, pefile
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
img=open(IMG,"rb").read()
GAME=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
cands=[]
for p in glob.glob(r"C:\Windows\SysWOW64\*.dll"):
    b=os.path.basename(p).lower()
    if b in ("ws2_32.dll","wsock32.dll","mswsock.dll","wship6.dll","wshtcpip.dll","napinsp.dll","pnrpnsp.dll","nsi.dll","iphlpapi.dll","dnsapi.dll"): cands.append(p)
for p in glob.glob(os.path.join(GAME,"*.dll")): cands.append(p)
lib={}
for p in cands:
    try:
        pe=pefile.PE(p,fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
        m={}
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if e.name: m[e.name.decode()]=e.address
        lib[p]=m
    except Exception: pass
print("candidate DLLs with exports:", len(lib))
# block A: slots 0xCA84D4..0xCA852C, expected ordinal->name from ws2_32
blockA=[("ntohs",15),("getsockname",6),("send",19),("recv",16),("select",18),("getpeername",5),("connect",4),("listen",13),("accept",1),("htonl",8),("ntohl",14),("shutdown",22),("inet_ntoa",12),("sendto",20),("recvfrom",17),("WSACleanup",116),("WSASetLastError",112),("__WSAFDIsSet",151),("getsockopt",7)]
slotsA=[0x8A84D4,0x8A84D8,0x8A84E0,0x8A84E4,0x8A84E8,0x8A84EC,0x8A84F0,0x8A84FC,0x8A8500,0x8A8504,0x8A850C,0x8A8510,0x8A8514,0x8A8518,0x8A851C,0x8A8520,0x8A8524,0x8A8528,0x8A852C]
blockB=[("WSAStartup",115),("gethostname",57),("WSAGetLastError",111),("ioctlsocket",10),("closesocket",3),("socket",23),("inet_ntoa",12),("htons",9),("bind",2),("setsockopt",21),("gethostbyname",52)]
slotsB=[0x8A8534,0x8A8538,0x8A853C,0x8A8540,0x8A8544,0x8A8548,0x8A854C,0x8A8550,0x8A8554,0x8A8558,0x8A855C]
def score(slots, expected, label):
    print("=== %s ==="%label)
    best=[]
    for p,m in lib.items():
        votes={}
        for rva,(nm,o) in zip(slots,expected):
            v=struct.unpack("<I",img[rva:rva+4])[0]
            e=m.get(nm)
            if e is None: continue
            b=v-e
            votes[b]=votes.get(b,0)+1
        if votes:
            b,c=max(votes.items(), key=lambda kv:kv[1])
            best.append((c,len(expected),os.path.basename(p),b))
    best.sort(reverse=True)
    for c,tot,nm,b in best[:6]: print("   %2d/%d  %-28s base=%08X"%(c,tot,nm,b))
score(slotsA,blockA,"block A")
score(slotsB,blockB,"block B")
print()
print("=== raw image dwords for block A and B ===")
for lab,slots in (("A",slotsA),("B",slotsB)):
    print("  ",lab,[ "%08X"%struct.unpack("<I",img[r:r+4])[0] for r in slots])
