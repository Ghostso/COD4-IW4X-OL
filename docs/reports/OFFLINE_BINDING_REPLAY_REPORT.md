# OFFLINE_BINDING_REPLAY_REPORT — P1-4 离线绑定重放工具

**日期**：2026-10-10
**工作基准**：**F = `F:\桌面\ol\ol-mod-olfinal`**（唯一活动基准；D 只读冻结）
**本轮性质**：新增 1 个离线工具 + 1 个测试模块（均为 F 中**新未跟踪文件**）。**未启动客户端、未注入、未读进程内存、未部署、未修改任何既有源文件、未提交 Git。**
**工具版本**：`ReplayEngineBindings` v1.0.0 · schemaVersion 1

---

## 0. 结论速览

| 项 | 结果 |
| --- | --- |
| 是否已有等价工具 | **否**。仓库有**等价的静态分析产物**（`prefix_recalibration.json`），但**生成它的工具不在树内**；`inspect-artifact.ps1` 只做 PE 元数据，不做规则重放 |
| 新工具 | `tools/reverse/ReplayEngineBindings.py`（42,867 B，stdlib-only） |
| 新测试 | `tools/reverse/ReplayEngineBindingsTests.py`（22,401 B）· **68 断言 / 16 用例 / 0 失败 / exit 0** |
| 对候选 A（`36997674…`） | **INSUFFICIENT_EVIDENCE**（81 条规则全部无法由静态文件判定） |
| 对候选 B（`7B31168D…`） | **INSUFFICIENT_EVIDENCE**（同上） |
| 负对照（自有插件 DLL，未加壳） | **FAIL**（53 FAIL / 26 AMBIGUOUS / 2 INSUFFICIENT）⇒ 工具**不是**"全部通过" |
| 历史产物复现 | `comFrame.expected`、`comFrame.actual`、`rva0x8371A.expected`、`candidates[A].match` **全部一致**；`pairedPrefixRva` 标记为**不可比** |
| 交叉验证 | 与既有 `inspect-artifact.ps1` 的 `machine` / `imageBase` / `sizeOfImage` / 段名**逐项一致** |
| 最终状态 | `OFFLINE_BINDING_REPLAY: VERIFIED AT STATIC SCOPE ONLY` |

---

## 1. 先核实已有实现（任务 §一.1）

在 F 内只读检索，结果如下。**未假定历史报告提到的工具存在。**

| 候选等价物 | 是否存在 | 能力 | 是否足以替代本工具 |
| --- | --- | --- | --- |
| `verify-bindings.py` | ❌ **不在树内** | 仅被 `EngineBindings.cpp:3158` 与 git `55fcdbf` 的提交信息引用 | — |
| `Tools/olfinal/import-signature.py` | ❌ **不在树内** | 被 `CodolClientPatches.cpp:41` 引用 | — |
| `Tools/olfinal/check-auth3-patches.py` | ❌ **不在树内** | 被 `Auth3ClientPatches.cpp:110` 引用 | — |
| `tools/` 下的 PE 解析库 | ❌ 0 命中（`e_lfanew`/`IMAGE_NT`/`SizeOfImage` 在 `tools/` 内 0 命中） | — | — |
| `.agents/audits/2026-10-09/inspect-artifact.ps1` | ✅ 存在（6,952 B） | 只读 PE/FF **元数据**：machine、imageBase、sizeOfImage、段表、FileVersion | ❌ **不做任何规则/签名匹配** |
| `codol-preflight.ps1` | ✅ 存在（20,525 B） | 就绪度令牌（`CLIENT_HASH_VERIFIED` 等），客户端哈希由**参数**传入 | ❌ 不做绑定规则重放 |
| `.agents/audits/2026-10-09/prefix_recalibration.json` | ✅ 存在（5,289 B） | **等价的静态分析产物**：79 条配对规则对两个候选的 match/mismatch、`comFrame` 与 `rva0x8371A` 的 expected/actual | ❌ **是产物不是工具**；生成器不在树内（`prefix_recalibration`、`recordedGuards`、`pairedPrefixRva` 在 F 内 **0 命中**） |

**结论**：
1. **不存在可复用的绑定重放工具**，因此新增文件是必要的，不是重复开发。
2. 存在一份**历史黄金产物**（`prefix_recalibration.json`），因此新工具必须能以它为**对照基准**——这比从零自证强得多。
3. PE 元数据部分**已有** `inspect-artifact.ps1`。新工具不与其竞争，而是**交叉验证**（§3.3），并把新增价值集中在**规则重放与状态裁定**上。

---

## 2. 工具设计

