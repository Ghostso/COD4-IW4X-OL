# CODOL Keyflow 算法结构独立来源审查（001）

> 任务：**CODOL-KEYFLOW-SPEC-PROVENANCE-001**
> 目标：审查 CODOL 2.6.9.7 Keyflow 算法结构描述是否存在**可验证的独立来源**，并判断 G2 `CONDITIONAL PASS` 能否升级。
> 性质：**只读 / 离线**。未修改游戏二进制，未执行运行时握手，未连接真实服务端。
> 运行时互通状态：**NOT-OBSERVED（不变）**。

## 0. 冻结基线复核（执行前，已通过）

| 输入集 | 校验 | 结果 |
|---|---|---|
| `CODOL-KEYFLOW-INDEPENDENT-VERIFY-001`（11 条清单） | 逐文件 SHA-256 | **11/11 通过** |
| `CODOL-DEMONWARE-RUNTIME-VALIDATION-001`（5 条清单） | 逐文件 SHA-256 | **5/5 通过** |
| `CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012`（外层 94 条） | 逐文件 SHA-256 | **94/94 通过** |
| 冻结客户端（打包 / 恢复镜像）、服务端 | SHA-256 复算 | **3/3 一致** |
| 既有参考源码 6 份 | SHA-256 复算 | **6/6 一致** |

**输入一致，未触发停止条件；历史文件未被覆盖**（执行后再次复算，结果相同）。

## 1. 结论摘要

| 项 | 结论 |
|---|---|
| 是否存在与 2.6.9.7 项目实现**无派生关系**的 Keyflow 结构规范来源？ | **否 → `NO-INDEPENDENT-SPEC-FOUND`** |
| 是否存在**同一构建**的独立分析谱系（非 ol-mod 谱系）？ | **否**（已定位另一谱系，但其目标为**不同构建**，见 §3） |
| 是否存在同一 codec **常量/变换式**的独立佐证？ | **参数层：是**（从冻结镜像机器码逐字节提取，见 §4）；**跨构建：SRC-05 存在同一常量块形态但函数体不同、构建不同** → 仍属 `ARTIFACT-ONLY`，非**规范级** |
| 密码原语的公开标准是否可作为整体协议结构的独立规范？ | **否**（原语标准 ≠ 私有协议结构，明确区分，见 §5） |
| G2 能否升级？ | **否，维持 `CONDITIONAL PASS`**（逐项理由见 §7 与 `CODOL_KEYFLOW_G2_REASSESSMENT_001.md`） |

**核心判定**：Keyflow 的**结构描述**（transcript 组成、secret 参数序、expandKey 计数器语义、20/20/16/16 切分、
codec 变换式与方向、帧布局、MAC 覆盖/截断、序列号语义）**全部来自本项目自身的分析产物或其派生材料**；
本工作区内**不存在**可独立复现该私有协议结构的第三方规范。

## 2. S1-01：待验证算法命题的拆分与来源标注

对每项标注四类来源：
`[BIN]` = 原始客户端二进制（直接证据）、`[DOC]` = 现有项目文档、`[IND]` = 独立来源、`[INF]` = 推导性结论。

