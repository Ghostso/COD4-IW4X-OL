# 03 — 主未解决问题台账（Master Unresolved Issue Register）

> 本文件由 `build_docs.py` 从 `MASTER_ISSUES.json` 直接生成，计数不会与数据脱节。

未解决 = 状态不属于 `RESOLVED_VERIFIED` / `OBSOLETE`。当前共 **86** 项。

### 按技术系统分布（未解决项）

| 系统 | 数量 | 覆盖文档 |
|---|---|---|
| `startup` 启动/IIPS/TCLS | 12 | 02, 06 |
| `lobby` 大厅/房间 | 13 | 05, 06 |
| `battle-network` 战斗网络 | 10 | 05, 07 |
| `battle-snapshot` 快照 | 10 | 05, 09 |
| `combat` 战斗玩法 | 9 | 09 |
| `client-re` 客户端逆向 | 7 | 06 |
| `baseline` 基线与工程 | 4 | 14 |
| `build` 构建 | 4 | 07, 14 |
| `movement` 移动 | 4 | 09 |
| `evidence-quality` 证词质量 | 4 | 10 |
| `battle-world` / `protocol` / `tooling` 各 2 | 6 | 05, 07 |
| `battle-entity` / `map` / `external` 各 1 | 3 | 07, 08 |
| **合计** | **86** | |


| Issue ID | 标题 | 系统 | 状态 | 优先级 | 阻塞可玩 |
|---|---|---|---|---|---|
| CODOL-ISSUE-0009 | 准备按钮点击不产生任何客户端上行，根因未定 | `lobby` | BLOCKED | P0 | 是 |
| CODOL-ISSUE-0010 | 房间下行推送格式在'位流 / 容器'之间反复，最终未定死 | `lobby` | CONTRADICTORY_EVIDENCE | P0 | 是 |
| CODOL-ISSUE-0012 | dwRoomMatch::Init 从未被调用（MyEventHandler 零实例） | `lobby` | OPEN | P0 | 是 |
| CODOL-ISSUE-0020 | BOT 房间场景下战斗服零收包（客户端从不 connect） | `battle-network` | OPEN | P0 | 是 |
| CODOL-ISSUE-0021 | mmstart 中的 playlist 编号在本轮解析为 37 而 findSessions 为 50，且均非官方 ID | `lobby` | OPEN | P0 | 是 |
| CODOL-ISSUE-0041 | recv 缓冲 → 0x7765A0 读取器的边未闭合（最小未闭合边） | `client-re` | OPEN | P0 | 是 |
| CODOL-ISSUE-0074 | 102/7 playerdata 批量读回全 0 会清空玩家选图/选模式 | `lobby` | OPEN | P0 | 是 |
| CODOL-ISSUE-0001 | 受保护基线 marketplace_store.py 哈希与清单不符（8/9） | `baseline` | OPEN | P1 | 否 |
| CODOL-ISSUE-0002 | 工作 kit 与受保护基线不同源，且每轮继续膨胀 | `baseline` | OPEN | P1 | 否 |
| CODOL-ISSUE-0004 | 战斗服构建产物不可复现：test_session.exe 与 codol_battle_server.exe 同尺寸 | `build` | UNVERIFIED | P1 | 否 |
| CODOL-ISSUE-0006 | 启动链只能在冻结 kit 上复现，无法从源码重建 | `startup` | PARTIALLY_RESOLVED | P1 | 否 |
| CODOL-ISSUE-0007 | iips.ini 的 enable_iips 是隐性环境依赖，未纳入受保护清单 | `startup` | PARTIALLY_RESOLVED | P1 | 否 |
| CODOL-ISSUE-0008 | 启动单发令牌与提权 agent 是隐性外部依赖 | `startup` | OPEN | P1 | 否 |
| CODOL-ISSUE-0011 | 房间推送的路由信封未定死（route key = roomId 高低 32 位） | `lobby` | OPEN | P1 | 是 |
| CODOL-ISSUE-0013 | 自动开局状态机停在状态 1（计时器从未启动） | `lobby` | OPEN | P1 | 是 |
| CODOL-ISSUE-0022 | 战斗服 --map 参数不改变碰撞数据（仍加载 coop_train clipmap） | `battle-world` | OPEN | P1 | 是 |
| CODOL-ISSUE-0023 | TX 快照缓冲仅 512 B，零售快照 7000–15000 B，且无下行分片 | `battle-network` | OPEN | P1 | 是 |
| CODOL-ISSUE-0024 | 实体段客户端收得下但看不到（model_index 恒 0、实体号冲突） | `battle-entity` | PARTIALLY_RESOLVED | P1 | 是 |
| CODOL-ISSUE-0025 | 服务端位置推不动客户端；omit=1 是唯一能用的配置 | `battle-snapshot` | OPEN | P1 | 是 |
| CODOL-ISSUE-0027 | 11 个 playerState 字段仍用 XOR 增量而三份参照都写裸值 | `battle-snapshot` | UNVERIFIED | P1 | 是 |
| CODOL-ISSUE-0028 | 跳跃在 usercmd 网络路径上不可能触发（walking 从不被刷新） | `movement` | OPEN | P1 | 是 |
| CODOL-ISSUE-0029 | 服务端地面是写死的无限平面 z=-116，与任何地图无关 | `movement` | OPEN | P1 | 是 |
| CODOL-ISSUE-0030 | 子弹命中不是射线：距离公式 + 固定假目标 + 固定武器 | `combat` | OPEN | P1 | 是 |
| CODOL-ISSUE-0032 | 投射物/爆炸、模式击杀、复活、复制层全部定义但从未被调用 | `combat` | NOT_IMPLEMENTED | P1 | 是 |
| CODOL-ISSUE-0042 | .tp3 第 3 节区缺失约 229.6 MB，任何已恢复映像都不完整 | `client-re` | BLOCKED | P1 | 是 |
| CODOL-ISSUE-0044 | 五项客户端消费语义（opcode/gamestate/configstring/snapshot/reliable）解决率 0% | `client-re` | OPEN | P1 | 是 |
| CODOL-ISSUE-0045 | ACE 内核驱动封死活进程内存读取与调试附加 | `tooling` | BLOCKED | P1 | 否 |
| CODOL-ISSUE-0046 | AS_* Scaleform 类有名字但无 COL、零引用，ui_mp.ff 加密 ⇒ UI 逻辑不可达 | `client-re` | BLOCKED | P1 | 是 |
| CODOL-ISSUE-0047 | 两套协议族并存：客户端 Demonware(0x81–0x85, 8-bit) vs 服务端 iD-Tech(3-bit 0..4) | `protocol` | CONTRADICTORY_EVIDENCE | P1 | 是 |
| CODOL-ISSUE-0050 | '22/22 全绿'、'域标 DONE' 与'实机未验'长期混用同一套措辞 | `evidence-quality` | CONTRADICTORY_EVIDENCE | P1 | 否 |
| CODOL-ISSUE-0052 | 多项'已解决'结论只有离线或自测证据 | `evidence-quality` | UNVERIFIED | P1 | 否 |
| CODOL-ISSUE-0054 | mmbook accepted 必须回显客户端自己的 (A,B)，预留槽填充者未定位 | `lobby` | OPEN | P1 | 是 |
| CODOL-ISSUE-0055 | 进图后客户端从不发送开火位（bit0 缺失） | `combat` | OPEN | P1 | 是 |
| CODOL-ISSUE-0078 | 战斗握手只有模拟客户端 e2e_client.py 验证过 | `battle-network` | UNVERIFIED | P1 | 否 |
| CODOL-ISSUE-0084 | IIPS 两难：enable_iips=1 弹窗 vs enable_iips=0 立即退出，二者未调和 | `startup` | CONTRADICTORY_EVIDENCE | P1 | 否 |
| CODOL-ISSUE-0087 | layer-2 世界资产（CLIPMAP_MP / MAP_ENTS / ComWorld）从未导出 | `map` | NOT_IMPLEMENTED | P1 | 是 |
| CODOL-ISSUE-0003 | 全工作区无版本控制 | `baseline` | OPEN | P2 | 否 |
| CODOL-ISSUE-0005 | 22/22 离线测试未覆盖三个关键探针与任何客户端联调 | `build` | PARTIALLY_RESOLVED | P2 | 否 |
| CODOL-ISSUE-0015 | memberCount 修复已落地但语义来自 ol-mod（非本 build） | `lobby` | PARTIALLY_RESOLVED | P2 | 否 |
| CODOL-ISSUE-0016 | 大厅存在大量 UNMAPPED service/task，一律回空 ACK | `lobby` | OPEN | P2 | 否 |
| CODOL-ISSUE-0017 | 客户端订阅 20 个 MM 事件，服务端从未推送任何一个 | `lobby` | OPEN | P2 | 否 |
| CODOL-ISSUE-0018 | GAME_START_PAYLOAD(162B) 是靶场抓包常量，不是 coop 开局数据 | `lobby` | OPEN | P2 | 否 |
| CODOL-ISSUE-0031 | 合成靶子血量不重置，长跑后所有命中都打在 0 血实体上 | `combat` | OPEN | P2 | 否 |
| CODOL-ISSUE-0033 | 战斗服 struct 是单客户端设计，多客户端不可表达 | `battle-network` | OPEN | P2 | 否 |
| CODOL-ISSUE-0035 | 快照基线在发送成功前就前移，发送失败会导致基线错位 | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0036 | gamestate 只尝试 5 次，且不随 usercmd 重试 | `battle-network` | OPEN | P2 | 否 |
| CODOL-ISSUE-0038 | 战斗服行为依赖进程 CWD 中的散落文件（无配置文件） | `build` | OPEN | P2 | 否 |
| CODOL-ISSUE-0039 | 世界配置写死 dm 模式、30 分、10 分钟、3 秒复活 | `battle-world` | NOT_IMPLEMENTED | P2 | 否 |
| CODOL-ISSUE-0040 | 多客户端/重连：per-connection 重置只在 key-exchange 分支发生 | `battle-network` | OPEN | P2 | 否 |
| CODOL-ISSUE-0043 | 主 DLL 的 .tvm0(31.4MB) / .tls(15.5MB) 未解码 | `client-re` | BLOCKED | P2 | 否 |
| CODOL-ISSUE-0048 | VA/RVA 混用导致多份报告产出假结论 | `evidence-quality` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0049 | 房间消息格式在 10-28 一天内反转四次 | `evidence-quality` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0056 | idx20 (pm_flags) 写 aiming?0x10，而 0x10 可能是 PMF_SPRINTING 并挡掉开镜 | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0057 | 动态武器索引无静态全表，且 firstDynamicWeapon 每图不同（1224 vs 1147） | `combat` | NOT_IMPLEMENTED | P2 | 否 |
| CODOL-ISSUE-0059 | usercmd.weapon 恒为 0，无选枪通道 | `movement` | OPEN | P2 | 否 |
| CODOL-ISSUE-0060 | 跳跃键位定义冲突（0x400 vs 0x2）与 bit29 未解释 | `movement` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0061 | netField 语义仍有大量空白（36 个 playerState 字段、7 个 entityState 字段未命名） | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0062 | entityState 字段数在 24 与 63 之间存在矛盾（记忆称 63） | `battle-snapshot` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0063 | 快照字段 62/83/107/162 与 idx219 只有我们写，参照无对应 | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0064 | gamestate 尾部 44 字节未解析，configstring index_bits 未知 | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0065 | FAT 分片实机从未触发；RELIABLE 分片 ack 无实机证据 | `battle-network` | UNVERIFIED | P2 | 否 |
| CODOL-ISSUE-0066 | 武器定义运行时布局未验证，WeaponAttach 545 条字符串记录不可消费 | `combat` | UNVERIFIED | P2 | 否 |
| CODOL-ISSUE-0067 | 命中盒/护甲/穿透几何缺失；recoil/spread/ADS 公式缺失 | `combat` | NOT_IMPLEMENTED | P2 | 否 |
| CODOL-ISSUE-0070 | C# 线遗留：加 pm_type/eFlags/otherFlags/字段54/83/217 全都会让快照崩 | `battle-snapshot` | OPEN | P2 | 否 |
| CODOL-ISSUE-0071 | 客户端停在 '100' 弹窗、rc=-1，从未进大厅（任务 031 线） | `startup` | OPEN | P2 | 否 |
| CODOL-ISSUE-0072 | hosts 文件原始 937B 不可恢复（现 915B） | `startup` | OPEN | P2 | 否 |
| CODOL-ISSUE-0073 | service 4/13 才是房间服务，旧映射 service==11 会 UNMAPPED | `lobby` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0075 | 2697 包与 3.19 的记录层从未被观测：COOKIE_ECHO 189 vs 219、AES192/Tiger192 vs AES128/SHA1 | `protocol` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0079 | IIPS 的 Stage-1 前置门（QoS helper）从未被跨过 | `startup` | OPEN | P2 | 否 |
| CODOL-ISSUE-0080 | 用户态无法恢复 VM 解释器 / ISA / 解密器（.tvm0 语义） | `client-re` | BLOCKED | P2 | 否 |
| CODOL-ISSUE-0081 | ResourceManager ABI 大部分是虚构的；GetResourceManagerII 从未被调用 | `startup` | CONTRADICTORY_EVIDENCE | P2 | 否 |
| CODOL-ISSUE-0082 | 命令行语义与历史真实命令行均未知（-q/-qa/-src=tgp、argv 提供者槽） | `startup` | UNVERIFIED | P2 | 否 |
| CODOL-ISSUE-0083 | TCLS 共享内存布局与 tcls_core.exe 的创建者未知 | `startup` | OPEN | P2 | 否 |
| CODOL-ISSUE-0085 | 本地原生链被镜像识别拒绝（unknown executable image / SizeOfImage 门禁） | `startup` | BLOCKED | P2 | 否 |
| CODOL-ISSUE-0086 | 3.19 运行时镜像仅覆盖约 4.5% SizeOfImage | `client-re` | OPEN | P2 | 否 |
| CODOL-ISSUE-0088 | 固化链的参考实现本身带 6 次重试与共享 GAME_ROOT | `startup` | PARTIALLY_RESOLVED | P2 | 否 |
| CODOL-ISSUE-0089 | 黄金源目录含 208 个运行时残留，不能直接当干净启动树 | `baseline` | OPEN | P2 | 否 |
| CODOL-ISSUE-0034 | stats 分块状态是全局而非 per-peer，且重连时不重置 | `battle-network` | OPEN | P3 | 否 |
| CODOL-ISSUE-0037 | 两个 usercmd 处理分支重复且已出现分歧 | `battle-network` | OPEN | P3 | 否 |
| CODOL-ISSUE-0053 | ol-mod EngineBindings 宿主映像门禁永不通过（SizeOfImage 不匹配） | `combat` | BLOCKED | P3 | 否 |
| CODOL-ISSUE-0058 | 小地图为空：northyaw 缺失、compass_map_* 需地图边界 | `battle-snapshot` | OPEN | P3 | 否 |
| CODOL-ISSUE-0069 | C# v0.1 战斗服：无碰撞、无 hitscan、无伤害、无死亡复活 | `combat` | NOT_IMPLEMENTED | P3 | 否 |
| CODOL-ISSUE-0076 | Fragment stride 1154 vs 1162 未裁决 | `battle-network` | UNKNOWN | P3 | 否 |
| CODOL-ISSUE-0077 | 插件边界 31,953 行零测试；部署制品陈旧 | `build` | NOT_IMPLEMENTED | P3 | 否 |
| CODOL-ISSUE-0090 | TESTOL 交付包：1/769 哈希不符、缺 inject_ayria.on、deploy 只比大小 | `external` | OPEN | P3 | 否 |
| CODOL-ISSUE-0091 | 真实 Frida 运行时从未执行（T2 线） | `tooling` | UNVERIFIED | P3 | 否 |


---

## 逐项详情

### CODOL-ISSUE-0001 — 受保护基线 marketplace_store.py 哈希与清单不符（8/9）

- **系统**: `baseline`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-21（CODOL_ANALYSIS_20261020/THIRD_ROUND_BLOCKER_STATUS_20261021.md §4）
- **证据等级**: E0-local-recomputed

