# 学习报告 061（重开）— `runtime.md` 收尾（health / spawn / modular weapon）

**学习范围**：`.agents\modules\runtime.md` 第 358–369 行（文件结束）
**性质**：全实测
**★★★ 本报告收录**三层诊断**与**一个未解决的长时稳定性问题**

---

## 一、★★★★★ `runtime.md` 的完整规模与结构

| 项 | 值 |
|---|---|
| 总行数 | **369** |
| 字节数 | **48,090** |
| 平均每行 | **130 字节** |

### ★★★ 完整的章节结构

```
1.   分发与启动                      （第 3–44 行）
2.   双进程启动                      （第 46–243 行）
3.   Frida 临时目录                  （第 245–249 行）
4.   匹配自动化                      （第 251–341 行）
5.   Weapon movement 回归            （第 339–341 行）
6.   观察顺序                        （第 343–352 行）
7.   2026-08-03 自动化边界更新       （第 354–369 行）
8.   2026-08-08 modular weapon 回归  （第 364–369 行）
```

★★★ **⇒ 八节，覆盖**分发/启动/双进程/自动化/回归/观察顺序**全链。**

---

## 二、★★★★★ 三层诊断的完整设计（第 360 行）

```markdown
health/damage 验证现由三层诊断共同读取：
`CODOL_GameServerGetWorldPlayerHealthStatus` 暴露 server-owned current/max health
与 damage 四元组，
`CodolNetchanTrace.py` 记录每次真实 parser commit，
`CodolCgameState.py` 同时读取 snapshot/next snapshot/predicted state。
clean run `.runtime/natural-match/20260804_health_spawn_v1/`
三层一致为 `100/100` 和四项零值，playerstate parser 零 overflow；
截图仍有紫红边缘，故视觉 overlay 不进入 health wire 的成功判据。
```

### ★★★★★ 三层诊断表

| # | 层 | 工具/API | 读什么 |
|---|---|---|---|
| **1** | **server-owned** | **`CODOL_GameServerGetWorldPlayerHealthStatus`** | current/max health + **damage 四元组** |
| **2** | **wire（parser）** | `CodolNetchanTrace.py` | 每次**真实 parser commit** |
| **3** | **client（state）** | `CodolCgameState.py` | **snapshot / next snapshot / predicted state** |

★★★ **⇒ 三层一致才是可信的验证：**
```
server 层  ⇒  值是多少
wire 层    ⇒  发了什么
client 层  ⇒  收到什么
        ↓
★★★ **三层一致 ⇒ 数据链完整**
```

### ★★★ 实测结果

```
三层一致为 100/100 和四项零值
playerstate parser 零 overflow
```

★★ **⇒ `100/100` = current/max health。**

★ **⇒ "四项零值" = damage 四元组全零（无伤害）。**

### ★★★★★ 一条重要的判据排除（逐字）

```
截图仍有紫红边缘，故视觉 overlay 不进入 health wire 的成功判据。
```

★★★ **⇒ **视觉现象不能作为 wire 的成功判据**：**
```
截图有紫红边缘（视觉异常）
        ↓
但三层 wire 数据一致（100/100 + 四零）
        ↓
★★★ **不能因为视觉异常就判 wire 失败**
```

★ **⇒ 这是**区分"wire 正确"与"渲染正确"**的关键设计。**

---

## 三、★★★★ `CODOL_GameServerGetWorldEventStatus` 的**最后转换保留**（第 362 行）

```markdown
`CODOL_GameServerGetWorldEventStatus` 现保留当前 world 的最后一个 authoritative transition，
避免 250 ms/500 ms watcher 错过单帧 spawn notify。
clean run `.runtime/natural-match/20260804_spawn_notify_v1/`
在 Playing 后读回唯一 `client_spawned sequence=1/spawnSequence=1/spawnGeneration=1`，
后续 snapshot 持续推进但 sequence 不变；
该 checkpoint 用于诊断与压缩恢复，脚本运行时仍应直接消费同帧 `SvServerWorld::frameEvents()`。
```

