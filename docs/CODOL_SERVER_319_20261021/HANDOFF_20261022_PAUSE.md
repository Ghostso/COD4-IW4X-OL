# CODOL 3.19 C 战斗服 —— 进度存档（2026-10-22 00:22 暂停）

> 本文件只记录**本轮实际验证过的**内容；推断标注 `[推断]`，未完成标注 `[未完成]`。
> 暂停时环境：无客户端/战斗服/注入器进程残留，无 agent 子进程，UDP 28960 空闲。

---

## 0. 一句话现状

**移动/输入/开火状态机已接通；出生点已用地图自己的实体数据修正；
但"落地/穿墙"仍未解决——因为服务端还没有地图碰撞数据。小地图、角色外观、背包武器同样未完成。**

当前构建：`build\Debug\codol_battle_server.exe`
SHA-256 = `F44159EDBB38F8A76016AED0A9683F5FD88F0989D771F9B48DE92933A3DB442D`（10-22 历史值；当前构建已更新）
单体测试：**15/15 通过**（2026-10-23 当前全量回归为 19/19 通过；本文件保留 10-22 暂停时基线）

---

## 1. 本轮最大突破：CODOL 快件（.ff）完整解密

此前多次卡在"读不出地图数据"。本轮把整条链打通，**这是后面所有世界/碰撞工作的前提**。

### 1.1 容器格式（已实测）

```
IWff0100 容器
  0x000  8   "IWff0100"
  0x008  4   version = 461
  0x015  256 RSA-2048 PKCS#1 v1.5 包裹的 key_material(40B)
  0x115  ..  AES-192-CTR 数据体（按 0x2000 分块）
数据体：
  block0(0x2000):  CTR(IV = key_material[24:])  -> "IWffs100" + zone名(300) + level-1 摘要表(336 + i*32)
  之后每 section:   CTR(IV = block0[336+i*32][:16])  -> level-2 表（每 32B 是各数据块的 SHA-256）
  每个数据块(0x2000): CTR(IV = 该块 SHA-256[:16])
  拼接后 zlib.decompress -> zone
```

**关键点：不是连续 CTR 流，而是"每块用自己的 SHA-256 前 16 字节当 IV"。**
这解释了为什么按连续流解永远得不到合法 deflate。

来源：
- 格式与打包器：`_e1_regression\ol-mod-olfinal\tools\reverse\OlfinalFastfile.py`（其 `unpack_zone()` 即规范）
- 密钥：与 **IW4X `Components\Modules\FastFiles.cpp` 的 `ZoneKey`** 同源；IW4X 的
  `AuthLoadInflateDecryptBaseFunc` / `AuthLoadInflateCompare` / `InflateInitDecrypt` 就是这套逐块 CTR + inflate

### 1.2 可复现命令（已固化为工具）

```powershell
# Layer1 + Layer2 一条命令（工具已入库）
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021
python -X utf8 tools\codol_ff_unpack.py ..\_map_extract\coop_train_mp_firingrange.ff ..\_map_extract\coop_train_zone.bin --name coop_train_mp_firingrange

# 分解看：Layer1
cd D:\BaiduNetdiskDownload\使命召唤OL\_PLAINTEXT_PROJECT
# Layer1（CTR 解出 IWffs100 + zone 名）
python -X utf8 tools\codol_ff_decrypt.py ..\_map_extract\coop_train_mp_firingrange.ff --out _l1test --json
# Layer2（逐块 CTR + zlib）见本目录下的 _map_extract\coop_train_zone.bin（已解出，6,291,523 B）
```

### 1.3 本轮产出

| 产物 | 说明 |
|---|---|
| `_map_extract\coop_train_zone.bin` | **解压后的 coop_train_mp_firingrange zone（6.29 MB）** |
| `_map_extract\coop_train_entities.txt` | 从中提取的地图实体串（51,189 B / 381 个实体） |
| `_map_extract\coop_train_spawns.json` | 出生点表 |
| `CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py` | **Layer2 解包工具（新增，可复现）** |

---

## 2. 出生点：已用地图自己的实体数据修正

从解出的 zone 实体串得到的**唯一设计出生点**：

```
info_player_start_so   origin = 48 -572 -116
（worldspawn 0 0 0；其余 379 个是 script_model/script_brushmodel/script_struct/trigger_*）
```

**结论：48 / -572 / -116 本来就是对的。**

