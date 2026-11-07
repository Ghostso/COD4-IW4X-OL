# -*- coding: utf-8 -*-
import csv, io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\05_DIFF"
os.makedirs(OUT, exist_ok=True)
cols = ["id","target_in_current_codol","early_source","reuse_type","evidence_level",
        "shared_protocol_evidence","adaptation_needed","shortest_path_rank","notes"]
R=[]
def row(*a): R.append(dict(zip(cols,a)))

row("C01","现有 C# 战斗服 UDP 传输/连接握手","dedicated/src/codol/net/codol_network.c, codol_handshake.c, codol_association.c, codol_ecdh.c, codol_crypto.c",
    "移植（先解冲突）","CONFIRMED","客户端字符串表 bdDTLS* 符号 ↔ 服务端分支逐条对应",
    "统一密码学原语（冲突A）与 COOKIE_ECHO 长度（冲突B）","P1",
    "合成对等体已跑通 handshake→CS_PRIMED；真实 C1 未验证")

row("C02","现有 C# 战斗服 netchan/分片重组","dedicated/src/codol/net/codol_netchan.c, codol_wire.c",
    "移植","STRONG_CANDIDATE","lobby protocol_map.md B.2 实测 netchan 头 15B",
    "对齐 6B/4B 头与 flags（FRAGMENT/FORCE_ACK/ACK/MASK）","P1",
    "分片 1162B、最多 128 片")

row("C03","现有 C# 战斗服 usercmd/clc 解码","dedicated/src/sv_client.c:2505, codol/net/codol_usercmd_queue.c, codol_client_command.c",
    "移植","CONFIRMED（服务端分发器）","服务端读 3 位 opcode",
    "确认客户端 clc 生产端字段布局（缺口F）","P1",
    "clc_move=0/moveNoDelta=1/clientCommand=2/EOF=3")

row("C04","现有 C# 战斗服 gamestate/snapshot 序列化","dedicated/src/codol/snapshot/*（76）, sv_snapshot.c:224",
    "移植（核心阻塞）","CANDIDATE","configstrings 6519；svc 1/5",
    "完成 CoDOL 帧构建，替换 IW3 序列化器","P0",
    "PORT §4 未完成；阻塞进战斗")

row("C05","现有 C# 战斗服会话描述符/地址下发","lobby/handoff/*, lobby/resources/session 相关",
    "直接复用（契约）","CONFIRMED","21/5 findSessions session 对象含 16B securityKey",
    "对齐 258B session 记录与 securityKey","P0",
    "现有 C# 已有 SessionDescriptor.cs，可交叉验证")

row("C06","现有 C# 战斗服准入/名册","dedicated/src/codol/net/codol_admission.c",
    "直接复用","CONFIRMED","名册行样例实测",
    "无","P1","key 即凭据")

row("C07","现有 Lobby 状态/健康契约","dedicated/src/codol/net/codol_match_status.c",
    "直接复用","CONFIRMED","qconsole 实测状态行",
    "无","P1","纯文本")

row("C08","现有 Lobby 启动战斗（RCON）","lobby/handoff/match_server_control.py",
    "直接复用","CONFIRMED","5 条命令顺序实测",
    "对齐 RCON 口令与端口 17733","P1","map 最后")

row("C09","现有 C# 战斗服结算→回写","dedicated/src/codol/stats/*（39）, lobby/career/rank_writeback.py",
    "移植","CONFIRMED","match_report.json 契约",
    "补全字段语义","P2","")

row("C10","现有 C# 战斗服资产/地图加载","dedicated/src/codol/assets/*（66）",
    "移植","CONFIRMED","fastfile/zone 读取",
    "运行时资产/脚本兼容（PORT §5）","P1","codol_asset_registry.c 128KB")

row("C11","现有 C# 战斗服碰撞","dedicated/src/codol/collision/*（33）",
    "移植","CONFIRMED","BSP/Clip",
    "地图实体/碰撞数据","P2","现 C# 亦缺 BSP/Clip")

row("C12","现有 C# 战斗服 pmove/玩家运动","dedicated/src/codol/player/codol_pmove_c1.c",
    "参考（版本锁定）","CONFIRMED","C1 pmove 布局",
    "确认现客户端 pmove 是否一致","P2","105KB")

row("C13","现有 C# 战斗服武器/装备","dedicated/src/codol/weapon/*（64）",
    "参考（版本锁定）","CONFIRMED","武器 wire ID 1024 vs 128 槽",
    "资产注册到显式武器映射","P2","139KB")

row("C14","现有 Lobby 进度/等级","lobby/career/*, resources/progression_tables.json",
    "移植","CONFIRMED","数据驱动",
    "数据表对齐","P2","")

row("C15","现有 Lobby 商店/装配","lobby/catalogue/*, resources/marketplace_catalogue.json",
    "移植","CONFIRMED","数据驱动",
    "数据表对齐","P3","")

row("C16","现有 Lobby 持久化","lobby/store/*, resources/lobby.sqlite",
    "移植","CONFIRMED","mpdata_s.<uid> 契约",
    "schema 对齐","P2","")

row("C17","现有 Lobby 区/地图校验","lobby/zones/*",
    "移植","CONFIRMED",".ff 读取 + CRC",
    "依赖游戏安装路径","P3","")

row("C18","现有项目回归测试基座","dedicated/tests/*（127）, lobby/selftests/*",
    "直接复用","CONFIRMED","离线测试",
    "无","P2","")

row("C19","本地编排/启动","tools/codol_stack.py, codol_rcon_probe.py, START-*.cmd（仅参考顺序）",
    "参考","CONFIRMED","lobby→native→client 顺序",
    "不执行样本脚本","P3","")

row("C20","客户端改造运行","Kernel33.dll, patcher/*",
    "排除/暂不可用","CONFIRMED","反保护绕过",
    "使用自研启动器替代","-","超出任务约束")

with io.open(os.path.join(OUT,"EARLY_SERVER_05_REUSE_CANDIDATES.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in R: w.writerow(r)
print("rows",len(R))
