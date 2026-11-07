# 修订记录 / REVISION LOG

> 规则（任务书 §1）：**不得删除、覆盖或破坏之前已经生成的报告。** 若新证据推翻旧结论，新增修订记录，保留旧结论、推翻理由、证据来源和裁定日期。
> 本文件只**追加**，不修改历史条目。

---

## REV-001 · 2026-10-12 · “CODOL 使用标准 DTLS” → 降级

- **旧结论：** CODOL 战斗通道使用 DTLS（依据：客户端存在 DTLS/ECDH/secp224 字符串）。
- **推翻理由：** 这些字符串来自客户端**静态链接的 OpenSSL 自带表**（OpenSSL x45、DTLS1_ x27、conf_def x1、X509 x119、ASN1 x138、OCSP x47、EVP_ x38）。**字符串存在不等于调用。**
- **证据来源：** `DEV-BOOKING\PVE-BATTLE-CONTRACT-LINEAGE-021.md` §3；本档案 EV-DTLS-OpenSSL。
- **新结论：** CODOL 有 **bdDTLS 风格的自定义记录层**（NAT/INIT/COOKIE + P-224 + MAC8 + counter），**未证明**使用标准 DTLS。
- **保留：** 旧结论保留于 `10_EVIDENCE_CONFLICTS.md` CONFLICT-03。
- **裁定日期：** 2026-10-12

## REV-002 · 2026-10-12 · “ol-mod 基于 IW4x” → 推翻

- **旧结论：** ol-mod 基于 IW4x，可优先复用 IW4x 实现。
- **推翻理由：** AUDIT.md 明示 ol-mod 是 CODOL 专有链路（Project Nova / Ayria）源码重建，**不基于 IW4x**；IW4/BO1/BO2/Ghosts 仅作 CODREF/CODDIFF 跨版本反编译参照。
- **证据来源：** `CODOL_OLMOD_AUDIT_20261009_094312\AUDIT.md`；本档案 EV-R-OlMod-NoIW4x。
- **新结论：** ol-mod 与 IW4x **血统无关**（`UNRELATED_OR_DIVERGED`）。
- **裁定日期：** 2026-10-12

## REV-003 · 2026-10-12 · “IW4x 提供可复用服务器实现” → 推翻

- **旧结论：** IW4x 有服务器端可作血缘参考。
- **推翻理由：** IW4x 是 DLL-only 客户端 mod，**无专用服务器源码**；`iw4x-rawfiles` 本地为空克隆（0 文件）。
- **证据来源：** EV-R-IW4x-NoServer；DEV-BOOKING-021 §9。
- **新结论：** IW4x 只能作 **OOB/发现/认证信封**参考（LOW–MEDIUM）。
- **裁定日期：** 2026-10-12

## REV-004 · 2026-10-12 · “缺 Battle Server 导致客户端不进入战斗” → 推翻因果

- **旧结论：** 客户端不进入战斗是因为缺少 Battle Server。
- **推翻理由：** 已监听 28960 运行 017/019，客户端 **一个包都没发**（`BATTLE_RX=0`）——说明客户端未走到拨号阶段。缺服务器不是因果。
- **证据来源：** DEV-BOOKING-021 §7；本档案 EV-Battle-RX0。
- **新结论：** 阻塞点在**上游 accepted/booking 门**。下一步应先关 020 的 accepted 门。
- **裁定日期：** 2026-10-12

## REV-005 · 2026-10-12 · “2697 服务端含源码” → 推翻

- **旧结论：** 2697 服务端可能含源码（二进制中存在 `codol_2697_*.c` 源文件名串）。
- **推翻理由：** 旧包源码树 `grep 2697` = **0 命中**；本地无 2697 源码树。源文件名串只是**符号/调试串**。
- **证据来源：** EV-2697-NoSrc；EV-R-OldSrc。
- **新结论：** 2697 只能**反汇编**；旧源码仅作**语义参照**，**不得**当作 2697 实现。
- **裁定日期：** 2026-10-12

## REV-006 · 2026-10-12 · 新增：OLD 与 1113 判为同一源码

