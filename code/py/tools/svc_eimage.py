#!/usr/bin/env python3
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()
print("size = 0x%X" % len(data))
classes = ["LeaderboardService","MarketService","MatchService","PartyService",
  "ChallengeService","CharacterLoadoutService","ClanService","CommonService",
  "CommunicationService","CommunityService","InGameService","LoginService",
  "OnboardService","PublisherStorageService","RewardService","SettingsService",
  "TutorialService","UIStencilService","WeaponLoadoutService","ServiceBase",
  "ServiceManager","ServiceID","ServiceId","addService","removeService"]
def findall(b):
    out=[]; i=0
    while True:
        p=data.find(b,i)
        if p<0: return out
        out.append(p); i=p+1
for c in classes:
    hs=findall(c.encode())
    print("  %-26s n=%d %s" % (c,len(hs),["0x%X"%h for h in hs[:6]]))
