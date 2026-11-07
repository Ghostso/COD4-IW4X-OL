# 047 — CODOL 战斗服实际构建与协议主路径闭环

**任务编号:** CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047
**状态:** 完成工程基线、模块实现与离线测试；最终 CODOL 线上协议保持显式阻塞。
**日期:** 2026-10-13

## 1. 一句话结论

本轮**建立了独立、可重复构建、可重复测试的 C# 战斗服工程**（.NET 8，31/31 测试通过，零警告），
把 2697 / legacy / 最终 CODOL 三条协议路径**在类型和注册表层面强制隔离**；
最终 CODOL 的 opcode、握手、reliable-command 与 snapshot 线格式**仍未实现，且代码会显式拒绝猜测**。
工作包 D 对 040–046 锁定的 socket 候选做了定向静态分析，得到可复核的**负证据**（可靠命令锚点的上游调用者不在 P4/P5），
但没有伪造一条未经证实的接收链。

## 2. 目录导航

| 文件 | 内容 |
|---|---|
| `01_BASELINE_AND_SCOPE.md` | 源码基线、版本、哈希、保护范围 |
| `02_EXISTING_CODE_AUDIT.md` | 现有模块复用与缺口 |
| `03_SERVER_ARCHITECTURE.md` | 模块边界、数据流、接口 |
| `04_IMPLEMENTED_MODULES.md` | 新增/修改代码及证据依据 |
| `05_PROTOCOL_EVIDENCE_BOUNDARIES.md` | 已知协议、未知协议、禁止推断项 |
| `06_CLIENT_GAME_RECEIVE_PATH.md` | 工作包 D 的静态闭环进展 |
| `07_MOVEMENT_STATE_MODEL.md` | 内部移动模型及限制 |
| `08_TESTS_AND_BUILD.md` | 构建、测试、已知失败项 |
| `09_ARTIFACT_MANIFEST.md` | 文件清单与 SHA-256 |
| `10_NEXT_IMPLEMENTATION_PLAN.md` | 048 可立即执行的模块级任务 |

工程入口：

```powershell
# 可重复构建 + 测试（唯一入口）
powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1

# 历史不可变性校验（040–046 + 原始 v0.1）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-history-immutability.ps1
```

## 3. 关键数字

- 新增 C# 源文件：13 个（库）+ 1 个测试工程
- 构建：成功，0 warning，0 error
- 测试：31 passed / 0 failed
- 历史不可变性：547 个文件校验，0 failures
- 最终 CODOL 线格式实现：**0**（显式阻塞）

## 4. 明确未完成（不得误读）

1. 没有修改客户端，没有把 2697 当作 CODOL 游戏协议。
2. 没有把内部 GameState/Movement 结构序列化为线上格式。
3. 没有证明客户端能进入战斗。
4. 工作包 D 得到的是**边界收敛与负证据**，不是完整 `接收→解析→分派→消费者` 链。
