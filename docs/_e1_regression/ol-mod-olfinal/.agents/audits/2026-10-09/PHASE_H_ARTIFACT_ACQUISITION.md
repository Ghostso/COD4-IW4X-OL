# PHASE_H_ARTIFACT_ACQUISITION — 阶段 H 报告（2026-10-09）

新增阶段记录；**不覆盖** STAGE1–STAGE7 的冻结基线（本文件末尾列出全部校验结果）。

## H0 — 执行前完整性检查：与阶段 G 报告**一致，无差异**

| 项 | 期望（阶段 G） | 实测 | 一致 |
| --- | --- | --- | --- |
| HEAD | `0436ad1e7cf1cee9627418b3801153449b78a3d5` | 同 | ✅ |
| 分支 | `OLfinal-live` | `OLfinal-live` | ✅ |
| 工作树 / stash | 干净 / 0 | `porcelain=0` / `stash=0` | ✅ |
| 与上游 | 7 ahead / 0 behind | `0 7` | ✅ |
| 最近 7 个审计提交 | 仍在历史中 | 7 个全部按顺序存在 | ✅ |
| 七份清单 | 全部通过 | 6/6、4/4、3/3、3/3、14/14、3/3、2/2 | ✅ |
| 既有备份 | 存在 | 两个备份均存在 | ✅ |
| `src/` 相对 origin | 未修改 | **0** 个文件 | ✅ |
| 正式哈希配置 | 冻结 | 5 处 `E3823FD6...` 全部原样 | ✅ |
| S2/S3 默认值 | 冻结 | `weaken=25`/`destroy=100`（`Appmain.cpp:1400-1401`）、`SvZmNavSource::CodolRecovered`（`:4598`）原样 | ✅ |

未发现状态不符，未触发停止条件；未自动恢复或覆盖任何内容。

## H1 — 工件需求清单

见 `ARTIFACT_REQUIREMENTS.md`（A 客户端 / B 地图资产 / C 来源关联 / D 核验命令 / E 交付清单）。

## H2 — 可复现的只读核验命令

新增 **`inspect-artifact.ps1`**（只读，仅用 PowerShell/.NET，**不需安装任何依赖**）。已在本机对两个已知文件实测通过：

| 输入 | 输出 |
| --- | --- |
| `codoMP_client_shipRetail.exe` | `36997674…A0172B537`、7,841,344 B、`0x014C (x86)`、ImageBase `0x00400000`、节区 `.tp3×5,.tvm0`、FileVersion 1649370（标注 never identity） |
| `mp_playlists.ff` | `BFD4588D…C2B0F767`、49,493 B、`fastfile magic=IWff0100 version=461` |

命令保证: 只处理显式指定路径；不启动程序；不修改文件或配置；不遍历其他目录；**不写入正式期望哈希**。

## H3 — 静态重新标定准备（**只生成计划**）

见 `recalibration_worklist.json`：**79 对构建守卫** + **170 个 RVA 常量** + 5 项结构布局 + 2 项协议 + 2 项 S2/S3。

每条守卫均记录: 旧构建期望值、候选 A/B 实测值、证据类型、当前状态、未来所需输入工件、可接受证据标准、变更影响范围、回退方案。

**遵守的禁止项**：未重复全量扫描；**未把加壳候选字节用作新构建的期望值**。

## H4 — 工具与 fixture 影响清单

**关键判定原则：不得把“需要评估”直接等同于“必须修改”。**

### A. 有**证据**证明硬绑 3.3.3.3 的对象（若切换则必须重标）
| 对象 | 证据 | 结论 |
| --- | --- | --- |
| `tools/runtime/CodolMapEntDump.py` | `:20 EXPECTED_IMAGE_SHA256 = E3823FD6...`；`:172-174` 强制校验 | **依赖 3.3.3.3（已证实）** |
| `tools/runtime/CodolGlassAssetDump.py` | `:20`；`:267-269` 强制校验 | **依赖 3.3.3.3（已证实）** |
| `tools/runtime/CodolNetfieldDump.py` | `:20`；`:161-163` 强制校验 | **依赖 3.3.3.3（已证实）** |
| `tools/runtime/CodolWeaponHitLocationDump.py` | `:19`；`:160` 强制校验 | **依赖 3.3.3.3（已证实）** |
| `tools/reverse/catalogs/codol_builtin_matrix.json` | `:8 codol_client_sha256 = E3823FD6...` | **记录**该哈希（目录性记录，非强制校验） |

