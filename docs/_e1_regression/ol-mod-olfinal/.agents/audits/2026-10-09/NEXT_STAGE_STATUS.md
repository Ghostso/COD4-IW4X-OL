# NEXT_STAGE_STATUS — 下一阶段状态（阶段 E，2026-10-09）

本文件是**新增的独立阶段记录**，不覆盖原始审计记录。
原始文件（AUDIT.md / EVIDENCE_STATUS.md / GOLDEN_COPY_SPEC.md / MANIFEST.json / NON_CODOL_SUBSTITUTIONS.md / SHA256SUMS.txt）保持第一次提交时的字节不变（提交 `6d2705d2`）。

---

## 0. 本阶段完成的动作

| 动作 | 结果 |
| --- | --- |
| 阶段一 保护现状（git 6 项 + 审计目录清单 + 备份核验） | 完成，与预期一致，未触发硬停止 |
| 阶段 A 审计基线固化（重算哈希 + 引用有效性 + 仅暂存审计目录 + 提交） | 完成，提交 `6d2705d2` |
| 阶段 A 追加修订（审计目录内 .gitattributes，保证跨 checkout 字节稳定） | 完成，已包含在 `6d2705d2` |
| 阶段 B1 匹配客户端 | `BLOCKED_NO_MATCHING_CLIENT` |
| 阶段 B2 完整资产集 | `BLOCKED_NO_VERIFIED_ASSET_SET` |
| 阶段 B3 构建工具链 | `BUILD_NOT_CONFIRMED`（工具链缺失） |
| 阶段 C 证据等级 + 运行验证计划 | 完成（RUNTIME_VALIDATION_PLAN.md） |
| 阶段 D S2/S3 原生数据路径分析 | 完成（S2_S3_NATIVE_DATA_PLAN.md），**未改默认行为** |
| 阶段 E 阶段记录 | 本文件 + PREREQUISITES.md + RUNTIME_VALIDATION_PLAN.md + S2_S3_NATIVE_DATA_PLAN.md |

---

## 1. 完成状态标记（逐项独立，不用单一总状态掩盖）

| 标记 | 状态 | 依据 |
| --- | --- | --- |
| `AUDIT_BASELINE_COMMITTED` | **成立** | 提交 `6d2705d27be5303000675ed0cff56af6e187bc9e`，7 文件 787 行；工作树 vs 提交 blob 逐文件字节一致（7/7） |
| `CLIENT_HASH_VERIFIED` | **不成立** | 扫描 2,138,998 文件，目标 SHA-256 E3823FD6... 未找到 |
| `ASSET_SET_VERIFIED` | **不成立** | 本机无地图 .ff；42 个 CODOL .ff 仅 16 个文件名、0 张地图 |
| `BUILD_CONFIRMED` | **不成立** | 无 MSVC / xmake / vcpkg / cmake / ninja / build 目录 |
| `PROTOCOL_TESTS_PASSED` | **不成立** | 无工具链，测试二进制从未运行 |
| `CLIENT_CONNECT_CONFIRMED` | **不成立** | NOT_OBSERVED + INSTRUMENTATION_BLOCKED |
| `GAMESTATE_ACCEPTED_CONFIRMED` | **不成立** | 同上 |
| `WORLD_SPAWN_CONFIRMED` | **不成立** | 同上 |
| `SNAPSHOT_FLOW_CONFIRMED` | **不成立** | 同上 |
| `TWO_CLIENT_GAMEPLAY_CONFIRMED` | **不成立** | 同上 |

**唯一成立的是基线固化。战斗服务器链路本阶段没有任何推进——这是事实，不是失败。**

---

## 2. 必须明确回答的 8 个问题

### Q1. 审计基线是否已安全提交？
**是。** 提交 `6d2705d27be5303000675ed0cff56af6e187bc9e`，message `docs: preserve OLMod audit baseline`。
- 暂存前工具检查: 7 个文件，全部位于 `.agents/audits/2026-10-09/`，`outside_audit_dir=0`。
- 提交后工作树 `git status --porcelain` = 0 行。
- 提交后逐文件比对: 工作树 SHA-256 与提交 blob 大小/内容一致（7/7 OK）。
- 与上游关系: `origin/OLfinal-live` 0 behind / 1 ahead —— **未推送**。
- 作者身份: 本机未配置 git identity（local 与 global 均为空）。提交使用**非持久化**的 `-c user.name='OLMod Audit Agent' -c user.email='olmod-audit@localhost'`，**未写入任何 git 配置**。如需改为你的身份，可 `git commit --amend --reset-author`。

