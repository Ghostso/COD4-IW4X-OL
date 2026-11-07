# 08 — 构建、测试与回归结果

所有命令都在 047 工程根目录执行;均在**本机 .NET 8.0.420** 上真实运行。

---

## 1. 构建

```
> dotnet build CODOL.BattleServer.Foundation.sln -c Release --nologo
已成功生成。
    0 个警告
    0 个错误
```

## 2. 一键构建 + 测试

```
> powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1
...
== 047 test summary ==
passed=39
failed=0
total=39
RESULT=PASS
BUILD_AND_TEST_OK manifest=...\build\BUILD_MANIFEST.txt
```

- **变更前:** 31 passed / 0 failed。
- **变更后:** **39 passed / 0 failed**(+8 项新测试)。

### 2.1 新增 8 项测试

| 测试 | 断言 |
|---|---|
| `finalcodol/opcode-table-starts-empty` | opcode 表初始为 0 |
| `finalcodol/unknown-opcode-rejected` | 未知 opcode → `UnknownMessage`,不处理 |
| `finalcodol/register-requires-evidence` | 无证据 id 注册 → `CodecException` |
| `protocol/connectionless-token-table` | `connectResponse` RVA=0x9BFF0C、方向=ServerToClient;`getchallenge`=ClientToServer |
| `protocol/connectionless-decode-connectResponse` | `connectResponse 1234567890` 解出 token+arg |
| `protocol/connectionless-unknown-token` | 垃圾 token → `UnknownToken` |
| `analysis/module-readiness-single-ready` | 恰好 1 个模块 Ready;netfield 保持 Blocked |
| `analysis/static-fact-va-from-rva` | VA = RVA + ImageBase |

## 3. 构建产物哈希

| 产物 | SHA-256 |
|---|---|
| `src\...\bin\Release\net8.0\Codol.BattleServer.dll` | `1CE9D9977A55F53E1D579868425E2BC927D27359E08663401E8938952F58A315` |
| `tests\...\bin\Release\net8.0\Codol.BattleServer.Tests.dll` | `EB55389E598AF5CDD3C37FB224150B37D733F0A0830D30983FC91DB901F67BD0` |

> 与 `build\BUILD_MANIFEST.txt` 一致;.NET 确定性编译。

## 4. 历史不可变性

```
> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-history-immutability.ps1
checked=547 failures=0
HISTORY_IMMUTABLE_OK
```

- 覆盖 040–046 与原始 v0.1 的 547 个文件,0 失败。
- 原始客户端(S-EXE/S-DLL/S-IMG)本轮**只读**;其 SHA-256 与 046 一致(见 `01` §3)。

## 5. 测试命令复现

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047
powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-history-immutability.ps1
```

## 6. 已知未通过项

无。最终 CODOL **in-match 线格式**测试**不存在**,因为格式未证 —— 这不是失败,
是刻意的 BLOCKED(见 `06`)。
