# -*- coding: utf-8 -*-
import csv, io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\04_REUSE"
os.makedirs(OUT, exist_ok=True)
cols = ["id","asset_name","category","evidence_level","source_path","role",
        "reuse_target_for_current_codol","dependency_conditions","interface_delta",
        "effort_estimate","blockers","notes"]
R = []
def row(*a): R.append(dict(zip(cols,a)))

row("R01","codol_dedrun.exe","B","CONFIRMED","dedicated/bin/codol_dedrun.exe",
    "CoD4x fork native CoDOL dedicated server (x86 Win32, UDP 17733, 185 Plugin_* exports)",
    "作为原生战斗主机 / 协议实现来源；也可在现客户端上直接尝试接入",
    "需完成 bdDTLS 会话行为、CoDOL 消息文法、gamestate/configstrings/snapshot 序列化",
    "IW3 引擎底座 + CoDOL 叠加层；快照仍用 IW3 序列化器",
    "大（数百至上千工时）",
    "PORT.md 'Required before a client can play' 6 项未完成；真实 C1 未观察",
    "已确认可自主运行跑 bots（qconsole running=1 bots=12）；尚不能面向真人 C1 可玩")

row("R02","codol_dedrun_next.exe","E","CONFIRMED","dedicated/bin/codol_dedrun_next.exe",
    "部署副本","无（重复）","-","与 R01 逐字节相同（同 SHA-256）",
    "-","重复文件；排除，使用 R01 即可","SHA 28366ae9... 与 R01 相同")

row("R03","服务端插件 DLL ×8","B","CONFIRMED","dedicated/plugins/*/*.dll",
    "进程内插件（censor/cpptest/b3hide/legacybanlist/pchat/nehoscreenshotuploader/simplebanlist/sourcebansplugin/warn）",
    "仅与 R01 的 CoD4x 插件宿主一起复用","依赖 R01 的 185 个 Plugin_* 导出 ABI",
    "导入表直接引用 codol_dedrun.exe","小-中","需 R01 宿主二进制",
    "9 个已编译 DLL；censor/b3hide 等与反作弊/审查相关，复用需评估合规")

row("R04","pexports.exe","E","CONFIRMED","dedicated/bin/pexports.exe",
    "第三方 PE 导出转储工具","无","-","-","-",
    "非游戏组件（工具，0.47 版）","仅为构建 .def 的辅助工具")

row("R05","Kernel33.dll + patcher 源","D","CONFIRMED","Kernel33.dll; patcher/kernel33.c; patcher/make_exe.py; patcher/unpacked.z; patcher/c1_tables.h",
    "打包版 1.1.1.13 客户端运行垫片 + 客户端补丁表","不用于服务端复用；仅解释早期客户端如何被改造运行",
    "依赖打包的 codoMP_client_shipRetail.exe 与 C1.exe；令 TenProtect 不执行",
    "改写 Kernel32→Kernel33 导入；GAME_ENTRY_VA 0x00ADFAFA 等",
    "-","涉及反保护绕过，超出本轮范围；且依赖打包客户端",
    "本地替代：直接运行已解包/自研启动器，不做保护绕过")

row("R06","dedicated 引擎底座（CoD4x/IW3）","B","CONFIRMED","dedicated/src/sv_main.c, sv_client.c, sv_snapshot.c, net_chan.c, common.c, sys_main.c 等（src 根 217 文件）",
    "原生服务端引擎骨架（初始化/帧循环/网络/快照）","作为自研原生战斗服的引擎底座移植",
    "AGPL3 许可；IW3 wire vs CoDOL wire 差异","SV_Frame/Com_Init/SV_Init 等可作为移植锚点",
    "大","AGPL3 传染性许可；需完整移植 CoDOL 叠加层",
    "架构骨架完整，SV_Init/SV_Frame/SV_SpawnServer 行号已定位")