| claim_id | 命题 | 来源分类 | 判定 |
|---|---|---|---|
| S1-01a | KDF 输入 = `clientHeader[8:28] ‖ serverAck26 ‖ clientAuth[:-8]` | `[DOC]` 强（`01 §5`） + `[INF]`（顺序构成） | **ARTIFACT-ONLY / SOURCE-SHARED** |
| S1-01b | `SHA-1(transcript) -> 20B` | `[BIN]`（名表 `sha1` 命中）+ `[IND]`（FIPS 180-4 **原语**） | 原语 `INDEPENDENTLY-CORROBORATED`；**结构** `SOURCE-SHARED` |
| S1-01c | `secret = HMAC-SHA1(key=SHA1(transcript), data=sessionKey24)` | `[BIN]`（调用点 `0xAAB884`，`push 0x18`）+ `[DOC]` | **SOURCE-SHARED**（参数序无独立第三方规范佐证） |
| S1-01d | 标签 `CLIENTCHAL`(10B→16B)、`BDDATA`(6B→72B) | `[BIN]`（`.rdata` 字面 + 调用序列 `push 0x0A/0x06/0x10/0x48`） | **ARTIFACT-ONLY**（本构建） + `SOURCE-SHARED`（语义标签） |
| S1-01e | `expandKey` = HMAC-SHA1 计数器模式 `prev‖label‖counter`，counter 自 1 | `[BIN]`（`0xAA9CE0` 循环体）+ `[DOC]` | **SOURCE-SHARED**（结构） |
| S1-01f | 72B 输出切分 `20/20/16/16`，`challenge[8:16]` | `[BIN]`（栈地址切片）+ `[DOC]` | **ARTIFACT-ONLY + SOURCE-SHARED** |
| S1-01g | Codec A/B：`out[j]=in[j]^CONST[PERM[j]]`，STORE/LOAD 同掩码 | `[BIN]`（常量表/置换/分支指令）+ `[DOC]` | 参数 **ARTIFACT-ONLY**；变换式 **SOURCE-SHARED** |
| S1-01h | AES 密钥切片 = `data[40:56]`(出站) / `data[56:72]`(入站)，不经 codec | `[BIN]`（`setKey` 调用点 + 栈地址） | **ARTIFACT-ONLY** |
| S1-01i | 帧结构 `u32len‖AB‖85‖seq‖iv16‖ct‖tag8` | `[BIN]`（组帧写入点）+ `[DOC]` | 布局 **ARTIFACT-ONLY**；语义 **SOURCE-SHARED** |
| S1-01j | MAC 覆盖 `frame[:-8]`、取前 8B | `[BIN]`（`HMAC_Update` 长度、tag 取址、8B 比较）+ `[DOC]` | **ARTIFACT-ONLY + SOURCE-SHARED** |
| S1-01k | 接收序列号严格递增（`[+0x5D0]`），无窗口 | `[BIN]`（读/比/写点 + `Bad recv counter`） | **ARTIFACT-ONLY** |
| S1-01l | 异常帧处理（长度上限、短帧、截断） | `[BIN]`（诊断串 4 处复读 + 分支） | **ARTIFACT-ONLY**（存在性）；处置后果 **UNRESOLVED** |
| S1-01m | 加密原语为 AES-128-CBC | `[BIN]`（provider vtable + `setKey` 16B）+ `[IND]`（FIPS 197 **原语**） | 原语 `INDEPENDENTLY-CORROBORATED`；**私有参数化** `SOURCE-SHARED` |

**小结**：`[BIN]`/`[DOC]` 覆盖全部命题；**`[IND]` 仅覆盖密码原语（SHA-1/HMAC/AES）**，**不覆盖任何私有协议结构**。

## 3. S1-02：独立来源检查（含派生来源的识别）

### 3.1 候选来源台账

