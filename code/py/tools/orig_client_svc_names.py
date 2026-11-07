#!/usr/bin/env python3
"""原版客户端三镜像里找 Demonware 服务名目录:
- 'Messaging2' / 'Messaging::' / 'Xxx::taskN' 形态
- 关键: 原版客户端是否自带服务名->号 表
"""
import os, re
PATHS = [
    (r"E:\codol_re\client_image_20261027.bin", "E_image(runtime)"),
    (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll", "Base.dll"),
    (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe", "EXE(disk)"),
]
needles = [b"Messaging2", b"Messaging::", b"MessagingService", b"::task",
           b"readQueuedMessages", b"sendInstantMessage", b"sendGlobalInstantMessage",
           b"getUnreadCount", b"getPublisherFile", b"listAllPublisherFiles",
           b"getBalanceLegacy", b"readStatsByRank", b"getServerTime",
           b"RecoveredEmpty", b"RecoveredCatalog"]
for path, lab in PATHS:
    if not os.path.exists(path):
        print("[%s] MISSING" % lab); continue
    data = open(path, "rb").read()
    print("=== [%s] size=0x%X ===" % (lab, len(data)))
    for n in needles:
        i=0; hits=[]
        while True:
            p=data.find(n,i)
            if p<0: break
            hits.append(p); i=p+1
            if len(hits)>=6: break
        if hits:
            print("  %-26s n=%d %s" % (n.decode(), len(hits), ["0x%X"%h for h in hits]))
    print()
