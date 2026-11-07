# PREFLIGHT_FALSE_POSITIVE_FIX — 修复记录（2026-10-09）

新增阶段记录，**不覆盖** SHA256SUMS.txt / STAGE2 / STAGE3 / STAGE4（本轮全部复验通过）。

## 1. 缺陷（上一轮已实证）

用 24 字节的 `IWff0100` 空壳文件即可让 `tokens.ASSET_SET_VERIFIED = true`。根因:
- `game.map_ff` 只做**文件名正则**；
- `game.header` 只探测**体积最大的那一个**文件；
- **从不检查资产与目标构建的关联**，也不要求完整性标准。

## 2. 修复后的判定（schemaVersion 2）

### ASSET_SET_VERIFIED 现在要求 **六项全部 PASS**
| 检查 id | 含义 |
| --- | --- |
| `game.map_ff` | 严格分类后至少 1 个地图 `.ff`（denylist 优先，见下） |
| `game.map_headers` | **每一个**地图候选都有可读 `IWff0100` 头 |
| `game.map_sizes` | 每一个地图候选 ≥ `-MinMapFastfileBytes`（默认 262144） |
| `game.map_hashes` | **每一个**地图候选都有 SHA-256 |
| `game.map_completeness` | 调用方给出的 `-RequiredMapFastfiles` 清单**全部存在** |
| `game.build_association` | 调用方给出**显式** `-ExpectedAssetBuildAssociation` 声明 |

任一项不满足 → 令牌为 `false`，状态为 `FAIL`，并在 `results.assetEvidence.missingEvidence` 中列出缺哪项证据。

### 分类 denylist 优先（解决 T4）
`playlist` / `^localized_` / `^code_` / `^common_` / `^ui_` / `^development` / `marketplace` / `loadscreen` **先**判定为非地图，
之后才看 `^(mp|zm|coop|sp)_`。因此 `mp_playlists.ff`、`ui_mp.ff`、`common_mp.ff`、`code_*` **永远不能**被当成地图。

### TOOLCHAIN_READY 现在要求 9 项全部 PASS
`tool.cl`（存在）、`tool.cl_version`（解析出 MSVC 版本）、`tool.cl_arch`（必须 x86）、`tool.xmake`（存在）、
`tool.xmake_version`（**≥ 3.0.9**）、`tool.vcpkg`（存在且解析出版本）、`tool.vcpkg_root`（有效目录）、
`tool.vcpkg_triplet`（`triplets\x86-windows-static.cmake` 存在）、`tool.openssl`（`installed\x86-windows-static\include\openssl\ssl.h` 存在）。

三级区分被明确记录: **命令存在**(`tool.cl`/`tool.xmake`) ≠ **依赖可用**(triplet/openssl) ≠ **构建成功**(`BUILD_CONFIRMED` 恒为 false)。
`cmake`/`ninja` 改为 `INFO`（本项目用 xmake，其缺失不是阻塞项，此前被误列为 FAIL）。

### FileVersion 与身份明确分离
`client.fileversion` 状态固定为 **`INFO`**，名称写明 “METADATA ONLY - never identity”，且**不参与任何令牌**。
身份只由 `client.sha256` 精确比对决定。

### 报告可复现性
报告改为两段: `runMetadata`（`generatedAt`、host、绝对路径输入）与 `results`（checks/tokens/verdict/evidence/manifest）。
新增 `-StableOut` 可单独导出 `results`。两次同参运行 **`results` 逐字节相同**（T9 实测），而 `runMetadata` 必然不同。

## 3. 反例测试结果（T1–T10，另加 T6b）

完整机读结果: `preflight_tests.json`；原始报告: `preflight-fix-evidence/*.json`。

| 测试 | 场景 | 结果 | 关键证据 |
| --- | --- | --- | --- |
| T1 | 24 字节 `IWff0100` 空壳 | **ASSET=false**, BLOCKED | `game.map_sizes=FAIL` |
| T2 | 文件名合规但内容无效 | **ASSET=false**, BLOCKED | `game.map_headers=FAIL` |
| T3 | 有效容器头但无构建关联证据 | **ASSET=false**, BLOCKED | `game.build_association=FAIL` |
| T4 | 只有 playlist/ui/common/code | **ASSET=false**, BLOCKED | `game.map_ff=FAIL`, mapCandidates=0 |
| T5 | 必需清单缺项 | **ASSET=false**, BLOCKED | `game.map_completeness=FAIL` |
| T6 | 工具命令存在但版本/架构/依赖不满足 | **TOOLCHAIN=false, ASSET=false**, BLOCKED | `cl=PASS` 但 `cl_arch=FAIL`、`xmake=PASS` 但 `xmake_version=FAIL`、`triplet=FAIL`、`openssl=FAIL` |
| **T6b** | **语义披露**: 同一桩工具链，但调用方提供可满足的资产集并显式声明关联 | **ASSET=true**, TOOLCHAIN=false, **BLOCKED** | 见 §4 |
| T7 | FileVersion 匹配但 SHA-256 不匹配 | **CLIENT=false**, BLOCKED | `client.sha256=FAIL`，`client.fileversion=INFO` |
| T8 | 报告 JSON 严格解析/UTF-8/LF | PASS | `BOM=false, CRLF=0, strictJson=true` |
| T9 | 重复执行比较稳定字段 | PASS | `results` 逐字节相同（14933 B） |
| T10 | 正常缺失客户端/地图/工具链 | **BLOCKED** | 12 个阻塞项，三个令牌均 false |

**验收: T1–T7 全部 `ASSET_SET_VERIFIED=false` 且 `verdict=BLOCKED` → 成立（11/11 通过）。**

### 关于 T6b 的诚实说明（不隐藏）
T6b **故意**让资产条件可满足，用来公开一个必须讲清楚的语义:
**`ASSET_SET_VERIFIED` 现在是「声明门控」的，不是独立证明。** 调用方只要声明了构建关联并满足其声明的完整性标准，该令牌就会为 true——
工具**无法**独立验证该声明，只能把它**逐字记录**进报告（`results.assetEvidence.associationDeclaration`）以便审计。
这是本次修复能达到的诚实上限: 它消除了**静默**假阳性（空壳文件、文件名匹配、头部合法都不再足够），但把「关联是否真实」变成了**显式、可追责的声明**，而不是伪造出来的验证结论。

## 4. 实际最小 diff

文件: `codol-preflight.v1-to-v2.diff`（31,097 字节，LF）
统计: `1 file changed, 206 insertions(+), 200 deletions(-)`

回滚方法: `git checkout 2823393 -- codol-preflight.ps1`，或从 `E:\OLMOD_BACKUP_PREFLIGHT_FIX_20261009035203\codol-preflight.ps1` 恢复（修复前 SHA-256 `4C2021CA28240F56BAD70E90057122855110CD15C21C16BC8B6B8AA7896778AA`）。

## 5. 未改变的东西

- **未改任何游戏逻辑、协议常量、RVA、ABI、S2/S3 默认行为**（`src/` 修改 = 0）；
- 未改客户端预期哈希（仍是 `E3823FD6...`）；
- 未安装任何工具、未构建、未运行游戏、未抓包、未生成 Golden；
- 未使用 amend / reset / 强推 / author 改写。