row("R07","codol/net 协议核心（crypto/association/handshake/ecdh/netchan/wire/network）","B","CONFIRMED","dedicated/src/codol/net/codol_crypto.c, codol_association.c, codol_handshake.c, codol_ecdh.c, codol_netchan.c, codol_wire.c, codol_network.c",
    "CoDOL 加密传输 + 分片 + 记录层","实现战斗服加密通道",
    "P-224 共享 X + 16B security → 24B key；32 位重放窗口",
    "记录头 16B 06 02 tag(2) counter(2) mac8(8) len(2)","中-大",
    "冲突 A（AES192/Tiger192 vs AES128/SHA1）；冲突 B（COOKIE_ECHO 189 vs 219）",
    "合成加密对等体已跑通 handshake→CS_PRIMED；真实 C1 未验证")

row("R08","codol_connect.c（challenge/connect 文本）","A","CONFIRMED","dedicated/src/codol/net/codol_connect.c",
    "getchallenge / connectResponse 文本文法","直接复用为明文 OOB 连接契约",
    "challenge = NET_CookieHash(from)","应答 4×0xFF + 'connectResponse ... protocol\\1 shortversion\\1.1.1.13'",
    "小","无（文本契约已被 lobby 实测旁证）",
    "protocol 字段硬编码 1（非 187）；与内部 codec 187 冲突已解释")

row("R09","codol_match_status.c（sh1x_status）","A","CONFIRMED","dedicated/src/codol/net/codol_match_status.c",
    "服务端状态文本行，供 lobby 轮询","直接复用为 lobby↔战斗服健康/状态契约",
    "任意状态可用；未载图 map=none running=0","sh1x_status map=.. session_map=.. gametype=.. running=.. humans=.. bots=.. maxclients=.. uids=..",
    "小","无","语言无关（纯文本），是最高价值复用点之一")

row("R10","codol_admission.c（名册/准入）","A","CONFIRMED","dedicated/src/codol/net/codol_admission.c",
    "名册行准入校验 + 凭据生命周期","直接复用为 lobby→战斗服 的准入边界",
    "名册行 <ipv4> <key:32hex> <uid:16hex|0> <expires> <gamertag>","文本文件契约",
    "小","无（文本 + 代码双证据）","与 lobby game_admissions.txt 实测样例一致")

row("R11","codol/net 辅助（usercmd_queue/pure/msg/client_command/atomic_file）","B","CONFIRMED","dedicated/src/codol/net/codol_usercmd_queue.c, codol_pure.c, codol_msg.c, codol_client_command.c, codol_atomic_file.c",
    "usercmd 队列、pure 校验、消息读写、原子文件","移植为战斗服输入层与持久化辅助",
    "与 clc 3 位 opcode 分发器配合","依赖 sv_client.c 分派点",
    "中","客户端 clc 生产端未确认（缺口 F）","服务端分发器 CONFIRMED")

row("R12","codol/snapshot（快照/configstrings/帧构建）","B","CONFIRMED","dedicated/src/codol/snapshot/*（76 文件）",
    "快照、configstrings、实体、delta、事件、帧构建","战斗服下行帧生成的核心移植目标",
    "6519 configstrings；武器从 5362 起","SV_WriteSnapshotToClient 仍用 IW3 序列化器",
    "大","缺口 E：序列化器未移植（阻塞进战斗）",
    "codol_engine_state.c 140KB 为最大件")

row("R13","codol/player（玩家/pmove/bot/actor）","C","CONFIRMED","dedicated/src/codol/player/*（87 文件）",
    "玩家状态、C1 pmove、bot、actor、sentient 生命周期","参考实现；若现客户端 pmove 一致可升为 B",
    "锁定 1.1.1.13 pmove 布局","codol_pmove_c1.c 105KB；bot 可独立跑",
    "大","版本锁定（1.1.1.13 vs 现客户端 2021 构建）",
    "能解释战斗生命周期与 bot 行为")

