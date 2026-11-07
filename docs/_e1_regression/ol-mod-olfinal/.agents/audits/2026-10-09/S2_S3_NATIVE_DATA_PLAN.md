# S2_S3_NATIVE_DATA_PLAN — 原生数据恢复路径分析（阶段 D，2026-10-09）

**本阶段只提交审计与测试方案。未修改任何默认行为，未删除任何实现。**
原始审计记录（含 NON_CODOL_SUBSTITUTIONS.md）保持原样，本文件为其后续深化。

---

# S2 — 玻璃伤害阈值

## S2.1 一手源码调用链

```
Appmain.cpp:4382  glassMetadata = Bindings.resolveGlassMapMetadata(request->mapName)
Appmain.cpp:4384  if (!glassMetadata) -> reportFailure("glass_map_metadata") ; return
Appmain.cpp:4389  glassThresholds = glassDamageThresholds()
Appmain.cpp:4390  if (!glassThresholds) -> reportFailure("glass_damage_thresholds") ; return   <<< 世界加载失败点
Appmain.cpp:4395  Server.configureGlassMap(*glassMetadata, *glassThresholds)
                   -> sv_main_mp.cpp:2207  ServerCore::configureGlassMap
                      -> sv_snapshot_mp.cpp:11270  SvServerWorld::configureGlassMap
                         -> SV_IsGlassMapMetadataValid  sv_collision_mp.cpp:543
```

### 阈值的产生（Appmain.cpp:1394-1430）
- :1399-1402 默认值 `{.weaken=25, .destroy=100}`，带 :1397-1398 的 `TODO(CODOL)`（明确写“Ghosts-derived recovery defaults”）。
- :1403-1422 读取 env；:1408-1409 **env 不存在时 return true → 保留默认（默认开启）**。
- :1423-1425 读 `OLMOD_GLASS_DAMAGE_TO_WEAKEN` / `OLMOD_GLASS_DAMAGE_TO_DESTROY`，要求 `weaken <= destroy`。
- :1426-1428 解析失败 / 越界 / `weaken > destroy` / 值为 0 → 返回 `std::nullopt`。

### 元数据的来源（CODOL 原生）
- EngineBindings.cpp:15773-15884 `resolveGlassMapMetadata`：
  - 资产路径 `maps/mp/<map>.d3dbsp`（:15784-15786），coop 图另加 borrowed `mp_*` 后缀（:15791-15792）。
  - 通过 `findXAsset(AssetTypeFxMap, ...)` 取 `NativeFxWorld`（:15800-15801）。
  - 读取 `world->glassSystem`：`definitionCount / pieceLimit / pieceWordCount / initialPieceCount / cellCount / activePieceCount`（:15824-15828）。
- **`AssetTypeFxMap = 20`**（EngineBindings.cpp:1033）。同文件:1034-1036 给出 `ClipMapSp=14 / ClipMapMp=15 / ComWorld=16`。

### 结构定义
- `SvGlassMapMetadata`（sv_collision_mp.hpp:292-298）= `{ uint32 definitionCount; vector<SvGlassInitialPieceGeometry> initialPieces; }`
  → **只有几何/分片元数据，没有任何伤害阈值字段。**
- `SvGlassDamageThresholds`（sv_collision_mp.hpp:373-378）= `{ ... }`（weaken / destroy），由 `SvGlassDamageState::thresholds()`（sv_collision_mp.cpp:778）暴露。
- 消费方: sv_collision_mp.cpp:713、sv_main_mp.cpp:2209、sv_snapshot_mp.cpp:11272、sv_bullet_mp.cpp:229/278、sv_melee_mp.cpp:22/204。

## S2.2 数据来源及可信度

| 数据 | 来源 | 可信度 |
| --- | --- | --- |
| 玻璃几何/边界/分片 | **CODOL 原生** FxWorld（type 20）glassSystem | CONFIRMED（本次读源码确认读取路径） |
| 伤害阈值 weaken=25 / destroy=100 | **Ghosts 推导**（源码自述） | 与 CODOL 原生语义的关系 **UNKNOWN** |
| “CODOL server glass_map (type 17)” | **仅存在于 TODO 注释**（Appmain.cpp:1398） | **该资产类型在代码库中未定义、未解析** |

