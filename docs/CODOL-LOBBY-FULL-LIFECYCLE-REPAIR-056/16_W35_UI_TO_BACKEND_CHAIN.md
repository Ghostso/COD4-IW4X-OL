# 16 — W3.5：UI→后端链路（为什么"选剧情任务"仍建房）

> 2026-10-29。输入 = `E:\codol_re\client_image_20261027.bin`（解包镜像，VA−0x400000=偏移）。
> 工具：`TOOLS/vtable_map.py`、`TOOLS/xref_va.py`、`TOOLS/vtable_annotate.py`。
>
> ## ★★ 实机已确认（2026-10-29，用户）
> **从"训练"入口进，客户端能正常进入对局** ⇒ 本文件 §6 的推论成立：
> **大厅 → 战斗交接这一段本身是通的**，此前"从不出现在 28960"只出现在
> **房间路径 / PvE 面板（队伍玩法）** 上。
> 剩余问题（训练地图碰撞不对）属**战斗服内部**（`CODOL_SERVER_319_20261021`，
> 其碰撞表来自 `coop_train_zone.bin` 的 29 个 box，与客户端所用地图需再对齐），
> 按 056 边界（只修大厅与交接层）**不在此任务范围**，探索到此为止。

---

## 1. UI↔C++ 接口全表（字符串即接口名）

`UiCppMatchSelectView` 通过 ActionScript 名称调用 C++，全部名字在同一张字符串表里（0x00DD7000 段）：

**面板 / 列表**
```
CPP_rootModeList      CPP_pvpPanel   CPP_pvePanel    CPP_warGodPanel
CPP_battleCityPanel   CPP_roomPanel  CPP_theatrePanel
CPP_theatreList       CPP_favouriteList
CPP_pveModeList       CPP_pveMapList        CPP_pveDifficultyList
CPP_roomTypeList      CPP_roomCreateModeList CPP_roomFindModeList  CPP_roomMatchList
CPP_pvpModeList       CPP_pvpMatchList      CPP_battleCityPlayList
```
**条目字段**（每个列表项都带这些标记）
```
mapType   coopMapType   isWarGod   isRoom   isBattleCity   isTheatre
pveDifficulties   playlists   isNewUnlock   unlockItem   isComplete   lockedByDLCLevel
```
**持久化选择**（与 055 记录的 102/7 playerdata 索引 44–50 **完全对应**）
```
currentMatchSelectRootIndex   (idx 49)
currentMatchSelectPVPMode / PVPMatch / PVEMode / PVEDifficulty / PVEMap   (idx 44–48)
currentBattleCityPlaylist     currentRoomType (idx 50)
```
**事件/方法**：`CPP_InitClickEvent`、`CPP_GetSelectedIndex`、`CPP_SelectIndex`、`CPP_GetQuickMatchType`、
`CPP_ShowViewPanel`、`CPP_HideViewPanel`、`CPP_OnRootModeClick`、**`CPP_OnTraining`**、`CPP_OnBattleCityMode`

## 2. 根模式分派器：`0x0073F8C0`

```
0x0073F8C0  mov  eax, <mode>            ; 入参：模式号
            cmp  eax, 6
            ja   0x73F902
            jmp  dword ptr [eax*4 + 0x73F934]     ; ★ 7 项跳表
   case0 → ebx=[obj+0x0C]   case1 → [obj+0x10]   case2 → [obj+0x14]
   case3 → ebx=[obj+0x18]   case4 → [obj+0x1C]   case6 → [obj+0x20]
   case5 → 直接落到 0x73F902（**没有描述符**）
0x0073F902  mov [obj+0x158], eax         ; ★ 写入"当前根模式"
            call 0x50F230(0x00DD7C6C, mode+1)   ; 字符串 = "currentMatchSelectRootIndex"
            call 0x73F950(ebx)                  ; 用该模式的描述符切面板
```
`0x0073F950`：隐藏旧面板（`CPP_HideViewPanel`）→ `[this+0x24] = 描述符` → 显示新面板（`CPP_ShowViewPanel`）。

**⇒ `[obj+0x158]` = 根模式号；模式 0..6，其中 mode 5 无描述符（= 训练/靶场）。**

## 3. ★ 三个 mmstart 构造串（形态由流程决定）

