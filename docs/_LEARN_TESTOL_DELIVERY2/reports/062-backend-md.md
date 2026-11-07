# 学习报告 062（重开）— `backend.md`（19,203 B）DW3 控制面

**学习范围**：`source\.agents\modules\backend.md` 第 1–120 行
**性质**：全实测（**与我们方案最相关的模块**）
**★★★ 本报告收录**Ready→Booking 完整链路**、**身份三层所有权**、**entitlement 两类来源**

---

## 一、★★★★★ Backend 的职责边界（第 5 行，逐字）

```markdown
`src/backend` 是 DW3 控制面，负责 Auth3、LSG、service/task 分发、publisher storage、
玩家持久化、房间消息、matchmaking 和 booking 转交。
它不负责地图模拟、`SV_Frame`、GSC、实体或 snapshot。
按原版 COD 职责，backend 与 dedicated game server 都属于服务端基础设施，
但不是同一模块；本地部署以后可以由一个 server launcher 同时启动二者，
不应因此合并数据所有权。
```

### ★★★★★ 完整的职责划分

| Backend **负责** | Backend **不负责** |
|---|---|
| **Auth3** | 地图模拟 |
| **LSG** | `SV_Frame` |
| **service/task 分发** | GSC |
| **publisher storage** | 实体 |
| **玩家持久化** | snapshot |
| **房间消息** | |
| **matchmaking** | |
| **booking 转交** | |

★★★ **⇒ 这是**极其清晰的职责边界**：**
```
backend  =  控制面（谁在玩、玩什么、怎么连）
game_server  =  数据面（地图、实体、快照）
        ↓
★★★ **不是同一模块，不合并数据所有权**
```

★ **⇒ 且明确："本地部署以后可以由一个 server launcher 同时启动二者，**不应因此合并数据所有权**。"**

### ★★★ 当前的迁移拓扑（第 7 行）

```markdown
当前仍是迁移拓扑：`OLMOD_PROCESS_ROLE=client` 时 backend 继续依附客户端进程内的
Localnetworking socket bridge，`combined` 保留旧单进程兼容。
它尚未成为独立网络 daemon；在客户端只保留 endpoint redirect、backend 能独立接受连接之前，
不能宣称控制面已移出客户端。
```

★★★ **⇒ 三条现状：**
```
① `role=client`   ⇒ backend 依附客户端进程内的 Localnetworking socket bridge
② `role=combined` ⇒ 旧单进程兼容
③ ★★★ **尚未成为独立网络 daemon**
```

★★ **⇒ 且给出**明确的完成判据**：**
```
★ "在客户端只保留 endpoint redirect、backend 能独立接受连接之前，
  不能宣称控制面已移出客户端"
```

---

## 二、★★★★★ 玩家身份的**三层所有权**（第 13–17 行）

### 2.1 ★★★ 第一层：backend `PlayerIdentityStore`（显示名权威）

```markdown
运行时玩家名现在由 backend `PlayerIdentityStore` 按 `titleId/userId` 持有，
live 文件为 `Ayria/Assets/Alwaysoffline/1004/<USERID>/Identity.json`，
字段为 `schemaVersion=1/displayName`。
首次认证时若玩家档案不存在，才从根目录 `Ayria/Assets/Alwaysoffline/Identity.json`
读取 `username` 作为迁移种子并原子创建档案；种子缺失时使用源码中唯一的 `DefaultUsername`。
档案建立后修改迁移种子不会影响既有账号。
显示名必须为 1 至 16 字节 printable ASCII；
已存在档案格式非法时认证 fail closed，不静默回退另一身份。
```

### ★★★★★ 第一层的完整规则

