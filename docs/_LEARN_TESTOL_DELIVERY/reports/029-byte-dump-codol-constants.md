# 学习报告 029 — 逐字节：CodolGameServer 的 61 个 `CODOL_*` 常量（战斗服能力全景）

**方法**：全文按 NUL 切分，正则 `^CODOL_[A-Za-z0-9_]+$` 去重 + 关键变量上下文读取
**性质**：全实测
**★★★ 本报告暴露了 9 个**未在导出表里**的 hook 点**

---

## 一、★★★ 61 个 `CODOL_*` 常量完整清单（实测）

### A. 52 个 `CODOL_GameServer*` 导出（与报告 019/020 的导出表**完全一致**）

```
CODOL_GameServerConfigureBooking
CODOL_GameServerConfigureGameState
CODOL_GameServerConfigureSession
CODOL_GameServerGetBotStatus
CODOL_GameServerGetClientGameplayStatus
CODOL_GameServerGetClientGameStateStage
CODOL_GameServerGetClientIngressStatus
CODOL_GameServerGetClientLoadingStatus
CODOL_GameServerGetClientMenuResponseStatus
CODOL_GameServerGetClientRejectStatus
CODOL_GameServerGetClientReliableCommandStatus
CODOL_GameServerGetClientUserCmdStatus
CODOL_GameServerGetConnectionlessDiagnosticsV1
CODOL_GameServerGetConstantConfigStringStatus
CODOL_GameServerGetDedicatedSessionConsumptionStatus
CODOL_GameServerGetEntityDamageStatusV1
CODOL_GameServerGetGameStateConfigurationStatus
CODOL_GameServerGetGameStateReadinessStatus
CODOL_GameServerGetGameStateStatus
CODOL_GameServerGetLoadingStatus
CODOL_GameServerGetLoadoutPreparationStatus
CODOL_GameServerGetLoadoutResolveFailure
CODOL_GameServerGetNetchanStatus
CODOL_GameServerGetNetworkStatus
CODOL_GameServerGetRegisteredCharacterPresentation
CODOL_GameServerGetRegisteredCharacterStatus
CODOL_GameServerGetSdStatusV1
CODOL_GameServerGetSessionStatus
CODOL_GameServerGetSnapshotDeltaStatus
CODOL_GameServerGetSnapshotStatus
CODOL_GameServerGetStatus
CODOL_GameServerGetTransportStatus
CODOL_GameServerGetTransportTimingStatus
CODOL_GameServerGetWorldBulletExecutionStatusV1
CODOL_GameServerGetWorldBulletExecutionStatusV2
CODOL_GameServerGetWorldClientThinkStatus
CODOL_GameServerGetWorldEventStatus
CODOL_GameServerGetWorldEventWeaponStatus
CODOL_GameServerGetWorldObjectiveStatusV1
CODOL_GameServerGetWorldPlayerFlagsStatus
CODOL_GameServerGetWorldPlayerHealthStatus
CODOL_GameServerGetWorldPlayerPmoveStatus
CODOL_GameServerGetWorldPlayerSampleV1
CODOL_GameServerGetWorldPlayerSampleV2
CODOL_GameServerGetWorldPlayerStatus
CODOL_GameServerGetWorldPlayerViewHeightStatus
CODOL_GameServerGetWorldPlayerWeaponStatus
CODOL_GameServerGetWorldPredictableEventStatusV1
CODOL_GameServerGetWorldResolvedLoadoutStatus
CODOL_GameServerGetWorldStatus
CODOL_GameServerRequestBots
CODOL_GameServerSetEnabled
```

★ **52 个 = 导出表 55 个减去 3 个非 `CODOL_` 前缀的**：
```
Createserver
onInitialized
onStartup
```
**52 + 3 = 55 ✓ 完全吻合**

### ★★★ B. 9 个**未在导出表里**的常量（重大发现）

```
CODOL_ANIMTREE_RESOLVE_HOOK      ← ★★★ 动画树解析 hook
CODOL_ANIMTREE_TRACE             ← ★ 追踪
CODOL_ANIMTREE_WRITE_WATCH       ← ★★ 写监视
CODOL_CLIENT_EXECUTION_STATE_PATCH ← ★★★ 客户端执行状态补丁
CODOL_FORGE_BUNDLE               ← ★★ 锻造包
CODOL_FORGE_CLONE                ← ★ 克隆
CODOL_FORGE_IMAGE_DIR            ← ★ 镜像目录
CODOL_IMAGE_UPLOAD_HOOK          ← ★★★ 图片上传 hook
CODOL_RAW_MOUSE_INPUT            ← ★★★ 原始鼠标输入
```

