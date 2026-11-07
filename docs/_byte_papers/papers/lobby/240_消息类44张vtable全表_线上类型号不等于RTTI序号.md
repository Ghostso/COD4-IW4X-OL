# 240 消息类 44 张 vtable 全表 + 线上类型号 ≠ RTTI 序号

## 一句话结论

`dwRoomImp` 内**连续 44 张 `dwRoomMessage*` vtable**（`0xDC74F4..0xDC7704`，步进 **12 字节** = `[COL][写][读]`）已全表取出并配上 MSVC RTTI 全名；**但「vtable 序号」不是「线上类型号」** —— 构造函数写进 `[obj+4]` 的那个字节才是线上类型号，实测与序号**不等**（`ChangeTeam` 序号 28，线上 `0x14`=20；`P2PInfo` 序号 27，线上 `0x13`=19；`ClanNameChange` 序号 34，线上 `0x26`=38）。

---

## 证据表

### E1 — 44 张 vtable 全表（`0xDC74F4` 起，步进 12）

| 序号 | vtable | RTTI 全名 | 写侧 | 读侧 |
|---|---|---|---|---|
| 0 | `0xDC74F4` | `.?AVdwRoomMessageManifold@@` | `0x625520` | `0x6256C0` |
| 1 | `0xDC7500` | `.?AVdwRoomMessageText@@` | `0x625970` | `0x625A20` |
| 2 | `0xDC750C` | `.?AVdwRoomSpyMessageText@@` | `0x625B30` | `0x625B90` |
| 3 | `0xDC7518` | `.?AVdwRoomMessageStartGame@@` | `0x625BE0` | `0x625CE0` |
| 4 | `0xDC7524` | `.?AVdwRoomMessageStartGameFailed@@` | `0x628320` | `0x625DB0` |
| 5 | `0xDC7530` | `.?AVdwRoomMessageMemberInfoEXT@@` | `0x625E20` | `0x625F50` |
| 6 | `0xDC753C` | `.?AVdwRoomMessageMemberInfoAdd@@` | `0x6260A0` | `0x626130` |
| 7 | `0xDC7548` | `.?AVdwRoomMessageMemberDetails@@` | `0x6261C0` | `0x6263C0` |
| 8 | `0xDC7554` | `.?AVdwRoomMessageMemberDetailsQuery@@` | `0x628320` | `0x625DB0` |
| 9 | `0xDC7560` | `.?AVdwRoomMessageMemberDetailsNoUpdated@@` | `0x626650` | `0x627CE0` |
| 10 | `0xDC756C` | `.?AVdwRoomMessageCard@@` | `0x626680` | `0x626730` |
| 11 | `0xDC7578` | `.?AVdwRoomMessageScore@@` | `0x626810` | `0x6268A0` |
| 12 | `0xDC7584` | `.?AVdwRoomMessageJoinMemberInfos@@` | `0x626960` | `0x6269E0` |
| 13 | `0xDC7590` | `.?AVdwRoomMessageJoin@@` | `0x626A80` | `0x626B30` |
| 14 | `0xDC759C` | `.?AVdwRoomMessageJoinRequest@@` | `0x6270D0` | `0x627230` |
| 15 | `0xDC75A8` | `.?AVdwRoomMessageMyPartyInvitation@@` | `0x627430` | `0x627560` |
| 16 | `0xDC75B4` | `.?AVdwRoomMessagMyPartyInvitationRejected@@` | `0x6276A0` | `0x627700` |
| 17 | `0xDC75C0` | `.?AVdwRoomMessageSyncPartyPendingToNewMember@@` | `0x627800` | `0x627990` |
| 18 | `0xDC75CC` | `.?AVdwRoomMessageJoinWithMe@@` | `0x627D30` | `0x627B40` |
| 19 | `0xDC75D8` | `.?AVdwRoomMessageJoinWithParty@@` | `0x627BB0` | `0x627C30` |
| 20 | `0xDC75E4` | `.?AVdwRoomMessageLeaveWithMe@@` | `0x626650` | `0x627CE0` |
| 21 | `0xDC75F0` | `.?AVdwRoomMessageLeave@@` | `0x627D30` | `0x627B40` |
| 22 | `0xDC75FC` | `.?AVdwRoomMessageRequestMemberList@@` | `0x626650` | `0x627CE0` |
| 23 | `0xDC7608` | `.?AVdwRoomMessageMemberList@@` | `0x627D80` | `0x627E00` |
| 24 | `0xDC7614` | `.?AVdwRoomMessageRoomInfo@@` | `0x627EA0` | `0x627EE0` |
| 25 | `0xDC7620` | `.?AVdwRoomMessageReady@@` | `0x6287D0` | `0x629090` |
| 26 | `0xDC762C` | `.?AVdwRoomMessageStartCountingDown@@` | `0x628320` | `0x625DB0` |
| 27 | `0xDC7638` | `.?AVdwRoomMessageP2PInfo@@` | `0x627FC0` | `0x6280B0` |
| **28** | `0xDC7644` | **`.?AVdwRoomMessageChangeTeam@@`** | **`0x6281D0`** | **`0x628260`** |
| 29 | `0xDC7650` | `.?AVdwRoomMessageChangeTeamRequest@@` | `0x628320` | `0x625DB0` |
| 30 | `0xDC765C` | `.?AVdwRoomMessageSetPilot@@` | `0x628370` | `0x6283C0` |
| 31 | `0xDC7668` | `.?AVdwRoomMessageVote@@` | `0x628320` | `0x625DB0` |
| 32 | `0xDC7674` | `.?AVdwRoomMessagePlaylistWeights@@` | `0x628430` | `0x6284E0` |
| 33 | `0xDC7680` | `.?AVdwRoomMessageRoomStateUpdated@@` | `0x6285B0` | `0x628610` |
| 34 | `0xDC768C` | `.?AVdwRoomMessageClanNameChange@@` | `0x6286C0` | `0x628740` |
| 35 | `0xDC7698` | `.?AVdwRoomMessagePlayerPrimaryWeaponCountChange@@` | `0x6287D0` | `0x629090` |
| 36 | `0xDC76A4` | `.?AVdwRoomMessageInRoomStateChange@@` | `0x6287D0` | `0x629090` |
| 37 | `0xDC76B0` | `.?AVdwRoomMessageDMZLeagueTicketStateChange@@` | `0x6287D0` | `0x629090` |
| 38 | `0xDC76BC` | `.?AVdwRoomMessageAvatarInfo@@` | `0x628840` | `0x628B90` |
| 39 | `0xDC76C8` | `.?AVdwRoomMessageUpdateDlcLevel@@` | `0x628FD0` | `0x629020` |
| 40 | `0xDC76D4` | `.?AVdwRoomMessageUpdateCreditRating@@` | `0x6287D0` | `0x629090` |
| 41 | `0xDC76E0` | `.?AVdwRoomMessageUpdateWarGodData@@` | `0x629110` | `0x6291B0` |
| 42 | `0xDC76EC` | `.?AUdwRoomMessageQQMembership@@` | `0x628320` | `0x625DB0` |
| 43 | `0xDC76F8` | `.?AUdwRoomMessageNetcafePrivileges@@` | `0x628320` | `0x625DB0` |