| 项 | 值 |
|---|---|
| **权威持有者** | **`PlayerIdentityStore`** |
| **键** | **`titleId/userId`** |
| **live 文件** | **`Ayria/Assets/Alwaysoffline/1004/<USERID>/Identity.json`** |
| **字段** | **`schemaVersion=1` / `displayName`** |
| **创建时机** | **首次认证且档案不存在** |
| **种子来源** | 根目录 **`Ayria/Assets/Alwaysoffline/Identity.json`** 的 **`username`** |
| **兜底** | **源码中唯一的 `DefaultUsername`** |
| ★★★ **格式要求** | **1 至 16 字节 printable ASCII** |
| ★★★ **非法处理** | **认证 fail closed，不静默回退** |

★★★ **⇒ 第 1 条与 `fake_auth_tls.py` 的 `sanitize`**完全对应**（报告 045）：**
```
1 至 16 字节 printable ASCII
        ↓
而 fake_auth_tls.py 改成"只丢控制字符"（支持中文）
        ↓
★★★ **两者不一致！**
```

★ **⇒ 这是一个**重要的不一致**：**
```
backend.md:  1-16 字节 **printable ASCII**
fake_auth_tls.py:  只丢控制字符（**支持中文**）
        ↓
★ 若 backend 严格执行 ASCII 校验，中文名会被**拒绝**
```

### 2.2 ★★★ 第二层：`sessionKey` 与 `userId` 从请求恢复（第 15 行）

```markdown
Auth3 task 28 仍从客户端请求恢复 `userId` 和 `sessionKey`，
随后按该 `userId` 查询玩家档案；
请求中的旧 username 不再覆盖 server-owned display name。
```

★★★ **⇒ 与 `fake_auth_tls.py` 的 `consumeTask28CodoRequest`**完全一致**（报告 012）：**
```
task 28 的 codo_request：
  +0x06  userId
  +0x0E  username（16 字节）
  +0x20  sessionKey（24 字节）
```

★ **⇒ 且明确："请求中的旧 username **不再覆盖** server-owned display name"。**

### 2.3 ★★★ 第三层：platform ID（房间/OpenID 兼容身份）

```markdown
同日又确认 room internal ID 属于独立的客户端 platform identity 链。
源码化 `ol_platformwrapper` 通过 Tencent tag `22` 提供 full platform ID
`0x01100001DEADC0DE`；
clean 自然运行后，room member identity 和内嵌 `MatchMakingInfo` 均持有
internal ID `0xDEADC0DE`，并闭合 QuickMatch 到 world。
该 ID 不能替代 backend display name，也不能由 backend 重写 opaque matchmaking descriptor；
正式所有权是 backend 按 authenticated user ID 持有玩家资料，
Platformwrapper 只提供 CODOL 客户端兼容 platform/OpenID。
```

### ★★★★★ 三层所有权的完整表

| 层 | 内容 | 权威来源 | 值示例 |
|---|---|---|---|
| **1** | **显示名** | **backend `PlayerIdentityStore`** | `dest1yo` |
| **2** | **sessionKey / userId** | **客户端 task 28 请求** | （每会话随机） |
| **3** | ★★★ **platform ID** | **`ol_platformwrapper` 的 Tencent tag 22** | **`0x01100001DEADC0DE`** |

★★★ **⇒ 三个 ID 的精确关系：**
```
full platform ID      = 0x01100001DEADC0DE    （Platformwrapper tag22）
room internal ID      = 0xDEADC0DE            （★ 低 32 位）
```

★★ **⇒ 与 `fake_auth_tls.py` 的 `lstrip("0")` 逻辑**部分对应**（报告 045）：**
```
"01100001DEADC0DE"  →  lstrip("0")  →  "1100001DEADC0DE"（★ 15 位）
        ↓
而这里说 internal ID = 0xDEADC0DE（★ 只有低 32 位）
        ↓
★★★ **两者不一致！**
```

★ **⇒ 需要进一步核实哪个才是客户端实际用的。**

---

## 三、★★★★★ Ready → Booking 的**完整链路**（第 25–41 行，逐字）