★★★ **这 9 个是**内部 hook 点/配置键**，不导出给加载器。**

★★ **⇒ 它们只被 `CodolGameServer` 自己用（读环境变量或内部开关）。**

---

## 二、★★★ 逐个解析这 9 个未知常量

### 1. `CODOL_ANIMTREE_RESOLVE_HOOK` —— 动画树解析 hook

★★ **`ANIMTREE`（animtree）** = CoD 引擎的**动画树**结构
（把动画、武器姿态、上半身/下半身混合的层级）。

★★ **`RESOLVE_HOOK`** = **在"解析动画树名 → 指针"时插入 hook。**

★★★ **这解释了 `OLMOD_VIEWHANDS_TF141` 和 `OLMOD_OUTFIT_ATTACHMENTS`**（报告 026）：
**换武器外观/手臂模型需要在动画树解析时替换模型指针。**

### 2. `CODOL_ANIMTREE_TRACE` / `CODOL_ANIMTREE_WRITE_WATCH`

★★ **`WRITE_WATCH`** = **监视对该内存的写入**（调试用）。

★ **可能是用 `VirtualProtect` 改成只读 + SEH 捕获写，或硬件断点（DR0-DR3）。**

★★ **⇒ 这是**深度调试工具**，说明作者曾深入研究动画树。**

### 3. `CODOL_CLIENT_EXECUTION_STATE_PATCH` —— 客户端执行状态补丁

★★ **`CLIENT_EXECUTION_STATE`** = 客户端的"执行状态机"（加载/进图/游戏中）。

★★★ **⇒ 这是用来**欺骗客户端状态机**的补丁**（让它以为已进图）。

★ **与 `CODOL_FORCE_RECORD_VALIDATOR`（报告 010）是同一类**：
**强制客户端走"成功"分支。**

### 4. `CODOL_FORGE_BUNDLE` / `CODOL_FORGE_CLONE` / `CODOL_FORGE_IMAGE_DIR`

★★ **`FORGE`** = 可能是**资产锻造**（像 Halo 的 Forge 模式）或**镜像构建**。

★ **`IMAGE_DIR`** = **镜像目录** —— 与 `CODOL_IMAGE_UPLOAD_HOOK` 呼应。

★★ **⇒ 这是一套"自定义资产"机制**：
**把自制模型/贴图打包，上传到客户端。**

### 5. `CODOL_IMAGE_UPLOAD_HOOK` —— 图片上传 hook

★★ **`IMAGE_UPLOAD`** = **玩家头像/自定义图片上传。**

★★ **⇒ hook 这个点可以**伪造上传结果**（离线时没有服务器）。**

### 6. `CODOL_RAW_MOUSE_INPUT` —— 原始鼠标输入

★★ **`RAW_MOUSE_INPUT`** = `WM_INPUT` / `RegisterRawInputDevices` 的原始鼠标。

★★★ **⇒ 与 `OLMOD_SWAY_PHASE`（报告 026，"瞄准摆动相位"）呼应：**
**作者在研究鼠标输入到瞄准的映射。**

★ **也可能是为了"离线机器人"注入鼠标输入。**

---

## 三、★★★ `OLMOD_SNAPSHOT_*` 的完整契约（逐串）

### `OLMOD_SNAPSHOT_ENTITY_BASELINES` @ `0x5D1294`

```
上下文：
  ...n_with_baseline...packet_entities.clients.overflow....client_infos....
  OLMOD_SNAPSHOT_ENTITY_BASELINES....
  predicted-mode client=%u frames=%u mode0=%u (%.1f%%) ctMatch=%u
  worstDist=%.4f noPred=%u weaponForced=%u
```

★★★ **这一段是**预测模式统计日志**，揭示了一个完整的调试体系**：

| 字段 | 含义 |
|---|---|
| `predicted-mode` | 预测模式 |
| `client=%u` | 客户端编号 |
| `frames=%u` | 帧数 |
| `mode0=%u (%.1f%%)` | 模式 0 占比 |
| `ctMatch=%u` | ★ 客户端-服务端匹配数 |
| `worstDist=%.4f` | ★★★ **最差距离** |
| `noPred=%u` | 无预测帧数 |
| `weaponForced=%u` | 武器强制数 |

★★★ **`worstDist` 是"客户端预测位置 vs 服务端位置"的最大偏差** ——
**这是**位置同步质量的核心指标**。**

