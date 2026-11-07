# 全服务器审计索引

日期：2026-10-21（Asia/Shanghai）

状态：CODOL 第一轮完成；第二轮 CoD4x/IW4X 已完成当前材料范围内的独立静态审计并冻结。第三轮首批离线输入已入库审计为 PARTIAL；P0 仍为 0/11 闭合，第三轮交叉验证已启动，顺序为 3.19 对全部对象的一对多交叉，随后再做剩余对象交叉；协议与可玩性闭合结论仍按证据边界保留。第三轮捕捉 `COLLECT_319_20261021_132905` 已入库为 PARTIAL：迟到抓包、ACE 后零页可读、仅 3 帧 TCP/3074，P0 仍为 0/11。机器门禁 `THIRD_ROUND_BLOCKER_STATUS_20261021.json` 已静态核验：11 个 P0 全开放、12 个产物唯一、6 条禁止结论完整。诊断运行 `ONCE_20261021_144241` 与 `DIRECT_20261021_145654` 已单独登记为负证据；后者出现 20 次 `mmbook accepted`、0 次 `mmstart`、UDP/28960 零收包，且 2026-10-21T15:09:39+08:00 只读检查发现 Auth/Lobby/Battle Python 残留仍在监听 3074/28960。另完成 `Welcome_CODOL_client-main` 独立静态审计；它不属于 CoD4x/IW4X/C 服三方的交叉结论。

