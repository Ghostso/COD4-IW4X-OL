# CODOL 大厅完整业务流程修复 056

当前：**R0 静态完整性完成；R1 PENDING_LIVE_VALIDATION（根因已定位：客户端视频资产缺失）。**

- [R0 基线完整性](R0_BASELINE_INTEGRITY.md)
- [R0 基线清单](R0_BASELINE_MANIFEST.json)
- [基线清单摘要](02_BASELINE_MANIFEST.md)
- [修复进度](01_REPAIR_PROGRESS.md)
- [PvE 实测与候选修复](03_PVE_REPAIR.md)
- [未解决阻塞](09_UNRESOLVED_BLOCKERS.md)
- [最终修复评估](10_FINAL_REPAIR_ASSESSMENT.md)
- [★ 大厅整体重构设计 v1.0（含 M0 结论，待评审）](11_RECONSTRUCTION_DESIGN.md)
- [M0 离线分析：Q1/Q2 已答，BP-07 作废](12_M0_OFFLINE_ANALYSIS.md)
- [★ M1/M1b 实验：Q3 已答 + 建房闸门结论修正](13_M1_MYHANDLER_RESULT.md)
- [★ 大厅全量深度逆向大纲（W1–W6）](14_LOBBY_RE_ATLAS_PLAN.md)
- [★ 大厅逆向发现 W1：类表 + UI→后端入口](15_LOBBY_RE_FINDINGS.md)
- [离线测试](TESTS/test_lobby_lifecycle.py)
- [证据索引](EVIDENCE/R1_LIVE_RUN_INDEX)
- [哈希](SHA256SUMS.txt)

五次官方客户端运行未恢复纯 PvE 战斗交接；R1 根因为客户端缺少 firingrange/cargoship 剧情 `_load.bk2` 视频资产，超出 056 范围。R2–R6 未验收。隔离补丁、候选 Kit 和离线测试均不得视为官方客户端通过。