| source_id | 标识 | 日期 | 作者/组织 | 支持的命题 | 与项目实现的关系 | 独立性判断 | 限制 |
|---|---|---|---|---|---|---|---|
| SRC-01 | `_e1_regression/ol-mod-olfinal`（git: `CODOL-EMU/ol-mod-olfinal`） | 2026-07-31 起（HEAD 2026-10-*） | `dest1yo` / CODOL-EMU | expandKey、标签、20/20/16/16、帧、MAC、序列号、KAT | **本项目自身的重建仓**（提交信息 "Migrate CODOL reconstruction to ol-mod"；首次提交即 `Initial commit`） | **非独立**（项目自有产物） | 为 G2 参考实现的直接来源 |
| SRC-02 | `REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs` | 未标注（随工作区） | 未署名（"三方"） | codec 常量/置换、AES/HMAC 使用、帧构造 | `codol_crypto.py` 自述"逐字段照抄"该文件；与 ol-mod 共用同一 KAT | **派生来源（SOURCE-SHARED）** | 无仓库/提交/作者可追溯；`decrypt` 路径为**内存读取** |
| SRC-03 | `REF_LOBBY_KIT/codol_crypto.py` | 2026-10-03~08 | 本项目 | expandKey、derive_session_keys、帧解析 | 自述依据 SRC-02；KAT 引自 `DemonwareTests.cpp` | **派生来源** | 无独立规范 |
| SRC-04 | `_e1_regression/.../DemonwareTests.cpp`（KAT） | 2026-07-31 起 | CODOL-EMU | KAT 向量、抓包向量 | 与 SRC-01 同仓；被 SRC-03 直接引用 | **同源 KAT** | KAT 非独立 oracle |
| SRC-05 | `CODOLServer/HANDOFF_20260930_REVERSE_MANUAL.md` + `_mainline/*`（运行时内存转储谱系） | 2026-09-25 ~ 10-05 | 本项目（另一工作分支） | **同构建**的 0x85 帧布局、MAC 覆盖、seq、codec 方向 | **独立测量路径**（运行时 dump + 观察器），但目标为**另一构建**（见 3.2） | **构建不匹配**（跨构建，非同一规范来源） | 不适用 2.6.9.7 的 KDF 结构 |
| SRC-06 | `12_CODEC_MVP_001/worktree/.../Aes128.cs` | 2026-10-12 | 本项目 | AES-128 实现 | 自述"依据 REF_LOBBY_KIT ... 自实现" | **派生来源** | 非独立 |
| SRC-07 | 公开密码学标准 FIPS 180-4 / RFC 2104 / FIPS 197 / NIST SP 800-38A | 1993–2001（标准） | NIST / IETF | SHA-1、HMAC-SHA1、AES-128、CBC | 仅覆盖**原语** | **独立（原语层）** | **不含**私有协议结构/参数 |
| SRC-08 | `docs/references/kisak/*`（外部文章归档） | 2025-06-25 / 2026-05-10 | Kisak（外部） | COD 逆向方法论（IDA/PDB） | 与 Keyflow **相关度为零**（无 CLIENTCHAL/BDDATA/expandKey 命中） | 独立但**不支持任何本任务命题** | 不适用 |
| SRC-09 | GitHub 公开检索（`demonware lobby/dw3/codol` 等） | 检索于 2026-10-12 | — | — | — | **未命中**任何可复现该结构的公开仓库 | 检索为有界抽样，非穷尽；不作为否证依据 |
| SRC-10 | `_e1_regression/.../dw3_feasibility.md` 所述 s1x / FourDeltaOne T5M / T5-DemonWare / OpenIW8 / dwd3 | 2026 | 外部（第三方） | 被**间接引用**为 DW 控制面参考 | **本工作区内不存在**（0 命中）；无法就地核验其是否实现同一 20/20/16/16 结构 | **不可用（未获取）** | 仅存在于文字引用，无 artifact |

### 3.2 关键发现：SRC-05 是"独立测量"，但**构建不匹配**

SRC-05 谱系（`CODOLServer`）通过**运行时内存转储**独立重建了 0x85 帧的密钥链，其目标构建与
冻结基线**不是同一构建**（逐字节核实）：

| 项 | 冻结基线（2.6.9.7） | SRC-05 目标构建 |
|---|---|---|
| 打包客户端 SHA-256 | `353754047dbb…`（9,964,656 B） | `36997674b18f…`（7,841,344 B，`COD OL\codoMP_client_shipRetail.exe`） |
| 恢复镜像 / dump | `24b4ef2502d3…`（12,571,648 B） | `17cef6e0a5e7…`（10,899,456 B，`image_best.bin`） |
| PE TimeDateStamp | `1430821084`（2015-05-05） | `1620480778`（2021-05-08） |
| `BDDATA` 字面 VA | `0xC5B13C` | `0xD5A4E0` |
| `CLIENTCHAL` 字面 VA | `0xC5B144` | `0xD5A4E8` |
| 密钥派生函数 | `0xAA9CE0`(expandKey)、`0xAAB310` | `0xBA13D0`、`0xBA0D20`、`0xBA05A0` |
| codec 常量块（A） | 位于 `0xAA8D9C` 附近 | 位于 `0x7A044C` 文件偏移函数内 |

