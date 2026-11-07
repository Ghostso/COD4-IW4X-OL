# -*- coding: utf-8 -*-
"""TASK-034: local connection-state globals evidence (read-only)."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
print("== raw bytes of the state globals named by the code we disassembled ==")
for va in (0x76446B0,0x76446A2,0x76446D8,0x331C0C8,0x82C3B58,0xC7AF6A8,0xE3F240):
    r=va-BASE
    print("  VA %08X (off %08X) : %s" % (va,r,d[r:r+8].hex() if 0<=r<len(d) else "OUT"))
print()
print("== how many code sites read [0x76446b0] (connection state) ==")
tb=struct.pack("<I",0x76446B0); n=0; first=[]
s=0
while True:
    i=d.find(tb,s)
    if i<0: break
    n+=1
    if len(first)<12: first.append(i)
    s=i+1
print("  imm32 refs: %d  first: %s" % (n,["%X"%x for x in first]))
print()
print("== 'EXE_' error-code strings reachable from the OOB path (state machine outcomes) ==")
for s_ in [b"EXE_HOSTUNREACH",b"EXE_CLIENTFAILEDTOCHALLENGE",b"EXE_MATCHENDED",b"EXE_DISCONNECTED"]:
    i=d.find(s_); print("  %-30s %s" % (s_.decode(), ("VA %08X"%(i+BASE)) if i>=0 else "not found"))