**问题现象**：REF_LOBBY_KIT/_golden_hashes.json 声明 marketplace_store.py 为 46,226 B / sha 28b4a1be…；实际 50,022 B / sha e44358f0…。其余 8 个文件复算与声明一致。

**预期行为**：AGENTS.md：受保护文件哈希变化即视为链被修改、该轮 run 无效。

**实际行为**：该文件自 2026-10-16 起即不符；--verify-only 只校验 6 个 launch_core 文件，因此启动校验不拦截。

**触发条件**：任何一次 run 前的基线校验。

**影响范围**：冻结链的完整性声明在形式上不成立；任何以'基线未变'为前提的结论都带一个已知例外。

**历史调查过程**：2026-10-21 第二轮审计即已记录为 preexisting_conflict；2026-10-27 再次记录；至今未处理。GOLDEN-LOBBY-001/REF_LOBBY_KIT 有一份 9/9 干净的源副本，但含 13 处运行时残留。

**当前最可信判断**：确定（本次审计复算）

**尚缺证据**：没有批准的 baseline migration 规则；没有说明 50,022 B 版本相对 46,226 B 的差异内容。

**最小验证方法**：对比两份文件的 diff，确认差异是否只是运行时残留（日志路径、证书、会话）。

**推荐修复方向**：走一次显式的 baseline migration：确认差异、更新清单、记录理由。不得直接改文件。

**证据来源**：

- `REF_LOBBY_KIT/_golden_hashes.json`
- `CODOL_ANALYSIS_20261020/THIRD_ROUND_BLOCKER_STATUS_20261021.md`
- `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md`
- `audit recomputation 2026-10-29: 9 entries, 8 OK, 1 mismatch`

**完成验收标准**：_golden_hashes.json 中 9 项全部匹配，或明确记载批准例外及其范围。

**复杂度**：S　**推荐处理顺序**：先于任何'基线完好'声明

---

### CODOL-ISSUE-0002 — 工作 kit 与受保护基线不同源，且每轮继续膨胀

- **系统**: `baseline`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-27（docs/FIX_MEMBERCOUNT_APPLIED_20261027.md §'一处既有偏差'）
- **证据等级**: E0-local-file-metadata

**问题现象**：lobby_server.py：受保护 76,410 B（2026-10-07）→ 工作 kit 88,162 B（2026-10-27）→ 10-29 三个 run 的 kit 分别为 108,173 / 108,944 / 109,705 B。

**预期行为**：受保护基线应是行为的事实来源。

**实际行为**：没有任何一份 lobby_server.py 是'事实来源'；每个 run 各有一份，逐轮增长。

**触发条件**：每次新建 run。

**影响范围**：任何'服务端行为'的结论都必须注明是哪一份文件；跨轮比较存在隐性变量。

**历史调查过程**：2026-10-27 记录'工作 kit 与受保护原件本来就不同源'。

**当前最可信判断**：确定

**尚缺证据**：没有补丁清单，无法从受保护版重建任一工作版。

**最小验证方法**：对 76,410 与 109,705 做逐函数 diff，产出一份补丁序列。

**推荐修复方向**：把补丁收敛成一个受版本管理的 patch 文件，作用于受保护基线。

**证据来源**：

- `REF_LOBBY_KIT/lobby_server.py`
- `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
- `run_codol_001/runs/ONCE_20261029_000806/kit/lobby_server.py`
- `run_codol_001/runs/ONCE_20261029_001513/kit/lobby_server.py`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_server.py`

**依赖**：`CODOL-ISSUE-0001`

**完成验收标准**：任一轮的 lobby_server.py 可由 受保护基线 + 补丁 确定性重建。

**复杂度**：M　**推荐处理顺序**：2

---

### CODOL-ISSUE-0003 — 全工作区无版本控制

- **系统**: `baseline`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: UNKNOWN（本次审计：Get-ChildItem 未找到任何 .git）
- **证据等级**: E0-local-filesystem

**问题现象**：D:\BaiduNetdiskDownload\使命召唤OL 及其所有子目录均非 git 仓库。

**预期行为**：能对源码与 kit 做 diff / blame / 回滚。

**实际行为**：所有变更只存在于目录副本与散文报告里。

**触发条件**：任何需要'上一版是什么'的判断。

**影响范围**：HANDOFF_20261025_BINARY_BISECT.md §6 自己写'源码级二分'时依赖人工记忆；此类调查不可复核。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：把 CODOL_SERVER_319_20261021 与各 kit 纳入 git（不包含受保护原件本体）。

**证据来源**：

- `filesystem scan 2026-10-29`

**完成验收标准**：战斗服源码与 kit 有可追溯的提交历史。

**复杂度**：M　**推荐处理顺序**：3

---

### CODOL-ISSUE-0004 — 战斗服构建产物不可复现：test_session.exe 与 codol_battle_server.exe 同尺寸