关键结论（本次核验，非推断）: **全仓库不存在 asset type 17 的任何定义或读取路径**。grep `AssetTypeFxMap|AssetTypeGlassMap|...` 只得到 14/15/16/20/39。因此所谓 type-17 glass_map 是**尚未定位的资产**，不是“已实现但未接线的代码”。

## S2.3 已知行为与未知行为

已知:
- 阈值类型为整数（按 uint16 解析），语义为两档 `weaken` / `destroy`。
- 校验: 两值均须非零、可解析、且 `weaken <= destroy`。
- 缺失/非法 → 世界加载**整体失败**（不是降级）。
- 玻璃分片状态机有 **4 态**（SvGlassPieceState: Pristine / Weakened / Destroyed / Deleted，sv_collision_mp.hpp:303-309），但只有 **2 个阈值**。

未知:
- CODOL 是否真的存在 type-17 glass_map；其结构、字段、单位。
- 25/100 与 CODOL 原生数值之间的差异（可能不仅是数值不同，而是语义/档数不同——4 态 vs 2 阈值提示可能存在额外阈值或自动转换）。
- 阈值的原生缺省行为（CODOL 在没有阈值时是禁用玻璃伤害、还是用引擎内建值）。

## S2.4 失败模式

| 触发 | 行为 |
| --- | --- |
| env 未设置 | 使用 25/100，世界正常加载 |
| env 解析失败 / 越界 / 为 0 | `nullopt` → `reportFailure("glass_damage_thresholds")` → **世界加载失败** |
| `weaken > destroy` | 同上，世界加载失败 |
| `weaken == destroy` | **接受**（只拒绝严格大于） |
| 若未来移除默认值且无原生来源 | **世界加载失败**（当前最大的改造风险） |

## S2.5 可执行测试用例（**无需修改代码**）

| 用例 | 操作 | 期望 | 目的 |
| --- | --- | --- | --- |
| T2.1 | 默认启动，加载任一含玻璃地图 | 世界加载成功 | 证明默认值生效 |
| T2.2 | `OLMOD_GLASS_DAMAGE_TO_WEAKEN=100` `..._DESTROY=25` | 命中 `reportFailure("glass_damage_thresholds")`，拒绝加载 | **在不改代码前提下实测“无有效阈值”的后果** |
| T2.3 | 设非数字（如 `abc`）或 >65535 | 同上失败路径 | 覆盖解析/边界拒绝 |
| T2.4 | `WEAKEN=50` `DESTROY=50`（相等） | 接受并加载 | 确认边界是 `>` 而非 `>=` |
| T2.5 | `WEAKEN=0` | 失败路径（`!parsed`） | 确认 0 被拒 |
| T2.6 | 在目标客户端中枚举 XAsset type 17（需要匹配客户端） | 找到/找不到 glass_map | 定位原生阈值来源 |

反证目标: 若 T2.2 显示世界仍能加载，则“阈值是硬依赖”结论被推翻。

## S2.6 最小修复方案（建议，未实施）

前提: **不得在没有替代语义和回归测试的情况下关闭现有默认值。**

1. 保持不变（推荐的第一步）: 保留 25/100，但把“来源=Ghosts推导”写入运行日志与 summary，使每次运行都可追溯。
2. 引入可选的原生阈值提供者: 若能从 type-17（或其它 CODOL 原生来源）取得阈值，则优先使用并在 summary 中标注来源为 `codol-native`；取不到时回退到当前默认，并标注 `ghosts-derived`。
3. **在取得原生来源之前，不得**把默认值改为“缺失即禁用玻璃伤害”——因为那会改变世界加载的成败语义，需要独立回归。
4. 若最终要移除默认值，必须先定义并测试“无阈值时的确定语义”（例如: 世界照常加载 + 玻璃伤害禁用 + 明确日志 + 受控测试），并对 T2.1-T2.5 全部回归。

## S2.7 回滚方案

- 代码改动（若未来实施）: 单提交回滚 `git revert <commit>`；因当前判据集中在 `glassDamageThresholds()` 一处，回滚面很小。
- 运行期: 不设任何 `OLMOD_GLASS_DAMAGE_TO_*` 即回到默认 25/100。
- 注意: 当前**没有**“禁用整个玻璃阈值机制”的 env 开关，只有改数值的开关。

## S2.8 需要用户提供的资源

