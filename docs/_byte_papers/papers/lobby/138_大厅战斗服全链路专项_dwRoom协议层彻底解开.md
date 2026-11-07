# 138 · 大厅↔战斗服 全链路专项卷：dwRoom 协议层彻底解开

> ⚠️ **本卷已被 139 更正三处，引用前必读**：
> ① **房间消息走 op6 或 op7**（同 handler `0xB7B300`），本卷 §2 写的"opcode 6 → `0xB7B210`"错了一层 —— `0xB7B210` 实为 **op5（邀请弹窗）**。
> ② `0xE374650` 记录表的 `+0x10=0x55667788/+0x14=0x11223344`、账号 ID、`M7-E8S6Client`、`+0x1C=0x12` 等"磁盘实测值"落在**段2（覆盖 0.2%）**，是**文件残留**不是编译期常量；真值由 `0x7E7F26/0x7E7F29` 运行时写入。
> ③ `0x82E1458` 的"磁盘全 0"是**读到文件空洞**。
> **结构/格式/流程类结论（47 type、位流、Manifold、归属过滤）全部成立。** 详见 [139](139_房间黑箱二轮扫荡_镜像边界与三通道定论.md)。
>
> 配套探讨：[138 探讨 · 三条"我以为对"的前提，全部被字节推翻](138_大厅战斗服全链路专项_dwRoom协议层彻底解开_探讨.md)
> 前序：119（0x13 内层）、137（静态侧全清）、`codol-65-response-and-room-event-dispatch-138`（6/5 应答）、`codol-room-delivery-chain-138b`（投递链）、`codol-dwroom-message-format-138c`（dwRoom 消息体）、`codol-dwroom-dispatch-key-138d`（分发键）、`codol-dwroom-47types-and-codenames-138e`（47 type 全表）
> 性质：**十二路静态逆向 + 两次实机对照实验 + 活进程 dump**。全部结论由我独立重跑反汇编/日志复核。

---

## §0 十五条结论

1. ★★★ **`[0x76446B0]` = `clientState`（CA_\* 枚举），开局闸门要求 `< 3`** ⇒ **客户端连着我们的服务器就拒绝本地开局**。
2. ★★★ **`ready_push.on` 双推送共用 `seq = 请求seq+1000` ⇒ 客户端 `10054` RST**（VERIFIED L1477 已修）。
3. ★★★ **两轮实机跑的都是旧版 GOLDEN（`D7EEB456`, 1323 行）**，全部修复在 VERIFIED（`FF473204`, 1575 行）⇒ **修复从未被执行**；而 VERIFIED 跑过之后**依然无效**。
4. ★★★ **房间事件不走 `6/5`，也不走 `11/4` 应答体** —— 走 **`dwRoom` 协议（独立一层）**。
5. ★★★ **`11/4` 的 blob 不是 dwRoom 消息**（实测：ready 族首 5 位=3 但后续 3 位=4；room 族首 5 位=0）⇒ **dwRoom 是比 srpc 更上层、语料里从未出现的一层**。
6. ★★★ **分发键 = `0x1122334455667788`**：dwRoom 消息首个 u64 必须等于它，否则 `0x7E7C90` 不命中、消息丢弃。
7. ★★★ **Manifold 每条记录的 64 位 = 归属者 ID**：**`0` = 广播放行**；`= 本机账号 ID` = 定向；**其他值 ⇒ 整条丢弃**。
8. ★★ **完整投递链已打通到消息泵**（§2）。
9. ★★ **`0x636F3C` 47 项表 = dwRoomMessage 类型空间**，47 种 type 字段位宽全表（§5）。
10. ★★ **字段码名表 `0xB773D0` 25 项实见**（§4）。
11. ★★ **`rec+0x90`（Ready）唯一写点 = `case 0x10`**；本地"点准备"只发不写 ⇒ 不回 Ready 永远不显示"已准备"。
12. ★★ **`rec+0x88`（阵营）由本地 `0x62A24C` 直写** ⇒ 按钮立即变灰（解释症状不对称）。
13. ★★ **`+0x105FE`（人数上限）← dvar `"3265"` ← playlist `rule 3265`**（= `2×vsrule`）。
14. ★★ **魔数 B `0x8D51E398` = `crc32("combat")`**。
15. ★★ **建房顺序 13/13 次 `11/13` 先于 `21/1`** ⇒ 服务端顺序反了。