- **系统**: `build`
- **状态**: `UNVERIFIED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: UNKNOWN（本次审计：build/Debug 目录逐文件哈希）
- **证据等级**: E0-local-hash

**问题现象**：codol_battle_server.exe 314,368 B sha 275B165F…；test_session.exe 314,368 B sha 2CEFF239…。当前 CMakeLists.txt 中 test_session 源文件仅 2 KB。

**预期行为**：每个可执行文件与其源清单一一对应，可由干净目录重建。

**实际行为**：build 目录混有 10-21..10-26 多个源码状态的产物；无构建清单记录'哪个 exe 来自哪次源码'。

**触发条件**：需要证明'线上跑的二进制就是这份源码'时。

**影响范围**：任何'改了源码所以行为应改变'的推断都缺一环。

**历史调查过程**：无记录。

**当前最可信判断**：可疑度高，未定性

**尚缺证据**：缺少 10-26 22:07 那次构建的源码快照。

**最小验证方法**：在干净目录用当前 CMakeLists 重建，比较 exe 哈希。

**推荐修复方向**：增加 CI 式干净构建与产物哈希记录。

**证据来源**：

- `CODOL_SERVER_319_20261021/CMakeLists.txt`
- `CODOL_SERVER_319_20261021/build/Debug/*.exe (hashes)`
- `run_codol_001/runs/ONCE_20261029_002046/kit/codol_battle_server.exe`

**依赖**：`CODOL-ISSUE-0003`

**完成验收标准**：同源码两次干净构建产出字节相同的 exe，或记录不可复现的原因。

**复杂度**：M　**推荐处理顺序**：4

---

### CODOL-ISSUE-0005 — 22/22 离线测试未覆盖三个关键探针与任何客户端联调

- **系统**: `build`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: UNKNOWN（本次审计：CMakeLists 与 LastTest.log）
- **证据等级**: E0-local

**问题现象**：ctest 注册 22 项，2026-10-26 22:07 全部通过（22 Passed / 0 Failed）。但 probe_snapshot_size.c、probe_world_damage.c、sim_check.c、e2e_client.py 不在 ctest 里。

**预期行为**：'全绿'应覆盖产生最强证据的路径。

**实际行为**：世界伤害/clipmap trace 这类最强离线证据，来自手工探针而非回归套件。

**触发条件**：每次声称'22/22 全绿故无回归'。

**影响范围**：回归套件无法发现世界/伤害/实体层的退化。

**历史调查过程**：各报告沿用'22/22'作为质量门槛。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：把三个探针注册为 ctest 用例。

**推荐修复方向**：补注册；为 e2e_client.py 建一个模拟客户端契约测试。

**证据来源**：

- `CODOL_SERVER_319_20261021/CMakeLists.txt`
- `CODOL_SERVER_319_20261021/build/Testing/Temporary/LastTest.log`
- `CODOL_SERVER_319_20261021/tests/`

**完成验收标准**：ctest 覆盖探针；e2e_client 有一个可重复的契约用例。

**复杂度**：S　**推荐处理顺序**：5

---

### CODOL-ISSUE-0006 — 启动链只能在冻结 kit 上复现，无法从源码重建

- **系统**: `startup`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-21（ICH001..ICH059 系列；CODOL_EX001..EX068）
- **证据等级**: E1-static+E0-runtime

**问题现象**：IIPS/IFS2/TCLS 的初始化契约被逐层拆解（EX060–EX065、ICH027–ICH050），但没有任何自研实现能替代 REF_LOBBY_KIT 起客户端。

**预期行为**：能解释并复现启动所需的最小外部契约。

**实际行为**：全部可用启动都依赖冻结的 REF_LOBBY_KIT；run_frozen_chain_once.py 只做复制与校验。

**触发条件**：任何'不用 kit 能否启动'的尝试。

**影响范围**：启动链是黑盒依赖，无法独立演进或移植。

**历史调查过程**：ICH 系列（2026-09-18..09-21）与 EX 系列（同期）逐步推进，最终选择'冻结可用链'路线。

**当前最可信判断**：确定（依赖关系确定；契约完整性未定）

**尚缺证据**：IIPS 契约的函数级完整定义与错误域。

**最小验证方法**：用 EX060–065 的契约写一个最小 IIPS 替身，看是否仍能过 6 秒。

**推荐修复方向**：先不重写；把契约文档化为可执行规格后，再做替身实验。

**证据来源**：

- `ICH027_IIPS_ENGINE_CONTRACT.md`
- `CODOL_EX060_IIPS_CFG_CLOSURE.md`
- `CODOL_EX061_IIPS_THIS60_DATAFLOW.md`
- `CODOL_EX062_CNIFS_LIFECYCLE.md`
- `CODOL_EX063_IIPS_EXTERNAL_ENTRY.md`
- `run_codol_001/run_frozen_chain_once.py`

**完成验收标准**：存在一份自研 IIPS 实现能让客户端通过 6 秒门槛，或被证明不需要。

**复杂度**：XL　**推荐处理顺序**：低优先（kit 可用）

---

### CODOL-ISSUE-0007 — iips.ini 的 enable_iips 是隐性环境依赖，未纳入受保护清单

- **系统**: `startup`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-27（docs/PVE_BATTLESTART_STATUS_20261027_1220.md §0）
- **证据等级**: E0-runtime-verified

**问题现象**：COD OL\iips.ini 的 enable_iips=0 导致本体 6 秒必崩；改为 1 后完整进大厅（模块 83→93、5E8 1→3、Auth 10→11、31 个 service 全应答）。

**预期行为**：决定启动成败的配置应被基线覆盖并有文档。

**实际行为**：该文件在游戏目录内、不在 REF_LOBBY_KIT 清单中；备份 iips.ini.bak_before_iips_enable_20261027 是本地手工备份。

**触发条件**：换机器 / 重装 / 恢复游戏目录。

**影响范围**：结论'客户端能进大厅'依赖一个手工改过的、未受管制的文件。

**历史调查过程**：2026-10-27 定位并修复；此前把 6 秒崩溃误归因为 ACE/.local/TAS，三条均被实测排除。

**当前最可信判断**：确定（修复有效）

**尚缺证据**：没有把该文件纳入任何清单或校验。

**最小验证方法**：在干净副本上把 enable_iips 改回 0，确认 6 秒崩复现。

**推荐修复方向**：把 iips.ini 的期望值纳入 run preflight 校验。

**证据来源**：

- `docs/PVE_BATTLESTART_STATUS_20261027_1220.md`
- `docs/PROGRESS_SAVE_20261027.md §三.1`

**完成验收标准**：preflight 会校验 iips.ini 的关键项，不一致时拒绝启动并说明。

**复杂度**：S　**推荐处理顺序**：6

---

### CODOL-ISSUE-0008 — 启动单发令牌与提权 agent 是隐性外部依赖

- **系统**: `startup`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: UNKNOWN（run_codol_001/run_frozen_chain_once.py）
- **证据等级**: E0-local

**问题现象**：run_frozen_chain_once.py 要求 CODOLServer/logs/elevated_agent.json 存在且 debug_privilege=true、PID 存活；当前指向 pid 5180 / port 56961（文件 2026-10-28 21:22）。

**预期行为**：启动前置条件应可程序化确认。

**实际行为**：agent 需由人先以提权方式拉起；PID 一旦失效，所有 run 失败。

**触发条件**：重启机器 / agent 崩溃。

**影响范围**：'为什么这轮没跑起来'可能是环境问题而非技术问题，跨轮结论因此不可比。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：agent 的重启脚本与健康检查。

**最小验证方法**：停掉 agent 后跑一次 launcher，确认拒绝原因清晰。

**推荐修复方向**：把 agent 的启动/健康检查纳入 preflight，并在 run 目录记录其身份。

**证据来源**：

- `run_codol_001/run_frozen_chain_once.py:315-335`
- `CODOLServer/logs/elevated_agent.json`

**完成验收标准**：每个 run 的 preflight.json 记录 agent PID/端口/版本，且失败原因可区分环境与技术。

**复杂度**：S　**推荐处理顺序**：7

---

### CODOL-ISSUE-0009 — 准备按钮点击不产生任何客户端上行，根因未定

- **系统**: `lobby`
- **状态**: `BLOCKED`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/READY_BUTTON_NO_RESPONSE_20261028.md）
- **证据等级**: E0-runtime-observed + E1-static

**问题现象**：用户按'准备'完全无反应；该轮 11/4 上行只有 4 条（房间初始化/成员状态/房间状态/mmbook），没有任何一条是'准备'。本地'已准备'状态也不变。

**预期行为**：点击应产生一条上行并把本地状态置为已准备。

**实际行为**：零上行、零本地状态变化。

**触发条件**：进入 BOT 房间 UI 后点击准备。

**影响范围**：BOT 房间入口无法走通；只能依赖 PvE 剧情入口（该入口从不使用此按钮）。

**历史调查过程**：先判为'AS_SetReadyState 未实现'（RTTI 无 COL、零引用）；后被修正为'dwRoomMatch::Init 未调用 ⇒ MyEventHandler 零实例'。两条解释并存，未判定哪条是根因。

**当前最可信判断**：现象确定；根因未定

**尚缺证据**：无法读活进程内存（ACE），无法反编译 ui_mp.ff（加密），无 .gfx 工具。

**最小验证方法**：在被明确批准的一次实验里，只改一个变量：让服务端在 createRoom 后推送 RoomInfo + RoomStateUpdated（已离线对拍通过的位流），观察按钮是否变为可点。

**推荐修复方向**：先确定'按钮禁用条件'的数据来源：房间状态对象是否因缺少服务端推送而未进入可准备态。

**证据来源**：

- `docs/READY_BUTTON_NO_RESPONSE_20261028.md`
- `docs/READY_BUTTON_NO_IMPL_20261028.md`
- `docs/AS_CLASSES_INVENTORY_20261028.md`
- `docs/UI_FF_ENCRYPTED_20261028.md`
- `docs/READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md`

**依赖**：`CODOL-ISSUE-0010`, `CODOL-ISSUE-0012`

**完成验收标准**：点击准备后，lobby_srv.log 出现一条可识别的准备上行，且本地 UI 状态改变。

**复杂度**：L　**推荐处理顺序**：P0-1

---

### CODOL-ISSUE-0010 — 房间下行推送格式在'位流 / 容器'之间反复，最终未定死

- **系统**: `lobby`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/ROOM_DIRECTION_SPLIT_20261028.md / TYPE02_IS_TEXT_20261028.md）
- **证据等级**: E0-runtime-behaviour-diff + E1-static

**问题现象**：上行 body 首字节只出现 0x02 与 0x18（87 条样本），且穷举 160 bit 偏移无 readBits==3 ⇒ 上行不是位流；下行由各 RoomMessage::deserialize 读位流（0x637000 以 (ptr, len*8) 直接建流）。据此重编后，实机首次出现可观测差异（任务数 85→71、11/4 由 6 次降为 4 次），但战斗服仍零收包，UI 是否点亮未确认。

**预期行为**：服务端能构造出被客户端接受并无错误地改变房间状态的下行消息。

**实际行为**：消息被处理（有行为差异）但未达成目标；无法确认是否被正确解析。

**触发条件**：createRoom 后的三条推送。

**影响范围**：房间状态机无法由服务端驱动。

**历史调查过程**：10-28 内至少经历四轮反转：位流 → 容器 → 上下行不同 → type02 是文本。每次反转都伴随一次实机无效。

**当前最可信判断**：两套格式都被部分证伪；最终形态未定

**尚缺证据**：无法确认客户端是否解析成功（无日志、无法读内存）。

**最小验证方法**：对同一条消息做'故意畸形'对照：若客户端 ack/行为对该消息敏感，说明确被解析；否则说明被忽略。

**推荐修复方向**：先用畸形对照建立'客户端确实在读这段'的证据，再谈内容正确性。

**证据来源**：

- `docs/ROOM_DIRECTION_SPLIT_20261028.md`
- `docs/TYPE02_IS_TEXT_20261028.md`
- `docs/DOWNLINK_STREAM_RUN_20261028.md`
- `docs/ROOM_MSG_NOT_BITSTREAM_20261028.md`
- `docs/ROOM_PROTOCOL_COMPLETE_20261028.md`
- `docs/ROOM_PUSH_SPEC_FIX_RUN_20261028.md`

**完成验收标准**：有一条消息能被证明被客户端解析（畸形对照产生可测差异）。

**复杂度**：L　**推荐处理顺序**：P0-2

---

### CODOL-ISSUE-0011 — 房间推送的路由信封未定死（route key = roomId 高低 32 位）

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md）
- **证据等级**: E0-memdump-static

**问题现象**：0x7E7C90 按 (p1,p2) 遍历表，建房间后表项 [+0x10]=roomId_lo、[+0x14]=roomId_hi、[handler]=0x6371F0；0x7E79C0 校验 [obj+8]==key_hi、[obj+0xc]==key_lo。现有三种信封构造都不满足。

**预期行为**：推送信封里解出的对象在 +8/+0xc 等于 roomId。

**实际行为**：build_room_push 把 roomId 放在 offset 25；instant_push_body(kind=11) 完全不含 roomId；channel_push_body 位置不符。

**触发条件**：任何房间推送。

**影响范围**：若路由键不匹配，消息即使格式正确也会被静默丢弃。

**历史调查过程**：10-28 前两轮按 (service,task) 读路由表全为 0，属误判，已推翻。

**当前最可信判断**：路由键语义确定；信封字节布局未定

**尚缺证据**：槽6 的调用者静态不可定位；硬件断点被 ACE 拒绝。

**最小验证方法**：在早期转储窗口内多次快照，观察 dwLobbyEventHandler+0x18/+0x1c 何时被写；但建房发生在 ACE 生效后，窗口不重叠。

**推荐修复方向**：找一个能在建房后仍可读的证据源（官方抓包、另一客户端实现、或非 ACE 环境）。

**证据来源**：

- `docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md`
- `docs/ROOM_CHANNEL_RECV_CHAIN_20261028.md`
- `docs/ROOM_OBJECT_LAYOUT_20261028.md`
- `docs/ROOM_PUSH_CHANNEL_WRONG_20261028.md`

**完成验收标准**：能构造出满足 obj+8/obj+0xc == roomId 的信封，并被客户端接受。

**复杂度**：L　**推荐处理顺序**：P0-3

---

### CODOL-ISSUE-0012 — dwRoomMatch::Init 从未被调用（MyEventHandler 零实例）

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-27（docs/GATE_B_INIT_PATH_20261027.md §'完整因果链闭合'）
- **证据等级**: E0-memdump

**问题现象**：整份 1478 MB 转储里搜 vtable 0x00DC78F0 的实例，一个都没有。

**预期行为**：Init 执行时应创建 MyEventHandler，其 slot[1]=0x63B500 是建房回调。

**实际行为**：零实例 ⇒ 0x63B500 永不被调用 ⇒ 0x63E510 不执行 ⇒ dwRoomMatchUber 不创建。

**触发条件**：进入大厅/房间阶段。

**影响范围**：整条自动开局链的上游断点。

**历史调查过程**：2026-10-27 由'三个包装函数是控制台命令'上溯到控制台注册表，再从 0x63B500 的 vtable 反推。2026-10-28 从符号层独立确认 MyEventHandler 是 dwRoomMatch::Init 的局部类。

**当前最可信判断**：实例数为 0：确定；Init 未调用的原因：未知

**尚缺证据**：Init 的调用点。函数体在加密节 .tp3（VSize 219 MB / RawSize 401 KB），静态看不到。

**最小验证方法**：行为二分：按 BISECT_EXPERIMENT_PLAN 逐组关闭大厅应答，看按钮是否变为可点。需用户逐轮反馈。

**推荐修复方向**：找到 Init 的调用条件；最可能是某条大厅应答前置数据。

**证据来源**：

- `docs/GATE_B_INIT_PATH_20261027.md`
- `docs/READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md`
- `docs/BISECT_EXPERIMENT_PLAN_20261028.md`

**依赖**：`CODOL-ISSUE-0009`

**完成验收标准**：转储中出现 MyEventHandler 实例（vtable 0x00DC78F0），且 0x63B500 被调用。

**复杂度**：L　**推荐处理顺序**：P0-4

---

### CODOL-ISSUE-0013 — 自动开局状态机停在状态 1（计时器从未启动）

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-27（docs/AB_MEMBERCOUNT_RESULT_20261027.md）
- **证据等级**: E0-memdump

**问题现象**：memberCount 修复后 dwRoomMatchUber 出现（vtable 0x00DC795C 校验通过、+0x68=0x63C5E0），但 [U+0x20]=1 停在状态 1；状态 1 在 0x63C350 返回假处返回。对象 +0x138/+0x140（计时器）实测全 0。

**预期行为**：状态推进到 5（0x63C970 自动开局）。

**实际行为**：停在状态 1；计时器字段全 0 ⇒ 从未启动。

**触发条件**：建房成功后。

**影响范围**：即使房间对象存在，自动开局也不发生。

**历史调查过程**：2026-10-27 从'对象不存在'推进到'对象存在但状态机停住'。

**当前最可信判断**：确定（停在状态 1）

**尚缺证据**：0x63C350 / 0x63C550 两个判据的具体条件；计时器的启动者。

**最小验证方法**：静态解 0x63C350 与 0x63C550；对比建房前后对象字段找出被谁写。

**推荐修复方向**：先解判据，再谈计时器。

**证据来源**：

- `docs/AB_MEMBERCOUNT_RESULT_20261027.md`
- `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md`
- `docs/PROGRESS_SAVE_20261027.md §四`

**依赖**：`CODOL-ISSUE-0012`

**完成验收标准**：状态机推进到 2 以上，或判据被解出并可被服务端满足。

**复杂度**：M　**推荐处理顺序**：P0-5

---

### CODOL-ISSUE-0015 — memberCount 修复已落地但语义来自 ol-mod（非本 build）

- **系统**: `lobby`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-27（docs/LOBBY_TRAFFIC_GAP_20261027.md）
- **证据等级**: E0-A/B-runtime

**问题现象**：11/13 createRoom 应答 [u64 roomId][u32 memberCount][u32 18][u64 secondId]… 中 memberCount 原为 0，改 1 后 dwRoomMatchUber 首次出现。

**预期行为**：字段语义应有本 build 的证据。

**实际行为**：该结构注明来自 ol-mod Unknown0BService（3.3.3.3），按项目规范不能直接采信；但 A/B 实测证明改 1 确实改变了客户端行为。

**触发条件**：每次 createRoom。

**影响范围**：'为什么是 1 而不是 2 或成员数'没有依据。

**历史调查过程**：10-27 两轮 A/B（memberCount=0 vs 1）+ 正式 kit 复跑。

**当前最可信判断**：行为相关性确定；语义未证

**尚缺证据**：本 build 客户端读 memberCount 的代码点。

**最小验证方法**：再试 memberCount=2，看对象是否仍创建、状态机是否更前进。

**推荐修复方向**：以行为为准；同时把'来自 ol-mod'的出处标注保留在代码注释里。

**证据来源**：

- `docs/LOBBY_TRAFFIC_GAP_20261027.md`
- `docs/AB_MEMBERCOUNT_RESULT_20261027.md`
- `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md`

**完成验收标准**：本 build 中该字段的读取点被静态定位，或 A/B 证明 1 是唯一有效值。

**复杂度**：S　**推荐处理顺序**：可并行

---

### CODOL-ISSUE-0016 — 大厅存在大量 UNMAPPED service/task，一律回空 ACK

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-28（run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log）
- **证据等级**: E0-runtime-log

**问题现象**：最近一轮出现 71/3、71/4、71/7、71/10、71/13、71/15、71/18、12/6、9/14、3/53、29/10、10/20、68/3、28/1、28/4、4/13、3/46、3/48、9/5、4/4 等 UNMAPPED，全部 '空 ACK (功能未实现)'。

**预期行为**：每个客户端会发的请求都应有已定义应答或明确'可安全空回'的依据。

**实际行为**：未见系统性清单说明哪些可空回、哪些不能。

**触发条件**：大厅每次初始化与房间互动。

**影响范围**：任何一条空回都可能成为某一功能静默失效的原因（准备按钮即为一例）。

**历史调查过程**：LOBBY_TRAFFIC_GAP_20261027.md 统计过 42 类请求；6/5 订阅 20 个事件服务端一个没推。

**当前最可信判断**：确定（现象）；影响面未知

**尚缺证据**：每个 UNMAPPED 请求的语义与'空回是否安全'的判据。

**最小验证方法**：逐个补最小合法应答，观察客户端行为差异。

**推荐修复方向**：先建'请求清单 + 语义 + 是否可空回'的表，再补。

**证据来源**：

- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`
- `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py:1238`

**完成验收标准**：每个客户端请求在日志中都有已定义的语义分类。

**复杂度**：L　**推荐处理顺序**：可并行（P2）

---

### CODOL-ISSUE-0017 — 客户端订阅 20 个 MM 事件，服务端从未推送任何一个

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-27（docs/LOBBY_TRAFFIC_GAP_20261027.md）
- **证据等级**: E0-runtime-log

**问题现象**：6/5 请求 payload 为 08 00 00 00 00 | 08 14 00 00 00 | 01 | 01 00（订阅 20 个事件）；出现 2 次，服务端两次都只回空应答。

**预期行为**：订阅后应有事件推送。

**实际行为**：全轮服务端仅 4 条推送，全部来自 11/4 回显 + game start。

**触发条件**：大厅初始化。

**影响范围**：房间状态无法由事件驱动更新。

**历史调查过程**：与 CODOL-ISSUE-0009/0010 同源。

**当前最可信判断**：确定（未推送）；'必须推送'是推断

**尚缺证据**：20 个事件编号到 dwRoomMessage* 类名的映射表。

**最小验证方法**：推一条 RoomInfo，观察客户端是否改变。

**推荐修复方向**：先解 6/5 请求里的编号序列到类名。

**证据来源**：

- `docs/LOBBY_TRAFFIC_GAP_20261027.md`

**依赖**：`CODOL-ISSUE-0010`

**完成验收标准**：20 个事件编号有映射表，且至少一条被客户端正确消费。

**复杂度**：M　**推荐处理顺序**：P0 关联

---

### CODOL-ISSUE-0018 — GAME_START_PAYLOAD(162B) 是靶场抓包常量，不是 coop 开局数据

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-07（codol_crypto.py:803-826 自述）
- **证据等级**: E0-offline-decode

**问题现象**：离线解包显示 F807(=2047) 出现 10 次，正是快照'恒在空中'哨兵 ⇒ 确为靶场快照。

**预期行为**：开局推送体应携带本局地图/模式信息。

**实际行为**：是三方从 firingrange 抓到的常量；实机触发+推送都成功但 PvE 仍停'战斗开始'、战斗服 0 收包。

**触发条件**：11/4 setRoomData(ready) 后的 game start 推送。

**影响范围**：任何'已推送开局数据'的结论都不成立。

**历史调查过程**：2026-10-07 抓取；2026-10-26 与 10-27 两次实机均无效。

**当前最可信判断**：确定（不是 coop 数据）

**尚缺证据**：真实 coop 开局数据；停服前的官方抓包（未见留存）。

**最小验证方法**：搜索 docs/ 与历史 run 是否留有当年抓包。

**推荐修复方向**：改由 dwRoomMessageStartGame 承担开局（已解出 serialize 首段）。

**证据来源**：

- `docs/PVE_BATTLESTART_STATUS_20261027_1220.md §4`
- `docs/PVE_STARTGAME_BLOCKER_20261026.md`
- `CODOL_VERIFIED_GOLDEN_20261019/codol_crypto.py`

**依赖**：`CODOL-ISSUE-0010`

**完成验收标准**：开局路径不再依赖 162B 常量。

**复杂度**：M　**推荐处理顺序**：P0 关联

---

### CODOL-ISSUE-0020 — BOT 房间场景下战斗服零收包（客户端从不 connect）

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-26（docs/PVE_STARTGAME_BLOCKER_20261026.md）
- **证据等级**: E0-runtime-verified

**问题现象**：客户端进程打开的 UDP 端口（22011/50095/…）没有一个连向 28960；战斗服日志 TX_NAT_REPLY=0 KEY_EXCHANGE_OK=0 RX_CLIENT_GAME_HEADER=0。

**预期行为**：客户端应发起 NAT/DTLS/getchallenge/connect。

**实际行为**：零收包。10-29 最新一轮仍然如此：_battle_out.txt 只有 7 行初始化。

**触发条件**：从 BOT 房间入口点开始/准备。

**影响范围**：任何战斗功能都无从验证。

**历史调查过程**：10-26 PvE 入口的 8 轮曾成功连上（mmstart 携带 map + g_gametype）。10-27 之后即使同样形态也全灭。10-28 提出三个候选：mmstart 无 map、102/7 回全 0、mmstart 推 StartGame。

**当前最可信判断**：现象确定；根因多候选未二分

**尚缺证据**：没有做过单变量二分（10-28 列出了计划但未见执行记录）。

**最小验证方法**：按 BATTLE_CONNECT_DIVERGENCE §五：mmstart 不推 StartGame、102/7 恢复不处理、memberCount 保留 1，跑一轮。

**推荐修复方向**：先做上述单变量回归，确认是否回到 10-26 行为。

**证据来源**：

- `docs/PVE_STARTGAME_BLOCKER_20261026.md`
- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`
- `docs/BATTLE_CONNECT_DIVERGENCE_20261028.md`
- `docs/DOWNLINK_STREAM_RUN_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/_battle_out.txt`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`

**依赖**：`CODOL-ISSUE-0009`, `CODOL-ISSUE-0010`

**完成验收标准**：战斗服日志出现 TX_NAT_REPLY 或 KEY_EXCHANGE_OK 或 RX_CLIENT_GAME_HEADER 之一。

**复杂度**：M　**推荐处理顺序**：P0-0（最高）

---

### CODOL-ISSUE-0021 — mmstart 中的 playlist 编号在本轮解析为 37 而 findSessions 为 50，且均非官方 ID

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md）
- **证据等级**: E0-runtime-log

**问题现象**：10-29 最新一轮：findSessions playlist=50 → 命中本地 mp_raid；mmstart 带 playlist 37 + start_map_rotate_once 7；lobby 日志打印 'mmstart 选择: gametype=? map=?'。

**预期行为**：房间最终地图/模式应唯一且本地可用。

**实际行为**：两个编号语义不同（ID / 下标 / 轮换序号三解未定），且 mmstart 未带 map。

**触发条件**：从 BOT 房间点开始。

**影响范围**：客户端拿不到目标地图 ⇒ 推断不发起 connect。

**历史调查过程**：10-28 已统计全 57 轮：A 形态（带 g_gametype）25 轮有 8 轮成功，B 形态（playlist 37）8 轮 0 成功。

**当前最可信判断**：相关性确定；因果未证

**尚缺证据**：playlist 编号的真实语义（官方表 123 项中无 37/50）。

**最小验证方法**：让 mmstart 也带 `map <本地图>; g_gametype coop`（复制 10-26 成功形态）跑一轮。

**推荐修复方向**：统一 findSessions 与 mmstart 指向同一张本地可用图。

**证据来源**：

- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`

**完成验收标准**：mmstart 携带的 map==findSessions 回的地图，且战斗服收到连接。

**复杂度**：S　**推荐处理顺序**：P0-1

---

### CODOL-ISSUE-0022 — 战斗服 --map 参数不改变碰撞数据（仍加载 coop_train clipmap）

- **系统**: `battle-world`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: UNKNOWN（本次审计：源码 + 10-29 run 日志）
- **证据等级**: E0-local-source

**问题现象**：_battle_out.txt 打印 `world "mp_raid" assets loaded (29 clip volumes)`。codol_clipmap_coop_train.inc 只有 29 行，内容全是 mp_firingrange 的道具（tire_wall 等）。

**预期行为**：--map 选择对应地图的碰撞几何。

**实际行为**：world.c:66-67 把 clipmap 与 map_ents 都指向同一个编译期数组；--map 只存字符串。

**触发条件**：任何换图。

**影响范围**：即使连上，客户端与战斗服的地图必然不一致。

**历史调查过程**：10-27 文档已指出'换图不会改变客户端是否连 28960'，但未指出服务端也不会换碰撞。

**当前最可信判断**：确定

**尚缺证据**：没有 mp_raid 的 clipmap 提取。

**最小验证方法**：加一个断言：map_name 与 clipmap 来源不一致时打警告。

**推荐修复方向**：按地图名选择 clipmap（需要先提取对应 zone）。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/world_assets/world.c:60-67`
- `CODOL_SERVER_319_20261021/include/codol_clipmap_coop_train.inc`
- `run_codol_001/runs/ONCE_20261029_002046/kit/_battle_out.txt`
- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md §五`

**完成验收标准**：加载 mp_raid 时使用 mp_raid 的碰撞数据。

**复杂度**：L　**推荐处理顺序**：P1

---

### CODOL-ISSUE-0023 — TX 快照缓冲仅 512 B，零售快照 7000–15000 B，且无下行分片

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-25（HANDOFF_20261025_BINARY_BISECT.md §16.4）
- **证据等级**: E0-local-source + E0-retail-corpus

**问题现象**：battle_service.c:425 uint8_t snap[512], payload[520]；零售首帧实测 14962 B。

**预期行为**：能发送完整对局快照。

**实际行为**：实体段上限 8 条（约 10 个实体）。

**触发条件**：实体数超过约 10。

**影响范围**：完整实体名册（334 条）不可能下发。

**历史调查过程**：已记录，未处理。

**当前最可信判断**：确定

**尚缺证据**：下行分片协议格式未解。

**最小验证方法**：把缓冲扩到 16 KB 并只发一条超大快照，看客户端是否仍需分片。

**推荐修复方向**：扩缓冲 + 实现服务端→客户端分片。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:425`
- `HANDOFF_20261025_BINARY_BISECT.md §16.4`

**完成验收标准**：可下发 >4 KB 的快照且客户端 ack 不断。

**复杂度**：L　**推荐处理顺序**：P1-2

---

### CODOL-ISSUE-0024 — 实体段客户端收得下但看不到（model_index 恒 0、实体号冲突）

- **系统**: `battle-entity`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-24（HANDOFF_20261025_BINARY_BISECT.md §17）
- **证据等级**: E0-runtime-verified（不判废）+ 推断（未渲染）

**问题现象**：开 snapshot_entities.on 后 ack 速率 83.02→83.05/s（比值 1.00），快照 103→176 B ents=8；撤掉即回 103。但游戏内看不到任何实体。

**预期行为**：能看到地图实体。

**实际行为**：只发 eType+origin 三坐标；model_index 由 memset 恒 0；号 0..7 是客户端自己的玩家/装饰槽。

**触发条件**：打开实体开关。

**影响范围**：多人/实体同步不可见。

**历史调查过程**：10-24 同客户端 ON/OFF 对照。

**当前最可信判断**：'包未被判废'确定；'是否被解析'未证

**尚缺证据**：没有做过畸形实体段对照来证明客户端确实在读这段。

**最小验证方法**：故意发截断字段的实体段，看 ack 是否中断。

**推荐修复方向**：先做畸形对照；再补 model/configstring 绑定与正确实体号空间。

**证据来源**：

- `HANDOFF_20261025_BINARY_BISECT.md §17`
- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:497-510`
- `CODOL_SERVER_319_20261021/src/entity/entity.c`

**依赖**：`CODOL-ISSUE-0023`

**完成验收标准**：客户端世界里出现一个我们发送的、可见的、原本不存在的实体。

**复杂度**：L　**推荐处理顺序**：P1-3

---

### CODOL-ISSUE-0025 — 服务端位置推不动客户端；omit=1 是唯一能用的配置

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-24（HANDOFF_20261025_BINARY_BISECT.md §13）
- **证据等级**: E0-runtime-verified

**问题现象**：三个坐标（355 1371 0 / 48 -572 -116 / -44 -387 -83）× 两种频率（只首帧 / 每帧）全部无效；字节级确认坐标确实上线（omit=0 包在 0x19–0x23 不同）。

**预期行为**：服务端权威位置应被客户端采纳。

**实际行为**：客户端本地玩家位置完全不受快照影响。

**触发条件**：任何 omit=0 配置。

**影响范围**：服务端无法权威控制玩家位置；出生点无法由服务端决定。

**历史调查过程**：10-24 两轮实机；10-25 已撤回服务端发坐标。

**当前最可信判断**：确定（推不动）；机制未定

**尚缺证据**：客户端为什么不采纳（clientInfo 段假设已被 §15 的参照对比部分削弱）。

**最小验证方法**：对比官方客户端在真实服务端下的同字段行为（无官方抓包则不可行）。

**推荐修复方向**：候选：补实体/客户端信息段；或承认客户端权威、服务端只做校验。

**证据来源**：

- `HANDOFF_20261025_BINARY_BISECT.md §13`
- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:486`

**依赖**：`CODOL-ISSUE-0024`

**完成验收标准**：客户端本地玩家位置随服务端快照变化（同一会话内可观测）。

**复杂度**：L　**推荐处理顺序**：P1-4

---

### CODOL-ISSUE-0027 — 11 个 playerState 字段仍用 XOR 增量而三份参照都写裸值

- **系统**: `battle-snapshot`
- **状态**: `UNVERIFIED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-24（docs/SNAPSHOT_FIELD_DIFF_20261024.md）
- **证据等级**: E0-runtime-partially-verified

**问题现象**：离线演示：输入相同、帧 2 差 8 字节；未动的值编码成 0 ⇒ 等于告诉客户端 position=(0,0,0)。

**预期行为**：与参照一致写裸值。

**实际行为**：2026-10-24 已按结论 1 改为裸值并实机验证'一条成一条坏'——裸值那条成了（用户确认弹药/换弹正常、默认主武器），idx61 那条坏了并已回退。

**触发条件**：第二帧起。

**影响范围**：已部分修复；需要确认哪些字段仍在 XOR。

**历史调查过程**：2026-10-24 修复并在 RUN SNAPSHOT_RAWFIX_20261024_1357 实机确认一半有效。

**当前最可信判断**：部分已验证

**尚缺证据**：逐字段确认当前源码里哪些仍是 XOR。

**最小验证方法**：跑 tools/offline_snapshot_crosscheck.py 并逐字段对拍。

**推荐修复方向**：继续按'一次一个字段 + 实机确认'推进。

**证据来源**：

- `docs/SNAPSHOT_FIELD_DIFF_20261024.md`
- `CODOL_SERVER_319_20261021/src/battle/snapshot.c`
- `tools/offline_snapshot_crosscheck.py（22/22 绿）`

**完成验收标准**：所有字段的编码方式与实测对照表一致，且有实机确认。

**复杂度**：M　**推荐处理顺序**：P1-5

---

### CODOL-ISSUE-0028 — 跳跃在 usercmd 网络路径上不可能触发（walking 从不被刷新）

- **系统**: `movement`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-29（本次审计：src/movement/movement.c）
- **证据等级**: E0-local-source

**问题现象**：codol_pmove_single() 里 jump 分支要求 pm->walking 为真，但 codol_movement_process_usercmd_dt() 每次构造全新局部 codol_player_t、设 on_ground=true，从不设置 walking，也从不调用 codol_pmove_single()。

**预期行为**：按住跳跃键应起跳。

**实际行为**：网络路径上 jump 分支不可达。

**触发条件**：任意跳跃输入。

**影响范围**：垂直移动完全依赖客户端预测；服务端永远认为玩家在地面。

**历史调查过程**：无记录。

**当前最可信判断**：确定（代码级）

**尚缺证据**：实机确认客户端跳跃时服务端表现。

**最小验证方法**：单测：构造一个 buttons=0x01 的 usercmd，断言 vz 变化。当前必然失败。

**推荐修复方向**：把 walking/on_ground 在 usercmd 路径里正确维持，或直接改用 trace 结果。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/movement/movement.c:71-141`

**完成验收标准**：带跳跃键的 usercmd 使 vz>0 且随后被重力拉回。

**复杂度**：S　**推荐处理顺序**：P1-6

---

### CODOL-ISSUE-0029 — 服务端地面是写死的无限平面 z=-116，与任何地图无关

- **系统**: `movement`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-26（docs/CLIPMAP_EXTRACTION_20261026.md + 源码）
- **证据等级**: E0-local-source + E1-local-extraction

**问题现象**：collision.c:11 const float codol_ground_z = -116.0f；trace 里 delta[2]<0 一律在 codol_ground_z 截断。coop clipmap 30 个 brush 覆盖 x -824..-177，出生点 (48,-572) 之外。

**预期行为**：地面来自地图碰撞数据。

**实际行为**：无限大平面常数。

**触发条件**：任何下落。

**影响范围**：所有垂直运动都被这个常数决定；换图无意义。

**历史调查过程**：2026-10-26 提取出 mp_firingrange 的 7587 平面/18770 brushside/1104 个朝上平面，但 cbrush_t 表尚未定位。

**当前最可信判断**：确定

**尚缺证据**：mp_firingrange 的 cbrush_t(36B) / brushBounds / brushContents 表位置。

**最小验证方法**：完成 MP_FIRINGRANGE_CLIPMAP 的下一步（定位 brush 表），生成完整 clipmap 后替换 inc。

**推荐修复方向**：用真实几何替换常数平面。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/world/collision.c:11,93-104`
- `docs/CLIPMAP_EXTRACTION_20261026.md`
- `docs/MP_FIRINGRANGE_CLIPMAP_20261026.md`

**依赖**：`CODOL-ISSUE-0022`

**完成验收标准**：任意出生点下方有真实地板面，服务端 trace 能落到地图几何上。

**复杂度**：L　**推荐处理顺序**：P1-7

---

### CODOL-ISSUE-0030 — 子弹命中不是射线：距离公式 + 固定假目标 + 固定武器

- **系统**: `combat`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-29（本次审计：src/battle/battle_service.c）
- **证据等级**: E0-local-source

**问题现象**：apply_test_hit() 用 |target.origin - player.origin| 作为 distance，武器写死 m4a1tech_mp，命中部位写死 CODOL_HITLOC_TORSO_UPPER；无方向、无 trace、无 miss。ensure_damage_target() 在 (0,0,-116) 生成 owner=1001 的合成 actor。

**预期行为**：沿视线方向做 trace，命中才结算。

**实际行为**：每次开火都对固定点结算。

**触发条件**：任意开火。

**影响范围**：'命中/伤害已闭合'的结论只在合成目标上成立。

**历史调查过程**：INMATCH_COMPLETENESS_GAP_MATRIX 标为 PARTIAL。

**当前最可信判断**：确定

**尚缺证据**：真实射线命中链（trace → hitloc → G_Damage 分支）。

**最小验证方法**：用 probe_world_damage 增加'目标在障碍物后应打不中'的用例。

**推荐修复方向**：用 codol_movement_trace() 替换距离公式。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:53-102`
- `CODOL_SERVER_319_20261021/src/world/combat.c`

**依赖**：`CODOL-ISSUE-0029`

**完成验收标准**：有遮挡时命中失败，无遮挡时命中，伤害随距离衰减。

**复杂度**：M　**推荐处理顺序**：P1-8

---

### CODOL-ISSUE-0031 — 合成靶子血量不重置，长跑后所有命中都打在 0 血实体上

- **系统**: `combat`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：src/battle/battle_service.c）
- **证据等级**: E0-local-source

**问题现象**：ensure_damage_target() 只在不存在时生成；codol_damage_apply 把 health 夹到 0；无复活/重置路径。

**预期行为**：靶子可重复用于验证。

**实际行为**：33 伤害 ×4 次后归零，此后 HIT 日志仍打印但 health 不再变化。

**触发条件**：长 run。

**影响范围**：可能把'没有伤害变化'误读为逻辑失效。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：连打 5 次，观察第 5 次 health。

**推荐修复方向**：命中后重置，或按地图 actor 的复活规则处理。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:53-74, 76-102`

**依赖**：`CODOL-ISSUE-0030`

**完成验收标准**：连续 10 次命中后目标仍可被伤害（或按规则死亡并复活）。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0032 — 投射物/爆炸、模式击杀、复活、复制层全部定义但从未被调用

- **系统**: `combat`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-29（本次审计：全 src 调用点 grep）
- **证据等级**: E0-local-source

**问题现象**：codol_projectile_spawn/step/trigger 无调用者；codol_mode_player_killed、codol_mode_respawn_due 无调用者；codol_replication_build/_ack 无调用者；codol_world_step 的 commands 参数在 main.c 传 NULL,0。

**预期行为**：对局生命周期由模式状态机驱动。

**实际行为**：这些子系统只在测试里被调用。

**触发条件**：任何完整对局尝试。

**影响范围**：对局无法结束、无法计分、无法复活、无投掷物。

**历史调查过程**：INMATCH_COMPLETENESS_GAP_MATRIX 标为 PARTIAL（'静态闭环'）。

**当前最可信判断**：确定（未接线）

**尚缺证据**：接线方式与事件顺序。

**最小验证方法**：在 main.c 里把 world_step 的 commands 接上，跑一次完整对局日志。

**推荐修复方向**：按 INMATCH 的门槛 5 逐项接线。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/main.c:164`
- `CODOL_SERVER_319_20261021/src/world/gamemode.c`
- `CODOL_SERVER_319_20261021/src/world/projectile.c`
- `CODOL_SERVER_319_20261021/src/replication/replication.c`

**依赖**：`CODOL-ISSUE-0030`

**完成验收标准**：一次对局内出现 spawn→kill→score→respawn→end 的可复核日志链。

**复杂度**：L　**推荐处理顺序**：P1-9

---

### CODOL-ISSUE-0033 — 战斗服 struct 是单客户端设计，多客户端不可表达

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c）
- **证据等级**: E0-local-source

**问题现象**：一个 svc 里只有一份 player / equip / snap_from / snap_cur / input_baselines；send_snapshot 只写本地客户端状态。

**预期行为**：多客户端各自的快照。

**实际行为**：无法表达两个玩家。

**触发条件**：第二个客户端接入。

**影响范围**：多人同步在本架构下不可实现（与 TX 缓冲问题并列）。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：把 per-client 状态移进 assoc。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c`
- `CODOL_SERVER_319_20261021/include/codol_battle_service.h`

**完成验收标准**：两个 peer 各自收到以自己为视角的快照。

**复杂度**：L　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0034 — stats 分块状态是全局而非 per-peer，且重连时不重置

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c:1100-1127）
- **证据等级**: E0-local-source

**问题现象**：svc->stats_total/stats_chunks/stats_buf 在 key-exchange 重置块里没有清零；两个 peer 会互相覆盖。

**预期行为**：每连接独立的 stats 组装。

**实际行为**：全局单份。

**触发条件**：重连或双客户端。

**影响范围**：极端情况下 statResponse 位掩码错误，客户端反复重传。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：单测：两次会话间 stats_chunks 应归零。

**推荐修复方向**：移进 assoc 并在连接重置时清零。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:680-703, 1100-1127`

**依赖**：`CODOL-ISSUE-0033`

**完成验收标准**：新会话 stats_chunks 从 0 开始。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0035 — 快照基线在发送成功前就前移，发送失败会导致基线错位

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c:541）
- **证据等级**: E0-local-source

**问题现象**：svc->snap_from = svc->snap_cur 在 send_frame 之前执行；send_frame 失败时客户端没收到这一帧，但服务端已把它当基线。

**预期行为**：基线只在发送成功后前移（或按 ack 前移）。

**实际行为**：失败即前移。

**触发条件**：发送失败（buffer 满、socket 错误）。

**影响范围**：后续帧全部按错误基线做增量。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：实机是否真的出现过发送失败。

**最小验证方法**：单测：注入 send 失败，检查基线。

**推荐修复方向**：把基线前移放到 send 成功之后。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:512-570`

**完成验收标准**：发送失败的帧不改变基线。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0036 — gamestate 只尝试 5 次，且不随 usercmd 重试

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c:610-613）
- **证据等级**: E0-local-source

**问题现象**：if (... gamestate_attempts < 5) 才发送；失败后 gamestate_due_ms += 2000 但 attempts 继续累加。

**预期行为**：客户端未进入 CA_LOADING 前应持续保障。

**实际行为**：5 次后永久放弃本会话。

**触发条件**：前 5 次 gamestate 未被客户端处理。

**影响范围**：会话静默失败且无日志告警（只有 TX_GAMESTATE 计数）。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：客户端在什么条件下才 ack gamestate。

**最小验证方法**：把上限改成无限并观察。

**推荐修复方向**：改为按状态（未收到 gamestateupdate）持续重试，并加告警日志。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:606-615`

**完成验收标准**：gamestate 未确认时会持续重发且日志可区分'已确认/超限'。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0037 — 两个 usercmd 处理分支重复且已出现分歧

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c:708-839 vs 923-1053）
- **证据等级**: E0-local-source

**问题现象**：handle_netchan_frame() 与 handle_plain() 的非 FAT 内联分支几乎相同；后者多了 CMD_FIELD_CHANGE 记录，keymap 表头一处是 \n 一处是字面反斜杠+n。

**预期行为**：单一实现。

**实际行为**：两份，已分歧。

**触发条件**：任何 usercmd 相关修改。

**影响范围**：修复需做两次，容易漏。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：合并为一个函数。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:800-820, 994-1024`

**完成验收标准**：只有一个 usercmd 解析实现。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0038 — 战斗服行为依赖进程 CWD 中的散落文件（无配置文件）

- **系统**: `build`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c）
- **证据等级**: E0-local-source

**问题现象**：firingrange-gamestate.bin、active_room.json、snapshot_entities.on、keymap_cal.csv 均按 "./" 相对路径读取/写入。

**预期行为**：显式配置。

**实际行为**：换工作目录即改变行为；run 之间靠复制 kit 传递。

**触发条件**：任何启动方式变化。

**影响范围**：与 HANDOFF §17.4 记录的'复制 kit 带上上一轮日志导致门控误判'是同一类问题。

**历史调查过程**：§17.4 记录过一次实际事故。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：在空目录启动，确认以何种方式失败。

**推荐修复方向**：加 --gamestate / --room / --flags 参数，并在启动时打印全部输入。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:175,178,391,805`
- `HANDOFF_20261025_BINARY_BISECT.md §17.4`

**完成验收标准**：战斗服启动时打印所有输入文件的绝对路径与来源。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0039 — 世界配置写死 dm 模式、30 分、10 分钟、3 秒复活

- **系统**: `battle-world`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：world.c:70-79）
- **证据等级**: E0-local-source

**问题现象**：mode_config.gametype 恒 "dm"；score_limit=30、time_limit_ms=600000、respawn_delay_ms=3000。

**预期行为**：按大厅下发的 gametype/playlist 配置。

**实际行为**：大厅的 g_gametype coop / playlist 选择完全不进入世界层。

**触发条件**：任何非 dm 模式。

**影响范围**：模式语义错误；胜负判定无意义。

**历史调查过程**：无记录。

**当前最可信判断**：确定

**尚缺证据**：官方 gametype 参数表。

**最小验证方法**：用 --gametype 参数覆盖并观察。

**推荐修复方向**：把模式配置从 mmstart/gamestate 传入。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/world_assets/world.c:70-79`
- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`

**完成验收标准**：服务端 gametype 与 mmstart 一致。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0040 — 多客户端/重连：per-connection 重置只在 key-exchange 分支发生

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-29（本次审计：battle_service.c:1100-1127）
- **证据等级**: E0-local-source

**问题现象**：gamestate_sent/snapshot_sent/snapshot_epoch/processed_input_time/FAT 只在此重置；会话超时后重建但未重新 key exchange 的情况未覆盖。

**预期行为**：每个新会话完全干净。

**实际行为**：部分状态会残留。

**触发条件**：重连但复用 assoc。

**影响范围**：可能出现'第二轮再进卡等待玩家数据'（该症状 2026-10-24 曾出现过并修复了一次）。

**历史调查过程**：2026-10-24 修过一次快照状态未重置。

**当前最可信判断**：确定（覆盖不全）

**尚缺证据**：是否有非 key-exchange 的重连路径。

**最小验证方法**：模拟会话超时后同地址重连，检查各字段。

**推荐修复方向**：把重置抽成 reset_session_state() 并在所有新建会话处调用。

**证据来源**：

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:1105-1127`

**依赖**：`CODOL-ISSUE-0034`

**完成验收标准**：任意新会话开始时全部相关字段为初值。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0041 — recv 缓冲 → 0x7765A0 读取器的边未闭合（最小未闭合边）

- **系统**: `client-re`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-14（CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md）
- **证据等级**: E1-static

**问题现象**：可证两端使用同一会话对象、同一长度/类型控制链；不能证 0x7765A0 读的字节就是 recv 的 payload。

**预期行为**：从 socket 到解析器的完整数据流。

**实际行为**：'对象构造'≠'payload 已复制'。

**触发条件**：任何'客户端会解析我们的包'的推断。

**影响范围**：所有上层协议结论都悬在这条边上。

**历史调查过程**：048→050 三个任务收敛到这一条边。

**当前最可信判断**：确定（未闭合）

**尚缺证据**：运行时 socket 数据指针与首个消费者的对应关系。

**最小验证方法**：在早期转储窗口内捕获 [esi+0xA8] 与 [esi+0xB0] 的指针关系。

**推荐修复方向**：用早期窗口内的高频转储对比缓冲区内容与 recv 目标。

**证据来源**：

- `CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md`
- `CODOL-BATTLE-SERVER-RECVBUFFER-TO-PARSER-041/`

**完成验收标准**：同一份字节可在 recv 目标与读取器输入两处被指认。

**复杂度**：L　**推荐处理顺序**：P0-6

---

### CODOL-ISSUE-0042 — .tp3 第 3 节区缺失约 229.6 MB，任何已恢复映像都不完整

- **系统**: `client-re`
- **状态**: `BLOCKED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-14（CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049/08_SECTION3_GAP_ANALYSIS.md）
- **证据等级**: E1-static

**问题现象**：声明 VSize 0x0DBB1CC0，仅 0x4F000 实际存在；工作区内没有任何文件长度超过 10,899,456。

**预期行为**：完整运行时映像。

**实际行为**：第 3 节区无数据；缺的是文件数据（壳压缩+恢复过程未展开），不是工具问题。

**触发条件**：任何静态定位落在该节区的目标。

**影响范围**：多个'找不到'结论其实是'这一节没有'。

**历史调查过程**：2026-10-14 裁定；此前误认为工具无法解码。

**当前最可信判断**：确定

**尚缺证据**：解壳流程；或一次成功的大尺寸运行时转储。

**最小验证方法**：ACE 早期窗口内转储 EXE 全映像（此前 snap_003 在 6 秒内向 DLL 读到 1630 MB）。

**推荐修复方向**：优先用运行时转储补该节区，而不是静态解壳。

**证据来源**：

- `CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049/08_SECTION3_GAP_ANALYSIS.md`

**依赖**：`CODOL-ISSUE-0045`

**完成验收标准**：该节区有可核对的运行时字节。

**复杂度**：L　**推荐处理顺序**：P1-10

---

### CODOL-ISSUE-0043 — 主 DLL 的 .tvm0(31.4MB) / .tls(15.5MB) 未解码

- **系统**: `client-re`
- **状态**: `BLOCKED`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（CODOL-BATTLE-SERVER-DLL-NETBIND-040/STATIC_ANALYSIS_BLOCKERS.md）
- **证据等级**: E1-static

**问题现象**：.tvm0 31.4 MB 未解码、3 个导出全在其中；.tls 熵 7.532、非正常 x86。

**预期行为**：能读出其中的代码/数据。

**实际行为**：未解码。

**触发条件**：任何指向该 DLL 内部的结论。

**影响范围**：'找不到'类结论必须附带'该区未解'的限定。

**历史调查过程**：注意：E06 解出的是 2.6.9.7 恢复映像的 .tvm0（aPLib 压缩块），与本 build 主 DLL 的 31.4 MB .tvm0 不是同一件东西，不可合并。

**当前最可信判断**：确定（未解码）

**尚缺证据**：该 build 的 .tvm0 结构。

**最小验证方法**：对主 DLL .tvm0 做熵/aPLib 签名探测。

**推荐修复方向**：先判定是否为 aPLib；若是，复用 E06 的工具。

**证据来源**：

- `CODOL-BATTLE-SERVER-DLL-NETBIND-040/STATIC_ANALYSIS_BLOCKERS.md`
- `E06_TVM0_STATIC_DECODE_001/08_E06_VERDICT.md`

**完成验收标准**：该节区可读出可识别的代码或数据布局。

**复杂度**：L　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0044 — 五项客户端消费语义（opcode/gamestate/configstring/snapshot/reliable）解决率 0%

- **系统**: `client-re`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-13（CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/07_A_BLOCKERS_STATUS.md）
- **证据等级**: E1-static

**问题现象**：对下列五项关键客户端消费语义，本轮解决率仍为 0%；只定位到诊断字符串引用（gamestateupdate %d @0x54B7B/0x73214；EXE_CONFIGSTRINGMISMATCH @0x731E1/0xF2833）。

**预期行为**：能指出每类消息在客户端被读、被分发、被存的位置。

**实际行为**：只有字符串存在与该字符串被引用，没有任何读取/分发/存储路径。

**触发条件**：任何'客户端会正确处理 X'的结论。

**影响范围**：服务端发送的一切都缺消费端证据。

**历史调查过程**：043→046 四次推进均未改变 0%。

**当前最可信判断**：确定

**尚缺证据**：运行时消费路径。

**最小验证方法**：（同 0041）早期窗口转储 + 指针关系。

**推荐修复方向**：与其继续静态找，不如做'畸形消息对照'证明客户端确实在读。

**证据来源**：

- `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/07_A_BLOCKERS_STATUS.md`

**依赖**：`CODOL-ISSUE-0041`

**完成验收标准**：至少一项有'读取位置 + 行为可观测'的双重证据。

**复杂度**：XL　**推荐处理顺序**：P1-11

---

### CODOL-ISSUE-0045 — ACE 内核驱动封死活进程内存读取与调试附加

- **系统**: `tooling`
- **状态**: `BLOCKED`  **优先级**: `P1`  **严重度**: critical
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-28（docs/ACE_BLOCKS_EVERYTHING_20261028.md）
- **证据等级**: E0-runtime-verified

**问题现象**：句柄抢到后 0.01 秒的第一次读取即 err=5；PE 头、vtable、代码段全部失败；ALL_ACCESS 也一样。ACE-BASE.sys / ACE-GAME.sys 是内核驱动。

**预期行为**：能读活进程内存或下断点。

**实际行为**：t+0.01s 起全程不可读；硬件断点依赖调试附加，被拒。

**触发条件**：任何运行时探针。

**影响范围**：房间按钮、路由键写入等动态问题的取证路径被关闭。

**历史调查过程**：与既有记忆'早期句柄(t+15.39s)可读'矛盾：本轮 t+0.01s 就失败，原因未定。但 10-27 的 dump_earliest 确实读到 1630 MB。

**当前最可信判断**：矛盾未解：两次实测结果不同

**尚缺证据**：早期窗口为何有时可用。

**最小验证方法**：连续多轮用 dump_early 记录'首个失败时刻'，找出窗口规律。

**推荐修复方向**：优先利用有窗口的那条路径（dump_earliest 抢句柄 + 立即全量转储）。

**证据来源**：

- `docs/ACE_BLOCKS_EVERYTHING_20261028.md`
- `docs/PROBE_BLOCKED_BY_ACE_20261028.md`
- `docs/PROBE_FAILED_VA_DRIFT_20261028.md`

**完成验收标准**：能稳定地按需取得一次完整转储，或明确记载窗口不可预测。

**复杂度**：M　**推荐处理顺序**：P1-12

---

### CODOL-ISSUE-0046 — AS_* Scaleform 类有名字但无 COL、零引用，ui_mp.ff 加密 ⇒ UI 逻辑不可达

- **系统**: `client-re`
- **状态**: `BLOCKED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/AS_CLASSES_INVENTORY_20261028.md / docs/UI_FF_ENCRYPTED_20261028.md）
- **证据等级**: E1-static

**问题现象**：163 个 AS_* RTTI 类名可在 EXE 中枚举；对每个类做 TD→COL 追溯，引用 0 处；ui_mp.ff 29,224,001 B 熵 7.95~8.00，明文搜索 Room/ready 全 0；SWF/GFX 签名 12 处全部 filelen 不合理。

**预期行为**：能确认按钮的回调绑定。

**实际行为**：静态层到头；Flash 资源不可达。

**触发条件**：任何'按钮为什么点不动'的调查。

**影响范围**：UI 侧根因无法独立确认。

**历史调查过程**：10-28 三轮：AS_* 无实现 → MyEventHandler 零实例 → UI 在 .gfx。

**当前最可信判断**：确定（不可达）

**尚缺证据**：.gfx 解析工具；.ff 解密。

**最小验证方法**：—

**推荐修复方向**：不做；改为从数据面（房间状态）绕过按钮。

**证据来源**：

- `docs/AS_CLASSES_INVENTORY_20261028.md`
- `docs/UI_FF_ENCRYPTED_20261028.md`
- `docs/READY_BUTTON_NO_IMPL_20261028.md`
- `run_codol_001/runs/RE_FULL_20261029/rtti_full.md`

**依赖**：`CODOL-ISSUE-0009`

**完成验收标准**：—

**复杂度**：XL　**推荐处理顺序**：不单独处理

---

### CODOL-ISSUE-0047 — 两套协议族并存：客户端 Demonware(0x81–0x85, 8-bit) vs 服务端 iD-Tech(3-bit 0..4)

- **系统**: `protocol`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-12（E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/E26_PROTOCOL_CONFLICTS_AND_BLOCKERS.md）
- **证据等级**: E1-static

**问题现象**：客户端 cmp al,0x81/0x83/0x84/0x85（8 位）；服务端 _MSG_ReadBits(msg,3) + cmp edi,4。2697 服务包 12511 文件/4 个 PE 中无 Demonware 对端。

**预期行为**：同一份线上的握手。

**实际行为**：两条不同协议族。

**触发条件**：跨协议复用。

**影响范围**：不能把任何一方的握手实现直接移植到另一方。

**历史调查过程**：E26 记录冲突；E27 把'不存在'收窄为'不在 codol_dedrun.exe 里'。

**当前最可信判断**：冲突确定；互操作未验证

**尚缺证据**：客户端 Demonware 握手的完整线上样本。

**最小验证方法**：在 3074 抓一次客户端 ↔ 我们大厅的握手，与 8-bit 假设对拍。

**推荐修复方向**：明确区分：大厅用 Demonware，战斗用 iD-Tech；不要混用常量。

**证据来源**：

- `E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/E26_PROTOCOL_CONFLICTS_AND_BLOCKERS.md`
- `E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/E27_EXECUTIVE_SUMMARY.md`

**完成验收标准**：两份协议各自有独立、可对拍的规格文档。

**复杂度**：M　**推荐处理顺序**：P1-13

---

### CODOL-ISSUE-0048 — VA/RVA 混用导致多份报告产出假结论

- **系统**: `evidence-quality`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/08_NEXT_ACTION_DECISION.md (045-C1)）
- **证据等级**: E1-static

**问题现象**：040/041/043/044 均称 '读 API IAT 槽 0x0CA84E8 落在镜像未覆盖节区'；045 实测该值是绝对 VA，RVA=0x8A84E8 < 0xA65000，文件内。另 E22 的 BSS 判定被 E23 以同类错误推翻。

**预期行为**：所有地址结论标注 VA/RVA 与换算。

**实际行为**：至少四处独立混用（E06 M-01、E08 M-01、E22→E23、040–044→045）。

**触发条件**：任何绝对地址引用。

**影响范围**：依赖这些结论的后续工作全部需要复核。

**历史调查过程**：各自已在原报告内更正；但更正经告未回灌到早期文档。

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：对每个现存地址结论做一次自动 VA/RVA 双读校验。

**推荐修复方向**：在工具层强制：地址必须以 (module, rva) 二元组表达。

**证据来源**：

- `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/08_NEXT_ACTION_DECISION.md`
- `E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001/E23_EXECUTIVE_SUMMARY.md`

**完成验收标准**：全部存量地址结论通过双读校验或标注为 UNKNOWN。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0049 — 房间消息格式在 10-28 一天内反转四次

- **系统**: `evidence-quality`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-28（docs/ROOM_MSG_NOT_BITSTREAM_20261028.md → ROOM_DIRECTION_SPLIT → TYPE02_IS_TEXT）
- **证据等级**: E0-meta

**问题现象**：位流（离线 5/5 通过）→ 穷举位偏移零命中 → 断定非位流 → 上下行不同 → type02 是 Text 而非分发 → 下行改回位流。

**预期行为**：每次反转后旧文档被标注。

**实际行为**：旧文档仍以肯定语气存在于 docs/ 中，未加作废标注。

**触发条件**：新人或新 agent 阅读 docs/。

**影响范围**：会按已作废的结论重做工作。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：给 docs/ 增加 superseded-by 头，并在 00_INDEX 里标注每篇的状态。

**证据来源**：

- `docs/ROOM_MSG_NOT_BITSTREAM_20261028.md`
- `docs/ROOM_DIRECTION_SPLIT_20261028.md`
- `docs/TYPE02_IS_TEXT_20261028.md`
- `docs/ROOM_UI_BITSTREAM_FIX_20261028.md`

**完成验收标准**：每篇被推翻的文档首行有 SUPERSEDED 标注。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0050 — '22/22 全绿'、'域标 DONE' 与'实机未验'长期混用同一套措辞

- **系统**: `evidence-quality`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（CODOL_SERVER_319_20261021/docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md）
- **证据等级**: E0-meta + E0-runtime

**问题现象**：该矩阵把'启动链与认证'、'战斗传输握手'、'Gamestate/configstring'、'Usercmd/可靠命令'标为 DONE，同时自述'完整实机验证 TODO'。但 10-28 起战斗服所有 BOT 房间轮次零收包，'传输握手 DONE'与实况冲突。

**预期行为**：DONE 应有官方客户端实机验收。

**实际行为**：DONE 的判据是离线/静态。

**触发条件**：任何引用该矩阵的进度判断。

**影响范围**：项目自评偏高。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：把 DONE 拆成 DONE-OFFLINE / DONE-SIM-CLIENT / DONE-LIVE 三级。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`
- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`

**完成验收标准**：全部状态表使用四级判据。

**复杂度**：S　**推荐处理顺序**：P1-14

---

### CODOL-ISSUE-0052 — 多项'已解决'结论只有离线或自测证据

- **系统**: `evidence-quality`
- **状态**: `UNVERIFIED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（多处；汇总见 02_ALL_HISTORICAL_ISSUES.md 的对照表）
- **证据等级**: E0-meta

**问题现象**：例：035 模块 84/84 离线通过但只覆盖已确认子集；FAT 分片离线 7 项全绿但实机从未触发（阻断点自行消失）；实体段'接受'被当作'可见'；'251/251 服务器自测'被当作'客户端兼容'。

**预期行为**：每项区分 offline / simulated / live。

**实际行为**：措辞不等。

**触发条件**：读历史报告。

**影响范围**：重复调查已'解决'的问题，或高估完成度。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：在 02_ALL_HISTORICAL_ISSUES.md 里逐条给出证据等级。

**证据来源**：

- `CODOL-BATTLE-OOB-STATE-035/UNKNOWN_AND_BLOCKERS.md §1`
- `HANDOFF_20261025_BINARY_BISECT.md §8.2, §17`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005/FREEZE-005_REPORT.md §8`

**完成验收标准**：每项历史结论有 evidence_level 字段。

**复杂度**：M　**推荐处理顺序**：P1-15

---

### CODOL-ISSUE-0053 — ol-mod EngineBindings 宿主映像门禁永不通过（SizeOfImage 不匹配）

- **系统**: `combat`
- **状态**: `BLOCKED`  **优先级**: `P3`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-14（COMBAT_SERVER_BLOCKERS.md §0（hist_combat #1））
- **证据等级**: E0-runtime-verified

**问题现象**：EngineBindings::bind() 要求 SizeOfImage==0x0E5D6000 且 TimeDateStamp==0x6096930A；实测客户端为 0x0E659000。三次实机运行只打印 'engine binding failed'，无阶段日志。

**预期行为**：ol-mod 插件线能挂上宿主。

**实际行为**：门禁在第一项就失败；且与 Signature 同处一个短路 || 的 if，不记录是哪一项。

**触发条件**：加载 ol-mod 插件。

**影响范围**：ol-mod 路线整体不可用；但不影响我们自研战斗服。

**历史调查过程**：已知且未变；按 AGENTS.md ol-mod 本就不是权威参照。

**当前最可信判断**：确定

**尚缺证据**：未收集 E-2（运行时 PE 头）与 E-3（0x0FEA20 / 0x8371A 运行期字节）。

**最小验证方法**：读运行时 PE 头确认 SizeOfImage，已知会失败；因此该线价值低。

**推荐修复方向**：不修 ol-mod；只把它当同类参考。

**证据来源**：

- `COMBAT_SERVER_BLOCKERS.md`
- `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md`
- `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md (G-08)`

**完成验收标准**：—

**复杂度**：L　**推荐处理顺序**：不处理（P3）

---

### CODOL-ISSUE-0054 — mmbook accepted 必须回显客户端自己的 (A,B)，预留槽填充者未定位

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-16（COMBAT_V0_1_NEXT_001_BLOCKER.md §2.5（hist_combat #14））
- **证据等级**: E1-static + E0-runtime

**问题现象**：八个连续的 COMBAT_V0_1_NEXT_00x 实现门禁都收敛到同一个点：[+0x168]/[+0x16C] 由谁填、填什么，始终未定位。

**预期行为**：服务端回显客户端期望的 (A,B)。

**实际行为**：未定位。

**触发条件**：6/14 mmbook。

**影响范围**：预约放行信号可能只是'看起来发出去了'。

**历史调查过程**：10-16..10-22 连续八轮未闭合。

**当前最可信判断**：未闭合

**尚缺证据**：[+0x168]/[+0x16C] 的写入点。

**最小验证方法**：在早期转储里对比 mmbook 前后该对象字段。

**推荐修复方向**：先定位写入点。

**证据来源**：

- `COMBAT_V0_1_NEXT_001_BLOCKER.md`
- `COMBAT_V0_1_NEXT_008_IMPLEMENTATION_GATE.md`

**依赖**：`CODOL-ISSUE-0020`

**完成验收标准**：能证明回显值与客户端写入值一致。

**复杂度**：M　**推荐处理顺序**：P1-16

---

### CODOL-ISSUE-0055 — 进图后客户端从不发送开火位（bit0 缺失）

- **系统**: `combat`
- **状态**: `OPEN`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-22（CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md §1.3（hist_combat #34））
- **证据等级**: E0-runtime-verified

**问题现象**：所有抓到的 usercmd 里都没有 bit0（开火）。

**预期行为**：开火时 buttons 应带开火位。

**实际行为**：从未出现。

**触发条件**：游戏内按开火。

**影响范围**：FIRE/HIT/DAMAGE 计数恒为 0，与伤害实现无关。

**历史调查过程**：与 CODOL-ISSUE-0068（bit29）、CODOL-ISSUE-0067（跳跃位冲突）同属按键位定义未闭合。

**当前最可信判断**：确定（缺失）

**尚缺证据**：开火在线上到底走 usercmd 还是可靠命令。

**最小验证方法**：一次实机里只按开火，看是否有任何可识别上行。

**推荐修复方向**：先确认开火的传输通道，再谈按钮位。

**证据来源**：

- `CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md`
- `run_codol_001/runs/*/kit/keymap_cal.csv`

**完成验收标准**：开火动作在服务端产生可识别的输入事件。

**复杂度**：M　**推荐处理顺序**：P1-17

---

### CODOL-ISSUE-0056 — idx20 (pm_flags) 写 aiming?0x10，而 0x10 可能是 PMF_SPRINTING 并挡掉开镜

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-24（docs/SNAPSHOT_FIELD_DIFF_20261024.md §12.3（hist_combat #36））
- **证据等级**: E0-runtime-observed + 假设

**问题现象**：SNAPSHOT_RAWFIX_20261024_1357 里用户报开镜失效，与 idx20 改动同期出现。

**预期行为**：开镜能启用的 pm_flags 值。

**实际行为**：0x10 在 CoD 里是 PMF_SPRINTING。

**触发条件**：持续开镜。

**影响范围**：开镜功能缺失；与 idx61 回退是两件独立事故。

**历史调查过程**：10-24 记录为未归因。

**当前最可信判断**：假设，未验证

**尚缺证据**：3.19 的 pm_flags 位定义表。

**最小验证方法**：把 idx20 固定为 0 跑一轮，看开镜是否恢复。

**推荐修复方向**：先做上面的单变量回退。

**证据来源**：

- `docs/SNAPSHOT_FIELD_DIFF_20261024.md`
- `CODOL_SERVER_319_20261021/src/battle/snapshot.c`

**完成验收标准**：开镜可用，且 idx20 语义有本 build 证据。

**复杂度**：S　**推荐处理顺序**：可并行

---

### CODOL-ISSUE-0057 — 动态武器索引无静态全表，且 firstDynamicWeapon 每图不同（1224 vs 1147）

- **系统**: `combat`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-25（_weapon_table_20261025/codol_dynamic_index_model.md（hist_combat #63/#64））
- **证据等级**: E0-runtime-verified

**问题现象**：客户端在 CL_ParseGamestate 第二遍分配武器索引；不同地图起点不同。

**预期行为**：服务端能算出与客户端一致的武器号。

**实际行为**：无静态表；公式不通用。

**触发条件**：换图/换配装。

**影响范围**：武器号在上线时可能错位（当前实机里武器号 1156 一直存在，说明本图对的）。

**历史调查过程**：—

**当前最可信判断**：确定（无全表）

**尚缺证据**：第一遍/第二遍分配规则的完整定义。

**最小验证方法**：换一张图，对比 firstDynamicWeapon。

**推荐修复方向**：按 gamestate 的武器表现场构造映射。

**证据来源**：

- `_weapon_table_20261025/codol_dynamic_index_model.md`

**完成验收标准**：任意地图上服务端武器号与客户端一致。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0058 — 小地图为空：northyaw 缺失、compass_map_* 需地图边界

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-22（HANDOFF_20261022_PAUSE.md §1.5（hist_combat #65））
- **证据等级**: E0-runtime-observed

**问题现象**：configstring 里缺 northyaw；compass_map_* 需要地图边界。

**预期行为**：小地图正常显示。

**实际行为**：空白。

**触发条件**：进图。

**影响范围**：HUD 不完整，但不阻断可玩性验证。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：configstring 编号与格式。

**最小验证方法**：补 northyaw 后观察。

**推荐修复方向**：从地图 zone 取边界与朝向。

**证据来源**：

- `CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md`

**完成验收标准**：小地图有内容。

**复杂度**：M　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0059 — usercmd.weapon 恒为 0，无选枪通道

- **系统**: `movement`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-22（HANDOFF_20261022_PAUSE.md §1.3/§3.2（hist_combat #70））
- **证据等级**: E0-runtime-verified

**问题现象**：usercmd 的 weapon 字段恒 0；换枪走可靠命令（mr …）。

**预期行为**：换枪能被服务端看到。

**实际行为**：只有可靠命令路径；且可靠命令只解析背包选择。

**触发条件**：游戏内换枪。

**影响范围**：切枪不能驱动服务端状态。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：换枪的完整命令行格式。

**最小验证方法**：换枪后检查可靠命令内容。

**推荐修复方向**：扩展可靠命令解析。

**证据来源**：

- `CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md`
- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:958-971`

