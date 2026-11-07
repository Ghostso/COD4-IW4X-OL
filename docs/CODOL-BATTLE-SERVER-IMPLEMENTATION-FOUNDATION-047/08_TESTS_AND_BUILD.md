# 08 — 构建与测试

## 1. 工具链

| 项 | 值 |
|---|---|
| SDK | .NET SDK 8.0.420 |
| Runtime | Microsoft.NETCore.App 8.0.26 |
| OS | Windows 10.0.19045, x64 |
| 目标框架 | net8.0 |
| 确定性构建 | 已启用（Deterministic + ContinuousIntegrationBuild） |

## 2. 构建命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1 -Configuration Release
```

## 3. 实测结果

- 构建：**成功**，0 warning，0 error。
- 测试：**31 passed / 0 failed / 31 total**，`RESULT=PASS`。
- 产物：
  - `src\Codol.BattleServer\bin\Release\net8.0\Codol.BattleServer.dll`
  - `tests\Codol.BattleServer.Tests\bin\Release\net8.0\Codol.BattleServer.Tests.dll`
- 哈希：见 `build\BUILD_MANIFEST.txt` 与 `09_ARTIFACT_MANIFEST.md`。

> **哈希口径说明**：两个工程均启用 `<Deterministic>true</Deterministic>` 与
> `<ContinuousIntegrationBuild>true</ContinuousIntegrationBuild>`。
> 实测连续两次构建（含 `--no-incremental`）产物 SHA-256 完全一致：
> `91EA16D80E544075B2857A40077C7BC198724C1DC48D5392D31757BBE0C9BB6F`。
> 因此 `build\BUILD_MANIFEST.txt` 的哈希是**逐字节可重复**的。

## 4. 测试分层

| 层 | 覆盖 |
|---|---|
| F1 单元 | 编解码边界、文本/长度、角度、方向、积分、快照模型 |
| F2 集成 | Transport↔Session、解码失败不破坏会话、版本不混用、未知 opcode 拒绝 |
| F3 构建 | 可重复构建脚本 + 构建产物哈希 |

## 5. 已知失败项

- 无测试失败项。
- **未验证项（非失败，是显式阻塞）:** 最终 CODOL 客户端兼容性、真实进入战斗、移动同步。