### ★★★★★ 一个精确的竞态问题

```
watcher 轮询间隔：**250 ms / 500 ms**
        ↓
spawn notify 只持续**单帧**（~50 ms）
        ↓
★★★ **watcher 会错过**
        ↓
修复：**保留最后一个 authoritative transition**
```

### ★★★ 实测的三个序列号

```
client_spawned sequence=1
              spawnSequence=1
              spawnGeneration=1
```

★★ **⇒ 三个都为 `1`（首次 spawn）。**

★★★ **⇒ 且明确使用边界：**
```
该 checkpoint **用于诊断与压缩恢复**
        ↓
★ 脚本运行时仍应直接消费**同帧** `SvServerWorld::frameEvents()`
```

★ **⇒ 即：**checkpoint 是补偿手段，不是主路径**。**

---

## 四、★★★★★ `--force-client-allocation` 的 loadout 门槛（第 366 行）

```markdown
`CodolNaturalMatchTrace.py --force-client-allocation` 现在在启动 QuickMatch 前等待
server `loadout_preparation.prepared=true`、当前/已准备角色一致且至少一套 class 已注册；
默认有界等待 45 秒，可用 `--loadout-prepare-timeout` 调整。
该门槛只约束会跳过自然倒计时的 forced allocation，
不改变自然 allocation 或 active-world 复用语义。
```

### ★★★★★ 三重前置条件

```
① server `loadout_preparation.prepared = true`
② 当前/已准备角色**一致**
③ 至少一套 class **已注册**
        ↓
★ 默认有界等待 **45 秒**
```

★★★ **⇒ 且明确**适用范围**：**
```
只约束 **forced allocation**（会跳过自然倒计时）
        ↓
★ **不改变**自然 allocation 或 active-world 复用语义
```

### ★★★ 实测数据（第 366 行）

```
clean run `.runtime/natural-match/20260808_weapon_dependency_cache_prepared_v12_retry/`
在角色 `3`、attempt `17`、mask `31` 后才进入匹配，
随后以真实 client cgame resolver 证明动态 weapon `352..360` 连续，
parser `42/42`、零 overflow/`Com_Error`，active client 和 snapshot world 均建立。
```

### ★★★★★ 四个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | 角色 | **`3`** |
| **2** | attempt | **`17`** |
| **3** | class mask | **`31`** |
| **4** | ★ 动态 weapon 范围 | **`352..360`**（连续 9 个） |

★★ **⇒ `mask 31` = `0x1F` = 低 5 位全置（5 个 class 已注册）。**

★ **⇒ `attempt 17` ⇒ 前 16 次都未满足前置条件（需要重试）。**

---

## 五、★★★★★ 一个**未解决的长时稳定性问题**（第 368 行，逐字）

```markdown
同 PID 的后续只读状态还确认用户自然选择的 `custom1` 已进入 `Playing`，
primary/secondary 为 `353/354`，当前 weapon `353`、clip `6`，
与客户端"自由 黑金"截图一致。
约 150 秒后 ingress 的 accepted packet 停在 `4256`，后续拒绝开始累积，
主要原因为 usercmd command time 非递增，之后又出现 invalid fragment，
ack 不再推进并最终退出。
该现象是下一项长时 netchan/usercmd 稳定性调查，
不归因于 modular registry，也不能用重发 loadout 或 UI 操作掩盖。
```

### ★★★★★ 完整的失败时间线

| 时刻 | 状态 |
|---|---|
| **进入 Playing** | `custom1`，primary/secondary **`353/354`**，当前 weapon **`353`**，clip **`6`** |
| ★ 验证 | 与客户端"自由 黑金"截图**一致** |
| **约 150 秒后** | ★★★ accepted packet 停在 **`4256`** |
| 之后 | **拒绝开始累积** |
| ★ 主要原因 | **usercmd command time 非递增** |
| 再之后 | **invalid fragment** |
| 最终 | **ack 不再推进并退出** |