**完成验收标准**：换枪后服务端 selected_slot 改变。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0060 — 跳跃键位定义冲突（0x400 vs 0x2）与 bit29 未解释

- **系统**: `movement`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-17（PROGRESS_20261017.md §二.3 vs §11.6（hist_combat #67/#68））
- **证据等级**: E0-runtime + 文档冲突

**问题现象**：同一文档不同段落给出 0x400 与 0x2 两种跳跃位；实测 0x400 固定。另有 bit29 语义未知。

**预期行为**：统一的 buttons 位表。

**实际行为**：冲突未裁决。

**触发条件**：任何按键映射。

**影响范围**：跳跃/开火等动作可能映射错。

**历史调查过程**：—

**当前最可信判断**：冲突确定

**尚缺证据**：逐位验证的按键标定实验。

**最小验证方法**：用 keymap_cal.csv 逐键录制，产出位表。

**推荐修复方向**：以实测为准，出一份位表并写进头文件。

**证据来源**：

- `PROGRESS_20261017.md`
- `CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md`
- `CODOL_SERVER_319_20261021/src/movement/movement.c:79`

**依赖**：`CODOL-ISSUE-0055`

**完成验收标准**：每个动作对应一个被实测确认的位。

**复杂度**：M　**推荐处理顺序**：P1-18

