# OFFLINE_BINDING_REPLAY_TESTS — 测试覆盖、运行结果与复现

**日期**：2026-10-10
**被测对象**：`F:\桌面\ol\ol-mod-olfinal\tools\reverse\ReplayEngineBindings.py`
**测试模块**：`F:\桌面\ol\ol-mod-olfinal\tools\reverse\ReplayEngineBindingsTests.py`
**结果**：**68 断言 / 16 用例 / 0 失败 / exit 0**
**日志**：[_p14_evidence\replay_tool_tests.log](_p14_evidence/replay_tool_tests.log)

---

## 0. 复现

```powershell
cd F:\桌面\ol\ol-mod-olfinal\tools\reverse
python ReplayEngineBindingsTests.py
# checks=68 failures=0   exit=0
```

- **依赖**：仅 Python 3 标准库（`argparse` `hashlib` `json` `math` `re` `struct` `sys` `tempfile` `pathlib` `datetime`）。**未新增任何依赖。**
- **实测环境**：Python 3.11.9。
- **遵循仓库既有 Python 测试约定**：与 `tools/reverse/OlfinalFastfileTests.py` 同型——一个 `<Tool>Tests.py` 模块，`main()` 内断言并打印 `checks=/failures=`，可直接运行。
- **副作用**：全部合成 PE 与临时文件写入 `tempfile.TemporaryDirectory()`，退出即删除；**不触碰仓库、不触碰真实客户端、不启动任何进程。**

---

## 1. 任务要求的九类覆盖 → 用例映射

任务 §一.4 要求的九类覆盖，逐项对应到具体用例：

| # | 要求 | 对应用例 | 关键断言 |
| --- | --- | --- | --- |
| 1 | 正常 PE 输入 | `[1]` | 合成 PE32 解析成功；`machine`/`sizeOfImage` 读出；规则 `PASS` |
| 2 | 错误格式输入 | `[8]` | 非 PE 文件 ⇒ `UNSUPPORTED_FORMAT`（或 `PARSE_FAILED`），exit 2，**`results` 为空数组（不编造规则结果）** |
| 3 | 输入缺失 | `[9]`、`[16]` | PE 不存在 ⇒ `INPUT_MISSING`，exit 2，`inputs.pe.sha256 == null`（不编造哈希）；规则文件缺失、规则源缺失同样 exit 2 |
| 4 | 零匹配 | `[2]` | `occurrences == 0` ⇒ `FAIL`，reason 含 `not found` |
| 5 | 唯一匹配 | `[1]`、`[11]` | `occurrences == 1` 且位于声明 RVA ⇒ `PASS` |
| 6 | 多重匹配 | `[3]` | `occurrences == 2` ⇒ `AMBIGUOUS`，两个偏移都被记录 |
| 7 | 不同来源对象的规则混用 | `[7]`、`[12]` | 规则声明 `applicableObjectClasses: ["unpacked"]` 而对象类别为 `packed-retail` ⇒ `NOT_APPLICABLE`，且 `anchorMatches == null`（**不做**锚点检查）；另一条适用规则仍被评估。每条结果都带 `sourceObject` |
| 8 | 加密/压缩载荷导致无法判断 | `[5]`、`[6]`、`[11]` | 加壳（`.tp3`/`.tvm0`）⇒ 每条规则 `INSUFFICIENT_EVIDENCE`，但**锚点观察仍被记录**；**即使所有锚点都命中，verdict 也绝不为 `STATIC_SCOPE_ONLY_PASS`**；普通 BSS 尾巴**不得**被误判为加壳 |
| 9 | 报告可重复生成且具有明确输入哈希 | `[10]` | 两次运行的 `--stable` 投影**逐字节相同**；投影含 PE 的 SHA-256 与规则源 SHA-256；投影**不含** `generatedAt`（完整报告含） |

另外补充的三类（任务未逐条要求，但为验收标准所必需）：

| # | 用例 | 覆盖的验收点 |
| --- | --- | --- |
| 10 | `[4]` 唯一匹配但**不在**声明 RVA | `FAIL(signature_relocated)` —— 与"零匹配"是可区分的两种失败 |
| 11 | `[6]` 加壳 + 全部锚点命中 | **"离线 PASS 不被解释为运行时兼容性 PASS"** 的机械化证明 |
| 12 | `[12]` 调用方声明 `packed-retail` 但启发式未检出加壳 | 声明被尊重（`staticBytesTrustworthy=false`）⇒ 规则**永不** `PASS`；冲突被写入 `classificationConflict` |
| 13 | `[14]` 真实源码解析 | 规则**从源码提取而非手工转录**：`ComFrame` ↔ `0xFEA20`/`558BEC5657`；`ByteDirections` ↔ `0xA51C70`/`4F9606BF0000000044C4593F`；`UnsignedFastfileVerification` ↔ `0x8371A`/`837C2408010F94C0`；`…Replacement` 必须留在 `unpaired` |
| 14 | `[13]` `prefixKind` | `55 8B EC…` ⇒ `code_prologue`；`ByteDirections` 向量 ⇒ `float_vector`；单字节 `0x90` ⇒ `other` |
| 15 | `[15]` 与历史产物对照 | 可比的项报告 `agrees`；**不可比的项**（配对数）显式 `comparable: false` |
| 16 | `[11]` 加壳启发式的假阳性回归 | 普通 `.data` 尾巴（vsize/rawSize ≫ 8）**不得**被判为加壳 |

