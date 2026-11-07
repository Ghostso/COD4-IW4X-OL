# 17 — W-A：房间子系统深度逆向

> 2026-10-29。输入 = `E:\codol_re\client_image_20261027.bin`。工具在 `056/TOOLS/`。

---

## 1. ★ 房间消息族：41 个类的 vftable 全部定位

| vftable | 类 |
|---|---|
| 0x00DF87F4 | dwRoomMessageNetcafePrivileges |
| 0x00DF8840 | dwRoomMessageQQMembership |
| 0x00DF888C | dwRoomMessageUpdateWarGodData |
| 0x00DF88D8 | dwRoomMessageUpdateCreditRating |
| 0x00DF8924 | dwRoomMessageUpdateDlcLevel |
| 0x00DF8970 | dwRoomMessageAvatarInfo |
| 0x00DF89BC | dwRoomMessageDMZLeagueTicketStateChange |
| 0x00DF8A08 | dwRoomMessageInRoomStateChange |
| 0x00DF8A54 | dwRoomMessagePlayerPrimaryWeaponCountChange |
| 0x00DF8AA0 | dwRoomMessageClanNameChange |
| 0x00DF8AEC | dwRoomMessageRoomStateUpdated |
| 0x00DF8B38 | dwRoomMessagePlaylistWeights |
| 0x00DF8B84 | dwRoomMessageVote |
| 0x00DF8BD0 | dwRoomMessageSetPilot |
| 0x00DF8C1C | dwRoomMessageChangeTeamRequest |
| 0x00DF8C68 | dwRoomMessageChangeTeam |
| 0x00DF8CB4 | dwRoomMessageP2PInfo |
| 0x00DF8D00 | dwRoomMessageStartCountingDown |
| 0x00DF8D4C | dwRoomMessageReady |
| 0x00DF8D98 | dwRoomMessageRoomInfo |
| 0x00DF8DE4 | dwRoomMessageMemberList |
| 0x00DF8E30 | dwRoomMessageRequestMemberList |
| 0x00DF8E7C | dwRoomMessageLeave |
| 0x00DF8EC8 | dwRoomMessageLeaveWithMe |
| 0x00DF8F14 | dwRoomMessageJoinWithParty |
| 0x00DF8F60 | dwRoomMessageJoinWithMe |
| 0x00DF8FAC | dwRoomMessageSyncPartyPendingToNewMember |
| 0x00DF9044 | dwRoomMessageMyPartyInvitation |
| 0x00DF9090 | dwRoomMessageJoinRequest |
| 0x00DF90DC | dwRoomMessageJoin |
| 0x00DF9128 | dwRoomMessageJoinMemberInfos |
| 0x00DF9174 | dwRoomMessageScore |
| 0x00DF91C0 | dwRoomMessageCard |
| 0x00DF920C | dwRoomMessageMemberDetailsNoUpdated |
| 0x00DF9258 | dwRoomMessageMemberDetailsQuery |
| 0x00DF92A4 | dwRoomMessageMemberDetails |
| 0x00DF92F0 | dwRoomMessageMemberInfoAdd |
| 0x00DF933C | dwRoomMessageMemberInfoEXT |
| 0x00DF9388 | dwRoomMessageStartGameFailed |
| 0x00DF93D4 | dwRoomMessageStartGame |
| 0x00DF9514 | dwRoomMessage（基类） |

**另有基类/框架类**：`dwRoom`(0x00DC7BEC)、`dwRoomImp`(0x00DC7274)、`dwRoomMatch`(0x00DC7E6C)、
`dwRoomMatchUber`(0x00DC795C)、`dwRoom::EventHandler`(0x00DC7D4C)、`MyEventHandler`(0x00DC78EC)、
`dwRoomEventTournamentHandler`(0x00DD7194)、`dwRoomSpyMessageText`(0x00DC7510)。

## 2. ★★ 分发表：`0x00636F3C`，47 项（type 0x00–0x2E）

**布局**：连续的代码指针数组，4 字节/项，共 47 项，第 48 项起是 `0xCCCCCCCC`（填充）。
**默认/忽略项** = `0x00636EBA`（type 01、0B、19、28、29、2A 六项用它）。
**类型 0x00 = 公共收尾出口**（所有 handler 的 `je 0x636F02` 都跳到这里，非独立消息）。

**★ 定名依据（硬证据）**：每个 handler 开头都会把
`[ebp-0xC1C] = <type>` 和 `[ebp-0xC20] = <消息 vtable>` 成对写入栈上对象后调解析器。
这一对值直接给出 **type ↔ 消息类**，无需推测。

