# 第三轮证据总账

日期：2026-10-21（Asia/Shanghai）

本文件只登记证据入口和裁决依据，不重复复制其它报告。所有交叉结论都必须能回到这里列出的输入。

## 1. 目标轴：3.19

| 证据 | 入口 | 等级 | 允许用途 |
|---|---|---|---|
| 3.19 静态逆向汇总 | CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001 | E1/E2 | 客户端调用链、覆盖和缺口 |
| 3.19 battle trace 汇总 | CODOL-BATTLE-SERVER-TRACE-034 | E1/E2 | RX、状态、gamestate/snapshot 线索 |
| 第三轮前置证据 | R3_EVIDENCE_20261021_122246 | E1/E2 | 镜像边界、receive ledger、snapshot 冲突、FF layer-1 |
| 迟到抓包封口 | COLLECT_319_20261021_132905 | E3/negative | 负证据、抓包顺序、ACE 阻断 |
| 诊断运行封口 | ONCE_20261021_144241 / DIRECT_20261021_145654 | E3/negative | Auth/Lobby、booking、PID 断链、no mmstart |
| 目标客户端身份 | codoMP_client_shipRetail.exe SHA 36997674... | E1 | 版本裁决 |

## 2. 同族参考

| 对象 | 证据入口 | 等级 | 不允许用途 |
|---|---|---|---|
| 2697 | CODOL_2697_SERVER_STATIC_ANALYSIS_20261011 | E2/static | 不能作 3.19 wire golden |
| 3.3.3.3 ol-mod | _e1_regression/ol-mod-olfinal | E2/source | 不能直接套字段或资产 |
| 1.1.1.13 | 旧 C 服实验副本 | E2/history | 只保留历史条目 |

## 3. 外部架构参考

| 对象 | 证据入口 | 等级 | 保留边界 |
|---|---|---|---|
| CoD4x | COD4X_INDEPENDENT_AUDIT.md、CoD4x 源码 | E2/server architecture | 不用于 CODOL wire/asset |
| IW4X | IW4X_INDEPENDENT_AUDIT.md、iw4x-client | E2/host extension | 不用于 CODOL wire/struct |

## 4. 审计与交付文档

| 文档 | 用途 |
|---|---|
| C_SERVER_FULL_STACK_AUDIT.md | CODOL 自身 A-S 审计 |
| COD4X_INDEPENDENT_AUDIT.md | CoD4x 独立审计 |
| IW4X_INDEPENDENT_AUDIT.md | IW4X 独立审计 |
| CROSS_VALIDATION.md | 3.19 对全部、再剩余对象的交叉 |
| THIRD_ROUND_VERSION_MATRIX.md | 版本差异表 |
| THIRD_ROUND_CAPABILITY_MATRIX.md | 全服务器能力矩阵 |
| SERVER_RECONSTRUCTION_SPEC.md | 模块、所有权、接口、验收 |
| THIRD_ROUND_ACCEPTANCE_PLAN.md | 验收门与放行条件 |
| THIRD_ROUND_EXTERNAL_GAPS.md | 外部逆向与最终缺口 |

## 5. 证据使用规则

- 3.19 证据优先于所有同族和外部参考。
- 2697 只能作为同族行为对照，不能覆盖 3.19。
- 3.3.3.3 只能作为架构参考，不能覆盖 3.19。
- CoD4x/IW4X 只能提供服务器骨架、边界和算法。
- PARTIAL、CONFLICT、UNKNOWN 不得被改写成 PASS。
- 任何跨版本复制都必须保留来源、版本和证据 id。
