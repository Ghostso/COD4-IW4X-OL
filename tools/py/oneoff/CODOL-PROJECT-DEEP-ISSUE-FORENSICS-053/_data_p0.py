#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 metadata for the database/index layer.

The P0 dossiers in ISSUES/ are hand-written (22 sections, incl. the E1/dump
revision). This file supplies only the fields the databases need so that the
machine-readable outputs cover all 92 issues.
"""
P0 = {}

P0["CODOL-ISSUE-0020"] = dict(
    title="BOT 房间场景下战斗服零收包（客户端从不 connect）", system="battle-network",
    prio="P0", status="OPEN", severity="critical", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E1→E2→E3 差分：分离'地图'与'入口路径'两个共线自变量；E1 已于 2026-10-29 执行（零 RX，因未复刻到条件）。",
    deps=["CODOL-ISSUE-0009", "CODOL-ISSUE-0010", "CODOL-ISSUE-0021", "CODOL-ISSUE-0074"],
    source=[("battle/battle_service.c", "1061-1140", "UDP 唯一入口"),
            ("lobby_server.py", "1090-1150", "mmstart 处理")],
    routes=[("run_codol_001/runs/E1_20261029_103001/E1_RESULT.md", "—", "E1 实测结果")])
P0["CODOL-ISSUE-0021"] = dict(
    title="mmstart 不带 map/gametype，playlist 语义未定", system="lobby",
    prio="P0", status="OPEN", severity="high", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E2（换地图）+ E4（playlist 编号语义表）。",
    deps=["CODOL-ISSUE-0012"],
    source=[("lobby_server.py", "1101-1116", "map/gametype 正则与静默跳过")],
    routes=[("run_codol_001/runs/ONCE_20261026_220815/kit/lobby_srv.log", "22:09:15", "成功形态")])
P0["CODOL-ISSUE-0074"] = dict(
    title="102/7 playerdata 回全 0 清空玩家选图/选模式", system="lobby",
    prio="P0", status="OPEN", severity="high", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E5：在成功形态里强制注入 102/7 回显，看 RX 是否消失（已排除为普遍原因）。",
    deps=["CODOL-ISSUE-0020"],
    source=[("lobby_server.py", "1181-1226", "102/7 val 恒 0")],
    routes=[("run_codol_001/runs/ONCE_20261026_233111/kit/lobby_srv.log", "全文", "首次失败轮无 102/")])
P0["CODOL-ISSUE-0012"] = dict(
    title="dwRoomMatch::Init 从未被调用（MyEventHandler 零实例）", system="lobby",
    prio="P0", status="OPEN", severity="critical", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E6：必须在 memberCount=1 的 kit 上重跑转储并统计 0x00DC78F0 实例数（E1 转储为 memberCount=0，不能回答）。",
    deps=[],
    source=[("lobby_server.py", "1002-1010", "11/13 memberCount")],
    routes=[("run_codol_001/runs/E1_20261029_103001/DUMP_FORENSICS.md", "§3", "memberCount=0 时二者皆无")])
P0["CODOL-ISSUE-0009"] = dict(
    title="准备按钮点击不产生任何客户端上行", system="lobby",
    prio="P0", status="BLOCKED", severity="critical", blocks=True,
    readiness="BLOCKED_BY_EVIDENCE", dossier_note="hand-written",
    next_step="E7a：点击其它房间按钮，判定是'整层事件死'还是'按钮级问题'。",
    deps=["CODOL-ISSUE-0010", "CODOL-ISSUE-0012"],
    source=[("lobby_server.py", "1048-1068", "ready_push 分支")],
    routes=[("run_codol_001/runs/RE_FULL_20261029/rtti_full.md", "AS_* 段", "163 个类名")])
P0["CODOL-ISSUE-0010"] = dict(
    title="房间下行推送格式反复反转，最终未定死", system="lobby",
    prio="P0", status="CONTRADICTORY_EVIDENCE", severity="critical", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E8 畸形对照：证明客户端是否在读下行位流（2026-10-29 转储已独立确认 0x637000 走位流）。",
    deps=["CODOL-ISSUE-0011"],
    source=[("—", "—", "客户端内置逻辑")],
    routes=[("run_codol_001/runs/E1_20261029_103001/DUMP_FORENSICS.md", "§2.7", "0x637000 建流实测")])
P0["CODOL-ISSUE-0041"] = dict(
    title="recv 缓冲 → 0xB765A0 读取器的边未闭合", system="client-re",
    prio="P0", status="OPEN", severity="critical", blocks=True,
    readiness="INVESTIGATION_READY", dossier_note="hand-written",
    next_step="E9（改写版）：一次含活动会话的转储，读 [esi+0xA8] 与 0xB779A0 的 buf 实参。",
    deps=["CODOL-ISSUE-0045"],
    source=[("—", "—", "客户端二进制")],
    routes=[("run_codol_001/runs/E1_20261029_103001/DUMP_FORENSICS.md", "§2", "地址纠错与真实链路")])