★★★ **⇒ 三个级联的失败：**
```
① **usercmd command time 非递增**（主因）
        ↓
② **invalid fragment**
        ↓
③ **ack 不再推进** ⇒ 退出
```

### ★★★ 明确的归因边界（逐字）

```
该现象是下一项长时 netchan/usercmd 稳定性调查，
不归因于 modular registry，
也不能用重发 loadout 或 UI 操作掩盖。
```

★★★ **⇒ 三条边界：**
```
① **不归因于** modular registry（那是另一回事）
② **不能用**重发 loadout 掩盖
③ **不能用** UI 操作掩盖
```

★ **⇒ 这是**极其严谨的归因纪律**。**

---

## 六、★★★ `forced allocation` 的 `startGame` 时序（第 358 行）

```markdown
forced allocation 现会在 `ready_confirmed` 的同一次 UI-thread drive 中调用 `startGame`，
避免依赖下一次 message dispatch。
但 `.runtime/natural-match/20260803_character_viewhands_v4/`
仍在调用后约 55 秒才看到客户端真正 connect；
这说明 room `SetReady(1)` 的本地 readback 尚不等于后端确认 ready，
不能把 pipeline 标成完整 working。
```

★★★ **⇒ 一个**关键的区别**：**
```
room `SetReady(1)` 的**本地 readback**
        ↓
★★★ **不等于**后端确认 ready
        ↓
（实测：调用后约 **55 秒**才真正 connect）
        ↓
★ 不能把 pipeline 标成完整 working
```

★★ **⇒ 且明确方向："后续 ready 修复应回到 **backend/room event ownership**，
**不重新研究 PVP UI 导航**。"**

---

## 七、★★★ `CodolMatchFlow` 的 PublicProfile 停滞处理（第 356 行）

```markdown
clean launch 偶发出现 lobby 已 logon、QuickMatch objects 已 ready，
但 PublicProfile 长时间停在 `chunk_mask=0/operation=1/parsed=false`。
backend 已有 `CODOL_RequestInventoryRefresh` export；
实跑中请求后 refresh generation `1` 从 queued 进入 succeeded，
客户端随即恢复到 `chunk_mask=0x7ffffff/operation=0/parsed=true`。
`CodolMatchFlow` 现只对这一精确停滞签名等待 10 秒后请求一次，
不对普通 lobby 登录、profile operation `0` 或其他失败状态盲目重试。
```

### ★★★★★ 一个精确的停滞签名与恢复

**停滞状态：**
```
chunk_mask = 0
operation  = 1
parsed     = false
```

**恢复后：**
```
chunk_mask = 0x7ffffff      （★ 27 位全置）
operation  = 0
parsed     = true
```

★★★ **⇒ `0x7ffffff` = 27 位 ⇒ 与第 297 行的"**27 个 required chunks**"完全吻合。**（报告 060 已记录）**

### ★★★ 修复方式（极精确）

```
只对**这一精确停滞签名**等待 **10 秒**后请求**一次**
        ↓
★ **不对**普通 lobby 登录、profile operation `0` 或其他失败状态**盲目重试**
```

★★★ **⇒ 这是**精确匹配 + 有限重试**的典范（不是笼统的"重试"）。**