| 文件 | 阶段 | 当前状态 | 说明 |
|---|---|---|---|
| [AUDIT_ORDER.md](./AUDIT_ORDER.md) | 总则 | 已建立 | A-S 全栈覆盖、隔离顺序、完成判据 |
| [SERVER_RECONSTRUCTION_SPEC.md](./SERVER_RECONSTRUCTION_SPEC.md) | 1. CODOL 规格 | 已建立 | 全服务器检查表、证据等级、四层完成判据与当前禁止结论 |
| [C_SERVER_FULL_STACK_AUDIT.md](./C_SERVER_FULL_STACK_AUDIT.md) | 1. CODOL | 进行中 | 服务器系统全对象、网络、地图、世界、快照、模式、外围服务与逆向资产 |
| [C_SERVER_WORLD_COLLISION_AUDIT.md](./C_SERVER_WORLD_COLLISION_AUDIT.md) | 1. CODOL 专章 | 已建立 | 世界/碰撞专项证据，不是全服务器完成声明 |
| [COD4X_INDEPENDENT_AUDIT.md](./COD4X_INDEPENDENT_AUDIT.md) | 2. CoD4x | 进行中（内部主线基本建立） | 可读源码层与反汇编恢复层、构建/测试/资产缺口 |
| [IW4X_INDEPENDENT_AUDIT.md](./IW4X_INDEPENDENT_AUDIT.md) | 3. IW4X | 进行中（内部主线基本建立） | 扩展层、宿主 ABI、认证、netchan、资产、dedicated 与子模块缺口 |
| [CROSS_VALIDATION.md](./CROSS_VALIDATION.md) | 4. 交叉 | 已启动 | 3.19 对全部对象的一对多交叉；其余对象交叉为后续层 |
| [COd4x_IW4X_3.19_C_SERVER_LINEAGE_AND_REUSE.md](./COd4x_IW4X_3.19_C_SERVER_LINEAGE_AND_REUSE.md) | 早期交叉草稿 | 暂缓使用 | 保留历史，不作为独立审计结论 |
| [AUDIT_FILE_INVENTORY.csv](./AUDIT_FILE_INVENTORY.csv) | 1. CODOL 全工作区当前总账 | 第一轮完成 | 375,294 个路径逐行登记，全部 SHA-256；内容重复项按哈希关联 |
| [AUDIT_FILE_INVENTORY.summary.json](./AUDIT_FILE_INVENTORY.summary.json) | 1. CODOL 总账摘要 | 第一轮完成 | 数量、字节、对象归属、重复量和唯一内容总结 |
| [audit_file_inventory.py](./audit_file_inventory.py) | 1. CODOL 盘点工具 | 已核验 | 只读扫描；输出仅写入本审计目录 |
| [AUDIT_FIRST_ROUND_CLASSIFIED.csv](./AUDIT_FIRST_ROUND_CLASSIFIED.csv) | 1. CODOL 分类总账 | 第一轮完成 | 375,294 路径，修正 IW4X 第二轮标签 |
| [AUDIT_FIRST_ROUND_REPORT.json](./AUDIT_FIRST_ROUND_REPORT.json) | 1. CODOL 汇总 | 第一轮完成 | 目录、扩展名和对象统计 |
| [FIRST_ROUND_OBJECTS.md](./FIRST_ROUND_OBJECTS.md) | 1. CODOL 对象表 | 已建立 | O1-O12 身份、版本与用途 |
| [FIRST_ROUND_CONFLICTS.md](./FIRST_ROUND_CONFLICTS.md) | 1. CODOL 冲突表 | 已建立 | C-01 至 C-12 |
| [FIRST_ROUND_MATRIX.md](./FIRST_ROUND_MATRIX.md) | 1. CODOL 能力矩阵 | 已建立 | A-S 四列证据矩阵 |
| [FIRST_ROUND_MISSING_ARTIFACTS.md](./FIRST_ROUND_MISSING_ARTIFACTS.md) | 1. CODOL 补件表 | 已建立 | M-01 至 M-14 |
| [FIRST_ROUND_FREEZE.md](./FIRST_ROUND_FREEZE.md) | 1. CODOL 冻结声明 | 已建立 | 冻结证据身份与盘点，不冻结协议实现 |
| [FIRST_ROUND_KEY_FILES.csv](./FIRST_ROUND_KEY_FILES.csv) | 1. CODOL 高相关入口 | 第一轮完成 | 2,618 个可审计入口，不代表最终证据资格 |
| [SECOND_ROUND_OBJECTS.md](./SECOND_ROUND_OBJECTS.md) | 2. CoD4x + IW4X objects | 已建立 | identities, inventories, evidence links |
| [SECOND_ROUND_COD4X_EVIDENCE.md](./SECOND_ROUND_COD4X_EVIDENCE.md) | 2. CoD4x | 静态证据已冻结 | A-S domain anchors, socket/netchan/RCON/WebAdmin/plugin evidence |
| [SECOND_ROUND_IW4X_EVIDENCE.md](./SECOND_ROUND_IW4X_EVIDENCE.md) | 2. IW4X | 静态证据已冻结 | extension/host boundary, auth, RCon/HTTP, demo, rawfiles |
| [SECOND_ROUND_CONFLICTS.md](./SECOND_ROUND_CONFLICTS.md) | 2. 冲突表 | 已建立 | R-01..R-08, I-01..I-08 |
| [SECOND_ROUND_MATRIX.md](./SECOND_ROUND_MATRIX.md) | 2. A-S 矩阵 | 已建立 | CoD4x and IW4X independently populated |
| [SECOND_ROUND_MISSING_ARTIFACTS.md](./SECOND_ROUND_MISSING_ARTIFACTS.md) | 2. 补件表 | 已建立 | M2-C4-01..10, M2-IW-01..12 |
| [SECOND_ROUND_FREEZE.md](./SECOND_ROUND_FREEZE.md) | 2. 冻结声明 | 已建立 | static evidence only; build/run/host unresolved |
| [SECOND_ROUND_FREEZE_HASHES.json](./SECOND_ROUND_FREEZE_HASHES.json) | 2. 冻结哈希 | 已生成 | hashes for round-two evidence/inventory files |
| [SECOND_ROUND_INVENTORY_SUMMARY.json](./SECOND_ROUND_INVENTORY_SUMMARY.json) | 2. 独立清单摘要 | 已完成 | CoD4x 1,093 / IW4X 604 / rawfiles 7,439 paths |
| [SECOND_ROUND_COMBINED_CLASSIFIED.csv](./SECOND_ROUND_COMBINED_CLASSIFIED.csv) | 2. 独立清单总账 | 已完成 | path-level hashes for CoD4x, IW4X source and rawfiles |
| [SECOND_ROUND_COD4X_INVENTORY.csv](./SECOND_ROUND_COD4X_INVENTORY.csv) | 2. CoD4x 清单 | 已完成 | 1,093 paths, all hashed |
| [SECOND_ROUND_IW4X_SOURCE_INVENTORY.csv](./SECOND_ROUND_IW4X_SOURCE_INVENTORY.csv) | 2. IW4X 源码清单 | 已完成 | 604 paths, all hashed |
| [SECOND_ROUND_IW4X_RAW_ASSETS_INVENTORY.csv](./SECOND_ROUND_IW4X_RAW_ASSETS_INVENTORY.csv) | 2. IW4X rawfiles 清单 | 已完成 | 7,439 paths, all hashed |
| [THIRD_ROUND_PREREQUISITES.md](./THIRD_ROUND_PREREQUISITES.md) | 3. 前置证据 | 待补件 | P0/P1/P2 worklist for round-three evidence |
| [THIRD_ROUND_INTAKE_AUDIT.md](./THIRD_ROUND_INTAKE_AUDIT.md) | 3. 输入入库审计 | 已接收为 PARTIAL | 60 files / 58 hashes; P0 0/11 closed |
| [WELCOME_CODOL_CLIENT_INDEPENDENT_AUDIT.md](./WELCOME_CODOL_CLIENT_INDEPENDENT_AUDIT.md) | 4. Welcome_CODOL_client-main | 静态审计完成（当前包边界） | 148-file/14.77 MB独立清单；客户端离线适配工程；交付包内无服务器实现，未进入血缘交叉定论 |
| [WELCOME_CODOL_CLIENT_INVENTORY.csv](./WELCOME_CODOL_CLIENT_INVENTORY.csv) | 4. Welcome清单 | 已完成 | 148 paths, all SHA-256; source package read-only |
| [COLLECT_319_20261021_132905_INTAKE_AUDIT.md](./COLLECT_319_20261021_132905_INTAKE_AUDIT.md) | 3. 捕捉入库 | ACCEPTED AS PARTIAL | 103 hashes OK; late capture, ACE-blocked image, 3 TCP frames only; P0 0/11 |
| [THIRD_ROUND_BLOCKER_STATUS_20261021.json](./THIRD_ROUND_BLOCKER_STATUS_20261021.json) | 3. 机器门禁 | 已审计 | 11 个 P0 全开放；新 run、先抓包、同 PID、真实战斗与 consumer trace 门槛已固定 |
| [THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md](./THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md) | 3. 门禁审计 | 完成 | 数值与封口证据一致；门禁不关闭 P0，不授权协议/可玩性结论 |
| [DIAGNOSTIC_RUNS_20261021_144241_145654_CLOSURE_AUDIT.md](./DIAGNOSTIC_RUNS_20261021_144241_145654_CLOSURE_AUDIT.md) | 3. 诊断负证据 | CLEANUP CONFLICT | mmbook accepted 20 次、mmstart 0、UDP/28960 零收包；发现 15676/1624/17536 残留服务 |
| [DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.csv](./DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.csv) | 3. 诊断清单 | 已生成 | 434 paths, all independently SHA-256 hashed |
| [DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.summary.json](./DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.summary.json) | 3. 诊断清单摘要 | 已生成 | 112,934,300 B; raw pcap must not be published as-is |
| [THIRD_ROUND_EVIDENCE_LEDGER.md](./THIRD_ROUND_EVIDENCE_LEDGER.md) | 3. 第三轮证据总账 | 已建立 | 3.19 目标轴、同族参考和外部架构证据入口 |
| [THIRD_ROUND_VERSION_MATRIX.md](./THIRD_ROUND_VERSION_MATRIX.md) | 3. 版本差异 | 已建立 | 3.19 对 2697、3.3.3.3、1.1.1.13 及外部参考 |
| [THIRD_ROUND_CAPABILITY_MATRIX.md](./THIRD_ROUND_CAPABILITY_MATRIX.md) | 3. 能力矩阵 | 已建立 | A-S 目标状态、同族参考与外部参考分开登记 |
| [THIRD_ROUND_ACCEPTANCE_PLAN.md](./THIRD_ROUND_ACCEPTANCE_PLAN.md) | 3. 验收方案 | 已建立 | 构建、启动、协议、世界、移动、快照、对局和对照门 |
| [THIRD_ROUND_EXTERNAL_GAPS.md](./THIRD_ROUND_EXTERNAL_GAPS.md) | 3. 外部逆向需求 | 已建立 | 限制完整还原，不阻止第三轮分析启动 |
| [THIRD_ROUND_DELIVERABLE_AUDIT.md](./THIRD_ROUND_DELIVERABLE_AUDIT.md) | 3. 交付对照 | EVIDENCE_BOUNDARY_DOCUMENTED | 六项覆盖与六类最终产物逐项核对 |
| [DELIVERABLES_MANIFEST.md](./DELIVERABLES_MANIFEST.md) | 总产物目录 | 已生成 | 59 个正式顶层产物，逐文件大小与 SHA-256；临时文件单列 |
| [DELIVERABLES_MANIFEST.csv](./DELIVERABLES_MANIFEST.csv) | 产物目录数据 | 已生成 | 机器可读文件清单 |
| [DELIVERABLES_MANIFEST.summary.json](./DELIVERABLES_MANIFEST.summary.json) | 产物目录摘要 | 已生成 | 分类计数、字节与清单哈希 |