**结构层面的实证差异**（`_data/cross_artifact_check.json`、`_data/codec_body_compare.json`）：

- 冻结基线 codec A 的常量块与置换表在**同址连续内联**；SRC-05 构建中同样形态存在（`0x7A044C`），
  但 codec 函数体的分支/偏移常量不同（codec A 有 130 处字节差异、codec B 有 7 处），说明**不同编译/不同版本**。
- SRC-05 的 KDF 结构（`HMAC_SHA1(key = SHA1(frame), data = transform(conn+0xD9, const24))`）
  与冻结基线的 `expandKey` 计数器结构**不同**——它不是 2.6.9.7 的同一算法描述。
- SRC-05 曾把 `CLIENTCHAL` 误判为协议字段，随后**自行撤回**（"CLIENTCHAL 是错误消息，不是协议字段"），
  这与冻结基线的 `CLIENTCHAL` 用作 `expandKey` 标签的结论**表面冲突、实质不冲突**（不同构建 + 不同语义位点）。

**判定**：SRC-05 是一份**真正独立的测量谱系**，但因**构建不匹配**，**不能**作为 2.6.9.7 Keyflow 结构描述的独立佐证。
它反而强化了一个负面结论：**该私有协议的 KDF 结构随构建变化**。

### 3.3 派生来源识别（明确记录，不误判为独立）

- SRC-01 ↔ SRC-03 ↔ SRC-04：**同一项目**，共用同一 KAT，提交历史显示"迁移而非外部引入"。
- SRC-02 → SRC-03 → SRC-06：**照抄链**（C# → Python → C#/AES）。
- SRC-05 与 SRC-01 之间**无文本交叉引用**（`ol-mod`/`CODOL-EMU`/`Alwaysoffline` 在 SRC-05 手册中 0 命中），
  即 SRC-05 是**独立产生**的——但如前所述，**构建不同**。

**未发现**任何"转载项目参考实现、共享相同 KAT、或引用同一未验证结论"的**外部**候选被误判为独立。

## 4. S1-03：逐项对照（详见 `CODOL_KEYFLOW_SPEC_CROSSWALK_001.csv`）

对照表对 15 条命题分别给出 `INDEPENDENTLY-CORROBORATED / ARTIFACT-ONLY / SOURCE-SHARED / CONFLICTING / UNRESOLVED`。

汇总：

| 判定 | 条目数 | 命题 |
|---|---:|---|
| `INDEPENDENTLY-CORROBORATED`（仅原语层） | 2 | S1-01b SHA-1/HMAC-SHA1 原语；S1-01m AES-128 原语 |
| `ARTIFACT-ONLY` | 7 | S1-01d 标签字面/长度；S1-01f 20/20/16/16 切分；S1-01g codec 参数；S1-01h AES 密钥切片；S1-01i 帧布局；S1-01j MAC 覆盖/截断；S1-01k 序列号 |
| `SOURCE-SHARED` | 4 | S1-01a transcript 组成；S1-01c secret 参数序；S1-01e expandKey 结构；S1-01o KAT 向量来源 |
| `CONFLICTING` | 0（同构建内） | — （唯一"冲突"为跨构建，见 §3.2，不构成同构建冲突） |
| `UNRESOLVED` | 2 | S1-01l 异常帧处置后果（断开 vs 丢弃、幂等性）；S1-01n 公开标准能否充当私有结构规范（按定义不能） |

**重要边界**：§4 中 TC-07…TC-11（codec）与 G2 的一致性，属**参数独立**（来自本构建镜像）
+ **原语独立**；**不是"规范独立"**。C# `DecodeKey` 与 Python 同源，**不构成**独立佐证。