★★ **⇒ 与记忆里的"位置 XOR 增量 bug"直接相关**（记忆 `codol-snapshot-field-diff-vs-references`）：
**如果位置写成 `to^from` 而位置没变 ⇒ 客户端读到 0 ⇒ `worstDist` 会很大。**

### `OLMOD_SNAPSHOT_ENTRY_FLAG` @ `0x5D132C`

```
上下文：
  ...ctMatch=%u worstDist=%.4f noPred=%u weaponForced=%u....
  solid=.
  OLMOD_SNAPSHOT_ENTRY_FLAG...
  useEntityBaselines=....
  [num=.. scriptMovers=.. brushModels=...
  -- the client will decode this messag
```

★★★ **关键字段**：

| 字段 | 含义 |
|---|---|
| `solid=` | 实体是否为实心 |
| `useEntityBaselines=` | ★★★ **是否用实体基线** |
| `num=` | 实体数 |
| `scriptMovers=` | ★ 脚本移动物体（电梯/门） |
| `brushModels=` | ★ 刷子模型（地图几何） |

★★★ **`"the client will decode this messag"`（被截断）** ——
**这是警告文本，说明某种情况下客户端会解错消息。**

★★ **`useEntityBaselines` 正是 `OLMOD_SNAPSHOT_ENTITY_BASELINES` 的效果开关。**

### `OLMOD_SNAPSHOT_HEX` @ `0x5DD4D4`

```
上下文：
  ...configuration ACCEPTED classMask=. firstDynamicWeapon=....
  buckets=...
  OLMOD_SNAPSHOT_HEX_OBITUARY.
  OLMOD_SNAPSHOT_HEX.. delta=. init=..
  snapshot build rejected client=. failure=...
  SNAPHEX seq=.... len=.
```

★★★ **`SNAPHEX seq=.... len=.`** = **快照十六进制转储**（`OLMOD_SNAPSHOT_HEX` 开启时）。

★★ **`snapshot build rejected client=. failure=.`** ——
**说明有**"快照构建被拒绝"**的分支，带 `failure` 原因。**

★★★ **⇒ 这是排查"客户端拒收快照"的**现成工具**。**
**对我们的"黑屏无 ack"问题（记忆 `codol-battle-server-world-binding`）直接可用。**

---

## 四、★★★ `OLMOD_BOT_NAMES` / `OLMOD_BOT_*` 的机器人体系

### `OLMOD_BOT_NAMES` @ `0x5DFCD0`

```
上下文：
  ...ls=... readUs=....BOTTRACE|class-resolve index=... lookupUs=..
  first=.
  OLMOD_BOT_NAMES.
  BOTTRACE|name-pool count=...official21..
  OLMOD_BOT_FILL..
  OLMOD_BOT_CHARACTERS....
  minPlanar=.
  OLMOD_BOTS..
  BOTTRACE|r
```

★★★ **`"official21"` 是一个关键常量** ——
**可能是"21 个官方机器人名"。**

★★ **`BOTTRACE|name-pool count=` + `BOTTRACE|class-resolve index=` + `minPlanar=`** ——
**完整的机器人调试日志。**

### ★★ 机器人相关的 12 个变量（报告 026）

```
OLMOD_BOTS                ← 总开关
OLMOD_BOT_AI              ← AI 开关
OLMOD_BOT_AI_TRACE        ← AI 追踪
OLMOD_BOT_CHARACTER       ← 单个角色
OLMOD_BOT_CHARACTERS      ← 角色列表
OLMOD_BOT_CLASS_TIMING    ← 职业时序
OLMOD_BOT_FILL            ← 自动填满
OLMOD_BOT_LIFE_GATE       ← 生命门槛
OLMOD_BOT_NAMES           ← 名字池
OLMOD_BOT_WAYPOINTS       ← 路径点
OLMOD_BATTLECHATTER_TEAM  ← 队友战吼
OLMOD_BATTLECHATTER_EXCLUDE_SELF
```

★★ **⇒ 这是一套**完整的离线机器人系统**。**

---

## 五、★★★ `bind_world` 在二进制的**完全缺失**（关键否证）

```
搜 bind_world       0 次
搜 WorldBind        0 次
搜 world_bind       0 次
搜 svc->world       0 次
搜 GameWorld        0 次
搜 world ==         0 次
搜 world=           0 次
搜 OLMOD_WORLD_BIND 未找到
```

★★★ **⇒ `CodolGameServer.Localnet32` 里**完全没有** `bind_world` 这个符号/字符串。**