### 2.1 输入（全部显式指定）

| 参数 | 说明 |
| --- | --- |
| `--rules-source <file>`（可重复） | 声明 RVA 常量与/或守卫字节数组的源文件。**规则从源码解析，不手工转录** |
| `--engine-bindings-hpp` / `--engine-bindings-cpp` | 上述的便捷写法（EngineBindings 把 RVA 放在 .hpp、数组放在 .cpp） |
| `--rules <json>` | 显式规则文件；每条规则可携带 `sourceObject` / `sourceSha256` / `evidenceLevel` / `applicableObjectClasses` |
| `--pe <file>` | 要重放的静态 PE 文件 |
| `--object-class <unpacked\|packed-retail\|plugin-dll\|unknown>` | 调用方声明的输入对象类别 |
| `--baseline <prefix_recalibration.json>` | 可选：与历史产物对照 |
| `--out` / `--stable` / `--quiet` | 完整报告 / 可复现投影 / 静默 |

### 2.2 规则提取（防漂移）

| 提取项 | 正则/来源 | 说明 |
| --- | --- | --- |
| RVA 常量 | `constexpr std::size_t <Name>Rva = 0x…;` | 同名只取首次出现（声明点） |
| 守卫数组 | `constexpr std::array<std::uint8_t, N> <Name>{ … };` | **声明长度与初始化元素数不一致时整条丢弃**，不猜测 |
| 配对 | 由 RVA 侧驱动：`<Stem>Rva` ↔ `<Stem>Prefix` / `<Stem>` / `<Stem>Original` | 只接受这三种后缀，因此 `…Replacement` / `…Patched` **不可能**被误当作期望原始字节 |
| 未配对项 | 两侧剩余项全部列出 | 不静默丢弃 |

每条规则自动携带**来源对象**：`out.exe (build 1649370)` + `044c396c…257f9`，证据等级 `SOURCE_DERIVED`。该来源记录在工具常量中，并在每条规则结果里重复出现——**规则永远不会被静默应用到另一个对象**。

### 2.3 状态词表（每条规则一个）

| 状态 | 含义 |
| --- | --- |
| `PASS` | 声明前缀位于声明 RVA，且该前缀在映像中**唯一**，且证据充分 |
| `FAIL` | 证据充分但规则在此不成立：`signature_not_found`（0 次）或 `signature_relocated`（唯一一次但**不在**声明 RVA） |
| `AMBIGUOUS` | 前缀在映像中出现 **>1 次**，站点无法唯一识别 |
| `NOT_APPLICABLE` | 规则声明的 `applicableObjectClasses` 不含本对象类别；**不做**锚点检查 |
| `INSUFFICIENT_EVIDENCE` | 输入无法判定该规则：加壳/加密载荷、RVA 未映射、或调用方声明为 `packed-retail` |

**输入级错误**（与规则级状态分离）：`INPUT_MISSING` / `UNSUPPORTED_FORMAT` / `PARSE_FAILED` → 报告 `errors[]` + `verdict=ERROR` + 退出码 2。**错误永远不会被伪装成 FAIL。**

### 2.4 加壳/加密判定（保守，只看代码）

| 信号 | 强度 |
| --- | --- |
| 段名命中 `.tp3`/`.tvm0`/`.vmp*`/`UPX*` 等 | **强** |
| **可执行**段熵 ≥ 7.0 | **强** |
| **可执行**段 `VirtualSize > SizeOfRawData × 8` 且 `> 1 MB` | 中 |
| 非可执行段 `VirtualSize ≫ SizeOfRawData` | **仅记为 informational**（普通 BSS 尾巴，不是加壳信号） |

> 最后一行是本轮实测修出来的：我们的自有插件 DLL（LTO 优化）`.data` 为 1.8 MB 虚拟 / 162 KB 原始，早期版本把它误判为加壳。修正后该 DLL 正确地被判为**未加壳**，从而得到 `FAIL` 而不是 `INSUFFICIENT_EVIDENCE`——这正是负对照能成立的前提。

**信任规则**：`staticBytesTrustworthy = NOT (启发式加壳 OR 调用方声明 packed-retail)`。
- 任一为真 ⇒ 每条规则**最多**只能得到 `INSUFFICIENT_EVIDENCE`；锚点比较结果**仍被记录**，但明确标注为"observation only"。
- 二者冲突时写入 `classificationConflict`。

### 2.5 输出（可审计报告）

顶层字段：`schemaVersion` / `kind` / `tool{name,version}` / `generatedAt` / **`scope`** / `inputs` / `rules` / `object` / `results[]` / `summary` / `errors[]` / `verdict` / `baselineComparison`。