---

### CODOL-ISSUE-0061 — netField 语义仍有大量空白（36 个 playerState 字段、7 个 entityState 字段未命名）

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（docs/PHASE4_FIELD_SEMANTICS_DONE_20261023.md §6（hist_combat #52/#53））
- **证据等级**: E1-static

**问题现象**：playerState 36 个字段未命名；entityState 7 个；18 种数组元素布局 × 64 字段从未语义命名。

**预期行为**：字段名与消费点。

**实际行为**：只有编号与宽度。

**触发条件**：任何超出当前已用字段的编码。

**影响范围**：无法安全使用未命名字段。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：消费端证据。

**最小验证方法**：逐字段 A/B（改一字段看客户端反应）。

**推荐修复方向**：按'一字段一次实机'推进，避免批量改。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/PHASE4_FIELD_SEMANTICS_DONE_20261023.md`
- `CODOL_SERVER_319_20261021/docs/INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md`

**完成验收标准**：当前使用的字段全部命名且有实测依据。

**复杂度**：L　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0062 — entityState 字段数在 24 与 63 之间存在矛盾（记忆称 63）

- **系统**: `battle-snapshot`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（docs/PHASE4_FIELD_SEMANTICS_DONE_20261023.md §2（hist_combat #51））
- **证据等级**: E1-static

**问题现象**：阶段文档写 24 netField 项；反汇编 0x671170 读出 6 位 lastChangedField（≤63）且 numFields 恒 63。

**预期行为**：唯一数字。

**实际行为**：两处不一致；以反汇编为准（63）。

**触发条件**：任何 len 计算。

**影响范围**：若按 24 写会截断字段。

**历史调查过程**：记忆条目已指出 63 是正解。

**当前最可信判断**：以 63 为准

**尚缺证据**：—

**最小验证方法**：重读 0x671170 的 numFields 表。

**推荐修复方向**：在 Phase4 文档加更正。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/PHASE4_FIELD_SEMANTICS_DONE_20261023.md`
- `docs/entity delta reader 0x671170（记忆 codol-entity-delta-reader-671170）`