---

## 2. 逐用例结果

```text
[1] a unique prefix at the declared RVA is PASS
  ok   exit code 0
  ok   status PASS
  ok   anchor matched
  ok   occurrences == 1
  ok   verdict is static-scope-only, not a compatibility PASS
  ok   runtime image explicitly not verified
[2] an absent prefix is FAIL(signature_not_found)
  ok   exit code 1
  ok   status FAIL
  ok   occurrences == 0
  ok   reason names the zero match
[3] a repeated prefix is AMBIGUOUS
  ok   exit code 1
  ok   status AMBIGUOUS
  ok   occurrences > 1
  ok   both offsets recorded
[4] a unique prefix at the WRONG RVA is FAIL(signature_relocated)
  ok   exit code 1
  ok   status FAIL
  ok   occurrences == 1
  ok   reason distinguishes relocation from absence
[5] a packed image yields INSUFFICIENT_EVIDENCE with the anchor kept
  ok   exit code 1
  ok   packed detected
  ok   status INSUFFICIENT_EVIDENCE
  ok   anchor observation still recorded
  ok   verdict is INSUFFICIENT_EVIDENCE
[6] even an all-anchors-match packed image is not a static PASS
  ok   both anchors matched
  ok   no PASS status is emitted
  ok   verdict is not STATIC_SCOPE_ONLY_PASS
[7] rules from another source object are NOT_APPLICABLE, not FAIL
  ok   out.exe-only rule is NOT_APPLICABLE
  ok   no anchor check is performed for it
  ok   the applicable rule is evaluated but capped by the declaration
  ok   the declaration is recorded
  ok   source object is recorded per rule
[8] a non-PE input is UNSUPPORTED_FORMAT, not FAIL
  ok   exit code 2
  ok   one error recorded
  ok   error code is UNSUPPORTED_FORMAT
  ok   verdict is ERROR
  ok   no rule result is fabricated
[9] a missing PE is INPUT_MISSING, not FAIL
  ok   exit code 2
  ok   error code is INPUT_MISSING
  ok   input hash is null, not a fabricated value
  ok   a missing rules file also exits 2
[10] the stable projection is byte-reproducible and carries input hashes
  ok   two runs produce identical bytes
  ok   stable projection carries the PE SHA-256
  ok   stable projection carries the rules SHA-256
  ok   stable projection has no timestamp
  ok   full report does have a generatedAt
[11] an ordinary writable .data tail is NOT classified as packing
  ok   not flagged as packed
  ok   the tail is reported as informational
  ok   static bytes are trusted
  ok   the rule is therefore evaluated to PASS
  ok   exit code 0
[12] a caller-declared packed-retail object can never PASS
  ok   no packer signal was detected
  ok   the declaration is still honoured
  ok   the conflict is recorded
  ok   status is INSUFFICIENT_EVIDENCE, not PASS
[13] prefix kind separates code prologues from data constants
  ok   55 8B EC... is a code prologue
  ok   the ByteDirections vector is a float vector
  ok   a lone 0x90 is neither
[14] the real source yields the documented guard set
  ok   at least 75 rules are paired
  ok   ComFrame pairs to 0xFEA20 / 55 8B EC 56 57
  ok   ByteDirections pairs to 0xA51C70 / the float vector
  ok   UnsignedFastfileVerification pairs to 0x8371A / 83 7C 24 08 01 0F 94 C0
  ok   every rule records its source object
  ok   every rule records an evidence level
  ok   the Replacement array is NOT mistaken for the expected bytes
[15] the baseline comparison reports agreement and refuses to equate
  ok   comparison ran
  ok   comFrame.expected agrees
  ok   the paired-count row is marked not comparable
[16] a missing rule source is INPUT_MISSING
  ok   exit code 2
checks=68 failures=0
```

---

## 3. 开发过程中由测试发现并修复的两个真实缺陷

测试不是走过场——它在本轮**实际抓出**了两个缺陷。两者都已修复，并各自留下回归用例。

### 3.1 加壳启发式的假阳性（由 `[11]` 抓出）

**症状**：负对照（自有插件 DLL `CodolGameServer.Localnet32`）被判为 `packedOrEncrypted = true`，原因是它的 `.data` 段 `VirtualSize 1,851,064` / `SizeOfRawData 162,816` = **11.4 倍**，触发了"VirtualSize 远大于 SizeOfRawData"信号。