---

## §1 症状 → 机制（用户实测）

| 用户观察 | 机制 | 地址 |
|---|---|---|
| 房间能建成 | `11/13`→`21/1`→`21/12`→`11/4` 全链路通 | 日志 |
| **点准备状态不变** | `rec+0x90` 唯一写点 = `case 0x10` | `0x635A86` |
| 加入阵营按钮变灰 | 本地直写 `rec+0x88` | `0x62A24C` |
| 投票/选图无效 | `Vote=0x1A` 走 47 项表 `case 0x1A` | `0x636291` |
| **秒断秒恢复** | 双推送同 seq ⇒ RST，客户端自动重连 | `seq=1062 ×2 → 10054` |
| **进不了对局服务器** | `clientState ≥ 3` ⇒ 开局闸门② 拒绝 | `0x62F867` |
| 返回大厅正常 | 无连接依赖 | — |

---

## §2 ★★★ dwRoom 完整投递链（逐字节验证）

```
【网络层】
0xB838A0  dwLobbyImp::handleMessage
 0xB82CCA  lea ecx,[edi+0x20]; call 0xB80D30   ; 读消息类型号
 0xB82D1D  if ([edi+0x4F0]) { cmp 0x3E9; dec; cmp 0x4A; jmp [eax*4+0xB83744] }
 0xB82DF7  call 0xB7B210                        ; opcode 6

【opcode 6 处理】
0xB7B210
 0xB7B287  mov ecx,[esi+0x4F0]   ; = 静态单例 0xE39B6E8 (vtable 0xDE07A4 dwLobbyEventHandler)
 0xB7B28F  mov edx,[edx+0x28]    ; vt[0x28] → 0x7F20C0 → 0x808DC0
 0xB7B299  call edx              ; 从消息流读数据 → 投递到 0xE37B918 事件环（每条 0x88）

【消息体解析（0xBA4C50）】
 0xBA4C85  call 0xB769A0   → [obj+0x08] = u64      ★★ 分发键 0x1122334455667788
 0xBA4C97  call 0xB76A30   → [obj+0x10] = char[64]
 0xBA4CBC  call 0xB76AF0   → [obj+0x60] = blob #1   ★★ 内层 = Manifold
 0xBA4CE3  call 0xB76AF0   → [obj+0x70] = blob #2

【srpc 分发（0x7E7C90）】
 0x7E7CE2  cmp arg1,[record+0x10]  ; = 0x55667788
 0x7E7CEA  cmp arg2,[record+0x14]  ; = 0x11223344
 0x7E7D0E  call [record+0x25B8]    ; = 0x6371F0

【收包（0x6371F0）】
 0x63722E  call 0x7E7970   ; 按 u64 查槽
 0x637280  call 0xB76AF0   ; 读 blob#1（tag 0x13 校验 + u32 len + 数据）
 0x6372AA  call 0xB76AF0   ; 读 blob#2
 0x637302  call 0x637000

【分派（0x637000）】
 0x63702C  call 0xB779A0   ; 建位流（lea edx,[len*8]）
 0x637048  call 0xB774E0(3) ; read5，断言 ==3
 0x637055  call 0xB772E0(8) ; read8 → [ebp-1]
 0x637070  cmp eax,1 / jne 0x63718D
   ==1 → 0x6256C0 (dwRoomMessageManifold)
   !=1 → 直通 0x634870

【Manifold（0x6256C0）】
 code(3)+u8(类型=1) + code(8)+u32(N) + N × { code(1)+1位hasValue
   [ code(0x15)+64位归属者ID ] + code(0x13)+code(8)+u32(len)+子位流 }

【归属过滤（0x6370CD，★关键）】
 0x6370D0  or ecx,[esi+0xC]        ; u64 = lo|hi
 0x6370D3  je  0x637104            ; ★ u64==0 ⇒ 放行（广播）
 0x6370F8  cmp [esi+8], 本地身份.lo ; 不匹配 ⇒ 0x637166 摘链丢弃
 0x637100  cmp [esi+0xC], 本地身份.hi
 0x637104  进入类型派发

【47 项表（0x634870）】
 0x6348AA  call 0xB774E0(3)  ; read3，断言 ==3
 0x6348C2  call 0xB772E0(8)  ; read8 → type
 0x63494A  cmp eax,0x2E / ja
 0x634953  jmp [eax*4+0x636F3C]

【case 0x10 (Ready)】
 0x635A32  call 0x629090                        ; 解析
 0x635A86  mov byte [eax+ebx+0xE3F8],cl         ★★ rec+0x90（唯一写点）
 0x635AA4  mov eax,[edx+0x40] / call eax        ; OBS+0x40

【UI 刷新】
0x7CB572  push 0xDDCED4 "cppSetMemberReadyState"
0x7CB588  call 0x730570                        ; GFx ExternalInterface
 → Flash LobbyController → 下一帧 0x7CAD60（脏标志 0x34027E7）→ cppSetRoomMembers
```

