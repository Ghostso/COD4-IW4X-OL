#!/usr/bin/env python3
"""本地佐证 (3): bd* RTTI 类名全谱 (找 messaging 家族) + 服务注册函数名 + 0x66 邻近检查。"""
import re
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)

print("=== RTTI 类名: .?AV...@@ 中含 'essag' ===")
for m in re.finditer(rb"\.\?A[VU][ -~]{2,80}?@@", data):
    s = m.group(0).decode("latin1")
    if "essag" in s:
        print("  0x%08X  %s" % (m.start(), s))

print("\n=== RTTI 类名: 含 'bdMessaging' 或 'Messaging' ===")
for m in re.finditer(rb"\.\?A[VU][ -~]{2,80}?@@", data):
    s = m.group(0).decode("latin1")
    if "Messaging" in s or "bdMessag" in s:
        print("  0x%08X  %s" % (m.start(), s))

print("\n=== 服务注册相关串 ===")
for n in [b"addService", b"removeService", b"getService", b"registerService",
          b"ServiceManager", b"serviceId", b"ServiceID", b"serviceName",
          b"InstantMessage", b"SendInstantMessage", b"GetMessages", b"FetchMessages",
          b"MessagingService", b"messagingService"]:
    i=0; hits=[]
    while True:
        p=data.find(n,i)
        if p<0: break
        hits.append(p); i=p+1
        if len(hits)>=6: break
    if hits:
        print("  %-22s n=%d %s" % (n.decode(), len(hits), ["0x%X"%h for h in hits]))

print("\n=== 'instantmessage' 家族 (大小写不敏感, 前后串) ===")
low=data.lower()
i=0; hits=[]
while True:
    p=low.find(b"instantmessage",i)
    if p<0: break
    hits.append(p); i=p+1
    if len(hits)>=20: break
for p in hits:
    lo=p
    while lo>0 and 32<=data[lo-1]<127: lo-=1
    hi=p
    while hi<N and 32<=data[hi]<127: hi+=1
    print("  0x%08X  %r" % (p, data[lo:hi].decode("latin1")[:110]))
