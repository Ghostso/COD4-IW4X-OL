# 122 · `6/14` 子命令词表收口 + `mmstart` 全键值域（含 `2654`=客户端标识）

> 项目：使命召唤OL 大厅（build 1649370 / 3.19）
> 前卷：`108`（实测 mmbook/mmstart/mmban）、`118`（数字 dvar）、`msg/06_14_matchmaking命令.md`
> 本卷：把 `6/14` 的**全部子命令**枚举清（只有 3 个），并把 **mmstart 的每一个键及其值域**摊开；同时**修正 118 卷的一处推断**
> 证据：`mm614_commands.txt`、`mm614_decode.txt`

---

## §0 结论

| 项 | 结论 |
|---|---|
| `6/14` blob 内层子命令 | **恰好 3 个**：`mmbook`(127) / `mmstart`(64) / `mmban`(44)，无其他 |
| `mmbook` 格式 | `mmbook <796> <base64 8B id> <0>` |
| `mmbook` 的 id 两种值 | `0x0100000000000000`(×107) / `0x8877665544332211`(×20，魔数 C) |
| `mmban` 格式 | `mmban\0\0\0`（空） |
| `mmstart` 键数 | **15 个键**（含命令 `sv_resetServer`），本卷全部列出值域 |
| ★ **新发现 `2654`** | 值 = **`M7-E8S6Client`**（客户端会话标识串），×31 |
| ★ **修正 118** | `g_difficulty` 是 **mmstart 里独立出现的键**（×41，值 0/1），**不是 2486 的"邻居"**——2486 是另一个独立数字 dvar |

---

## §1 `6/14` 子命令词表：只有 3 个

`mm614_commands.txt`——对全部 `6/14` blob 内层（剥 `u32` 长度头）取首个 ASCII 词：

```
mmbook   x127
mmstart  x64
mmban    x44
```

★★ **只有三个子命令，没有第四个。** 这坐实 `108` 卷的实测（127/64/44），并排除了"还有没发现的 6/14 命令"这个黑箱。

---

## §2 `mmbook`：`mmbook <playlistVersion> <base64 8B id> <0>`

`mm614_decode.txt`：

```
x107  'mmbook 796 AQAAAAAAAAA= 0'   → b64 解 = 0x0100000000000000 (8B)   ver=796 flag=0
x20   'mmbook 796 iHdmVUQzIhE= 0'   → b64 解 = 0x8877665544332211 (8B)   ver=796 flag=0
```

- **`796`** = playlist 版本（`PLAYLIST_VERSION`，与 `codol_crypto.py` 常量一致）。
- **第三个字段 = base64 编码的 8 字节 id**，两种取值：
  - `0x0100000000000000`（×107）——**默认/初始 id**（`01` + 7 个 0）
  - `0x8877665544332211`（×20）——**魔数 C 的字节反序**！`0x1122334455667788` 的小端存储 = `88 77 66 55 44 33 22 11`。
    ★ 与 `107` 卷「`iHdmVUQzIhE=` = 魔数 C 的第三条编码路径」完全一致。
- **末字段 `0`** = 标志（全 0）。

★★ **`mmbook` 是"预约/登记房间"命令**：告诉服务端"用 playlist 版本 796，登记这个 8 字节会话 id"。id = `01…` 是新建，id = `0x8877…` 是复用魔数 C 会话。

★ **注意 base64 的方向**：报文里是 base64 文本，解出 8 字节；`0x8877665544332211` 是**字节串原样**（`88 77 66 …`），而数值 `0x1122334455667788` 是它的**大端读法**。这两个数是同一个东西的两种表达——这正是 `118` 卷教训"用字节串而非数值对账"的又一例。

---

## §3 `mmban`：空

```
mmban\0\0\0    ×44
```

**空黑名单**（无被禁玩家）。结构 = `mmban` + 3 个 0（对齐/占位）。

---

## §4 `mmstart` 全键值域（15 键）

`mm614_decode.txt`：