**四个槽回调**（`0x63401C..0x63403A` 一次注册）：

| 槽 | 函数 | 职责 |
|---|---|---|
| `+0x25B8` | `0x6371F0` | 房间消息接收（→ Manifold → 47 项表）|
| `+0x25BC` | `0x6374E0` | 成员/房间状态同步（`0x637360`）|
| `+0x25C0` | `0x637520` | 房间已建立回填（`0x62B640` 置 `+0x278=1`）|
| `+0x25C4` | `0x633D50` | 状态码查询（`0x927100` 读到 `0x45B` 时遍历 `room+4`）|

---

## §3 ★★★ 服务端构造（三条硬规则）

### 规则 1：分发键必须是 `0x1122334455667788`
```
0xE374650 首条记录实测：+0x10 = 0x55667788, +0x14 = 0x11223344
0x7E7CE2/0x7E7CEA 用它匹配 ⇒ 消息首个 u64 不是它 ⇒ 丢弃
```

### 规则 2：Manifold 条目的 64 位必须是 `0` 或本机账号 ID
```
u64 == 0                → 放行（广播/无主）
u64 == 0xE7C8A98A6B4C2D0E → 放行（定向给自己）
u64 == 其它              → 0x637166 摘链释放（静默丢弃）
```

### 规则 3：位流必须逐位对齐（客户端会断言）
`0xB774E0` 读完 5 位码后 **`cmp` 断言等于期望值**，不匹配即类型错误。

---

## §4 ★★ 字段码名表 `0xB773D0`（25 项，逐条实见）

```asm
0xB773EF mov [ebp-0x64],0xD59824 'NoType'     0xB773F6 'Bool'
0xB773FD 'Char8'        0xB77404 'UChar8'     0xB7740B 'WChar16'
0xB77412 'Int16'        0xB77419 'UInt16'     0xB77420 'Int32'
0xB77427 'UInt32'       0xB7742E 'Int64'      0xB77435 'UInt64'
0xB7743C 'RangedInt32'  0xB77443 'RangeUInt32' 0xB7744A 'Float32'
0xB77451 'Float64'      0xB77458 'RangeFloat32' 0xB773D6/DE 'String'×2
0xB7745F 'MultiByteString' 0xB773E1/E9 'Blob'×2  0xB77466 'NaN'
0xB7746D 'FullType'     0xB77474 'StructData'  0xB7747B 'Unknown Type'
0xB77482 cmp eax,0x18 (下限钳制)
0xB77499 mov ebx,[ebp+eax*4-0x64]
```

