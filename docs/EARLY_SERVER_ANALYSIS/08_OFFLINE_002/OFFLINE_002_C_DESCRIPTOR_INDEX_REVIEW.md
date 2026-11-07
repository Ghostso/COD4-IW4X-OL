# OFFLINE_002 — 复核 C：会话描述符字段编号歧义裁决（field#15 vs field#19）

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §4。
> 输入：只读；仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告，不输出密钥材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## C.0 裁决结论（一句话）

**field#15 与 field#19 不是同一结构、不是零基/一基约定冲突，而是两个不同结构上的两个不同索引。** → **CONFIRMED**。

- **field#15** 属于 **258B 会话记录**（33 个带 tag 字段；securityKey = **0-based 第 15 个字段**，blob 头 @147，负载 @153..168）。
- **field#19** 属于 **`lobby\session_desc.pickle`**（28 字段的大厅侧描述符；securityKey 位于 **索引 19**）。
- 两者**索引基与字段集合都不同**：258B 记录前有 **5 个前置字段**（Hostaddress/SessionId/GameType/MaxPlayers/CurrentPlayers），securityKey 落在整体第 15 位；pickle 是另一套 28 字段布局，securityKey 落在索引 19。
- **编号是否统一**：**是（已裁决）** —— 统一为"两套不同结构各自独立编号"，**不强行合并**。

---

## C.1 两套结构的原始证据

### C.1.1 258B 会话记录（field#15）

- **构造代码**：`CODOL-Combat-Server-v0.1\src\Codol\SessionDescriptor.cs:131-159` `BuildSessionRecord`。
  - `:137-142` 注释 "5 个前置字段"，依次 `ob.Blob(BuildCommonAddress(...))`（Hostaddress）、`ob.Blob(U64Le(sessionId))`（SessionId）、`ob.U32(gameType)`、`ob.U32(maxPlayers)`、`ob.U32(currentPlayers)`。
  - `:149-151` `byte[] sk = new byte[16]; ... ob.Blob(sk);  // 6 16B securityKey`。
  - 从第 0 个 Blob（Hostaddress）数起：Hostaddress=0、SessionId=1、GameType=2、MaxPlayers=3、CurrentPlayers=4、roomId=5、hostUid=6、mapName=7、criterion=8..12、**sk=15**（`0x13` Blob 字段的 0-based 序号）。
- **字节解析（本轮独立复算）**：`verify_offline_002.py` 对 `session_record_258.bin`（SHA-256 `72ECC9E6…`）做显式 tag-walk：
  - `size=258`、`field_count=33`、`parse_consumed=258`
  - `securitykey_field_index=15`、`securitykey_blob_offset=147`、`securitykey_payload_range=[153,169]`
  - `first_field_blob_len=37`、`first_field_total_len=43`

### C.1.2 `session_desc.pickle`（field#19）

- **读取代码**：`07_OFFLINE_001\_tools\probe_lobby_descriptor2.py:5` `f19 = obj[19][1]`（**索引 19**）。
- **本轮复算**（`verify_offline_002.py`，`C_pickle`）：
  - `field_count=28`、`field19_len=16`
  - `field19_equals_keybin=true`
  - `field19_sha256=DB8A6DF1A30B0253A2FFE8D79A4DFDB0584F24E62125C5CDFCEB41BB04876A36`（与 `lobby\securitykey.bin` 同哈希）
  - `field0_blob_len=37`、`field21_blob_len=56`

---

## C.2 为什么不是零基/一基冲突

| 维度 | 258B 记录 | `session_desc.pickle` |
|---|---|---|
| 字段总数 | **33** | **28** |
| securityKey 索引 | **15**（0-based） | **19**（0-based） |
| 前置字段 | 5 个（Hostaddress/SessionId/GameType/Max/Current） | 结构不同 |
| 序列化格式 | tag 文法（`0x08/0x07/0x0A/0x13/0x10`） | Python pickle（元组列表） |
| securityKey 长度 | 16B（blob 负载） | 16B |

- **字段总数不同（33 vs 28）**：若是同一结构的零基/一基差异，字段总数应相同而仅编号相差 1。实际 **33≠28** 且 **15 与 19 相差 4**（不是 1）→ **排除零基/一基解释（REFUTED）**。
- **索引差 4** 且两结构前置字段数不同，说明是**不同结构各自独立编号**。

