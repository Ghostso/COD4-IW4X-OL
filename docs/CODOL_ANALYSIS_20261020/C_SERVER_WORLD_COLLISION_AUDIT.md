# CODOL C 服世界模型与碰撞审计

日期：2026-10-21（Asia/Shanghai）

范围：只读审计。没有启动客户端、战斗服、Auth/Lobby 或 IIPS，没有修改 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019`、原始客户端、地图文件或既有运行目录。

目标：解释当前战斗服“移动已修好，但人物仍穿墙、没有真正落地”的根因，列出继续实现所需的信息、获取方式，并对现有逆向资料做相关性分类。本文只是 CODOL 全栈审计中的“世界模型与碰撞”专章，不是整个服务器审计的完成声明。

## 0. 结论先行

当前现象不是单个移动公式错误，而是**服务器没有地图几何、没有地表查询、没有碰撞求解**。

现有实现能证明的事实：

1. `GameWorld.IntegratePlayer()` 只计算水平位移；
2. `VerticalSim=0` 时完全不改 `Z`，`OnGround` 只在出生/复活时置 `true`；
3. `VerticalSim=1` 时积分重力，但“地面”被硬编码为 `Spawn[2]`，不是从地图查询；
4. `OnGround` 与 `groundEntityNum` 的 2046/2047 是快照状态字段，不是服务端碰撞结果；
5. 工程注释和日志均明确承认“地图 BSP / Clip 真实碰撞未实现”；
6. 启动日志实际出现过“地图 mp_firingrange 未在已登记资产中找到”的警告。

因此：

```text
移动修复 = 输入方向 + 位置下发已接通
落地/碰撞 = 尚未实现，不是尚未调参
```

## 1. 当前实现调用链

```text
客户端 usercmd
  -> ClientLogic 解析
  -> GameWorld.IntegratePlayer()
       -> ComputeMoveVelocity()
       -> p.X += VX * dt
       -> p.Y += VY * dt
       -> [可选] IntegrateVertical()
            -> p.Z += VZ * dt
            -> groundZ = cfg.Spawn[2]   <-- 唯一地面
  -> MotionSnapshot
       -> groundEntityNum = OnGround ? 2046 : 2047
```

关键缺口位于 `p.X/p.Y` 更新之后与快照编码之前：没有以下任一调用：

```text
trace capsule / player bounds against clipMap
classify world contents
resolve penetration
detect floor / step / slope
set groundEntityNum from actual contact
```

## 2. 为什么不能归因于重力或快照字段

### 2.1 重力参数不是根因

`Gravity`、`JumpVelocity` 只影响 `vertical_sim=on` 的实验积分；实际生产配置 `firingrange_live.cfg` 仍是 `vertical_sim=0`。即使打开，落点仍只是出生点 Z。

### 2.2 快照的 `OnGround` 不是证据

`SnapshotOptions.OnGround` 来自 `PlayerState.OnGround`。该布尔值初始化为 `true`，在出生、复活时也会被强制设为 `true`；它不是“查询地面后得到的接触状态”。

### 2.3 `groundEntityNum=2046` 不能替代碰撞

写入 2046/2047 只是在协议字段里表达“地/空”。它不会在服务端或客户端自动生成 ground trace、墙体阻挡或世界接触。

### 2.4 “丢位置/镜像预测”不是修复方案

当前代码存在以下开关：

- `client_movement=1`：入场后省略位置/速度，让客户端预测；
- `omit_motion=1`：完全不发运动；
- `mirror_predicted=1`：回发客户端预测位置。

这些只能改变“谁覆盖状态”，不能给服务器提供地图碰撞。若服务端仍持续改写状态，客户端预测会被拉回；若完全不发，服务端又失去了权威。

## 3. 需要的服务端世界模型

对一个最小可玩对局，至少需要下面六类数据。

### 3.1 世界几何

```text
clipMap_t:
  planes
  nodes
  leafs
  leaf brushes
  brush sides
  brush models / static models
  contents / surface flags