`scope` 是**硬编码**的自我限制，出现在每一份报告里：

```json
"scope": {
  "staticFileOnly": true,
  "runtimeImageVerified": false,
  "disclaimer": "Every rule result describes a STATIC FILE. EngineBindings::bind() checks the HOST PROCESS image (GetModuleHandleW(nullptr)). A PASS here is never evidence of runtime-image compatibility."
}
```

每条规则结果含：`id` / `rva` / `prefixHex` / `prefixBytes` / `prefixKind` / `sourceObject` / `sourceSha256` / `evidenceLevel` / `applicableObjectClasses` / `status` / `reason` / `anchorMatches` / `actualHex` / `occurrences` / `occurrenceRvas`。

`summary.anchorObservations` 单独统计 `anchorMatched` / `anchorMismatched` / `anchorUnavailable` / `uniqueMatches` / `zeroMatches` / `multipleMatches` / `anchorMatchedKinds`。

`verdict.compatibility` 取值域**不含裸 `PASS`**：`STATIC_SCOPE_ONLY_PASS` / `FAIL` / `AMBIGUOUS` / `INSUFFICIENT_EVIDENCE` / `NOT_APPLICABLE` / `ERROR`，且**始终**附带 `runtimeImageVerified: false`。

### 2.6 `prefixKind` 启发式（让"唯一匹配"能自我解释）

| 值 | 判据 |
| --- | --- |
| `code_prologue` | 前 3 字节 `55 8B EC`，或前 2 字节 `8B FF`，或首字节 `E8/E9/EB` |
| `float_vector` | 长度为 4 的倍数，且每组小端 float 都是有限值且落在 `0` 或 `(1e-6, 1e6)` |
| `other` | 以上皆非 |

---

## 3. 运行结果

### 3.1 候选 A（实际运行目标，加壳零售客户端）

```text
object      : E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe
  sha256    : 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
  bytes     : 7841344
  machine   : 0x014C (x86)      timeDateStamp: 0x6096930A      sizeOfImage: 0x0E659000
  packed    : True (static bytes trustworthy=False)
    - packer section names present: .tp3, .tvm0
    - executable section entropy >= 7.0: .tp3@0x1000 entropy=7.140, .tp3@0xE5D7000 entropy=7.337
    - executable VirtualSize far above SizeOfRawData: .tp3@0xA16000 vsize/rawSize=573.9
statuses    : PASS=0  FAIL=0  AMBIGUOUS=0  NOT_APPLICABLE=0  INSUFFICIENT_EVIDENCE=81
anchor      : matched=1 mismatched=80 unavailable=0
occurrences : unique=18 zero=47 multiple=16
matched kinds: float_vector
verdict     : INSUFFICIENT_EVIDENCE
```

**唯一命中的那条是 `ByteDirections`（RVA `0xA51C70`，12 字节 `4F9606BF0000000044C4593F`），工具独立把它分类为 `float_vector`**——与历史产物"唯一匹配项是 DATA 常量而非代码"的判断**独立一致**。

### 3.2 候选 B（`EXPERIMENT_017_BOOT_SKIP`）

```text
  sha256    : 7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342
  packed    : True   statuses: INSUFFICIENT_EVIDENCE=81
  anchor    : matched=1 mismatched=80 unavailable=0   matched kinds: float_vector
  verdict   : INSUFFICIENT_EVIDENCE
```

与候选 A 完全同型，与历史产物一致。

### 3.3 负对照：自有插件 DLL（未加壳、另一个对象）

```text
object      : F:\...\build\bin\release\CodolGameServer.Localnet32
  sha256    : 21D1481735828B48F3C36C09B84581756A1BC6051F57DE198E75B1556A54B9CA
  machine   : 0x014C (x86)   timeDateStamp: 0x6AC8D885   sizeOfImage: 0x007E0000
  packed    : False (static bytes trustworthy=True)
statuses    : PASS=0  FAIL=53  AMBIGUOUS=26  NOT_APPLICABLE=0  INSUFFICIENT_EVIDENCE=2
anchor      : matched=0 mismatched=79 unavailable=2
verdict     : FAIL
```

**这个结果证明工具不是"什么都通过"**：面对一个字节可读、但属于**另一个对象**的未加壳映像，81 条宿主规则里 79 条锚点不匹配、2 条 RVA 根本不存在于该映像 ⇒ `FAIL`。工具的判别力由此得到实证。

### 3.4 与既有 `inspect-artifact.ps1` 的交叉验证

对同一个候选 A 分别运行两个工具：