```text
room request
  -> service 0x0B handler
  -> event 8 push
  -> local ready committed
  -> service 0x15 task 5, query kind 1 FIND_SERVERS
  -> explicit Session.Role=server result
  -> service 0x06 task 14 mmbook
  -> event 21 mmbook accepted
  -> service 0x06 task 14 mmstart
  -> BookingSink
  -> DedicatedBookingDispatcher worker
  -> client bridge captures native booking selection and item-ID loadout on Com_Frame
  -> backend entitlement validation
  -> versioned SessionStart
  -> dedicated game thread resolves its own assets and configures booking
```

### ★★★★★ 完整的十四步链路

| # | 步骤 | service/task |
|---|---|---|
| **1** | room request | — |
| **2** | service 0x0B handler | **`0x0B`** |
| **3** | event 8 push | event **`8`** |
| **4** | local ready committed | — |
| **5** | query kind 1 FIND_SERVERS | **`0x15` task `5`** |
| **6** | explicit `Session.Role=server` result | — |
| **7** | mmbook | **`0x06` task `14`** |
| **8** | event 21 mmbook accepted | event **`21`** |
| **9** | mmstart | **`0x06` task `14`** |
| **10** | BookingSink | — |
| **11** | DedicatedBookingDispatcher worker | — |
| **12** | client bridge capture（on `Com_Frame`） | — |
| **13** | backend entitlement validation | — |
| **14** | versioned SessionStart | — |
| **15** | dedicated 解析资产 + 配置 booking | — |

★★★ **⇒ 关键的服务/任务号：**
```
0x0B  → room handler
0x15 task 5  → FIND_SERVERS
0x06 task 14 → mmbook / mmstart
event 8   → ready
event 21  → mmbook accepted
```

### ★★★ query kind 的精确值（第 43 行）

```markdown
query kind `1` 是 `FIND_SERVERS`，kind `3` 是 `FIND_LOBBIES_BY_PLAYLIST`。
不能把玩家自己创建的 lobby 当作 server 返回。
```

★★★ **⇒ 两个 query kind：**
```
kind 1  =  FIND_SERVERS
kind 3  =  FIND_LOBBIES_BY_PLAYLIST
```

★★ **⇒ 且明确："**不能把玩家自己创建的 lobby 当作 server 返回**"。**

### ★★★ `BookingSink` 的语义边界（第 45 行）

```markdown
`BookingSink` 接受 `mmstart` 只表示 game server 已接管并排队该 booking；
CCS reset/reinitialize 和 `gamestate_configured` 在后续 `Com_Frame` 中完成，
不能把 sink 返回值解释为即时 gamestate 成功。
```

★★★ **⇒ 一个**重要的时序区分**：**
```
BookingSink 接受 mmstart  =  只是**排队**
        ↓
CCS reset/reinitialize + gamestate_configured  =  **后续 Com_Frame 中完成**
        ↓
★ 不能把 sink 返回值解释为**即时** gamestate 成功
```

---

## 四、★★★★★ `DedicatedBookingDispatcher` 的重试策略（第 47 行）

```markdown
`DedicatedBookingDispatcher` 收到 `mmstart` 后先通过 client bridge 捕获该 booking generation
的 native selection/loadout。该捕获由客户端 `Com_Frame` 消费，
加载切换期可能在 1.5 秒窗口内暂时返回 `Rejected`；
dispatcher 对这个只读操作使用同一 request ID 最多重试三次，
再做 entitlement 与 `SessionStart`。
不可在第一次 transient capture 失败后静默丢弃已经接受的 booking，
否则客户端会在加载边界显示服务器离线；
协议错误仍立即失败，重试也不得重复提交 dedicated side effect。
```

### ★★★★★ 五个精确规则

| # | 规则 | 值 |
|---|---|---|
| **1** | 加载切换期窗口 | **1.5 秒** |
| **2** | 暂时返回 | **`Rejected`** |
| **3** | ★ 重试次数 | **最多三次**（同一 request ID） |
| **4** | ★★ 不可静默丢弃 | 否则客户端**显示服务器离线** |
| **5** | ★★★ 协议错误 | **立即失败**（不重试） |