`[已修正]` 中途曾照某份 C# 配置把它改成 `-127.018`（比地图出生点**低 11 单位**）→
人物陷进地板 → 表现成"卡住 / 在房顶"。现已改回：

```c
// src/battle/battle_service.c
codol_player_init(&svc->player, 48.0f, -572.0f, -116.0f);
```

---

## 3. 本轮代码改动（CODOL_SERVER_319_20261021）

### 3.1 结构性修复：快照字段的"新值 XOR 基线"

依据 `CoD4x msg.c:1983-2216 MSG_WriteDeltaField`：
```
case -88:  MSG_WriteLong(msg, to ^ from);                       // float
case -87:  MSG_WriteAngle16(msg, to);                           // 角度不异或
default:   if (to) { bit1; write (to ^ from), abs(bits) 位 } else bit0;
```
此协议**每个字段写的是 `to ^ from`**。首帧 `deltaNum=0`（基线全零）时裸值恰等于异或值，
所以看起来"能跑"；**第二帧起客户端拿上一帧做基线，写裸值就全错**。

- 新增 `codol_snap_state_t` 帧基线；`codol_snapshot_build(..., const codol_snap_state_t *from, codol_snap_state_t *cur, ...)`
- 服务层每帧 `snap_from = snap_cur`
- 新测试 `tests/test_snapshot_delta.c`：首帧含裸值 / 同值第二帧写成 0 / 变化帧写异或值

### 3.2 快照字段

| 项 | 之前 | 现在 | 依据 |
|---|---|---|---|
| `command_time` | 写死 1000 | `processed_input_time` | 客户端 usercmd 的确认；写死会导致**指令溢出** |
| 左右武器状态 | 只写 index 17/3/44（**右/副武器**） | 另写 **62/162/107**（左/当前武器） | 3.19 字段表 `LeftWeaponState/Time/Delay` |
| index 61 | 恒 2047 | `on_ground ? 2046 : 2047` | groundEntityNum |
| index 83 | 从未写 | `0`（PM_NORMAL） | pm_type；否则客户端走 spectator/noclip |
| 快照速率 | 20 Hz | **128 Hz**（tick 也 128） | 参考实现实机采样率 |
| 武器 | 写死 1156 | 采信 `usercmd.weapon`（实测该值常为 0，**暂无实效**） | CoD4x/IW4 语义 |

### 3.3 移动模型（`src/world/player.c`）

照 `CODOL-Combat-Server-v0.1\src\Engine\GameWorld.cs:621-638`：
`dir_bias = 0 -2`、`flip_move_y = 1`、`flip_strafe_x = 1`、`WalkSpeed = 190`、`vertical_sim = 0`（不积分 Z）。

### 3.4 装备状态机（`src/battle/equipment.c`，本轮新增）

逐行移植参照的 `_Slot`/`_Equipment`：开火扣弹/射速冷却/换弹转运/空仓换弹/半自动/背包切换。
测试 `tests/test_equipment.c`。

### 3.5 其它

- `/utf-8`（MSVC 源文件编码，消除 C4819）
- `tools/ref_reader.py` + `gen_cases.py` + `cases.txt` + `test_usercmd.c`：C 解析器 vs 参照读取器**差分对账台**
  （600 用例 0 失配；真实客户端 16 条 body 字节 **16/16 一致**）
- `tools/scan_map_entities.py`：从**活客户端内存**抓地图实体串（备用路径，本轮未用上）
- `run_codol_001\runs\make_run_dir.py` + `check_protected_integrity.py`：每轮隔离目录与受保护文件哈希

---

## 4. 已验证 / 未验证（不得混淆）

### 已在真实客户端上验证
- NAT / DTLS init / 密钥交换 / stats / game state / netchan 全链路
- `[world] USERCMD` 出现，`time` 递增、`yaw/pitch` 随转头变化、`F/R` 随按键变化
- 与参照读取器在**真实字节**上 16/16 一致
- 出生点 `48,-572,-116` 与**地图实体数据**一致
- 开镜状态生效（用户实测确认）
- 快照能被客户端接受并进入对局（`RX_GAMESTATE_PROGRESS 1..6`）

### 未验证 / 未完成
- **落地 / 穿墙 / 真实 ground trace** —— 服务端**没有地图碰撞**，`vertical_sim=0` 时不动 Z
- **小地图** —— 本地图 zone 内无 `compass/radar/northyaw` 字符串，需从 `common_mp.ff`（77 MB，已解出）或 configstring 找
- **角色外观 / 背包武器** —— 仍写死；`usercmd.weapon` 实测为 0，此通道不存在
- 快照 index 82（radarFlags，codec -101）/ index 28（eFlags，codec -98）**编码未确定，暂不发**