| 键 | 次数 | 值域 | 语义（本卷/前卷） |
|---|---|---|---|
| `mmstart` | 64 | `sv_resetServer` | **命令头**（先重置服务器） |
| `2486` | 64 | `{1:51, 0:13}` | 数字 dvar（118：难度相关 bool） |
| `3265` | 64 | `{1:31, 6:20, 18:13}` | 数字 dvar（118：局结束/回合，playlist 双来源） |
| `2489` | 64 | `{0:44, 1:20}` | 数字 dvar（118） |
| `2574` | 64 | `{0:44, 2:20}` | 数字 dvar（118） |
| `roomChatChannelID` | 64 | `{0x1122334455667788:47, 0:13, 1800154382:4}` | **频道 ID**（107 卷） |
| `2500` | 44 | `{0}` | 数字 dvar（118：恒 0） |
| `g_gametype` | 44 | `{coop:41, train:3}` | 游戏类型 |
| `map` | 44 | `{coop_training_mp_cargoship:26, coop_train_mp_firingrange:10, mp_nuked:3, coop_chopper_mp_suburbs:2, coop_take_mp_fav_tropical:2, coop_escape_mp_storm_spring:1}` | **地图名**（明文可读，108 卷） |
| **`g_difficulty`** | 41 | `{0:31, 1:10}` | **难度**（独立键！见 §5） |
| ★ **`2654`** | 31 | **`M7-E8S6Client`** | **客户端会话标识串**（本卷新发现） |
| `playlist` | 20 | `{37}` | playlist 编号 |
| `start_map_rotate_once` | 20 | `{1..7}` | 地图轮换起始 |
| `2810` | 3 | `{0}` | 数字 dvar |
| `sv_post_options` | 3 | （base64 长串） | 服务器后置选项 |

★★ **15 个键，值域全部列出。** 这是 `6/14 mmstart` 的**完整键表**——改开局时按这张表逐键填即可。

---

## §5 `2654` 的真相 + 修正 118 卷

### 5.1 `2654` = 客户端会话标识 `M7-E8S6Client`

`2654` ×31，**值恒为 `M7-E8S6Client`**（字符串）。

★★ 这说明 **`2654` 不是"数字命名的 dvar"**（不像 2486/2489/2574/2500），而是 **dvar 名为 `2654`、值为客户端会话标识串** 的字段。

- `10/21` 里 `M7-E8S6Client` 出现 ×211（`111` 卷：会话客户端标识）。
- 这里 `2654 M7-E8S6Client;` ⇒ **mmstart 把会话客户端标识当 dvar 值下发**。
- ★ **`M7-E8S6Client` 是 9 字符的固定串**（可能是机器/会话类型标识），与账号 ID（`0xE7C8A98A6B4C2D0E`）不同。

### 5.2 修正 118 卷：`g_difficulty` 是独立键

`118` 卷从"同池邻居"推断 `2486` 是"难度相关 bool（紧邻 `g_difficulty`）"。本卷发现：**`g_difficulty` 自己在 mmstart 里就是一个独立的键**（×41，值 0/1）。

**⇒ 修正**：`2486` 和 `g_difficulty` 是 **mmstart 里并列的两个不同键**——`2486` 不"紧邻" `g_difficulty` 是因为它们在**同一字符串池**，而是在**同一命令串**里各自赋值。`2486` 的语义**仍未知**（不能因为 `g_difficulty` 就在旁边就断言 2486=难度），但**至少确认 2486 ≠ g_difficulty**。

★ 这正是 `118` 卷"邻居不是绑定"提醒的自我兑现：`118` 自己标了"中"可信度，本卷把这条"中"进一步降为"2486 独立、不等于 g_difficulty"。

---

## §6 `mmstart` 的完整语义骨架（可落地）

一条 mmstart 命令的完整骨架（按实测键序列）：

```
mmstart sv_resetServer;
  <2486 dvar>; <3265 dvar>; <2489 dvar>; <2574 dvar>; <2500 dvar>;
  roomChatChannelID <频道id>;
  g_gametype <coop|train>;
  map <地图名>;
  g_difficulty <0|1>;
  2654 <客户端标识 M7-E8S6Client>;
  playlist <37>;
  start_map_rotate_once <1..7>;
  2810 <0>;
  sv_post_options <b64>;
```

★★ **这是"客户端告诉服务端我要开什么局"的完整清单。** 服务端解析 mmstart 时按这张表读，`battle_server` 桥接时也用这张表。

---

## §7 状态表

| 项 | 状态 | 证据 |
|---|---|---|
| 6/14 子命令 = 3 个 | ✅ 枚举闭合 | `mm614_commands.txt` |
| mmbook = `<796> <b64 8B id> <0>` | ✅ 两形态解出 | `mm614_decode.txt` |
| mmbook id `iHdmVUQzIhE=` = 魔数 C | ✅ `0x8877665544332211` | 同上（第三路径） |
| mmban 空 | ✅ | 同上 |
| mmstart 全 15 键值域 | ✅ | 同上 |
| `2654` = `M7-E8S6Client` | ✅ ×31 恒定 | 同上 |
| `g_difficulty` 独立键 | ✅ ×41（修正 118） | 同上 |
| `2486` 精确语义 | ⚠️ 仍未知（≠g_difficulty） | —— |

---

## §8 复现命令

```powershell
python -I tools/mm614_commands.py   # 6/14 子命令词表 + mmstart 键全集
python -I tools/mm614_decode.py     # mmbook b64 解码 + mmstart 全键值域
```
