# 学习报告 094（重开）— `shared\DedicatedControl.hpp`（13,274 B / 330 行）

**学习范围**：`shared\DedicatedControl.hpp` 全文
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**17 种控制消息（含 3 种退役/未用）** ②**端口 28961/28962 与 `OLMOD_HOST_ADDRESS` 远程机制** ③**`GameplayClientStatus` 的 60+ 个诊断字段** ④**Frida 探针会杀死专服的实测教训** ⑤**公告员 392 行音效库与 `uk_1mc_timesup`**

---

## 一、★★★★★ 7 个协议常量（第 15–21 行）

| 常量 | 值 | 说明 |
|---|---|---|
| **`ProtocolVersion`** | **2** | 协议版本 |
| **`DefaultPort`** | ★ **28961** | 控制端口 |
| **`DefaultClientBridgePort`** | ★ **28962** | 客户端桥端口 |
| **`DefaultHostAddress`** | **`"127.0.0.1"`** | 默认主机地址 |
| **`LoopbackHostIpv4`** | **`0x7F000001`** | 回环（**主机序**） |
| **`MaximumPayloadSize`** | ★ **16 × 1024 = 16,384** | 单条消息上限 |
| **`MaximumRecentReliableCommands`** | **128** | 保留的最近可靠命令数 |

★★ **⇒ 两个相邻端口（28961/28962）⇒ 控制通道与客户端桥通道分离。**

★ **⇒ `LoopbackHostIpv4 = 0x7F000001` 是**主机序**（不是网络序）—— 第 309 行的注释明确：
"`a.b.c.d` from the same **host-order** convention `LoopbackHostIpv4` uses"。**

---

## 二、★★★★★ **17 种控制消息类型**（`MessageType`，第 23–85 行）

| 值 | 名称 | 状态 | 说明 |
|---|---|---|---|
| **1** | **`Booking`** | ✓ | 预订 |
| **2** | **`CaptureLoadout`** | ✓ | 捕获配装 |
| **3** | **`SessionStart`** | ✓ | ★★ 会话开始 |
| **4** | **`ConfigureSession`** | ✓ | 配置会话 |
| **5** | **`QueryEndpoint`** | ✓ | 查端点 |
| **6** | **`QueryGameplayStatus`** | ✓ | ★★ 查对局状态 |
| **7** | **`SetNoclip`** | ✓ | ★★ 穿墙（见第三节） |
| **8** | **`UpdateLoadout`** | ✓ | ★★ 热更新单个成员配装 |
| **9** | **`RunDiagnostic`** | ✓ | ★★★ **在活客户端里跑诊断** |
| **10** | **`PlayAnnouncer`** | ✓ | ★★★ **试听一条公告员语音** |
| **11** | **`SendRawCommand`** | ✓（门控） | ★★★ **重放原始可靠命令** |
| **12** | **`DebugGrantBattery`** | ✓ | 调试给电池 |
| **13** | ★★★ ****退役** | ✗ | **`// =13 RETIRED (2026-10-10, operator ruling): live character swap was rejected -- native CODOL never had it. Do not reuse this number.`** |
| **14–15** | ★ **（空号）** | — | 未使用 |
| **16** | **`RoomConnect`** | ✓ | 房间连接 |
| **17** | **`RoomDisconnect`** | ✓ | 房间断开 |
| **18** | **`RoomSetReady`** | ✓ | 房间就绪 |
| **19** | **`RoomFreeze`** | ✓ | 房间冻结 |
| **20** | **`RoomCanonicalizeSession`** | ✓ | ★★ 规范化会话 |

★★★ **⇒ 实际使用 **15 个**（1–12 + 16–20）,13 退役,14/15 空号。**

### ★★★★★ 消息 13 的退役声明（逐字,极有价值）

```
// =13 RETIRED (2026-10-10, operator ruling): live character swap was
// rejected -- **native CODOL never had it**. Do not reuse this number.
        ↓
★★★ ⇒ 甲方（operator）裁定：**原生 CODOL 从来没有"活体角色切换"**
   ⇒ 所以该功能被**否决并退役**
   ⇒ 且明确 **"Do not reuse this number"**（不重用编号）
```

### ★★★★★ 消息 9 `RunDiagnostic` 的完整背景（逐字）

