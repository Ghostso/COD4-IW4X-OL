# CODOL-ISSUE-0004 — 战斗服构建产物不可复现（test_session.exe 与 codol_battle_server.exe 同尺寸）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

build/Debug/codol_battle_server.exe = 314,368 B sha 275B165F…；build/Debug/test_session.exe = 314,368 B sha 2CEFF239…。当前 CMakeLists 中 test_session 的源文件仅 2 KB，不可能产出 314 KB。

## 2. 历史首次发现过程

- **首次发现**：UNKNOWN（`本次审计：build/Debug 逐文件哈希`）
- **最近验证**：2026-10-29
- **所属系统**：`build`　**优先级**：P1　**登记状态**：`UNVERIFIED`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 本审计对 build/Debug 全部 27 个 exe 做 SHA-256 | 发现两文件同尺寸不同哈希 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0004-01 | source | `CMakeLists.txt` | 全文 | 22 个 ctest 目标，无 test_session 大目标 | — |
| EV-0004-02 | location | `CMakeLists.txt` | 1-288 | 构建定义 | — |
| EV-0004-03 | location | `build/Debug/*.exe` | — | 27 个产物，mtime 10-21..10-26 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `CMakeLists.txt` | 全文 | 22 个 ctest 目标，无 test_session 大目标 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `CMakeLists.txt` | 1-288 | 构建定义 |
| `build/Debug/*.exe` | — | 27 个产物，mtime 10-21..10-26 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0004，系统 `build`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0004，系统 `build`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
源码 → CMake → build/Debug → kit 复制。链条中段无记录。
```

## 10. 第一条未闭合调用边

**10-26 22:07 那次构建的源码快照不存在。**

## 11. 已确认事实

- codol_battle_server.exe 与 kit 中那份逐字节相同（SHA 一致），即线上二进制确定来自该 build

## 12. 尚未确认的假设

- test_session.exe 为何 314 KB
- 哪些源码状态参与过构建

## 13. 已排除的假设

- '线上跑的不是这份源码'——kit 内 exe 哈希与 build 产物一致

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

CMakeLists 当前定义可读；build 目录是历史累积。

## 16. 最小复现条件

清空 build，用当前 CMakeLists 重建，比较 codol_battle_server.exe 的 SHA-256。

## 17. 最小验证实验

**实验 B4**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 建一个干净目录：cmake -S . -B build_clean -G "Visual Studio 17 2022" -A x64<br>2. cmake --build build_clean --config Debug<br>3. 比较 codol_battle_server.exe 哈希 |
| 通过判据 | 哈希与 275B165F… 一致 ⇒ 可复现 |
| 失败判据 | 不一致 ⇒ 当前源码≠线上二进制（重大） |
| 成本 | 离线 10 分钟 |

## 18. 条件式修复方案

**方案A：增加 CI 式干净构建 + 产物哈希记录（MANIFEST.sha256）。**

**方案B：把 build 目录纳入版本控制外的产物仓库，按 commit 存哈希。**

## 19. 修改影响分析

决定所有'改源码→行为变化'推断的有效性。

## 20. 可测量的验收标准

1. 同源码两次干净构建产出字节相同的 exe；或明确记录不可复现的原因。

## 21. 回归测试方案

每次构建写 build_manifest.json（源码哈希 + 产物哈希）。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B4：干净目录重建并比对哈希。
- **上游依赖**：`CODOL-ISSUE-0003`

---