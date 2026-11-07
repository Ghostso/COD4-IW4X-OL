#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit INVESTIGATION_PACKAGES/CODOL-ISSUE-XXXX/ for the P0 batch.

No FIX_PACKAGES are emitted in this batch: FIX_READINESS_MATRIX.csv has
can_fix_now = false for all 7 P0 issues, so producing a fix package would
misrepresent an investigation as a repair task.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "INVESTIGATION_PACKAGES")

# issue -> dict of the 8 required sections
PACKAGES = {
    "CODOL-ISSUE-0020": dict(
        title="战斗服零收包：分离地图变量与入口路径变量",
        known=[
            "战斗服 UDP 28960 监听正常，协议栈可用（10-26 有 8 轮全链路 RX）。",
            "战斗服 `codol_battle_service_on_packet` 对任何包都会打日志；失败轮零日志 ⇒ 包没来。",
            "34 次带 mmstart 的运行里，`map==coop_train_mp_firingrange && 不建房` 与 RX 出现 100% 共变（8/8 vs 26/26）。",
            "区间 B（10-26 23:31 起）带 map 仍零 RX ⇒ '没有 map' 不是充分条件。",
            "区间 B 完全没有 102/7 ⇒ '102/7 回全 0' 不是区间 B 的原因。",
            "区间 B 未推 StartGame ⇒ '推 StartGame 打断' 被排除。",
            "成功轮根目录是沙箱 `sandbox_ifs1_20260923`；10-27 12:00 起是本体 `COD OL`。",
        ],
        unknown=[
            "地图与入口路径在全部历史数据里完全共线，无法分离。",
            "客户端在哪个函数决定'不建 socket'。",
            "沙箱 vs 本体是否也是共因（区间 B 在同一沙箱里就失败了）。",
            "`task_params.txt` 里 `6c080800000002000000000000000500000000` 是谁写的、什么语义。",
        ],
        hypotheses=[
            ("H1", "所选地图不在客户端可加载集合 ⇒ 不连", "HIGH_UNPROVEN"),
            ("H2", "入口路径（PvE 直接开局 vs 房间内开始）决定是否连接", "HIGH_UNPROVEN"),
            ("H3", "102/7 回全 0", "EXCLUDED"),
            ("H4", "memberCount", "EXCLUDED"),
            ("H5", "mmstart 推 StartGame", "EXCLUDED"),
            ("H6", "战斗服没起/端口占用", "EXCLUDED"),
            ("H7", "沙箱 vs 本体", "EXCLUDED_FOR_REGIME_B"),
        ],
        sources=[
            (r"CODOL_SERVER_319_20261021\src\battle\battle_service.c", "1061-1140",
             "codol_battle_service_on_packet — 唯一的 UDP 入口，失败轮零日志的观测点"),
            (r"CODOL_SERVER_319_20261021\src\main.c", "157-175",
             "主循环：transport_poll → battle_service_on_packet"),
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "1090-1150",
             "mmstart 分支：写 coop_map.txt / active_room.json"),
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "789-849",
             "findSessions：用 coop_map.txt 决定回哪张图"),
        ],
        experiment=dict(
            id="E1 → E2 → E3",
            steps=[
                "E1：完全复刻 10-26 22:08 成功条件（沙箱根 + coop_map.txt=coop_train_mp_firingrange + PvE 直接开局 + 不建房）。",
                "E2：同 E1，只把地图换成 coop_training_mp_cargoship。",
                "E3：同 E1，只把入口换成 BOT 房间。",
            ],
            expected="E1 应出现 TX_NAT_REPLY；E2/E3 的结果决定归因。",
            judgment=[
                ("E1 RX, E2 RX, E3 零", "入口路径是根因 (H2)"),
                ("E1 RX, E2 零, E3 RX", "地图是根因 (H1)"),
                ("E1 RX, E2 零, E3 零", "两者都必要"),
                ("E1 RX, E2 RX, E3 RX", "都不是；转查 U4/U5/U6"),
                ("E1 零", "成功基线已不可复现，先修环境"),
            ],
            prerequisites=[
                "提权 agent 在线（CODOLServer/logs/elevated_agent.json）",
                "run_codol_001/run_frozen_chain_once.py --authorize-next-launch",
                "沙箱根仍存在，或明确改用本体并在结论中标注 D4 也变成变量",
                "用户需在 UI 上走 PvE 剧情入口（不是 BOT 房间）",
            ],
            caution="需要启动官方客户端，属于需授权操作；本审计未执行。",
        ),
    ),
    "CODOL-ISSUE-0021": dict(
        title="mmstart 的 playlist 语义与地图缺失",
        known=[
            "成功形态：`mmstart … g_gametype coop; g_difficulty 1; ; map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;`",
            "失败形态（区间 D）：`mmstart … playlist 37; start_map_rotate_once 7; roomChatChannelID 1800154382;`",
            "官方 playlist 表 123 项里没有 37，也没有 50。",
            "服务端在 `_map` 为空时静默跳过 coop_map.txt 写入（源码行 1116）。",
            "findSessions 发生在 mmstart 之前，所以 coop_map 自校正只在下一轮生效。",
        ],
        unknown=[
            "`2486/3265/2489/2574/2500/2654` 这组编号键的语义。",
            "`37` 是 playlist ID、排序下标、还是轮换序号。",
            "客户端为什么在该入口选择发 playlist 而不是 map。",
        ],
        hypotheses=[
            ("H1", "playlist 编号单独不足以定位地图", "MEDIUM"),
            ("H2", "37 是排序下标而非官方 ID", "MEDIUM"),
            ("H3", "房间入口本身让客户端走另一条分支", "HIGH_UNPROVEN"),
        ],
        sources=[
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "1101-1116",
             "map/gametype 正则与静默跳过"),
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "789-849",
             "findSessions 使用 coop_map override"),
        ],
        experiment=dict(
            id="E2 + E4",
            steps=[
                "E2（与 0020 共用）：换地图，保持入口不变。",
                "E4：在同一 UI 位置选择不同的播放列表项，记录 `playlist <n>` 与 `start_map_rotate_once <m>` 的变化。",
            ],
            expected="E4 应能画出一张 'UI 选择 → 编号' 对照表。",
            judgment=[
                ("E4 得到一致映射", "H2 可判定，编号语义可写进文档"),
                ("E4 显示编号随列表位置而非 ID 变化", "H2 成立"),
                ("E2 零 RX", "本 Issue 是 0020 的根因之一，升回 P0 核心"),
            ],
            prerequisites=["同 0020（需授权启动）"],
            caution="E4 需要用户在 UI 上多次选择不同播放列表。",
        ),
    ),
    "CODOL-ISSUE-0074": dict(
        title="102/7 应答不被接受（建议从 P0 降为 P2）",
        known=[
            "成功轮与第一次失败轮都**没有** 102/7（`Select-String '102/'` 计数 = 0）。",
            "区间 C 有 102/7（回 555 B 全 0），客户端每 5 秒重发。",
            "区间 D 已改为'不处理'，仍零 RX。",
            "服务端实现的 `val` 恒为 0，没有任何真实值来源。",
        ],
        unknown=["客户端判定 555 B 应答无效的具体条件。", "`[44..49]` 的真实值来源。"],
        hypotheses=[
            ("H1", "102/7 回全 0 导致不连", "EXCLUDED"),
            ("H2", "应答格式本身被拒（重发）", "OPEN_LOCAL"),
        ],
        sources=[
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "1181-1226",
             "102/7 构造，val 恒 0"),
        ],
        experiment=dict(
            id="E5",
            steps=[
                "在成功形态（PvE + firingrange）的 kit 里主动加回 555 B 全 0 回显。",
                "若无法强制注入（成功轮客户端不发 102/7），则本 Issue 保持 UNKNOWN 影响。",
            ],
            expected="若仍出现 RX ⇒ 102/7 与连接无关。",
            judgment=[
                ("仍 RX", "H1 彻底排除，本 Issue 降为 P2"),
                ("RX 消失", "重大发现：102/7 在成功形态下也能打断连接"),
            ],
            prerequisites=["同 0020"],
            caution="—",
        ),
    ),
    "CODOL-ISSUE-0012": dict(
        title="MyEventHandler 实例数必须重新测量（证据已陈旧）",
        known=[
            "memberCount=0 的那次运行里，vtable 0x00DC78F0 零实例（EARLIEST_20261027_123806）。",
            "memberCount=1 之后 dwRoomMatchUber（0x00DC795C）确实出现了（EARLIEST2_20261027_132645）。",
            "按原因果图，MyEventHandler 缺失本应切断 dwRoomMatchUber 的创建 —— 但后者出现了。",
            "`0x63E5D6` 有无条件写 `[0x82E1514]`，在分配之前；实测为 0 ⇒ 函数体当时没跑。",
        ],
        unknown=[
            "当前（memberCount=1）状态下 MyEventHandler 是否存在。",
            "若不存在，dwRoomMatchUber 是经由哪条路径创建的。",
        ],
        hypotheses=[
            ("H0", "memberCount=1 后 MyEventHandler 其实已有实例", "MUST_TEST_FIRST"),
            ("H1", "Init 依赖某条大厅应答，该应答未发", "MEDIUM"),
        ],
        sources=[
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "1002-1010",
             "11/13 createRoom 的 memberCount=1"),
        ],
        experiment=dict(
            id="E6",
            steps=[
                "用当前正式 kit 启动客户端（需授权）。",
                "用 CODOLServer/_mainline/dump_earliest.py <outdir> 200 6 抢早期句柄。",
                "扫描 vtable 0x00DC78F0 的实例数。",
                "同转储扫描 0x00DC795C 作阳性对照。",
            ],
            expected="若 H0 成立，0x00DC78F0 实例数 ≥ 1。",
            judgment=[
                ("0x00DC78F0 ≥ 1", "H0 成立；本 Issue 作废"),
                ("0x00DC78F0 = 0 且 0x00DC795C ≠ 0", "存在第二条创建路径（重大发现）"),
                ("两者都为 0", "该次转储没覆盖到建房时刻"),
            ],
            prerequisites=[
                "转储窗口需覆盖建房时刻（t≈80–100 s），而早期窗口约 t≈24 s —— 这是已知障碍",
            ],
            caution="若窗口不重叠，需要先解决 ISSUE-0045 的转储可行性。",
        ),
    ),
    "CODOL-ISSUE-0009": dict(
        title="准备按钮无反应：先用一次低成本观察二分整个问题",
        known=[
            "点击不产生任何上行（该轮 11/4 只有 4 条，无准备）。",
            "本地 UI 状态也不变。",
            "`ui_mp.ff` 加密（熵 7.95–8.00）；`.gfx` 无工具。",
            "163 个 AS_* 类名存在，但 TD→COL 引用 0 处、代码引用 0 处。",
            "'无 COL ⇒ 未实现' 这个推断已被原作者在后续轮次承认不完整。",
        ],
        unknown=[
            "点击是否被 Flash 接收。",
            "C++ 侧是否有处理器 / 是否注册。",
            "整个房间 UI 事件系统是否都死。",
        ],
        hypotheses=[
            ("H1", "AS_* 未注册到 Scaleform", "LOW"),
            ("H2", "房间事件系统未建立（Init 未调用）", "MEDIUM"),
            ("H3", "按钮被有意禁用", "LOW"),
            ("H4", "前置条件未满足（房主/人数）", "LOW"),
        ],
        sources=[
            (r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py", "1048-1068",
             "ready_push 只在客户端已发 0B/4 时才回推"),
        ],
        experiment=dict(
            id="E7a",
            steps=[
                "进入 BOT 房间 UI。",
                "点击**准备以外的**房间按钮（换阵营、投票等任一）。",
                "观察 `lobby_srv.log` 是否有任何新增上行。",
            ],
            expected="回答'是不是整个房间 UI 都死'。",
            judgment=[
                ("其它按钮也无上行", "整个房间事件系统死 ⇒ 合并进 ISSUE-0012"),
                ("其它按钮有上行，只有准备没有", "按钮级问题 ⇒ 指向 H1，需要 .gfx 工具"),
            ],
            prerequisites=["需授权启动 + 用户配合点击"],
            caution="纯观察，不改任何代码。",
        ),
    ),
    "CODOL-ISSUE-0010": dict(
        title="房间下行：先证明客户端到底有没有在读",
        known=[
            "上行不是位流（7 条样本 × 160 bit 偏移穷举零命中）。",
            "下行走位流（0x637000 用 (ptr, len*8) 直接建流）。",
            "type 0x02 是 dwRoomMessageText（vtable 0x00DC7504）。",
            "改回位流后出现过一次可观测行为差异（任务数 85→71、11/4 6→4）。",
            "代码里同时存在容器型与位流型两套构造器。",
        ],
        unknown=[
            "客户端是否成功解析了我们发的下行消息。",
            "信封路由键（obj+8 == roomId）是否满足。",
        ],
        hypotheses=[
            ("H1", "格式对但内容不足", "MEDIUM"),
            ("H3", "信封路由键不对", "HIGH_UNPROVEN"),
            ("H4", "被当回声忽略", "MEDIUM"),
        ],
        sources=[
            (r"CODOL_SERVER_319_20261021\src\battle\battle_service.c", "302-409",
             "（对照）gamestate 路径不受房间推送影响"),
        ],
        experiment=dict(
            id="E8",
            steps=[
                "基线：不推任何 room push，记录任务数与 11/4 次数。",
                "正常：推当前格式，记录同样的两个数字。",
                "畸形：推一条**字段截断**的 room push，记录同样的两个数字。",
            ],
            expected="畸形段应与正常段、基线段三者不同，才能证明客户端在读这段。",
            judgment=[
                ("畸形 == 基线", "客户端整段忽略 ⇒ 先解决信封路由 (H3)"),
                ("畸形 ≠ 基线", "客户端确实在读 ⇒ 进入内容/格式细化"),
            ],
            prerequisites=["同 0020", "需要一个能跑三轮的隔离 kit"],
            caution="本 Issue 的任何改动都不会影响 10-26 的成功基线（成功轮不建房间）。",
        ),
    ),
    "CODOL-ISSUE-0041": dict(
        title="recv 缓冲 → 0x7765A0 读取器：需要一次含活动会话的转储",
        known=[
            "`[esi+0xA8]` 是 recv 目的地（静态证实）。",
            "`0x7765A0` 使用同一会话对象 `[esi+0xB0]`（静态证实）。",
            "`0x81/0x83/0x84/0x85` 是 Demonware 类型码比较点。",
            "已排除 `0x3524F0` 是接收环形缓冲（它是发送/序列化暂存）。",
        ],
        unknown=["读取器读的字节是否就是 recv 写入的字节。", "中间是否有解密/解压层。"],
        hypotheses=[
            ("H1", "[esi+0xA8] 就是读取器输入", "HIGH_UNPROVEN"),
            ("H2", "中间有解密/解压层", "MEDIUM"),
            ("H3", "读取器读另一块缓冲", "LOW"),
        ],
        sources=[
            (r"CODOL-BATTLE-SERVER-RECEIVE-LINK-050\00_FINDINGS.md", "全文",
             "静态分析收敛点与明确措辞"),
        ],
        experiment=dict(
            id="E9",
            steps=[
                "在可读窗口内转储（依赖 ISSUE-0045 解决）。",
                "定位 [esi+0xA8] 指向的缓冲及其内容。",
                "回溯 0x7765A0 的入参指针。",
                "比较两者，或画出中间的拷贝链。",
            ],
            expected="若能指认同一缓冲或完整拷贝链，该边闭合。",
            judgment=[
                ("同一指针", "H1 成立"),
                ("存在拷贝/解密链", "H2 成立"),
                ("无关且无链", "H3 成立"),
            ],
            prerequisites=["ISSUE-0045：需要一个能覆盖活动会话的可读窗口"],
            caution="本 Issue 是取证问题，不是缺陷；没有代码可改。",
        ),
    ),
}


