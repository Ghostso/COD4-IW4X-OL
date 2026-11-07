# -*- coding: utf-8 -*-
"""构造正式的多模式游玩清单 mp_playlists_shipRetail_*.info。

背景:
  * 客户端在大厅初始化时向 10/21 要 `mp_playlists_shipRetail_1.0.0.info`。
  * 原文件只有 1 条 coop 占位, 且 `version 1` —— 客户端
    `MatchMakingStripView.as:343` 抛 #1009, 游玩清单空白。
  * 项目里已知真版本号 `PLAYLIST_VERSION = 796`(codol_crypto.py:345)。
  * 真实地图名来自 IIPS 包名: mp_village / mp_cross_fire / mp_highrise /
    mp_hardhat_sh / mp_terminal_cls / mp_nuked / mp_killhouse_sh /
    mp_rust_long / mp_shipment_long / mp_storm_spring / ...

文件是 zlib 压缩的纯文本; 这里生成明文后压缩写回。
可回滚: 原文件备份到 *.bak_before_playlists_<时间>。
"""
import os
import shutil
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "publisher_files")
TARGETS = ["mp_playlists_shipRetail_release.info",
           "mp_playlists_shipRetail_1.0.0.info"]
VERSION = 796

# ★ 地图名取自客户端内存里的**权威地图注册表**
#   (mem_linear\r_259D0000_06400000.bin @0x27FE3A0 附近的 sfproto_* / mp_* 串),
#   不是 IIPS 包名。两者不同: 包名 mp_hardhat_sh, 注册表名 mp_hardhat。
MAPS = ["mp_village", "mp_raid", "mp_terminal_cls", "mp_hardhat", "mp_dome",
        "mp_seatown", "mp_strike_sh", "mp_overwatch_sh", "mp_nightshift_sh",
        "mp_italy_sh", "mp_backlot_sh", "mp_wasteland_sh", "mp_arkaden_sh",
        "mp_derail_sh", "mp_fallen_sh", "mp_lookout_sh", "mp_resistance_sh",
        "mp_bootleg_sh", "mp_lockdown_sh", "mp_foundation_sh",
        "mp_interchange_sh", "mp_underground_sh", "mp_mission_sh",
        "mp_battlecity", "mp_mogadishu_sh", "mp_showdown", "mp_district",
        "mp_conflict", "mp_offshore", "mp_streamline", "mp_jardin",
        "mp_tunisia", "mp_qadeem_sh", "mp_mountain", "mp_meleeresort",
        "mp_nukearena_sh", "mp_subbase_sh", "mp_abandon_sh_mk"]

# gametype 取自客户端 OBJECTIVES_* / GM_* 表:
#   OBJECTIVES_WAR(TDM) DM(FFA) DOM(占点) HP(据点) TAG(击杀确认) SR(搜索救援)
# (playlist id, 名称, category, displayorder, minparty, maxparty, 每队人数, gametype, 地图)
# ★ category 用 0 —— 与能工作的 coop 占位同款; 之前用 1 可能不匹配客户端的分类表。
PLAYLISTS = [
    (1, "Team Deathmatch", 0, 1, 1, 6, 6, "war", MAPS[:12]),
    (2, "Free For All", 0, 2, 1, 8, 8, "dm", MAPS[:10]),
    (3, "Domination", 0, 3, 1, 6, 6, "dom", MAPS[4:16]),
    (4, "Hardpoint", 0, 4, 1, 6, 6, "hp", MAPS[8:20]),
    (5, "Kill Confirmed", 0, 5, 1, 6, 6, "tag", MAPS[12:24]),
    (6, "Search & Rescue", 0, 6, 1, 6, 6, "sr", MAPS[16:28]),
]

