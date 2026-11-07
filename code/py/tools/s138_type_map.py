#!/usr/bin/env python3
"""s138_type_map: 把 0x636F3C 的 47 项跳转表与"构造器 vtable 写入点"对账,
   得出 type -> C++ 类名。判定: 处理函数起始 <= 构造点 < 下一个 case 入口。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

JT = 0x636F3C
tbl = [struct.unpack_from("<I", d, JT - VA + 4 * i)[0] for i in range(0x2F)]

# 来自 s138_vt_refs.py 的输出（vtable -> 类名 -> mov 立即数引用点）
INSTALL = {
    0xDC74F8: ("dwRoomMessageManifold", [0x633654, 0x634468, 0x63606D]),
    0xDC7504: ("dwRoomMessageText", [0x62595E, 0x625ACF]),
    0xDC7510: ("dwRoomSpyMessageText", [0x625ADD]),
    0xDC751C: ("dwRoomMessageStartGame", [0x62FB38, 0x634606, 0x634B03]),
    0xDC7528: ("dwRoomMessageStartGameFailed", [0x62F89C, 0x634C50]),
    0xDC7534: ("dwRoomMessageMemberInfoEXT", [0x6355D2]),
    0xDC7540: ("dwRoomMessageMemberInfoAdd", [0x63463B, 0x6356E6]),
    0xDC754C: ("dwRoomMessageMemberDetails", [0x635B5B, 0x635D68]),
    0xDC7558: ("dwRoomMessageMemberDetailsQuery", [0x635C6F]),
    0xDC7564: ("dwRoomMessageMemberDetailsNoUpdated", [0x635D3F]),
    0xDC757C: ("dwRoomMessageScore", [0x6339DC, 0x635DA3]),
    0xDC7588: ("dwRoomMessageJoinMemberInfos", [0x63447C, 0x634CF8]),
    0xDC7594: ("dwRoomMessageJoin", [0x634379, 0x634D8E]),
    0xDC75A0: ("dwRoomMessageJoinRequest", [0x626C3D, 0x626E90, 0x656117]),
    0xDC75AC: ("dwRoomMessageMyPartyInvitation", [0x6273C3]),
    0xDC75C4: ("dwRoomMessageSyncPartyPendingToNewMember", [0x62779F]),
    0xDC75D0: ("dwRoomMessageJoinWithMe", [0x6353D3, 0x63542E]),
    0xDC75DC: ("dwRoomMessageJoinWithParty", [0x63531E]),
    0xDC75F4: ("dwRoomMessageLeave", [0x635532]),
    0xDC760C: ("dwRoomMessageMemberList", [0x635803, 0x63587E]),
    0xDC7618: ("dwRoomMessageRoomInfo", [0x6359C5]),
    0xDC7624: ("dwRoomMessageReady", [0x635A21]),
    0xDC7630: ("dwRoomMessageStartCountingDown", [0x635E73]),
    0xDC763C: ("dwRoomMessageP2PInfo", [0x627F50, 0x635F49, 0x63609E]),
    0xDC7648: ("dwRoomMessageChangeTeam", [0x6281BF, 0x636428]),
    0xDC7654: ("dwRoomMessageChangeTeamRequest", [0x636612]),
    0xDC7660: ("dwRoomMessageSetPilot", [0x636729]),
    0xDC766C: ("dwRoomMessageVote", [0x6362A5]),
    0xDC7678: ("dwRoomMessagePlaylistWeights", [0x6367D7]),
    0xDC7684: ("dwRoomMessageRoomStateUpdated", [0x6345BE, 0x63683D]),
    0xDC7690: ("dwRoomMessageClanNameChange", [0x62869F]),
    0xDC769C: ("dwRoomMessagePlayerPrimaryWeaponCountChange", [0x636CE5]),
    0xDC76A8: ("dwRoomMessageInRoomStateChange", [0x636D93]),
    0xDC76B4: ("dwRoomMessageDMZLeagueTicketStateChange", [0x636E1E]),
    0xDC76C0: ("dwRoomMessageAvatarInfo", [0x6361E1]),
    0xDC76CC: ("dwRoomMessageUpdateDlcLevel", [0x633C18, 0x6368BB]),
    0xDC76D8: ("dwRoomMessageUpdateCreditRating", [0x636952]),
    0xDC76E4: ("dwRoomMessageUpdateWarGodData", [0x636A11]),
    0xDC7BE0: ("dwRoomMessage", [0x625946, 0x625ABA, 0x65610B]),
}

# 每个 case 的右界 = 下一个更大的 case 入口 (只考虑 case 表内地址)
cases = sorted(set(tbl))

print("| type | 处理函数 | 区间 | 构造点 | 类名 |")
print("|------|----------|------|--------|------|")
for t in range(0x2F):
    h = tbl[t]
    nxt = min([c for c in cases if c > h], default=h + 0x300)
    hits = []
    for vt, (nm, addrs) in INSTALL.items():
        for a in addrs:
            if h <= a < nxt:
                hits.append((a, vt, nm))
    if not hits:
        print("| 0x%02X | 0x%08X | 0x%08X..0x%08X | - | - |" % (t, h, h, nxt))
        continue
    for a, vt, nm in sorted(hits):
        print("| 0x%02X | 0x%08X | 0x%08X..0x%08X | 0x%08X | %s |" % (
            t, h, h, nxt, a, nm))