**为什么是错的**：那是普通的 **BSS 式尾巴**（可写、不可执行段的未初始化部分），在 LTO 优化的 DLL 上完全正常，**不是**加壳证据。

**修复**：
- 段判定加入 `Characteristics`：只有**可执行**段的熵/尺寸异常才算加壳信号；
- 非可执行段的 `vsize/rawSize` 异常降级为 `packingInformational`（记录但不参与判定）。

**修复后**：插件 DLL ⇒ `packed=False` ⇒ 规则被真正评估 ⇒ **`FAIL`（53 FAIL / 26 AMBIGUOUS / 2 INSUFFICIENT）**。负对照由"无法判定"变成"明确失败"，判别力才真正建立。

**回归用例**：`[11]`（合成 `.text` + 大 `.data` 尾巴，断言 `packedOrEncrypted == false`、`staticBytesTrustworthy == true`、规则 `PASS`、exit 0）。

### 3.2 测试用 PE 构造器的原始指针错误（由 `[11]` 的 `AMBIGUOUS` 抓出）

**症状**：`[11]` 期望 `PASS`，实际得到 `AMBIGUOUS`（前缀出现 2 次）。诊断显示**两个段共享同一个 `PointerToRawData`**（都是 1024）。

**根因**：构造器把 `raw_cursor = len(blob)` 写在了**追加本段数据之前**，于是第二段沿用了第一段的原始指针，加载器把同一份字节映射到了两个虚拟地址。

**修复**：先按 FileAlignment 对齐、再取 `raw_ptr = len(blob)`、然后写段头、最后追加数据。

**为什么值得记录**：这个 bug 会让**测试本身**产生假象（一个"应该 PASS"的用例变成 AMBIGUOUS，或反之掩盖真实的多次匹配）。测试基础设施的正确性与被测工具同等重要。

### 3.3 另两处由测试抓出的**预期写错**（工具行为正确）

| 用例 | 原期望 | 实际 | 裁定 |
| --- | --- | --- | --- |
| `[7]` | 适用规则应为 `FAIL` | `INSUFFICIENT_EVIDENCE` | **工具正确**：对象被声明为 `packed-retail` ⇒ `staticBytesTrustworthy=false` ⇒ 任何规则都不能 `PASS`。**修正测试期望** |
| `[11]` 段尺寸 | `.data` vsize 512 KB | 未触发 1 MB 下限 | 修正测试数据为 2 MB |

---

## 4. 覆盖边界（测试**未**覆盖的内容）

| 未覆盖 | 原因 | 影响 |
| --- | --- | --- |
| 真实加壳客户端的**运行时**行为 | 需启动客户端（本轮禁止） | 这正是 `INSUFFICIENT_EVIDENCE` 的来源；不是测试缺陷 |
| 真实 `out.exe`（`044c396c…`）作为输入 | 本机不存在 | 无法离线演示"未加壳 + 全规则 PASS"。用合成 PE 覆盖了该路径（`[1]`/`[11]`） |
| 大于 512 MB 的映像 | `MAX_IMAGE_BYTES` 上限 | 超过上限会被截断；报告记录 `imageBytesReconstructed` |
| PE32+（x64）映像 | 未构造 x64 合成样本 | 解析器支持 `0x20B`，但无对应用例。**记为已知缺口** |
| 段表损坏 / 重叠段 / `e_lfanew` 指向文件尾 | 仅覆盖了"非 PE"与"过短" | 其余畸形输入走 `PARSE_FAILED` 路径，未逐一构造 |
| 历史配对数 79 的**精确**复现 | 历史生成器不在树内，作用域未知 | 已标注 `comparable: false`，不主张一致 |

---

## 5. 文件哈希

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `tools/reverse/ReplayEngineBindings.py` | 42,867 | `8DFA9FE2FC0EECD6369614841474600D00D831E0B9F37399FBD482CD0B896CEE` |
| `tools/reverse/ReplayEngineBindingsTests.py` | 22,401 | `A12825DA2A711010B5676AC8CE338B1E7E14BA97359217B9846A795BEE517735` |
| `_p14_evidence/replay_tool_tests.log` | 4,025 | `45670962B9F849C1DBF5F17E38139E09C112F6F0495565F14DC094D1E8F48165` |

完整清单见 [_p14_evidence\SHA256_MANIFEST.txt](_p14_evidence/SHA256_MANIFEST.txt)。

---

## 6. 关联交付

- [OFFLINE_BINDING_REPLAY_REPORT.md](OFFLINE_BINDING_REPLAY_REPORT.md) — 工具设计与真实运行结果
- [T1_MINIMAL_FIX_PROPOSAL.md](T1_MINIMAL_FIX_PROPOSAL.md) — T-1 最小修复方案
- [_p14_evidence\replay_tool_tests.log](_p14_evidence/replay_tool_tests.log) · [_p14_evidence\SHA256_MANIFEST.txt](_p14_evidence/SHA256_MANIFEST.txt)