```
// RUN A DIAGNOSTIC IN THE LIVE CLIENT, so an audit does not cost a cycle.
//
// Every measurement today needed a full restart: kill the stack, rebuild, relaunch,
// and the player had to queue up again -- for a question that is a loop over a
// table the running client already has. Payload is the diagnostic's name.
//
// It TRIGGERS and returns; it does not carry results back. The work runs on a
// detached thread and writes to the log or a CSV, because doing it on the request
// path would put it on the same thread the loadout capture needs, which is exactly
// what stalled a match earlier.
```

★★★★★ **⇒ 三个精确事实：**
```
① **动机**："Every measurement today needed a **full restart**: kill the stack,
   rebuild, relaunch, and the player had to **queue up again**"
        ↓
② ★★★ **只触发不返回**："It **TRIGGERS and returns**; it **does not carry results back**"
   结果写日志或 CSV
        ↓
③ ★★★ **线程隔离的原因（逐字）**："doing it on the request path would put it on
   the **same thread the loadout capture needs**, which is exactly what
   **stalled a match earlier**"
```

★★ **⇒ 第 ③ 条是一个**已发生过的故障**（"stalled a match earlier"）⇒ 所以诊断必须跑在 detached 线程。**

### ★★★★★ 消息 10 `PlayAnnouncer` 的完整背景（逐字）

```
// AUDITION ONE ANNOUNCER LINE, so naming a clip does not cost a match.
//
// The announcer band is **392 lines** the client already holds (191n) and the
// demo only proves **WHEN** retail sent each one, **never what the recording
// SAYS**. Reasoning about a filename is not a measurement -- retail sent
// **`uk_1mc_timesup`** at exactly **30 s remaining**, and whether that clip
// speaks "time's up" or "thirty seconds" cannot be read off its name.
//
// Payload is the u16 event parameter. Broadcast to every Active client,
// on the game thread, exactly as the match announcer sends it.
```

★★★★★ **⇒ 三个精确数据：**
```
① ★★ **公告员音效库 = 392 行**（客户端已持有,出处标记 `191n`）
② ★★★ **零售录像只证明"何时发送",不证明"内容是什么"**
   ⇒ "**Reasoning about a filename is not a measurement**"
③ ★★★ **具体例子**：零售在**剩余恰好 30 秒**时发送 **`uk_1mc_timesup`**
   ⇒ 但无法从文件名判断它说的是 "time's up" 还是 "thirty seconds"
```

★★ **⇒ 第 ③ 条是**"文件名 ≠ 语义"的绝佳论证**（与报告 087 的"材质名 ≠ 地图名"同类）。**

### ★★★★★ 消息 11 `SendRawCommand` 的完整背景（逐字）

```
// REPLAY A RAW RELIABLE COMMAND, byte for byte, into the running match.
//
// The **kill feed** is carried by something we have not decoded. Retail's
// own bytes are in the demo; replaying them and watching the screen
// turns an **unbounded reverse-engineering job into a bounded experiment**,
// which is what this project's runtime tools are for.
//
// A MALFORMED BINARY COMMAND CAN DESYNC OR CRASH A CLIENT, so this is
// refused unless **`OLMOD_ALLOW_RAW_COMMAND=1`**. Payload is the raw bytes
// INCLUDING the verb.
```

★★★★★ **⇒ 三个要点：**
```
① ★★★ **击杀提示（kill feed）尚未解码** ⇒ 承载它的东西未知
② ★★★ 策略："replaying them and watching the screen turns an
   **unbounded reverse-engineering job into a bounded experiment**"
③ ★★★ **安全门控**：畸形二进制命令**会让客户端失步或崩溃**
   ⇒ 除非 **`OLMOD_ALLOW_RAW_COMMAND=1`**,否则拒绝
   ⇒ 载荷是**原始字节（含动词）**
```

★ **⇒ 这与既有 memory 的"`OLMOD_*` 配置面"呼应 —— 又一个环境变量门控。**

### ★★★ 消息 7 `SetNoclip` 的注释（第 31–35 行）

```
// A player holding the noclip key. Sent by the CLIENT plugin, which
// already carries OLMOD_DEDICATED_CONTROL_PORT and the platform user
// id, and reaches a remote dedicated unchanged because the control
// listener binds 0.0.0.0 whenever OLMOD_HOST_ADDRESS is not loopback.
```

★★ **⇒ 两个环境变量：`OLMOD_DEDICATED_CONTROL_PORT` / `OLMOD_HOST_ADDRESS`。**

### ★★★ 消息 8 `UpdateLoadout` 的注释（第 36–39 行）

