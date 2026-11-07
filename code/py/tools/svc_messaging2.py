#!/usr/bin/env python3
"""在 E 镜像 + Base.dll + 磁盘 EXE 里搜 Messaging2 / messaging2 / 其他服务类名。"""
import os
PATHS = [
    (r"E:\codol_re\client_image_20261027.bin", "E_image"),
    (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll", "Base.dll"),
    (r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe", "EXE"),
]
needles = [b"Messaging2", b"messaging2", b"MessagingService", b"messaging_service",
           b"InstantMessage", b"instantmessage", b"BandwidthTest", b"ContentUnlock",
           b"TitleUtilities", b"RichPresence", b"Storage2", b"Profiles2", b"Friends2",
           b"Matchmaking2", b"Unknown66", b"bdMessaging", b"dwMessaging"]
for path, lab in PATHS:
    if not os.path.exists(path):
        print("[%s] MISSING" % lab); continue
    data = open(path, "rb").read()
    print("=== [%s] size=0x%X ===" % (lab, len(data)))
    for n in needles:
        i = 0; hits = []
        while True:
            p = data.find(n, i)
            if p < 0: break
            hits.append(p); i = p+1
            if len(hits) >= 5: break
        if hits:
            print("  %-20s n=%d %s" % (n.decode(), len(hits), ["0x%X"%h for h in hits]))
