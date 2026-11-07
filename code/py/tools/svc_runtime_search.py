#!/usr/bin/env python3
"""在 client_runtime.bin (241MB, 内存展开镜像) 里搜服务类名/服务名串表。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin"
data = open(PATH, "rb").read()
print("size = 0x%X" % len(data))

classes = ["LeaderboardService","MarketService","MatchService","PartyService",
  "ChallengeService","CharacterLoadoutService","ClanService","CommonService",
  "CommunicationService","CommunityService","InGameService","LoginService",
  "OnboardService","PublisherStorageService","RewardService","SettingsService",
  "TutorialService","UIStencilService","WeaponLoadoutService","ServiceBase",
  "ServiceManager","ServiceID","ServiceId"]

def findall(b):
    out=[]; i=0
    while True:
        p=data.find(b,i)
        if p<0: return out
        out.append(p); i=p+1

for c in classes:
    hs=findall(c.encode())
    print("  %-26s n=%d %s" % (c,len(hs),["0x%X"%h for h in hs[:6]]))