row("R14","codol/weapon（武器状态/native/compose）","C","CONFIRMED","dedicated/src/codol/weapon/*（64 文件）",
    "武器状态机、原生武器表、组合/配件","参考；武器表可能与现客户端不同",
    "武器 wire ID 1024 vs 引擎 128 槽","codol_weapon_state.c 139KB",
    "大","版本锁定；PORT §3 武器映射未完成","提供武器/配件数据模型参考")

row("R15","codol/vehicle（载具）","C","CONFIRMED","dedicated/src/codol/vehicle/*（48 文件）",
    "载具物理/轮动画/脉冲世界","参考；仅当目标模式需要载具",
    "ODB/ODE 物理集成","codol_vehicle_native.cpp 26KB",
    "中-大","版本锁定","非核心路径")

row("R16","codol/script（GSC/内置函数桥）","C","CONFIRMED","dedicated/src/codol/script/*（150 文件）",
    "GSC VM 内置函数桥（combat/player/vehicle/anim/profile）","参考；可解释脚本侧战斗逻辑",
    "GSC VM 操作码","codol_script_startup_extra.c 54KB",
    "大","版本锁定","数量最大区域之一")

row("R17","codol/assets（资产注册/加载）","B","CONFIRMED","dedicated/src/codol/assets/*（66 文件）",
    "资产注册表、加载块、资产命令、模型动画","移植为资产/地图加载层",
    "依赖 fastfile/zone 读取","codol_asset_registry.c 128KB",
    "大","运行时资产/脚本兼容未完成（PORT §5）","含模型动画 30KB")

row("R18","codol/collision（碰撞/物理）","B","CONFIRMED","dedicated/src/codol/collision/*（33 文件）",
    "碰撞、地图实体、玻璃、物理、地形探针","移植为碰撞层",
    "依赖 BSP/Clip 数据","codol_collision_native.c 26KB",
    "中-大","版本锁定","现 C# 战斗服亦缺 BSP/Clip 碰撞")

row("R19","codol/stats（结算/档案）","A","CONFIRMED","dedicated/src/codol/stats/*（39 文件）",
    "比赛报告、记分板、档案推送、结构化 schema","复用为战斗结算→lobby 回写契约",
    "match_report.json 契约","codol_match_report.c 50KB",
    "中","字段语义待补全","与 lobby rank_writeback 对接")

row("R20","dedicated/tests（127 文件）","A","CONFIRMED","dedicated/tests/*",
    "离线测试/回归覆盖","复用为兼容性/回归测试基座",
    "make test-codol（7 子测试）","C 测试框架","小-中","无",
    "含 test_codol_native.c 116KB / test_codol_assets.c 350KB")

row("R21","dedicated/docs（280+ md）","C","CONFIRMED","dedicated/docs/*",
    "逆向研究笔记（协议/资产/武器/僵尸/渲染）","作为知识与证据参考（含冲突证据）",
    "-","-","-","含作者自述与实测日志，须与快照运行态区分",
    "CODOL_PORT.md / CODOL_IMPLEMENTATION_PASS.md / CODOL_ASSOCIATION.md 等")

row("R22","GSC 脚本树（codol_rawfiles）","B","CONFIRMED","dedicated/bin/home/codol_rawfiles/*（1341 GSC）",
    "服务端 GSC 脚本源","移植/替换为战斗服脚本集",
    "mounted rawfiles 喂脚本编译器","1341 个 GSC 文件","中-大",
    "存在脚本编译错误（sys_error.txt: bar.x = -barWidth / 2）","可作为脚本兼容性测试语料")

row("R23","bin/home/main（iwd/cfg/日志）","C","CONFIRMED","dedicated/bin/home/main/sh1x_svr_scripts.iwd, q3config_server.cfg, missingasset.csv, qconsole.log",
    "运行时脚本包/配置/资产缺口清单","参考；missingasset.csv 可指导资产补全",
    "-","sh1x_svr_scripts.iwd 4.28MB","小",
    "qconsole.log 仅 bot 会话（humans=0）","日志是运行态反证来源")

