# -*- coding: utf-8 -*-
"""大厅数据源全面审计 —— 为"大厅大修"提供清单。

把大厅用到的每一类数据源列出来, 标注:
  名称 / 类型 / 编码 / 当前状态 / 是否占位 / 影响的客户端界面

数据来源:
  * 10/21 publisher files(客户端实际请求的文件名, 见 lobby_srv.log)
  * service/task 归属(见 _lobby_task_matrix.py)
  * 客户端 UIException(见 _dump_uiexception_bin.py)
"""
import json
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "publisher_files")

# 客户端在大厅初始化时实际请求的 publisher 文件(2026-10-06 实测)
PUBLISHER_FILES = [
    "mp_playlists_shipRetail_1.0.0.info",
    "activities_v1.info",
    "configs_s.info",
    "daily_challenge_config.info",
    "broadcast.info",
    "tlogconfig.info",
    "market_ui.info",
    "market-down.info",
    "whitelist_tester.info",
    "MOTD.info",
]

PLACEHOLDER_MARKERS = (b"No local", b"parser probe", b"not the recovered",
                       b"diagnostic", b"placeholder")


def classify(path):
    """返回 (编码, 明文长度, 是否占位, 预览)。"""
    b = open(path, "rb").read()
    enc, plain = "text", b
    try:
        if len(b) > 2 and b[0] == 0x78:
            plain = zlib.decompress(b)
            enc = "zlib"
    except Exception:
        enc = "zlib?"
    ph = any(m in plain for m in PLACEHOLDER_MARKERS)
    try:
        prev = plain.decode("utf-8")[:90].replace("\n", " | ")
    except Exception:
        prev = plain[:40].hex(" ")
    return enc, len(plain), ph, prev


def main():
    print("=" * 108)
    print("大厅数据源审计")
    print("=" * 108)
    print("%-38s %-8s %-8s %-6s %s" % ("文件", "编码", "明文字节", "占位", "预览"))
    print("-" * 108)
    n_ph = 0
    for fn in PUBLISHER_FILES:
        p = os.path.join(PUB, fn)
        if not os.path.exists(p):
            print("%-38s %-8s %-8s %-6s %s" % (fn, "-", "-", "-", "**缺失**"))
            n_ph += 1
            continue
        enc, ln, ph, prev = classify(p)
        if ph:
            n_ph += 1
        print("%-38s %-8s %-8d %-6s %s"
              % (fn, enc, ln, "是" if ph else "否", prev))
    print("-" * 108)
    print("publisher 文件: %d 个, 其中占位/缺失 %d 个"
          % (len(PUBLISHER_FILES), n_ph))
    print()

    print("=" * 108)
    print("service/task -> 数据源 / 客户端界面")
    print("=" * 108)
    rows = [
        ("80/70,107,119,173,174,232", "商城目录页", "空应答",
         "商城空白 + 军火箱页面重叠 + 大量买不了"),
        ("80/203", "库存", "已实现", "库存/拥有判定"),
        ("80/230", "玩家资产", "已实现", "军牌定制数据"),
        ("93/131,80/154", "购买", "已实现(有货币/Item 编号问题)", "背包/副武器/近战/名片购买"),
        ("10/21", "publisher 文件", "部分占位", "游玩清单/挑战/公告/活动"),
        ("10/12,10/20", "用户文件", "部分", "档案/云存储"),
        ("8/1,8/2,8/3", "玩家档案", "已实现", "等级/名片槽位"),
        ("11/4,11/13,21/5", "房间/匹配", "已实现", "靶场/房间"),
        ("3/46,48,53", "生涯/结算", "未映射", "战后结算"),
        ("9/5,9/14", "好友", "未映射", "好友列表"),
        ("28/1,28/4,29/10", "任务参数", "未映射", "任务/活动"),
        ("68/3,68/8,71/*", "遥测/日志", "未映射(可忽略)", "无 UI 影响"),
        ("102/1,5,7", "未知", "未映射", "未知"),
    ]
    for a, b, c, d in rows:
        print("  %-28s %-22s %-28s %s" % (a, b, c, d))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
