# CODOL-BATTLE-OOB-STATE-035 — 目标版本 OOB 状态机离线实现与对测

**目标：** CODOL **3.19.26.22** / Build **1649370**
**证据基座：** `CODOL-BATTLE-SERVER-TRACE-034`
**日期：** 2026-10-13（Asia/Shanghai）
**性质：** 独立 WorkCopy 中的离线实现 + 离线对测。**未改动 FREEZE-005**，**未改动正式服务器源码**，**未执行真实客户端 E2E**。

---

## 0. 一句话结论

> **已在独立模块中实现 TASK-034 已确认的 OOB 状态机子集，构建通过，离线自测 84/84 全绿（exit 0，确定性可复现）。**
> 同时，本轮**新增确认**了两条 TASK-034 未闭合的证据，并据此**更正**了 TASK-034 的两处描述：
> **① 状态 4 = `connect` + 28 键 userinfo；② 状态 5 = `stats`**（TASK-034 曾记为"未命名/无字面量"）。
> **3000 / 100 / 500 的业务语义仍未确认**，因此节流测试**仅**声明内部一致性，**不**声称与目标客户端精确时序一致。

---

## 1. 完成判据回答

| # | 问题 | 回答 |
|---|---|---|
| 1 | **哪些状态转换已由目标版本直接证实？** | 门 `state ∈ {3,4,5,6}`；**3 → `getchallenge 0 "%s"`**；**4 → `connect %s "%s"` + 28 键 userinfo**；**5 → `stats`**；**6 → `heartbeat`**；以及节流的**数值与适用状态**（3000 对 3/4，100 对 5，500 对 6）。全部以目标 RVA 为锚（见 `CONFIRMED_VS_UNKNOWN.tsv` 的 `E-*`）。 |
| 2 | **哪些只是服务器实现策略、尚未证实与客户端一致？** | ① 门 2 中 `[ebx+0x100260]` 被解读为"进行中/占用"（`INFERRED`）；② `cancelConnect` 仅关闭本会话、`Ordinal` 比较（服务器侧策略）；③ 未知/空/截断/缺终止符一律拒绝（服务器侧安全策略）；④ 把两个计时槽分别持久化的方式。全部在 `CONFIRMED_VS_UNKNOWN.tsv` 中标 `U-*` 或 `SERVER-SIDE POLICY`。 |
| 3 | **3000、100、500 各自的作用是否已确认？** | **未确认。** 已确认的是：**数值**（3000=0xBB8、100=0x64、500=0x1F4）、**适用状态**（3000→3/4；100→5；500→6）、**比较方向**（`<` 抑制）、以及 **3000 与 100/500 使用不同计时源**（`[ebx+0x30]` vs `[ebx+0x8]`）。**业务含义**（驻留/重试/心跳周期）**未确认**，报告与代码中均**未**赋予语义标签。 |
| 4 | **所有离线测试是否实际运行并通过？** | **是。** `pass=84 fail=0`，`RESULT: ALL GREEN`，**exit code 0**，且二次运行输出 SHA-256 与首次**相同**（确定性）。原始输出在 `build\selftest.output.txt`。 |
| 5 | **独立模块与现有服务器之间的最小集成差异是什么？** | **最小差异 = 在 legacy 发送路径前插入一个默认关闭的判定钩子**，其输入为客户端上报的 `clientState` 数字，并复用 `ThrottleGate` 的**双时间源**；其余 legacy 行为一律不动、不替换（`SERVER_INTEGRATION_GAP.tsv` 的 `GAP-INT-01`/`GAP-INT-10`）。 |
| 6 | **哪些未知项阻止宣称真实客户端兼容？** | 主要 9 项（`U-03` 状态业务语义、`U-05b` 状态 5/6 进入条件、`U-01/U-02` 三个阈值语义、`U-06` 接收分支体、`U-07` 入站信封、`U-09` 报文长度、`U-10` 种子生成、`U-04` 键→值映射、`U-08` cancelConnect 副作用）。因 `U-07`/`U-09` 未闭合，**当前模块不产出可发送报文**，仅产出判定与已确认字符串。 |

---