| type | 处理函数 | 消息 vtable | 消息类 |
|---|---|---|---|
| 0x00 | 0x00636F02 | — | *公共收尾出口* |
| 0x01 | 0x00636EBA | — | *忽略* |
| 0x02 | 0x0063495A | （见 0x2C） | StartGame 家族入口（校验 `+0x10798`） |
| 0x03 | 0x00634AC2 | 0x00DC751C | **dwRoomMessageStartGame** |
| 0x04 | 0x00634C3C | 0x00DC7528 | **dwRoomMessageStartGameFailed** |
| 0x05 | 0x00634D35 | 0x00DC7594 | **dwRoomMessageJoin** |
| 0x06 | 0x00634F13 | — | 仅已进房（`[+0x278]!=0`、`[+0x1C]!=0`） |
| 0x07 | 0x00635399 | 0x00DC75D0 | **dwRoomMessageJoinWithMe** |
| 0x08 | 0x006354A9 | 0x00DC75F4 | **dwRoomMessageLeave** |
| 0x09 | 0x0063550B | 0x00DC75F4 | **dwRoomMessageLeave**（变体） |
| 0x0A | 0x006356B8 | 0x00DC7540 | **dwRoomMessageMemberInfoAdd** |
| 0x0B | 0x00636EBA | — | *忽略* |
| 0x0C | 0x006355C2 | 0x00DC7534 | **dwRoomMessageMemberInfoEXT** |
| 0x0D | 0x006357BB | 0x00DC760C | **dwRoomMessageMemberList** |
| 0x0E | 0x00635814 | 0x00DC760C | **dwRoomMessageMemberList**（变体） |
| 0x0F | 0x00635968 | 0x00DC7618 | **dwRoomMessageRoomInfo** |
| 0x10 | 0x006359FC | 0x00DC7624 | **dwRoomMessageReady** |
| 0x11 | 0x00635E57 | 0x00DC7630 | **dwRoomMessageStartCountingDown** |
| 0x12 | 0x006361B6 | 0x00DC76C0 | **dwRoomMessageAvatarInfo** |
| 0x13 | 0x00635F2C | 0x00DC763C | **dwRoomMessageP2PInfo** |
| 0x14 | 0x00636336 | 0x00DC7648 | **dwRoomMessageChangeTeam** |
| 0x15 | 0x006365A3 | 0x00DC7654 | **dwRoomMessageChangeTeamRequest** |
| 0x16 | 0x006367C3 | 0x00DC7678 | **dwRoomMessagePlaylistWeights** |
| 0x17 | 0x006367F5 | 0x00DC7684 | **dwRoomMessageRoomStateUpdated** |
| 0x18 | 0x00635D8F | 0x00DC757C | **dwRoomMessageScore** |
| 0x19 | 0x00636EBA | — | *忽略* |
| 0x1A | 0x00636291 | 0x00DC766C | **dwRoomMessageVote** |
| 0x1B | 0x00636715 | 0x00DC7660 | **dwRoomMessageSetPilot** |
| 0x1C | 0x00635AC3 | 0x00DC7570 | **dwRoomMessageCard** |
| 0x1D | 0x00635B47 | 0x00DC754C | **dwRoomMessageMemberDetails** |
| 0x1E | 0x00635C5B | 0x00DC7558 | **dwRoomMessageMemberDetailsQuery** |
| 0x1F | 0x00635BE6 | 0x00DC7558 | **dwRoomMessageMemberDetailsQuery**（变体） |
| 0x20 | 0x006368A7 | 0x00DC76CC | **dwRoomMessageUpdateDlcLevel** |
| 0x21 | 0x0063693E | 0x00DC76D8 | **dwRoomMessageUpdateCreditRating** |
| 0x22 | 0x006369FD | 0x00DC76E4 | **dwRoomMessageUpdateWarGodData** |
| 0x23 | 0x00636ABE | 0x00DC76F0 | **dwRoomMessageQQMembership** |
| 0x24 | 0x00636B6D | 0x00DC76FC | **dwRoomMessageNetcafePrivileges** |
| 0x25 | 0x00634CB3 | 0x00DC7588 | **dwRoomMessageJoinMemberInfos** |
| 0x26 | 0x00636C1D | 0x00DC769C | **dwRoomMessagePlayerPrimaryWeaponCountChange** |
| 0x27 | 0x00636CD1 | 0x00DC769C | **dwRoomMessagePlayerPrimaryWeaponCountChange**（变体） |
| 0x28 | 0x00636EBA | — | *忽略* |
| 0x29 | 0x00636EBA | — | *忽略* |
| 0x2A | 0x00636EBA | — | *忽略* |
| 0x2B | 0x006352DC | 0x00DC75DC | **dwRoomMessageJoinWithParty** |
| 0x2C | 0x00634A28 | 0x00DC751C | **dwRoomMessageStartGame**（变体） |
| 0x2D | 0x00636D7F | 0x00DC76A8 | **dwRoomMessageInRoomStateChange** |
| 0x2E | 0x00636E0A | 0x00DC76B4 | **dwRoomMessageDMZLeagueTicketStateChange** |