★★★ **⇒ 这是**极其精确的重试语义**：**
```
transient capture 失败（1.5 秒窗口内 Rejected）
        ↓
★ 重试最多 3 次（同一 request ID）
        ↓
协议错误 ⇒ 立即失败（不重试）
        ↓
★★★ 重试不得重复提交 dedicated side effect
```

---

## 五、★★★★ `entitlement` 的**两类来源**（第 51 行）

```markdown
backend entitlement 当前按 CODOL `CODOL_ItemAvailability_Query 0x695BC0` 已恢复的两类来源裁决：
有效且数量非零的持久 inventory，
以及 `CODOL_DefaultAvailableItems_Init 0x7052F0` 恢复出的 build 固定默认集合。
过期、零数量和未知 item 固定拒绝；
item-definition `flags & 2` 只影响已授予 inventory item 的非过期语义，不作为授予来源。
secure unlock/rank 条件和 onboarding-only fallback 尚未成为 backend provider 的完整输入，
因此不能把当前实现描述为全部 CODOL entitlement 规则已恢复，
也不能用"全部允许"绕过该边界。
```

### ★★★★★ 两类来源 + 三个精确地址

| # | 项 | 值 |
|---|---|---|
| **1** | 查询函数 | **`CODOL_ItemAvailability_Query 0x695BC0`** |
| **2** | 来源 A | **有效且数量非零的持久 `inventory`** |
| **3** | 来源 B | **`CODOL_DefaultAvailableItems_Init 0x7052F0`** 的 build 固定默认集合 |
| **4** | ★ 固定拒绝 | **过期 / 零数量 / 未知 item** |
| **5** | `flags & 2` 语义 | **只影响已授予 item 的非过期语义，不作为授予来源** |

★★★ **⇒ 三条明确的未完成：**
```
① secure unlock/rank 条件
② onboarding-only fallback
③ （因此不能声称全部 entitlement 规则已恢复）
```

★★ **⇒ 且明确："**也不能用'全部允许'绕过该边界**"。**

---

## 六、★★★★★ 多客户端共享 room 的**当前边界**（第 55–60 行）

```markdown
当前 backend 不能让两个真实客户端加入同一个控制面房间。
每个 client 进程都各自构造一套 `ServerFactory -> AuthSession -> LobbyServer`；
`LobbyServer` 又独占 `MatchmakingService`、`LobbyProtocol` 和 `DedicatedBookingDispatcher`。
`LanDiscovery` 只广播 session properties 和 channel/instant-message event，
能发现另一个进程的广告，却不持有 room member、ready、host、booking generation
或成员到 bridge endpoint 的权威映射。
当前 `AuthSession` 也只保存一个身份，因此不能把两个进程各自的 local state 拼成 roster。
```

### ★★★★★ 三个根本障碍

| # | 障碍 | 说明 |
|---|---|---|
| **1** | **每进程独立一套** | `ServerFactory → AuthSession → LobbyServer` |
| **2** | **`LobbyServer` 独占三个服务** | `MatchmakingService` / `LobbyProtocol` / `DedicatedBookingDispatcher` |
| **3** | ★★★ **`AuthSession` 只存一个身份** | 不能拼成 roster |

★★ **⇒ `LanDiscovery` 只能**发现广告**，不持有权威状态。**

### ★★★ 三步最小链路（第 69–80 行）

```markdown
1. 建立独立于 client 进程的共享 backend owner。
   它按 authenticated user ID 保存 connection、display name、room membership、ready
   和可版本化的 client bridge endpoint；客户端内 backend 退化为原协议接入/重定向边界。
2. booking owner 从共享 room 冻结 generation-scoped roster。
   它分别向每个成员登记的 bridge port 请求 `ClientSessionCapture`，
   校验所有 capture 的 booking selection 一致，并按成员自己的 backend inventory 执行 entitlement；
   任何成员超时、身份漂移、selection 冲突或非法物品都使整次 booking fail closed，
   不能提交半个 roster。
3. 新增版本化 match-start descriptor，公共 booking/rules 只编码一次，
   成员数组至少携带 authenticated `userId`、server-owned display name 和该成员的 item-ID loadout。
   dedicated 接收后冻结允许连接的 XUID 集合，并在 `SV_DirectConnect` 后按 XUID 将成员绑定到 slot；
   未列入 roster、重复 XUID 或缺失 loadout 均拒绝。
```

