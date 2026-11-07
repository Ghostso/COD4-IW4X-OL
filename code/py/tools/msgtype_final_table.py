#!/usr/bin/env python3
"""最终类型号表：44 个 dwRoomMessage 类 + 3 个保留缺口 + P2PInfo。

数据来源：
  - _byte_papers/msgtype_stack2.txt（43 类来自栈上工厂）
  - 人工依据代码补正：
      dwRoomMessageText  = 2   (0x62b953 `mov [ebp-0x1c],2` + 换 vfptr)
      dwRoomMessageP2PInfo = 19 (0x627f49 `mov [esi+4],0x13` + `[esi]=0xdc763c`)
"""
import sys

ROWS = [
    (0, "dwRoomMessage", "基类；本身也可发送（0x62b8f8）"),
    (1, "dwRoomMessageManifold", ""),
    (2, "dwRoomMessageText", ""),
    (3, "dwRoomMessageStartGame", "★ 战斗开始"),
    (4, "dwRoomMessageStartGameFailed", ""),
    (5, "dwRoomMessageJoin", ""),
    (6, "dwRoomMessageJoinRequest", ""),
    (7, "dwRoomMessageJoinWithMe", ""),
    (8, "dwRoomMessageLeaveWithMe", ""),
    (9, "dwRoomMessageLeave", ""),
    (10, "dwRoomMessageMemberInfoAdd", "★ 含昵称串"),
    (11, None, "★ 保留，无类使用"),
    (12, "dwRoomMessageMemberInfoEXT", ""),
    (13, "dwRoomMessageRequestMemberList", ""),
    (14, "dwRoomMessageMemberList", "★ 成员名单"),
    (15, "dwRoomMessageRoomInfo", "★ 房间信息"),
    (16, "dwRoomMessageReady", ""),
    (17, "dwRoomMessageStartCountingDown", ""),
    (18, "dwRoomMessageAvatarInfo", ""),
    (19, "dwRoomMessageP2PInfo", "★ dwroom_serializers 漏收，本卷补"),
    (20, "dwRoomMessageChangeTeam", ""),
    (21, "dwRoomMessageChangeTeamRequest", ""),
    (22, "dwRoomMessagePlaylistWeights", ""),
    (23, "dwRoomMessageRoomStateUpdated", ""),
    (24, "dwRoomMessageScore", ""),
    (25, None, "★ 保留，无类使用"),
    (26, "dwRoomMessageVote", ""),
    (27, "dwRoomMessageSetPilot", ""),
    (28, "dwRoomMessageCard", ""),
    (29, "dwRoomMessageMemberDetails", ""),
    (30, "dwRoomMessageMemberDetailsQuery", ""),
    (31, "dwRoomMessageMemberDetailsNoUpdated", ""),
    (32, "dwRoomMessageUpdateDlcLevel", ""),
    (33, "dwRoomMessageUpdateCreditRating", ""),
    (34, "dwRoomMessageUpdateWarGodData", ""),
    (35, "dwRoomMessageQQMembership", ""),
    (36, "dwRoomMessageNetcafePrivileges", ""),
    (37, "dwRoomMessageJoinMemberInfos", ""),
    (38, "dwRoomMessageClanNameChange", ""),
    (39, "dwRoomMessagePlayerPrimaryWeaponCountChange", ""),
    (40, "dwRoomMessageMyPartyInvitation", ""),
    (41, "dwRoomMessageMyPartyInvitationRejected", ""),
    (42, "dwRoomMessageSyncPartyPendingToNewMember", ""),
    (43, "dwRoomMessageJoinWithParty", ""),
    (44, "dwRoomSpyMessageText", "★ 类名不同前缀 dwRoomSpy"),
    (45, "dwRoomMessageInRoomStateChange", ""),
    (46, "dwRoomMessageDMZLeagueTicketStateChange", ""),
]


def main():
    print("%-4s %-4s %-46s %s" % ("#", "hex", "class", "备注"))
    for n, c, note in ROWS:
        print("%-4d %-4s %-46s %s" % (
            n, "0x%02x" % n, c if c else "<保留>", note))
    used = [n for n, c, _ in ROWS if c]
    print("\n共 %d 个号，%d 个有名类，%d 个保留" % (
        len(ROWS), len(used), len(ROWS) - len(used)))
    with open("_byte_papers/msgtype_FINAL.tsv", "w", encoding="utf-8") as f:
        f.write("type\thex\tclass\tnote\n")
        for n, c, note in ROWS:
            f.write("%d\t0x%02x\t%s\t%s\n" % (n, n, c or "", note))


if __name__ == "__main__":
    main()