客户端内存里就有三条 mmstart 模板（同一函数 0x00632070 内引用）：

| 串 VA | 模板（节选） | 对应实测形态 |
|---|---|---|
| `0x00DC6800` | `… 2489 %d; 2574 0; 2500 %d; %s; %s g_difficulty %d; %s; map %s;2654 %s; roomChatChannelID %llu;` | **10-26 成功轮的 PvE 形态**（带 map + 难度） |
| `0x00DC6888` | `… 2500 0; %s; %s 2810 %d; sv_post_options %s; map %s; roomChatChannelID %llu;` | 带 post_options 的 map 形态 |
| `0x00DC6948` | `… 2574 %d; playlist %d; %s %d; roomChatChannelID %llu;` | **房间路径 B1 形态**（playlist，无 map） |

相关：`mmbook`(0x00DC6724)、`mmbook accepted`(0x00DC69B0)、`sv_resetServer`、`roomChatChannelID`。
`0x00632070` 是"构造开局指令"的函数（读 `combat`/`cha`/`war` 变异、`mp/mutators.csv`、gametype 等）。

**⇒ 形态不是"服务端选"的，而是客户端在构造时就选定了——只要我们能让它走模板 #1，就是 10-26 那条路。**

## 4. 点击处理器链（模板化）

所有 `OnXxxClick_SF_Handler` 共用一套模板：

```
mov eax,[ebp+8] / mov eax,[eax+8]        ; Scaleform 事件对象
mov ecx,[eax+0xC] / and ecx,0x8F / cmp cl,0xA / sete dl   ; 读一个 Value 的类型标记
… call [obj->vtable+0xB4]                ; 取当前视图对象
… call [ret->vtable+8]                   ; 取子对象
call <差异化的处理函数>
```

| 处理器 | vftable | 处理函数 | 备注 |
|---|---|---|---|
| `OnRootModeClick_SF_Handler` | 0x00DD8470 | `0x0073FA00` | 比较 `[esi+0x158]`；**若点击值 == 5 → `CPP_OnTraining`**，否则 → `CPP_OnRootModeClick` |
| `OnPveModeClick_SF_Handler` | 0x00DD847C | `0x00741E20` | PvE 模式 |
| `OnPveMapClick_SF_Handler` | 0x00DD8488 | `0x00739430`(取值)+`0x00739430` | 入参 = `[obj+0x134]`（所选地图索引） |
| `OnPveDifficultyClick` | 0x00DD8494 | — | PvE 难度 |
| `OnRoomTypeClick` / `OnRoomCreateModeClick` / `OnRoomFindModeClick` / `OnRoomMatchClick` | 0x00DD84A0 / C4 / D0 / DC | — | 房间面板四项 |
| `OnPvpModeClick` / `OnPvpMatchClick` | 0x00DD84AC / B8 | — | PvP |
| `AS_CreateRoom` / `AS_IsInRoom` / `AS_GetRoomInfo` | 0x00DC8904 / 0x00DC8598 / 0x00DDD7A8 | — | UI 主动查询/动作 |

`0x00739430` 是**通用"取点击值"**（RootModeClick 传 `[esi+8]`，PveMapClick 传 `[ebx+0x134]`）。
`0x0073F510` = **"按当前选择开始匹配"**：依次读 `CPP_GetQuickMatchType`、`mapType`、`isWarGod`、
`isRoom`、`isBattleCity`、`isTheatre` … 组装成 C++ 侧描述符；
其唯一调用者是 `AS_ShowView`（0x0073E75B）——即"显示匹配界面时若有待处理请求则开打"。

## 5. ★★ 根模式 ↔ 面板映射（在 0x0073DFCA 的建立代码里读出）

`0x0073DFCA` 起依次调用 `0x745A80(<名字>)` 并把**上一次调用的返回值**存入对象字段；
配合 §2 的跳表 `[obj+0xC..0x20]`，得到完整映射：

| 根模式 | 字段 | 面板（字符串） | 含义 |
|---|---|---|---|
| 0 | `[obj+0x0C]` | `CPP_pvpPanel` | PvP |
| 1 | `[obj+0x10]` | `CPP_pvePanel` | **PvE（剧情 / 生存）** |
| 2 | `[obj+0x14]` | `CPP_battleCityPanel` | 战地 |
| 3 | `[obj+0x18]` | `CPP_warGodPanel` | 战神 |
| 4 | `[obj+0x1C]` | `CPP_roomPanel` | **房间** |
| 5 | —（跳表 case5 无描述符） | — | **训练 → `CPP_OnTraining`** |
| 6 | `[obj+0x20]` | `CPP_theatrePanel` | 剧场 |