★★★ **⇒ 三步：**
```
① 独立 backend owner（按 authenticated user ID 保存五类状态）
② booking owner 冻结 roster（逐成员 capture + 一致校验 + 逐成员 entitlement）
③ 版本化 match-start descriptor（成员数组 + XUID 绑定 slot）
```

### ★★★ 已经建立的 `SharedRoomSessionOwner`（第 88–96 行）

```markdown
共享 owner 的协议无关状态核心现已建立为 `SharedRoomSessionOwner`：
按 authenticated XUID 保存 display name、独立 client bridge port、connection token 和 ready；
同一 XUID 重连会产生新 token，旧连接的 disconnect/ready 事件不能删除或修改新登录。
room 有一般化容量限制，成员按 XUID 稳定排序，
只有当前全部成员 ready 才能按非零 booking generation 冻结 roster；
同一 generation 的重复 freeze 永远返回首次快照，不随之后重连或离开漂移。
该 owner 已线程安全，并通过独立 `ol_room_owner.exe` 在 loopback 端口
（默认 `28970`，`OLMOD_ROOM_OWNER_PORT` 可覆盖）提供有界 connect/disconnect/ready/freeze IPC；
```

### ★★★★★ `SharedRoomSessionOwner` 的六个设计

| # | 设计 | 说明 |
|---|---|---|
| **1** | 按 **XUID** 保存四类 | display name / bridge port / **connection token** / ready |
| **2** | ★ **token 机制** | 同一 XUID 重连 ⇒ **新 token**；旧连接事件**不能修改新登录** |
| **3** | 容量限制 | 一般化（非固定 2 人） |
| **4** | ★ 排序 | **按 XUID 稳定排序** |
| **5** | ★★ 冻结条件 | **全部成员 ready** + **非零 booking generation** |
| **6** | ★★★ 幂等 | 同一 generation 重复 freeze ⇒ **永远返回首次快照** |

★★★ **⇒ 第 2 条是**关键的重连安全性设计**：**
```
同一 XUID 重连
        ↓
★ 产生**新 token**
        ↓
旧连接的 disconnect/ready 事件
        ↓
★★★ **不能删除或修改新登录**
```

★ **⇒ 第 6 条是**幂等设计**（重复 freeze 返回首次快照，不漂移）。**

---

## 七、★★★★ 资产分类的**四类**（第 113 行）

```markdown
正式分类如下：
`assets/backend/1004/Server` 与 `Cloud` 是不可变 publisher/backend 输入；
`MarketplaceSkus.json` 是项目恢复的 backend catalog；
user ID 目录下的 profile、inventory、wallet 与 identity 是 backend 可变状态；
根目录 `Identity.json` 只是首次迁移种子；
`Ayria/Assets/Platformwrapper` 只服务源码化客户端兼容插件，不属于 backend 状态。
```

### ★★★★★ 五类资产

| # | 类别 | 路径 |
|---|---|---|
| **1** | **不可变 publisher 输入** | `assets/backend/1004/Server` + `Cloud` |
| **2** | **项目恢复的 catalog** | `MarketplaceSkus.json` |
| **3** | **backend 可变状态** | `1004/<UID>/` 的 profile/inventory/wallet/identity |
| **4** | **首次迁移种子** | 根 `Identity.json` |
| **5** | ★ 客户端兼容插件 | `Ayria/Assets/Platformwrapper`（**不属 backend**） |

### ★★★ 三个不属于 live 的（第 113 行）

```markdown
`CODOLBackend/`、profile `.bak` 和 `Publicprofile-test` 不属于 live asset contract，
前者确认无消费者后移出运行目录，后两者作为不可再生测试快照归档而不由 installer 管理。
```