- **说明：** 本档案新增的定量结果（**216/217 顶层文件逐字节相同**，唯一差异 `g_sv_main.c`）。
- **影响：** 任何把 OLD 与 1113 当作两个独立协议版本的论述必须撤回。
- **证据来源：** R-01（本档案实测）。
- **裁定日期：** 2026-10-12

## REV-007 · 2026-10-12 · 新增：2697 双通道并存

- **说明：** 2697 二进制**同时保留** legacy writer（`_CODOL_WriteGamestate` RVA 0xA865A、`_CODOL_WriteConfigstrings` RVA 0xA857F）与新增 2697 writer（0xA21B8 / 0xA0468）；`_SV_WriteReliableCommand`（0x8612E）**仅 2697 有**。
- **影响：** 2697 ≠ 替换旧通道，而是**叠加**新通道。
- **证据来源：** R-06（本档案实测）。
- **裁定日期：** 2026-10-12

## REV-008 · 2026-10-12 · 新增：OLD 是 CoD4x 的 fork（字面证据）

- **说明：** `q_shared.h:6` / `qcommon.h:6` 字面 "This file is part of IW4OL source code, a fork of CoD4x."；行级 Jaccard 93–99.7%。
- **影响：** 把“OLD 与 CoD4x 相似”从推断升格为**有字面证据的血统**。
- **证据来源：** R-02/R-03（本档案实测）。
- **裁定日期：** 2026-10-12

---

## 未变更的重要结论（明确保留）

以下结论在本轮**未被推翻**，继续保留：

| 结论 | 状态 |
|---|---|
| 2697 双门控（资源 `+0x78F4` + 注册 `+0x6408`） | 保留（CONFIRMED） |
| 2697 gamestate/configstring/snapshot 字段顺序与终止符 | 保留（VERIFIED） |
| 客户端 `0xA2E50` 字段形状（long+short+payload，上限 0x3FC） | 保留（VERIFIED） |
| 客户端 `0x02` 分派未找到 | 保留（BLOCKED，**不是**“不存在”） |
| 客户端 `0x06` 处理未找到 | 保留（NOT-OBSERVED） |
| COOKIE_ECHO 189 vs 219 | 保留（SOURCE-CONFLICT） |
| codec 187 vs protocol 1 | 保留（SOURCE-CONFLICT） |
| 大厅能进、战斗不能进 | 保留 |
---

## REV-009 · 2026-10-12 · 2697 传输层与 CODOL 家族的关系：推断 → 已证实

- **旧结论：** 2697 与 OLD/1113 的 netchan 同族（依据：符号名 + 源码常量，属 `STRONG_INFERENCE`）。
- **新证据：** 2697 服务端二进制中直接读出 `0x489`(1161)、`0x24500`(1162×128=148736)、`0x1fffffff`、`0x70cc729`(=ceil(2³⁷/1162))。这组常量与 OLD 源码 `codol_wire.h` 的 `CODOL_FRAGMENT_SIZE 1162` / `CODOL_MAX_FRAGMENTS 128` / `CODOL_FRAGMENT_BIT` **精确对应**。
- **证据来源：** `_analysis\OUT_e02` / `RAW_RESULTS_BUNDLE.txt`（本轮只读反汇编 S-2697 `_CODOL_NetchanTransmit` RVA 0x999B6、`_CODOL_NetchanTransmitNextFragment` RVA 0x998D8）。
- **新结论：** `CONFIRMED_BY_EVIDENCE`。OLD→2697 传输层延续获**二进制常量级**证据。
- **保留：** 旧结论保留于 `13` §3。
- **裁定日期：** 2026-10-12

## REV-010 · 2026-10-12 · 恢复镜像 `.data` 完整性假设：修正

- **旧假设（隐含）：** 恢复镜像的 `.data` 与 `.rdata` 指针表可在当前文件内搜索，未命中即接近否定。
- **新证据：** 恢复镜像 `.data` 的 `Misc_VirtualSize = 0x0D05C420`（218 MB），而 `SizeOfRawData = 0x00049600`（300,544 B），**仅 0.138% 在文件内**。同时 `.rdata` 确有 30,895 个 →`.text` 指针与 613 个连续指针表（未被全局破坏）。
- **证据来源：** `_analysis\RAW_RESULTS_BUNDLE.txt` §E-04b / §E-04c（本轮只读 PE 解析）。
- **新结论：** 二者必须**同时**陈述：
  1. 指针表**未**被全局破坏（削弱“指针全毁”的说法）；
  2. `.data` 存在 **99.86% 结构性缺失**（强化“搜索不完备”的保留）。
