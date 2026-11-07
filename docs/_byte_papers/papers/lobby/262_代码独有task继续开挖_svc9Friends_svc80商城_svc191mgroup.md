# 262 · 63 个"代码独有" task 继续开挖：svc 9=Friends、svc 80=商城、svc 191=mgroup

> 卷次：262（第九轮·大厅黑箱扫荡）
> 承接：`233`（63 个代码独有 task）/`260`（svc 3 全量）
> 方法：`0xBA72C0` 全库引用 + 寄存器追踪还原 + 宿主/宿主调用者字符串逐层外溯

---

## §0 结论

**233 的 63 个"代码有语料无"task，本卷接着 260（svc 3 = 24 个）往下挖，
把 `0xBA72C0` 覆盖的其余大族挖到语义级：svc 9 = Friends、svc 80 = 商城、svc 191 = mgroup。**

1. **★★★★★ svc 9 = Friends（好友服务）**：宿主字符串铁证
   `CREATE REMOTE TASK FAILED:"bdFriends::proposeFriendship"`（9/1）、
   `"bdFriends::withdrawProposal"`（9/6）、`"bdFriends::getOutgoingProposals"`；
   9/27 = `chat.friend`。指令名 `bdFriends::*` 直接给出协议命令名。
2. **★★★★ svc 80 = 商城（marketplace）**：其 7 个代码独有 task
   （`1,110,140,142,150,151,155`）的宿主全落在 **`0x4A79xx..0x4A95xx`**（= 231 卷的商城区）；
   `80/110` 宿主调用者含 **`cppRequestUpdateMarketInventory`**。
3. **★★★★ svc 191 = mgroup（社交群组）**：`191/6` 宿主调用者含
   `mgroup.post / mgroup.list / mgroup.query / mgroup.subscript / mgroup.unsubscript / mgroup.bigSpeaker`；
   `191/2` 宿主调用者含 `type / isNewSearch / keyword / offset / count`（= 搜索）；
   `191/4` 建造器含 `profileCollisionField`。
4. **★★★ svc 139 仍是盲区**：`139/4` 建造器 `0xB90970` **无任何直接调用者** ⇒ 经 vtable/间接调用。

| # | 证据 | 强度 |
|---|---|---|
| ① | `bdFriends::proposeFriendship` / `withdrawProposal` / `getOutgoingProposals` 三串 | ★★★★★ |
| ② | svc 9 七 task 的建造器/宿主坐标全表 | ★★★★★ |
| ③ | `mgroup.*` 6 个命令名 | ★★★★★ |
| ④ | `cppRequestUpdateMarketInventory` + 宿主落在 0x4A7xxx | ★★★★ |

---

## §1 方法：一条与 260 相同的恢复链

```powershell
python -I _rev_analysis/_p259/a40_codemap.py   # 全 code (svc,task) 地图
python -I _rev_analysis/_p259/a41_svc80.py     # svc80/9/139/191 坐标
python -I _rev_analysis/_p259/a42_svc9.py      # svc9 锚点（bdFriends）
python -I _rev_analysis/_p259/a43_svc139.py    # 139/191 尾项
```
用 260 的 `int(op,0)` + 函数起点修复后，`0xBA72C0` 侧得到 **13 个 svc / 90 个 (svc,task)**。

★ **`0xB78C10` 侧不适用本恢复法** —— 它的调用约定不同（232：`push task; lea buf; push svc; push buf`），
本脚本把它误归成 `svc 0`（= 假桶）。**这是本卷的方法边界，不是数据。**
（`svc 6/8/11/12/29/58/102` 仍以 232 的表为准。）

---

## §2 ★★★★★ svc 9 = Friends

（`a41_svc80.py` + `a42_svc9.py`）

| task | 建造器 | 宿主 | 宿主调用者字符串（铁证） |
|---|---|---|---|
| **1** | `0xB84600` | `0x4A0FA0` | `bdFriends::proposeFriendship` + `bdFriends::getOutgoingProposals` + `@UI_SOCIAL_FRIEND_PROPOSAL_ERROR_UNKNOWN` + `FRIEND SERVICE UNAVAILABLE` |
| **2** | `0xB84AE0` | `0x7EFF90` | 调用者 `0x726750` 含 `codo.objects.UserObj` |
| **3** | `0xB84AE0` | `0x7EFF90` | （与 2/4 共用建造器+宿主） |
| **4** | `0xB84AE0` | `0x7EFF90` | 同上 |
| **6** | `0xB846F0` | `0x4A1240` | `bdFriends::withdrawProposal` |
| **27** | `0xB85040` | `0x818A60` | **`chat.friend`** |
| **29** | `0xB84EE0` | `0x7F0710` | 调用者 `0x4E6800` |

**⇒ svc 9 = Friends（好友/社交）**：加好友提案、撤回提案、拉取待处理提案、好友聊天。
★ **`bdFriends::` 是 Demonware/Friends 的命令命名空间前缀** —— 这是 260 里"语义锚点在最外层调用者"
那条方法论的**又一次命中**（建造器无字符串，宿主调用者里全是命令名）。

★ **2/3/4 共用建造器 `0xB84AE0`** —— 与 260 的 57/63、46/47 同型：**task 号是 `push` 参数**。

---

## §3 ★★★★ svc 80 代码独有 task = 商城操作