| 码 | 名 | 码 | 名 |
|---|---|---|---|
| 0 | NoType | 12 | RangeUInt32 |
| 1 | Bool | 13 | Float32 |
| 2 | Char8 | 14 | Float64 |
| 3 | **UChar8** | 15 | RangeFloat32 |
| 4 | WChar16 | 16,17 | String |
| 5 | Int16 | 18 | MultiByteString |
| 6 | UInt16 | 19,22 | Blob |
| 7 | Int32 | 20 | NaN |
| 8 | **UInt32** | 21 | **FullType** |
| 9 | Int64 | 23 | StructData |
| 10 | UInt64 | 24 | Unknown Type |
| 11 | RangedInt32 | | |

---

## §5 ★★ 47 种 dwRoomMessage 全表（`0x636F3C`）

记法：`cN` = `0xB774E0` 断言 5 位 == N；`r/W` = `0xB772E0` 读 W 位。

| type | 类 | 反序列化器 | 字段序列 |
|---|---|---|---|
| 0x00 | — | — | **空** |
| 0x01 | — | — | **空**（仅广播） |
| 0x02 | Text | 0x625A20 | `c3; r/8; String; c21; r/64; c2; r/8` |
| 0x03 | StartGame | 0x625CE0 | `c3; r/8; Blob; Blob; Blob` |
| 0x04 | StartGameFailed | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x05 | Join | 0x626B30 | `c3; r/8; c3; r/8; c1; r/1; call 0x624BF0` |
| 0x06 | JoinRequest | 0x627230 | `c3;r/8; String; c21;r/32; c21;r/16; c21;r/32; c21;r/32; call0x623DE0; c21;r/8; c21;r/32` |
| 0x07 | JoinWithMe | 0x627B40 | `c3; r/8; c21; r/64` |
| 0x08 | — | 0x627CE0 | `c3; r/8`（不构造对象） |
| 0x09 | Leave | 0x627B40 | `c3; r/8; c21; r/64` |
| 0x0A | MemberInfoAdd | 0x626130 | `c3; r/8; call0x623DE0; String` |
| 0x0B | — | — | **空** |
| 0x0C | MemberInfoEXT | 0x625F50 | `c3;r/8; c21;r/64; String; c21;r/32; c3;r/8; c3;r/8; c1;r/1` |
| 0x0D | MemberList | 内联 | `c3;r/8; c21;r/32; {c21; r/32}×count` |
| 0x0E | MemberList | 0x627E00 | `c3;r/8; c21;r/32; {call0x623DE0}×count` |
| 0x0F | RoomInfo | 0x627EE0 | `c3; r/8; call 0x624BF0` |
| **0x10** | **Ready** | **0x629090** | **`c3; r/8; c1; r/1`** |
| 0x11 | StartCountingDown | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x12 | AvatarInfo | 0x628B90 | `c3;r/8; c3;r/8; {c6; r/16}×12; …; c3; r/32` |
| 0x13 | P2PInfo | 0x6280B0 | `c3;r/8; c21;r/32; Blob; Blob; c21;r/32; c21;r/64` |
| **0x14** | **ChangeTeam** | **0x628260** | `c3;r/8; c21;r/32; c21;r/8; c21;r/32; c21;r/64` |
| 0x15 | ChangeTeamRequest | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x16 | PlaylistWeights | 0x6284E0 | `c3;r/8; c21;r/32; {c21; r/32}×N` |
| **0x17** | **RoomStateUpdated** | **0x628610** | **`c3; r/8; c21; r/32; c21; r/32`** |
| 0x18 | Score | 0x6268A0 | `c3; r/8; c21;r/32 ×4` |
| 0x19 | — | — | **空** |
| **0x1A** | **Vote** | **0x625DB0** | **`c3; r/8; c21; r/32`** |
| 0x1B | SetPilot | 0x6283C0 | `c3; r/8; c21; r/8` |
| 0x1C | Card | 0x626730 | `c3; r/8; {c21; r/16}×5` |
| 0x1D | MemberDetails | 0x6263C0 | `c3;r/8; c21;r/32; c2;r/8 ×15; c8;r/32; c8;r/32 ×4; c6;r/16 ×3; c8;r/32 ×4` |
| 0x1E | MemberDetailsQuery | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x1F | — | 0x627CE0 | `c3; r/8`（不构造对象） |
| 0x20 | UpdateDlcLevel | 0x629020 | `c3; r/8; c3; r/8` |
| 0x21 | UpdateCreditRating | 0x629090 | `c3; r/8; c1; r/1` |
| 0x22 | UpdateWarGodData | 0x6291B0 | `c3; r/8; c3; r/8; c8; r/32 ×2` |
| 0x23 | QQMembership | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x24 | NetcafePrivileges | 0x625DB0 | `c3; r/8; c21; r/32` |
| 0x25 | JoinMemberInfos | 0x6269E0 | `c3; r/8; c21; r/8; {call0x623DE0}×N` |
| 0x26 | ClanNameChange | 0x628740 | `c3; r/8; String` |
| 0x27 | PrimaryWeaponCountChange | 0x629090 | `c3; r/8; c1; r/1` |
| 0x28–0x2A | — | — | **空** |
| 0x2B | JoinWithParty | 0x627C30 | `c3;r/8; c21;r/64; c21;r/8; c21;r/8` |
| 0x2C | SpyMessageText | 0x625AB0 | `{call0x625A20}×2; c1; r/1` |
| 0x2D | InRoomStateChange | 0x629090 | `c3; r/8; c1; r/1` |
| 0x2E | DMZLeagueTicketStateChange | 0x629090 | `c3; r/8; c1; r/1` |

