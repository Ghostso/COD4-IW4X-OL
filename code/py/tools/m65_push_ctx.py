#!/usr/bin/env python3
"""dump subscribe 串上下文 + 追加关键字(推送/队列/事件订阅相关)."""
import re
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read()
def strs(lo,hi):
    out=[];i=lo
    while i<hi:
        e=d.find(b"\x00",i)
        if e<0 or e>hi: break
        s=d[i:e]
        if s and all(32<=b<127 for b in s) and len(s)>=3: out.append((i,s.decode()))
        i=e+1
    return out
print("=== 0x9DC200-0x9DC360 附近串 ===")
for off,s in strs(0x9DC200,0x9DC360):
    print("  file0x%X (VA 0x%X)  %r"%(off,off+0x400000,s))

# 更多关键字
words=[b"onEvent",b"eventID",b"eventId",b"notification",b"Notification",
       b"notify",b"Notif",b"dispatchEvent",b"handler",b"Handler",
       b"tickRate",b"pollInterval",b"keepalive",b"Keepalive",b"KeepAlive",
       b"timeout",b"lastPoll",b"nextPoll",b"Poll"]
print("\n=== 追加关键字 ===")
for w in words:
    hits=[];i=0
    while True:
        p=d.find(w,i)
        if p<0: break
        hits.append(p);i=p+1
        if len(hits)>=5: break
    print("  %-16s %s"%(w.decode(),["0x%X"%h for h in hits] or "—"))