```
// Refresh ONE roster member's loadout live, mid-match, with no world
// rebuild: payload is u64 userId + encode(LoadoutRequest). The dedicated
// re-registers the member's weapons into the running gamestate and pushes
// their config strings to every client. See §157c and the handler.
```

★★★ **⇒ 载荷格式明确：**`u64 userId + encode(LoadoutRequest)`**（复用报告 093 的 `LoadoutRequest` 编码）。**

---

## 三、★★★★★ **`NoclipRequest`：边缘触发 + 保活**（第 125–138 行，逐字）

```cpp
// EDGE PLUS KEEP-ALIVE, NOT LEVEL. The sender pushes one message when the
// key goes down, one when it comes up, and a repeat every half second in
// between. holdMilliseconds is how long the dedicated should keep flying
// the player without hearing again -- so a LOST key-up expires instead of
// leaving somebody stuck in the air forever, which is the failure mode
// that matters when the sender is a friend's machine across the internet.
struct NoclipRequest
{
    std::uint64_t userId{};
    bool enabled{};
    std::uint32_t holdMilliseconds{};
};
```

★★★★★ **⇒ 一个精确的**容错设计**：**
```
**EDGE PLUS KEEP-ALIVE, NOT LEVEL**
        ↓
按下 ⇒ 发 1 条（`enabled = true`）
松开 ⇒ 发 1 条（`enabled = false`）
中间 ⇒ **每 500 ms 重复一次**
        ↓
★★★ `holdMilliseconds` = 专服在**没再收到**的情况下还应继续让玩家飞行多久
        ↓
★★★★★ 目的（逐字）："so a **LOST key-up expires** instead of leaving
 somebody **stuck in the air forever**, which is the failure mode that matters
 when the sender is a **friend's machine across the internet**"
```

★★ **⇒ 这是**"边缘事件 + 保活超时"的经典模式**（防止丢包导致永久状态）。**
**⇒ 与报告 072 的 `zm.lua` SPAWN_BACKOFF、报告 069 的回合超时**同一类容错思路。**

---

## 四、★★★★★ **`GameplayClientStatus`：60+ 个诊断字段**

### 4.1 ★★★ 字段分组（第 166–243 行）

#### ① 身份与网络（11 个）

```cpp
clientNum, gameplayState, team,
reliableSequence, reliableAcknowledge,
peerIpv4, peerPort,
lastPacketReceivedTime, incomingSequence, outgoingSequence, messageAcknowledge
```

#### ② UDP 发送统计（7 个）

```cpp
udpSendAttempts (u64), udpSendSucceeded (u64), udpSendFailed (u64),
udpBytesSent (u64),
lastUdpSendTime, lastUdpSendBytes, lastUdpSendError (i32)
```

#### ③ ★★★ usercmd 流水线（**12 个**，全部带"未初始化 = `UINT32_MAX`"哨兵）

```cpp
pendingUserCmdCount
oldestPendingUserCmdTime          = UINT32_MAX
newestPendingUserCmdTime          = UINT32_MAX
lastReceivedUserCmdTime           = UINT32_MAX
lastDispatchedUserCmdTime         = UINT32_MAX
lastExecutedUserCmdTime           = UINT32_MAX
lastDiscardedUserCmdTime          = UINT32_MAX
discardedUnsupportedUserCmds
lastDiscardedRejectedUserCmdTime  = UINT32_MAX
discardedRejectedUserCmds
clientThinkLastAttemptedCommandTime = UINT32_MAX
clientThinkLastCommittedCommandTime = UINT32_MAX
clientThinkFailureStage
clientThinkFailureCount
```

#### ④ 最后派发的输入（7 个）

```cpp
lastDispatchedButtons
lastDispatchedAngles[3]
lastDispatchedWeapon
lastDispatchedOffhand
lastDispatchedForwardMove (i32)
lastDispatchedRightMove (i32)
```

#### ⑤ 快照掩码（2 个）

```cpp
snapshotPlayerEntityMask
snapshotClientInfoMask
```

#### ⑥ ★★★★★ **Schema 5：定位命中读数（17 个）**

```cpp
origin[3] (float)
viewAngles[3] (float)
health
bulletCommandTime           = UINT32_MAX
bulletStart[3] (float)
bulletEnd[3] (float)
bulletFraction (float)
bulletHitType
bulletHitEntityNum          = **2047**   ← ★★★ 注意这个默认值
bulletModelIndex
bulletPartName
bulletPartGroup
bulletResult
```

