# 147 · 快照实体基线、原生玩家状态镜像、启动器、bot 导航、击杀回放归档

## 一、范围

本报告完整学习 **5 个头文件**：

- `sv_snapshot_mp.hpp`（前 200 行：标志位与实体类型）
- `sv_native_playerstate_mp.hpp`（前 200 行）
- `sv_native_server_entity_mp.hpp`（75 行）
- `sv_launcher_launch_mp.hpp`（53 行）
- `sv_bot_nav_mp.hpp`（前 120 行）
- `sv_killcam_archive_mp.hpp`（80 行）

`server_mp` 进度推进到 **117/154**。

## 二、快照标志位：0x10 是本项目最重要的一次"缺失"

### 2.1 五个标志

| 值 | 名字 | 含义 |
|---:|---|---|
| 0x04 | SnapshotServerCountFlag | 带服务端数量 |
| 0x08 | SnapshotBaselineFlag | 基线帧 |
| 0x0A | SnapshotSceneBlockFlags | 场景块 |
| **0x10** | **SnapshotUseEntityBaselinesFlag** | **新实体解析 `cl.entityBaselines[num]`** |

### 2.2 0x10 的完整论证

```
0x10 → sub_470F20 @0x471300 调 sub_470E70(entityNumber, Dst):
    v2 = dword_77CE488[num];
    if (v2 > 0 && v2 < dword_7795824) qmemcpy(Dst, &unk_779E6E0 + 280*v2, 0x118);
    else                              memset(Dst, 0, 0x118);
```

注释的核心结论：

> **本服务器从未设置这一位，这就是地图几何不可见的原因。**

零售的静态 ET_SCRIPTMOVER 在线上几乎什么都不断言——2021 factory demo 里实体 43 在 349 帧断言里只带**一个** xModelIndex，实体 104 只带一个 `trBase[2]`——因为 origin、angles、model **全部来自客户端在地图加载时建的基线**。没有这一位，它们全从零解码 ⇒ 没有模型、什么都不画。

**为什么无条件设置是安全的**：客户端没有基线的实体号仍然拿到零结构，也就是今天的行为。风险不在标志，在**编号**——客户端按实体号索引，所以放在一个地图也在用的号上的实体会继承那个地图实体的 origin 和 model。

**编号在哪来的（重要）**：`dword_779E6E0` **不是** 从地图构建的——客户端在地图加载时从 `<map>_const.ff` 填，即每个地图都带的 `mp/constbaselines/bl_pc_<map>_<gametype>.bin`。**那个文件就是编号**：factory 的带 397 项、实体号 37..699，其中 238 个 brush model 正好是本服务器那 238 个 script_brushmodel。

所以这个标志由 `SvSnapshotFrame::useEntityBaselines` 驱动，**只有世界把这些静态实体发布在那些号上时才置位**；没有提取表的地图上它保持关闭，编号保持本服务器自己的。

`OLMOD_SNAPSHOT_ENTITY_BASELINES=0` 可以不开编译器关掉，用于在同一活客户端上 A/B 两种线形。

### 2.3 ps+0x10 的 flags 是**与引擎共享**的

```text
BG_PlayerStateToEntityState 测 (flags & 0x1800) 来在 ET_PLAYER / ET_INVISIBLE 之间选
这两个位是本服务器唯一拥有的部分
引擎把 stance 和 toggle 状态存在其余位里
PmoveSingle 测其中的 0x10000000
```

注释：**只在这里定义一次**——"一个数字出现在多于一个文件里已经让本项目付出过一次活 bind() 失败和一整个武器目录的代价（§43d）"。

`PlayerOtherFlagPlayer = 1u << 12`，`PlayerOtherFlagsServerOwnedMask = 0x1800`。

## 三、实体类型（eType）：19 与 21 都是演员，但 21 才对

