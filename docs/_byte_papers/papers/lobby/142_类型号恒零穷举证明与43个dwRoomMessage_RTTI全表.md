# 142 · 类型号恒为 0 的穷举证明 + 43 个 dwRoomMessage RTTI 全表

> 前序：141（服务注册链）、140（类型号定案）、138（dwRoom 协议层）
> 性质：**穷举扫描 + RTTI 名池提取 + 集合对账**。
> 本卷闭合 141 的未闭合项 1、2，并首次拿到 **43 个 `dwRoomMessage*` 类的 RTTI 全名**。

---

## §0 九条结论

1. ★★★★★ **`srpc+4`（类型号分配器）在全镜像只有一处写点：`0xB82179 mov [r6+4],r3`（置 0），之后无任何自增。**
   ⇒ **类型号恒为 0**（穷举证明，见 §1）。
2. ★★★★ **`0xB80D90` 的 7 个 helper 全文无一处 `[reg+4]` 的写**（只有 7 处 `8b 4b 04` 读）。
3. ★★★★★ **首次取得 43 个 `dwRoomMessage*` RTTI 全名**（`0xE6F094..0xE6F7FC`，地址连续），
   与 138/140 的 47 项表做第三方对账（§3）。
4. ★★★★ **对账结果：138 表 38 个类中 36 个有 RTTI 铁证**；2 个"缺"是命名差异
   （`PrimaryWeaponCountChange`→RTTI 里是 `PlayerPrimaryWeaponCountChange`；`SpyMessageText` 无独立 RTTI）。
5. ★★★★ **RTTI 里有、138 表未覆盖的 6 个具体类**：
   `RequestMemberList`、`LeaveWithMe`、`SyncPartyPendingToNewMember`、
   `MyPartyInvitation`、`MemberDetailsNoUpdated`、`MyPartyInvitationRejected`
   ⇒ **这 6 个是 138/140 表里未定位到类型号的类**（对应表里某些空 handler）。
6. ★★★ **140 表的 75 项中 13 个是空 handler**：类型号 `14/22/23/24/25/26/27/28/36/37/44/45/59`。
7. ★★★ **62 个非空 handler 对应 41 个具体类** ⇒ **多个类型号共用同一 handler**
   （type 7/8 同 `0xB82E03`、9/10 同 `0xB82E29`、11/12 同 `0xB82DB3` 等）。
8. ★★ **`dwRoomMessage` 基类 + `Manifold` 是 2 个非具体类**（RTTI 里 `. ?AVdwRoomMessage@@` 与 `.?AVdwRoomMessageManifold@@`）。
9. ★★ **段2（0xE6xxxx）只有 RTTI 名字串本体**，type_info / COL / vtable 全在文件空洞里
   （`0xD77818` 这个共享 type_info vftable 零引用），**无法从名字反查到 vtable**。

---

## §1 ★★★★★ 类型号恒为 0：穷举证明

### 1.1 唯一的写点

```asm
0xB82130  srpc ctor
0xB82173  mov dword [esi], 0xD599DC     ; vtable
0xB82179  mov dword [esi+4], ebx        ; ★ ebx = 0（0xB8216C xor ebx,ebx）
```

全镜像 `0xB7A000..0xB8C000` 内所有对 `[reg+4]` 的**写**（`89/C7/FF` 三族）逐条列出：

| 地址 | 指令 | 归属 |
|---|---|---|
| `0xB7AED1` | `mov [r6+4], r0` | 其他对象 |
| `0xB7FABF` | `mov [r0+4], r1` | 数组析构 |
| `0xB7FB68` / `0xB7FC75` | `mov [r7/r6+4], r1` | 哈希表桶数 |
| `0xB815FB` | `mov [r6+4], r3` | 其他 helper |
| **`0xB82179`** | **`mov [r6+4], r3`** | **★ srpc ctor 置 0** |
| `0xB83B46` | `mov dword [r6+4], 0xD599FC` | 子对象 vtable |
| `0xB83E03` | `mov [r6+4], r7` | 其他 |
| `0xB85196`/`0xB853F5`/`0xB85609` | `mov dword [r6+4], 0x...` | 子对象 vtable |
| 其余 17 处 | `mov dword [r6/r0+4], <vtable>` | 子对象 vtable |

**没有任何 `inc dword [reg+4]` 命中 srpc。**

### 1.2 读侧

7 个 helper 全部是 `8b 4b 04`（`mov ecx,[ebx+4]`），**没有一处 `+1`**：
```
0xB80E37  0xB80F67  0xB81097  0xB811C7  0xB812F7  0xB81427  0xB81557
```