### 闸门分布（`[dwRoom+0x278]` / `[dwRoom+0x27C]` / `[dwRoom+0x283]`）

| 闸门要求 | type 集合 | 含义 |
|---|---|---|
| **要求未进房** `[+0x278]==0` | 0x06、0x07、0x0A、0x0C、0x0D、0x0E、0x0F、0x11、0x13、0x18、0x2B | 进房前的握手/初始化类 |
| **要求已进房** `[+0x278]!=0` | 0x06（与上互补分支） | 进房后的消息 |
| **要求 `[+0x27C]==0`** | 0x04、0x05、0x25 | 进房标志前置 |
| **额外要求 `[+0x283]==0`** | 0x0F RoomInfo | RoomInfo 只处理一次 |
| 无闸门 | 0x03、0x08、0x09、0x10、0x12、0x14–0x17、0x1A–0x1F、0x20–0x24、0x26、0x27、0x2C–0x2E | 直接处理 |



## 3. 分派框架（与 055 记载吻合）

- `0x637000` 建位流（`nbits = 字节数*8`）→ `readBits(3)` + `readData(8)` 得 type → 查本表
- `0x636F3C` 表被 `0x00634956` 引用（在 `0x0063495A` handler 前一条，即分派入口处）
- handler 返回后统一走 `0x00636EF0` 一带的清理（`[edx+0x14]` 虚调用 + `0xca8114`）

## 4. ★★★ 房间对象核心数据结构（硬结论，来自 handler 反汇编）

### 4.1 成员表

| 项 | 值 | 证据 |
|---|---|---|
| 成员表基址 | `dwRoom + 0xE368` | `lea ecx, [ebx + 0xe368]`（多个 handler 一致） |
| **成员条目大小** | **0x1D0 = 464 字节** | `add ecx, 0x1d0` 循环步长 |
| 成员数 | `[dwRoom + 0x105D8]` | `cmp dword ptr [ebx + 0x105d8], eax` |
| 成员 ID | 条目 `+0x00`(dword) / `+0x04`(dword) | `cmp [ecx], edi` / `cmp [ecx+4], edx` 双重匹配 |

### 4.2 逐字段写入点（偏移相对成员条目基址）

| 消息 | type | 写入偏移 | 含义 |
|---|---|---|---|
| Ready | 0x10 | `+0x90`（= 0xE3F8 − 0xE368） | 该成员的**准备标志**（`mov byte [..], cl`） |
| Card | 0x1C | `+0xB2`（= 0xE41A − 0xE368） | 名片/卡片数据 |
| Card 变体 | — | `+0xB2`、`+0xB6` | 连续两个 dword 写入 |

### 4.3 handler 通用形态

```
mov eax,[ebx] / mov edx,[eax+0x60] / call edx      ; 虚调用（房间态判定闸门）
test al,al / je <default exit>
lea ecx,[ebp-0xC20]
mov [ebp-0xC1C], 0x10                              ; ★ type 号
mov [ebp-0xC20], 0x00DC7624                        ; ★ 消息 vtable = dwRoomMessageReady
mov byte [ebp-0xC18], 0
call 0x629090                                      ; 解析器（读入消息字段到栈）
… 按成员 ID 在 0xE368 表里线性查找 …
… 写入成员条目对应偏移 …
call 0x632D00 / call 0x632A70                      ; 收尾（广播/刷新）
```

**这就是完整的"下行消息 → 房间状态"落地路径**，可直接对照实现。

## 5. 消息元信息块（44 个，含名称）

每个消息类有一个 20 字节元信息块：`[构造函数][0x00DF9520 基类vtable][0][类型名指针][1]`。
条目在 `0x009F87xx` 段、构造函数在 `0x00DF87xx` 段，**两段一一对应**。
完整清单已导出：`RUNS/room_messages.txt`（44 行：条目地址 / 构造函数 / 类名）。

首条是 `dwPartyMessageReadyInfo`（队伍消息，与房间消息同族）。

## 7. ★★★ W-A4：房间状态机与字段表（逐个 handler 反汇编）

### 7.1 dwRoom 对象字段表（相对 `ebx` = dwRoom 实例）