1. SHA-256 = E3823FD6... 的目标客户端（用于确认是否存在 type-17 资产及其结构）。
2. 完整游戏目录（含地图 .ff，用于实际加载含玻璃地图并跑 T2.1-T2.5）。
3. 可构建的工具链（用于任何代码级验证）。

---

# S3 — IW4 destructible 数据

## S3.1 涉及的 7 类 CODOL 同名 type（本次逐行核验）

来源: sv_destructible_mp.cpp:34-55（`constexpr std::array Definitions`）

| # | type 名 | 阶段血量序列 | 替换模型名 |
| --- | --- | --- | --- |
| 1 | `toy_tv_flatscreen_wallmount_01` | {1, 200} | （空，无替换模型） |
| 2 | `toy_transformer_small01` | {75, 75, 150, 250, 400} | `utility_transformer_small01_dest` |
| 3 | `toy_light_ceiling_fluorescent_single` | {150} | `me_lightfluohang_single_destroyed` |
| 4 | `vehicle_80s_sedan1_red` | {250, 200, 100, 300, 400} | `vehicle_80s_sedan1_red_destroyed` |
| 5 | `vehicle_80s_sedan1_green` | {250, 200, 100, 300, 400} | `vehicle_80s_sedan1_green_destroyed` |
| 6 | `vehicle_80s_sedan1_brn` | {250, 200, 100, 300, 400} | `vehicle_80s_sedan1_brn_destroyed` |
| 7 | `vehicle_pickup` | {300, 200, 100, 300, 400} | `vehicle_pickup_destroyed` |

阶段表定义: sv_destructible_mp.cpp:16-32（FlatscreenStages / TransformerStages / FluorescentLightStages / SedanStages / PickupStages）。

## S3.2 一手源码调用链

```
Appmain.cpp:5535  destructible = gameplayActive ? SV_FindIw4DestructibleDefinition(scriptModelSpawn.destructibleType) : nullptr
                   -> sv_destructible_mp.cpp:274-280  std::ranges::find(Definitions, type, &SvDestructibleDefinition::type)
Appmain.cpp:5539  if (destructible) { SV_ResolveDestructiblePresentation(*destructible, resolveModelConfigStringIndex) ... }
                   -> 模型名必须经 CODOL 自己的 CCS resolver 解析
Appmain.cpp:5548  SV_InitializeDestructibleDamageState(...)
伤害路径: SV_ApplyDestructibleEntityDamage(...)   sv_destructible_mp.hpp:91-97
                -> SvDestructibleModelResolver / SvResolvedDestructiblePresentation / SvEntityDamageMutation
校验: SV_IsDestructibleDefinitionValid  sv_destructible_mp.cpp:58+
```

## S3.3 “名称相同” vs “结构/语义相同”（任务要求的区分）

| 维度 | 是否相同 | 依据 |
| --- | --- | --- |
| type **名称** | 相同（按定义） | 源码注释自述“restricted to exact type names observed in CODOL crash MapEnts”（:12-13、hpp:99-101） |
| 阶段**血量序列** | **来源为 IW4**，是否等于 CODOL 原生**未知** | sv_destructible_mp.cpp:11-12 明确 `CODREF(g_damage): health sequences ... come from IW4's original _destructible.gsc` |
| 替换**模型名** | **来源同样标注为 IW4**，但模型必须经 CODOL CCS 解析 | :11-12 + Appmain.cpp:5541-5547 |
| 生命周期/消费者 | 由 CODOL 侧代码实现（SvDestructible* + CCS） | 上述调用链 |

=> 结论: **名称相同已由源码自述确认；血量序列与替换模型名的 CODOL 原生一致性未被证明。** 不得声称 IW4 数据与 CODOL 兼容。

补充（源码自身划界）: :268-270 `TODO(CODOL)` 明确“stage collision, part/tag mutation, animation, explosion radius damage and specialized vehicle behavior are not represented by this model/event-only plan and must not be inferred from type names”。即当前只覆盖 **模型 + 事件** 计划，不覆盖碰撞/部件/动画/爆炸。

## S3.4 替代数据缺失时为何退化为普通布景

Appmain.cpp:5535-5538 是三元表达式: 只有 `gameplayActive` 为真**且**定义命中时才得到非空指针；否则 `destructible == nullptr`。
Appmain.cpp:5539 `if (destructible)` 之后才注册可破坏状态与呈现。因此 **null 时该实体不被注册为可破坏物**，退化为普通场景实体，**不触发世界加载失败**。这与 S2 的硬依赖形成对照。

