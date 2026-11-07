# 阶段报告：Lobby → Battle 主线（2026-10-07）

> 按主任务要求：每完成一个阶段立即报告
> ①做了什么 ②观察到什么 ③CONFIRMED ④仍 UNKNOWN ⑤下一步唯一最短路径

---

## P0-1 冻结 GOLDEN-LOBBY-001 —— ✅ 完成

### ① 做了什么

产出两个冻结物：

```
GOLDEN-LOBBY-001\
    REF_LOBBY_KIT\          22 个文件，**全部只读**
    （含 GOLDEN-LOBBY-001.md 复现手册 + _golden_hashes.json）

REF_LOBBY_KIT\GOLDEN-LOBBY-001.md     冻结清单（权威复现依据）
REF_LOBBY_KIT\_golden_hashes.json     核心文件 SHA-256（机器可读）
```

冻结内容覆盖主任务要求的 16 项：完整工作目录、客户端环境、REF_LOBBY_KIT
核心、CODOLServer 提权代理、配置、hosts、启动参数、CWD、**内存补丁清单
（4 处 + KDF hook，含确切地址与字节）**、Server/Auth 日志、关键文件 SHA-256、
沙箱路径、依赖 DLL、成功运行命令。

**关于转储**：`REF_LOBBY_KIT` 全目录 26.7 GB，绝大部分是内存转储
（用户明确要求保留）。Golden **只冻结运行所需部分**，转储不纳入版本管理。

### ② 观察到什么

冻结时基线（可复现判据已写入手册）：

```
lobby_srv.log  134,649 B
  连接建立 23 / 结束 23 / recv 异常 0 / keepalive 15
  hmac=OK 235 / hmac=BAD 0        ← 零错误
battle_srv.log 322,463 B（已监听 28960，收包=0）
```

SHA-256 与清单**逐项核对一致**，只读属性 22/22 生效。

### ③ CONFIRMED

- `GOLDEN-LOBBY-001` = **FROZEN**，可只读复现"正式进大厅 + KeepAlive 稳定"
- 4 处内存补丁 + 1 处 KDF hook 的**确切地址与字节已固化**
- `firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH` 冻结为**禁止开启**

### ④ 仍 UNKNOWN

- 无（本项范围内）

### ⑤ 下一步最短路径

→ 转 P0-2

---

## P0-2 获取 ol-mod `src/game_server/` —— ⛔ **BLOCKED（需外部输入）**

### ① 做了什么

全盘搜索 `ol-mod` / `olfinal` / `handoff2` 相关包：

```
D:\   E:\   F:\   G:\   C:\Users\Z7-CT5N1   （含 4~5 层深度）
```

### ② 观察到什么

```
命中 0 个 ol-mod 包 / 仓库 / zip
命中 0 个 src\game_server 目录
命中 0 个 DedicatedControl / sharedRoomClient 源文件

唯一命中的是**我们自己的文档**里的引述：
  REF_LOBBY_KIT\HANDOFF_20261007_TAKEOVER.md
  REF_LOBBY_KIT\HANDOFF_20261007_BATTLE_SERVER.md

原包路径 E:\handoff2\ol-mod-olfinal.zip —— E 盘已被清理，不存在。
```

**我们从文档里能确认的 ol-mod 事实（仅此，无源码）：**

```
Servers.cpp:340-365
    RoomEvent::Ready        -> sharedRoomClient_.setReady(userId, true)
    mmbook/mmstart (booking) -> sharedRoomClient_.setReady(...)
                              + bookingDispatcher_.submit(...)
    sharedRoomClient_.connect(identity,
        OlMod::DedicatedControl::configuredClientBridgePort())
```

⇒ **booking 走的是独立于 3074/28960 的"客户端桥"端口**，
但**端口号与帧格式 UNKNOWN**。