同一段代码还建立了子列表字段（存"上一次返回值"，故错位一格读出）：
```
[obj+0x128] = CPP_favouriteList      [obj+0x12C] = CPP_theatreList
[obj+0x130] = CPP_pveModeList        [obj+0x134] = CPP_pveMapList      ★
[obj+0x138] = CPP_pveDifficultyList
```
**闭环验证**：`OnPveMapClick` 读的正是 `[obj+0x134]`（= `CPP_pveMapList`）并调 `0x739430` 取选中索引 —— 两处独立证据吻合。

## 6. ★★★ 结论：10-26 成功走的是"训练"，不是 PvE 面板

| 入口 | 根模式 | 开局模板 | 结果 |
|---|---|---|---|
| **训练**（`CPP_OnTraining`） | **5** | #1（带 `map coop_train_mp_firingrange`，`roomChatChannelID 0`） | **10-26 八轮：连上战斗服** |
| PvE 面板（`CPP_pvePanel`） | 1 | 经房间/队伍流程 | 056 各轮：`createRoom` → 房间路径 → 零连接 |
| 房间面板（`CPP_roomPanel`） | 4 | #3（`playlist N`） | 房间路径 B1 |

`coop_train_mp_firingrange` 里的 **`train`** 与 `CPP_OnTraining`、playlist 198（"Party - DWARF"，`coop_train_mp_firingrange`）
三处独立证据一致：**成功的引用是"训练"这一入口**。
而 PvE 面板下的 `playlist 10`（Survival Normal，`minparty 1 / maxparty 6`）本就是**队伍玩法**，
客户端为它建房属预期行为 —— 这就是"选剧情任务却建房"的原因。

**⇒ 要复现 10-26，必须从"训练"入口（根模式 5）进，而不是 PvE 剧情列表。**

## 7. 已验证的闭环

- `CPP_OnTraining`(0x00DD7D88) 全镜像**只有一处引用** = `0x0073FA2F`，
  正落在 `OnRootModeClick` 的 `cmp eax,5 → je/jne` 分支内（`0x0073FA19` 起）⇒
  **根模式 5 直接触发 UI 的 `CPP_OnTraining`**，无中间层。
- `0x0073F510` 采集器内还按模式算出 **quickMatchType**：
  `mode==1` → 依 flag 取 2/3/4；`mode==2` → 依 flag 取 5（`0x0073F790`–`0x0073F7CC`），
  即 PvE/战地各自还有子类型分流。

## 9. 实机验证结论（2026-10-29，用户确认）

> **"训练入口可以正常进入对局"** —— 根模式 5 的推论得到实机确认。

由此确立三条，并界定本任务边界：

| 事实 | 意义 |
|---|---|
| 训练入口能正常进对局 | **大厅→战斗交接这一段是通的**（`createRoom`/成员/事件/准备都不是必需） |
| PvE 面板建房、训练不建房 | 分叉在客户端 UI 根模式，服务端无法改变——我们只需**不去误导它** |
| 训练地图碰撞不对 | **属战斗服内部**（世界/碰撞数据），不在大厅与交接层范围 |

**本任务（大厅 + 战斗连接交接层）的结论：该层已可闭合。**
剩余问题下沉到战斗服（`CODOL_SERVER_319_20261021`）：
- 碰撞表只有一套 `mp_firingrange` 的静态盒（29 个 clip volume），`--map` 只改名字不改几何
- 训练模式客户端进的是 `coop_train_mp_firingrange`，与 `mp_firingrange` 是不同 zone

**大厅侧遗留（低优先）**：PvE 面板/房间面板的完整流程（R2–R5），只有在需要这两类玩法时才需继续。

## 10. 下一步（大厅侧，可选）

1. `createRoom`(11/13) 发送点与 `isRoom` 消费者（若要做房间玩法）
2. `CPP_rootModeList` 条目内容（哪一项对应"训练"在 UI 上的位置）
3. mmstart 模板 #1/#2/#3 的选择分支逐条标注