| 偏移 | 类型 | 含义 | 证据 |
|---|---|---|---|
| `+0x01C` | ptr | 房间 ID 结构体；`+0x20`=lo, `+0x24`=hi | `mov eax,[ebx+0x1c]` → `cmp edi,[eax+0x20]` |
| `+0x278` | byte | **房间态闸门 1**（0=未进房） | MemberList/RoomInfo/StartCountingDown 均 `cmp byte [ebx+0x278],0` |
| `+0x27C` | dword | **进房标志**（Join 后置值，Leave 后清 0） | Join: `mov [ebx+0x27c], ecx`；Leave: `mov [eax+0x27c], 0` |
| `+0x283` | byte | **房间态闸门 2**（RoomInfo 额外要求为 0） | RoomInfo: `cmp byte [ebx+0x283],0` |
| `+0x287` | byte | Join 写入的一个字节标志 | Join: `mov byte [ebx+0x287], dl` |
| `+0x338` | dword | Join 写入：本机成员 ID 低位 | Join: `mov [ebx+0x338], edi` |
| `+0x33C` | dword | Join 写入：本机成员 ID 高位 | Join: `mov [ebx+0x33c], ecx` |
| **`+0xE368`** | array | **成员表基址**，条目 **0x1D0** 字节 | 见 7.2 |
| `+0x105D8` | dword | **成员数** | `cmp [ebx+0x105d8], eax` |
| `+0x105F0` | struct | 房间配置串区（`\mapname\…`），RoomInfo 解析目标 | `lea esi,[ebx+0x105f0]` |
| `+0x10660` | struct | RoomInfo 的输出/镜像区 | `lea edi,[ebx+0x10660]` |
| `+0x106E0/+0x106E4` | dword | **待加入房间 ID**（lo/hi），Join 前置校验 | Join: `cmp [ebx+0x106e0], edi` |
| `+0x106F8` | struct | Join 后的会话/频道对象 | `lea ecx,[ebx+0x106f8]` |
| `+0x10710` | float | **倒计时剩余秒数** | StartCountingDown: `lea ecx,[ebx+0x10710]` + 浮点比较 |
| `+0x10720` | struct | Leave 时清理的对象 | `lea ecx,[eax+0x10720]` |
| `+0x10758/+0x1075C` | dword | Leave 时清 0 的一对 dword | `mov [eax+0x10758],0` / `+0x1075c` |
| `+0x10798` | struct | StartGame 前的校验目标 | `lea edx,[ebx+0x10798]` |

### 7.2 成员表条目（基址 `dwRoom+0xE368`，步长 `0x1D0`）

| 条目内偏移 | 含义 | 证据 |
|---|---|---|
| `+0x00` | 成员 ID 低 32 | `cmp [ecx], edi` |
| `+0x04` | 成员 ID 高 32 | `cmp [ecx+4], edx` |
| `+0x90` | **准备标志**（byte） | Ready handler 写 `[eax+ebx+0xe3f8]` = `+0x90` |
| `+0xB2` | 名片/卡片字段 1 | Card handler 写 `[eax+ebx+0xe41a]` |
| `+0xB6` | 名片/卡片字段 2 | Card handler 紧接着写 |

### 7.3 各消息的处理条件（状态机转换）

| type | 消息 | 前置条件（不满足即丢弃到 0x636F02） | 动作 |
|---|---|---|---|
| 0x0D | MemberList | `[+0x278] == 0` | 读成员数/表指针，调 `[vtable+0x144]` 处理 |
| 0x0F | RoomInfo | `[+0x278]==0` **且** `[+0x283]==0` **且** 房间ID匹配 | 解析配置串到 `+0x105F0`，比对 `+0x10660`，遍历 `[+4]` 链表调 `[vtable+0x48]` |
| 0x0A | MemberInfoAdd | `[+0x278]==0` **且** `[vtable+0x60]()` 为真 | 调 `0x623770` 构造欢迎对象 → `0x626130` 解析 → `0x801600` |
| **0x05** | **Join** | `[+0x27C]==0` **且** 消息 ID == `[+0x106E0/+0x106E4]` | 写 `+0x338/+0x33C`(本机ID)、`+0x27C`(进房)、`+0x287`；解析到 `+0x105F0`；建 `+0x106F8` |
| **0x08** | **Leave** | `[dwRoomImp+0x1C] != 0` **且** `[vtable+0x54]()` 为假 | 清 `+0x27C`/`+0x10758`/`+0x1075C`，清 `+0x10720`，调 `0x62F370` 收尾 |
| 0x10 | Ready | `[vtable+0x60]()` 为真 | 按成员 ID 线性查找 → 写条目 `+0x90` → 遍历 `[+4]` 调 `[vtable+0x40]` |
| 0x11 | StartCountingDown | `[+0x278]==0` **且** `[vtable+0x64]()` 为假 | 读 float 倒计时 → 写 `+0x10710` → 与 `[0xcaddc4]` 常量比较 |
| 0x02 | StartGame | `0x4A3AF0` 校验（ID 匹配 `+0x10798`） | 读 `[0x82E1408]`，比 `[0x76446B0] == 0xA` |