| task | 建造器 | 宿主 | 备注 |
|---|---|---|---|
| 1 | `0xB86870` | `0x4A7930` | 调用者含密钥类十六进制常量 `683A84DE...` |
| 110 | `0xB86F80` | `0x4A8680` | 调用者含 **`cppRequestUpdateMarketInventory`** / `uiNotificationFlags` |
| 140 | `0xB872F0` | `0x4A9530` | 无直接调用者（间接） |
| 142 | `0xB87460` | `0x4A9480` | |
| 150 | `0xB87610` | `0x4A2BE0` | 调用者 `0x4A2CDB`/`0x4A2D9D` |
| 151 | `0xB87770` | `0x4A2EB0` | 调用者含 `0x5EA6A3` |
| 155 | `0xB87AC0` | `0x4A30A0` | 调用者含 `0x697C00` |

**⇒ svc 80 的这 7 个 task 全是商城子系统操作**（宿主全部落在 `0x4A7xxx..0x4A95xx`，
与 231 卷「`0x4A9A60..0x4A9E5C` = marketplace 控制台命令表」同一代码区）。
`80/110` 明确 = "请求刷新商城库存"。

★ **这些 task 客户端代码有、语料 0 条** —— 即**客户端能发但当前链路没人触发**。
**它们不是"服务端该实现"的，而是"客户端某入口没走到"**（与 261 的"是否需数据"是正交问题）。

---

## §4 ★★★★★ svc 191 = mgroup（社交群组）

| task | 建造器 | 宿主 | 锚点 |
|---|---|---|---|
| 2 | `0xB8E200` | `0x7FEB30` | 调用者 `0x691E00`：`type / isNewSearch / keyword / offset / count` = **搜索** |
| 4 | `0xB8E410` | `0x7FF890`（无直接调用者） | 建造器含 **`profileCollisionField`** |
| 6 | `0xB8E300` | `0x4AB2C0` | 调用者 `0x4AB800`：**`mgroup.post / list / query / subscript / unsubscript / bigSpeaker`**；调用者 `0x727340` 含 `@SF_UI_NOT_JOIN_GLOBAL_CHAT` |

**⇒ svc 191 = mgroup（群组/社区）服务**：发帖、列表、查询、订阅/退订、"大喇叭"。
★ **`mgroup.bigSpeaker`（大喇叭）** 是非常具体的功能名 ——
这类"业务动作名"只能从**调用者的字符串**里拿到，是命名协议命令的正确层级。

---

## §5 svc 139 仍是盲区

`139/4` 建造器 `0xB90970`、宿主 `0x7FF890` 均**无直接 `call` 调用者**
⇒ 经 **vtable 槽 / 函数指针表**调用。**"静态不可达 ≠ 没有调用者"**（176 卷方法论）——
需要扫 vtable 指针表才能继续，本卷未做。

---

## §6 边界总账

| # | 项 | 状态 |
|---|---|---|
| 1 | svc 9 = Friends | ✅ **闭合**（`bdFriends::*` 命令名铁证） |
| 2 | svc 80 代码独有 7 task = 商城操作 | ✅ 坐标 + 区域锁定 |
| 3 | svc 191 = mgroup | ✅ **闭合**（`mgroup.*` 命令名） |
| 4 | svc 139 = ? | ❌ 盲区（vtable 间接） |
| 5 | `0xB78C10` 侧 svc（6/8/11/12/29/58/102）坐标 | ⚠ 本卷恢复法不适用（约定不同），仍以 232 表为准 |
| 6 | svc 3 = Team 还是 svc 58 = Clan（260 遗留） | ❌ **未定**（本卷又发现 svc9=Friends 也带社交面；三者的区分需独立判据） |
| 7 | 未实机 | 需授权 |

---

## §7 复现命令

```powershell
python -I _rev_analysis/_p259/a40_codemap.py
python -I _rev_analysis/_p259/a41_svc80.py
python -I _rev_analysis/_p259/a42_svc9.py
python -I _rev_analysis/_p259/a43_svc139.py
```

---

## §8 方法论

1. **★★★★★ 协议命令名在"最外层调用者"的字符串里，不在建造器。**
   建造器全是类型化写入（260 已证零字符串）；宿主是薄壳；**业务名字挂在
   "触发动作"的那层**（`bdFriends::*`、`mgroup.*`、`cppRequestUpdateMarketInventory`）。
   这是**逐层外溯**（task→建造器→宿主→宿主调用者）的正确终止条件。
2. **★★★★ 「代码有语料无」有两种，要分开。** 260 说 svc3 的 21 个是"客户端不发"；
   本卷 svc80 的 7 个也是"客户端能发但没走到"；svc9/191 的则是"**服务端/入口都没走**"。
   **"语料 0 条"只说明"这条链路本次没触发"，不说明"功能存在与否"。**
3. **★★★ 同一恢复法不是万能的。** `0xBA72C0` 与 `0xB78C10` 约定不同 ——
   **换函数必须换约定，不能把一套 push 解析套到所有建造器上**（本卷的 `svc 0` 假桶就是教训）。
4. **★★★ "静态不可达"要显式区分于"没有调用者"。** svc 139 的两个函数都无直接 `call`，
   但它们在 vtable 里可能各有一槽 —— **必须写出来**，不能当成"死代码"丢掉。