（`46` 张初看以为 44，实为 **44**；`0xDC74F4` 到 `0xDC7704` 步进 12 = `(0xDC7704-0xDC74F4)/12 = 44`）

**取出方法**：每条目三槽 = `[+0]=COL 指针][+4]=写][+8]=读]`；COL 的 `+0xC` 指向 MSVC `TypeDescriptor`，`TypeDescriptor+8` 起是 `.?AV...@@` 名字串。

### E2 — ★线上类型号 = 构造函数写进 `[obj+4]` 的字节，**不是** vtable 序号

| 类 | vtable 序号 | 构造点 | `[obj+4]` = 线上类型号 | 差 |
|---|---|---|---|---|
| `ChangeTeam` | **28** | `0x6281BF` 装 vtable，`0x6281B8` 写 `[eax+4]=0x14` | **0x14 = 20** | −8 |
| `P2PInfo` | **27** | `0x627F50` 装 vtable，前文写 `[eax+4]=0x13` | **0x13 = 19** | −8 |
| `MyPartyInvitation` | 15 | `0x6273C3` / `0x6273BC` | **0x28 = 40** | +25 |
| `SyncPartyPendingToNewMember` | 17 | `0x62779F` | **0x2A = 42** | +25 |
| `ClanNameChange` | 34 | `0x62869F` | **0x26 = 38** | +4 |