| 值 | 名字 |
|---:|---|
| 0 | General |
| 1 | Player |
| 2 | Corpse |
| 3 | Item |
| **6** | **ScriptMover**（`sub_1F2EF0` 是唯一到达 `R_AddBrushModelToScene` 的呈现处理器 ⇒ 这个 eType 决定笔刷模型到底画不画；factory 全部 373 个 scriptmover 都是 6） |
| 19 | Actor |
| **21** | **ActorCorpse（零售实际发布的那个）** |

### 3.1 eType 19 的实测画像（64 条演员生命）

- 每条生命以 `pos.trType 1` 开场，**只出现 1 或 13**；19 条临近死亡时切到 13，无一回退；pos 与 apos **19/19 同时切换**；
- 位置与 yaw 几乎每帧流式（各约 2400 次断言），而 `pos.trDelta` 二十分钟只设了 18 次 ⇒ **服务端推送的行走者，不是客户端外推的轨迹**；
- pitch 与 roll **恒为零**，`groundEntityNum` **恒为 2047**。

### 3.2 为什么必须发 21

> 整个 zm 捕获里（12.30）：任何采样时刻 eType-19 实体**数量为零**，而 et21 在 3→36→56→30→16 之间变化；t=26350 时活着的 et21 是 **723、724、725**——正好是客户端 agent 数组与 `c_zom_garbageman_body_blue` / `_worker_` / `_ger_` 配对的那三个号。demoq 把 21 标成 `ET_ACTOR_CORPSE`，而它们显然不是尸体；**测到的是编号，不是名字**。

**不是外观问题**：`sub_540860` 对 eType 分支，它的 `case 19: case 21:` 以 `if (a2 && v14 == 21) sub_530E70(Source)` 结尾——**21 得到一个 19 永远拿不到的记录初始化器**，从**实体状态**（`Source+332`、`Source+352`）而不是从 agent element 填记录。发 19 完全绕开那条路径。

18 字段写入器原样转移：per-eType 的 index→offset 映射对 19 和 21 在**每一个共享 index 上都相同**（idx1 +0x040、idx2 +0x018、idx3 +0x01C、idx10 +0x08C、idx11 +0x058、idx14 +0x008、idx19 +0x00C、idx20 +0x030…），**只有值和它的 allow-list 变**。

`isActorEType` 必须接受两者，否则演员在序列化前就被丢（12.14 的失败，三次）。

`SvAgentSlotCount = 32`（`sub_530C30` 用 `cmp ecx,20h` 走记录数组），零售在规格捕获里对 31 个做差分编码。

### 3.3 agent 默认模板：XOR 基线必须与客户端一致

这是本组最有教育意义的一段。

快照字段是与基线 **XOR**（`writeUnsignedDelta` 写 `value ^ (baseline & mask)`），所以**服务端的 delta 基必须等于客户端的**，否则解出来的值是双方都没选的东西。

agent 槽**第一次出现**时客户端不是从零开始。`sub_471980` 拷一个 88 字节模板交给字段解码器当基线：

```text
sub_769710(v26, &unk_DA9920, 88);
sub_670FF0(v5, a4, v26, v16, 24, &unk_DA63E8, 3);
```

`unk_DA9920` 读作：

```text
+0x004 = 345    +0x008 = 2    +0x00C = 1266    +0x010 = 0xFFFFFFFF
+0x014 = 1267   +0x018 = 1317 +0x028 = 3       +0x034 = 3    +0x040 = 1
```

**实测后果（12.27）**：本服务器对零基线发 `modelIndex 310`，所以线上传 310；客户端算 `310 ^ (1266 & 0x3FF) = 310 ^ 242 = 452` 并存 452——**从客户端 agent 数组活读出来的**。模型永不解析，`record+568` 空，不构建 DObj。

**证明这条的对照实验**：队伍字段本来就用 `SvTeam::Sc (2)` 当基线——正好是 `+0x008`——而那个字段**单独**落地正确。它上面的注释已经为一个字段发现了这件事，却从未推广。

`ActorCorpseRingSize = 32`。

### 3.4 两条被默认关闭的实验