**⇒ 类型号恒为 0。**

### 1.3 这与"每张表只有空串一个条目"完全自洽

141 卷已证：68 个注册点名字参数 100% 是空串 `""`。
**每张表只有 1 个条目、类型号恒为 0 ⇒ 表内不存在歧义。**

---

## §2 ★★★ 141 未闭合项 2：srpc RTTI 名

**结论：静态拿不到。** 原因：
- `0xD599DC - 4` 处读为 0（段2 空洞）
- `0xD77818`（共享 type_info vftable）在全镜像零引用
- 段2 覆盖 0.2%，RTTI 结构体（type_info/COL）全部落在空洞

★ **但换了一条路拿到了 43 个类名本身**（§3），这比 RTTI 结构更有用。

---

## §3 ★★★★★ 43 个 `dwRoomMessage*` RTTI 全表

| 地址 | 类名 | 地址 | 类名 |
|---|---|---|---|
| `0xE6F094` | NetcafePrivileges | `0xE6F424` | RequestMemberList ★ |
| `0xE6F0C4` | QQMembership | `0xE6F454` | Leave |
| `0xE6F0EC` | UpdateWarGodData | `0xE6F478` | LeaveWithMe ★ |
| `0xE6F118` | UpdateCreditRating | `0xE6F4A0` | JoinWithParty |
| `0xE6F148` | UpdateDlcLevel | `0xE6F4CC` | JoinWithMe |
| `0xE6F174` | AvatarInfo | `0xE6F4F4` | SyncPartyPendingToNewMember ★ |
| `0xE6F19C` | DMZLeagueTicketStateChange | `0xE6F52C` | MyPartyInvitationRejected ★ |
| `0xE6F1D4` | InRoomStateChange | `0xE6F560` | MyPartyInvitation ★ |
| `0xE6F204` | PlayerPrimaryWeaponCountChange | `0xE6F590` | JoinRequest |
| `0xE6F240` | ClanNameChange | `0xE6F5B8` | Join |
| `0xE6F26C` | RoomStateUpdated | `0xE6F5D8` | JoinMemberInfos |
| `0xE6F298` | PlaylistWeights | `0xE6F604` | Score |
| `0xE6F2C4` | Vote | `0xE6F628` | Card |
| `0xE6F2E4` | SetPilot | `0xE6F648` | MemberDetailsNoUpdated ★ |
| `0xE6F308` | ChangeTeamRequest | `0xE6F67C` | MemberDetailsQuery |
| `0xE6F338` | ChangeTeam | `0xE6F6AC` | MemberDetails |
| `0xE6F360` | P2PInfo | `0xE6F6D8` | MemberInfoAdd |
| `0xE6F384` | StartCountingDown | `0xE6F704` | MemberInfoEXT |
| `0xE6F3B4` | Ready | `0xE6F730` | StartGameFailed |
| `0xE6F3D8` | RoomInfo | `0xE6F75C` | StartGame |
| `0xE6F3FC` | MemberList | `0xE6F7C0` | Text |
| | | `0xE6F7E0` | **(base)** |
| | | `0xE6F7FC` | **Manifold** |

★ 带 ★ 的 6 个是 138/140 表里**未定位到类型号**的具体类。

---

## §4 ★★★★ 与 138/140 表的对账

### 4.1 138 表的 38 个类 → 36 个有 RTTI 铁证

| type | 类 | RTTI |
|---|---|---|
| 0x02 Text | ✓ | 0x03 StartGame ✓ |
| 0x04 StartGameFailed | ✓ | 0x05 Join ✓ |
| 0x06 JoinRequest | ✓ | 0x07 JoinWithMe ✓ |
| 0x09 Leave | ✓ | 0x0A MemberInfoAdd ✓ |
| 0x0C MemberInfoEXT | ✓ | 0x0D/0x0E MemberList ✓ |
| 0x0F RoomInfo | ✓ | **0x10 Ready ✓** |
| 0x11 StartCountingDown | ✓ | 0x12 AvatarInfo ✓ |
| 0x13 P2PInfo | ✓ | **0x14 ChangeTeam ✓** |
| 0x15 ChangeTeamRequest | ✓ | 0x16 PlaylistWeights ✓ |
| 0x17 RoomStateUpdated | ✓ | 0x18 Score ✓ |
| **0x1A Vote** | ✓ | 0x1B SetPilot ✓ |
| 0x1C Card | ✓ | 0x1D MemberDetails ✓ |
| 0x1E MemberDetailsQuery | ✓ | 0x20 UpdateDlcLevel ✓ |
| 0x21 UpdateCreditRating | ✓ | 0x22 UpdateWarGodData ✓ |
| 0x23 QQMembership | ✓ | 0x24 NetcafePrivileges ✓ |
| 0x25 JoinMemberInfos | ✓ | 0x26 ClanNameChange ✓ |
| 0x27 PrimaryWeaponCountChange | **命名差异** | 0x2B JoinWithParty ✓ |
| 0x2C SpyMessageText | **无独立 RTTI** | 0x2D InRoomStateChange ✓ |
| 0x2E DMZLeagueTicketStateChange | ✓ | |