### B. 已具备**双构建**能力，切换成本低
| 对象 | 证据 |
| --- | --- |
| `tools/runtime/CodolMatchFlow.py` | `:86` 起已有独立 `"1649370"` 表；`:83` 记录 vtable 75 vs 88 项差异；`:26-27` 说明来源为 `re/olfinal/matchflow-1649370.json` |
| `tests/game_server/PlayerDataDefTests.cpp` | `:273` 载入 `mp_playerdata.def.1649370.bin`，`:278` 载入 `mp_playerdata.def.3333.bin` —— **两个构建都已测** |
| `tests/game_server/Fixtures/` | 同时含 `profile-69420.olfinal.document.bin` 与 `profile-seed.3333.document.bin` |
| `tests/game_server/ServerCoreTests.cpp` | 大量 `CODDIFF(1649370)` 注解（`:6857`、`:7198`、`:12733`、`:15371` 等） |

### C. **不能**断定依赖 3.3.3.3 的对象（仅需“评估”，非“必须修改”）
| 对象 | 现状证据 | 结论 |
| --- | --- | --- |
| `EngineBindings.hpp` 的 RVA/prefix 记录 | 170 个 RVA 与 104 个 prefix 数组，注释中大量 `CODDIFF(1649370)` | 记录面向**当前构建**；**无证据**表明专属于 3.3.3.3。需在内存上核验，**不可仅凭加壳文件字节判定** |
| `playerState_s` | `sv_native_playerstate_mp.hpp:17-23` 明确写 `0x3564` 是 **3.3.3.3 的**，本构建是 `0x3BBC` | 现记录**已经是 1649370 取向**，**不是** 3.3.3.3 依赖 |
| `entityState_s` | `sv_native_entitystate_mp.hpp:32-36` = `0x118`（`0x110` 才是 3.3.3.3） | 同上 |
| 协议 / netfield 表 | `EVIDENCE_STATUS.md` R5: 235 vs 246 冲突未解决 | `UNRESOLVED`，与构建切换无关的独立问题 |
| S2/S3 原生数据来源 | S2 的 asset type 17 在全树无定义；S3 的 7 类为 IW4 派生 | `UNKNOWN`/`UNPROVEN`，需匹配客户端才能推进 |

### D. 结论
**只有 A 组的 4 个 dump 工具 + 1 条哈希记录有确凿的 3.3.3.3 依赖。** 其余绝大多数要么已是双构建就绪，要么本就以 1649370 为取向，或与构建切换无关。**本阶段未修改其中任何一项。**

## H5 — 工件到位后的门禁 → 当前**无工件到位**

你未提供任何目标文件，因此：
| 状态 | 值 |
| --- | --- |
| 客户端 | **`NOT_FOUND`** |
| 地图 | **`NOT_FOUND`** |
| 门禁结果 | **`STOPPED_AT_ARTIFACT_GATE`** |

按授权要求：**不再重复扫描已覆盖目录**，只输出交付清单（见 `ARTIFACT_REQUIREMENTS.md` §E）。

**不得用更多静态分析代替缺失的原始证据。** 本轮到此停止。

## 交付物与基线状态

新增（全部在 `.agents/audits/2026-10-09/`）：`PHASE_H_ARTIFACT_ACQUISITION.md`、`ARTIFACT_REQUIREMENTS.md`、`artifact_provenance.json`、`recalibration_worklist.json`、`inspect-artifact.ps1`、`SHA256SUMS_STAGE8.txt`。

| 项 | 值 |
| --- | --- |
| 提交前独立备份 | `E:\OLMOD_BACKUP_PHASE_H_20261009042622`（审计目录完整副本，48 个文件） |
| `src/` 修改 | **0** |
| 正式期望哈希 / RVA / ABI / 协议常量 / S2-S3 默认值 | **未修改** |
| fixture | **未修改** |
| 工具链 | **未安装** |
| 构建 / 游戏运行 / 抓包 / Golden | **未执行** |
| 推送 / amend / reset / rebase | **未执行** |

独立备份: `E:\OLMOD_BACKUP_PHASE_H_20261009042622`（含 `MANIFEST.txt` 记录提交前 HEAD）。
