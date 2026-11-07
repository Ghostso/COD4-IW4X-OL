# NON_CODOL_SUBSTITUTIONS — 非 CODOL 原生替代审计（2026-10-09）

任务硬约束: “CODOL 原始 FF/Zone/资产优先，禁止用 MW2/IW4X 资产替代 CODOL 资产。”
本文件只做**审计与测试方案**。**本任务不修改任何默认行为，也不删除任何实现**（见 §5 硬停止）。

证据等级: CONFIRMED = 本次直接读取源码核验；其余标注来源。

---

## 0. 汇总

| # | 替代项 | 位置 | 默认状态 | 影响范围 | 关闭后后果 | 等级 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | BO1 Der Riese donor 导航图 | src/game_server/server_mp/sv_zm_navgraph_bo1_hybrid_table_mp.cpp | **关闭（opt-in）** | 仅 zm_factory_sh 僵尸模式 | 无影响（默认本就不使用） | CONFIRMED |
| S2 | Ghosts 推得的玻璃伤害阈值 | src/game_server/Appmain.cpp:1394-1430 | **开启** | 所有含玻璃的地图 | **世界加载整体失败** | CONFIRMED |
| S3 | IW4 _destructible.gsc 的血量序列 + 替换模型名 | src/game_server/server_mp/sv_destructible_mp.cpp / .hpp | **开启（限 7 类 CODOL 同名 type）** | crash/SD 等含这些 MapEnt 的地图 | 这些实体退化为普通场景实体（不崩） | CONFIRMED |

前提说明: 树内**没有**任何非 CODOL **二进制资产**被打包（无 .ff/.d3dbsp/.gsc/.iwi/.dds）。以上三项替代都是**源码内嵌的数据/常量**，不是被复制的游戏资产。这一点很重要：它们是“数据来源”问题，不是“资产文件”问题。

---

## S1. BO1 donor 导航图（opt-in）

### 位置与自述
- src/game_server/server_mp/sv_zm_navgraph_bo1_hybrid_table_mp.cpp:1-6 自述: “BO1 Der Riese is a donor reference, not recovered CODOL aipaths”（BO1 Der Riese 是 donor 参照，不是恢复出的 CODOL aipaths）。
- 数据规模: 106 shadow nodes / 5553 walks / 17 heights，由 CODOL 采样生成（混合）。

### 默认启用条件（CONFIRMED）
Appmain.cpp:
- :4598 `auto navSource = SvZmNavSource::CodolRecovered;` —— **默认是 CODOL 恢复图**。
- :4600-4602 读取 env OLMOD_ZM_NAV_SOURCE，仅当其值恰为字符串 "bo1_hybrid" 时置位。
- :4603 该整段逻辑只在 `request->mapName == "zm_factory_sh"` 分支内。
- :4623-4625 `if (bo1HybridRequested) { navSource = SvZmNavSource::Bo1Hybrid; ... }`。

=> 结论: BO1 donor 图只有在**同时**满足（a）地图恰为 zm_factory_sh **且**（b）进程环境变量 OLMOD_ZM_NAV_SOURCE=bo1_hybrid 时才被使用。**默认路径不使用任何 BO1 数据。** 且它不是静默回退：不存在“CODOL 图缺失就自动用 BO1”的逻辑。

### 运行期门禁
- sv_zm_navgraph_mp.cpp:111-125: 当 source == Bo1Hybrid 时额外要求 reference walk validator（native world 地面 + 身体检查）通过；sv_zm_navgraph_mp.cpp:106-125 在节点与表不一致时**返回空图**（fail closed）。

### 受影响模式/地图
只影响僵尸模式（ZM），且当前只有 zm_factory_sh 有对应门禁与图。普通多人（MP）完全不受影响。

### 关闭后是否回归（CONFIRMED）
- 默认本就关闭，因此“删除该实现”对默认运行**零影响**。
- 若某次运行曾显式设置该 env：Appmain.cpp:4590-4593 注释说明，当 CODOL 图不可用/与地图节点不一致时，SV_BuildZmNavGraph 返回空图，**actors 会停在它们的 spawner 上，这是正确摆放而非降级模式**。即不会崩溃，表现为僵尸不巡逻。

### 测试方案（不改代码）
- T1.1 默认启动 zm_factory_sh，确认受控诊断中记录的 nav source 为 CodolRecovered（Appmain.cpp:5356 会打印 source 名），且不加载 BO1 表。
- T1.2 设置 OLMOD_ZM_NAV_SOURCE=bo1_hybrid 并重复，确认 source 变为 Bo1Hybrid 且 reference walk validator 生效。
- T1.3 设置 OLMOD_ZM_NAV_SOURCE=其他任意值，确认仍为 CodolRecovered（严格字符串比较）。
- T1.4 在非 zm_factory_sh 地图设置该 env，确认导航源不改变（地图分支限制）。
- 反证目标: 若 T1.1/T1.4 显示默认路径会消费 BO1 数据，则“opt-in only”结论被推翻。