★★ **这与记忆的对照**：

> 记忆 `codol-battle-server-world-binding.md`：
> "`codol_battle_service_bind_world` **从未被调用** ⇒ `svc->world` 恒 NULL
> ⇒ 实体层/真 clipmap 碰撞/伤害/HIT **整条是死的**;
> `main.c` 一行接上全解锁（离线:damage 33、位移 89.1、trace fraction 0.292）"

★★★ **⇒ 记忆说的是**我们自己的** C 实现（`codol_battle_service_bind_world`），
**不是外部包的 C++ 实现（`CodolGameServer.Localnet32`）。**

★★ **⇒ 外部包可能**没有**这个问题（它是从零实现的 C++ 战斗服，
`world` 由构造函数/`onStartup` 初始化）。**

★★★ **这解开了两个项目的一个重大混淆：**
```
我们的 C 实现：        codol_battle_service_bind_world 从未调用 → world = NULL
外部 C++ 实现：        无 bind_world 符号 → world 在别处初始化（或直接内嵌）
```

★ **但**外部实现也可能有同样的问题**（只是用别的名字）。
**验收标准是 `CODOL_GameServerGetEntityDamageStatusV1` 返回什么。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 唯一 `CODOL_*` 串 | **61 个** |
| 2 | `CODOL_GameServer*` 导出名 | **52 个**（+ 3 个非前缀导出 = 55） |
| 3 | 未导出的 `CODOL_*` 常量 | **9 个**（ANIMTREE×3 / FORGE×3 / CLIENT_EXECUTION_STATE / IMAGE_UPLOAD / RAW_MOUSE_INPUT） |
| 4 | `OLMOD_SNAPSHOT_ENTITY_BASELINES` | `0x5D1294` |
| 5 | `OLMOD_SNAPSHOT_ENTRY_FLAG` | `0x5D132C` |
| 6 | `OLMOD_SNAPSHOT_HEX` | `0x5DD4D4` |
| 7 | ★ `worstDist=%.4f` | 预测质量核心指标 |
| 8 | ★ `useEntityBaselines=` | 实体基线开关 |
| 9 | ★ `snapshot build rejected client=` | 拒收诊断 |
| 10 | ★ `official21` | 21 个官方机器人名 |
| 11 | **`bind_world` 等 7 个符号** | ★★★ **全部 0 次** |

---

## 七、结论

### 结论 1：★★★ 战斗服的**可调试面极完整**

```
OLMOD_SNAPSHOT_*     快照/实体/位置诊断
OLMOD_BOT_*          机器人调试
OLMOD_*_PROBE        各类探针
CODOL_ANIMTREE_*     动画树 hook
SNAPHEX / BOTTRACE   十六进制/追踪日志
```

★★ **⇒ 如果我们的实现进不了图，可以用这些外部包的开关做对照实验。**

### 结论 2：★★★ `bind_world` 缺失解开了项目混淆

```
我们的 C 实现  → 有 bind_world，但从未调用 ⇒ world = NULL
外部 C++ 实现  → 无 bind_world 符号 ⇒ 结构不同
```

★★ **⇒ 两个项目的"世界绑定"问题**不是同一个 bug**。**

### 结论 3：★★ 换战斗服的**最小契约**（由 52 个导出确定）

```
必须实现（被 Alwaysoffline 调用）：
  CODOL_GameServerConfigureSession      ← ★ 最重要
  CODOL_GameServerConfigureBooking
  CODOL_GameServerConfigureGameState
  CODOL_GameServerSetEnabled            ← ★

必须实现（状态查询，供外部轮询）：
  CODOL_GameServerGetStatus
  CODOL_GameServerGetSessionStatus
  ... （其余 47 个，可以返回"未就绪"）
```

★★★ **⇒ 真正的核心只有 4 个 `Configure*`/`SetEnabled` + `GetStatus`。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **`CODOL_GameServerConfigureSession` @ RVA `0x2215B0` 的反汇编**
- [ ] ★★★ **`CODOL_GameServerSetEnabled` @ RVA `0x220890` 之后的部分**
- [ ] ★★ **`0x5D1294` 的完整 `predicted-mode` 格式串**
- [ ] ★★ **`official21` 的完整上下文**（21 个名字是什么）
- [ ] ★ **9 个未导出 `CODOL_*` 常量的读取点**
- [ ] ★ **`CODOL_ANIMTREE_RESOLVE_HOOK` 是否在环境变量里**（还是编译期）