---

## 5. 下一步（按优先级）

1. **从同一 zone 里定位 clipMap**（planes/nodes/leafs/brushes/leafbrushNodes）→ 移植 CoD4x
   `cm_local.h` / `cm_load_obj.cpp` / `cm_trace.c` / `cm_test.c`，给服务端加 `CM_BoxTrace` / `CM_PointContents`。
   拿到之后：水平位移用 sweep、垂直用 trace 找地面、`groundEntityNum` 用真实接触。
2. **小地图**：用同一套解密流程解 `common_mp.ff`，找 compass/radar 材质与 `northYaw` configstring，
   写进 gamestate 的 minimap configstring。
3. **武器/角色**：`usercmd.weapon` 不可用；需从角色定制/装配来源取，或改为**不下发**这些字段让客户端保留大厅状态。
4. 快照 index 28 / 82 的 codec 编码（-98 / -101）从客户端解析器轨迹
   （`CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted\reference\playerstate-*-trace.json`）
   或 CoD4x `MSG_WriteEFlags` 定下来后再发。

---

## 6. 关键路径索引

| 用途 | 路径 |
|---|---|
| C 服工程 | `CODOL_SERVER_319_20261021\` |
| 构建 | `E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe --build build --config Debug` |
| 快件解密器(Layer1) | `_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py` |
| 快件解包工具(Layer1+2) | `CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py` |
| 快件打包/解包规范 | `_e1_regression\ol-mod-olfinal\tools\reverse\OlfinalFastfile.py` |
| IW4X 引擎核心 | `IW4X\iw4x-client\src\Components\Modules\FastFiles.cpp`、`src\Game\Structs.hpp` |
| CoD4x 编码/碰撞 | `CoD4x_Server-21.2\src\msg.c`（MSG_WriteDeltaField）、`cm_local.h`、`cm_load_obj.cpp`、`cm_trace.c` |
| 3.19 字段表 | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted\reference\playerstate-fields.json` |
| 客户端解析轨迹 | 同目录 `playerstate-*-trace.json` |
| 解出的地图 zone | `_map_extract\coop_train_zone.bin` |
| 本轮运行目录 | `run_codol_001\runs\C_SERVER_FIRST2..13_20261021\`（每轮独立；`kit\` 为链副本） |

## 7. 本轮未启动客户端

用户要求“没修完就不要起”，所以**本轮没有跑任何实机测试**；出生点修正只做了离线实体数据校验与单体测试。
下一次真正要验证的就一件事：**人能否站在地面上且自由移动**。

## 8. 受保护文件状态（AGENTS.md）

`REF_LOBBY_KIT\_golden_hashes.json` 比对：唯一 FAIL 是**先于本会话**的既有漂移
`marketplace_store.py`（实际 50022 B / `E44358F0...`，manifest 期望 46226 B / `28B4A1BE...`，
修改时间 2026-10-16）。本会话**未读写** `REF_LOBBY_KIT` 与 `CODOL_VERIFIED_GOLDEN_20261019` 下任何文件。
可还原来源：`run_codol_001\runs\ONCE_20261021_14*\kit\marketplace_store.py`（46226 B，与 manifest 一致）。

---

# 2026-10-22 续接会话：clipMap 定位 + 最小碰撞层落地

## 0. 一句话

**已完成**：clipMap 关键段定位（自校验工具）、碰撞层 `codol_collision.c` 落地、移动模型改为真实重力+地面/障碍 trace；**全部 18 个单测通过**。
**未完成**：clipMap 的完整精确解析（aabbTrees/cmodels/brushes 数组边界未闭合），当前碰撞是**轴对齐近似**。

## 1. 本轮新增产物

| 文件 | 说明 |
|---|---|
| `tools\clipmap_locate.py` | **新增**。从解包 zone 定位 MapEnts/TriggerModel/TriggerHull/TriggerSlab/cplane/材质名/brushside 指针表，全部带自校验（`SELF-CHECK OK`） |
| `include\codol_collision.h` | **新增**。碰撞 API：`codol_collision_box_trace` / `codol_collision_point_solid` |
| `src\world\collision.c` | **新增**。29 个 script_brushmodel 轴对齐 clip 盒 + 地面平面 z=-116；AABB sweep（slab 法，照 CoD4x cm_tracebox 语义） |
| `include\codol_clipmap_approx.h` | 数据快照（与 collision.c 同源） |
| `tests\test_collision.c` | **新增**。5 组断言：落地、空地移动、clip 阻挡、点实体判定、盒数量 |
| `_map_extract\coop_train_collision_approx.json` | 近似碰撞数据（机器可读） |
| `_map_extract\mp_firingrange_zone.bin` | mp_firingrange 解包 zone（57.9 MB） |

## 2. 已确证的 clipMap 结构（可复算）

`coop_train_zone.bin`，全部偏移经 `tools\clipmap_locate.py` 自校验：

```
0x2327CE..0x23EFC3  entity text (51,189 B)
0x23EFC4..0x23F044  TriggerModel[16]   每项 8B {contents=0x28000001, hullCount, firstHull}
0x23F044..0x23F4C4  TriggerHull[32]    每项 32B {Bounds 24B, contents, slabCount u16, firstSlab u16}
0x23F4C4..0x23F564  TriggerSlab[8]     每项 20B {dir3 单位向量, midPoint, halfSize}
0x23F564..0x23F59C  目录 7 组 (count, cleared-ptr):
                      (27, 4, 27, 144, 30, 30, 30)