**指令证据（ChangeTeam）**：
```
0x6281B8   c7 40 04 14 00 00 00     mov dword ptr [eax+4], 0x14
0x6281BF   c7 00 48 76 DC 00        mov dword ptr [eax], 0xdc7648   ; 装 vtable(+4 槽) = 序号28
```
**指令证据（P2PInfo）**：
```
0x627F4?   mov dword ptr [eax+4], 0x13
0x627F50   mov dword ptr [esi], 0xdc763c                          ; 序号27
```

### E3 — 线上类型号 → 分派表：`0x634870` 用**线上号**索引，且表长 `0x2F`

```
0x6348A5  je  0x634907            ; [ebx+0x1c]==0 -> 跳过（未初始化）
0x6348AA  push 3
0x6348AE  call 0xB774E0           ; R_TAG(3)：5 位标签，返回 bool
0x6348B7  push 8
0x6348C2  call 0xB772E0           ; 读 8 位 -> [ebp-0xA88]  ★ 这就是线上类型号
0x6348C7  movzx eax, byte [ebp-0xA88]
0x6348D1  mov dword [edx+0x1C], 1 ; 标记已初始化
0x6348D8  mov esi, [eax*4 + 0x82E1458]   ; ★ 工厂表（44 项，本卷实测全 0）
0x6348E5  test esi,esi / je 0x63494A
0x634902  call esi                        ; 先调工厂（若有）
0x63494A  cmp eax, 0x2E                   ; ★ 上界 0x2E = 46
0x63494D  ja  0x636EBA                    ; >0x2E -> 静默返回
0x634953  jmp dword ptr [eax*4 + 0x636F3C]  ; ★ 分派表，47 项
```

**★★ 表和读侧的对应关系是「相邻类型号共享一个读函数」，不是「一个号一个读函数」。**
下表用**分支起止地址**切分（每个分支到下一个表项目标为止），只统计**落在本分支区间内**的 `call`：

