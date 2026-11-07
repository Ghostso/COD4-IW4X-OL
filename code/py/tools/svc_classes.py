#!/usr/bin/env python3
"""在 7.8MB 客户端 EXE 里搜 Service 类名 (RTTI .?AV<Name>@@) 及裸串。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()

svc_classes = ["LeaderboardService","MarketService","MatchService","PartyService",
  "ChallengeService","CharacterLoadoutService","ClanService","CommonService",
  "CommunicationService","CommunityService","InGameService","LoginService",
  "OnboardService","PublisherStorageService","RewardService","SettingsService",
  "TutorialService","UIStencilService","WeaponLoadoutService","ServiceBase",
  "ServiceManager","ServiceID","DwService","dwService"]

print("=== 裸串搜索 ===")
for s in svc_classes:
    b = s.encode()
    hits = []
    i = 0
    while True:
        p = data.find(b, i)
        if p < 0: break
        hits.append(p); i = p + 1
    print("  %-26s n=%d %s" % (s, len(hits), ["0x%X"%h for h in hits[:6]]))

print("\n=== RTTI 名 .?AV<Name>@@ 搜索 ===")
for s in svc_classes:
    for form in (".?AV"+s+"@@", ".?AV"+s+"@@"):
        b = form.encode()
        if b in data:
            print("  FOUND %s" % form)