## 2. 交付物

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文件 |
| `OOB_STATE_MACHINE_SPEC.md` | 规格：地址核实、值域、门、节流、命令映射、接收、cancelConnect、状态分离 |
| `CONFIRMED_VS_UNKNOWN.tsv` | 19 条 `CONFIRMED`（`E-*`）+ 10 条 `UNKNOWN`（`U-*`），逐条带目标 RVA |
| `OOB_STATE_MACHINE_IMPLEMENTATION.md` | 模块与接口设计、构建、运行、缺陷修复记录 |
| `TV01_TV06_TEST_RESULTS.md` | 6 组测试 + 健壮性，逐断言结果 |
| `OOB_TEST_VECTORS.tsv` | 31 条向量（含 `NOT_RUN` 项） |
| `SERVER_INTEGRATION_GAP.tsv` | 10 条集成差异与最小接入步骤 |
| `UNKNOWN_AND_BLOCKERS.md` | 阻塞清单与下一步 |
| `FILE_HASH_MANIFEST.tsv` | 全部分析对象 + 源码 + 构建/测试产物的哈希 |
| `SHA256SUMS.txt` | 本目录交付物完整性清单 |
| `src\*.cs`（12 个）+ `src\build.ps1` + `src\run_selftest.ps1` | **源码与构建脚本**（按要求同时交付） |
| `build\bin\OobStateMachine.exe` | **构建输出**（19,456 B） |
| `build\selftest.output.txt` / `selftest.exitcode.txt` / `selftest.run2.txt` | **测试输出** |
| `evidence\*` | 本轮只读验证脚本与捕获输出 |

---

## 3. 目标证据核对（任务书 §二 要求逐条核对原始位置）

| 任务书列出的项 | 本轮核对结果 | 证据文件 |
|---|---|---|
| OOB 发送器 RVA `0x1C05F0` | **成立**（真实序言 `55 8b ec b8 bc 11 00 00`） | `evidence\dis_oob_full.out.txt` |
| OOB 接收器 RVA `0x1C13A0` | **成立**（真实序言）；且**扩展确认**为 7 令牌比较链 | `evidence\receiver_chain.out.txt` |
| `cancelConnect` handler RVA `0x1BF1C0` | **成立**（引用点 `0x1BF25C`） | `evidence\receiver_literals.out.txt` |
| `gamestateupdate` 引用点 RVA `0x73180` | **成立**（另一处 `0x054B7A` 未定入口） | `evidence\locate_local_battle_entries.out.txt` |
| 状态门 `[0x76446B0]`：何种地址表达/何对象 | **核实**：绝对寻址 `mov eax,[0x076446B0]`；位于 `.tp3` 但**超出 raw 文件**（未初始化数据段）；**进程全局变量**；193 处引用；5 处立即数写 `{3,4,7,0}` | `evidence\confirm_state_gate_address.out.txt`、`state_write_sites.out.txt` |
| 值集合 `{3,4,5,6}` | **成立**（`cmp` 3/4/6/5 + `jne`） | `evidence\dis_oob_full.out.txt` |
| 状态 3 有 `getchallenge` 路径 | **成立**（格式串 `getchallenge 0 "%s"`，19 B） | `evidence\branch_literals_full.out.txt` |
| 状态 6 有 `heartbeat` 路径 | **成立**（`heartbeat`，9 B） | 同上 |
| 节流 3000 / 100 / 500 | **成立**（0xBB8 / 0x64 / 0x1F4，各有状态守卫） | `evidence\oob_branch_throttle.out.txt` |
| 格式串 `getchallenge 0 "%s"` | **成立**（逐字节） | `evidence\oob_literals_exact.out.txt` |
| 接收器引用 `challengeResponse` / `connectResponse` | **成立**，且扩展为 7 令牌 | `evidence\receiver_literals.out.txt` |

**更正记录（2 处）：**
1. TASK-034 写"状态 4 分支未命名、状态 5 无字面量" → 本轮确认为 **state 4 = `connect` + userinfo**、**state 5 = `stats`**。
2. TASK-034 写"100/500 对所有状态执行" → 实为**各有状态守卫**（`esi∈{3,4}` / `eax==5` / `eax==6`）。

---

## 4. 安全与边界声明

- **未**修改 `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`（`FREEZE-005_REPORT.md` 哈希未变）。
- **未**修改 `CODOL-Combat-Server-v0.1`：`src/**/*.cs` 共 25 个文件，指纹仍为
  `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`（与 FREEZE-005 一致）。
- **未**修改原始游戏 EXE / DLL / 运行时镜像 / 抓包 / 既有证据。
- **保留旧协议模式**：模块不替换任何既有逻辑；集成方案要求默认关闭的独立开关（`GAP-INT-10`）。
- **未**把旧版本抓包时序作为 3.19.26.22 的预期行为。
- 所有**需推断**的转换（`[ebx+0x100260]` 语义、cancelConnect 副作用、拒绝策略）均与**已确认**转换分开登记。
- **未**声称真实客户端兼容性已验证。
- **未**扩展到 snapshot 实现。