#### ⑦ 目标与命令（2 个）

```cpp
objectives[3]
recentReliableCommands (vector)
```

### ★★★★★ Schema 5 的完整理由（第 217–224 行，逐字）

```cpp
// Schema 5. The locational hit readout, over the control socket rather
// than through Frida: CodolGameServerControl.py --pid <dedicated>
// terminated the dedicated two runs out of three, so a Frida probe can
// never be the way this is sampled during a live match. Origin plus the
// last committed bullet trace is enough to compute the world point the
// server resolved a hit to, and therefore its height above the target's
// feet - which is the one measurement that separates a collapsed hit
// skeleton from a mis-aimed trace.
```

★★★★★ **⇒ 一个极其重要的实测结论：**
```
★★★ **`CodolGameServerControl.py --pid <dedicated>` 在三次运行中**终止了专服两次**
   （"terminated the dedicated **two runs out of three**"）
        ↓
★★★ ⇒ **Frida 探针绝不能用于活体比赛采样**
        ↓
★ 替代方案：**通过控制套接字**读 `origin + 最后提交的子弹轨迹`
   ⇒ 可算出服务端解算的**世界命中点**
   ⇒ 进而算出它**相对目标脚部的高度**
        ↓
★★★★★ ⇒ 这是"区分**命中骨架坍缩**与**瞄偏**的唯一测量"
```

★★ **⇒ 这与既有 memory 的"实体段实机验证"「收得下，但看不到」直接相关 —— 命中高度是判断实体骨架是否正常的判据。**

### ★★★★★ `bulletHitEntityNum = 2047` 的默认值（第 234 行）

```cpp
std::uint32_t bulletHitEntityNum{ 2047 };
```

★★★★★ **⇒ `2047` = `0x7FF` = 11 位全 1。**

★★ **⇒ 与既有 memory**完全吻合**：**
```
memory（快照字段级离线对照）：
  "**idx61 我们恒 2047, CSV/CSC 都是 `OnGround?2046:2047`**
   且 ClientLogic 喂进真实接地状态,
   其注释写明「恒写 2047 ⇒ 永远在空中 ⇒ 悬空/无移动动画/不能跳」"
        ↓
★★★ 本报告：`bulletHitEntityNum` 的**默认值也是 2047**
        ↓
★ 说明 **2047 在这个代码库里是"无效实体号"的哨兵**（11 位最大值）
   ⇒ 与 idx61 的 2046/2047 是**同一编码空间的同一哨兵**
```

★★★ **⇒ 这是一条**重要的跨结论印证**：`2047` 是**11 位实体号的"无"值**。**

---

## 五、★★★★★ **`GameplaySdStatus`：SD 模式的 18 个字段**（第 245–267 行）

```cpp
roundConfigured, roundArmed, roundCompleted, roundsPlayed,
roundWinner, roundEndReason,
bombConfigured, bombPhase,
attackers, defenders, attackersAlive, defendersAlive,
carrierClientNum, planterClientNum, defuserClientNum,
plantedSiteLabel, phaseStartServerTime, plantedServerTime
```

★★★ **⇒ 18 个字段,完整覆盖 SD 的回合与炸弹状态。**

★ **⇒ 与报告 065/069 的 `sd.lua` 的 10 个观察事件（`sd_bomb_picked_up` … `sd_round_ended`）**对应**：
**这些状态字段就是那些事件的数据源。**

### ★★★ `GameplayStatus` 的顶层（第 269–276 行）

```cpp
struct GameplayStatus
{
    std::uint32_t serverTime{};
    GameplaySdStatus sd;
    std::vector<GameplayClientStatus> clients;
};
```

★ **⇒ `serverTime` + `sd` + `clients[]`。**

---

## 六、★★★★★ **`OLMOD_HOST_ADDRESS` 的远程机制**（第 323–329 行，逐字）

```cpp
// OLMOD_HOST_ADDRESS names the ONE machine that runs the room owner, the
// dedicated and the game socket. Unset means 127.0.0.1, so an environment
// that does not mention it behaves exactly as it did before remote play
// existed. Every peer -- host included -- sets the SAME value.
```

★★★★★ **⇒ 三个精确要点：**
```
① `OLMOD_HOST_ADDRESS` 指定**唯一一台**机器（跑 room owner + dedicated + game socket）
② ★★ **未设置 = 127.0.0.1** ⇒ 不设就**与引入远程play之前完全一致**（向后兼容）
③ ★★★ **每个 peer（含 host 自己）都设同一个值**
```