- **影响：** 维持 `opcode 0x02 → 0xA2E50` 为 `BLOCKED`（**不是** REFUTED），符合任务书 §6.1“不得把缺少调用引用作为强否定证据”。
- **裁定日期：** 2026-10-12

## REV-011 · 2026-10-12 · 2697 `scripts` 含协议逻辑：削弱

- **旧假设：** 2697 的 1,341 个脚本可能含协议相关逻辑（列为未核验）。
- **新证据：** 脚本扩展名以 `.gsc` 1,198 为主；含 `2697|gamestate|netconst|registration` 标记者仅 **15** 个，且均为游戏逻辑脚本（maps/gametypes/zm/killstreaks）。
- **证据来源：** 本轮只读目录普查（E-15）。
- **新结论：** 协议级逻辑集中在 **EXE**，不在脚本层。搜索面收窄。
- **裁定日期：** 2026-10-12

## REV-012 · 2026-10-12 · 方法学自查：VA/RVA 混淆（本档案内部）

- **错误：** 本档案第二轮早期脚本曾把 **VA** 当作 **RVA** 传入区段映射，得出“`0xA2E50` 落在 thunk 指令中段（真实入口 0x4A2E40）”的中间结果。
- **发现：** 用既有交接值双向校验（`RVA 0x1AC1D0 → off 0x1AB5D0`；`RVA 0xA2E50 → off 0xA2250`）时发现不一致；正确公式为 `off = PointerToRawData + (RVA − VirtualAddress)`。
- **纠正后：** 全部扫描重跑，结果与既有 F2/F3 报告**一致**（`.text` 对 `0xA2E50` 直接调用 = 0）。
- **保留：** 错误中间结果与纠正过程一并保留，作为 H11“分析工具造成假象”的实例记录。
- **裁定日期：** 2026-10-12

---

## 未变更的结论（第二轮后）

| 结论 | 状态 |
|---|---|
| `0x02 → 0xA2E50` 分派 | BLOCKED（维持，负面证据加强） |
| 2697 双门控（资源 `+0x78F4` + 注册 `+0x6408`） | CONFIRMED（本轮复算通过） |
| `0x02`/`0x01` 选择条件 | CONFIRMED（指令级） |
| 内部 `0x06` ≠ 外层 EOF | CONFIRMED（指令级） |
| OLD ≡ 1113（216/217 文件） | CONFIRMED |
| OLD 是 CoD4x fork | CONFIRMED |
| 客户端 `0x06` 处理 | NOT-OBSERVED / BLOCKED |
| COOKIE_ECHO 189 vs 219 | SOURCE-CONFLICT（保留） |
| codec 187 vs protocol 1 | SOURCE-CONFLICT（保留） |

---

## REV-013 · 2026-10-12 · configstring body 位编码：BLOCKED → 服务端已闭合

- **旧结论（E1）：** `configstring` 状态 `VERIFIED_HEADER_TRAILER_BODY_BLOCKED`；body 位编码列为 `BLOCKED`（"exact index bit packing / string indexing rules / array encoding"未知）。
- **新证据：** 对 `_CODOL2697_WriteConfigstrings`（RVA 0xA0468..0xA04E2）逐指令追踪，闭合：
  - 索引增量规则（RVA 0xA0400：连续→1 bit；否则 0 + 13 bit；初值 -1）；
  - A1（字符串表：`strlen+1` 字节，含 NUL）；
  - A2（10-bit count + 每项 索引 + 10-bit 值）；
  - A3（10-bit count + 每项 索引 + 10-bit + 7-bit + 4-bit n + n×12-bit，记录步长 0x4C）；
  - 全部上限与失败分支（越界/去重/黑名单 → `msg+0x14=1` + `return 0`）。