- **agent elements 发送**：第一次发 agent element 的构建在 world spawn 时挂死——日志停在 `SessionStart accepted` 与 gameplay script 第一条打印之间，所有服务端线程都在 Wait，没有一个在跑。那是 handoff 记录的 `loadGameplayScript` 死锁的形状，**尚未确定是本改动引起还是只是扩大了窗口**。关闭则恢复上一个能启动的构建的线形。
- **直线追击（stepActorEntities）**：按实测零售速度在平面上直冲最近玩家，**无寻路**——所以穿墙、立刻离开出生壁橱、最后站在玩家旁边的空地上。它证明了自己要证明的东西（流式 origin 能让客户端上的演员移动，12.33），所以留在 flag 后面。

## 四、原生玩家状态镜像：0x3BBC 而不是 0x3564

```text
0x3564 是 3.3.3.3 的 per-client 镜像。
本 build 是 0x3BBC：引擎自己的清除循环边界是 32 * stride
    A sub_464490  cmp ebx, 0x6AC80
    C sub_5BEB50  cmp ebx, 0x77780
    0x77780 / 32 = 0x3BBC
```

> PmoveSingle 通过这个缓冲区写入，所以**旧的尺寸比引擎认为自己拥有的少了 1624 字节**。

`SvNativePlayerState` 是 `alignas(uint32_t) array<byte, 0x3BBC>`，两个 static_assert 钉死尺寸与对齐。

### 4.1 一个反复出现的陷阱：原生缓冲会覆盖源副本

注释里三次以不同方式说同一件事：

> think 在 pmove 之后、**以及武器移动阶段之后再一次**把 native → source 投影，所以只在源副本里改正的值会在快照构建之前被从原生缓冲读回来并丢失。

对应的三个 setter：

- `SV_SetNativePlayerStateOtherFlags`——pmove 会用它自己的受保护存储覆盖 `ps+0x10`；
- `SV_SetNativePlayerStateCurrentWeapon`——同时写 `+0x2F4` 十五项武器列表的槽 0，因为"玩家并不持有的当前武器是原生转换器不必尊重的状态"；
- `SV_SetNativePlayerStateWeaponAmmo`——写 `+0x494` 的 clip 与 `+0x41C` 的 pool，以及 `+0x330` 的 `heldBefore`（它住在 held-weapon 状态记录里，不在 `+0x2F4` 的索引列表里）。

**弹药那条的来源**：

> 只填源副本的授予在快照构建前就被擦除，这正是"枪在手里、Out of ammo"从玩家侧看起来的样子。
>
> 为什么 clip 和 pool 都需要：clip 是 HUD 左边那个数字读的弹匣，也是武器唯一能开火的来源；pool 是斜杠后面的储备。**有 clip 无 pool 读作一把永远不能换弹的枪。**

### 4.2 副手状态是**视图不是字段**

```text
SvNativeOffhandState{ weaponAssetIndex, grenadeTimeLeft, field004C, throwbackTimeLeft, throwbackWeaponAssetIndex }
```
注释：`+48` 的烹饪计时器与旁边 `+50` 的 throwback 计时器是**不同的**。`field004C` 的注释写着"429450 写 entity-none 哨兵；owner 含义未确认"。

### 4.3 alt 武器槽

`SV_SetAltWeaponResolver` 的函数形态理由：

> 只有 EngineBindings 有模块基址，所以它读 weaponDefinition `+3720`（`sub_42EF60` 从 `+3716` 的名字链接的索引），这个 resolver 把答案传下来。**是函数不是字段**：往一个被按地址键控的原生缓冲包含的结构里加成员，正是两次弄坏死亡动画的原因（§184h），而这里没有任何东西需要被存储。

### 4.4 predictable event

```text
SvNativePredictableEvent{ int32 event, int32 parameter }  — 8 字节
SvNativePredictableEventBatch{ currentSequence, array<4>, count }
```

写自己的环：

> 写当前游标指名的槽，然后推进游标。两者都住在**原生缓冲**里，所以写在那里才能让添加存活下来——think 在每个阶段之后都会从它那里重读环与游标。

**为什么需要这个**：