def write_pkg(iid, p):
    d = os.path.join(OUT, iid)
    os.makedirs(d, exist_ok=True)

    def w(name, text):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)

    w("README.md", "\n".join([
        "# %s — INVESTIGATION PACKAGE（不是修复任务包）" % iid,
        "",
        "> 本包的 `FIX_READINESS_MATRIX.csv` 判定为 `can_fix_now = false`，",
        "> 因此**不生成 FIX_PACKAGE**。这里给出的是取证任务，不是补丁任务。",
        "",
        "## 标题",
        p["title"],
        "",
        "## 完整档案",
        "[`../../ISSUES/%s.md`](../../ISSUES/%s.md)" % (iid, iid),
        "",
        "## 本包包含",
        "- `KNOWN_FACTS.md` — 已证明的事实（每条带出处）",
        "- `UNKNOWN_FACTS.md` — 未知事实与假设矩阵",
        "- `TARGET_SOURCE.md` — 需要检查的精确源码位置",
        "- `EXPERIMENT.md` — 最小实验、预期结果、判断标准",
        "",
        "## 交付给下一个 Agent 时的一句话",
        "先读 `EXPERIMENT.md`；在拿到实验结果之前不要写任何补丁。",
        "",
    ]))

    w("KNOWN_FACTS.md", "# 已证明的事实\n\n" +
      "\n".join("- %s" % k for k in p["known"]) + "\n")

    w("UNKNOWN_FACTS.md", "\n".join([
        "# 未知事实与假设",
        "",
        "## 未知",
        "",
    ] + ["- %s" % u for u in p["unknown"]] + [
        "",
        "## 假设矩阵",
        "",
        "| ID | 假设 | 状态 |",
        "|---|---|---|",
    ] + ["| %s | %s | `%s` |" % h for h in p["hypotheses"]] + [""]))

    w("TARGET_SOURCE.md", "\n".join([
        "# 需要检查的精确源码位置",
        "",
        "| 文件 | 行 | 说明 |",
        "|---|---|---|",
    ] + ["| `%s` | %s | %s |" % s for s in p["sources"]] + [
        "",
        "> 行号以本任务读取的版本为准；引用前请先核对文件哈希（见 `../../EVIDENCE_INDEX.json`）。",
        "",
    ]))

    e = p["experiment"]
    lines = [
        "# 最小实验：%s" % e["id"],
        "",
        "## 步骤",
        "",
    ] + ["%d. %s" % (i + 1, s) for i, s in enumerate(e["steps"])] + [
        "",
        "## 预期结果",
        "",
        e["expected"],
        "",
        "## 判断标准",
        "",
        "| 观察 | 结论 |",
        "|---|---|",
    ] + ["| %s | %s |" % j for j in e["judgment"]] + [
        "",
        "## 前置条件",
        "",
    ] + ["- %s" % x for x in e["prerequisites"]] + [
        "",
        "## 风险/注意",
        "",
        e["caution"],
        "",
    ]
    w("EXPERIMENT.md", "\n".join(lines))


def main():
    for iid, p in PACKAGES.items():
        write_pkg(iid, p)
    print("wrote %d investigation packages" % len(PACKAGES))
    print("FIX_PACKAGES: 0 (none of the P0 issues is fix-ready)")


if __name__ == "__main__":
    main()