| 线上号 | 分支区间 | 分支内调到的 `dwRoomMessage*` 读函数 | 对应类 |
|---|---|---|---|
| `0x00` | `0x636F02..0x636F40` | **无** — 失败退出（`pop/pop/xor/ret`） | ★ 失败返回 |
| `0x01` | `0x636EBA..0x636F02` | **无** — **静默忽略** | ★ 无处理 |
| `0x02` | `0x63495A..0x634A28` | 无 vtable 读；调 `0x625940`=**`Text` 构造函数**（`0x62595E` 装序1 vtable） | `Text`（构造后送 UI） |
| `0x03` | `0x634AC2..0x634C3C` | `0x625CE0` | **`StartGame`(序3)** |
| `0x04` | `0x634C3C..0x634CB3` | `0x625DB0`→`NetcafePrivileges` | 共用读 |
| `0x05` | `0x634D35..0x634F13` | `0x626B30` | `Join`(序13) |
| `0x06` | `0x634F13..0x6352DC` | `0x627230` | `JoinRequest`(序14) |
| `0x07` | `0x635399..0x6354A9` | `0x627B40` ×2 | `Leave`(序21) |
| `0x08` | `0x6354A9..0x63550B` | `0x627CE0` | `RequestMemberList`(序22) |
| `0x09` | `0x63550B..0x6355C2` | `0x627B40` | `Leave` |
| `0x0A` | `0x6356B8..0x6357BB` | `0x626130` | `MemberInfoAdd`(序6) |
| **`0x0B`** | `0x636EBA..0x636F02` | **无 — 静默忽略** | ★ 空 |
| `0x0C` | `0x6355C2..0x6356B8` | `0x625F50` | `MemberInfoEXT`(序5) |
| `0x0D` | `0x6357BB..0x635814` | 无 vtable 读（`0x627E00`） | `MemberList` |
| `0x0E` | `0x635814..0x635968` | `0x627E00` | `MemberList`(序23) |
| `0x0F` | `0x635968..0x6359FC` | `0x627EE0` / `0x629090` | `RoomInfo`(24) / `Ready`(25) |
| `0x10` | `0x6359FC..0x635AC3` | `0x629090`/`0x626730` | `Ready` / `Card`(10) |
| `0x11` | `0x635E57..0x635F2C` | `0x625DB0` | 共用读 |
| `0x12` | `0x6361B6..0x636291` | `0x628B90` | **`AvatarInfo`(序38)** |
| **`0x13`** | `0x635F2C..0x6361B6` | **`0x6280B0`** | **★ `P2PInfo`(序27)** |
| **`0x14`** | `0x636336..0x6365A3` | **`0x628260`** | **★ `ChangeTeam`(序28)** |
| `0x15` | `0x6365A3..0x636715` | `0x625DB0`/`0x6283C0` | 共用 / `SetPilot`(30) |
| `0x16` | `0x6367C3..0x6367F5` | `0x6284E0` | `PlaylistWeights`(32) |
| `0x17` | `0x6367F5..0x6368A7` | `0x628610` | `RoomStateUpdated`(33) |
| `0x18` | `0x635D8F..0x635E57` | `0x6268A0` | `Score`(11) |
| **`0x19`** | `0x636EBA..0x636F02` | **无 — 静默忽略** | ★ 空 |
| `0x1A` | `0x636291..0x636336` | `0x625DB0` | 共用读 |
| `0x1B` | `0x636715..0x6367C3` | `0x6283C0` | `SetPilot` |
| `0x1C` | `0x635AC3..0x635B47` | `0x626730`/`0x6263C0` | `Card` / `MemberDetails` |
| `0x1D` | `0x635B47..0x635BE6` | `0x6263C0` | `MemberDetails`(7) |
| `0x1E` | `0x635C5B..0x635D8F` | `0x625DB0`/`0x6268A0` | 共用 / `Score` |
| `0x1F` | `0x635BE6..0x635C5B` | `0x627CE0`/`0x6268A0` | `RequestMemberList`/`Score` |
| `0x20` | `0x6368A7..0x63693E` | `0x629020` | `UpdateDlcLevel`(39) |
| `0x21` | `0x63693E..0x6369FD` | `0x629090`/`0x6291B0` | `Ready`/`UpdateWarGodData` |
| `0x22` | `0x6369FD..0x636ABE` | `0x6291B0` | `UpdateWarGodData`(41) |
| `0x23` | `0x636ABE..0x636B6D` | `0x628740` | `ClanNameChange`(34) |
| `0x24` | `0x636B6D..0x636C1D` | `0x628740` | `ClanNameChange` |
| `0x25` | `0x634CB3..0x634D35` | `0x6269E0`/`0x626B30` | `JoinMemberInfos`/`Join` |
| `0x26` | `0x636C1D..0x636CD1` | `0x628740` | `ClanNameChange` |
| `0x27` | `0x636CD1..0x636D7F` | `0x629090` | `Ready` |
| **`0x28`/`0x29`/`0x2A`** | `0x636EBA..0x636F02` | **无 — 静默忽略** | ★ 空 |
| `0x2B` | `0x6352DC..0x635399` | `0x627C30`/`0x627B40` | `JoinWithParty`/`Leave` |
| `0x2C` | `0x634A28..0x634AC2` | 无 vtable 读；调 `0x625AB0`=**`Text`+`SpyMessageText` 双构造** | ★ 双类复合 |
| `0x2D`/`0x2E` | `0x636D7F..0x636E0A` / `0x636E0A..0x636EBA` | `0x629090` | `Ready` |

**★ 关键结构发现**：`0x636EBA` 与 `0x636F02` 是 `0x634870` 的**两个共享出口**，被 6 个表项（`0x01/0x0B/0x19/0x28/0x29/0x2A`）直接指向 ⇒ **这 6 个线上类型号「合法但无处理」**（静默丢弃），不是「非法」。

**★ `0x2C` 分支是双类复合**：`0x625AB0` 在同一个栈对象上连续装两次 vtable ——
```
0x625ACF  mov dword [esi], 0xDC7504   ; Text  vtable（序1）
0x625AD5  call 0x625A20               ; Text 读
0x625ADD  mov dword [esi], 0xDC7510   ; SpyMessageText vtable（序2）
0x625AE3  call 0x625A20               ; 同一读函数再读一遍
```
⇒ 线上号 `0x2C` = **`Text` + `SpyMessageText` 两个字段块**。

### E4 — ★工厂表 `0x82E1458` 在磁盘镜像里**全 0**（44 项）

