# 150 · 帧更新 + 全部 dwRoomMessage 出站 vtable 全表

> 前序：149（出站三入队一真发）、148（房间按钮全链路）、147（消息泵 this=srpc）
> 性质：**帧更新入口定位 + 43 个出站消息 vtable 全表**。
> 本卷首次给出**每一条出站消息的类名与序列化函数**。

---

## §0 十一条结论

1. ★★★★★ **`0x632D90` = `dwRoomImp::FrameUpdate`**（每帧更新，room 从 `[ebp+8]` 传入）。
2. ★★★★★ **帧更新内含「主机可达性」状态机**：
   ```asm
   0x632DCA  mov eax,[0x331C0C8]
   0x632DCF  xor eax, 0xD362501F          ; ★ 解密（与 0x6332C1 同一个全局）
   0x632DD4  mov eax,[eax+0x28]
   0x632DD8  call 0x7F4F10                ; ★ 查询 host 状态 0..3
   0x632DE5  jmp [eax*4 + 0x633D10]       ; ★ 4 项跳转表
   ```
3. ★★★★ **跳转表 `0x633D10`**：
   | 状态 | 目标 | 行为 |
   |---|---|---|
   | 0 | `0x632DEC` | 检查 `[0x7887040]` → 失败报 **`EXE_HOSTUNREACH`** |
   | 1 | `0x632E1B` | 时间阈值检查 |
   | 2 | `0x632E2B` | `call 0x6295A0`（重置计时器 + 日志）|
   | 3 | `0x632DEC` | 同 0 |
4. ★★★★ **`0x7F4F10(handle)` 的语义**：
   - `handle == 0x9D`(157) → 返回 **2**
   - 否则：`vt[0x24]()` 得 `edi`；`edi==3` 且 `[0xE3F4DC4 + handle*0x18] > 0` → 返回 **1**；否则返回 `edi`
5. ★★★★ **`0x6295A0`（状态 2 的动作）**：重置 `+0x10738` 计时器 →
   比较 `+0x105F0` 与 `"playlist"`/`"combat"` → `0x629520` 取 gametype → 打日志。
   **没有网络发送。**
6. ★★★★★ **全部 43 个 `dwRoomMessage*` 类的 vtable + `slot[0]`（序列化函数）已导出**（§2）。
7. ★★★★★ **`0x634340` 真发的是 `dwRoomMessageJoinMemberInfos`**（vtable `0xDC7588`，slot0 `0x626960`），
   以及 `StartGame`(`0xDC751C`) / `MemberInfoAdd`(`0xDC7540`) / `RoomStateUpdated`(`0xDC7684`)。
8. ★★★★ **更正 138 卷的一处**：`0x628320` **不是** ChangeTeam 专属 ——
   它是 **`StartGameFailed`/`MemberDetailsQuery`/`StartCountingDown`/`ChangeTeamRequest`/`Vote`
   五个类共用的序列化器**（形态同为 `c3+8+c21+32`）。
9. ★★★★ **`dwRoomMessageReady`（`0xDC7624`，slot0 `0x6287D0`）** 与
   **`dwRoomMessageChangeTeamRequest`（`0xDC7654`，slot0 `0x628320`）** ——
   **都是 `AS_*` 房间动作构造的，都为发送而生。**
10. ★★★ **帧更新依次处理三个容器**：`+0x3A0D4`（`0x63307F`）→ `+0x3A098`（`0x6330C7`·`0x633181`）
    → `+0x3A118`（`0x6331BD`·`0x63342C`）→ **`0x63346E call 0x634340`**。
11. ★★★ **`0x632FF0` 扫描 `+0x3A0A8`（`+0x3A098` 哈希表的桶数组）**，
    取第一个非空桶作为工作项，再按时间戳比较（`fcomp [0xCADDD8]`）。

---

## §1 帧更新 `0x632D90` 骨架

```asm
0x632D90  push ebp / mov ebp,esp / sub esp,0xF8
0x632DA3  push ebx
0x632DA4  mov ebx,[ebp+8]              ; ★ room
0x632DA9  mov edi,ebx
0x632DAB  call 0x632A70                ; 子更新 1
0x632DB0  lea ecx,[ebx+0x10738]        ; 时间戳
0x632DB6  call 0xB75DA0                ; 取时间
0x632DCA  mov eax,[0x331C0C8] / xor eax,0xD362501F
0x632DD8  call 0x7F4F10                ; ★ host 状态
0x632DE5  jmp [eax*4+0x633D10]
; --- 状态 0/3 ---
0x632DEC  mov ecx,[0x7887040]
0x632DF5  call [0xCA8168]
0x632E0A  push 0xDB45C4 "EXE_HOSTUNREACH"
0x632E11  call 0x4F82E0                ; 日志
; --- 状态 1 ---
0x632E1B  fld [0xDADA7C] / fcomp [ebp-0x50]
0x632E2B  call 0x6295A0                ; 状态 2
; --- 继续 ---
0x632E32  lea eax,[ebx+0x38528] / call 0x622E00
0x632E3D  lea ecx,[ebx+0x106F8]        ; 第二个时间戳
...
0x63307F  mov ecx,[ebx+0x3A0D8] / lea eax,[ebx+0x3A0D4]   ; 容器 1
0x6330C7  lea eax,[ebx+0x3A098]                            ; 容器 2
0x633181  lea eax,[ebx+0x3A098]
0x6331BD  mov edi,[ebx+0x3A118]                            ; 容器 3
0x63346E  call 0x634340                                    ; ★ 房间状态广播
```