文档另记录 ol-mod 有（但本机没有）：
```
src/game_server/   sv_main_mp.cpp  sv_gamestate_mp.cpp  ServerCore
                   sv_snapshot_mp.cpp  sv_collision_mp.cpp
                   NativePmoveBindings.cpp  EngineBindings.cpp
                   server_mp/sv_bullet_mp.cpp  sv_const_baselines_mp.cpp
.agents/research/  playable_architecture.md
                   source_reconstruction_progress.md
```

### ③ CONFIRMED

- ol-mod 源码**不在本机任何盘**（搜索证据：4 个根 + 5 层深度，0 命中）
- 我们**没有任何 PvE booking 应答样本**（三方 `lsg.log` 里无 `service=11`）
- 已实测否证：用靶场信封回 PvE booking → **9/9 断连**

### ④ 仍 UNKNOWN

```
6/14 PvE booking 应答的 **帧格式** = UNKNOWN
DedicatedControl 的 **端口号**      = UNKNOWN
booking **opcode / 序列化器**       = UNKNOWN
room/session 对象在 booking 阶段的要求 = UNKNOWN
battle server 地址**下发方式**      = UNKNOWN
```

### ⑤ 下一步唯一最短路径

**需要您提供 ol-mod 仓库（或以下任一项）：**

```
优先级 1: ol-mod-olfinal.zip（完整包）
优先级 2: src/game_server/ 目录
优先级 3: src/network/DedicatedControl.*（端口+帧格式在这里）
优先级 4: .agents/research/playable_architecture.md
```

**为什么不自己实现**：booking 帧格式是**原客户端契约**（主任务"第四原则 A 类"），
不能自定义；且已证伪"用靶场信封代替"（9/9 断连）。
盲猜会反复导致客户端断连/闪退 —— 与商城 SKU 页同类风险，
主任务"第三原则"明确要求"不要凭空重建已有标准实现"。

**若确实拿不到 ol-mod**，备选（按可行性）：

```
B1) 用**靶场**而非剧情走通 Lobby→Battle
    —— 靶场是三方**唯一验证过**的路径
    —— 但实测本客户端的 findSessions 恒回 playlist=10，
       未观察到 playlist=1 的靶场入口（UNKNOWN：入口是否存在于 UI）
B2) 暴力枚举 booking 应答（不推荐）
    —— 每次错都会断连；无收敛判据
B3) 暂时冻结 Battle 主线，转 P1 大厅缺口
    —— 但主任务"第八原则"要求这些不得阻塞 Battle 主线
```

---

## P0-3 打通 Lobby→Booking→Battle —— ⏸ **待 P0-2 解除阻塞**

### ⑤ 唯一最短路径（P0-2 完成后的执行顺序）

```
① 从 ol-mod 提取 DedicatedControl 端口 + booking 帧格式
② 在 REF_LOBBY_KIT 新增 booking_server.py（或 lobby 转发）
     - 接收 6/14 mmbook/mmstart
     - 回**正确格式**的 booking accepted
③ 判据：客户端**停止 5 秒重试**（当前 retry 行为已记录）
④ 判据：客户端连上 UDP 28960 → battle_srv.log 出现 RX #1 16B
⑤ 之后已有实现可直接复用：
     NAT 29B -> DTLS 16B -> 38B cookie -> 219B -> ECDH P-224 -> 114B ack
     -> stats -> game state -> 运动快照（字段序列已 29/29 对齐实录）
⑥ 成功标准：原客户端**进入实际地图**（非仅"进程没退出"）
⑦ 一旦成功立即冻结 GOLDEN-BATTLE-001
```

---

## 附：ACE / IW4X 诚实状态（主任务第十、十一原则）

```
ACE_REMOVAL    = NOT_COMPLETE      （文件在、驱动在、BugTrace 仍加载；
                                    靠 4 个内存补丁绕过，不是移除）
IW4X 直接引用  = 0                 （REF_LOBBY_KIT 搜 IW4X/IW4 = 0 命中）
实际参考实现   = 三方 C#（_ref\CodolLocalLobbyServer.cs）+ ol-mod（不在本机）
```