## S3.5 已知 / 未知

已知:
- 7 个 type 名与其阶段表（本次逐行核验）。
- 准入为“CODOL MapEnt type 名命中”+“IW4 表存在”双重条件。
- 定义命中后，阶段/终态模型必须经 CCS 解析成功——**任一缺失则 world fail closed**（严格）。
- 缺失定义时优雅降级为普通实体（宽松）。

未知:
- CODOL 原生 destructible 定义是否存在可读取的表（类型、阶段、阈值、替换资产）。
- IW4 血量数值与 CODOL 原生的差异。
- 其余 5 类 CODOL 类型（doc 提及 tropical / ratnest02 / tubetvsound / ceiling-fan 等）的原生定义。
- 车辆类（4 个 vehicle_*）在 CODOL 中是否真的走同一状态机。

## S3.6 失败模式

| 触发 | 行为 |
| --- | --- |
| type 不在 Definitions | 实体保持普通布景（无破坏），不崩 |
| type 命中但 stage/destroyed 模型无法解析 | **world fail closed**（整体拒绝） |
| CODOL 原生血量与 IW4 不同 | 表现上“打几下就碎/打不碎”，且**无法从日志区分**（当前不记录数据来源为 IW4） |

## S3.7 可执行测试用例

| 用例 | 操作 | 期望 | 目的 |
| --- | --- | --- | --- |
| T3.1 | crash/SD 默认运行，用 `CodolGameServerControl.py --damage-entity-num` 读回实体状态 | 得到被注册为 destructible 的实体集合 | 建立实际注册集合基线 |
| T3.2 | 对 5 类 unsupported 类型的实体读回状态 | 均**未**注册为 destructible | 验证双重准入的宽松端 |
| T3.3 | 对某个已注册实体核验全部 stage/destroyed 模型均可解析 | 全部解析成功 | 验证 fail-closed 的严格端 |
| T3.4 | 对已注册实体施加伤害并逐阶段读回 health/stage | 与表中序列一致且单调 | 验证阶段推进正确性 |
| T3.5 | 记录一次加载，确认日志中**是否**标注数据来源为 IW4 | 当前预期不标注 | 暴露可追溯性缺口 |

反证目标: 若 T3.2 显示 unsupported 类型也被注册，则“双重准入”结论被推翻。

## S3.8 最小修复方案（建议，未实施）

1. 可追溯性（最低成本，优先）: 在注册 destructible 时把“定义来源=IW4-derived”写入运行日志与 summary，使每次运行可分辨。
2. 增加显式开关（补上 S3 当前缺失的能力）: 现在 **S3 没有任何 env 开关**，无法在不改代码的情况下关闭；建议引入 `OLMOD_DESTRUCTIBLE_SOURCE=codol|iw4|off`，默认保持现状以不改变行为。
3. 原生恢复: 从匹配客户端/地图资产中定位 CODOL 原生 destructible 定义表，按同样的准入校验接入；在取得前保持 IW4 表并显式标注。
4. **不得**直接删除现有数据路径（会导致这些实体永远不可破坏，且丢失已恢复的模型/事件表现）。

## S3.9 回滚方案

- 代码改动（若未来实施）: 单提交回滚；改动集中在 Definitions 表与 Appmain.cpp:5535-5538 的准入。
- 运行期: 当前**无开关**；若实施 S3.8 第 2 项后，可用 `OLMOD_DESTRUCTIBLE_SOURCE=iw4` 回到现状。
- 备份: 已提交的审计基线 + E:\\OLMOD_BACKUP_20261009_095356 可用于对照恢复。

## S3.10 需要用户提供的资源

1. 目标客户端（用于定位 CODOL 原生 destructible 定义）。
2. 完整游戏目录（含 crash 地图，用于 T3.1-T3.5 实际运行）。
3. 可构建的工具链。

---

## 共同结论

- S2 与 S3 都**必须先有匹配客户端 + 完整资产集**才能取得 CODOL 原生数据；当前两者均 BLOCKED。
- 在此之前可做的**唯一安全动作**是“增加可追溯性/开关而不改变默认行为”，且仍需工具链才能验证。
- 两者都**不允许**在缺测试与回滚的情况下改动默认行为。