### Q2. 匹配客户端是否找到并验证？
**否 → `BLOCKED_NO_MATCHING_CLIENT`。**
- 扫描范围 D: / E: / F: / G: / C:\Users，**2,138,998** 个文件。
- 候选 42 个，仅 **2 个不同构建**（`36997674...` ×41、`7B31168D...` ×1），**均不匹配**目标。
- `out.exe` 实例 **0** 个。
- **更正**: 上级指令中“out.exe 文件大小 1,649,370 bytes”是误读；`assets/backend/1004/Server/configs_s.info:314` 明确写 `build_number=1649370`，全仓库 283 处均作构建标识使用。按该大小搜索亦 0 命中。
- 未猜测任何 RVA/结构偏移/parser 行为。

### Q3. 完整资产集是否验证？
**否 → `BLOCKED_NO_VERIFIED_ASSET_SET`。**
- 配置目录 `D:\codo_3.19.26.13_fresh\CoD Online` **不存在**。
- 本机 CODOL 侧共 42 个 .ff（5 个目录），容器头全部 `IWff0100` **v8=461**，可读；
  但去重后**仅 16 个文件名**，且 **0 张地图 .ff**（唯一 mp_* 是 `mp_playlists.ff` 播放列表）。
- 全盘另有 24,662 个 .ff（约 59.6 GB）绝大部分属于**其他游戏**（IW4X、WWII、Infinite Warfare、WaW），**已明确排除，不作为 CODOL 原生数据**。
- 这些资产绑定旧沙箱客户端 `36997674...`，与目标构建无法建立可验证对应关系。

### Q4. 工具链是否可以实际构建？
**否 → `BUILD_NOT_CONFIRMED`。**
仓库声明需求: `set_toolchains("msvc")`、`c++latest`、`vcpkg::openssl`、`vcpkg::mhook`、`nlohmann_json 3.12.0`、`lua 5.4.8`(static)、triplet `x86-windows-static`、vcpkg `builtin-baseline aa2d3768...`。
环境实测: MSVC/VS、vswhere、xmake、vcpkg、cmake、ninja、`build/` **全部不存在**；仅有 Python 3.11 / git。
**未实际构建 → 不标记 BUILD_CONFIRMED。** 仅有工具存在也不构成可构建的证明。

### Q5. 哪些测试真正执行了，哪些只是设计了？
- **真正执行: 无。** 因为无工具链，7 个测试套件从未运行；阶段 B 的各项检查属于**环境与文件级核验**，不是仓库测试。
- **只是设计: RUNTIME_VALIDATION_PLAN.md 的十级阶梯全部；S2_S3_NATIVE_DATA_PLAN.md 的 T2.1-T2.6、T3.1-T3.5 全部。**
- 本阶段**实际执行并通过**的检查（可复核）: 审计文件哈希重算（6/6）、引用有效性（16/16）、备份文件级比对（821/821）、客户端全盘哈希比对、.ff 容器头读取（42/42）、工具链探测。
- 仓库内协议 fixture（ServerCoreTests.cpp:27314-27391、:27502-27555）**存在但未执行**，等级维持 CONFIRMED（作为字节证据）而非“测试通过”。

### Q6. 真实客户端链路验证推进到了哪个阶段？
按十级阶梯:
- 第 1 级（源码存在对应实现）: **成立**（CONFIRMED，本 HEAD 源码 + 本次逐行核验）。
- 第 2 级（协议 fixture 验证字节/解析）: **成立**（CONFIRMED，仓库内已提交捕获字节）。
- 第 3-10 级: **全部未到达**（NOT_OBSERVED / INSTRUMENTATION_BLOCKED）。

即: **仍停留在“源码 + 协议 fixture”层面，未进入任何真实运行验证。**

### Q7. S2/S3 各自的原生数据恢复路径？
**S2（玻璃阈值）**
- 现状: 阈值 `weaken=25 / destroy=100` 为 **Ghosts 推导**（Appmain.cpp:1397-1402，带 TODO）。
- 已恢复的 CODOL 原生部分: 玻璃**几何/边界**来自 FxWorld（`AssetTypeFxMap = 20`，EngineBindings.cpp:1033、15773-15884）；`SvGlassMapMetadata`（sv_collision_mp.hpp:292-298）**只有几何，没有阈值**。
- 原生阈值来源: TODO 指向 “CODOL server glass_map (**type 17**)”，但**全代码库不存在 type 17 的任何定义或读取路径**（本次 grep 核验）。它是**尚未定位的资产**，不是“已实现待接线”。
- 恢复路径: 用匹配客户端枚举 XAsset type 17 → 定位结构 → 确认 weaken/destroy 语义与档数 → 接入为可选原生来源，取不到时回退并标注来源。
- **不可直接删除默认值**: 缺失时 `glassDamageThresholds()` 返回 nullopt，Appmain.cpp:4390-4394 会 `reportFailure("glass_damage_thresholds")` 使**世界加载整体失败**。