row("R24","bin/home/codol_progress（3 个 uid 存档）","C","CONFIRMED","dedicated/bin/home/codol_progress/*.txt",
    "早期服务端进度存档","参考 playerdata 结构",
    "-","-","小","仅 3 个 uid","非核心")

row("R25","bin/home/codol_animtrees（9 .atr）","B","CONFIRMED","dedicated/bin/home/codol_animtrees/*.atr",
    "动画树数据","可能被现客户端读取（需验证格式）",
    "格式兼容未验证","-","小","格式兼容 UNKNOWN","")

row("R26","bin/home/serverstatus.xml（B3）","C","CONFIRMED","dedicated/bin/home/serverstatus.xml",
    "B3 管理插件状态","参考","gamename='Call of Duty Online Closed Alpha Server'","-","小","无","")

row("R27","lobby 核心（dw-capture.py/paths.py）","A","CONFIRMED","lobby/dw-capture.py, lobby/paths.py",
    "Demonware 模拟器监听与分发","复用为本地大厅（无认证）",
    "端口 3074 UDP+TCP，3075 准入","无认证；uid 自报、session key 恒定","小-中",
    "1.1.1.13 专用；无认证（勿暴露公网）","服务 10/11/21/80/4/102")

row("R28","lobby/demonware（6 服务 + wire）","A","CONFIRMED","lobby/demonware/*（13 py）",
    "wire 编解码 + storage/rooms/matchmaking/marketplace/stats/chat","复用为大厅服务实现",
    "dw_wire 为底层，六服务在上","3DES 帧 + tagged-value codec","中",
    "1.1.1.13 专用","")

row("R29","lobby/store（SQLite + playerdata codec）","B","CONFIRMED","lobby/store/*（9 py）, lobby/resources/lobby.sqlite",
    "SQLite 持久化 + v11 blob codec","移植/复用为档案存储",
    "playerdata 编解码","mpdata_s.<uid> 契约","中","schema 与现版本可能不同","")

row("R30","lobby/career（rank/XP/挑战/武器）","B","CONFIRMED","lobby/career/*（8 py）",
    "等级、经验、挑战、武器等级、结算回写","移植为进度系统",
    "progression_tables.json 驱动","-","中-大","版本锁定","")

row("R31","lobby/catalogue（商店可售项）","B","CONFIRMED","lobby/catalogue/*（8 py）",
    "商店目录、角色槽、武器装配","移植为商店/装配",
    "-","marketplace_catalogue.json 376KB","中","版本锁定","")

row("R32","lobby/zones（.ff 区读取）","B","CONFIRMED","lobby/zones/*（3 py）",
    "读取随包 .ff 区 + CRC","复用以做区/地图校验",
    "依赖游戏安装 client_shipRetail\\chinese\\*.ff","-","小-中","依赖现客户端安装路径","")

row("R33","lobby/handoff（选图 + RCON 控制）","A","CONFIRMED","lobby/handoff/*（4 py，map_handoff.py 90KB）",
    "选图/模式 + 经 RCON 启动战斗","复用为大厅→战斗服启动器",
    "5 条 RCON 命令顺序 set fs_game→sessionMap→zoneType→g_gametype→map","map 最后","小-中",
    "依赖 loopback RCON 与口令文件","含 installed_zones.json / match_instances.py")

row("R34","lobby/notices（新闻/ticker）","B","CONFIRMED","lobby/notices/*（3 py）",
    "ticker/news/banner 打包","移植","-","-","小","版本锁定","")

row("R35","lobby/ffwriter（fastfile 创作）","B","CONFIRMED","lobby/ffwriter/*（5 py）",
    "fastfile 拼装（zone splice/animslist/ffotd）","复用以创作/修补区文件",
    "依赖 .ff 格式知识","-","中","格式专有","")