# ★ 2026-10-07: PvE / 剧情模式(PVE)入口。
#   实机证据(REF_LOBBY_KIT/lobby_srv.log 11:18:41):
#     客户端点剧情任务 -> 21/5 请求第 3 个 u32 == 10 -> `playlist=10`;
#     随后 6/14 的完整 mmstart 明确写 `g_gametype coop; map coop_training_mp_cargoship;`。
#   也就是说客户端自己把"剧情任务"解析成 playlist 10 / gametype coop。
#   而我们重建的 mp_playlists 里**根本没有 coop 类型, 也没有 playlist 10** ——
#   客户端拿到的 session(Playlist=10)无法与本表对齐, 匹配就停在"战斗开始"转圈。
#   (2026-10-07 之前的旧探针文件里确实有一条 `gametype coop` + `playlist 1`,
#    那次剧情列表可用; 本次重建把 playlist 1 换成了 TDM, 顺带把 coop 弄没了。)
#
# ★ coop 地图名取自客户端内置的 coop 任务注册表
#   (mem_linear/r_259D0000_06400000.bin 里 `coop_*` 串表), 全部本地已安装。
#   字段沿用 exe 0x6C5D14 起的 playlists 键表, 与 MP 条目同款。
# ★ 只加一条(playlist 10), 与客户端实测的 playlist=10 对齐; 先不铺量。
#   回滚: 本文件若不存在 -> 生成器退回纯 MP 版本(见 PVE_PLAYLISTS 开关)。
PVE_PLAYLISTS = [
    (10, "Coop Mission", "coop", 10, 1, 4, 4,
     ["coop_training_mp_cargoship",
      "coop_train_mp_firingrange",
      "coop_survival_mp_cross_fire",
      "coop_survival_mp_crash_tropical",
      "coop_survival_mp_fav_tropical",
      "coop_survival_mp_storm_spring",
      "coop_survival_mp_seatown",
      "coop_survival_mp_highrise",
      "coop_survival_mp_mountain",
      "coop_survival_mp_terminal_cls",
      "coop_survival_mp_subbase_sh",
      "coop_survival_mp_raid"]),
]
# 是否把 PvE playlist 并入清单: 由 REF_LOBBY_KIT/playlists-include-pve.on 控制。
INCLUDE_PVE_FLAG = os.path.join(ROOT, "playlists-include-pve.on")


def build_text():
    lines = [
        "// CODOL local lobby playlists (rebuilt 2026-10-06).",
        "// Maps verified present in the local IIPS packages.",
        "version %d" % VERSION,
        "",
    ]
    include_pve = os.path.exists(INCLUDE_PVE_FLAG)
    gametypes = []
    for _pid, _n, _c, _d, _mn, _mx, _per, gt, _maps in PLAYLISTS:
        if gt not in gametypes:
            gametypes.append(gt)
    if include_pve:
        for _pid, _n, gt, _d, _mn, _mx, _per, _maps in PVE_PLAYLISTS:
            if gt not in gametypes:
                gametypes.append(gt)
    for gt in gametypes:
        lines += ["gametype %s" % gt, "script %s" % gt,
                  'name english "%s"' % gt, ""]
    for pid, name, cat, order, mn, mx, per, gt, maps in PLAYLISTS:
        lines += [
            "playlist %d" % pid,
            'name english "%s"' % name,
            'description english "%s"' % name,
            "category %d" % cat,
            # ★ 以下字段来自 exe 0x6C5D14 起的 playlists 解析键表;
            #   之前只写了 name/category/displayorder/minparty/... 若干项,
            #   条目可能因缺字段被丢弃 -> 游玩清单空。
            "catinfo %d" % cat,
            "rule 0",
            "teambased %d" % (1 if gt != "dm" else 0),
            "hardcore 0",
            "displayorder %d" % order,
            "minparty %d" % mn,
            "maxparty %d" % mx,
            "maxhumanplayersperteam %d" % per,
            "numrounds 1",
            "buildversion 1649370",
            "unlockflag 0",
            "unlocklevelstart 0",
            "unlocklevelend 0",
            "levelrestricted 0",
            "homepagead 0",
            "buddy_playlist 0",
        ]
        for m in maps:
            lines.append("%s %s 1" % (m, gt))
        lines.append("")
    if include_pve:
        for pid, name, gt, order, mn, mx, per, maps in PVE_PLAYLISTS:
            lines += [
                "playlist %d" % pid,
                'name english "%s"' % name,
                'description english "%s"' % name,
                "category 0",
                "catinfo 0",
                "rule 0",
                "teambased 1",
                "hardcore 0",
                "displayorder %d" % order,
                "minparty %d" % mn,
                "maxparty %d" % mx,
                "maxhumanplayersperteam %d" % per,
                "numrounds 1",
                "buildversion 1649370",
                "unlockflag 0",
                "unlocklevelstart 0",
                "unlocklevelend 0",
                "levelrestricted 0",
                "homepagead 0",
                "buddy_playlist 0",
            ]
            for m in maps:
                lines.append("%s %s 1" % (m, gt))
            lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


def main():
    text = build_text()
    n_pve = len(PVE_PLAYLISTS) if os.path.exists(INCLUDE_PVE_FLAG) else 0
    print("明文 %d 字节, version=%d, %d 条 playlist (含 PvE %d 条)"
          % (len(text), VERSION, len(PLAYLISTS) + n_pve, n_pve))
    comp = zlib.compress(text, 9)
    print("压缩后 %d 字节" % len(comp))
    ts = time.strftime("%Y%m%d_%H%M%S")
    for fn in TARGETS:
        p = os.path.join(PUB, fn)
        if os.path.exists(p) and not os.path.exists(p + ".bak_before_playlists_" + ts):
            shutil.copy(p, p + ".bak_before_playlists_" + ts)
        with open(p, "wb") as f:
            f.write(comp)
        print("写出 %s (%d 字节, 已备份原文件)" % (p, len(comp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