- **证据来源：** `E08_CONFIGSTRING_BODY_001\`（EV-08-01/02）。
- **新结论：** **服务端 body 规格 `CONFIRMED`**；**客户端消费仍 `BLOCKED`**。
- **保留：** 旧 `BLOCKED` 状态保留于 E1 报告与 `_EVIDENCE_REGISTER.md` 历史段，不删除。
- **裁定日期：** 2026-10-12

## REV-014 · 2026-10-12 · 更正：RVA 0xA0807 / 0xA0997 属服务端函数体

- **旧表述：** 把 RVA 0xA0807–0xA0997 当作"最终版 CODOL **客户端**"的待调查地址。
- **新证据：** 服务端 `S-2697` 在该区间为 `_CODOL2697_WriteConfigstrings` **函数体内**（`call 0x499566` 写计数、`call 0x499551` 写 `0x06`）；客户端 `C-2697-Rec` 在同 RVA 为**函数尾/int3 填充**。
- **证据来源：** EV-08-04。
- **新结论：** 该地址区间应在**服务端**语境下调查；客户端需按**行为签名**（位读取原语）另行定位。
- **保留：** 旧表述记录于 `06_UNKNOWN_AND_CONFLICTS.md` C-03。
- **裁定日期：** 2026-10-12

## REV-015 · 2026-10-12 · 新增两侧位序同构证据

- **新证据：** 客户端存在 LSB-first 位读取原语（自足函数 RVA 0x1A07B0/0x1A07E7；54 处同族；1 位读取函数被 115 个调用点共用），与服务端 `MSG_WriteBits`（RVA 0x99590）位序一致。
- **意义：** 字段级兼容的**必要条件已满足**；**不构成**充分条件，亦**不**证明协议兼容。
- **证据来源：** EV-08-03。
- **裁定日期：** 2026-10-12

## REV-016 · 2026-10-12 · 新增冲突：`count1` 宽度（8 vs 16 位）

- **指令级：** `0xA0807: call 0x499566`，其内部 `mov ecx,2` → **2 字节**。
- **内联注释串：** VA 0x7C0A00 `"* %u"`、0x7C0A05 `"** %u %u"` 暗示 **8 位**。
- **处置：** 双留（`E08\06_UNKNOWN_AND_CONFLICTS.md` C-01）；本轮以指令级为准，但记录两者可能属不同字段。
- **裁定日期：** 2026-10-12

## REV-017 · 2026-10-12 · 方法学：VA/RVA 混淆第三次复发

- **现象：** E-08 期间再次把 Capstone 输出的 **VA** 当 **RVA** 查区段表，落入 `.eh_fram` 得到误导性反汇编（并一度得出"服务端原语不存在"的错误中间结论）。
- **纠正：** 建立 `E08\...\_tools\pe_helper.py` 统一规则（区段表=RVA；capstone=VA；立即数=VA），并以既有映射对自检。
- **建议：** 将"地址基准自检"写入总档案的**强制流程**。
- **保留：** E-06 REV-012 与本条并列，作为同类高发错误的连续记录。
- **裁定日期：** 2026-10-12

---

## REV-018 · 2026-10-12 · E-09：客户端 configstring 消费路径 PROVEN（BLK-1 解除）

- **旧结论（E-08）：** 客户端 configstring body 读取顺序为 `BLOCKED`。
- **新证据：** 客户端 `0xA2660`（入口）…`0xA2975`（`ret`）与服务端 `_CODOL2697_WriteConfigstrings` 逐字段对应：
  - count1 = `MSG_ReadData(...,2)` @ 0xA26B2；
  - 13-bit 索引 + 连续性判定 @ 0xA26F4 / 0xA26E2；
  - 索引上界 `0x1DD7` @ 0xA2702；索引区间 `cmp cl,0x14` / `cmp cl,0x12` @ 0xA2728；
  - A1 条目 `0xA25F0` @ 0xA2751；
  - A2 = 11-bit 计数 @ 0xA276C、13-bit 索引 @ 0xA27A8、10-bit 值 @ 0xA27D7；
  - A3 = 10-bit 计数 @ 0xA2879、记录子过程 `0xA2480`（10/7/4/n×12）@ 0xA28E0。
- **证据来源：** `E09_CONFIGSTRING_BLOCKERS_001\`（EV-09-02）。
- **新结论：** **PROVEN**（非形状匹配）。
- **保留：** 旧的 `BLOCKED` 记录保留于 E-08 报告，不删除。
- **裁定日期：** 2026-10-12

## REV-019 · 2026-10-12 · E-09：`count1` 宽度裁定为 2 字节（BLK-2 解除）

- **旧状态（E-08）：** `SOURCE-CONFLICT`（指令级 16 位 vs 注释串暗示 8 位）。
- **新证据：** 核心写入器 `0x994FC` 中 `ecx` 同时是拆字节循环次数、`MSG_WriteData` 的 `len`、`value >> 8k` 步长 → 字节数；客户端 `push 2` → `MSG_ReadData` 且 `movsx word ptr` 按 16 位解释；8 位来源 `"* %u"` 实为 `snprintf` 文本用途。
- **新结论：** **16 位（2 字节）PROVEN；8 位 REFUTED。**
- **工程影响：** E-08 `22_SERVER_START_GATING_AUDIT.md` 中"参数化 count1"的建议**不再必要**。
- **保留：** 冲突双方记录保留于 `E08\06_UNKNOWN_AND_CONFLICTS.md` C-01。
- **裁定日期：** 2026-10-12

## REV-020 · 2026-10-12 · E-09：`0x06` 终止语义（服务端闭合 / 客户端仍 BLOCKED）

- **新证据：**
  - 位游标在字节边界强制重同步 `bitpos = used*8`（`MSG_WriteBits` 增长块 0x9960A–0x99635）；
  - `MSG_WriteData` 与 `WriteLenStr`（0x99651）**不**更新位游标 → A1 字符串不占位；
  - `0x06` 起始 bitpos 依输入而变（44/53/61/72/129），**不总字节对齐**；
  - 客户端 `0xA2660` 循环结束即 `ret`，**无 `0x06` 读取**。
- **新结论：** 服务端写入侧 **闭合**；客户端读取侧 **BLOCKED**；端到端终止语义 **不得标 PROVEN**。
- **新增阻断项：** BLK-7（外层分派器未定位）、BLK-8（`0x06` 位流常量 vs 字节标记）。
- **裁定日期：** 2026-10-12

## REV-021 · 2026-10-12 · E-09：更正 E-08 对 0x1A07B0 的识别

- **旧表述（E-08 / EV-08-03）：** RVA 0x1A07B0 为"客户端共享单比特读取器"，115 个调用点，用于与服务端 `MSG_WriteBits` 比对位序。
- **新证据：** 0x1A07B0 调用 `0x1A0660`，后者压入 `"mp/playerdata.def"`(0xCB5D58) / `"mp/playersecuredata.def"`(0xCB6CB8)；0x1A07B0 本身是 **类型分派器**（`cmp eax,9` + 10 项跳转表 0x5A086C）。
- **新结论：** 0x1A07B0 为 **`.def` 脚本字段读取器**；真正的客户端 Msg 位读取器是 **RVA 0x1AC670**。
- **影响：** E-08 "位序两侧同构"的**方向不变**（0x1AC670 亦为 LSB-first），但其**样本指针需更正**。
- **保留：** 旧表述保留于 E-08 报告；本条为更正记录。
- **裁定日期：** 2026-10-12

## REV-022 · 2026-10-12 · E-09：开工准入审计更新（BLK-1/2 解除）

- **旧审计（22_SERVER_START_GATING_AUDIT.md，E-08）：** 8 通过 / 1 部分 / 6 未通过；裁定 `CONDITIONAL GO`（要求 count1 参数化）。
- **新审计（`E09\06_UPDATED_START_GATING_AUDIT.md`）：** **10 通过 / 2 部分 / 4 未通过**；裁定 `CONDITIONAL GO（放宽）`——解除"count1 参数化"与"configstring body 未知"两项约束；新增 BLK-7/BLK-8 两项约束。
- **说明：** 旧审计文件**保留不删**；本条为 supersede 记录。
- **裁定日期：** 2026-10-12