```

用途：

- capsule / AABB 对世界做 sweep；
- 阻止水平穿墙；
- 识别地面、墙、天花板、斜坡；
- 设置真实的 `groundEntityNum` 与 `OnGround`；
- 处理台阶、斜面、角落、门窗。

### 3.2 出生和实体数据

```text
mapEnts entity string:
  info_player_start / info_player_deathmatch
  script_origin
  trigger / spawn / gametype filters
map_ents 或 addon_map_ents:
  额外实体、模式差异
```

用途：出生点不能再用单点常量；要按地图、队伍、模式与当前 space 选择有效出生点。

### 3.3 世界视觉/光照关联数据

```text
comWorld / gfxWorld / physics map
```

用途：至少用于从地图资源中解析空间边界、BSP 树和关联的物理/碰撞对象。不是先做渲染，而是把几何资产按正确类型加载。

### 3.4 玩家运动参数

```text
pmove 常数:
  gravity
  max speed / acceleration / friction
  jump velocity
  step height
  ground snap distance
  slope limits
  player mins/maxs
```

现有 `gravity=800`、`jump_velocity=270`、`walk_speed=190` 明确被代码标为“非实录”或“实验”值，不能直接当权威。

### 3.5 trace / collision 接口

服务端至少需要：

```text
SV_Trace / CM_BoxTrace / CM_TransformedBoxTrace
PointContents / BSP leaf lookup
plane / brush iteration
```

此处只登记缺口，不提前引入其他项目的结构或算法；跨项目可借鉴性在独立审计全部完成后单独判断。

### 3.6 权威帧与网络下发契约

```text
usercmd -> movement -> collision -> authoritative state
-> snapshot fields -> client prediction reconciliation
```

必须明确：

- 服务端是否接受客户端预测的位置；
- 哪些字段允许省略；
- 出现偏差时如何回正；
- 落地/离地/贴墙/台阶是否正确写入快照。

否则即使接上碰撞，网络层仍可能把正确位置覆盖成错误位置。

## 4. 当前缺失的信息与获取方式

### 4.1 地图资产层

| 缺失信息 | 当前状态 | 获取方式 |
|---|---|---|
| `mp_firingrange` 的 `clipMap_t` | 只有 `.ff` 容器，未见可直接读取的结构 | 对 `mp_firingrange.ff` 做 fastfile 资产解析，导出 CLIPMAP_MP(0xF) |
| `mapEnts` | 未见导出 | 导出 ASSET_TYPE_MAP_ENTS(0x13)，解析实体字符串 |
| `comWorld` | 未见导出 | 导出 ASSET_TYPE_COMWORLD(0x10)，确认空间/物理关联 |
| 地图 BSP / brush 原始结构 | 未见独立 `.d3dbsp/.bsp` 文件 | 从 fastfile 资产层获取，或由运行时资产注册表转储 |
| 地图资产名称/索引映射 | 有别名/路径线索，未闭合 | 从 zone 资产表与 `mp_firingrange` 加载日志建立映射 |

注意：`_map_extract` 下目前主要是 `.ff` 容器，不是已解析的地图几何。

### 4.2 地图位置层

| 缺失信息 | 当前状态 | 获取方式 |
|---|---|---|
| 真实出生点坐标 | 只有 `48,-572,-127.018` 常量 | 解析 `mapEnts` 的 spawn 实体，并在客户端/服务端两侧核对 |
| 出生朝向/队伍/模式过滤 | 未知 | 从 spawn entity 的 key/value 与 gametype 规则获取 |
| 地面高度 | 当前用出生平面代替 | 从 clipMap trace 或地图 geometry 查询 |
| 墙体/障碍物位置 | 完全没有 | 从 clipMap brushes/planes/leafs 获取 |

### 4.3 玩家运动层

| 缺失信息 | 当前状态 | 获取方式 |
|---|---|---|
| CODOL 3.19 的 pmove 常量 | 只有旧实现/实验值 | 客户端 pmove 反汇编 + 运行时观测 + 参考 IW4 结构 |
| 玩家碰撞盒 mins/maxs | 未闭合 | 客户端 pmove / G_SetOrigin / trace 调用观测 |
| step height / slope | 未闭合 | 客户端 pmove 与地图测试对照 |
| fall damage / landing | 未闭合 | 客户端战斗脚本、pmove 与状态字段的交叉验证 |
| ground trace 规则 | 未闭合 | 定位客户端 ground trace 调用并同步实现服务端 |

### 4.4 网络/权威层

| 缺失信息 | 当前状态 | 获取方式 |
|---|---|---|
| 位置字段何时省略 | 当前靠开关实验 | 观察客户端 ack、预测回正与快照字段消费 |
| `groundEntityNum` 的真实来源 | 当前是布尔映射 | 客户端 trace 结果与 snapshot 对照 |
| 快照 delta 基线 | 部分/未闭合 | 3.19 客户端快照 parser 继续取证 |
| 位置/速度一致性 | 当前会出现服务端覆盖预测 | 记录服务端 tx、客户端 ack、客户端 predicted 位置，做只读对照 |

## 5. 逆向资料分类

### 5.1 A 类：直接相关，应优先整理

| 目录/资料 | 相关性 | 用途 |
|---|---|---|
| `CODOL-BATTLE-SERVER-TRACE-034` | 高 | OOB、状态门、类型分派、snapshot 结构 |
| `CODOL-BATTLE-SERVER-CLIENT-GAME-RECEIVE-PATH-048` | 高 | 接收链、OOB token、P5 候选 |
| `CODOL-BATTLE-SERVER-RECEIVE-LINK-050` | 高 | P5 recv 到读取器的已知边与缺口 |
| `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046` | 高 | 移动/快照证据等级与错误推断纠正 |
| `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` | 高（服务端写法参考） | 2697 gamestate/configstring/snapshot writer 结构 |
| `CODOL-Combat-Server-v0.1` | 高（当前实现） | 世界、移动、快照、配置、日志 |
| `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin` | 高 | 3.19 客户端静态镜像 |
| `CODOLServer/_mainline/zonekey_der.hex`、`ff_zonekeys.json` | 高 | fastfile 解密与资产提取前提 |
| `_map_extract/mp_firingrange*.ff` | 高 | 当前地图资产 |
### 5.2 B 类：工程骨架相关，但不是 3.19 线协议事实

本阶段暂不引入 CoD4x 或 IW4X 的结论。两者将按照用户指定顺序，先各自独立审计，全部完成后再进入交叉验证阶段。

### 5.3 C 类：协议/运行证据，但不直接提供几何

| 目录/资料 | 相关性 | 说明 |
|---|---|---|
| `REF_LOBBY_KIT` 的 Auth/Lobby 记录 | 中 | 证明启动链和会话，不提供地图几何 |
| `HANDOFF_20261015_FIRINGRANGE_BRINGUP.md` | 中 | 记录快照卡点与运行时证据 |
| `FIRINGRANGE-BRINGUP-VERIFY-20261015` | 中 | 快照字节/运行对照，不是碰撞数据 |
| `CODOL_NATIVE_BATTLE_CHAIN_20261019` | 中 | 原生链/启动日志，非地图资产 |
| `DEMO_GOLDEN_BACKUP_20261015` | 中 | 可用于观察真实移动/出生/视角，但不直接给 clipMap |
| `DEV-BOOKING` | 中（协议/匹配） | 连接、booking、字段身份，不是碰撞 |

### 5.4 D 类：辅助或历史材料

| 目录/资料 | 相关性 | 说明 |
|---|---|---|
| `EARLY_SERVER_ANALYSIS` 的旧 CODOL 资料 | 低中 | 历史版本参考；须避免与当前 3.19 混同 |
| `_cleanout` 的大量脚本和切片 | 低中 | 需要按文件名/哈希筛选，不能整体当输入 |
| `backup_reverse_engineering` | 低中 | 历史备份，可能有重复/过期证据 |
| `_observer*`、`_core*`、`_ich*` | 低中 | 观察器与历史实验 |

历史实验的版本差异也必须保留：`FIRINGRANGE-BRINGUP-VERIFY-20261015` 的 `TX_SPAWN_EXPERIMENT` 使用 `z=-116`，当前 `firingrange_live.cfg` 则为 `z=-127.018`。两者不能混成同一出生/地面证据；后续应以同一次运行的地图资产、快照和客户端观测三方对齐。

### 5.5 E 类：与当前碰撞问题基本无关

| 目录/资料 | 相关性 | 说明 |
|---|---|---|
| `CODOL_VERIFIED_GOLDEN_20261019/mkt_assets` | 低 | 商店/资源目录，不是地图 clipMap |
| `CODOL_NATIVE_BATTLE_CHAIN_20261019/kit/mkt_assets` | 低 | marketplace 资产生成物 |
| 各种 marketplace `.ifs.paths.txt` | 低 | 商品路径，不是地图 |
| `tools/`、`pexports`、编译缓存 | 无 | 工具/中间产物 |
| 旧 `Kernel33`/patcher 资产 | 无（当前目标） | 不用于碰撞实现 |
| `_PLAINTEXT_PROJECT` 的商店/UI 明文 | 低 | 非世界几何 |

## 6. 明确的空白点（不自行补齐）

以下项目在现有资料中没有可复核的完整产物，必须等待用户后续逆向统一获取：

1. `mp_firingrange` 的 CLIPMAP_MP 资产导出结构；
2. `mp_firingrange` 的 MAP_ENTS 实体字符串完整内容；
3. `mp_firingrange` 的 COMWORLD / PHYSICS 关联表；
4. 地图 brush / plane / node / leaf 的字节级解析；
5. CODOL 3.19 玩家胶囊/盒体尺寸与 trace 参数；
6. `groundEntityNum` 的真实服务端生成点；
7. `pmove` 的台阶、斜坡、落地、贴墙规则；
8. 出生实体的队伍/模式过滤；
9. 服务端权威位置与客户端预测的正确回正策略；
10. 当前地图 zone 是否完整加载到 C 服资产表。

这些空白点不能用“已知重力值”“旧版 CoD4x 字段”或“项目侧实跑值”填补。

## 7. 建议的取证顺序

### P0：地图几何

1. 从 `mp_firingrange.ff` 解出 `ASSET_TYPE_CLIPMAP_MP`；
2. 同时解出 `ASSET_TYPE_MAP_ENTS`；
3. 验证资产名与 `mp_firingrange` 的对应关系；
4. 输出只读结构清单：brush/plane/node/leaf 的数量与偏移。

验收：

```text
能对给定坐标查询“是否在实体内”与“向下 trace 的距离”
```

### P1：玩家 trace

1. 从客户端/旧实现确认玩家 mins/maxs；
2. 实现只读的 `trace_player`；
3. 先用固定出生点测试“是否落地”，再测试“前进撞墙”；
4. 不接网络，只做离线几何验证。

### P2：服务端移动

1. 用 trace 替换 `groundZ = Spawn[2]`；
2. 处理水平 sweep、step up、slope、ground snap；
3. 只在 trace 成功时设置 `OnGround` 和 `groundEntityNum`；
4. 把结果与客户端实际 `pmove` 对照。

### P3：网络同步

1. 先验证入场帧位置；
2. 再验证每帧位置/速度；
3. 最后决定是否有条件省略位置或使用 predicted mirror；
4. 所有开关先离线回归，再进运行实验。

## 8. 最终判断

当前 C 服已经解决了“输入能变成水平移动”的问题，但尚未拥有“地图是什么、脚踩在哪里、墙在哪里”的模型。

因此下一步不应继续调 `gravity`、`spawn_y`、`groundEntityNum` 或快照开关，而应先获取并解析以下三件核心资产：

```text
CLIPMAP_MP
MAP_ENTS
COMWORLD / PHYSICS 关联
```

在这些资产可读之前，人物穿墙与无法真正落地是**结构性必然结果**，不是偶发 bug。