## 5. 公开密码学标准 ≠ 私有协议规范（明确区分）

| 层次 | 是否可用公开标准独立佐证 | 本任务判定 |
|---|---|---|
| 原语算法（SHA-1 / HMAC-SHA1 / AES-128 / CBC） | **是**（FIPS/RFC 标准 + 独立库实现） | 已 `INDEPENDENTLY-CORROBORATED` |
| 原语的**参数化与拼接**（标签字面、长度、counter 起点、20/20/16/16 切分） | **否** | `SOURCE-SHARED` / `ARTIFACT-ONLY` |
| 私有协议**结构**（transcript 组成、secret 参数序、codec 层、帧布局、MAC 覆盖/截断、序列号） | **否** | `SOURCE-SHARED` |
| 私有协议**参数值**（codec 常量/置换、AES 密钥切片） | 否（但可由**本构建 artifact 独立提取**） | `ARTIFACT-ONLY` |

**禁止的推理**：不得因 "SHA-1/HMAC/AES 是公开标准" 而推断"Keyflow 协议结构已获独立规范"。
公开标准只覆盖 §5 第一行。

## 6. S1-04：G2 升级条件审查

| G2 升级所需 | 现状 | 结论 |
|---|---|---|
| 关键协议结构有充分**独立**佐证 | 结构描述全部 `SOURCE-SHARED`；唯一独立规范来源（SRC-05）**构建不匹配** | **未满足** |
| 测试向量输入/预期/来源可追溯 | 已满足（上一任务 TC-01…TC-11 全部 PASS，来源可追溯） | 满足 |
| 仅能确认密码原语及二进制参数 | **正是本任务结论** | → 维持 `CONDITIONAL PASS` |
| 找到真正独立规范 | **未找到（本工作区 + 有界公开检索）** | → 记录 `NO-INDEPENDENT-SPEC-FOUND` |
| 不得虚构来源 / 无限扩大搜索 | 已遵守（检索有界并声明为抽样） | 满足 |

## 7. `NO-INDEPENDENT-SPEC-FOUND` 的实际影响

1. **不影响**已完成的 artifact 级结论：`K_client,consumed = K_reference,derived`（静态 bit-exact）与
   上一任务的 11/11 独立原语+独立参数一致性**仍然成立**。
2. **限制**结论强度：无法排除"项目自身的结构描述整体有误、而所有派生实现一致复现该错误"这一残余可能。
3. **不改变** G2 的 `CONDITIONAL PASS`，也**不提升**其等级。
4. **不改变** `NOT-OBSERVED`：运行时互通仍未验证。

## 8. 交付物

| 文件 | 说明 |
|---|---|
| `CODOL_KEYFLOW_SPEC_PROVENANCE_001.md` | 本文件 |
| `CODOL_KEYFLOW_SPEC_CROSSWALK_001.csv` | 15 条命题逐项对照 |
| `CODOL_KEYFLOW_SOURCE_INDEPENDENCE_001.csv` | 10 条来源台账 + 独立性判定 |
| `CODOL_KEYFLOW_G2_REASSESSMENT_001.md` | G2 升级逐项理由 |
| `SHA256SUMS_SPEC_PROVENANCE_001.txt` | 本轮新增文件完整性清单 |
| `_data/cross_artifact_check.json`、`_data/codec_body_compare.json` | 跨 artifact 核验原始证据 |

## 9. 声明

- 本任务**未**修改游戏二进制，**未**覆盖冻结文件，**未**执行运行时握手，**未**连接真实服务端。
- 本任务**未**虚构任何独立来源；公开检索为**有界抽样**，其 0 命中不作为穷尽否证。
- 运行时互通状态维持 **`NOT-OBSERVED`**。
- 不建议继续在静态来源审查上追加投入（见 `CODOL_KEYFLOW_G2_REASSESSMENT_001.md` §6）。