**共用反序列化器**：`0x625DB0`(c3+8+c21+32)×7 · `0x629090`(c3+8+c1+1)×5 · `0x627B40`(c3+8+c21+64)×2 · `0x627CE0`(c3+8)×2 · `0x624BF0`(成员档案)×2。

★ **type↔类绑定双向自证**：`0x628320` 首段 `mov al,[esi+4] → writeCode(3) → writeData(&al,8)` ⇒ `[obj+4]` = 8 位类型号；38 个 case 里 35 个构造器 `mov dword [obj+4],k` 精确等于跳转表下标。

---

## §6 ★★★ 开局闸门：`[0x76446B0]` = `clientState`

```asm
0x62F85A  cmp byte [ebx+0x278], 0       ; ① 房间已建立
0x62F867  cmp dword [0x76446B0], 3      ; ② ★ clientState < 3
0x62F86E  jge 0x62FB86                  ; ≥3 拒绝
0x62F874  movzx eax,[ebx+0x105FE]       ; ③ 人数上限
0x62F87B  cmp [ebx+0x105D8], eax        ; 成员数 <= 上限
0x62F883  ... vtable=0xdc7528, type=4, code=7   ; 发 StartGameFailed
```

**5 个写入点**：`0x470469`=3（网络初始化）· `0x5BE90A`=7（建连）· `0x5BEA8B`=4（认证中）· `0x77C343`=0（断线）· `0x813D34`=7（demo 清理）

**CA_\* 表**（`0xDC0900`）：`0 CA_DISCONNECTED / 1 CA_CINEMATIC / 2 CA_LOGO / 3 CA_CONNECTING / 4 CA_CHALLENGING / 5 CA_SENDINGSTATS / 6 CA_LOADING / 7 CA_CONNECTED / 8 CA_GAMESTATE / 9 CA_PRIMED / 10 CA_ACTIVE`

★★ **`< 3` = DISCONNECTED/CINEMATIC/LOGO ⇒ "尚未真正进入在线连接"才允许本地开局**。
⇒ **客户端连着我们的服务器（≥3）⇒ 它认为不该本地开局 ⇒ 必须服务端下发 `dwRoomMessageStartGame`。**