| 字段 | `inspect-artifact.ps1` | `ReplayEngineBindings.py` | 一致 |
| --- | --- | --- | --- |
| `sha256` | `36997674…2B537` | 同 | ✅ |
| `bytes` | 7,841,344 | 7,841,344 | ✅ |
| `machine` | `0x014C` | `0x014C` | ✅ |
| `imageBase` | `0x00400000` | `0x00400000` | ✅ |
| `sizeOfImage` | `0x0E659000` | `0x0E659000` | ✅ |
| 段名 | `.tp3,.tp3,.tp3,.tp3,.tp3,.tvm0,.tp3` | 同 | ✅ |

⇒ PE 元数据层**没有重复实现分歧**；新工具的新增价值是规则重放与状态裁定。

---

## 4. 与历史黄金产物的对照（`prefix_recalibration.json`）

| 对照项 | 历史值 | 本轮重放值 | 一致 | 备注 |
| --- | --- | --- | --- | --- |
| `keyFindings.comFrame.expected` | `558BEC5657` | `558BEC5657` | ✅ | 规则 `ComFrame` @ `0xFEA20` |
| `keyFindings.comFrame.actual` | `03C1E00650` | `03C1E00650` | ✅ | 候选 A 磁盘字节 |
| `keyFindings.rva0x8371A.expected` | `837C2408010F94C0` | `837C2408010F94C0` | ✅ | 需把 `ClientProcessPatches.cpp` 纳入规则源 |
| `candidates[A].match` | 1 | 1 | ✅ | 锚点命中数 |
| `candidates[A].mismatch` | 78 | **80** | ❌ | 差 2 |
| `recordedGuards.pairedPrefixRva` | 79 | **81** | ❌ | **标记为 `comparable: false`** |
| `onlyMatchIsDataNotCode` | `true` | `anchorMatchedKinds=["float_vector"]` | ✅ | 独立复现 |

**差异的诚实处置**：历史产物的生成器**不在树内**，其**作用域与提取正则未被记录**，且当前源码相对该产物生成时已变化。因此 `pairedPrefixRva`（79 vs 81）在报告中**显式标注为不可比**，两个数字**并列显示**，**不主张**一致也**不主张**不一致；`mismatch` 的 2 之差与配对数 2 之差同源。

**这一点本身就是设计目标**：工具宁可承认"这两个数不是同一个量"，也不把 79/81 强行对齐。

---

## 5. 限制与明确不主张

| 限制 | 说明 |
| --- | --- |
| **不是运行时验证** | `EngineBindings::bind()` 读的是宿主进程自身模块（`GetModuleHandleW(nullptr)`）；本工具读**文件**。二者是不同的对象 |
| **加壳输入无法判定** | 加壳文件不含运行时代码字节。工具给出 `INSUFFICIENT_EVIDENCE`，**绝不**通过修改签名来制造 PASS |
| **`NOT_APPLICABLE` 不是"安全"** | 它只表示"该规则不覆盖此对象类别"，**不**表示该对象安全或兼容 |
| **`float_vector` 命中不构成兼容性证据** | 数据常量可在加壳后原样保留，所以它命中是**预期**的，与代码正确性无关 |
| **未做签名搜索** | 工具**只**在声明 RVA 处比对 + 统计整映像出现次数。它**不**寻找"签名搬到别处"的可用替代站点——那是另一类工具 |
| **历史配对数不可复现** | 见 §4；已标注为不可比 |
| **`prefixKind` 是启发式** | 仅用于解释，不参与状态判定 |

**明确不主张**：
- ❌ 不主张候选 A/B 与 `out.exe` 是同一构建；
- ❌ 不主张候选 A/B 的运行时映像满足门禁；
- ❌ 不主张历史 `prefix_recalibration.json` 的配对数正确或错误；
- ❌ 不主张任何 RVA/前缀/常量需要修改。

---

## 6. 文件与哈希

### 6.1 本轮在 F 中新增（**唯一**对 F 的写入）

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `tools/reverse/ReplayEngineBindings.py` | 42,867 | `8DFA9FE2FC0EECD6369614841474600D00D831E0B9F37399FBD482CD0B896CEE` |
| `tools/reverse/ReplayEngineBindingsTests.py` | 22,401 | `A12825DA2A711010B5676AC8CE338B1E7E14BA97359217B9846A795BEE517735` |

F 的 `git status` 由 9 条变为 **11 条**（9 条原有 + 2 条新增未跟踪）。**HEAD 未变**（`2a75bdd`），**无提交、无推送**。

### 6.2 只读输入（未修改）