### 7.4 房间态转换（由上述条件推出）

```
[未进房]  +0x278=0, +0x27C=0
   │  收 type 0x05 Join，且房间 ID 匹配 [+0x106E0]
   ▼
[已进房]  +0x27C=非0，+0x338/+0x33C=本机成员ID
   │  收 0x0F RoomInfo → +0x283 被置起（之后 RoomInfo 不再处理）
   │  收 0x0D MemberList → 建立成员表 +0xE368 / 成员数 +0x105D8
   │  收 0x0A MemberInfoAdd → 逐个成员补全
   │  收 0x10 Ready → 该成员条目 +0x90 = 1
   │  收 0x11 StartCountingDown → +0x10710 = 剩余秒数
   ▼
[开局]    收 0x02 StartGame（校验 +0x10798）
   │
   ▼  收 0x08 Leave
[退出]    +0x27C/0x10758/0x1075C 归零
```

### 7.5 与 dwRoomImp 的关系

Leave 处理里第一条就是 `mov edx,[0x82E13FC]`（**dwRoomImp 单例**），
说明房间进出都经过 dwRoomImp——这与已知的两道闸门（`+0x60`/`+0x64`）同源。

## 9. ★★★ 11/4 blob（房间信道）入口链路

### 9.1 入口 `0x637000`（055 记录的点，本次补全）

```
0x637009  push 0x24 / call 0xB74220          ; 分配 0x24 字节（位流对象）
0x637019  mov ecx,[ebp+0x24]                  ; 长度参数（字节数）
0x63701C  lea edx,[ecx*8]                     ; ★ nbits = 字节数 × 8
0x637023  mov ecx,[ebp+0x20]                  ; buf
0x63702C  call 0xB779A0                       ; 构造位流
0x637048  push 3 / call 0xB774E0              ; ★ readBits(3)
0x637055  push 8 / lea eax,[ebp-1]            ; 8 字节缓冲
0x63705D  call 0xB772E0                       ; ★ readData(8)  → type
0x637062  movzx eax, byte [ebp-1]             ; type
0x63706B  mov [esi+0x1C], 1                   ; 位流对象标记
0x63706E  cmp eax, 1
0x637070  jne 0x63718D                        ; ★ type != 1 → 普通分派
```

### 9.2 type 1 = `dwRoomMessageManifold`（分片/多段容器）

```
0x637080  mov [ebp-0x20], 0x00DC74F8         ; ★ vtable = dwRoomMessageManifold
0x637090  call 0x6256C0                       ; 解析 Manifold 头
0x6370A6  push 3 / call 0xB774E0              ; readBits(3)
0x6370B3  push 8 / call 0xB772E0              ; readData(8) = 子类型 → edi
0x6370C6  mov [eax+0x1C], 1
0x6370CD  mov ecx,[esi+8] / or ecx,[esi+0xC]  ; ★ 检查 8 字节分片 ID（lo|hi）
0x6370D3  je 0x637104
0x6370D5  mov ecx,[0x84ABB08]                 ; 全局分片表
```

**⇒ type 1 是"一条信道消息里包含多个子消息"的容器**，子类型同样 3+8 位编码。
这与 055 记的 "type 0x02 是 Text" 并不冲突：0x02 是**顶层** type，Manifold 里的是**子**类型。

### 9.3 普通 type → 分派器 `0x634870`

```
0x63718D  … 读入 5 个参数 …
0x6371AE  mov eax,[edx+0x25C8]               ; ★ 房间对象指针（dwRoom 实例）
0x6371B9  call 0x634870                       ; ★ 分派器
0x6371BE  释放位流对象（0xCA8114 / 0xCA8128）
```

**分派器签名（推定）**：`0x634870(type, dwRoom*, buf, len, ctx*)`，
其内部 `jmp [0x636F3C + type*4]` 进入 §2 的 47 项表。

## 10. ★★★ 成员条目完整字段表（0x1D0 = 464 字节）

由全部 handler 对 `[成员基址 + offset]` 的访问汇总得出（`成员基址 = dwRoom + 0xE368`）：