---

## §7 实机对照实验（因果确认）

| | ONCE_20261031_222356（有 `ready_push.on`）| NOPUSH_20261031_223151（删除）|
|---|---|---|
| 断连 | **3 次 `10054`** | **0 次** |
| 结果 | 76 秒后退出 | **持续存活，进房间成功** |

**断连时序**：`应答 seq=62` → `推送 seq=1062(body=70)` → `推送 seq=1062(body=190)` → `10054`（0 秒内）
⇒ **同一请求两条推送共用 `seq = 请求seq+1000`**（GOLDEN L1196），客户端判重放 ⇒ RST。

---

## §8 ★★★ 修复从未被执行

```
GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_server.py   D7EEB456…  1323 行  ← 两轮实机都用它
CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py   FF473204…  1575 行  ← 有全部修复
```

VERIFIED 独有：`build_startgame_payload()` L626（注释"严格对齐 `0x00625BE0`/`0x00625CE0`"）· `build_room_push()` L642 · `11/13` memberCount=1 **且 maxPlayers=1** L1002 · 推送 seq 用 `out_seq` L1477 · `11/4` ready→推 StartGame L1058 · `mmstart`→推 StartGame L1150 · 102 playerdata L1193-1237

★ **VERIFIED 跑过后依然无效**（2026-10-31 23:50 实测：`11/13 x2 / 11/4 x6 / seq 已递增 / 无断连`，但房间内仍无反应）⇒ **VERIFIED 的推送格式与客户端期望仍不匹配**。

---

## §9 `dwRoomImp` 结构与成员表

**构造器 `0x62C000` / `0x62DEE0`，vtable `0xDC7274`，大小 `0x3A128`**

| 偏移 | 含义 |
|---|---|
| `+0x278` | 房间已建立标志（唯一置 1 = `0x62FBBB`）|
| `+0x340` / `+0x7470` | 两个数组各 **50** × 0x238（MatchMakingInfo）|
| `+0xE360` | 选中索引（-1 = 无）|
| **`+0xE368`** | **成员表 19 × 0x1D0** |
| **`+0x105D8`** | **成员数** |
| **`+0x105FE`** | **人数上限**（← dvar `"3265"`）|
| `+0x10768` / `+0x10778` | RoomStateUpdated 状态 / float |

**成员记录**：`+0x00 u64 账号` / `+0x88 阵营` / `+0x8C 变更序号` / **`+0x90 Ready`** / `+0x94 ping(1000)` / `+0xAC 投票` / `+0xB0 队内就绪计数` / `+0xB1 SetPilot` / `+0xB2..0xBC 明细` / `+0x1A0..0x1C8 明细`

---

## §10 21 匹配层

- `21/5` 两形态：35B（`#0b=10`）/ 75B（`#08=796` 版本、`#09=123` playlist id）
- 都含 `0xD692ADAB`（魔数 A = query criterion，crc32 穷搜 0 命中）
- ★★ **魔数 B `0x8D51E398` = `crc32("combat")`**（配套 `crc32("sd")=0x0F149D8B`、`crc32("playlist")=0xD782112D`、`crc32("coop")=0xF93C0DB8` 均在语料对上）
- `21/1` 携带 `playlist id + version + 地图 crc32 + 模式族 crc32 + 人数上限(=`rule 3265`)`
- `rule 3265` = playlist 总人数上限（`2×vsrule`）
- ★★ 顺序 13/13 次 `11/13` 先于 `21/1`

---

## §11 诚实边界（本卷全部）

