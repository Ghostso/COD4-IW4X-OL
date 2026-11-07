# 13 — E：GO / NO-GO 裁决

> 任务：`EARLY-NATIVE-TAP-BUILD-001`
> 边界：本文件只做静态裁决；**未应用补丁到实验副本、未编译、未运行任何游戏进程、未注入、未导出秘密材料**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## E.0 一句话裁决

- **设计草案：有条件通过（CONDITIONAL GO for design review）。**
- **构建阶段：NO-GO / INSTRUMENTATION_BLOCKED（工具链缺失，未产生候选二进制）。**
- **运行实验：NO-GO（不具备可运行候选产物，且运行时无扰动未验证）。**

`GO` 仅表示设计已通过审查、可以申请下一阶段授权，**不代表已获得运行授权，也不代表已验证互通**。

## E.1 逐项通过条件与阻塞项

| # | 条件 | 结果 | 状态 |
|---|---|---|---|
| A1 | 已确认源码根、构建系统、目标二进制 | 是 | **CONFIRMED** |
| A2 | 已创建独立实验副本，未覆盖原始/基线 | 是，3726/3726 匹配 | **CONFIRMED** |
| A3 | 已记录文件清单、SHA-256、构建配置 | 是 | **CONFIRMED** |
| A4 | 构建工具版本可确认 | 否，工具链不存在 | **INSTRUMENTATION_BLOCKED** |
| B1 | 观测点位于序列化后、发送前、加密前 | 是（源码级） | **CONFIRMED** |
| B2 | 不修改消息内容/长度/顺序/协议状态 | 源码审查未发现写回 | **STRONG_CANDIDATE** |
| B3 | 不添加强制状态转换、不改错误处理 | 是（源码审查） | **STRONG_CANDIDATE** |
| B4 | 不导出密钥/凭据/秘密 | 默认模式不读取 | **CONFIRMED（设计）** |
| B5 | 先输出 diff 供审查 | 是，`n3_hooks.diff` | **CONFIRMED** |
| B6 | diff 可干净应用 | 一次性临时副本 `git apply --check` 通过（5 文件） | **CONFIRMED（apply-check）** |
| B7 | 观测不会破坏缓冲区生命周期 | 调用点在 `msg` 有效期内、发送前；未异步持有 | **STRONG_CANDIDATE** |
| B8 | 观测不引入不合理时序影响 | 同步 I/O 可能影响时序，未验证 | **NOT_OBSERVED** |
| C1 | 在独立副本中构建候选产物 | 否，工具链缺失 | **INSTRUMENTATION_BLOCKED** |
| C2 | 不执行候选服务器/客户端 | 是，未运行 | **CONFIRMED（本轮操作记录）** |
| C3 | 不覆盖现有二进制 | 是，未构建 | **CONFIRMED（本轮操作记录）** |
| C4 | 不自动运行未知脚本 | 是 | **CONFIRMED（本轮操作记录）** |
| C5 | 记录完整构建命令/工具版本/结果 | 无构建，仅记录“未执行” | **NOT_OBSERVED** |
| C6 | 候选产物 SHA-256 可复核 | 无产物 | **NOT_OBSERVED** |

## E.2 阻塞项汇总

1. **工具链缺失**：`make`/`gcc`/`g++`/`windres`/`nasm`/`cl` 均未找到；`tools\BUILD-CODOL.ps1:40` 硬编码的 `C:\msys64\usr\bin\make.exe` 不存在。因此无法编译候选，无法产生可复核二进制。
2. **候选未编译验证**：类型自洽性目前仅为静态审查结论（`INSTRUMENTATION_BLOCKED`），不能声称“可编译”。
3. **运行时无扰动未验证**：同步 `fopen`/`fprintf`/`fflush` 对发送时序的影响为 `NOT_OBSERVED`。
4. **内部段 opcode 未解决**：N-3 整包观测只能得到整包首字节；内部 gamestate/snapshot 段 opcode 需要 N-1/N-2 段级观测。
5. **源码与二进制精确对应未定**：缺 commit/PDB/MAP/构建日志，精确对应关系为 `STRONG_CANDIDATE / UNKNOWN（精确 commit 层）`。

## E.3 阶段 D 验收问题逐条回答

1. **实验副本是否与原始源码清单一致，除明确记录的改动外？**
   是。3726/3726 纳入文件 SHA-256 匹配，0 差异；候选文件未进入副本。**CONFIRMED**。
2. **补丁是否仅增加观测能力？**
   设计层面是：只新增 cvar、一个 `void` 观察函数调用与两个新文件，未发现写回消息/客户端状态。**STRONG_CANDIDATE**（未编译、未运行）。
3. **是否存在消息内容、长度、顺序或错误处理被改变的风险？**
   直接写回风险低（源码审查未发现写操作）；但同步 I/O 可能改变发送时序，属**未验证风险**，状态 **NOT_OBSERVED**。
4. **是否能准确界定 gamestate 和 snapshot 的完整消息边界？**
   整包边界可确定（`msg->cursize` + `msg->data` 在发送前有效）；**内部段边界不能**仅靠 N-3 确定。整体状态 **STRONG_CANDIDATE（整包）/ UNKNOWN（内部段）**。
5. **捕获设计是否排除了认证秘密？**
   默认元数据模式不读取密钥/凭据，可行；完整载荷模式**未批准**，需先做秘密过滤审查。状态 **CONFIRMED（默认模式）/ INSTRUMENTATION_BLOCKED（完整载荷）**。
6. **构建是否成功，产物是否可复核？**
   否，未构建，无产物。**INSTRUMENTATION_BLOCKED**。
7. **是否具备申请独立运行实验的条件？**
   否。缺可运行候选二进制与运行时无扰动证据。**NO-GO**。

## E.4 对后续任务的授权含义

- 本裁决**不授予**任何运行、注入、编译或应用补丁的授权；
- 若后续获得 32 位 MinGW/MSYS2 工具链，可先申请“仅对象编译/构建验证”任务，不涉及运行；
- 只有构建成功且候选通过独立审查后，才可申请单次运行实验；
- 运行实验仍须满足 `11_F_GO_NO_GO.md` 与 `12_NO_GO.md` 的全部前置条件。

## E.5 最终裁决

**设计草案：CONDITIONAL GO。构建：NO-GO / INSTRUMENTATION_BLOCKED。运行实验：NO-GO。**