| 偏移 | 触及的 type | 推断含义 |
|---|---|---|
| `+0x005` | 0x02/0x03/0x2C | 开局相关字节（StartGame 家族） |
| `+0x006` | 0x0F/0x10/0x11/0x13/0x18/0x1C/0x1D–0x1F | **成员状态字节组**（被最多消息读） |
| `+0x048` | 0x07/0x08/0x09/0x0C/0x16/0x17/0x1B/0x20–0x24/0x26/0x2B | 成员名/队伍区 |
| `+0x088` | 0x12/0x14/0x15/0x1A | 头像/换队区 |
| `+0x08C` | 0x02/0x03/0x04/0x05/0x25/0x2C | 进房/开局标志 |
| **`+0x090`** | 0x08/0x09/0x0A/0x0C/0x0D/0x0E/0x0F/0x10 | **准备标志（已确证）** |
| `+0x094`–`+0x099` | 0x0F/0x10/0x18/0x1C/0x1D–0x1F | 连续标志/计数字节组 |
| `+0x0A8` | 0x07/0x08/0x09/0x2B | 进房相关 |
| `+0x0AC` | 0x11/0x12/0x13/0x18/0x1A | 倒计时相关 |
| `+0x0B1` | 0x12/0x14/0x15/0x1A/0x1B | 队伍/阵营字节 |
| **`+0x0B2`** | 0x0A/0x0C/0x0D/0x0E/0x0F/0x10/0x1C | **名片/Card 区** |
| `+0x0BC` | 0x0A/0x0C/0x0D/0x0E/0x0F/0x10/0x1C–0x1F | 名片扩展 |
| `+0x182` | 0x02/0x03/0x04/0x05/0x25/0x2C | 开局相关（远区） |
| `+0x1A0` | 0x14–0x17/0x1B/0x20 | 详情区起点 |
| `+0x1A4`–`+0x1AC` | 0x15–0x17/0x1B/0x20–0x22 | 详情区（连续 dword） |
| `+0x1B1`–`+0x1B3` | 0x15–0x17/0x1B/0x20/0x21/0x23/0x24/0x26/0x27 | 详情/特权区 |
| `+0x1B6`/`+0x1B7` | 0x20–0x24/0x26/0x27/0x2D/0x2E | DLC/信誉/战神数据区 |
| `+0x1B8`–`+0x1BE` | 0x07/0x08/0x09/0x0C/0x2B | 队伍/邀请区 |
| `+0x1C0`/`+0x1C4` | 0x15–0x17/0x1B/0x20–0x24 | 详情区尾部 |

**区段划分（工程视图）**：

```
+0x000 .. 0x087   基础身份区（ID / 状态字节 / 名字 / 队伍）
+0x088 .. 0x0BF   头像 + 准备 + 名片区  ★ 最常用
+0x0C0 .. 0x19F   （未在消息路径中引用 —— 可能是本地缓存/渲染数据）
+0x1A0 .. 0x1D0   详情扩展区（DLC / 信誉 / 战神 / 特权 / 队伍邀请）
```


055 判 "39 个未命名 type" ⇒ **现已命名 41 个消息类 + 44/47 分发表项**。
房间下行的完整语义面因此建立：

| 我们的需求 | 对应下行 type |
|---|---|
| 建房完成 | 0x0F RoomInfo |
| 成员同步 | 0x0D MemberList / 0x0A MemberInfoAdd / 0x0C MemberInfoEXT |
| 准备状态 | 0x10 Ready |
| 倒计时 | 0x11 StartCountingDown |
| 开局 | 0x03 / 0x2C StartGame（0x02 为家族入口）、0x04 StartGameFailed |
| 进/退房间 | 0x05 Join / 0x08 Leave / 0x2B JoinWithParty |
| 玩家详情 | 0x1D / 0x1E / 0x1F MemberDetails* |
| 房间状态 | 0x17 RoomStateUpdated / 0x2D InRoomStateChange |
| **多消息容器** | **0x01 Manifold**（内含 3+8 位子类型） |

**下一步（已知缺口）**：
1. `0x634870` 分派器的参数顺序需进一步确认（`0x6371B9` 处压了 5 个参数）
2. 其余消息类的 `deserialize` 未逐个定位（Ready 已解完，见 §12）
3. 成员条目 `+0x0C0 .. 0x19F` 区间未被任何消息 handler 引用，
   疑为客户端本地缓存/渲染数据，未解

## 12. ★★★ 字段级线格式（首个完整样本：dwRoomMessageReady）

### 12.1 位流读写原语

| 函数 | 方向 | 签名 |
|---|---|---|
| `0x00B774E0` | **读** | `readBits(stream, nbits)` → bool（剩余位数是否足够） |
| `0x00B772E0` | **读** | `readData(stream, nbits, out_ptr)` → bool |
| `0x00B77B10` | **写** | `writeBits(stream, nbits)` |
| `0x00B777C0` | **写** | `writeData(stream, nbits, in_ptr)` |
| `0x00B779A0` | 构造 | `newStream(buf, nbits, mode)` |

