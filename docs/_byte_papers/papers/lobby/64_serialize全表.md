# 房间消息的 serialize / deserialize 全表（50 类）

> **这是"房间事件推送格式"的完整入口**
> 证据：`client_runtime.bin`，从 50 个 vtable 提取 `[0]/[1]/[2]`
> 产物：`_byte_papers/dwroom_serializers.txt`

---

## 1. 表结构

每个消息类的 vtable 有 3 项：

| 槽 | 含义 |
|---|---|
| `[0]` | 析构 / RTTI 辅助 |
| **`[1]`** | **`serialize`（写）** |
| **`[2]`** | **`deserialize`（读）** |

**⇒ `[1]` 就是要找的"线格式生成函数"。**

---

## 2. ★ 关键类的 serialize 地址

| 类 | serialize | deserialize |
|---|---|---|
| **`dwRoomMessageStartGame`** | **`0x625be0`** | **`0x625ce0`** |
| `dwRoomMessageStartGameFailed` | `0x628320` | `0x625db0` |
| **`dwRoomMessageRoomInfo`** | **`0x627ea0`** | **`0x627ee0`** |
| `dwRoomMessageRoomStateUpdated` | `0x6285b0` | `0x628610` |
| **`dwRoomMessageReady`** | **`0x6287d0`** | **`0x629090`** |
| **`dwRoomMessageStartCountingDown`** | **`0x628320`** | **`0x625db0`** |
| `dwRoomMessageMemberList` | `0x627d80` | `0x627e00` |
| `dwRoomMessageJoin` | `0x626a80` | `0x626b30` |
| `dwRoomMessageLeave` | `0x627d30` | `0x627b40` |
| `dwRoomMessageMemberInfoEXT` | `0x625e20` | `0x625f50` |
| `dwRoomMessageMemberInfoAdd` | `0x6260a0` | `0x626130` |
| `dwRoomMessageManifold` | `0x625520` | `0x6256c0` |

**`StartGame` 的 `0x625be0` / `0x625ce0` 与
`memory: codol-dwroom-protocol-reversed` 记录的完全一致。**

---

## 3. ★★ 发现：大量类共用同一对函数

**统计 `[1]` 的重复：**

| serialize | 使用它的类 |
|---|---|
| `0x628320` | `Vote`、`ChangeTeamRequest`、`StartCountingDown`、`StartGameFailed`、`MemberDetailsQuery`、`NetcafePrivileges`、`QQMembership` |
| `0x6287d0` | `Ready`、`UpdateCreditRating`、`DMZLeagueTicketStateChange`、`InRoomStateChange`、`PlayerPrimaryWeaponCountChange` |
| `0x626650` | `RequestMemberList`、`LeaveWithMe`、`MemberDetailsNoUpdated`、`dwRoomMessage`(基类) |
| `0x627d30` | `Leave`、`JoinWithMe` |

**⇒ 这些类是"空消息"或"只带一个整数的消息"。**

**⇒ `0x628320` 是最简单的序列化器（7 个类共用）。**

---

## 4. 数据推论的验证

**`lobby/40` 发现 `11/4` 的模板里有多组 `02 0X 00 00`。**

**现在能对上：**

**`Manifold` 的 serialize 是 `0x625520` ——
它是"把多个消息打包"的函数。**

**如果把 `Manifold` 反汇编出来，
就能知道 `11/4` 里的分组结构
（`02 02 00 00` / `02 04 00 00` / …）是什么。**

---

## 5. 下一步的优先级

### 优先级 1：`dwRoomMessageManifold::serialize`（`0x625520`）

**它决定所有批量消息的格式。**

**而 `11/4` 的所有形态都是"分组"，很可能就是 Manifold。**

### 优先级 2：`dwRoomMessageRoomInfo::serialize`（`0x627ea0`）

**建房必需的第一条推送。**

### 优先级 3：`dwRoomMessageStartGame::serialize`（`0x625be0`）

**已知部分（memory 记录），可补全。**

---

## 6. 50 个类的完整清单（按 serialize 分组）

### `0x625520`（Manifold）

`dwRoomMessageManifold`

### `0x625970`（文本）

`dwRoomMessageText`

### `0x625b30`

`dwRoomSpyMessageText`

### `0x625be0`（StartGame）

`dwRoomMessageStartGame`

### `0x625e20`

`dwRoomMessageMemberInfoEXT`

### `0x6260a0`

`dwRoomMessageMemberInfoAdd`

### `0x6261c0`

`dwRoomMessageMemberDetails`

### `0x626650`（基类，4 个共用）

`dwRoomMessage`、`RequestMemberList`、`LeaveWithMe`、`MemberDetailsNoUpdated`

### `0x626680`

`dwRoomMessageCard`

### `0x626810`

`dwRoomMessageScore`

### `0x626960`

`dwRoomMessageJoinMemberInfos`

### `0x626a80`

`dwRoomMessageJoin`

### `0x6270d0`

`dwRoomMessageJoinRequest`

### `0x627430`

`dwRoomMessageMyPartyInvitation`

### `0x6276a0`

`dwRoomMessagMyPartyInvitationRejected`

### `0x627800`

`dwRoomMessageSyncPartyPendingToNewMember`

### `0x627bb0`

`dwRoomMessageJoinWithParty`

### `0x627d30`

`dwRoomMessageLeave`、`JoinWithMe`

### `0x627d80`

`dwRoomMessageMemberList`

### `0x627ea0`（RoomInfo）

`dwRoomMessageRoomInfo`

### `0x6281d0`

`dwRoomMessageChangeTeam`

### `0x628320`（7 个共用，最简）

`Vote`、`ChangeTeamRequest`、`StartCountingDown`、`StartGameFailed`、
`MemberDetailsQuery`、`NetcafePrivileges`、`QQMembership`

### `0x628370`

`dwRoomMessageSetPilot`

### `0x628430`

`dwRoomMessagePlaylistWeights`

### `0x6285b0`

`dwRoomMessageRoomStateUpdated`

### `0x6286c0`

`dwRoomMessageClanNameChange`

### `0x6287d0`（5 个共用）

`Ready`、`UpdateCreditRating`、`DMZLeagueTicketStateChange`、
`InRoomStateChange`、`PlayerPrimaryWeaponCountChange`

### `0x628840`

`dwRoomMessageAvatarInfo`

### `0x628fd0`

`dwRoomMessageUpdateDlcLevel`

### `0x629110`

`dwRoomMessageUpdateWarGodData`

---

## 7. 对"房间推送"的意义

**之前（`lobby/62`）：51 个类，只见过 4 个，盲区 92%。**

**现在：50 个类的 serialize 地址全部拿到。**

**⇒ 盲区从"完全不知道"变成"知道去哪读"。**

**⇒ 反汇编 `0x625520`–`0x629110` 这一小段，就能拿到全部线格式。**
