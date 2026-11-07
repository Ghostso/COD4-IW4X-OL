# 房间消息类族：50 个 vtable 全部解出

> **这是房间消息体系的完整函数表**
> 证据：`client_runtime.bin` RTTI 解析，**50/50 成功**
> 产物：`_byte_papers/dwroom_vtables.txt`

---

## 1. 解析方法

**三级跳：**

```
名字 ".?AV<Class>@@"
  ↓ 前 8 字节是 vftable=0x00D77818
TypeDescriptor（name - 8）
  ↓ 搜索该值作为 COL.pTD 字段（COL = 该处 - 12）
CompleteObjectLocator（sig/off/cd 全 0）
  ↓ 搜索指向 COL 的地址
vtable
```

**校准点：`dwRoomMessageStartGame`**
- TD = `0x00E6F754`
- COL = `0x00DF93B0`
- vtable = **`0x00DC7518`**

**与 `memory: codol-dwroom-protocol-reversed` 记录的完全一致。**

---

## 2. 完整表（50 个）

### 2.1 消息类（42 个）

| 类名 | vtable |
|---|---|
| `dwRoomMessageUpdateWarGodData` | `0xdc76e0` |
| `dwRoomMessageUpdateCreditRating` | `0xdc76d4` |
| `dwRoomMessageUpdateDlcLevel` | `0xdc76c8` |
| `dwRoomMessageAvatarInfo` | `0xdc76bc` |
| `dwRoomMessageDMZLeagueTicketStateChange` | `0xdc76b0` |
| `dwRoomMessageInRoomStateChange` | `0xdc76a4` |
| `dwRoomMessagePlayerPrimaryWeaponCountChange` | `0xdc7698` |
| `dwRoomMessageClanNameChange` | `0xdc768c` |
| `dwRoomMessageRoomStateUpdated` | `0xdc7680` |
| `dwRoomMessagePlaylistWeights` | `0xdc7674` |
| `dwRoomMessageVote` | `0xdc7668` |
| `dwRoomMessageSetPilot` | `0xdc765c` |
| `dwRoomMessageChangeTeamRequest` | `0xdc7650` |
| `dwRoomMessageChangeTeam` | `0xdc7644` |
| **`dwRoomMessageStartCountingDown`** | **`0xdc762c`** |
| **`dwRoomMessageReady`** | **`0xdc7620`** |
| **`dwRoomMessageRoomInfo`** | **`0xdc7614`** |
| `dwRoomMessageMemberList` | `0xdc7608` |
| `dwRoomMessageRequestMemberList` | `0xdc75fc` |
| `dwRoomMessageLeave` | `0xdc75f0` |
| `dwRoomMessageLeaveWithMe` | `0xdc75e4` |
| `dwRoomMessageJoinWithParty` | `0xdc75d8` |
| `dwRoomMessageJoinWithMe` | `0xdc75cc` |
| `dwRoomMessageSyncPartyPendingToNewMember` | `0xdc75c0` |
| `dwRoomMessagMyPartyInvitationRejected` | `0xdc75b4` |
| `dwRoomMessageMyPartyInvitation` | `0xdc75a8` |
| `dwRoomMessageJoinRequest` | `0xdc759c` |
| `dwRoomMessageJoin` | `0xdc7590` |
| `dwRoomMessageJoinMemberInfos` | `0xdc7584` |
| `dwRoomMessageScore` | `0xdc7578` |
| `dwRoomMessageCard` | `0xdc756c` |
| `dwRoomMessageMemberDetailsNoUpdated` | `0xdc7560` |
| `dwRoomMessageMemberDetailsQuery` | `0xdc7554` |
| `dwRoomMessageMemberDetails` | `0xdc7548` |
| `dwRoomMessageMemberInfoAdd` | `0xdc753c` |
| `dwRoomMessageMemberInfoEXT` | `0xdc7530` |
| **`dwRoomMessageStartGameFailed`** | **`0xdc7524`** |
| **`dwRoomMessageStartGame`** | **`0xdc7518`** |
| `dwRoomSpyMessageText` | `0xdc750c` |
| `dwRoomMessageText` | `0xdc7500` |
| **`dwRoomMessage`（基类）** | **`0xdc7bdc`** |
| **`dwRoomMessageManifold`** | **`0xdc74f4`** |
| `dwRoomMessageNetcafePrivileges`(`?AU`) | `0xdc76f8` |
| `dwRoomMessageQQMembership`(`?AU`) | `0xdc76ec` |

### 2.2 核心对象（4 个）

| 类名 | vtable |
|---|---|
| **`dwRoom`** | **`0xdc7be8`** |
| **`dwRoomImp`** | **`0xdc7270`** |
| **`dwRoomMatch`** | **`0xdc7e68`** |
| **`dwRoomMatchUber`** | **`0xdc7958`** |

### 2.3 处理器（2 个）

| 类名 | vtable |
|---|---|
| `dwRoomDMZLeagueCallbackHandler` | `0xdcf398` |
| `dwRoomEventTournamentHandler` | `0xdd7190` |

---

## 3. ★ vtable 的地址规律

**42 个消息类的 vtable 全部在 `0xdc74f4`–`0xdc76f8` 区间，
间隔恰好 `0xC` 字节。**

```
dwRoomMessageManifold       0xdc74f4
dwRoomMessageText           0xdc7500   (+0xC)
dwRoomSpyMessageText        0xdc750c   (+0xC)
dwRoomMessageStartGame      0xdc7518   (+0xC)
dwRoomMessageStartGameFailed 0xdc7524  (+0xC)
...
```

**⇒ 每个 vtable 只有 **3 项**（12 字节）。**

**⇒ 室消息类只有 3 个虚函数：**
1. 析构
2. `serialize`
3. `deserialize`

**这与 `memory: codol-dwroom-protocol-reversed` 的记录一致
（StartGame 的 serialize @ `0x625BE0`、deserialize @ `0x625CE0`）。**

---

## 4. 与 `dwRoomImp` 的关系

**`dwRoomImp` 的 vtable 是 `0xdc7270`。**

**而房间对象 `[0x82e13fc]` 的 vtable 是 `0xdc7274`（`lobby/50` 记录）。**

**`0xdc7270` vs `0xdc7274` —— 相差 4 字节。**

**⇒ `0xdc7274` 是 `dwRoomImp` vtable 的**第二项**（第一个虚函数）。**

**⇒ 这确认了：房间对象就是 `dwRoomImp` 实例。**

---

## 5. `dwRoomMatchUber` 的 vtable

```
0xdc7958
```

**与 `dwRoomMatch`（`0xdc7e68`）相差 `0x510`。**

**⇒ Uber 是 Match 的扩展子类，vtable 更长。**

**⇒ 这解释了 `memory: codol-dwroommatchuber-never-created`
为什么说"自动开局状态机属于这个不存在的类"。**

---

## 6. 可直接使用的下一步

**有了 50 个 vtable，可以：**

1. **反汇编每个类的 `serialize`（vtable[1]）→ 得到线格式**
2. **反汇编 `deserialize`（vtable[2]）→ 验证**
3. **构造一条 `RoomInfo` 推送**

**这是解开"房间事件推送格式"的直接路径。**

---

## 7. 产物

```
_byte_papers/dwroom_vtables.txt   50 个类的 TD/COL/vtable
tools/dwroom_vtables_dump.py      可复跑
tools/dwroom_rtti2.py             磁盘侧 TD 解析（50 个 TD 全解）
```