> 把武器强推进 playerState 会让客户端**画**它，这和客户端**接收**它不是一回事。零售自己的 dmz 捕获先发一个可靠 `a <weapon>`，然后约 300 ms 后……

### 4.5 脚本化运动/视角的窄接口

四个 setter 刻意"不 round-trip 整个原生镜像"：

- `SV_SetNativePlayerStateScriptedMotion`：只重述 mission 脚本玩家轨拥有的五个运动字段（origin/pmType/pmFlags/groundEntityNum），**predictable events、武器状态和每一个未知的引擎拥有字节保持移动代码产出的样子**；
- `SV_SetNativePlayerStateScriptedViewAngles`：**两个数组都要写**——viewAngles 是快照发布的，deltaAngles 防止客户端下一条 usercmd 立刻把视角转回鼠标角度；
- `SV_SetNativePlayerStateScriptedViewLink`：free-look clamp 与 linked-camera 状态。

## 五、原生服务端实体：0x2C8 × 2046

```text
SvNativeServerEntity::Size     = 0x2C8
SvNativeServerEntity::Capacity = 2046
```

注释明确：这是"构建模板或某个原生槽的不透明备份"，**复制刻意保留原始字节**；按地址绑定的 entityState origin 只在从 `SvNativeEntityState` 发布到目标槽时被重定位。

三个阶段：`Collision / IncrementalCollision / Presentation`。

`SvNativeEntityStateSource` 带 `spawnGeneration`，注释是本组另一个重要发现：

> characterInfo 的动画 lerp 帧**只在角色选择时初始化一次**，重生既不改变选择也不改变模型上下文，所以没有这个字段时**死亡姿势会活到下一条命**，服务端骨架停在约腰高——打得到低处、永远打不到头，**第一条命之后的每一条命都如此**。`playerState +0x1F8` 的 spawnGeneration 是 CODOL 自己的 per-life 计数器，`SV_ClientSpawn` 已经在递增它。

## 六、启动器：一次按 int 读 float 的实测事故

```text
WeaponTypeLauncher = 2（rpg/javelin/stinger/at4/crossbow/sparrow）
手雷是 1，附件是 0
```

`SvLauncherProjectileParameters` 的六个数值字段全部是 **float**，注释记录了原因：

> ★ 2026-10-16 27:00——六个数值字段改 float（**实测更正，非设计变更**）。
>
> 活体日志（16:06 `rpgdragon_mp`）：按 int 读出 `1121714176 / 1114636288 / 1086324736` 等，**恰是 float 位模式**：`0x42DC0000=110.0`、`0x42700000=60.0`、`0x40C00000=6.0`（RPG 合理参数：内伤 110 / 外伤 60 / 半径 6）。
>
> C1 契约文档把 `794/798/79c` 标为 "signed int32" 是**磁盘资产序列化类型**；本代运行内存的 WeaponDef 里这些字段是 float（C1 消费者 `573f21` 本来就要 "convert to float"）。**按 int 读 ⇒ (float)1.12e9 初速 ⇒ 一帧飞出地图。**

速度计算：`forward * iProjectileSpeed`，加 `iProjectileSpeedUp` 到 z，再加 `iProjectileSpeedForward` 沿归一化水平前向。

## 七、bot 导航：另一套数据源，同一套路由

注释开头就解释了为什么它**独立于** `sv_zm_navgraph_mp`：

> 那个模块的图是**表驱动**的。`SV_ZmNavTable()` 返回针对某一份作者化地图实体串测出的边，对其它任何地图都返回 null，并明确指示调用方**停放演员而不是临时发明**。比赛 bot 有另一个更好的来源：`<map>_wp.csv` 随地图发布，**自带位置和有向链接**（运行时资产树里的 `waypoints/`）。所以这个模块产出**同形状**的图——`SV_ZmNavRoute` / `…AvoidingEdges` / `…ToClosestReachableNode` 接受的是图不是表——路由、边过滤和行走校验全部复用。

