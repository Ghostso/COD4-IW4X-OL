#!/usr/bin/env python3
"""137 修正表: 同记录配对(COL↔vf1) 下, 输出
(a) vf1 == 0x8435E0 的**正确名字**清单(空实现对象)
(b) UI/大厅族(带 AS_ 前缀)名字↔handler
(c) 若干锚点(AS_JoinRoom 的 vf1 等)"""
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


def short(nm):
    if not nm:
        return None
    s = nm
    for sep in ("AV", "AU"):
        if sep in s:
            s = s.split(sep, 1)[1]
    return s.split("@@")[0]


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
    col = rd(vf0 - 4)
    nm = None
    if col and VA <= col < VA + N:
        ti = rd(col + 0x0C)
        if ti and VA <= ti < VA + N:
            nm = cstr(ti + 8)
    if nm and nm.startswith(".?") and fn and VA <= fn < VA + N:
        rows.append((short(nm), fn, vf0))

print("行数 =", len(rows))
same = [r for r in rows if r[1] == 0x8435E0]
print("\n(a) vf1 == 0x8435E0 的行: %d 个" % len(same))
for nm, fn, vf0 in same:
    print("    %-42s vf0=0x%08X" % (nm, vf0))

UI = ["AS_JoinRoom", "AS_QuickMatch", "AS_EnableRoomListEvent", "AS_EnableQuickMatchEvent",
      "AS_IsLogOnLobby", "AS_TencentGetAASRecord", "AS_UILog", "AS_SetRecommendedSetting",
      "AS_SetTierSetting", "AS_SetVideoSetting", "AS_IIPS_Response", "AS_JumpGame",
      "AS_GetGroupCounts", "AS_GetLockedMapsFromPublisher", "AS_GetServerTime",
      "AS_GetPlayListIdForNum", "AS_GetPlayListNumForId", "AS_IsDMZGametype",
      "AS_CreateRoom", "AS_CancelList", "AS_TencentReportPlayer",
      "AS_TencentSanitizeString", "AS_TencentReportBadLanguage", "AS_MainMenuWillReload"]
print("\n(b) UI/大厅族(修正配对):")
for nm, fn, vf0 in rows:
    if nm in UI:
        print("    %-34s 0x%08X   (vf0=0x%08X)" % (nm, fn, vf0))

print("\n(c) 锚点: vf0=0xDC8910 的行 ->", [r for r in rows if r[2] == 0xDC8910])
print("    0xDC8910 的 COL 名 =", short(
    cstr(rd(rd(0xDC8910 - 4) + 0x0C) + 8) if True else None))