## 第一轮文件盘点结果

全工作区只读扫描，显式排除 `CoD4x_Server-21.2`、`IW4X`、`.git`、`__pycache__` 和本轮输出目录。

| 指标 | 结果 |
|---|---:|
| 登记路径 | 375,294 |
| 总字节 | 713,718,068,342 |
| 已计算 SHA-256 | 375,294 |
| 哈希延迟/失败 | 0 |
| 唯一内容 | 164,687 |
| 内容重复路径 | 232,713 |
| 误入并转第二轮的 IW4X rawfiles | 7,439 路径 / 1.03 GB |
| 关键大目录 | `工具` 238 GB、`REF_LOBBY_KIT` 133 GB、IIPS restore 约 141.8 GB、`run_codol_001` 约 104.9 GB |

该总账解决“有哪些文件、哈希、重复和对象归属”，不证明其中每个文件可用于 3.19 重构。完整结论见对象表、冲突表、A-S 矩阵和补件表。

## 本轮边界

- 未启动 CODOL 客户端、战斗服、Auth/Lobby 或 IIPS。
- 未修改 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019` 或其他冻结输入。
- 未执行 ol-mod 的构建、测试、安装或覆盖游戏目录。
- 清单中的 `/mem_linear*/` 与 `run_*` 是历史运行和扫描产物，不自动视为 3.19 可直接复用的证据。

## 当前一手证据入口

- CODOL：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001`、`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011`、`14_SERVER_KNOWLEDGE_ATLAS_001`、`11_CUSTOM_SERVER_FEASIBILITY_001`、`CODOL-BATTLE-SERVER-TRACE-034`
- CODOL C# 原型：`CODOL-Combat-Server-v0.1`
- CODOL 第二实现：`CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047`
- CODOL ol-mod 参考：`_e1_regression/ol-mod-olfinal`
- CoD4x：`CoD4x_Server-21.2`
- IW4X：`IW4X/iw4x-client`；资产候选 `DEV-BOOKING/_lineage021/iw4x-rawfiles`