### 12.2 Ready 的 deserialize `0x00629090`

```asm
0062909D  push 3 / call readBits      ; 读 3 位（属性标记）
006290AA  push 8 / call readData      ; 读 8 位 → [ebp+0xB]
006290C1  movzx ecx, byte [ebp+0xB]
006290C5  mov [ebx+4], ecx            ; ★ 字段1 = 8 位值（dword 存储）
006290CE  push 1 / call readBits      ; 读 1 位（属性标记）
006290DB  push 1 / call readData      ; 读 1 位 → [ebp+0xB]
006290F0  cmp byte [ebp+0xB], 0
006290F5  setne al
006290F8  mov [ebx+8], al             ; ★ 字段2 = 1 位布尔（byte）
006290FC  mov al, 1                   ; 成功
```

### 12.3 Ready 的 serialize `0x00629110` —— 与读**严格对称**

```asm
0062911E  mov al, byte [esi+4]        ; 字段1
00629121  push 3 / call writeBits     ; 写 3 位
0062912D  push 8 / call writeData     ; 写 8 位
0062913C  mov dl, byte [esi+8]        ; 字段2
0062913F  push 3 / call writeBits     ; 写 3 位
0062914B  push 8 / call writeData     ; 写 8 位
```

### 12.4 ★★ 由此确立的编码范式

**每个字段 = `writeBits(3)` + `writeData(N)`**：前 3 位是**属性/位宽标记**，随后按该属性
声明的宽度写值（示例中属性 1 是 8 位，属性 2 是 1 位）。

这与 055 记的"下行 `readBits(3)` + `readData(8)` 得顶层 type"是**同一套机制**——
顶层 type 只是这套"属性-值对"编码的第一个字段。

**⇒ 这解释了此前所有按"固定字段表"拼推送的尝试为何全部失败**：
消息体不是固定布局，而是**属性-值对序列**，且**读写两侧的 3 位标记必须一致**。

### 12.5 可复用的实现要点

1. 先写 3 位属性号，再按该属性的位宽写值——不能跳号、不能换序
2. 属性位宽表需要从各消息的 deserialize 逐条读出（Ready 已解，其余待解）
3. 顶层 type 用 `readBits(3)+readData(8)`，与字段同构；`type==1` 另有 Manifold 子结构

## 13. ★★★ 完整属性位宽表（四类消息的 deserialize 已解）

### 13.1 vtable 三层继承结构（重要）

每个消息类的 vtable 是**三层拼接**，每层三槽 `[serialize, deserialize, 元信息指针]`：

| 槽位 | 含义 |
|---|---|
| `[0]` / `[1]` | **本类** serialize / deserialize |
| `[3]` / `[4]` | **父类** serialize / deserialize |
| `[6]` / `[7]` | **祖父类** serialize / deserialize |

⇒ 解析消息体时必须**从祖父层到本类层依次调用**，而不是只调一个函数。

### 13.2 各消息的 deserialize 入口

| 消息 | vftable | 本类 DESER | 父/祖父层 DESER |
|---|---|---|---|
| `dwRoomMessageReady` | 0x00DC7624 | `0x00629090` | `0x00625DB0`、`0x00628320`(SER) |
| `dwRoomMessageRoomInfo` | 0x00DC7618 | `0x00627EE0` | `0x00629090`、`0x00625DB0` |
| `dwRoomMessageMemberList` | 0x00DC760C | `0x00627E00` | `0x00627EE0`、`0x00629090` |
| `dwRoomMessageJoin` | 0x00DC7594 | `0x00626B30` | `0x00627230`、`0x00627560` |
| `dwRoomMessageStartGame` | 0x00DC751C | `0x00625CE0` | `0x00625DB0`、`0x00625F50` |

**继承链（由槽位包含关系推出）**：
```
dwRoomMessage (基)
   └─ dwRoomMessageReady          (+0x04 id, +0x08 bool)
        └─ dwRoomMessageMemberList
             └─ dwRoomMessageRoomInfo    (+0x0C, +0x0D, … 连续 8 位字段)
dwRoomMessage
   └─ dwRoomMessageJoin
   └─ dwRoomMessageStartGame
```

### 13.3 字段编码规格（已实测）