0x23F5A4..0x23F7C0  cplane_s[27]       20B/项，单位法线
0x23F7C0..0x23F7F0  ClipMaterial[4]    12B/项 {namePtr=-1, surfaceFlags, contents}
0x23F7F0..0x23F81B  材质名 "clip_player"/"clip_shot_block"/"clip_full"/"clip"
0x23F81B..0x23F8F3  cbrushside_t[27]   8B/项，plane 指针步长恰为 20B（与 plane 数一一对应）
0x23F8F3..0x23F983  brushEdges[144]
0x23F983..           cLeaf/leafbrushNode 记录流（20B stride，未闭合）
```

**自洽点**：27 planes ↔ 27 brushside 指针（步长 20）↔ 目录里的 27；4 材质 ↔ 4 材质名；144 brushEdges ↔ 目录 144。

## 3. 本轮代码改动

- `src\world\player.c`：删除 `vertical_sim=0`（不积分 Z、`on_ground=true` 写死）的旧行为，改为
  - 水平 X/Y 各自独立 sweep（避免斜向穿角）
  - `vz -= gravity*dt` 后向下 trace
  - 命中且 `normal.z > 0.5` → 钳 z、`vz=0`、`on_ground=true`
- `src\world\collision.c`：地面判定用**包含式**比较（`end_z <= ground`），修复"出生点正好在地面上→首帧穿地"的边界 bug
- `CMakeLists.txt`：`collision.c` 加入主目标、`test_player`、`test_session`

## 4. 测试结果

```
test_collision.exe   all checks passed          (落地 / 空地 / 阻挡 / 点实体 / 29 盒)
test_player.exe      ALL PASSED (0)             (出生点 -116、落地、四向移动、斜向归一、开镜)
其余 16 个 test_*    exit=0
test_usercmd.exe     600 cases, 0 mismatch      (需在 tools\ 下运行读 cases.txt)
test_gs_vector.exe   len=263                    (需在 tests\fixtures\ 下运行)
```

## 5. 未完成 / 已知局限

1. **clipMap 精确解析未闭合**：`cLeaf_t` / `cLeafBrushNode_t` / `aabbTrees` / `cmodels` / `brushes` 的数组边界还没定位。zone 里这些数组的落盘顺序与 `clipMap_t` 字段序不同（ZoneBuilder 按 `SaveLogEnter` 顺序写：planes → staticModels → materials → brushsides → brushEdges → nodes → leafs → leafBrushes → leafBrushNodes → borders → partitions → aabbTrees → cmodels → brushes → brushBounds → smodelNodes）。
2. **碰撞是轴对齐近似**：29 个 clip 盒统一按 64×64×64、以实体 origin 为中心。实际 brush 尺寸未取到（实体串不含 size）。**地形/楼梯/斜坡没有碰撞**，只有平地 + 方形障碍。
3. **`codol_static_boxes` 会挡住 spawn 附近移动**：出生点 (48,-572,-116) 距最近 clip 盒 (-75,-434) 约 180 单位，暂不冲突；但若后续加入真实 brush 尺寸需重算。
4. **未实机验证**：按上一轮"没修完不要起"的约定，本轮没启动客户端。

## 6. 下一步（按优先级）

1. 把 `clipMap_t` 各数组边界闭合：以 `0x23F564` 的 7 组目录为起点，用"每个数组的元素尺寸 × count = 下一段偏移"做链式约束求解；`cLeaf_t=40B`、`cLeafBrushNode_t=20B`、`CollisionAabbTree=32B`、`cmodel_t=68B`、`cbrush_t=36B`。
2. 拿到真实 brush 后，用 `cbrush_t.sides → cbrushside_t.plane → cplane_s` 三元组做 `CM_BoxTrace` 的精确面测试，替换 AABB 近似。
3. 之后再处理小地图（common_mp.ff）、武器/外观（usercmd.weapon 恒 0 的替代来源）。

## 7. 受保护文件校验（AGENTS.md）

`REF_LOBBY_KIT\_golden_hashes.json` 9 项：**8 项 OK，1 项既有漂移**
`marketplace_store.py`（实际 50022 B / `E44358F0...`，期望 46226 B / `28B4A1BE...`，mtime 2026-10-16）。
本轮**未读写** `REF_LOBBY_KIT` 与 `CODOL_VERIFIED_GOLDEN_20261019` 任何文件。

---

# 2026-10-22 实机排查断点（clipmap/collision + 快照 + 装备）

## 0. 一句话状态

**服务端已对齐权威快照实现（124B playerstate + clientInfo 段），但客户端仍不采纳：出生卡房顶、背包固定、开火只扣弹、小地图空。**
根因已定位为 **服务端与客户端状态机互相覆写**，非单字段错误。**未修复。**

## 1. 本轮确认的硬事实（全部有日志/字节证据）

### 1.1 `omit_motion` 是唯一有实证支撑的开关

| 轮次 | omit | z 轨迹 | 判定 |
|---|---|---|---|
| `C_SERVER_FIRST3_20261021` | **1** | **-78 ~ -116 起伏（69 个不同值）** | ✅ 客户端自己跑物理 |
| 后续所有轮 | 0 | 恒定 -116 / -127 / -56 | ❌ 客户端直接采用服务端值 |

**注入前 `firingrange-gamestate.bin` 的 z 从未变化（35326 帧全 -116）。**

### 1.2 usercmd 解析器是正确的

- `test_usercmd` 600 自生成用例：0 失配
- **`real_cases.txt`（15 条真实客户端 body）：0 失配**
- 说明 `buttons` / `weapon` 解析无误

### 1.3 真实 usercmd 的按钮分布（本轮 FINAL 轮）

```
btn=0x20000800  18 次   bits=[11,29]   ← ADS + 未知位 29
btn=0x00000000   4 次
btn=0x10000000   1 次   bit28
```
**没有一帧含 bit0（开火）**。而标定轮（KEYMAP_CAL）中：
```
0x2002      bits=[1,13]        ← W+Shift（bit1=SPRINT ✓）
0x200       bits=[9]           ← 单独 Shift
0x20102801  bits=[0,11,13,20,29] ← 鼠标左键（bit0=ATTACK ✓）
```
**结论：按键位定义正确，但客户端在进图后停止上报真实按键（卡在残留值）。**

### 1.4 客户端显示的武器是 1159，不是我们发的 1156

- gamestate 的 `configstring[765] = "1159"`（`firingrange-gamestate.bin` @0x d0）
- `CODOL-DEMONWARE-EVIDENCE-BUNDLE` 与 `living-player-weapons-20260926.md` 均记录 **1159 = M4A1 Tech 典藏版**
- 我们快照 index 39 发 1156 → **客户端忽略**
- 用户确认：显示为 **"M4A1 Tech 典藏版，裸枪，只有一把"**

### 1.5 小地图依赖 `northyaw` / `compass_map_*`

反汇编 `image_t004.76s_100.bin` @`0x4EC170`：
```asm
push 0xdb9754        ; "northyaw"
push 0x32ad060       ; configstring base
call 0x4e88d0        ; Info_GetConfigValue
```
后续写 `[0x32af42c]`（sin/cos）与 `[0x32a73c4]`。
**主 configstring 里没有 `northyaw` → 小地图空。**

### 1.6 clientInfo 字段 0 = 11bit 武器子实体引用（已在本客户端二进制验证）

```
netfield 表 @0x00DA8078: {offset=0x140, width=11}
@0x0054BD7A: mov ecx,[ebx+0x140]; mov [edi+0x398],ecx
```
与 ol-mod `sv_snapshot_mp.cpp` 的 `ClientInfoLivingWeaponField = 0` 完全一致。
**已加入 `snapshot.c`，值恒 0（无 ET6 实体）。**

## 2. 本轮代码改动（全部编译通过）

| 文件 | 改动 | 状态 |
|---|---|---|
| `src/battle/snapshot.c` | 对齐 `CodolMotionSnapshot.cs`：124B；删多余 62/83/107/162；`groundEntityNum` 恒 2047；`ViewHeight` 60 直写；尾部补 clientInfo 段（127B） | 已编译，实机无效 |
| `src/battle/battle_service.c` | `omit_motion` 恢复为 `true`（镜像未命中时） | **未实机验证** |
| `src/battle/equipment.c` | 槽位武器 ID 恒定写自己；`usercmd.weapon` 只接受 1..2047 且命中已知槽位 | 已编译 |
| `src/world/usercmd.c` | 可靠命令文本带出到 `list->reliable[]` | 已编译 |
| `src/world/collision.c` | 新增：29 个 clip 盒 + 地面 z=-116，AABB sweep | 已编译，单测通过 |
| `src/world/player.c` | 真实重力 + 逐轴 sweep；新增 SPRINT(0x2) | 已编译 |

## 3. 测试状态

```
test_snapshot            127 bytes
test_snapshot_delta      ALL PASSED
test_player              ALL PASSED
test_equipment           ALL PASSED
test_collision           ALL PASSED
test_backpack_reliable   ALL PASSED
test_regression_20261022 ALL PASSED
test_usercmd             600 cases 0 mismatch（在 tools/ 下）
test_usercmd real_cases  15 cases 0 mismatch
```

## 4. 硬阻塞（不可绕过）

**ACE-BASE.sys / ACE-GAME.sys 内核驱动**拦截 `ReadProcessMemory`（err=5），
即使持有 `SeDebugPrivilege` 且 `OpenProcess` 成功。

**唯一可行读取方式（已验证）**：`CreateProcess(CREATE_SUSPENDED)` → `OpenProcess` → `ResumeThread`。
脚本：`CODOLServer\_mainline\_dyn100_mem.py`
本轮成功产物：`run_codol_001\runs\SUSPEND_DUMP_20261022\image_best.bin`
（10.39 MB，`nonzero=9354813`，`fails=0`）

**注意**：该脚本不启动 Auth/Lobby，客户端会卡在连接失败，但**解壳代码已在 t≈4.7s 完成**（该时刻 nonzero 从 6.4M 跳到 9.35M）。

## 5. 逆向进展与缺口

**已解出**（来自 `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\disasm_key2697.txt`，
该文件是 **2.6.9.7 服务端** `codol_dedrun.exe` 的反汇编，**不是 3.19 客户端**）：

```
_CODOL2697_WriteConfigstrings(msg, ctx, cstr, count, cmp, cmpCount):
    WriteByte(4)
    WriteShort(count)                 // ≤ 0x1DD7
    repeat: index_bits(index) + WriteString(value)
    WriteBits(cmpCount, 11)           // ≤ 0x7FF
    repeat: index_bits(index) + WriteBits(value, 10)
    WriteBits(?, 10)
    WriteBits(?, 4)
```

**缺口**：`index_bits()` 的位编码规则（递增索引如何压缩）。
`0x4A0400` 在**客户端**镜像里不是该函数（是 `std::vector::push_back`），
**地址来自 2.6.9.7 服务端，不能直接套用**。

## 6. 下一步（按性价比排序）

1. **实机验证 `omit=1`**（唯一有历史证据的改动）——只看出生点/移动
2. 若 omit=1 有效，再解决背包：需要 gamestate 的 `configstring[765]` 与快照 index39 一致（都用 1159 或都用 1156）
3. 小地图：主 configstring 加 `\northyaw\0`；`compass_map_*` 需真实地图边界
4. `index_bits` 逆向：低优先级，收益不确定

## 7. 受保护文件

`REF_LOBBY_KIT\_golden_hashes.json` 9 项：8 OK，1 既有漂移（`marketplace_store.py` 50022B vs 46226B，mtime 2026-10-16）。
本轮未读写 `REF_LOBBY_KIT` / `CODOL_VERIFIED_GOLDEN_20261019`。
