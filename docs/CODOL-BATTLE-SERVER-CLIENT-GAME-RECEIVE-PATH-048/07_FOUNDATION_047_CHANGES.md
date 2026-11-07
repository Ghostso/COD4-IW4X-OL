# 07 — 047 工程本轮实际代码变更

**工程:** `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047`
**分支:** `048/analysis-adapters`(独立开发分支)

| 项 | 值 |
|---|---|
| 修改前 commit(047 终态) | `a9f03144c841bad4cf1efa90ded54c98255f3057` |
| 修改后 commit(HEAD) | `8f3e331fb01db7f6580a258380c06c3cdf5421f3` |
| 中间 commit | `3d9f588`(主体变更),`8f3e331`(清理 scratch 脚本) |

---

## 1. 文件变更清单

| 变更 | 文件 | 行数 | 证据依据 |
|---|---|---|---|
| A | `src\Codol.BattleServer\Analysis\StaticEvidenceFact.cs` | +64 | 046/048 地址口径;`01` §2,§6 |
| A | `src\Codol.BattleServer\Analysis\ProtocolModuleReadiness.cs` | +118 | `06` 的八模块判定 |
| A | `src\Codol.BattleServer\Protocol\ConnectionlessCommands.cs` | +80 | `03` §2.5;RVA 0x9BFD04..0x9BFF90 |
| A | `src\Codol.BattleServer\Protocol\ConnectionlessTextDecoder.cs` | +88 | 同上;最小文法 |
| A | `src\Codol.BattleServer\Protocol\OpcodeDispatcher.cs` | +108 | `06` 模块 2;显式拒绝 |
| M | `tests\Codol.BattleServer.Tests\Program.cs` | +76 | 8 项新测试 |
| M | `.gitignore` | +2 | 忽略 scratch 脚本 |
| M | `build\BUILD_MANIFEST.txt` | ±10 | 构建产物哈希(自动) |

**未修改:** 047 既有 13 个库源文件、`baseline\`(只读副本)、040–046 全部产物、原始客户端。

---

## 2. 每个新增文件的依据与边界

### 2.1 `Analysis\StaticEvidenceFact.cs`

- 固化被分析映像的身份常量:ImageBase `0x00400000`、三个样本的 SHA-256 / 大小。
- `StaticEvidenceFact` 记录 `(FactId, Kind, Symbol, Rva, Detail, EvidenceLevel)`,
  并派生 `Va = Rva + ImageBase`。
- 显式标注恢复覆盖不完整:`CoverageIsComplete = false`、`LongRunCoverageRatio ≈ 0.0083`。
- **不含**任何线格式声明。

### 2.2 `Analysis\ProtocolModuleReadiness.cs`

- 把 `06` 的八模块判定做成**编译期数据** + `ModuleReadiness` 枚举。
- `ReadyForFinalImplementation()` 目前**恰好返回一个**模块(握手/连接)。
- 每个 BLOCKED 项带 `MinimumMissingFact` 与证据 id。

### 2.3 `Protocol\ConnectionlessCommands.cs`

- 连接无关命令词表,**每条带 RVA 与方向**;方向来自客户端自身的构造点/比较点。
- `ServerToClient` token 均有实测 `strcmp` xref;`ClientToServer` token 为客户端格式串。

### 2.4 `Protocol\ConnectionlessTextDecoder.cs`

- 实现**证据能支持的最小文法**:`<token>[ <arg>]`,ASCII,上限 32 字节。
- 未知 token → `UnknownToken`(显式拒绝,不回落)。
- 注释中**明确写死**:不得扩展到 in-match opcode / reliable / snapshot。

### 2.5 `Protocol\OpcodeDispatcher.cs`

- `FinalCodolOpcodeDispatcher`:opcode 表**默认为空**;`RegisterProvenOpcode` 要求非空证据 id;
  未注册 opcode → `UnknownMessage`,**不落默认业务处理**。
- `OpcodeEvidenceAudit` 记录「opcode → 证据 id」以供断言。

---

## 3. 证据依据编号(与 048 报告对应)

| 代码 | 证据 |
|---|---|
| `ConnectionlessCommands`/`ConnectionlessTextDecoder` | `03` §2.5,`04` §4,`05` S-4-1..S-4-3 |
| `OpcodeDispatcher` | `06` §3,`05` §3 N-4-4 |
| `ProtocolModuleReadiness` | `06` §1 |
| `StaticEvidenceFact` | `01` §3,§6 |

---

## 4. 严格未做的(防止误读)

1. 没有把 2697 当最终 CODOL 协议。
2. 没有把内部 GameState/Movement 序列化为线上格式。
3. 没有提交任何**猜测的** opcode / ACK 规则 / snapshot 布局。
4. 没有修改客户端或进入大厅基线。