## 仍需用户提供或后续统一逆向

1. 3.19 客户端的完整运行时镜像或等价静态恢复镜像。
2. 3.19 真实战斗通道抓包，至少含一条 configstring、gamestate 与 snapshot。
3. `mp_firingrange` 的 CLIPMAP_MP、MAP_ENTS、COMWORLD/PHYSICS 导出。
4. 用户所述 3.19 目标 C 语言战斗服的原始路径与构建标识；当前可见对象中，047 与 v0.1 为 C#，旧 C 服的版本为 1.1.1.13。
5. CoD4x 的可复现 32 位构建环境与合法 Cod4 服务端资产。
6. IW4X 16 个 submodule 的锁定版本初始化，以及匹配的 MW2/IW4 宿主二进制。

## 基线迁移状态（2026-10-21 14:30）

第三轮开放证据审查可以继续，下一轮正式采集仍为 **未授权启动**。当前机器门禁记录：

- `launch_authorized=false`
- `baseline_migration=BLOCKED_PENDING_USER_DECISION`
- 当前受保护文件 `8/9`；冲突为 `REF_LOBBY_KIT/marketplace_store.py`（50,022 B，golden 46,226 B）
- 已验证 `GOLDEN-LOBBY-001/REF_LOBBY_KIT` 为 9/9 文件源，但含旧日志、证书、会话文件和 `tas_off.flag`/`poke_off.flag` 等 13 项运行残留
- 原始 `run_all.py` 使用共享 `GAME_ROOT` 且默认 `--retries 6`，不满足单次启动与 run 隔离门禁

因此当前只允许基线决策、静态复核和采集准备，不允许启动新客户端。决策单见 [NEXT_RUN_BASELINE_DECISION_20261021.md](./NEXT_RUN_BASELINE_DECISION_20261021.md)，机器门禁见 [THIRD_ROUND_BLOCKER_STATUS_20261021.json](./THIRD_ROUND_BLOCKER_STATUS_20261021.json)。