★ **⇒ 调用的 API 是 **`CODOL_RequestInventoryRefresh`**（`Alwaysoffline` 的 5 个导出之一，报告 053）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ `runtime.md` 规模 | **369 行 / 48,090 B** |
| 2 | ★★★ 八节结构 | 分发/双进程/Frida/自动化/weapon 回归/观察顺序/两节更新 |
| 3 | ★★★★★ **三层诊断** | **server API** + **wire parser** + **client state** |
| 4 | 三层实测 | **`100/100` + 四项零值**，parser 零 overflow |
| 5 | ★★★ **视觉不参与判据** | 截图有紫红边缘，但 **overlay 不进入 wire 判据** |
| 6 | ★★★ watcher 竞态 | **250 ms / 500 ms** 会错过**单帧** spawn notify |
| 7 | ★ 修复 | **保留最后一个 authoritative transition** |
| 8 | 三个序列号 | **`sequence=1` / `spawnSequence=1` / `spawnGeneration=1`** |
| 9 | ★★ 使用边界 | checkpoint 用于诊断；**主路径仍消费同帧 `frameEvents()`** |
| 10 | ★★★ `--force-client-allocation` 三重门槛 | `prepared=true` + 角色一致 + **至少一套 class 注册** |
| 11 | 默认等待 | **45 秒** |
| 12 | ★ 实测 | 角色 **`3`** / attempt **`17`** / mask **`31`** |
| 13 | ★★ 动态 weapon | **`352..360`**（连续 9 个） |
| 14 | ★★★★★ **未解决的长时问题** | **150 秒后 accepted 停在 `4256`** |
| 15 | ★★★ 主因 | **usercmd command time 非递增** |
| 16 | 级联 | **invalid fragment** ⇒ **ack 不推进** ⇒ 退出 |
| 17 | ★★★ 归因纪律 | **不归因 modular registry；不能用重发 loadout/UI 掩盖** |
| 18 | ★★★ `SetReady` 陷阱 | **本地 readback ≠ 后端确认**（55 秒后才 connect） |
| 19 | ★★★ PublicProfile 停滞 | **`chunk_mask=0/operation=1/parsed=false`** |
| 20 | 恢复后 | **`chunk_mask=0x7ffffff`（27 位）/ operation=0 / parsed=true** |
| 21 | ★★ 重试策略 | **只对这一签名等 10 秒请求一次**（不盲目重试） |

---

## 九、结论

### 1. ★★★★★ **三层诊断（server/wire/client）是验证数据链的标准方法**

★ **⇒ 三层一致才可信；视觉现象不参与判据。**

### 2. ★★★★★ **一个未解决的长时稳定性问题**

```
约 150 秒后：
  accepted packet 停在 4256
  usercmd command time 非递增（主因）
  invalid fragment
  ack 不推进 ⇒ 退出
        ↓
★★★ **明确的归因纪律**：不归因 modular registry，
不能重发 loadout 或 UI 操作掩盖
```

### 3. ★★★★ **`SetReady(1)` 的本地 readback ≠ 后端确认**（55 秒后才 connect）

### 4. ★★★ **watcher 250/500 ms 会错过单帧 spawn notify** ⇒ 需保留最后 transition

### 5. ★★★ **PublicProfile 的 `chunk_mask=0x7ffffff` = 27 个 required chunks**

### 6. ★★ **精确停滞签名 + 有限重试**（不盲目重试）

---

## 十、`runtime.md` 的完整学习总览

| 报告 | 范围 | 核心成果 |
|---|---|---|
| **058** | 第 1–120 行 | 标准启动四约束 / 六个 Winsock hook / mutex 改名 |
| **059** | 第 120–249 行 | **13 个裁剪实验 v26–v51** / 两次证伪 |
| **060** | 第 249–358 行 | 十个工具 / 两条 Frida 教训 / 抖动定量排除 |
| **061** | 第 358–369 行 | 三层诊断 / 长时稳定性问题 |

---

## 十一、下一步

- `source\.agents\modules\game_server.md`（223,587 B，**最大的文档**）
- `source\.agents\modules\backend.md`（19,203 B）
- `source\.agents\modules\gsc.md`（21,617 B）
- `source\.agents\modules\reverse_engineering.md`（89,517 B）
- `source\docs\devlog\`（中文开发历程）
- `source\tools\runtime\CodolGame.py`
