# 05 — 修复就绪度报告（全量）

> 由 `FIX_READINESS_MATRIX.csv` 汇总。判据：`FIX_READY` 需同时满足根因有证据、已定位代码、
> 方案有技术依据、有可重复验证、有验收标准、已评估对成功基线的影响。

## 汇总

| fix_readiness | 数量 |
|---|---|
| BLOCKED_BY_DEPENDENCY | 11 |
| BLOCKED_BY_EVIDENCE | 7 |
| FIX_READY | 28 |
| INVESTIGATION_READY | 32 |
| OBSOLETE | 11 |
| RESOLVED_VERIFIED | 3 |

## 逐项

| Issue | 优先级 | 就绪度 | 标题 |
|---|---|---|---|
| CODOL-ISSUE-0009 | P0 | `BLOCKED_BY_EVIDENCE` | 准备按钮点击不产生任何客户端上行 |
| CODOL-ISSUE-0010 | P0 | `INVESTIGATION_READY` | 房间下行推送格式反复反转，最终未定死 |
| CODOL-ISSUE-0012 | P0 | `INVESTIGATION_READY` | dwRoomMatch::Init 从未被调用（MyEventHandler 零实例） |
| CODOL-ISSUE-0020 | P0 | `INVESTIGATION_READY` | BOT 房间场景下战斗服零收包（客户端从不 connect） |
| CODOL-ISSUE-0021 | P0 | `INVESTIGATION_READY` | mmstart 不带 map/gametype，playlist 语义未定 |
| CODOL-ISSUE-0041 | P0 | `INVESTIGATION_READY` | recv 缓冲 → 0xB765A0 读取器的边未闭合 |
| CODOL-ISSUE-0074 | P0 | `INVESTIGATION_READY` | 102/7 playerdata 回全 0 清空玩家选图/选模式 |
| CODOL-ISSUE-0001 | P1 | `INVESTIGATION_READY` | 受保护基线 marketplace_store.py 哈希与清单不符（8/9） |
| CODOL-ISSUE-0002 | P1 | `INVESTIGATION_READY` | 工作 kit 与受保护基线不同源，且每轮继续膨胀 |
| CODOL-ISSUE-0004 | P1 | `INVESTIGATION_READY` | 战斗服构建产物不可复现（test_session.exe 与 codol_battle_ |
| CODOL-ISSUE-0006 | P1 | `BLOCKED_BY_EVIDENCE` | 启动链只能在冻结 kit 上复现，无法从源码重建 |
| CODOL-ISSUE-0007 | P1 | `FIX_READY` | iips.ini 的 enable_iips 是隐性环境依赖，未纳入受保护清单 |
| CODOL-ISSUE-0008 | P1 | `FIX_READY` | 启动单发令牌与提权 agent 是隐性外部依赖 |
| CODOL-ISSUE-0011 | P1 | `INVESTIGATION_READY` | 房间推送的路由信封未定死（route key = roomId 高低 32 位） |
| CODOL-ISSUE-0013 | P1 | `INVESTIGATION_READY` | 自动开局状态机停在状态 1（计时器从未启动） |
| CODOL-ISSUE-0022 | P1 | `BLOCKED_BY_DEPENDENCY` | 战斗服 --map 参数不改变碰撞数据（仍加载 coop_train clipmap） |
| CODOL-ISSUE-0023 | P1 | `INVESTIGATION_READY` | TX 快照缓冲仅 512 B，零售快照 7000–15000 B，且无下行分片 |
| CODOL-ISSUE-0024 | P1 | `INVESTIGATION_READY` | 实体段客户端收得下但看不到（model_index 恒 0、实体号冲突） |
| CODOL-ISSUE-0025 | P1 | `BLOCKED_BY_DEPENDENCY` | 服务端位置推不动客户端；omit=1 是唯一能用的配置 |
| CODOL-ISSUE-0027 | P1 | `INVESTIGATION_READY` | 11 个 playerState 字段仍用 XOR 增量而三份参照都写裸值 |
| CODOL-ISSUE-0028 | P1 | `FIX_READY` | 跳跃在 usercmd 网络路径上不可能触发（walking 从不被刷新） |
| CODOL-ISSUE-0029 | P1 | `BLOCKED_BY_DEPENDENCY` | 服务端地面是写死的无限平面 z=-116，与任何地图无关 |
| CODOL-ISSUE-0030 | P1 | `FIX_READY` | 子弹命中不是射线：距离公式 + 固定假目标 + 固定武器 |
| CODOL-ISSUE-0032 | P1 | `FIX_READY` | 投射物/爆炸、模式击杀、复活、复制层全部定义但从未被调用 |
| CODOL-ISSUE-0042 | P1 | `RESOLVED_VERIFIED` | .tp3 第 3 节区缺失约 229.6 MB，任何已恢复映像都不完整 |
| CODOL-ISSUE-0044 | P1 | `INVESTIGATION_READY` | 五项客户端消费语义（opcode/gamestate/configstring/snap |
| CODOL-ISSUE-0045 | P1 | `INVESTIGATION_READY` | ACE 内核驱动封死活进程内存读取与调试附加 |
| CODOL-ISSUE-0046 | P1 | `INVESTIGATION_READY` | AS_* Scaleform 类有名字但无 COL、零引用，ui_mp.ff 加密 ⇒  |
| CODOL-ISSUE-0047 | P1 | `FIX_READY` | 两套协议族并存：客户端 Demonware(0x81–0x85, 8-bit) vs 服 |
| CODOL-ISSUE-0050 | P1 | `FIX_READY` | '22/22 全绿'、'域标 DONE' 与'实机未验'长期混用同一套措辞 |
| CODOL-ISSUE-0052 | P1 | `FIX_READY` | 多项'已解决'结论只有离线或自测证据 |
| CODOL-ISSUE-0054 | P1 | `BLOCKED_BY_DEPENDENCY` | mmbook accepted 必须回显客户端自己的 (A,B)，预留槽填充者未定位 |
| CODOL-ISSUE-0055 | P1 | `INVESTIGATION_READY` | 进图后客户端从不发送开火位（bit0 缺失） |
| CODOL-ISSUE-0078 | P1 | `BLOCKED_BY_DEPENDENCY` | 战斗握手只有模拟客户端 e2e_client.py 验证过 |
| CODOL-ISSUE-0084 | P1 | `FIX_READY` | IIPS 两难：enable_iips=1 弹窗 vs enable_iips=0 立即 |
| CODOL-ISSUE-0087 | P1 | `INVESTIGATION_READY` | layer-2 世界资产（CLIPMAP_MP / MAP_ENTS / ComWorl |
| CODOL-ISSUE-0003 | P2 | `FIX_READY` | 全工作区无版本控制 |
| CODOL-ISSUE-0005 | P2 | `FIX_READY` | 22/22 离线测试未覆盖三个关键探针与任何客户端联调 |
| CODOL-ISSUE-0015 | P2 | `INVESTIGATION_READY` | memberCount 修复已落地但语义来自 ol-mod（非本 build） |
| CODOL-ISSUE-0016 | P2 | `INVESTIGATION_READY` | 大厅存在大量 UNMAPPED service/task，一律回空 ACK |
| CODOL-ISSUE-0017 | P2 | `INVESTIGATION_READY` | 客户端订阅 20 个 MM 事件，服务端从未推送任何一个 |
| CODOL-ISSUE-0018 | P2 | `INVESTIGATION_READY` | GAME_START_PAYLOAD(162B) 是靶场抓包常量，不是 coop 开局数 |
| CODOL-ISSUE-0031 | P2 | `FIX_READY` | 合成靶子血量不重置，长跑后所有命中都打在 0 血实体上 |
| CODOL-ISSUE-0033 | P2 | `BLOCKED_BY_DEPENDENCY` | 战斗服 struct 是单客户端设计，多客户端不可表达 |
| CODOL-ISSUE-0035 | P2 | `FIX_READY` | 快照基线在发送成功前就前移，发送失败会导致基线错位 |
| CODOL-ISSUE-0036 | P2 | `FIX_READY` | gamestate 只尝试 5 次，且不随 usercmd 重试 |
| CODOL-ISSUE-0038 | P2 | `FIX_READY` | 战斗服行为依赖进程 CWD 中的散落文件（无配置文件） |
| CODOL-ISSUE-0039 | P2 | `FIX_READY` | 世界配置写死 dm 模式、30 分、10 分钟、3 秒复活 |
| CODOL-ISSUE-0040 | P2 | `FIX_READY` | 多客户端/重连：per-connection 重置只在 key-exchange 分支发 |
| CODOL-ISSUE-0043 | P2 | `BLOCKED_BY_EVIDENCE` | 主 DLL 的 .tvm0(31.4MB) / .tls(15.5MB) 未解码 |
| CODOL-ISSUE-0048 | P2 | `FIX_READY` | VA/RVA 混用导致多份报告产出假结论 |
| CODOL-ISSUE-0049 | P2 | `FIX_READY` | 房间消息格式在 10-28 一天内反转四次 |
| CODOL-ISSUE-0056 | P2 | `BLOCKED_BY_DEPENDENCY` | idx20 (pm_flags) 写 aiming?0x10，而 0x10 可能是 PM |
| CODOL-ISSUE-0057 | P2 | `INVESTIGATION_READY` | 动态武器索引无静态全表，且 firstDynamicWeapon 每图不同（1224 v |
| CODOL-ISSUE-0059 | P2 | `INVESTIGATION_READY` | usercmd.weapon 恒为 0，无选枪通道 |
| CODOL-ISSUE-0060 | P2 | `INVESTIGATION_READY` | 跳跃键位定义冲突（0x400 vs 0x2）与 bit29 未解释 |
| CODOL-ISSUE-0061 | P2 | `INVESTIGATION_READY` | netField 语义仍有大量空白（36 个 playerState 字段、7 个 en |
| CODOL-ISSUE-0062 | P2 | `FIX_READY` | entityState 字段数在 24 与 63 之间存在矛盾（记忆称 63） |
| CODOL-ISSUE-0063 | P2 | `INVESTIGATION_READY` | 快照字段 62/83/107/162 与 idx219 只有我们写，参照无对应 |
| CODOL-ISSUE-0064 | P2 | `BLOCKED_BY_DEPENDENCY` | gamestate 尾部 44 字节未解析，configstring index_bit |
| CODOL-ISSUE-0065 | P2 | `INVESTIGATION_READY` | FAT 分片实机从未触发；RELIABLE 分片 ack 无实机证据 |
| CODOL-ISSUE-0066 | P2 | `INVESTIGATION_READY` | 武器定义运行时布局未验证，WeaponAttach 545 条字符串记录不可消费 |
| CODOL-ISSUE-0067 | P2 | `BLOCKED_BY_DEPENDENCY` | 命中盒/护甲/穿透几何缺失；recoil/spread/ADS 公式缺失 |
| CODOL-ISSUE-0070 | P2 | `FIX_READY` | C# 线遗留：加 pm_type/eFlags/otherFlags/字段54/83/2 |
| CODOL-ISSUE-0071 | P2 | `INVESTIGATION_READY` | 客户端停在 '100' 弹窗、rc=-1，从未进大厅（任务 031 线） |
| CODOL-ISSUE-0072 | P2 | `FIX_READY` | hosts 文件原始 937B 不可恢复（现 915B） |
| CODOL-ISSUE-0073 | P2 | `FIX_READY` | service 4/13 才是房间服务，旧映射 service==11 会 UNMAPP |
| CODOL-ISSUE-0075 | P2 | `FIX_READY` | 2697 包与 3.19 的记录层从未被观测：COOKIE_ECHO 189 vs 21 |
| CODOL-ISSUE-0079 | P2 | `BLOCKED_BY_EVIDENCE` | IIPS 的 Stage-1 前置门（QoS helper）从未被跨过 |
| CODOL-ISSUE-0080 | P2 | `BLOCKED_BY_EVIDENCE` | 用户态无法恢复 VM 解释器 / ISA / 解密器（.tvm0 语义） |
| CODOL-ISSUE-0081 | P2 | `BLOCKED_BY_EVIDENCE` | ResourceManager ABI 大部分是虚构的；GetResourceManag |
| CODOL-ISSUE-0082 | P2 | `FIX_READY` | 命令行语义与历史真实命令行均未知（-q/-qa/-src=tgp、argv 提供者槽） |
| CODOL-ISSUE-0083 | P2 | `BLOCKED_BY_EVIDENCE` | TCLS 共享内存布局与 tcls_core.exe 的创建者未知 |
| CODOL-ISSUE-0085 | P2 | `OBSOLETE` | 本地原生链被镜像识别拒绝（unknown executable image / Size |
| CODOL-ISSUE-0086 | P2 | `RESOLVED_VERIFIED` | 3.19 运行时镜像仅覆盖约 4.5% SizeOfImage |
| CODOL-ISSUE-0088 | P2 | `FIX_READY` | 固化链的参考实现本身带 6 次重试与共享 GAME_ROOT |
| CODOL-ISSUE-0089 | P2 | `BLOCKED_BY_DEPENDENCY` | 黄金源目录含 208 个运行时残留，不能直接当干净启动树 |
| CODOL-ISSUE-0034 | P3 | `FIX_READY` | stats 分块状态是全局而非 per-peer，且重连时不重置 |
| CODOL-ISSUE-0037 | P3 | `FIX_READY` | 两个 usercmd 处理分支重复且已出现分歧 |
| CODOL-ISSUE-0053 | P3 | `OBSOLETE` | ol-mod EngineBindings 宿主映像门禁永不通过（SizeOfImage |
| CODOL-ISSUE-0058 | P3 | `INVESTIGATION_READY` | 小地图为空：northyaw 缺失、compass_map_* 需地图边界 |
| CODOL-ISSUE-0069 | P3 | `OBSOLETE` | C# v0.1 战斗服：无碰撞、无 hitscan、无伤害、无死亡复活 |
| CODOL-ISSUE-0076 | P3 | `BLOCKED_BY_DEPENDENCY` | Fragment stride 1154 vs 1162 未裁决 |
| CODOL-ISSUE-0077 | P3 | `OBSOLETE` | 插件边界 31,953 行零测试；部署制品陈旧 |
| CODOL-ISSUE-0090 | P3 | `OBSOLETE` | TESTOL 交付包：1/769 哈希不符、缺 inject_ayria.on、depl |
| CODOL-ISSUE-0091 | P3 | `OBSOLETE` | 真实 Frida 运行时从未执行（T2 线） |
| CODOL-ISSUE-0014 | NONE | `OBSOLETE` | 闸门 B（dvar 3291）设计上不可由服务端下发，只是旁支 |
| CODOL-ISSUE-0019 | NONE | `OBSOLETE` | service 71 被误读为订阅状态机（实为 TLog 日志模板） |
| CODOL-ISSUE-0026 | NONE | `OBSOLETE` | 按参照逐字节重写快照编码器会让本客户端卡住 |
| CODOL-ISSUE-0051 | NONE | `OBSOLETE` | 目标版本曾长期被写成 3.9.9.7，该版本不存在于工作区 |
| CODOL-ISSUE-0068 | NONE | `RESOLVED_VERIFIED` | 训练图只有 1 个 actor，'没有 BOT'是地图设计而非配置 |
| CODOL-ISSUE-0092 | NONE | `OBSOLETE` | '数据链 99.86% 缺失'被推翻：是 BSS 不是丢失 |