---

## C.3 securityKey 实际偏移、长度与载荷边界（258B 记录）

- blob 头：`0x13`(1B tag) + `0x08`(1B) + 4B 小端长度(=16) = **6B 头**。
- blob 起始偏移：**147**；长度字段在 `[149:153]`；负载 `[153:169]`（16B）。
- 复算依据：`verify_offline_002.py` 的 `struct.unpack_from("<I", data, i+2)` 读长度 + `sk_idx/sk_off` 搜索（`ln==22` 即 6+16）。
- **载荷边界确认**：`[153:169]` 恰 16B，`[169]` 为下一字段 tag（`0x07` I32=19）。

---

## C.4 `lobby\securitykey.bin` 与 `session_desc.pickle` 的来源与对应关系

- **`lobby\securitykey.bin`**：16B，SHA-256 `DB8A6DF1…`（值不输出）。是 ECDH 派生输入的一半。
- **`session_desc.pickle`**：28 字段大厅侧描述符；其 **索引 19** 的 blob 与 `securitykey.bin` **逐字节相同**（`field19_equals_keybin=true`，哈希一致）→ **同一份 16B 密钥**（CONFIRMED）。
- **引用链**：16B securityKey → `x28 ‖ sec16 → key24`（`codol_crypto.c:28-37`）→ DATA 记录 MAC/keystream（工作流 A）。
- **与 258B 记录的差异（非布局差异）**：本机 `session_record_258.bin` 的 securityKey 负载为 **16×0x01**，而 `lobby\securitykey.bin` 为另一份值 → 属**部署参数差异**，非结构差异（`OFFLINE_001` C 已记；本轮复核维持）。

---

## C.5 与工作流 A/B 的关联边界

- securityKey 与工作流 A **有真实引用链**（派生 key24）；这与"字段编号歧义"无关。
- **不能**用本结构解释 A 的数值差异（A 阻塞在缺完整 24B key / ECDH 私钥）或 B 的差异（地址块 67 vs 37）。
- **258B 记录内嵌 37B 短地址**，而观测 COOKIE_ECHO 携带 **67B 长地址** → 属**不同上下文**，**不强行关联**。

---

## C.6 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 258B 记录 = 33 个带 tag 字段、总长自洽 | **CONFIRMED** | 独立 tag-walk：`field_count=33`、`parse_consumed=258` |
| securityKey = 258B 记录 0-based field#15，blob@147，负载@153..168 | **CONFIRMED** | `SessionDescriptor.cs:131-159` + 字节解析 |
| `session_desc.pickle` = 28 字段，securityKey @ index 19 | **CONFIRMED** | `probe_lobby_descriptor2.py:5` + 复算 `field_count=28` |
| pickle field19 == `securitykey.bin` | **CONFIRMED** | 逐字节相同 + 同 SHA-256 |
| field#15 与 field#19 是零基/一基冲突 | **REFUTED** | 字段总数 33≠28、索引差 4≠1 |
| 字段编号"已统一"为两套独立结构 | **CONFIRMED** | 上述四项 |
| 258B 记录内嵌 37B 短地址 vs COOKIE_ECHO 67B 长地址的实机对应 | **NOT_OBSERVED** | 无实机对应证据 |

---

## C.7 结论

- **编号歧义已裁决**：field#15（258B 记录，0-based，含 5 前置字段）与 field#19（28 字段 pickle）是**两个不同结构**的编号，**不是**零基/一基冲突，**不需要强行统一**。
- **securityKey 布局已确认**：258B 记录内 16B @153..168；pickle 内 16B @index 19；两者与 `securitykey.bin` 的对应关系已闭合（pickle 侧逐字节相同）。
- **仍未知（不猜测）**：258B 记录内 37B 短地址与实机 67B 长地址的对应关系（NOT_OBSERVED）；本机 16×0x01 与 `securitykey.bin` 哪一份为目标运行时密钥。

---

## C.8 复算命令（只读）

```
python _tools\verify_offline_002.py           # C_descriptor: field_count=33, securitykey_field_index=15, blob_offset=147
python _tools\probe_lobby_descriptor2.py      # pickle field19 == securitykey.bin
```