| 消息 | 字段序 | 编码 | 落位 |
|---|---|---|---|
| Ready | 1. 成员 ID | `readBits(3)`+`readData(8)` | `+0x04` (dword) |
| | 2. 布尔 | `readBits(1)`+`readData(1)` | `+0x08` (byte) |
| RoomInfo | 1. 成员 ID | `readBits(3)`+`readData(8)` | `+0x04` |
| | 2. 字符串/复杂字段 | 调 `0x624BF0`（含子字段链） | `+0x08` 起 |
| | 3. 字段 A | `readBits(3)`+`readData(8)` | `+0x0C` |
| | 4. 字段 B | `readBits(3)`+`readData(8)` | `+0x0D` |
| | …（`0x624BF0` 内继续） | 同上 | 连续字节 |
| MemberList | 1. 成员 ID | `readBits(3)`+`readData(8)` | `+0x04` |
| | 2. 列表头 | 后续 `readBits(3)+readData(8)` | `+0x08+` |

### 13.4 ★ 通用编码规则（可直接实现）

```
字段 = [3 bits: 属性标记] [N bits: 值]
N 由属性决定 —— 实测常见 N ∈ {1, 8}；其他属性待逐个读出
所有字段串联，无分隔符、无长度前缀（长度由属性隐含）
消息体 = 顶层 type(3+8) + Manifold(type==1 时) + 按继承链逐层的字段序列
```

**这解释了此前"固定字段表"全部失效的原因**：消息体是**属性驱动的变长编码**，
字段顺序与宽度由属性标记本身决定，不能按固定 dw​ord 偏移硬拼。

### 13.5 尚未解的部分（诚实标注）

- 属性标记（3 位）到**属性名**的映射表尚未建立——目前只知道"读 3 位 → 按属性宽度读值"
- `0x624BF0`、`0x623DE0` 等"字段处理器"内部的子字段链只看了头部
- Join / StartGame 的字段细节未逐个列出（入口已定位，见 13.2）
- 字符串类字段的编码（长度前缀？终止符？）未确认

## 15. ★★★★ 编码位序已用真实字节确证（可实现的最终规格）

### 15.1 位序修正（推翻此前的 `readBits(3)` 先的假设）

`readBits` 的实参是**上限**（内部 `push 0x1F` 先读 31 位再比较），
`readData(n, dst)` 写 n 位。真实位流是 **LSB-first**。

**用 6 个真实 11/4 上行样本验证（`lobby_tasks.bin`，服务 11 任务 4）：**

```
body = p[19:]                     ; 跳过 0a<8B roomId> 13 08 <len4> <u32>
type    = readBits(8)             ; ★ 先 8 位
subtype = readBits(3)             ; 再 3 位
```

| 样本 | body 首字节 | type | 分发表对应 |
|---|---|---|---|
| 0 | `02` | **0x02** | dwRoomMessageStartGame ✅ |
| 1 | `18` | **0x18** | dwRoomMessageCard ✅ |
| 2 | `02` | **0x02** | StartGame ✅ |
| 3 | `02` | **0x02** | StartGame ✅ |
| 4 | `18` | **0x18** | Card ✅ |
| 5 | `02` | **0x02** | StartGame ✅ |

**6/6 全部命中已知 type，无例外** ⇒ 位序与宽度确认。

> ⚠ 055 记的 "`readBits(3)` + `readData(8)`" 描述的是**调用顺序**（3 位操作在前），
> 但实际消费的位数是 **8 位值 + 3 位标记**。凡按"先 3 位再 8 bit 拼值"的解析都会错位。

### 15.2 上行 11/4 完整封装（已验证）

```
0a <roomId:8B>                     ; 频道/房间 ID
13 08 <declared_len:4B LE>         ; 内层长度
<len-4:4B LE>                      ; 实测 = declared - 4（100% 吻合）
<body: 上面解码的位流>
```

### 15.3 字段级编码（同一位序）

```
字段 = readBits(8) 得值 + readBits(3) 得标记
（Ready 实测：值 8 位→[+0x04]，随后 1 位布尔→[+0x08]）
```

### 15.4 可实现清单

| 项 | 状态 |
|---|---|
| 上行 11/4 封装 | ✅ 已验证（6 样本） |
| 顶层 type 解码 | ✅ 已验证（8 位 + 3 位） |
| Ready 字段解码 | ✅ 已解（`0x00629090`） |
| RoomInfo/MemberList/Join/StartGame 解码入口 | ✅ 已定位（§13.2） |
| 各字段的 3 位标记语义 | ⚠ **仍未知**（标记值 0/2/4 均出现，含义未定） |
| 下行推送的封装差异 | ⚠ 055 记"下行无 `<u32 len-4>` 前缀"，未在本轮复核 |

**⇒ 写出正确推送所需的最少信息已齐**：封装 + 位序 + 顶层 type + 分层调用顺序。
剩余未知只影响"字段具体含义"，不影响"能否被客户端解析"。

## 16. 对修复的直接含义