**⇒ 138 的 type→类 对应关系获得 36/38 的独立印证。**

### 4.2 6 个 RTTI 有、表里没定位到的类

```
RequestMemberList           → 可能对应表里某个空 handler（14/22-28/36/37/44/45/59）
LeaveWithMe
SyncPartyPendingToNewMember
MyPartyInvitation
MyPartyInvitationRejected
MemberDetailsNoUpdated
```

### 4.3 数量关系

```
140 表 75 项 − 13 个空 handler = 62 个非空 handler
RTTI 43 个 − base − Manifold = 41 个具体类
```

**⇒ 多个类型号共用同一 handler**（type 7/8 → `0xB82E03`、9/10 → `0xB82E29`、11/12 → `0xB82DB3` 等）。

---

## §5 与"房间消息 = 类型号 7/8"的关系

本卷**未改动** 140 的结论，反而加强了它：

- 类型号恒为 0（§1）⇒ 类型号**不是**注册顺序，而是**表下标语义**
- 140 的 `0xB83744[类型号-1]` 索引规则不受影响（那是**消息泵**的表，不是 srpc 的注册表）
- **★ 两个"类型号"是不同的东西：**
  - **srpc 注册表的类型号**（`srpc+4`）= 恒 0，仅用于哈希表节点
  - **dwLobbyImp 消息泵的类型号**（`[ebp-0x78]`）= 来自 4 字节名 FNV 查表，决定 `0xB83744` 下标

★★ **这是本卷最重要的澄清：两个"类型号"同名不同义，不能混用。**

---

## §6 诚实边界

1. **6 个 RTTI 类（§4.2）未映射到类型号**。需要动态观测或更深的构造器扫描。
2. **RTTI 结构（type_info/COL/vtable）在段2 空洞**，无法从名字反查 vtable，因此**无法用 vtable 交叉验证 138 的构造器自证**。
3. **`0x2C SpyMessageText` 无独立 RTTI**（可能内联或复用基类）。
4. **另 7 张哈希表的注册者仍未追**（`+0x08/+0x20/+0xD4/+0xF4/+0x15C/+0x1A4/+0x1D4` 的 `lea` 命中都在别处，非注册点）。
5. **`0xDAE091` 的 3165 次 `push` 里只分析了 68 次**（注册相关）。

---

## §7 工具

| 工具 | 用途 |
|---|---|
| `tools/s142a_inc4.py` / `s142d_fix.py` / `s142e_w.py` | `[reg+4]` 读/写穷举（**修正了 `(m&0xC7)==0x40` 的判据错误**） |
| `tools/s142f_other7.py` | 另 7 张哈希表的 `lea` 定位 |
| `tools/s142g_rtti.py` / `s142h_rttinames.py` / `s142i_msgs.py` | RTTI 名池提取 |
| `tools/s142j_align.py` / `s142m_ti.py` | type_info→COL→vtable 反查（0 命中） |
| `tools/s142k_cross.py` / `s142n_cross.py` | 与 138/140 表对账 |

## §8 方法论

1. ★★★★★ **`(m & 0xC7) == 0x40` 判据错误**：`mod=01` 应判 `(m>>6)==1` 且 `(m&7)!=4`。
   这个错误让我在 141 卷误报"`0xB80D90` 全文无 `[reg+4]` 读"。
2. ★★★★ **"恒为某值"要穷举写侧才能下结论**：只扫读侧不够。
3. ★★★★ **RTTI 名池是独立于 vtable 的证据源**：即使结构体在空洞，名字串本体仍可提取。
4. ★★★ **两个同名字段要先确认是不是同一个东西**（srpc 类型号 vs 消息泵类型号）。
5. ★★ **集合对账（RTTI 类 vs 表项）能发现"有类无 handler"的缺口。**
