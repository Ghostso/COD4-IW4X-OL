#!/usr/bin/env python3
"""129 卷: 54 条模板名 vs 65 个日志点事件名 的双向差集.
判定口径: 模板名 = NUL 串且匹配 ^[A-Z][A-Za-z0-9_]{2,40}\| 且后半含 % 或 ${ 或为空.
"""
import re, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")

# 1) 全镜像"NUL 串"普查
FALSE_POS = {"TdO","LvO","D_q"}
tmpl = {}
i = 0
while True:
    j = d.find(b"\x00", i)
    if j < 0 or j+1 >= N: break
    s = d[j+1: d.find(b"\x00", j+1)]
    i = j+1
    if len(s) < 4: continue
    if not all(32 <= c < 127 for c in s): continue
    m = re.match(rb"([A-Z][A-Za-z0-9_]{2,40})\|(.*)", s)
    if not m: continue
    body = m.group(2)
    if not (b"%" in body or b"${" in body or body == b""): continue
    name = m.group(1).decode()
    off = j+1
    tmpl.setdefault(name, []).append((off, s.decode("latin1")))
out("NUL 串口径下模板名: %d" % len(tmpl))

SITES_DIR = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\telemetry_sites.txt"
sites = set()
try:
    for line in open(SITES_DIR, encoding="utf-8"):
        line = line.strip()
        if line: sites.add(line)
except FileNotFoundError:
    out("(缺 %s, 先用下面的已知清单)" % SITES_DIR)
    sites = set("""ChannelSubscriptionFail Chat ChatMessageReport ClanCreate ClanDismiss ClanNameChange ClanProfileUpdate ClanUpdate ClientDisconnect ClientInvalidBuild ClientLoadout ClientLogin ClientOffline ClientOfflineLastPacket ClientOfflinePackets ClientReconnected ClientSettingsGpu CreateRoom CreditRating CreditRatingBlock LoadoutChangeEvent MapVote MatchMaking MatchMakingJoin MissingLocalizedString NameChange OnBoarding PreprocessGroupInfoResult ProfileEvent SendLoudSpeaker TimerError UIException UIFriendEvent UIFriendList UIInitialGameMode UIKeySetting UserWarning WarGodMatchEnd WarGodMatchMaking WarGodMatchStart ClientLoadTime ExpectedNetConfigStringMismatch OperationEventXPGP STUNServerPingResult SkinnedModelExceeded TencentCrossInit UserSettings""".split())

out("日志点事件: %d" % len(sites))
out("")
out("=== 日志点有、NUL 普查没有 ===")
only_sites = sorted(sites - set(tmpl))
for n in only_sites: out("   %s" % n)
out("")
out("=== NUL 普查有、日志点没有 ===")
only_tmpl = sorted(set(tmpl) - sites)
for n in only_tmpl:
    out("   %-40s %s" % (n, [hex(o) for o, s in tmpl[n]]))
out("")
out("=== 两边都有 (%d) ===" % len(sites & set(tmpl)))
for n in sorted(sites & set(tmpl)):
    out("   %-40s %s" % (n, [hex(o) for o, s in tmpl[n]]))
