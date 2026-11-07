#!/usr/bin/env python3
"""在 Base.dll (60MB) 里找服务类名与可能的 {id,name} 表。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
data = open(PATH, "rb").read()
print("size = 0x%X" % len(data))

classes = ["LeaderboardService","MarketService","MatchService","PartyService",
  "ChallengeService","CharacterLoadoutService","ClanService","CommonService",
  "CommunicationService","CommunityService","InGameService","LoginService",
  "OnboardService","PublisherStorageService","RewardService","SettingsService",
  "TutorialService","UIStencilService","WeaponLoadoutService","ServiceBase",
  "ServiceManager","ServiceID"]

def findall(b):
    out=[]; i=0
    while True:
        p=data.find(b,i)
        if p<0: return out
        out.append(p); i=p+1

print("=== 裸串 ===")
for c in classes:
    hs=findall(c.encode())
    print("  %-26s n=%d %s" % (c,len(hs),["0x%X"%h for h in hs[:5]]))

print("\n=== RTTI ===")
for c in classes:
    for form in (".?AV"+c+"@@",):
        hs=findall(form.encode())
        if hs:
            print("  %-30s n=%d %s" % (form,len(hs),["0x%X"%h for h in hs[:5]]))