---

## S2. Ghosts 推得的玻璃伤害阈值（默认开启，且是硬依赖）

### 位置与自述（CONFIRMED）
Appmain.cpp:1394-1430 `glassDamageThresholds()`:
- :1397-1398 显式注释: `TODO(CODOL): Remove the Ghosts-derived recovery defaults once a CODOL server glass_map (type 17) supplies the native thresholds.`
- :1399-1402 默认值 `{.weaken = 25, .destroy = 100}`。
- :1403-1422 读取 env；:1408-1409 **env 不存在时 return true（保留默认）** → 默认生效。
- :1423-1425 读取 OLMOD_GLASS_DAMAGE_TO_WEAKEN / OLMOD_GLASS_DAMAGE_TO_DESTROY，并要求 weaken <= destroy。
- :1426-1428 任一解析失败或 weaken > destroy → 返回 `std::nullopt`。

### 调用链（CONFIRMED）
- 消费点: Appmain.cpp:4389 `const auto glassThresholds = glassDamageThresholds();`
- :4390-4394 `if (!glassThresholds) { reportFailure("glass_damage_thresholds"); return; }`
- :4395 `Server.configureGlassMap(*glassMetadata, *glassThresholds)`
- 下游: sv_collision_mp.hpp:373-419 (SvGlassDamageThresholds / SvGlassDamageState::thresholds)，sv_main_mp.hpp:842 / sv_main_mp.cpp:2209，sv_snapshot_mp.hpp:2971 / sv_snapshot_mp.cpp:11272。

### 关键结论（本次最重要的发现）
**这些阈值是硬依赖，不是可选的 fallback。** 如果移除 Ghosts 默认值而又没有 CODOL 原生来源，`glassDamageThresholds()` 返回 nullopt，:4390-4394 直接 `reportFailure("glass_damage_thresholds")` 并 return —— **整个世界加载会失败**。

因此:
- 该替代**不能**被简单地“删除”或“改成默认关闭”。
- 必须先获得 CODOL 原生 glass_map（asset type 17）阈值，或明确决定“无阈值时以何种确定语义继续”（例如禁用玻璃伤害但照常加载世界），并把该语义写成有测试的契约。

### 受影响模式/地图
所有含玻璃的地图。文档声明曾对 27/27 glassed maps 测量过 bounds/relations（Agent 报告，未在本机复核）。

### 部分 CODOL 原生性
注意 glass 的 **bounds/relations 元数据**确实来自 CODOL 的 FxWorld（type 20）与原生 glass 系统（resolveGlassMapMetadata）；只有**伤害阈值**这一项是 Ghosts 推得。因此不能把整个 glass 链称为非 CODOL——必须精确区分。

### 关闭后是否回归
如上的 nullopt -> reportFailure：**世界加载失败**。这是必须记录的高风险点。

### 测试方案（不改代码）
- T2.1 默认运行任一带玻璃地图，确认世界加载成功（证明默认值在用）。
- T2.2 设置 OLMOD_GLASS_DAMAGE_TO_WEAKEN=100 且 DESTROY=25（weaken > destroy），观察是否按代码进入 reportFailure("glass_damage_thresholds") 并拒绝加载 —— 这可以**在不改代码的前提下实测出 nullopt 分支的真实后果**，直接量化“关闭默认值”的影响。
- T2.3 设置非法值（非数字/超 uint16），同样确认失败路径。
- T2.4 检查 CODOL 侧是否存在可用的 glass_map (type 17) 数据（需要匹配客户端与游戏目录；当前 INSTRUMENTATION_BLOCKED）。
- 反证目标: 若 T2.2 显示世界仍能加载，则“阈值是硬依赖”结论被推翻。

---

## S3. IW4 destructible 数据（默认对 7 类同名 type 开启）

### 位置与自述（CONFIRMED）
- sv_destructible_mp.cpp:11-13: `CODREF(g_damage): health sequences and replacement model names come from IW4's original _destructible.gsc. CODDIFF(g_damage): exposure is restricted to exact type names observed in CODOL crash MapEnts.`
- :16-30 起为 constexpr 阶段表，例如 FlatscreenStages = { Stage{1,{}}, Stage{200,"ma_flatscreen_tv_wallmount_broken_01"} } —— **血量序列与替换模型名同表**。
- sv_destructible_mp.hpp:99-104: `conservative IW4-derived subset. Only exact CODOL MapEnt type names whose state-health sequence is present in the original IW4 scripts are exposed here. CODOL-specific variants remain unsupported.` 并有 `TODO(CODOL): do not add tropical/ratnest02/tubetvsound/ceiling-fan variants until their title-local state tables and presentation are found.`