CSV 契约：首行节点数；之后每行 `"x y z"` / 空格分隔的链接索引 / stance / angles / target。**任何偏差都拒绝整张表而不是半装载**——"部分装载的图会让演员穿过从未被校验过的几何"。

`SvBotNavStance` 七个值，后三个（Climb/Claymore/Grenade/Javelin）是**普通站立节点上的战术标注，不是独立的通行模式**（重建树的加载器把它们映射到 STAND 并保留标签）。

加载报告字段：`source / reason / declaredNodes / parsedNodes / uniqueLinks / selfLinksDropped / duplicateLinksDropped / isolatedNodes / missingStanceNodes / maxOutDegree`。

> 只写 "failed" 的加载器每次都赔掉一次活会话。

上限：文件 4 MiB（最大随包 waypoint 略超 30 KB），节点 2048，每节点链接 48。

## 八、击杀回放归档：只有记录，没有回放

本阶段（A1）只建 A2 会重放的环形缓冲，`OLMOD_KILLCAM_ARCHIVE` 默认 **OFF**。

背景：2697 的 `_killcam.gsc` 设 `self.archivetime = killcamofftime`，当 `camtime <= 0` 时取消——即引擎没有录制的游戏时间可回退。本服务器有四个 playerState killcam 字段和 `setPlayerKillCam`，但**完全没有归档**，所以每次死亡都走取消分支（`killCamRecordingAvailable=false`）。

成本预算：

```text
24 clients × 160 frames × 32 B = 122,880 B 静态，编译期固定
Record() 是 O(1)，无分配，热路径不日志
```

帧结构 32 字节：

```text
timeMs(u32) / origin(3×f32) / view(2×f32: pitch,yaw) / weapon(u16) / pmType(u8) / health(u16)
```

窗口：`160 帧 × 20 Hz = 8 s`，覆盖 `SvKillCamPreKillMilliseconds(5000)` 加上 2697 最长 killcam（标枪 8 s）并留余量。

**重复/倒流时间戳被丢弃**，所以卡住或回退的 commandTime 永远不能污染环。

`SV_KillcamArchivePoseAt` 取"时间 ≤ targetMs 且最接近"的采样——这是 2697 的归档帧查找，做在项目侧位姿环而不是原生 `cachedSnapshot` 环上：

> `sv_snapshot.c:1843-1870` 通过读 `gametime = now - deltaTime` 的缓存实体来倒带，客户端纯粹因 `ps.deltaTime`(+0xa50) 非零而进入 killcam（`codol_engine_state.c:388-397`）。

## 九、关键结论

1. **0x10 标志的缺失解释了"地图几何不可见"**，而它的安全前提是编号——编号来自 `<map>_const.ff`，不是服务器自己编的。
2. **XOR 基线必须两端一致**：agent 槽首次出现时客户端用 `unk_DA9920` 那个 88 字节模板当基线，服务端用零基线就会解出 310^242=452 这样的垃圾。**而且有人曾经为一个字段（team，基线 2）发现过这件事却没有推广。**
3. **原生缓冲是"最后说话的人赢"**：think 在 pmove 后与武器移动后再各自投影一次，所以任何只在源副本里做的修正都会在快照前被擦掉。
4. **一个按 int 读 float 会让子弹一帧飞出地图**——这类错误在活体日志里表现为 1.12e9 这样的整数。
5. **spawnGeneration 不进入 characterInfo 就意味着死亡姿势活到下一条命**，症状是"永远打不到头"。
6. **19 与 21 都画演员，但 21 才走记录初始化路径**；发 19 是静默退化成另一条路径。

## 十、未闭合点

- 快照 0x10 依赖 const baseline 表；没有表的地图上保持关闭。
- agent elements 发送与直线追击都被默认关闭，且前者与一次 world spawn 挂死相关、原因未定。
- `SvNativeOffhandState::field004C` 的 owner 含义未确认。
- killcam 归档只有 A1（记录），A2（回放）尚未在本组出现。
- bot 导航要求地图随包提供 `<map>_wp.csv`，缺失即无导航（不是错误）。