---

## §2 ★★★★★ 全部 43 个 `dwRoomMessage*` vtable + 序列化函数

| vtable | 类名 | slot[0] |
|---|---|---|
| `0xDC74F8` | dwRoomMessageManifold | `0x625520` |
| `0xDC7504` | dwRoomMessageText | `0x625970` |
| `0xDC7510` | dwRoomSpyMessageText | `0x625B30` |
| **`0xDC751C`** | **dwRoomMessageStartGame** | **`0x625BE0`** |
| `0xDC7528` | dwRoomMessageStartGameFailed | `0x628320` |
| `0xDC7534` | dwRoomMessageMemberInfoEXT | `0x625E20` |
| **`0xDC7540`** | **dwRoomMessageMemberInfoAdd** | **`0x6260A0`** |
| `0xDC754C` | dwRoomMessageMemberDetails | `0x6261C0` |
| `0xDC7558` | dwRoomMessageMemberDetailsQuery | `0x628320` |
| `0xDC7564` | dwRoomMessageMemberDetailsNoUpdated | `0x626650` |
| `0xDC7570` | dwRoomMessageCard | `0x626680` |
| `0xDC757C` | dwRoomMessageScore | `0x626810` |
| **`0xDC7588`** | **dwRoomMessageJoinMemberInfos** | **`0x626960`** |
| `0xDC7594` | dwRoomMessageJoin | `0x626A80` |
| `0xDC75A0` | dwRoomMessageJoinRequest | `0x6270D0` |
| `0xDC75AC` | dwRoomMessageMyPartyInvitation | `0x627430` |
| `0xDC75B8` | dwRoomMessagMyPartyInvitationRejected | `0x6276A0` |
| `0xDC75C4` | dwRoomMessageSyncPartyPendingToNewMember | `0x627800` |
| `0xDC75D0` | dwRoomMessageJoinWithMe | `0x627D30` |
| `0xDC75DC` | dwRoomMessageJoinWithParty | `0x627BB0` |
| `0xDC75E8` | dwRoomMessageLeaveWithMe | `0x626650` |
| `0xDC75F4` | dwRoomMessageLeave | `0x627D30` |
| `0xDC7600` | dwRoomMessageRequestMemberList | `0x626650` |
| `0xDC760C` | dwRoomMessageMemberList | `0x627D80` |
| `0xDC7618` | dwRoomMessageRoomInfo | `0x627EA0` |
| **`0xDC7624`** | **dwRoomMessageReady** | **`0x6287D0`** |
| `0xDC7630` | dwRoomMessageStartCountingDown | `0x628320` |
| `0xDC763C` | dwRoomMessageP2PInfo | `0x627FC0` |
| `0xDC7648` | dwRoomMessageChangeTeam | `0x6281D0` |
| **`0xDC7654`** | **dwRoomMessageChangeTeamRequest** | **`0x628320`** |
| `0xDC7660` | dwRoomMessageSetPilot | `0x628370` |
| `0xDC766C` | dwRoomMessageVote | `0x628320` |
| `0xDC7678` | dwRoomMessagePlaylistWeights | `0x628430` |
| **`0xDC7684`** | **dwRoomMessageRoomStateUpdated** | **`0x6285B0`** |
| `0xDC7690` | dwRoomMessageClanNameChange | `0x6286C0` |
| `0xDC769C` | dwRoomMessagePlayerPrimaryWeaponCountChange | `0x6287D0` |
| `0xDC76A8` | dwRoomMessageInRoomStateChange | `0x6287D0` |
| `0xDC76B4` | dwRoomMessageDMZLeagueTicketStateChange | `0x6287D0` |
| `0xDC76C0` | dwRoomMessageAvatarInfo | `0x628840` |
| `0xDC76CC` | dwRoomMessageUpdateDlcLevel | `0x628FD0` |

★ **共用序列化器**：
- `0x628320`（`c3+8+c21+32`）：**5 个类**（StartGameFailed / MemberDetailsQuery / StartCountingDown / ChangeTeamRequest / Vote）
- `0x6287D0`（`c3+8+c1+1`）：**4 个类**（Ready / PlayerPrimaryWeaponCountChange / InRoomStateChange / DMZLeagueTicketStateChange）
- `0x626650`：RequestMemberList / MemberDetailsNoUpdated / LeaveWithMe
- `0x627D30`：JoinWithMe / Leave