**完成验收标准**：文档与本 build 反汇编一致。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0063 — 快照字段 62/83/107/162 与 idx219 只有我们写，参照无对应

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-24（docs/SNAPSHOT_FIELD_DIFF_20261024.md §7（hist_combat #41））
- **证据等级**: E0-runtime-verified（能用）+ 无出处

**问题现象**：这五个字段在参照实现里都不存在（参照还说 idx219 在真实序列里不存在、playerState 表只有 87 项）。

**预期行为**：有依据的字段集。

**实际行为**：但当前这套是唯一能让客户端进图的写法。

**触发条件**：任何'清理无关字段'的念头。

**影响范围**：删除可能导致回退（§15 的教训）。

**历史调查过程**：10-25 已明确'以实测为准'。

**当前最可信判断**：确定（能用但无出处）

**尚缺证据**：本 build 客户端读这些索引的代码。

**最小验证方法**：一次只删一个，跑一轮；失败即回退。

**推荐修复方向**：逐字段做出现/删除 A/B。

**证据来源**：

- `docs/SNAPSHOT_FIELD_DIFF_20261024.md`
- `CODOL_SERVER_319_20261021/src/battle/snapshot.c:440-456`

**完成验收标准**：每个保留字段有'删除会失败'的反证。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0064 — gamestate 尾部 44 字节未解析，configstring index_bits 未知

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（docs/PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023.md §6（hist_combat #60/#61））
- **证据等级**: E1-static + E0-runtime-roundtrip