★ **⇒ `CODOLBackend/` / profile `.bak` / `Publicprofile-test` 都不属于 live。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ Backend 职责 | **Auth3 / LSG / service-task / publisher storage / 持久化 / 房间消息 / matchmaking / booking** |
| 2 | ★ Backend 不负责 | **地图模拟 / `SV_Frame` / GSC / 实体 / snapshot** |
| 3 | ★★★ 当前拓扑 | `role=client` ⇒ 依附客户端进程；**尚未成为独立 daemon** |
| 4 | ★★★★★ **三层身份** | **显示名（backend）** / **sessionKey+userId（task28）** / **platform ID（tag22）** |
| 5 | 显示名要求 | **1–16 字节 printable ASCII**，非法 **fail closed** |
| 6 | ★★★ **ASCII vs 中文冲突** | `backend.md` 要 ASCII，`fake_auth_tls.py` 支持中文 ⇒ **不一致** |
| 7 | ★★★ platform ID | **`0x01100001DEADC0DE`**（full）/ **`0xDEADC0DE`**（room internal） |
| 8 | ★★★★★ **14 步链路** | room → `0x0B` → event8 → ready → `0x15/5` → `0x06/14` mmbook → event21 → mmstart → BookingSink → dispatcher → capture → entitlement → SessionStart → dedicated |
| 9 | ★★ query kind | **`1`=FIND_SERVERS / `3`=FIND_LOBBIES_BY_PLAYLIST** |
| 10 | ★★ `BookingSink` 边界 | 只是**排队**；gamestate 在**后续 Com_Frame** |
| 11 | ★★★ **重试策略** | **1.5 秒窗口** + **最多 3 次** + 协议错误**立即失败** |
| 12 | ★★★ **entitlement 两源** | **持久 inventory** + **`DefaultAvailableItems_Init 0x7052F0`** |
| 13 | entitlement 查询 | **`CODOL_ItemAvailability_Query 0x695BC0`** |
| 14 | ★ 固定拒绝 | 过期 / 零数量 / 未知 item |
| 15 | ★★★ 多客户端三障碍 | 每进程独立 / `LobbyServer` 独占 / **`AuthSession` 只存一个身份** |
| 16 | ★★★ **`SharedRoomSessionOwner`** | 按 **XUID** + **connection token** + **全部 ready 才 freeze** |
| 17 | ★★★ token 机制 | 重连 ⇒ 新 token；**旧事件不能修改新登录** |
| 18 | ★ 幂等 | 同一 generation 重复 freeze ⇒ **首次快照** |
| 19 | 端口 | **`28970`**（`OLMOD_ROOM_OWNER_PORT`） |
| 20 | ★★ 五类资产 | 不可变 publisher / catalog / 可变状态 / 迁移种子 / 客户端插件 |

---

## 九、结论

### 1. ★★★★★ **三层身份所有权**是本报告最重要的发现

```
显示名    →  backend PlayerIdentityStore（1-16 ASCII）
sessionKey →  客户端 task 28 请求
platform ID →  ol_platformwrapper 的 Tencent tag 22
```

★★★ **⇒ 三者**互不替代**，且各自有明确的权威来源。**

### 2. ★★★★★ **发现一处不一致：ASCII vs 中文**

```
backend.md        :  1-16 字节 printable ASCII
fake_auth_tls.py  :  只丢控制字符（支持中文）
        ↓
★ 若 backend 严格校验，中文名会被**拒绝**
```

### 3. ★★★ **`0xDEADC0DE` vs `1100001DEADC0DE` 也需核实**

### 4. ★★★★★ **14 步 Ready→Booking 链路**已完全定案

### 5. ★★★★ **`SharedRoomSessionOwner` 的 connection token 机制**是关键的重连安全设计

### 6. ★★★ **entitlement 只有两类来源**（inventory + 默认集合），secure unlock 未实现

---

## 十、下一步

- `backend.md` 剩余（第 120 行起，约 100 行）
- `source\.agents\modules\game_server.md`（223 KB）
- `source\docs\devlog\`（中文开发历程）