**S3（destructible）**
- 现状: 7 类 CODOL 同名 type（本次逐行核验，sv_destructible_mp.cpp:34-55）使用 IW4 `_destructible.gsc` 的**血量序列 + 替换模型名**（源码 :11-13 自述）。
- 名称相同已确认；**血量序列/模型名与 CODOL 原生的一致性未证明**，不得声称兼容。
- 恢复路径: 从匹配客户端/地图资产定位 CODOL 原生 destructible 定义表 → 按同样准入校验接入 → IW4 表降级为显式标注的回退。
- 缺失时行为: 实体退化为普通布景（不崩）；但定义命中后模型解析失败会 world fail closed。
- **当前 S3 没有任何 env 开关**，无法在不改代码的情况下关闭 → 建议先加开关但保持默认不变。

### Q8. 哪些问题需要用户提供文件或人工确认？
1. **目标客户端**: SHA-256 = `E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B`（或另一个你确认的构建 + 其 SHA-256）。**阻塞 B1，进而阻塞一切协议级工作。**
2. **完整 CODOL 游戏目录**（含各地图 .ff），并与目标构建同源。**阻塞 B2 与一切运行验证。**
3. **构建工具链授权**: Visual Studio 2022(C++) + xmake + vcpkg(`x86-windows-static`, OpenSSL)。**阻塞 B3 与测试执行。**
4. **git 身份确认**: 是否用你的 name/email 重写提交作者（`git commit --amend --reset-author`）。
5. **OLfinal live 交接仓库**: `CODOL-main` / `OLFINAL-FFA-HANDOFF.md §191ak`（本机不存在），用于确认分支最新意图。
6. **PCAP 采集授权**: 是否允许建立抓包流程（可用 Windows 自带 pktmon），以及采集范围/留存策略。
7. **是否允许为 S2/S3 增加“可追溯性 + 开关但不改默认”的小改动**（需工具链才能验证）。

---

## 3. 硬停止条件检查

| 条件 | 本阶段是否触发 |
| --- | --- |
| 备份或哈希校验失败 | 否（备份 821/821 全等；审计文件 6/6 全等） |
| 工作树存在未解释差异 | 否（审计前仅有 `?? .agents/audits/`，与预期一致） |
| 无法确定某项修改是否覆盖用户工作 | 否（暂存前工具校验 `outside_audit_dir=0`，`modified_tracked=0`） |
| 目标客户端无法匹配却需依赖 RVA/结构偏移 | **未发生**——已停止在 `BLOCKED_NO_MATCHING_CLIENT`，未猜任何偏移 |
| 资产集无法验证却需推导原生游戏数据 | **未发生**——未推导任何原生数值 |
| 测试工具缺失却无法执行验证 | 是（已如实记录为 INSTRUMENTATION_BLOCKED，未伪造） |
| S2/S3 修改会改变行为但缺测试/回滚 | **未发生**——本阶段未修改任何默认行为 |

---

## 4. Git 状态变化（本阶段）

- 阶段开始: HEAD `3915fa98...`，`?? .agents/audits/`（6 个未跟踪文件），0 tracked 修改。
- 阶段结束: HEAD `6d2705d2...`（新增 1 个本地提交，7 文件 787 行），另新增本阶段 4 个文件 + 校验和文件（见 §5）。
- 与上游: 0 behind / **ahead N**（未推送）。
- **未修改任何既有源码、配置或资产文件。**

---

## 5. 本阶段新增文件

- PREREQUISITES.md（B1/B2/B3 结果）
- RUNTIME_VALIDATION_PLAN.md（十级阶梯 + 证据目录规范 + 防混淆规则）
- S2_S3_NATIVE_DATA_PLAN.md（S2/S3 调用链、来源、测试、最小修复、回滚）
- NEXT_STAGE_STATUS.md（本文件）
- SHA256SUMS_STAGE2.txt（上述文件的校验和；**不改动**原始 SHA256SUMS.txt）

---

## 6. 下一步动作（严格顺序）

1. 用户提供 §2-Q8 的 1-3 项（客户端 / 资产集 / 工具链）。
2. 重新执行 B1/B2/B3，取得 `CLIENT_HASH_VERIFIED` / `ASSET_SET_VERIFIED` / `BUILD_CONFIRMED`。
3. 构建并运行 7 个测试套件，取得 `PROTOCOL_TESTS_PASSED`（记录退出码 + 日志 + 产物 SHA-256）。
4. 按 RUNTIME_VALIDATION_PLAN.md 逐级推进第 5-10 级，每级产出唯一证据目录与哈希清单。
5. 首次进入战斗地图后，按 GOLDEN_COPY_SPEC.md 创建不可变 Golden Copy。
6. 仅在以上全部成立后，才考虑 S2/S3 的原生数据接入。

**任何一级未成立，均不得报告对应阶段成功。**