| 文件 | SHA-256 |
| --- | --- |
| `src/game_server/EngineBindings.hpp` | `9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E` |
| `src/game_server/EngineBindings.cpp` | `E624A8A1AFF2BB59F57CCD1D37BF1FD609D0573FFD505DB5BD6CD32C3E07465B` |
| `src/game_server/ClientProcessPatches.cpp` | `E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885` |
| `.agents/audits/2026-10-09/prefix_recalibration.json` | `A6EE4AA0EA1E3FC8CF381B8B622D039BAF4AF15DD551A76D205AFD7DCD2535ED` |
| `.agents/audits/2026-10-09/inspect-artifact.ps1` | `57DFF0D5C706293677608CAC2D4D238C53010750A2D4F4610C6D289A733A3394` |

### 6.3 制品（只读）

| 制品 | 字节 | SHA-256 |
| --- | --- | --- |
| 候选 A | 7,841,344 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| 候选 B | 7,841,344 | `7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342` |
| 负对照 `CodolGameServer.Localnet32` | 6,559,232 | `21D1481735828B48F3C36C09B84581756A1BC6051F57DE198E75B1556A54B9CA` |

### 6.4 证据与日志（`_p14_evidence\`）

| 文件 | 说明 |
| --- | --- |
| [SHA256_MANIFEST.txt](_p14_evidence/SHA256_MANIFEST.txt) | **完整哈希清单**（工作树、规则源、T-1 源、制品、证据、交付物） |
| [replay_candidate_A.json](_p14_evidence/replay_candidate_A.json) · [.stable.json](_p14_evidence/replay_candidate_A.stable.json) · [.log](_p14_evidence/replay_candidate_A.log) | 候选 A 的完整报告 / 可复现投影 / 控制台日志 |
| [replay_candidate_B.json](_p14_evidence/replay_candidate_B.json) · [.stable.json](_p14_evidence/replay_candidate_B.stable.json) · [.log](_p14_evidence/replay_candidate_B.log) | 候选 B |
| [replay_plugin_negative_control.json](_p14_evidence/replay_plugin_negative_control.json) · [.stable.json](_p14_evidence/replay_plugin_negative_control.stable.json) · [.log](_p14_evidence/replay_plugin_negative_control.log) | 负对照 |
| [replay_tool_tests.log](_p14_evidence/replay_tool_tests.log) | 测试模块输出（68 断言 / 0 失败） |
| [inspect_candidate_A.json](_p14_evidence/inspect_candidate_A.json) · [.log](_p14_evidence/inspect_candidate_A.log) | 既有 `inspect-artifact.ps1` 的独立输出（交叉验证） |

### 6.5 复现命令

```powershell
# 规则重放（候选 A）
cd F:\桌面\ol\ol-mod-olfinal
python tools\reverse\ReplayEngineBindings.py `
  --rules-source src\game_server\EngineBindings.hpp `
  --rules-source src\game_server\EngineBindings.cpp `
  --rules-source src\game_server\ClientProcessPatches.cpp `
  --pe E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe `
  --object-class packed-retail `
  --baseline .agents\audits\2026-10-09\prefix_recalibration.json `
  --out report.json --stable stable.json

# 测试
cd F:\桌面\ol\ol-mod-olfinal\tools\reverse
python ReplayEngineBindingsTests.py
```

---

## 7. 最终状态

```text
OFFLINE_BINDING_REPLAY: VERIFIED AT STATIC SCOPE ONLY

T1_LIFECYCLE: FIXES PROPOSED, PENDING IMPLEMENTATION APPROVAL

FULL_ENCRYPTED_CLIENT_RUNTIME: UNVERIFIED

CLIENT LAUNCH / INJECTION: NOT EXECUTED
```

**离线 PASS ≠ 运行时兼容性 PASS。** 本轮对两个真实候选得到的结论是 `INSUFFICIENT_EVIDENCE`——**这正是正确的结论**，因为加壳静态文件根本不包含运行时代码字节。真正未闭合的门禁仍然是 **O-4 运行时映像证据**（见 [FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md](FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md) §7 E-2/E-3）。

---

## 8. 关联交付

- [OFFLINE_BINDING_REPLAY_TESTS.md](OFFLINE_BINDING_REPLAY_TESTS.md) — 测试覆盖矩阵与运行结果
- [T1_MINIMAL_FIX_PROPOSAL.md](T1_MINIMAL_FIX_PROPOSAL.md) — T-1 四项缺陷的最小修复方案
- [FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md](FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md) · [NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md)
- [_p14_evidence\SHA256_MANIFEST.txt](_p14_evidence/SHA256_MANIFEST.txt)