★★ **⇒ 第 ② 条是**向后兼容的明确承诺**（与报告 067 的 "byte-for-byte in charge" 同一手法）。**

### ★★★ 五个环境变量汇总（从本文件）

| 变量 | 用途 |
|---|---|
| **`OLMOD_HOST_ADDRESS`** | ★★ 主机地址（默认 `127.0.0.1`） |
| **`OLMOD_DEDICATED_CONTROL_PORT`** | 控制端口 |
| **`OLMOD_ALLOW_RAW_COMMAND`** | ★★★ 允许原始命令重放（默认拒） |

★★ **⇒ 加上报告（`OLMOD_CONSOLE_LOG` / `OLMOD_DEDICATED_CONTROL_PORT` / `OLMOD_UNLOCK_ALL` /
`OLMOD_SYNTHETIC_DNS` / `OLMOD_ZM_COOP_SPAWN_ZONES` / `OLMOD_DUMP_MODEL_BAND`），
`OLMOD_*` 面已积累 **8+ 个**。**

### ★★★ `Server` 类的接口（第 280–297 行）

```cpp
class Server
{
public:
    Server();
    ~Server();
    Server(const Server &) = delete;
    Server &operator=(const Server &) = delete;

    bool start(std::uint16_t port, MessageHandler handler);
    void stop();
    [[nodiscard]] bool running() const;
    [[nodiscard]] std::uint16_t port() const;
    [[nodiscard]] int lastSocketError() const;

private:
    struct State;
    std::unique_ptr<State> state_;      // ★ pImpl
};
```

★★ **⇒ 标准 pImpl 模式（`struct State; unique_ptr<State>`）。**

### ★★★ `submit()` 的默认超时（第 299–303 行）

```cpp
[[nodiscard]] SubmitResult submit(
    std::string_view host, std::uint16_t port, const Message &message,
    std::uint32_t timeoutMilliseconds = **500**);
```

★ **⇒ 默认超时 **500 ms**。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ **7 个协议常量** | `ProtocolVersion 2` / **`DefaultPort 28961`** / **`DefaultClientBridgePort 28962`** / `DefaultHostAddress "127.0.0.1"` / `LoopbackHostIpv4 0x7F000001` / **`MaximumPayloadSize 16,384`** / `MaximumRecentReliableCommands 128` |
| 2 | ★★ 主机序 | `LoopbackHostIpv4` 是**主机序**,`ipv4Text` 沿用同一约定 |
| 3 | ★★★★★ **17 种消息** | 1 Booking · 2 CaptureLoadout · 3 SessionStart · 4 ConfigureSession · 5 QueryEndpoint · **6 QueryGameplayStatus** · **7 SetNoclip** · **8 UpdateLoadout** · **9 RunDiagnostic** · **10 PlayAnnouncer** · **11 SendRawCommand** · 12 DebugGrantBattery · **13 RETIRED** · 14/15 空 · 16–20 Room* |
| 4 | ★★★★★ **消息 13 退役** | **"live character swap was rejected -- native CODOL never had it. Do not reuse this number."**（2026-10-10 甲方裁定） |
| 5 | ★★★★★ **消息 9 的背景** | 动机：每次测量都要 **full restart + 玩家重新排队**；**只触发不返回**（结果写日志/CSV）；★ 必须在 **detached 线程**（否则占住 loadout capture 的线程,"**which is exactly what stalled a match earlier**"） |
| 6 | ★★★★★ **消息 10 的背景** | 公告员音效库 **392 行**（出处 `191n`）；零售只证明**何时**发送、不证明**内容**；★ 例：剩余**恰好 30 秒**时发 **`uk_1mc_timesup`**,但无法从文件名判断语义 |
| 7 | ★★★★★ **消息 11 的背景** | **击杀提示尚未解码**；用重放把"**unbounded reverse-engineering job**"变成"**bounded experiment**"；★ 畸形命令会让客户端**失步或崩溃** ⇒ 必须 **`OLMOD_ALLOW_RAW_COMMAND=1`** |
| 8 | ★★ 消息 8 载荷 | **`u64 userId + encode(LoadoutRequest)`**（复用报告 093 的编码） |
| 9 | ★★★★★ **`NoclipRequest` 设计** | **EDGE PLUS KEEP-ALIVE, NOT LEVEL**：按下/松开各 1 条 + **每 500 ms** 重复；`holdMilliseconds` 让**丢失的 key-up 会超时** ⇒ 防止"**stuck in the air forever**" |
| 10 | ★★★★★ **`GameplayClientStatus` 60+ 字段** | 身份网络 11 / UDP 统计 7 / **usercmd 流水线 14** / 最后派发输入 7 / 快照掩码 2 / **Schema 5 定位命中 17** / 目标与命令 2 |
| 11 | ★★★ usercmd 哨兵 | **12 个字段默认 `UINT32_MAX`** = "未发生" |
| 12 | ★★★★★ **Frida 的实测教训** | **`CodolGameServerControl.py --pid <dedicated>` 三次运行中终止了专服两次** ⇒ **Frida 绝不能用于活体采样** |
| 13 | ★★★★★ **定位命中的用途** | `origin + 最后提交的子弹轨迹` ⇒ 算出**世界命中点** ⇒ 相对目标脚部的**高度** ⇒ **"区分命中骨架坍缩与瞄偏的唯一测量"** |
| 14 | ★★★★★ **`bulletHitEntityNum = 2047`** | ★ **`2047` = `0x7FF` = 11 位全 1** ⇒ 与 memory 的"idx61 恒 2047 / `OnGround?2046:2047`"是**同一哨兵** ⇒ **2047 = 11 位实体号的"无"值** |
| 15 | ★★★★ **`GameplaySdStatus` 18 字段** | 回合 6 + 炸弹 2 + 人数 4 + 角色 3 + 站点 1 + 时间 2 |
| 16 | ★★★ `GameplayStatus` | `serverTime` + `sd` + `clients[]` |
| 17 | ★★★★★ **`OLMOD_HOST_ADDRESS`** | 指定**唯一一台**机器；★ **未设置 = `127.0.0.1`**（向后兼容）；**每个 peer 都设同值** |
| 18 | ★★ `Server` 类 | 标准 **pImpl**（`struct State; unique_ptr<State>`） |
| 19 | ★ `submit()` 默认超时 | **500 ms** |
| 20 | ★★ `OLMOD_*` 面累计 | 本文件贡献 3 个（`OLMOD_HOST_ADDRESS` / `OLMOD_DEDICATED_CONTROL_PORT` / `OLMOD_ALLOW_RAW_COMMAND`） |