row("R36","lobby/resources（采集表）","B","CONFIRMED","lobby/resources/*（74 文件）",
    "progression_tables/marketplace_catalogue/mpdata_s.*/map_spawns.proposed/playlists","复用为大厅运行数据",
    "-","-","小-中","部分 .proposed 为未定稿","")

row("R37","lobby/players（2 份真人 career）","C","CONFIRMED","lobby/players/*（2 文件）",
    "真人档案（唯一副本）","参考 playerdata 真实结构","-","-","-",
    "唯一副本，勿清理","")

row("R38","lobby/captures（wiretap jsonl）","C","CONFIRMED","lobby/captures/*（4 天 jsonl）",
    "真实流量捕获","离线复算协议（MAC/长度）","-","-","-","无",
    "是解决冲突 A/B 的离线证据来源")

row("R39","lobby/docs（39 篇）","C","CONFIRMED","lobby/docs/*",
    "协议地图/大厅/进度研究笔记","参考（含实测标注 MEASURED/INFERRED）",
    "-","-","-","含 protocol_map.md / admission.md / progression.md","")

row("R40","lobby/selftests（11 套）","A","CONFIRMED","lobby/selftests/*（17 文件）",
    "离线回归测试","复用为大厅回归","无 socket、不触库","-","小","无","")

row("R41","状态/契约文件","A","CONFIRMED","lobby/startgame.txt, game_admissions.txt, securitykey.bin, native_server_rcon.txt, map_selection.state.json, dedicated/bin/home/codol_sessions.txt, session_desc.pickle",
    "大厅↔战斗服文本契约与状态","直接复用为接口契约（口令不得输出）",
    "key 即凭据；securitykey.bin 16B","纯文本/二进制小文件","小","口令文件敏感，禁止外泄","")

row("R42","tools（launcher/stack/player/rcon_probe/setup）","B","CONFIRMED","tools/codol_launcher.pyw, codol_stack.py, codol_player.py, codol_rcon_probe.py, codol_setup_env.py",
    "编排/启动/探针工具","移植为本地编排（不直接运行样本 .cmd）",
    "编排 lobby→native→client 顺序","RCON health probe 就绪判定","中",
    "含运行样本服务的编排，本轮不执行","")

row("R43","START-*.cmd 编排脚本","C","CONFIRMED","START-ALL.cmd, START-LOBBY.cmd, START-SERVER.cmd, START-CLIENT.cmd",
    "一键编排","仅参考其顺序与参数（不运行）",
    "顺序 lobby→native→client","真实 readiness 而非 sleep","-",
    "本轮禁止执行","")

row("R44","resource/icon.*","E","CONFIRMED","resource/icon.ico, icon.png",
    "图标资源","无","-","-","-","与战斗复原无关","")

row("R45","build/（pyenv/pyinstaller）","D","CONFIRMED","build/pyenv/*（7633 文件）, build/pyinstaller/*, build/env-manifest.json",
    "打包/运行环境","不直接复用；本地重建等价环境",
    "Python 环境","-","-","体积大、平台绑定","本地替代：自建 Python 环境","")

row("R46","_clone_backup_*/_purge_backup_*","E","CONFIRMED","_clone_backup_20261005_203207/, _clone_backup_20261005_203212/, _purge_backup_20261005_200601/",
    "历史备份","无","-","-","-","历史副本，与主树重复","")

row("R47","dedicated/.git","E","CONFIRMED","dedicated/.git",
    "Git 元数据","无","-","-","-","无有效提交（BUILD_NUMBER=0）","")

row("R48","*.o / *.pyc / __pycache__","E","CONFIRMED","dedicated/**/*.o, **/__pycache__/*, patcher/kernel33_res.o",
    "编译中间产物","无","-","-","-","可由源码重建","")

with io.open(os.path.join(OUT,"EARLY_SERVER_04_REUSE_MATRIX.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in R: w.writerow(r)
print("rows",len(R))
from collections import Counter
print(Counter(r["category"] for r in R))