**问题现象**：gamestate 有 44 字节尾未解析；configstring 的 incremental index 编码未知。

**预期行为**：完整 gamestate 结构。

**实际行为**：只做到字节往返一致。

**触发条件**：改 gamestate 内容时。

**影响范围**：动态房间适配（_gs_adapt_dynamic）只改首部，尾部语义不明。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：客户端读取路径。

**最小验证方法**：逐字节改尾部，观察客户端反应。

**推荐修复方向**：先解尾再改。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023.md`
- `CODOL_SERVER_319_20261021/src/battle/battle_service.c:302-372`

**完成验收标准**：尾部字段有名且有实测。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0065 — FAT 分片实机从未触发；RELIABLE 分片 ack 无实机证据

- **系统**: `battle-network`
- **状态**: `UNVERIFIED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-24（HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md（hist_combat #57/#58））
- **证据等级**: impl-only

**问题现象**：FAT 重组离线 7 项全绿，但修好索引编码后客户端消息稳定在 174~371 字节，永远达不到 1154 阈值。RELIABLE 片段 ack(0xA0000000) 只有文档。

**预期行为**：分片路径有实机证据。

**实际行为**：从未触发。

**触发条件**：长可靠命令。

**影响范围**：分片代码是'离线已验证、实机未验'。

**历史调查过程**：10-25 §8.2 明确记录阻断点自行消失。

**当前最可信判断**：确定（未触发）

**尚缺证据**：能让消息超长的场景。

**最小验证方法**：构造一条超长可靠命令（如大配装串）触发分片。

**推荐修复方向**：保留代码；不投入直到有触发场景。

**证据来源**：

- `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md`
- `HANDOFF_20261025_BINARY_BISECT.md §8.2`
- `CODOL_SERVER_319_20261021/src/netchan/netchan.c`

**完成验收标准**：实机日志出现 RX_FAT_REASSEMBLED 且后续 usercmd 正常。

**复杂度**：M　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0066 — 武器定义运行时布局未验证，WeaponAttach 545 条字符串记录不可消费

- **系统**: `combat`
- **状态**: `UNVERIFIED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（docs/PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md（hist_combat #81/#82/#83））
- **证据等级**: E1-static + 冲突

**问题现象**：旧候选 +0xBB4/+0xBCC/+0xBF0 已被 zone 对拍否定；+0x810..+0x824/+0xAC0 未验证。WeaponAttach 545 条 string/resource 记录被跳过，168 个资产共享槽无法解析。且标量覆盖率有两套数字（172/879 vs 94 记录/44 资产）。

**预期行为**：最终布局与全量附件解析。

**实际行为**：标量可用，字符串/资源不可用。

**触发条件**：使用非基础配件。

**影响范围**：配件效果不完整。

**历史调查过程**：—

**当前最可信判断**：布局未验证

**尚缺证据**：运行时 WeaponDef 布局证据。

**最小验证方法**：用 probe 读一份真实 WeaponDef。

**推荐修复方向**：先定布局，再谈附件。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md`
- `CODOL_SERVER_319_20261021/src/battle/weaponattach.c`

**完成验收标准**：WeaponDef 关键字段有 3.19 实测值。

**复杂度**：L　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0067 — 命中盒/护甲/穿透几何缺失；recoil/spread/ADS 公式缺失

- **系统**: `combat`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-23（docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md（hist_combat #84–#87））
- **证据等级**: impl-partial

**问题现象**：20 槽 hitloc 有名字但无几何；无原生护甲表；无 FMJ 材质穿透；无 recoil/view kick/ADS 精度公式。

**预期行为**：与原版一致的射击手感。

**实际行为**：通用 AABB + 固定部位。

**触发条件**：任何射击。

**影响范围**：伤害数值与原版不一致（但基础闭环可用）。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：原生骨骼/命中盒几何、护甲表、G_Damage 分支。

**最小验证方法**：—

**推荐修复方向**：按 INMATCH 门槛 3 逐项补齐。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`
- `CODOL_SERVER_319_20261021/src/world/combat.c`

**依赖**：`CODOL-ISSUE-0030`

**完成验收标准**：至少一把枪完成真实命中：trace + 距离伤害 + 部位倍率 + 护甲/穿透。

**复杂度**：L　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0069 — C# v0.1 战斗服：无碰撞、无 hitscan、无伤害、无死亡复活

- **系统**: `combat`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-14（CODOL-BATTLE-SERVER-GAMEPLAY-003/00_INDEX.md §6（hist_combat #72））
- **证据等级**: impl-only

**问题现象**：C# 路线的所有轮次都由服务端自证（V0_1_ACCEPTANCE_MATRIX AC-4/AC-7：实机从未连接）。

**预期行为**：—

**实际行为**：功能缺口大且未与真实客户端联调。

**触发条件**：—

**影响范围**：C# 线不再作为主线（C 线已取代）。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：不作为主线维护。

**证据来源**：

- `CODOL-BATTLE-SERVER-GAMEPLAY-003/00_INDEX.md`
- `V0_1_ACCEPTANCE_MATRIX.md`

**完成验收标准**：—

**复杂度**：XL　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0070 — C# 线遗留：加 pm_type/eFlags/otherFlags/字段54/83/217 全都会让快照崩

- **系统**: `battle-snapshot`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-17（PROGRESS_20261017.md §三/§13.5（hist_combat #78/#79/#80））
- **证据等级**: E0-runtime-verified（阴性）

**问题现象**：逐项加字段的实验全部导致客户端失败；另有 'noclip' 现象（客户端把 pm_flags 清零、vel=(0,0,0)，origin 跟随服务端）。hint==2 的第二遍字段写入从未实现。

**预期行为**：—

**实际行为**：阴性结果未整理成规则。

**触发条件**：扩展快照字段。

**影响范围**：有用：这些是'不要做'的清单。

**历史调查过程**：—

**当前最可信判断**：确定（阴性结果）

**尚缺证据**：noclip 现象的机制。

**最小验证方法**：—

**推荐修复方向**：整理成'快照字段禁区'清单。

**证据来源**：

- `PROGRESS_20261017.md`

**完成验收标准**：禁区清单进入文档并有出处。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0071 — 客户端停在 '100' 弹窗、rc=-1，从未进大厅（任务 031 线）

- **系统**: `startup`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION/UNKNOWN_AND_BLOCKERS.md（hist_e #47））
- **证据等级**: E0-runtime

**问题现象**：BLK-031-01：客户端停在 '100' 弹窗、rc=-1。

**预期行为**：进入大厅。

**实际行为**：未进入。

**触发条件**：该线使用的启动链（有 6 处与已知良好链的偏差，含缺 8444 portproxy）。

**影响范围**：该线整体阻塞；但当前主线的启动链已能进大厅，说明这一条对主线不适用。

**历史调查过程**：10-13；10-19 之后的链已能进大厅，故该线的失败条件可能已不存在。

**当前最可信判断**：对该线确定；对主线是否仍有意义 UNKNOWN

**尚缺证据**：该线的 6 处偏差是否仍存在。

**最小验证方法**：用当前链复现 031 的启动方式。

**推荐修复方向**：先判定该线是否已被主线取代。

**证据来源**：

- `CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION/UNKNOWN_AND_BLOCKERS.md`

**完成验收标准**：该线或已作废，或能进大厅。

**复杂度**：M　**推荐处理顺序**：待裁定

---

### CODOL-ISSUE-0072 — hosts 文件原始 937B 不可恢复（现 915B）

- **系统**: `startup`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION/UNKNOWN_AND_BLOCKERS.md §6（hist_e #49））
- **证据等级**: E0-runtime

**问题现象**：原 937 字节的 hosts 被覆盖为 915 字节，原始内容无备份。

**预期行为**：配置变更可回滚。

**实际行为**：不可逆。

**触发条件**：—

**影响范围**：若将来需要原始 hosts，无法恢复。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：原始内容。

**最小验证方法**：—

**推荐修复方向**：记录当前状态并在未来变更前备份。

**证据来源**：

- `CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION/UNKNOWN_AND_BLOCKERS.md`

**完成验收标准**：hosts 有版本化备份。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0073 — service 4/13 才是房间服务，旧映射 service==11 会 UNMAPPED

- **系统**: `lobby`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-24（SERVICE71_CLIENT_REVERSE_20261024.md §14.5（hist_combat #19））
- **证据等级**: E0-runtime

**问题现象**：旧代码把房间服务映射到 11；实测房间服务是 4/13。

**预期行为**：正确映射。

**实际行为**：已在当前 lobby 中修正（日志显示 4/13 有专门分支）。

**触发条件**：—

**影响范围**：若回退到旧 kit 会重现。

**历史调查过程**：已修正。

**当前最可信判断**：已解决但文档未清理

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：在旧文档加更正。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/SERVICE71_CLIENT_REVERSE_20261024.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`

**完成验收标准**：文档与代码一致。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0074 — 102/7 playerdata 批量读回全 0 会清空玩家选图/选模式

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/BATTLE_CONNECT_DIVERGENCE_20261028.md §3（hist_combat #20））
- **证据等级**: E0-runtime-correlation

**问题现象**：字段表索引 [44..49] = PVEDifficulty/PVEMap/PVEMode/PVPMatch/PVPMode/RootIndex。曾回 50 个字段全 0，等于告诉客户端'你什么都没选'。

**预期行为**：回显客户端真实选择。

**实际行为**：当前最新一轮已改为'保持不处理（对齐 10-26 成功轮）'，但未验证是否能恢复连接。

**触发条件**：大厅初始化 102/7。

**影响范围**：与 CODOL-ISSUE-0020 同为战斗服零收包的候选根因。

**历史调查过程**：10-27 两轮回显均失败（客户端每 5 秒重发）；10-28 起改回不处理。

**当前最可信判断**：候选根因，未二分

**尚缺证据**：单变量二分结果。

**最小验证方法**：BATTLE_CONNECT_DIVERGENCE §五 的三步回归。

**推荐修复方向**：先做单变量回归，再逐个放开。

**证据来源**：

- `docs/BATTLE_CONNECT_DIVERGENCE_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`
- `docs/PVE_STUCK_INVESTIGATION_20261027.md §3`

**依赖**：`CODOL-ISSUE-0020`

**完成验收标准**：战斗服收到连接，且 102/7 行为与地图选择一致。

**复杂度**：S　**推荐处理顺序**：P0-1

---

### CODOL-ISSUE-0075 — 2697 包与 3.19 的记录层从未被观测：COOKIE_ECHO 189 vs 219、AES192/Tiger192 vs AES128/SHA1

- **系统**: `protocol`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-12（CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md (G-01)（hist_e #64））
- **证据等级**: E1-static

**问题现象**：两套加密/记录层参数并存，从未在 3.19 上观测到 2697 记录层。

**预期行为**：唯一的加密参数集。

**实际行为**：两套并存。

**触发条件**：跨版本复用。

**影响范围**：不能把 2697 的记录层当 3.19 的。

**历史调查过程**：—

**当前最可信判断**：冲突确定

**尚缺证据**：3.19 的加密参数实测。

**最小验证方法**：—

**推荐修复方向**：以 3.19 本地逆向为准（AGENTS.md 权威顺序）。

**证据来源**：

- `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md`

**完成验收标准**：加密参数全部来自 3.19 本地证据。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0076 — Fragment stride 1154 vs 1162 未裁决

- **系统**: `battle-network`
- **状态**: `UNKNOWN`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-13（CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/07_SERVER_READINESS_ISSUE_LEDGER.tsv (B-05)（hist_e #68））
- **证据等级**: E1-static

**问题现象**：两处记录给出不同 stride。

**预期行为**：唯一值。

**实际行为**：1154 是当前实现（codol_types.h 常量），且 FAT 已实测不触发，影响小。

**触发条件**：—

**影响范围**：低（FAT 不触发）。

**历史调查过程**：—

**当前最可信判断**：低影响

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：随 0065 一起处理。

**证据来源**：

- `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/07_SERVER_READINESS_ISSUE_LEDGER.tsv`
- `CODOL_SERVER_319_20261021/include/codol_types.h`

**依赖**：`CODOL-ISSUE-0065`

**完成验收标准**：stride 有单一定义。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0077 — 插件边界 31,953 行零测试；部署制品陈旧

- **系统**: `build`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-14（COMBAT_SERVER_RECOVERY_BASELINE.md §4.2（hist_combat #9/#5））
- **证据等级**: hash-verified

**问题现象**：9 个插件专属文件（31,953 行）无测试；部署的插件 build DBA7273A… ≠ 部署 6D493B82…，'改源码后直接跑'的验证无效。

**预期行为**：源码与部署一致且有测试。

**实际行为**：不一致。

**触发条件**：ol-mod 插件线。

**影响范围**：该线结论不可信（但已非主线）。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：该线不投入。

**证据来源**：

- `COMBAT_SERVER_RECOVERY_BASELINE.md`
- `COMBAT_SERVER_BLOCKERS.md §4.2`

**完成验收标准**：—

**复杂度**：XL　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0078 — 战斗握手只有模拟客户端 e2e_client.py 验证过

