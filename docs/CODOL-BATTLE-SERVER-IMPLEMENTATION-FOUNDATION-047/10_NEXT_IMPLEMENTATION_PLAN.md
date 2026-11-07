# 10 — 048 实施计划（模块级、可立即执行）

## 0. 原则

048 **不再是全面研究**。每个任务都以模块为单位、有输入、有输出、有验收断言。
继续禁止：修改客户端、猜测 opcode、把 2697 当最终协议、把内部模型当线上格式。

## 1. P0：补一条可复核的接收路径证据（不阻塞工程）

**048-T1 游戏 socket 收包点定向定位**

- 输入：046 `05_CLIENT_PATH_MAPPING.md` 的 P4/P5，047 的 4 份 evidence JSON。
- 步骤：
  1. 用更严格的函数边界（PE 异常目录/pdata 或栈帧模式）替换 047 的启发式 `find_func_start`。
  2. 对 P4/P5 各函数入口做双向调用图（上游调用者 + 下游被调用者）。
  3. 检查接收缓冲区来源：`WSARecvFrom/recvfrom` 结果如何流入解析函数。
- 输出：`evidence\048_T1_receive_candidates.json`。
- 验收：要么给出一条带地址的候选链，要么给出“P4/P5 均非 in-match netchan”的负证据。
- **禁止**：仅凭地址接近断言链闭合。

**048-T2 游戏串 xref 到 handler 的桥接**

- 输入：047 已定位的 `0x376B14`（13 个上游调用者）与 046 其他串锚点。
- 步骤：逐个调用者反汇编，确认其参数是否来自网络缓冲；区分“诊断打印点”与“分派点”。
- 输出：`evidence\048_T2_string_to_handler.json`。
- 验收：明确每个锚点是 `DIAGNOSTIC` / `DISPATCH_CANDIDATE` / `UNKNOWN`。

## 2. P1：协议模块（只在证据出现后）

**048-T3 FinalCodol opcode 分派骨架**

- 前置：048-T1/T2 至少定位到一个`读 opcode → 分支`的指令点。
- 实现：`Protocol\FinalCodol\OpcodeDispatcher`，未注册 opcode 一律 `UnknownOpcode`，不得落到默认业务处理。
- 验收：未知 opcode 测试 + 与 2697 不混用测试。

**048-T4 Reliable-command 线格式**

- 前置：确认最终客户端 opcode 与 ACK 语义。
- 实现：`FinalCodolReliableCodec`，与内部 `ReliableCommandChannel` 通过接口连接。
- 验收：已知抓包向量往返；未知字段显式拒绝。

**048-T5 Snapshot/Gamestate 解码**

- 前置：确认 netfield 表与 EOF 边界。
- 实现：只读解码器，输出到 `GameStateModel`。
- 验收：`gamestateupdate` / `configstring mismatch` 路径不再依赖猜测。

## 3. P2：工程加固（可与 P0/P1 并行）

| 任务 | 内容 | 验收 |
|---|---|---|
| 048-T6 | 把 31 项测试迁移/扩展到 xUnit 或 NUnit（当前为自研 runner） | 结果可被标准 CI 读取 |
| 048-T7 | 增加 `--simulate` 离线合成报文入口 | 不启动客户端即可跑 Transport+Session+2697 集成 |
| 048-T8 | CI 脚本：构建+测试+历史不可变性校验 | 一条命令，失败即非零退出 |
| 048-T9 | 把 `04_IMPLEMENTED_MODULES.md` 的证据等级接入构建期检查 | 未标注证据的线上格式代码导致构建失败 |

## 4. 完成 048 的判定

1. 至少 P0 有一个可复核产物。
2. P1 每个模块都有前置证据，否则保持未实现。
3. 构建/测试入口仍为一键、可重复。
4. 040–047 历史产物哈希不变。