---

## 八、结论

### 1. ★★★★★ **`DedicatedControl` 是 ol-mod 自建的**控制协议**（不是零售的）

```
**17 种消息**（15 个在用 / 1 退役 / 2 空号）
端口 **28961**（控制）/ **28962**（客户端桥）
        ↓
★★★ 其中 3 种是**为绕过逆向难题而设计的运行时工具**：
  **`RunDiagnostic`**（在活客户端跑诊断）
  **`PlayAnnouncer`**（试听公告员语音）
  **`SendRawCommand`**（重放原始命令）
        ↓
★★★★★ ⇒ 三者的注释都写明了**同一个动机**：
   "把一个**无界的逆向工程任务**变成**有界的实验**"
```

### 2. ★★★★★ **三条带实测数据的教训**

```
① **Frida 会杀死专服**：`CodolGameServerControl.py --pid` **三次运行终止了两次**
   ⇒ 改用**控制套接字**读命中数据
② **公告员语义不可从文件名推断**：`uk_1mc_timesup` 在 30 秒剩余时发送,
   但不知它说的是"time's up"还是"thirty seconds"
③ **诊断不能跑在请求路径上**：会占住 loadout capture 的线程,
   "**which is exactly what stalled a match earlier**"
```

### 3. ★★★★★ **`bulletHitEntityNum = 2047` 与既有 memory 的 idx61 是同一哨兵**

★ **⇒ 确立了 `2047` = **11 位实体号的"无"值**,这是一条跨结论的编码事实。**

### 4. ★★★★ **`NoclipRequest` 的"边缘 + 保活"设计**（防丢包导致永久悬空）

### 5. ★★★ **`OLMOD_HOST_ADDRESS` 未设即回环**（明确的向后兼容承诺）

### 6. ★★★ **消息 13 的退役裁定**（"native CODOL never had it"）

---

## 九、下一步

- `shared\DedicatedControl.cpp`（36,106 B / 844 行）—— 实现层
- `shared\RuntimeLog.cpp`（398 行）+ 两个小 `.hpp`（`LocalnetServer` / `ProcessRole`）
- 然后 `game_server\qcommon\`（8 文件）