### 默认启用条件（CONFIRMED）
Appmain.cpp:5535-5538:
```
const auto *const destructible = gameplayActive
    ? CodolGameServer::SV_FindIw4DestructibleDefinition(scriptModelSpawn.destructibleType)
    : nullptr;
```
- 当实体 `gameplayActive` 为真，且其 destructibleType 命中 SV_FindIw4DestructibleDefinition（sv_destructible_mp.cpp:274）时，才注册为可破坏物。
- 因此**准入条件是双重的**: (a) 该 MapEnt type 名确实出现在真实 CODOL crash MapEnts 中；(b) 该 type 名存在于 IW4 派生表里。二者同时满足才启用。
- 文档/前期审计: 真实 crash MapEnts 共 82 个 destructible / 12 种类型，其中 7 种被覆盖，5 种（tropical / ratnest02 / tubetvsound / ceiling-fan 等）保持 unsupported。

### 受影响模式/地图
含这些 MapEnt 类型的地图（文档举例 crash + SD 配置）。ZM 的 board/barrier 走独立路径。

### 关闭后是否回归（CONFIRMED）
destructible 指针为 null 时，该实体**只是不作为可破坏物注册**（退化为普通场景实体），不触发世界加载失败。=> 关闭该替代是**优雅降级**（实体变成打不烂的布景），而非崩溃。

但需注意反向风险: 一旦**已解析**为 destructible，所有 stage/destroyed XModel 必须经 CCS 完整解析，任一缺失则 **world fail closed**（前期审计与源码注释一致）。即“启用后”是严格的，“禁用”是宽松的。

### CODOL 原生性区分（重要）
- 阶段**血量序列**与**替换模型名**来自 IW4 —— 这是真正的非 CODOL 数据。
- 替换模型名（如 ma_flatscreen_tv_wallmount_broken_01）仍需经 **CODOL 自己的 CCS resolver** 解析，解析不到即拒绝 —— 因此模型资产本身仍来自 CODOL 的 .ff，不会引入外部模型文件。

### 测试方案（不改代码）
- T3.1 在 crash/SD 默认运行中，通过只读诊断（CODOL_GameServerGetEntityDamageStatusV1 / CodolGameServerControl.py --damage-entity-num）确认被注册为 destructible 的实体集合，与“crash MapEnts 中 12 种类型、7 种覆盖”对照。
- T3.2 对 5 种 unsupported 类型中的实体确认其未被注册为 destructible（验证 fail-open 到普通实体）。
- T3.3 验证某个已注册实体的全部 stage/destroyed XModel 都能解析（验证 fail-closed 的严格性）。
- T3.4 静态核对: 阶段表模型名是否都能在已加载 CCS 中找到（需要匹配客户端与游戏目录，当前 INSTRUMENTATION_BLOCKED）。
- 反证目标: 若 T3.2 显示 unsupported 类型也被注册，则“双重准入”结论被推翻。

---

## 4. 不是替代的跨版本引用（避免误伤）

仓库内大量 IW4/BO1/BO2/Ghosts 字样是 **CODREF/CODDIFF 反编译参照**，不提供数据、也不改变行为，例如:
- sv_snapshot_mp.cpp 中的 field 编号/编码注释（来源是 CODOL 自己的 235/246 条 netfield 表）。
- tools/reverse/CodolBuiltinMatrix.py 抽取 BO1 builtin 表作为**证据列**；运行时 builtin 仍按 `kind:name` 键控（sv_script_builtin_mp.hpp:53-59），不使用 BO1 索引。
- Kodol/BO1 注释在 net_chan_mp.cpp、sv_client_spawn_mp.cpp 等处仅解释“为什么这样解释字节”。

**清理时必须按 CODREF/CODDIFF/OLMOD 标记区分，不得按字符串匹配批量删除。**

另有第 4 处“更彻底的替代”但性质不同: 整个脚本层被替换为项目自研 Lua VM（assets/game_scripts/*.lua，全局仅暴露 `codol`），不执行 CODOL GSC。这属于**自研实现**而非导入外部资产，本文件仅记录，不列为 S1-S3 同类项。

---

## 5. 硬停止与约束（本任务遵守）

- 任务规定: “不能确认替代逻辑的影响范围：不修改其默认行为。” 本任务**未修改任何默认行为**，也未删除任何实现。
- 任何后续改动必须先满足: (a) 已有 Phase 1 式可恢复备份并验证哈希；(b) 有回归证据；(c) 对 S2 必须先确定“无 CODOL 阈值时的确定语义”，否则会破坏世界加载。
- 不推送 origin。

---

## 6. 结论（对任务禁令的可执行回答）

- 真正需要处理的只有 **S2 与 S3**（默认开启）。S1 是 opt-in，不构成默认违规。
- **S2 不能直接删**：删除会导致世界加载失败；必须先取得 CODOL glass_map (type 17) 阈值，或定义并测试替代语义。
- **S3 可以安全降级**（实体退化为布景），但要先接受“可破坏玩法消失”这一功能损失，并记录 5 种 unsupported 类型本就未覆盖。
- 两者都需要**匹配的客户端与游戏目录**才能取得 CODOL 原生数据；当前为 INSTRUMENTATION_BLOCKED。