1. **Manifold 在语料中 0 真实样本**（6848 条严格扫描：bit0 对齐 0 条；任意偏移 1 条已证为巧合）⇒ 构造的字节序列**纯按反汇编推导，无抓包佐证**。
2. **dwRoom opcode ↔ srpc (svc,task) 无静态表**：opcode 是 `dwLobbyImp` 事件号，srpc 键是另一层；两者通过 `0x7E7C90` 回调间接相接，**具体数值运行期由订阅报文写入**。
3. **`0x82E1458` 字段描述符表磁盘全 0**（运行时填）⇒ 47 种 type 的字段只能从处理函数反推（本卷已完成）。
4. `0x0D` 的反序列化器**内联**、经 `vtable+0x144` 虚派发，无法从 call 图追；数组上界来自 `[room+0x105D8]`。
5. `0x12` 的 12~13 个 16 位槽、`0x1D` 的 15 个 8 位槽**语义未定**。
6. **本地身份槽是账号 ID 还是会话 ID64 未百分百定死**（`0x801490` 覆盖自 `[会话+0x50]/[+0x54]`，静态默认值恰为账号 ID）。
7. 76 项表 `0xB83744` 是 **`dwLobbyImp` 事件兜底**，不是 dwRoom 协议（13 项无处理 / 10+ 项落空桩）。
8. `0x85` 帧需要 HMAC-SHA1[:16] + seq 计数器（密钥来自 KDF `BDDATA`/`CLIENTCHAL`）；链路本有会话密钥，但**Manifold 内容从未被真实流量验证**。

---

## §12 工具

| 工具 | 用途 |
|---|---|
| `s138_bitstream.py` | **位流写入器（MSB-first，还原 `0xB777C0`）+ Ready/ChangeTeam/Vote/RoomStateUpdated 构造器 + 自测** |
| `s138_manifold.py` | Manifold 模型 + 语料扫描 + 自测 |
| `s138_find_manifold.py` / `s138_check_cand.py` | 全语料搜 Manifold 样本（含滑动窗口） |
| `s138_layer_test3.py` | 三层分层验证（`11/4` blob 是否 dwRoom） |
| `s138_bitverify.py` | 位流反向验证 |
| `s138_upchain.py` / `s138_ptrref.py` / `s138_deepref.py` / `s138_isvfunc.py` | 调用链/指针/虚函数分析 |
| `dyn138_onetouch_dump.py` / `dyn138_watcher.py` / `dyn138_clean.py` | 实机：一键转储/早期句柄探针/提权清理 |
| `dyn138_create_room_probe.py` / `dyn138_nopush_launch.py` / `dyn138_verified_launch.py` | 建房探针 / 对照实验 / VERIFIED 版启动 |

---

## §13 方法论

1. ★★★ **两路独立互证才算定案**：房间不走 `6/5` 由投递链 + 248B 记录两路分别得出。
2. ★★★ **先验"我跑的是哪个版本"**：两轮实机跑旧版 ⇒ 所有"修复无效"判断作废。**跑之前先 hash + 报版本。**
3. ★★★ **因果只能靠改一个变量证**：删 `ready_push.on` ⇒ 断连 0 次。
4. ★★ **症状矛盾 ⇒ 找"被挡住"，不是"坏掉"**；**用户的"不对称"= 代码里两条路径**。
5. ★★ **判据反直觉 ⇒ 查值域语义**：`clientState < 3` 查 CA_\* 表就通了。
6. ★★ **"零引用"先查是不是虚表/遍历派发**：`0x6371F0` 无 `call [reg+0x25B8]`，是 `[esi]` + 基址负偏移。
7. ★★ **算术自证结构**：`0x340+50*0x238=0x7230` 否掉"49"；`0xE368+19*0x1D0=0x105D8` 证实 19。
8. ★★★ **扫描形式会漏整族**：构造器写在**栈上** `mov [ebp-x],imm32`，扫 `mov [reg],imm` 会漏掉整个构造器族（这是早期 47 type 全表扫不出来的真因）。
9. ★★ **分层验证先排除错误假设**：`11/4` 的 blob 实测走不通 `0x637000` ⇒ 避免按错误前提改服务端。