- **系统**: `battle-network`
- **状态**: `UNVERIFIED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-22（docs/STAGE1_CRYPTO_DONE.md §五（hist_combat #98））
- **证据等级**: simclient

**问题现象**：e2e_client.py 是独立实现，不是官方客户端。

**预期行为**：官方客户端验证。

**实际行为**：加密/NAT/DTLS 链路的端到端只对模拟客户端成立。

**触发条件**：任何'握手已完成'的结论。

**影响范围**：握手层的官方兼容性未证——这与 10-26 的 8 轮成功并不矛盾（那 8 轮确为官方客户端），但 10-27 之后全部零收包。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：官方客户端的握手抓包。

**最小验证方法**：在能连上的配置下抓一次官方客户端握手。

**推荐修复方向**：以 10-26 的 8 轮为准复现，并落盘抓包。

**证据来源**：

- `CODOL_SERVER_319_20261021/docs/STAGE1_CRYPTO_DONE.md`
- `CODOL_SERVER_319_20261021/docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`
- `docs/BATTLE_CONNECT_DIVERGENCE_20261028.md`

**依赖**：`CODOL-ISSUE-0020`

**完成验收标准**：官方客户端握手被完整抓包并逐字节复用。

**复杂度**：M　**推荐处理顺序**：P1-19

---

### CODOL-ISSUE-0079 — IIPS 的 Stage-1 前置门（QoS helper）从未被跨过

- **系统**: `startup`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-19（ICH017_IIPS_BOUNDARY_SYNTHESIS.md（hist_boot #1/#10））
- **证据等级**: E1-static + 负面运行时

**问题现象**：分叉点 iips.dll+0x98D2 `test al,al` 是静态已证；AL 的来源是 QoS helper（tqos_create → WSOCK32!select() → 负值 → AL=0）。该 helper 检查什么、返回什么，自评 DEPENDENCY_CAUSALITY = CANDIDATE。IIPS 成功路径从未在运行时观测到。

**预期行为**：能解释并复现 IIPS 初始化成功。

**实际行为**：冻结 kit 能绕过，但机制未明。

**触发条件**：不用 kit 自建 IIPS 环境时。

**影响范围**：启动链的'正规'实现不可能；只能依赖 kit。

**历史调查过程**：ICH013–ICH021 共约 8 轮推进，最后绕开而非解决。

**当前最可信判断**：分叉点确定；前置条件未知

**尚缺证据**：QoS helper 的检查对象与返回值。

**最小验证方法**：用 EX060–065 的契约写最小替身并观测 AL 值。

**推荐修复方向**：与 ISSUE-0006 合并处理；当前不阻塞主线。

**证据来源**：

- `ICH017_IIPS_BOUNDARY_SYNTHESIS.md`
- `ICH018_QOS_RETURN_VALUE_ATTRIBUTION.md`
- `ICH014_IIPS_FOUR_STAGE_FAILURE.md`

**依赖**：`CODOL-ISSUE-0006`

**完成验收标准**：IIPS 成功路径被运行时观测一次。

**复杂度**：L　**推荐处理顺序**：低优先

---

### CODOL-ISSUE-0080 — 用户态无法恢复 VM 解释器 / ISA / 解密器（.tvm0 语义）

- **系统**: `client-re`
- **状态**: `BLOCKED`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-21（ICH039/ICH041/ICH058/ICH059（hist_boot #11–#15））
- **证据等级**: E1-static + 负面运行时

**问题现象**：解释器、ISA、解密 routine、调度器全部 NOT_LOCATED；'.tls 是调度器'与 Anchor A/B 两条假设均被自行证伪。调试访问被反作弊阻断。

**预期行为**：能读出 .tvm0 里的逻辑。

**实际行为**：只能在用户态观察，且观察窗口会被 ACE 截断。

**触发条件**：任何指向 .tvm0/.tls 内部的结论。

**影响范围**：所有'在明文里找不到'的结论都必须带'该区未解'限定。

**历史调查过程**：四条假设已作废（.tls 调度器、Anchor A/B、96 项表、Resource→FF 桥）。

**当前最可信判断**：确定（未定位）

**尚缺证据**：VM 入口。

**最小验证方法**：—

**推荐修复方向**：不做；改用运行时转储在窗口内取字节。

**证据来源**：

- `ICH039_DECISION.md`
- `ICH041_DECISION.md`
- `ICH058_DECISION.md`
- `ICH059_DECISION.md`
- `ICH046_DECISION.md`

**依赖**：`CODOL-ISSUE-0043`

**完成验收标准**：—

**复杂度**：XL　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0081 — ResourceManager ABI 大部分是虚构的；GetResourceManagerII 从未被调用

- **系统**: `startup`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-21（RESTORE_LOCALRM_006_DECISION.md / RESTORE_ENGINE_BRIDGE_003（hist_boot #20/#25））
- **证据等级**: E0-runtime + E1-static

**问题现象**：9 次运行、两套 provider 下 GetResourceManagerII 被调用 0 次；ICH-027 的 IIPS_IsPackReady 契约在运行时被否定；早期'ResourceManager ABI'描述大部分虚构；LocalRM_v3 导出目录错位 4 字节；对象尺寸 0x480 vs 0x410 矛盾。

**预期行为**：资源栈有可信 ABI。

**实际行为**：自建 ABI 与客户端实际行为不符。

**触发条件**：任何试图替代 IIPS/资源管理器的实现。

**影响范围**：'自研资源层'这条路线的全部设计前提不可信。

**历史调查过程**：连续多轮自我证伪。

**当前最可信判断**：确定（ABI 描述不可信）

**尚缺证据**：真实 ABI。

**最小验证方法**：—

**推荐修复方向**：不再按虚构 ABI 设计；只能走 kit。

**证据来源**：

- `RESTORE_LOCALRM_006_DECISION.md`
- `RESTORE_ENGINE_BRIDGE_003_DECISION.md`
- `ICH027_IIPS_ENGINE_CONTRACT.md`
- `ICH054_DECISION.md`

**依赖**：`CODOL-ISSUE-0006`

**完成验收标准**：任何资源层替代方案有运行时调用证据。

**复杂度**：XL　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0082 — 命令行语义与历史真实命令行均未知（-q/-qa/-src=tgp、argv 提供者槽）

- **系统**: `startup`
- **状态**: `UNVERIFIED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-16（CODOL_EX032/EX033/EX035（hist_boot #35–#37））
- **证据等级**: E1-static

**问题现象**：argv 提供者槽 0xCA827C 的 API 身份未证；`-q/-qa/-src=tgp` 语义未决；历史真实命令行从未找到。

**预期行为**：能复现官方启动参数。

**实际行为**：当前靠 kit 的固定 argv。

**触发条件**：换启动方式。

**影响范围**：若官方参数不同，行为可能不同。

**历史调查过程**：—

**当前最可信判断**：未证

**尚缺证据**：官方命令行样本。

**最小验证方法**：对比 kit argv 与 EX033 的候选集合。

**推荐修复方向**：记录 kit 使用的 argv 为事实基线。

**证据来源**：

- `CODOL_EX032_ARGV_PROVIDER_SEMANTICS.md`
- `CODOL_EX033_HISTORICAL_CLIENT_COMMANDLINE.md`
- `CODOL_EX035_Q_QA_GATE_AND_BOOTSTRAP.md`

**完成验收标准**：kit 的 argv 被文档化为'已知可行'而非'官方等价'。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0083 — TCLS 共享内存布局与 tcls_core.exe 的创建者未知

- **系统**: `startup`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-09-16（CODOL_EX065–EX068 / CODOLLauncher（hist_boot #38–#42））
- **证据等级**: E1-static + E0-runtime

**问题现象**：TCLS 共享内存/签名布局未知（写零缓冲）；谁创建 tcls_core.exe 未知；payload 的 PID/GameID 生成未知；TenProxy Invoke(0x566) 未解包；状态值 0x63/0x18/0x11 语义未知。

**预期行为**：能独立构造 TCLS 握手。

**实际行为**：只能靠 kit。

**触发条件**：脱离 kit 启动。

**影响范围**：同 ISSUE-0006。

**历史调查过程**：—

**当前最可信判断**：确定（未知）

**尚缺证据**：TCLS 协议规格。

**最小验证方法**：—

**推荐修复方向**：不处理（kit 可用）。

**证据来源**：

- `CODOL_EX065_TCLS_UPSTREAM_BOUNDARY.md`
- `CODOL_EX066_TCLS_PROTOCOL_CLOSURE.md`
- `CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md`
- `CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md`
- `CODOLLauncher/CODOL_LAUNCHER_V1.md`

**依赖**：`CODOL-ISSUE-0006`

**完成验收标准**：—

**复杂度**：XL　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0084 — IIPS 两难：enable_iips=1 弹窗 vs enable_iips=0 立即退出，二者未调和

- **系统**: `startup`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-19（TAKEOVER_STATUS_20261019.md（hist_boot #47））
- **证据等级**: E0-runtime（两处）

**问题现象**：在 sandbox 语境下记录为两难；但在本体上 enable_iips=1 已实测可完整进大厅（2026-10-27）。

**预期行为**：单一解释。

**实际行为**：两处结论未对齐：一方说 =1 会弹窗，一方说 =1 能进大厅。

**触发条件**：使用沙箱 vs 本体。

**影响范围**：若将来有人读 TAKEOVER_STATUS，会误以为 =1 不可用。

**历史调查过程**：2026-10-27 的修复是在本体上做的；2026-10-19 的记录是沙箱语境。

**当前最可信判断**：两者可能是不同环境；未显式调和

**尚缺证据**：沙箱与本体在该项上的对照实验记录。

**最小验证方法**：在同一轮里分别用沙箱与本体跑 enable_iips=1。

**推荐修复方向**：在 TAKEOVER_STATUS 加环境限定注记。

**证据来源**：

- `TAKEOVER_STATUS_20261019.md`
- `docs/PVE_BATTLESTART_STATUS_20261027_1220.md §0`

**依赖**：`CODOL-ISSUE-0007`

**完成验收标准**：文档明确区分沙箱/本体结论。

**复杂度**：S　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0085 — 本地原生链被镜像识别拒绝（unknown executable image / SizeOfImage 门禁）

- **系统**: `startup`
- **状态**: `BLOCKED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-19（TAKEOVER_STATUS_20261019.md（hist_boot #45/#46））
- **证据等级**: E0-runtime

**问题现象**：AlwaysofflineRe: 'unknown executable image'（returncode 6，frame_hook=false）；宿主 SizeOfImage 门禁 0x0E5D6000 vs 实际 0x0E659000。

**预期行为**：本地原生链接管客户端。

**实际行为**：被拒。

**触发条件**：走 Localnetworking/AlwaysofflineRe 路线。

**影响范围**：该路线不可用（与 ol-mod 线同源的门禁）。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：—

**最小验证方法**：—

**推荐修复方向**：不投入；kit 路线已可用。

**证据来源**：

- `TAKEOVER_STATUS_20261019.md`
- `XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT`

**完成验收标准**：—

**复杂度**：L　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0086 — 3.19 运行时镜像仅覆盖约 4.5% SizeOfImage

- **系统**: `client-re`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: high
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-21（CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md R3-A01（hist_boot #70））
- **证据等级**: E1-static

**问题现象**：image_best.bin 10,899,456 B，仅覆盖约 4.513% SizeOfImage；IAT 槽与运行时全局在 EOF 之外。

**预期行为**：完整映像。

**实际行为**：静态 xref 无法证明完整分发器。

**触发条件**：任何需要读分发表/全局的结论。

**影响范围**：与 ISSUE-0042（.tp3 缺 229.6 MB）是同一现象的不同测法。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：完整页面列表或全量转储。

**最小验证方法**：dump_earliest 全量转储后统计覆盖率。

**推荐修复方向**：与 ISSUE-0042/0045 合并处理。

**证据来源**：

- `CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md`

**依赖**：`CODOL-ISSUE-0042`

**完成验收标准**：镜像覆盖 SizeOfImage 的可读部分并被记录。

**复杂度**：M　**推荐处理顺序**：P1-20

---

### CODOL-ISSUE-0087 — layer-2 世界资产（CLIPMAP_MP / MAP_ENTS / ComWorld）从未导出

- **系统**: `map`
- **状态**: `NOT_IMPLEMENTED`  **优先级**: `P1`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-21（THIRD_ROUND_PREREQUISITES.md R3-A07（hist_boot #53））
- **证据等级**: E1-static

**问题现象**：FF 容器已解出 block-0 布局，但 layer-2 世界资产从未导出；mp_firingrange 的 cbrush_t 表未定位。

**预期行为**：从 FF 导出四类资产。

**实际行为**：只有 coop_train 的稀疏 clip 体积。

**触发条件**：任何需要真实地图几何的工作。

**影响范围**：与 ISSUE-0029 同源。

**历史调查过程**：10-26 已解出 plane/brushside 表，brush 表未完成。

**当前最可信判断**：确定

**尚缺证据**：cbrush_t / brushBounds / brushContents 表。

**最小验证方法**：沿用 MP_FIRINGRANGE_CLIPMAP 的下一步。

**推荐修复方向**：与 ISSUE-0029 合并处理。

**证据来源**：

- `CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md`
- `docs/MP_FIRINGRANGE_CLIPMAP_20261026.md`
- `docs/CLIPMAP_EXTRACTION_20261026.md`

**依赖**：`CODOL-ISSUE-0029`

**完成验收标准**：mp_firingrange 的完整 clipmap 可导出并用于 trace。

**复杂度**：L　**推荐处理顺序**：P1-21

---

### CODOL-ISSUE-0088 — 固化链的参考实现本身带 6 次重试与共享 GAME_ROOT

- **系统**: `startup`
- **状态**: `PARTIALLY_RESOLVED`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-21（NEXT_RUN_BASELINE_DECISION_20261021.md（hist_boot #76））
- **证据等级**: E0-local-source

**问题现象**：受保护的 run_all.py 默认 6 次重试、共享 GAME_ROOT，与'单发'纪律冲突。

**预期行为**：参考实现本身就满足单发与隔离。

**实际行为**：靠 run_frozen_chain_once.py 在副本上改写（换成 range(1,2)、替换 GAME_ROOT）来满足。

**触发条件**：任何直接使用 kit 的尝试。

**影响范围**：纪律靠补丁维持，不是靠基线。

**历史调查过程**：已用 launcher 补齐。

**当前最可信判断**：确定（已缓解）

**尚缺证据**：—

**最小验证方法**：直接跑受保护 run_all.py 应出现 6 次重试。

**推荐修复方向**：保持现状；在文档里写明这是有意为之。

**证据来源**：

- `run_codol_001/run_frozen_chain_once.py:207-227, 299-306`
- `CODOL_ANALYSIS_20261020/NEXT_RUN_BASELINE_DECISION_20261021.md`

**完成验收标准**：文档说明 launcher 的两处改写及其理由。

**复杂度**：S　**推荐处理顺序**：P3

---

### CODOL-ISSUE-0089 — 黄金源目录含 208 个运行时残留，不能直接当干净启动树

- **系统**: `baseline`
- **状态**: `OPEN`  **优先级**: `P2`  **严重度**: medium
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-21（NEXT_RUN_BASELINE_DECISION_20261021.md（hist_boot #77））
- **证据等级**: E0-local

**问题现象**：GOLDEN-LOBBY-001/REF_LOBBY_KIT 有 13 处（另一处统计为 208 个）运行时残留：日志、证书、会话文件、两个 off 开关。

**预期行为**：干净可用的 9/9 基线。

**实际行为**：字节一致但含残留，需批准清理/迁移规则。

**触发条件**：baseline migration 时。

**影响范围**：与 ISSUE-0001 相关；不能简单覆盖。

**历史调查过程**：—

**当前最可信判断**：确定（计数口径不同）

**尚缺证据**：两份残留计数（13 vs 208）的差异说明。

**最小验证方法**：列出该目录相对受保护清单多出的文件。

**推荐修复方向**：与 ISSUE-0001 一起做 migration。

**证据来源**：

- `CODOL_ANALYSIS_20261020/NEXT_RUN_BASELINE_DECISION_20261021.md`
- `CODOL_ANALYSIS_20261020/THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md §11`

**依赖**：`CODOL-ISSUE-0001`

**完成验收标准**：有批准的 clean 规则，且迁移后可复现 9/9。

**复杂度**：M　**推荐处理顺序**：P2

---

### CODOL-ISSUE-0090 — TESTOL 交付包：1/769 哈希不符、缺 inject_ayria.on、deploy 只比大小

- **系统**: `external`
- **状态**: `OPEN`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-25（_LEARN_TESTOL_DELIVERY2/reports/010, 013；_LEARN_TESTOL_DELIVERY/reports/009（hist_boot #83–#85））
- **证据等级**: E0-local-hash

**问题现象**：清单 769 条里 1 条哈希不符（Localnetworking.Ayria32）；缺 inject_ayria.on ⇒ 插件不加载；deploy.ps1 只比大小 ⇒ 同大小替换永远部署不进去。

**预期行为**：交付包自洽可复现。

**实际行为**：三处缺陷；按 README 双击会失败。

**触发条件**：使用 TESTOL 包。

**影响范围**：该包不能作为独立路线；且按记忆条目它是用户 GOLDEN 主基线的精简子集。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：原版 Localnetworking.Ayria32 无法恢复（用户记忆条目）。

**最小验证方法**：—

**推荐修复方向**：只读参考；不作为主线。

**证据来源**：

- `_LEARN_TESTOL_DELIVERY2/reports/010-manifest-verify-result.md`
- `_LEARN_TESTOL_DELIVERY/reports/009-inject-switch-final-verdict.md`
- `_LEARN_TESTOL_DELIVERY2/reports/013-*.md`

**完成验收标准**：—

**复杂度**：M　**推荐处理顺序**：不处理

---

### CODOL-ISSUE-0091 — 真实 Frida 运行时从未执行（T2 线）

- **系统**: `tooling`
- **状态**: `UNVERIFIED`  **优先级**: `P3`  **严重度**: low
- **阻塞可玩战斗**: 否
- **首次发现**: 2026-10-16（T2_3_REGRESSION_REPORT.md（hist_boot #81））
- **证据等级**: 计划级

**问题现象**：T2 系列的运行时验证计划只做了脚本层回归；真实 Frida 从未执行。

**预期行为**：—

**实际行为**：计划未执行。

**触发条件**：—

**影响范围**：该线的运行时结论全部缺失。

**历史调查过程**：—

**当前最可信判断**：确定

**尚缺证据**：执行记录。

**最小验证方法**：—

**推荐修复方向**：不处理（ACE 已封死该路线）。

**证据来源**：

- `T2_3_REGRESSION_REPORT.md`
- `T2_1_G1_PROCESS_IDENTITY_REPORT.md`

**依赖**：`CODOL-ISSUE-0045`

**完成验收标准**：—

**复杂度**：M　**推荐处理顺序**：不处理

---