★★ **更正 138 卷**：138 说「ChangeTeam/Vote/ChangeTeamRequest → `0x628320`」，
实际是 **5 个类共用**，且 `dwRoomMessageChangeTeam`（`0xDC7648`）用的是 `0x6281D0`（**不同**）。

---

## §3 `0x634340` 发出的消息（修订）

| 真发点 | vtable | 类 | 序列化 |
|---|---|---|---|
| `0x63453C` | `0xDC7588` | **dwRoomMessageJoinMemberInfos** | `0x626960` |
| `0x634626` | `0xDC751C` | **dwRoomMessageStartGame** | `0x625BE0` |
| `0x634677` | `0xDC7540` | **dwRoomMessageMemberInfoAdd** | `0x6260A0` |
| （构造）| `0xDC7684` | dwRoomMessageRoomStateUpdated | `0x6285B0` |
| （构造）| `0xDC74F8` | dwRoomMessageManifold | `0x625520` |

---

## §4 ★★★★★ vtable 反查：每类恰有「发送侧 + 接收侧」两处构造点

**方法**：从每个类的 vtable 反查全镜像所有 `mov dword [reg], <vtable>` 引用点。

| 类 | vtable | 构造点 |
|---|---|---|
| **dwRoomMessageReady** | `0xDC7624` | `0x6301B8`（**发送侧**，AS_SetReadyState）<br>`0x635A27`（**接收侧**，紧跟 `0x635A32 call 0x629090` = Ready 反序列化器）|
| **dwRoomMessageChangeTeamRequest** | `0xDC7654` | `0x630788`（发送侧，AS_ChangeTeam）<br>`0x636618`（接收侧）|
| dwRoomMessageRoomStateUpdated | `0xDC7684` | `0x631A02` / `0x6345C4` / `0x636843`（3 处）|
| dwRoomMessageStartGame | `0xDC751C` | `0x62FB3E` / `0x6327ED` / `0x63460C` / `0x634B09`（4 处）|
| dwRoomMessageMemberInfoAdd | `0xDC7540` | `0x634641` / `0x6356EC`（2 处）|

**⇒ Ready 与 ChangeTeamRequest 各只有两处构造点，没有隐藏的第三处。**

★ 接收侧的构造点紧跟对应类的反序列化器（如 `0x635A32 call 0x629090`），
说明**接收侧"构造对象 + 解析 + 应用本地状态"是一套对称设计**。

★★ **结合 §3 与 149 卷的排除：Ready / ChangeTeamRequest 的发送链在静态上止于
`0x62C5A0` 入队 `+0x3A098`，而该容器的遍历只做清理。**

---

## §5 诚实边界

1. **「房间动作（Ready/ChangeTeamRequest）入网」的路径仍未找到**。
   本卷确认了：① 两个消息类都存在且都有序列化函数；② 它们被 `AS_*` 构造；
   ③ 构造后调 `0x62C5A0` 入队 `dwRoomImp+0x3A098`；
   ④ 帧更新遍历该容器，但只做"摘链+释放+count--"。
2. **`0x6330xx` 的完整分支未逐条读**（`0x632E80`..`0x633010` 之间还有内容）。
3. **`0x7F4F10` 的 `vt[0x24]` 是哪个对象的虚函数未定**。
4. **`[0x331C0C8] ^ 0xD362501F` 指向的对象身份未定**（只知道它有 `+0x28`、`+0x140`、`+0x144`、`+0x148`）。
5. **dump 时未进房间**，无法验证容器在房间内的实际内容。

---

## §5 工具

| 工具 | 用途 |
|---|---|
| `tools/s150a_bounds.py` | 函数入口/边界定位 |
| `tools/s150b_vtrtti.py` | vtable → RTTI 反查 |
| `tools/s150c_sweep.py` / `s150d_fine.py` | `0xDC74xx..0xDC77xx` vtable 全扫 |
| `tools/s150e_ctors.py` | **vtable → 全部构造点反查** |

## §7 方法论

1. ★★★★★ **`vtable[-1]` → COL → `+12` → type_info → `+8`** 是 MSVC RTTI 的固定链，
   用它能把**整个类的 vtable 表**一次导出。
2. ★★★★★ **从 vtable 反查构造点**，是判断"某类由谁创建"的最快路径 ——
   比读函数体更可能命中（本卷即由此确认 Ready 只有 2 个构造点）。
3. ★★★★ **共用序列化函数是正常现象**：形态相同的类会复用同一个写法。
   **不能假定"一个 type 一个序列化器"**（138 卷在此处出了一处错）。
4. ★★★ **帧更新函数是"每帧都会跑"的地方**，容器遍历/状态机/广播都在这里。
5. ★★★ **`vtable[-1]` 校验（必须是 .rdata 内的 COL）能过滤掉绝大多数假 vtable**。