```
0x6348D8  mov esi, [eax*4 + 0x82E1458]
0x6348E5  test esi, esi
0x6348E7  je 0x63494A            ; 恒跳 => 工厂永不调用
```
`0x82E1458..0x82E150C` 实测 **44 个 DWORD 全 `0x00000000`**。neighboring `0x82E13FC..0x82E1454` 有 21 个非零指针（`0x0810E0xx` 段），但**那是另一张表**（`0x82E13FC` 是 `0x639D00` 里创建的单例）。

**结论**：工厂表是**运行时填充**（`0x639D00` 建 3 个单例那条链），**静态不可读**；但 `0x6348E7 je` 让它**即使为空也不影响分派** —— 分派靠 `0x636F3C` 表，不靠工厂。

### E5 — vtable 三槽的第二槽（写）才是装载点：11 处 `mov [reg], <triple+4>`

| 构造点 | 类 | 线上号 |
|---|---|---|
| `0x62595E` / `0x625ACF` | `Text` | ??（走 `0x625A20` 读，`[+4]` 写在别处） |
| `0x625ADD` | `SpyMessageText` | ?? |
| `0x626C3D` / `0x626E90` / `0x656117` | `JoinRequest` | ?? |
| `0x6273C3` | `MyPartyInvitation` | **0x28** |
| `0x62779F` | `SyncPartyPendingToNewMember` | **0x2A** |
| `0x627F50` | `P2PInfo` | **0x13** |
| `0x6281BF` | `ChangeTeam` | **0x14** |
| `0x62869F` | `ClanNameChange` | **0x26** |

**剩余 33 类没有独立构造函数**（它们全走 `0x628320` 共用写侧 / `0x625DB0` 共用读侧），`[+4]` 由**其它路径**写入（栈上临时对象，见 234 卷）。

---

## 边界表

| # | 未解项 | 可独立核验任务 | 已穷尽排查记录 |
|---|---|---|---|
| B1 | 线上号与 vtable 序号的**完整映射表**（44 项） | 对每个 `dwRoomMessage*` 找其构造函数的 `mov [reg+4], imm`；对 33 个无构造函数的类，追 `0x628320`/`0x625DB0` 调用点前栈对象的 `[esp+8]` 赋值 | ⚠️ 部分。已得 5 对确定值（E2）。其余 39 项的 `[+4]` 写在栈上临时对象，本卷未逐点取完 |
| B2 | 表项 `0x02`/`0x03` 等分支里调用的「读函数」是否等于该类 vtable 的读槽 | 逐表项断点：`0x63495A` 调 `0x625940`（是 `Text` ctor 而非读侧）；需区分 ctor vs reader | ⚠️ 已发现混淆：`0x63495A` 调的是 `0x625940`（**构造函数**，`0x62595E` 装 vtable），不是 `0x625A20` 读侧。**本卷 E3 表的「读函数」列需按此修正** |
| B3 | `[ebx+0x1c]`（`0x6348A5` 判空的那个）是什么 | 反查 `dwRoomImp+0x1c` 写点 | ⚠️ 未做，标为开放。见 172 卷「`[obj+0x1C]` 是 bitstream 吗」——`0xB778E0` 里 `+0x1C` 是写游标，但这里是 `dwRoomImp+0x1c`，**不同对象** |
| B4 | 47 项表里 6 个 `0x636EBA`（`0x0B/0x19/0x28/0x29/0x2A`…）是「合法但无处理」还是「非法」 | `0x636EBA` 是否只是 `0xC3C20F`（栈检查）+ `ret` | ✅ 已读：`0x636EBA` 只 `call 0xC3C20F`（安全 cookie 检查）后返回 —— **是「静默忽略」路径**，与 `0x636F02`（真正的失败返回）不同 |

## 更正

- **169 卷「`cmp eax,0x2e / jmp [eax*4+0x636f3c]` = 138 卷 47 类型表本体」**：表本体对，但**`eax` 是线上类型号，不是 vtable 序号**。旧卷把 `0x636F3C[28]` 当成 `ChangeTeam`（因为 vtable 序号 28），实际 **`ChangeTeam` 在 `[0x14]`**，而 `[0x1C]=0x635AC3` 读的是 `Card/MemberDetails`。这是「按序号索引」造成的系统性错配。
- **172 卷「43 类写侧全存在」**：44 类（不是 43），已全表。