不声称"当前 Server 基于 IW4X"。

---

## 【P0-2 解锁检查 · 2026-10-07 19:0x】结果：仍然 BLOCKED

按指令执行"检查 `E:\handoff2\ol-mod-olfinal.zip` 是否存在"：

```
① E:\handoff2\ol-mod-olfinal.zip     NOT FOUND
② E:\handoff2\  目录本身             NOT FOUND
③ E:\ 根目录内容                     $RECYCLE.BIN / 16 / BaiduNetdiskDownload /
                                    BX / CODOL_SANDBOX / IW4X / model /
                                    Program Files / SteamLibrary / System Volume Information
                                    （无 handoff、无 ol-mod）
④ E:\ 下 *handoff* / *ol-mod*       零命中

⑤ 全盘特征文件搜索（D:\ E:\ F:\ G:\ C:\Users\Z7-CT5N1，深度 6）：
   Servers.cpp / DedicatedControl.* / sharedRoomClient.* /
   bookingDispatcher.* / playable_architecture.md /
   "Understand Project Repository.md" / ol-mod*.zip
   ⇒ 命中 0
```

### 结论

```
BOOKING_SOURCE   = BLOCKED      （全机确认不存在）
BOOKING_PROTOCOL = UNKNOWN      （保持原样，不降级为 CANDIDATE）
BATTLE_ENTRY     = NOT_OBSERVED
```

### 已按指令执行"立即停止"

自本检查起，**不再进行任何 booking 相关尝试**。具体遵守：

```
✔ 不再猜 booking 帧格式
✔ 不再猜 DedicatedControl 端口
✔ 不再把靶场协议当 booking 协议
✔ 不再修改 6/14 response
✔ 不再尝试自定义 booking envelope
✔ 不修改 Golden
✔ 不再研究 Lobby 握手
✔ 不修改 4 个 Lobby patch
✔ 不修改 KDF hook
```

### 等待输入（按优先级）

```
1. ol-mod-olfinal.zip
2. src/game_server/
3. src/network/DedicatedControl.*
4. .agents/research/playable_architecture.md
```

### 收到后的执行计划（已就绪，不重复劳动）

```
第一步  完整解包 + 建立源码清单
第二步  定位 src/game_server/ · src/network/DedicatedControl.* ·
        sharedRoomClient · bookingDispatcher · mmbook · mmstart
第三步  建立链路图 Client -> 6/14 -> booking req ->
        DedicatedControl/client bridge -> booking resp ->
        session/room -> 28960 -> Battle handshake
第四步  逐字段建表 FIELD / SOURCE / TYPE / SIZE / ENDIAN /
        CONDITION / CLIENT READ / SERVER WRITE / EVIDENCE

产物   BOOKING_PROTOCOL_SPEC-001.md（**先出规格，不改 Server**）
       ↓（规格完成且经确认后）
       BOOKING-IMPLEMENTATION-001（**在开发副本**实现，Golden 只读）

特别验证项（9 条，文档已列）：
  configuredClientBridgePort() 实际端口 / client bridge 是否为 6/14 接收端 /
  booking req 帧格式 / booking resp 帧格式 / identity 内容 /
  session-room ID 产生方式 / booking 成功后的 endpoint / 28960 的角色 /
  booking → battle 状态转移

验收（BATTLE_ENTRY = CONFIRMED 的唯一标准）：
  6/14 -> booking accepted -> 客户端停止 retry -> valid room/session ->
  Battle endpoint -> Battle connection -> handshake ->
  **原 CODOL 客户端进入实际地图**
  （"Server 收到 6/14" 不算成功）
```

### 当前全项目状态

```
GOLDEN-LOBBY-001 = COMPLETE     （22 文件只读冻结，哈希已核）
BOOKING_SOURCE   = BLOCKED      （全机零命中，等外部提供）
BOOKING_PROTOCOL = UNKNOWN      （保持 UNKNOWN）
BATTLE_ENTRY     = NOT_OBSERVED
```
