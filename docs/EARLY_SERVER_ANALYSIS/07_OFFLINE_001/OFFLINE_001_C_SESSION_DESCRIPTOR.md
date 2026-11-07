# OFFLINE_001 — 工作流 C：258B 会话描述符 与 16B securityKey 布局/引用关系

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-001` 工作流 C。
> 只读输入；派生脚本/报告仅写 `07_OFFLINE_001\`；不启动服务端/客户端，不执行 `.cmd`。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## C.0 一句话结论

**258B 会话描述的布局为"已确认布局"（字节级），16B securityKey 在其中的位置与引用链为"已确认"。**

- `session_record_258.bin` = **258B，33 个带 tag 字段**，`parse_consumed == size == 258`、`parse_error == null`（无尾部残留、无越界）。
- 地址字段：**field#0 = Blob[37]**（`bdCommonAddr` 短形态），位于偏移 **0..42**。
- **securityKey：field#15 = Blob[16]**，位于偏移 **147..168**（含 5B tag/len 头，总长 22B，负载 16B）。
- 与冻结参考实现 `codol_crypto.build_session_record` 的**字节差异只有 15B，且全部落在 securityKey 负载内**（本机 `.bin` 为 16×`0x01`，黄金向量为 `00..0F`）——属**参数差异，不是布局差异**。
- 16B securityKey 是 **ECDH 派生输入的一半**（`x[28] ‖ security[16] → key24`），故它与工作流 A 的密钥派生直接相连。
- **客户端接受性 UNPROVEN**：布局自洽 + 与冻结参考一致，但**尚无真实客户端接受该 258B 记录的实机证据**。

---

## C.1 原始证据来源

| # | 结构 | 路径 | SHA-256 | 性质 |
|---|---|---|---|---|
| 1 | 258B 记录（本机导出） | `CODOL-Combat-Server-v0.1\build\bin\session_descriptor\session_record_258.bin` | `72ECC9E6E73C5AFA3051107E5A90AB60D9F115A787C43F8D49828B6BB654122C` | 待验证字节 |
| 2 | 16B 密钥文件 | `...\CODOL_Server\lobby\securitykey.bin` | `DB8A6DF1A30B0253A2FFE8D79A4DFDB0584F24E62125C5CDFCEB41BB04876A36` | 16B，值不输出 |
| 3 | 28 字段大厅侧描述符 | `...\CODOL_Server\lobby\session_desc.pickle` | `5423902CCDB43B02E1CD845F1526FED2B9C184D5126BDB64624EAE3F41CA6FDF` | 另一结构 |
| 4 | 冻结参考实现 | `REF_LOBBY_KIT\codol_crypto.py` | `E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607` | 黄金来源 |
| 5 | C# 移植实现 | `CODOL-Combat-Server-v0.1\src\Codol\SessionDescriptor.cs` | `0E1A31706B9467D997CE22A3622D3CE2CAEB065AE4DE5F50A03F82695EC2C732` | 移植 |
| 6 | C# 黄金向量 | `CODOL-Combat-Server-v0.1\src\Codol\SessionGolden.cs` | `FE23C29567A1992BE6EABE7F2E2E0857BE24BE158AE7AF212B59449FF7EEC154` | 冻结字节 |
| 7 | 黄金生成器 | `CODOL-Combat-Server-v0.1\tests\gen_session_golden.py` | `D386CC569A22108FF1D1960B3FE8258514AC0CF2DBA9FEC0126EA15A7CA73AD2` | 生成脚本 |
| 8 | ol-mod 实现 | `_e1_regression\ol-mod-olfinal\src\backend\Demonware\MatchmakingService.cpp` | （见 `_evidence`，本轮按行核对） | 第三方实现 |
| 9 | 描述符元数据 | `...\build\bin\session_descriptor\session_descriptor.json` | `911EA690373D51D3EFC2BA905D54A03717F60BD664A375086AA3788713DA1870` | 自述元数据 |
| 10 | 原生 16B 读取路径 | `...\dedicated\src\codol\net\codol_network.c` | `FEB5BD4A0E78CD3134F3380CCBA2DDDF75583A91985BFE2637047574D2807B55` | 引用链 |
| 11 | 原生派生 | `...\dedicated\src\codol\net\codol_crypto.c` | `CAAD3E3CE1A8F68172C5B99F2FAD5B6BB80472D8A568C5852EC4E07F4F406FB8` | 引用链 |

（路径根：`REF_LOBBY_KIT` 与 `CODOL-Combat-Server-v0.1` 在 `D:\BaiduNetdiskDownload\使命召唤OL\` 下；`CODOL_Server` 样本在 `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\` 下。）

---

## C.2 258B 描述符逐字段偏移表（33 字段）

**tag 文法**（`SessionDescriptor.cs:52-69` / `codol_crypto.py:300-329` 一致）：

| tag | 含义 | 编码 |
|---|---|---|
| `0x08` | U32 | tag + 4B 小端 |
| `0x07` | I32 | tag + 4B 小端（有符号必须用 7，混用 8 客户端判非法） |
| `0x0A` | U64 | tag + 8B 小端 |
| `0x13` | Blob | tag + `0x08` + 4B 小端长度 + 负载 |
| `0x10` | String | tag + ASCII 负载 + `0x00` |

**实测偏移表**（由 `_tools\verify_offline_001.py` tag-walk 解析，`parse_consumed=258`，`field_count=33`）：

| # | 起始偏移 | 总长 | tag | 值 / 负载 | 备注（来源） |
|---|---|---|---|---|---|
| 0 | 0 | 43 | BLOB | len=37，payload_sha1=`A236DCAD92A299553A6B392D2611B0B29C9DC373` | Hostaddress = 37B `bdCommonAddr` |
| 1 | 43 | 14 | BLOB | len=8，payload_sha1=`C3BAA7A6C6F1C0AB9EE7577B19C3166629DD5AF7` | SessionId = `0x1122334455667788` LE |
| 2 | 57 | 5 | U32 | 0 | GameType |
| 3 | 62 | 5 | U32 | 18 | MaxPlayers |
| 4 | 67 | 5 | U32 | 1 | CurrentPlayers |
| 5 | 72 | 12 | STRING | `"1432778633"` | roomId（非零十进制串） |
| 6 | 84 | 9 | U64 | 1000001 | host uid |
| 7 | 93 | 19 | STRING | `"mp_crash_tropical"` | map |
| 8 | 112 | 5 | I32 | -695030357 | query criterion `0xD692ADAB` |
| 9 | 117 | 5 | I32 | 0 | query criterion |
| 10 | 122 | 5 | I32 | 0 | query criterion |
| 11 | 127 | 5 | I32 | 0 | query criterion |
| 12 | 132 | 5 | I32 | 0 | query criterion |
| 13 | 137 | 5 | I32 | 0 | query criterion |
| 14 | 142 | 5 | I32 | 0 | query criterion |
| **15** | **147** | **22** | **BLOB** | **len=16，payload_sha1=`345C0E97987B1F4E1BE38EE1678A5F1061C2C301`** | **securityKey（16B 负载 @153..168）** |
| 16 | 169 | 5 | I32 | 19 | query criterion |
| 17 | 174 | 5 | I32 | 0 | — |
| 18 | 179 | 5 | I32 | 0 | — |
| 19 | 184 | 5 | I32 | 8 | query criterion |
| 20 | 189 | 5 | I32 | -1 | — |
| 21 | 194 | 5 | I32 | 796 | playlist version |
| 22 | 199 | 5 | I32 | 30 | query criterion |
| 23 | 204 | 5 | I32 | 0 | — |
| 24 | 209 | 5 | I32 | 7 | query criterion |
| 25 | 214 | 5 | I32 | 0 | — |
| 26 | 219 | 5 | I32 | 202235905 (`0x0C0DE001`) | room id（刻意非零） |
| 27 | 224 | 9 | U64 | 1000001 | demonwareID / room id |
| 28 | 233 | 5 | I32 | 0 | — |
| 29 | 238 | 5 | I32 | 0 | — |
| 30 | 243 | 5 | I32 | 0 | — |
| 31 | 248 | 5 | I32 | 1 | — |
| 32 | 253 | 5 | I32 | 0 | 末字段，结束于 258 |

- **总长自洽**：`Σ 各字段总长 = 258`，无剩余、无越界（`parse_consumed==258`）。
- **字段序号说明**：字段 8..25 中的 7 个 I32 是 `writeSessionRecordTail` 的 "query criterion"，客户端据以过滤；字段 0..4 是 5 个前置字段。
- **字段名映射**：`SessionDescriptor.BuildSessionRecord`（`SessionDescriptor.cs:131-159`）逐行对应上表；冻结参考 `codol_crypto.build_session_record`（`codol_crypto.py:348-389`）语义相同。

---

## C.3 securityKey 的偏移、读取/写入位置与交叉引用

**写入位置（构造侧）**
- 冻结参考：`codol_crypto.py:381` `ob.blob((security_key or b"")[:16].ljust(16, b"\x00"))` —— **第 6 个"记录尾"字段，Blob[16]**。
- C# 移植：`SessionDescriptor.cs:149-151` `byte[] sk = new byte[16]; ... ob.Blob(sk);`。
- ol-mod：`MatchmakingService.cpp:531-537` `std::array<uint8_t,16> key{}; ... object.writeBlob(key);`（注释：`The 16-byte security key ... comes from the session descriptor rather than being minted here`）。
- 三者一致：**16B、Blob、位于记录尾、值由会话参数提供而非本地生成**。

**读取位置（原生引用链）**
- 原生以 `codol_securityKeyPath`（`codol_network.c:48-49`）指向一个**恰好 16 字节**的文件；`read_key(byte out[16])`（`:78-84`）`fread` 17B 缓冲、**要求 `n == 16`**，否则失败。
- 会话候选密钥集合 `candidate_keys()`（`:93-102`）把 admission roster 与 `securitykey.bin` 合并。
- 该 16B 与共享 X 一起进入派生：`codol_crypto.c:28-37` `CODOL_DeriveKey(key24, x[28], security[16])` 计算 `Tiger192(x ‖ security)`；`codol_association.c:21,24` 调用它并保存 `shared_x`。
- C#/REF/ol-mod 侧同位置：`x[28] ‖ security[16] → key24`（见工作流 A.1 证据 2/3/4）。

**结论**：16B securityKey 是 **ECDH 派生输入的另一半**，两侧（大厅下发的描述符 / 战斗服读取的密钥文件）**必须逐字节相同**，否则传输密钥分叉 → 静默丢包（`SessionDescriptor.cs:7-8` 注释明述此门槛）。

**交叉引用（本机 16B 密钥的字节一致性）**
- `lobby\session_desc.pickle` 的 **field#19 = Blob[16]** 与 `lobby\securitykey.bin`（16B）**逐字节相等**（本报告复算：`bytes(field19) == securitykey.bin` 为 `True`；二者 SHA-256 均为 `DB8A6DF1…`）。→ 说明"描述符内嵌的 16B"与"战斗服读取的 16B 文件"在部署上指向同一密钥。
- 但 **258B 记录内嵌的 16B 是另一条路径**：`session_record_258.bin` 的 field#15 负载为 16×`0x01`（默认密钥），sha1=`345C0E97…`；它与 `lobby\securitykey.bin`（`DB8A6DF1…`）**不是同一份值**——这是**不同的部署/参数**，非布局冲突。

---

## C.4 与黄金向量 / 冻结参考的逐字节对照

**复算步骤（可重复）**
1. 计算 `session_record_258.bin` SHA-256 = `72ECC9E6…`（与 `session_descriptor.json:9` 自述一致）。
2. 运行 `_tools\verify_offline_001.py`（自实现解析器）→ `C_session_descriptor`：`size=258`、`field_count=33`、`parse_error=null`。
3. 运行 `_tools\verify_cookie_len_2nd.py`（独立第二实现）→ `C_descriptor_offset_table`：
   - `securitykey_blob_offset=147`，`securitykey_blob_total_len=22`；
   - `byte_exact_equal_to_golden=false`，`diff_count=15`，`all_diffs_within_securitykey_payload=true`；
   - `byte_exact_except_securitykey=true`。

**结果**
- 与 C# 黄金向量 `REC_GOLDEN`（`SessionGolden.cs:18-27`，258B）对照：**除 securityKey 负载外逐字节相同**。
- 差异 **15B**（偏移 153..168 内 15 个不同字节）：本机 `.bin` 为 **16×`0x01`**，黄金为 **`00..0F`**。
- 解释：黄金生成器 `tests\gen_session_golden.py` 用 `security_key=bytes(range(16))`，本机导出用 `DefaultSecurityKey`（`CodolProtocol.cs:56-57` = 16×`0x01`，注释"实机核实 build 1649370 ID 1"）。→ **参数差异，不是布局差异**。
- 结论：**布局 CONFIRMED**（tag/偏移/长度全部一致）；**唯一可变字段就是 securityKey 负载**（与参考注释"可变项只有 3 个: roomId / map / 16B securityKey"一致）。

---

## C.5 相关但不同的结构（避免混淆）

### C.5.1 21/5 mission session 对象（268B / 237B / 228B 变体）
- 构造：`codol_crypto.build_mission_session_object`（`:460-`）；C# `SessionDescriptor.BuildMissionSessionObject`（`SessionDescriptor.cs:176-231`）。
- 靶场 / Extended67：**268B**（67B 地址块）；普通 / Normal24：**237B**（24B 地址块）。
- **本机导出 `mission_normal.bin` = 228B**（`session_descriptor.json:10`）。复算证明：228 = 237 − 9，差值来自 **map 名长度**（导出用 `"mp_crash_tropical"` 17 字符，参考默认 `"coop_training_mp_cargoship"` 26 字符，差 9B）。→ **参数（地图名）差异，非布局差异**；实测 `.bin` 内 ASCII 串为 `mp_crash_tropical`（@60）。
- 该结构字段数与 258B 记录不同（33 字段但字段序不同），**不是** 258B 记录的别名。

### C.5.2 大厅侧 28 字段描述符（`session_desc.pickle`，356B）
- 这是**客户端 createSession/updateSession 上送的 bdMatchMaking 描述符**，与战斗服下发的 258B 记录是**两个不同结构**。
- 布局（`map_handoff.py:36-46` 文档 + 本报告复算 28 元素）：
  - `0 Blob[37] bdCommonAddr`、`1 U32`、`2 U32 maxPlayers`、`3/4 String name`、`5 I32 mode(0/1/2)`、`6 I32 0`、`7 I32 406`、`8 I32 0`、`9 I32 rolling`、`10 I32 0/1`、`11 I32`、`12..18 I32 0`、**`19 Blob[16] clientSecurityKey`**、`20 U64 xuid`、`21 Blob[56] zeros`、`22 U64 roomId`、`23 I32 crc32(gametype)`、`24 I32 crc32(map)`、`25..27 I32`。
  - 实测 field#0=Blob[37]、field#19=Blob[16]、field#21=Blob[56]；field#23=2370954136=`crc32("combat")`、field#24=1543214545=`crc32("mp_crash_tropical")`（复算一致）。
- **共同点**：两种结构都在**偏移靠后的字段里嵌入同一个 16B securityKey**，且都以 **Blob 语义**承载。**不同点**：字段数、字段序、总长都不同。

---

## C.6 与握手 / 数据认证 / 会话生命周期的关联

- **握手**：COOKIE_ECHO 携带 100B 客户端公钥（工作流 B）；双方各自用 ECDH 得 `x[28]`，再与 **16B securityKey** 组合派生 24B 传输密钥（`codol_crypto.c:28-37`）。securityKey 由**大厅经描述符下发**（本报告 C.3）。
- **数据认证**：派生出的 24B key 供 DATA 记录做 HMAC 与 keystream（工作流 A）。**同一 16B 输入 ⇒ 同一 key24 ⇒ MAC 两侧可校验**；两侧不一致 ⇒ 静默丢包（`SessionDescriptor.cs:7-8`）。
- **会话生命周期**：原生 `codol_sessions.txt`（`SESSION_FILE`，`codol_network.c:155`）持久化 association（含 `shared_x`、计数器），`SESSION_TTL=900`（`:156`）。securityKey 变更会改变后续 association 的派生密钥（`codol_association.c:82` 用 `candidate` 重新派生）。
- **边界**：以上是**代码级引用链**（CONFIRMED 的源码事实）；**没有**任何证据表明 258B 描述符能解释 A/B 的**数值**差异——A 的阻塞是"缺完整 24B key / ECDH 私钥"，B 的差异是"地址块 67 vs 37"，二者都不由描述符布局决定。**故不强行关联。**

---

## C.7 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 258B 记录 = 33 个带 tag 字段、总长自洽 | **CONFIRMED** | 两独立解析器 `parse_consumed=258`、`field_count=33` |
| 地址 field#0 = Blob[37] @0..42 | **CONFIRMED** | 解析 + `SessionDescriptor.cs:107-121` |
| securityKey = field#15 Blob[16] @147（负载 @153..168） | **CONFIRMED** | 解析 + `codol_crypto.py:381` / `SessionDescriptor.cs:149-151` / `MatchmakingService.cpp:531-537` |
| 与冻结参考除 securityKey 外逐字节相同 | **CONFIRMED** | `verify_cookie_len_2nd.py`：`byte_exact_except_securitykey=true`，`diff_count=15` 全在密钥负载 |
| 16B securityKey 是 ECDH 派生输入的一半 | **CONFIRMED** | `codol_crypto.c:28-37`、`codol_association.c:21,24`、`codol_crypto.py:328-336` |
| `session_desc.pickle` field#19 == `securitykey.bin` | **CONFIRMED** | 本报告复算 `bytes(field19)==securitykey.bin`，SHA-256 同 `DB8A6DF1…` |
| 21/5 mission 对象 268/237/228B 差异源于地址块/地图名 | **CONFIRMED** | 复算 228=237−9（地图名长度） |
| **真实客户端接受 258B 记录** | **NOT_OBSERVED** | 无客户端接入；`SessionDescriptor.cs:19-20` 自述"不证明客户端接受" |

---

## C.8 独立复核

- **输入版本一致**：C 与 A/B 共用同一 `session_record_258.bin`（`72ECC9E6…`）；16B 密钥文件哈希 `DB8A6DF1…` 与输入清单一致。
- **共享解析错误**：布局由**两套独立解析器**（`verify_offline_001.py` 与 `verify_cookie_len_2nd.py`）分别 tag-walk，得到同一字段表与同一 securityKey 偏移；tag 文法另有 `SessionDescriptor.cs:52-69` 与 `codol_crypto.py` 两份源码交叉印证。
- **隐含假设**：本机 `.bin` 的 16×`0x01` 属**参数选择**（`DefaultSecurityKey`），非结构问题——由黄金生成器与 C# 常量两处独立说明支撑。
- **与其他工作流矛盾**：无。A 的 24B key 派生需要 16B securityKey（本报告给出其布局与引用）；B 的 219B COOKIE_ECHO 地址块为 67B 长形态，而**258B 记录**内嵌 37B 短形态——**这是两个不同上下文**（ol-mod `net_dtls_cod.cpp:324-341`：客户端回显它被给的形态，37/67 均为合法变体）。**不构成矛盾**，但记为待澄清项（见 C.9）。
- **可否由另一脚本复现**：是。任一解析器可重跑得到同一偏移表；黄金对照由 `verify_cookie_len_2nd.py` 独立完成。
- **是否超出证据**：未断言"客户端一定接受"；未输出密钥材料（仅 sha1/长度/前缀）；未把描述符与 A/B 数值差异强行关联。

---

## C.9 结论与待澄清项

- 258B 描述符：**已确认布局**（33 字段、securityKey @147/负载 @153..168、总长 258）；与冻结参考**除 securityKey 外逐字节一致**。
- 16B securityKey：**已确认**为 ECDH 派生输入的一半，且在描述符/密钥文件间有明确引用链。
- **待澄清（不猜测）**：
  1. **客户端接受性**：无实机证据证明真实客户端接受该 258B 记录（`NOT_OBSERVED`）。
  2. **地址块形态**：258B 记录内嵌 **37B** 短地址；观测到的 COOKIE_ECHO 携带 **67B** 长地址（工作流 B）。二者分属不同上下文，需一份"客户端下发的 67B 地址块 ↔ 记录内 37B/67B 变体"的实机对应证据才能闭合。
  3. **本机 16×`0x01` vs `lobby\securitykey.bin`**：为不同部署参数，需确认哪一份才是目标运行时应使用的一致密钥。

---

## C.10 复算命令（只读）

```
python _tools\verify_offline_001.py            # C_session_descriptor: size=258 fields=33
python _tools\verify_cookie_len_2nd.py         # C_descriptor_offset_table: securitykey_blob_offset=147
python _tools\probe_lobby_descriptor.py        # session_desc.pickle 28 字段
python _tools\probe_lobby_descriptor2.py       # field19 == securitykey.bin
python _tools\probe_golden_lengths.py          # 黄金/参考长度 258/268/237
python _tools\probe_mission_len.py             # 228 = 237 - 9（地图名长度）
```
