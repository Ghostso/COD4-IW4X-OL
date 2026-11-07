#!/usr/bin/env python3
"""137 重算: 按 [COL][vf0=0x693DD0][vf1=handler] 同记录配对, 输出**正确**的 AS_* 名字↔handler 表.
(修正 131 卷按 [f+4]/[f+8] 取值造成的名字列错位一格)"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def rd(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f < N - 4 else None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def name_of_vt(vt):
    col = rd(vt - 4)
    if not col or not (VA <= col < VA + N):
        return None
    ti = rd(col + 0x0C)
    if not ti or not (VA <= ti < VA + N):
        return None
    return cstr(ti + 8)


rows = []
pos = 0
pat = struct.pack("<I", 0x00693DD0)
while True:
    i = d.find(pat, pos)
    if i < 0:
        break
    pos = i + 1
    vf0 = VA + i
    fn = rd(vf0 + 4)
    nm = name_of_vt(vf0)
    if nm and nm.startswith(".?") and fn and VA <= fn < VA + N:
        rows.append((nm, fn))

print("配对成立的行数 =", len(rows))
UI = ["JoinRoom", "QuickMatch", "EnableRoomListEvent", "EnableQuickMatchEvent",
      "IsLogOnLobby", "TencentGetAASRecord", "UILog", "SetRecommendedSetting",
      "SetTierSetting", "SetVideoSetting", "IIPS_Response", "JumpGame",
      "GetGroupCounts", "GetLockedMapsFromPublisher", "GetServerTime",
      "GetPlayListIdForNum", "GetPlayListNumForId", "IsDMZGametype",
      "CreateRoom", "CancelList", "TencentReportPlayer", "TencentSanitizeString",
      "TencentReportBadLanguage", "MainMenuWillReload"]
print("\n-- UI/大厅族(正确配对) --")
for nm, fn in rows:
    short = nm.split("@@")[0].split("AV")[-1].split("AU")[-1]
    if short in UI:
        print("   %-30s 0x%08X" % (short, fn))
print("\n-- 名字含 'AS_' 的前 60 条(正确配对) --")
n = 0
for nm, fn in rows:
    short = nm.split("@@")[0].split("AV")[-1].split("AU")[-1]
    if short.startswith("AS_"):
        print("   %-46s 0x%08X" % (short, fn))
        n += 1
        if n >= 60:
            break
print("   ... AS_* 共 %d 条" % sum(
    1 for nm, _ in rows
    if nm.split("@@")[0].split("AV")[-1].split("AU")[-1].startswith("AS_")))
