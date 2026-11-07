# COMBAT-V0.1-NEXT-011 - R2 原始帧解码 (FRAME DECODE)

- 任务: COMBAT-V0.1-NEXT-011 (R2 原始帧解码与 A/B 字段映射)
- 日期: 2026-10-11
- 证据: `REF_LOBBY_KIT_CAP009/capture-21-5.meta` / `capture-21-5.hex` (R2 采集, 由 NEXT-010 埋点产生)
- 性质: 纯离线、只读分析。不启动/附加/注入/读取客户端进程, 不修改 SEC_KEY/协议/accepted 正文/冻结大厅基线/战斗服务器源码。
- 派生目录: `_combat_next011/` (解码脚本 `decode_capture.py`) 与 `_combat_next011_agent/` (独立校验脚本与 JSON/TSV 产物)。
- 本报告不复述 NEXT-001~010 的结论, 只给出本次新增的逐帧字节证据。

## 0. 结论速览

- `meta` 有 1 条 `SESSION-BEGIN` + 44 条 `FRAME`; `hex` 有 44 组 (每组 1 行 `>` 头 + 1 行 hex 载荷)。二者一一对应。
- 44 条记录 = **22 个请求/应答循环**, 全部 `cid=c0001`。
- 每个循环固定为 4 帧: `21/5 请求(82B)` -> `21/5 响应(306B)` -> `6/14 mmbook 请求(98B)` -> `6/14 响应(66B)`。
- 序列号 51..72 成对递增 (请求/响应共享同一 seq); 循环周期约 5s, 共 11 组。
- 全部 44 帧通过: cid 一致、方向标签与实际一致、长度一致、SHA-256 复算一致、帧头自洽 (`u32(raw[0:4]) == len(raw)-4`)、magic `AB 85`、HMAC-SHA1 校验。
- 关键帧独立校验 (见第 4 节): `21/5` 响应 306B (索引 2) 与紧随其后的 `6/14` mmbook 请求 98B (索引 3) 均**由解密明文独立确认** service/task, 不依赖长度或日志标签。
- **响应对象边界实测 = 236 B** (经严格 TLV 遍历恰好消费 236 B, 33 个字段, 无解析错误), **不是 237 B, 也不是 568 B**。

## 1. 证据完整性

| 文件 | 字节 | 计算 SHA-256 | 期望 SHA-256 | 结果 |
|------|------|--------------|--------------|------|
| `capture-21-5.meta` | 7485 | `8242e2cef7dfdeb8408838fe107738268e80c823faf0473919c4d62a6dc4dff5` | `8242e2cef7dfdeb8408838fe107738268e80c823faf0473919c4d62a6dc4dff5` | MATCH |
| `capture-21-5.hex` | 13387 | `3c939ddca07accf3cc20d46bcfd31745e3c6420353a624adaf5848ebab94b653` | `3c939ddca07accf3cc20d46bcfd31745e3c6420353a624adaf5848ebab94b653` | MATCH |

两个文件的 SHA-256 均与任务给定的期望值一致, 证据可信, 分析继续。全过程只读, 未改写原始证据。

## 2. 帧记录清单 (44 条, 保持原始顺序)

| # | cid | meta-label | actual-dir | marker | svc/task | seq | frame-len | frame SHA-256 |
|---|-----|-----------|-----------|--------|----------|-----|-----------|--------------|
| 1 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 51 | 82 | a4147b9449e2921e8486ad191ad6c0fad1647bc17c9922cb3add4196f494729b |
| 2 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 51 | 306 | 7bcd62db926b1a20404fbb9c5b71563fcb2d6c2ea71b2feed8ed46f3ca29acf2 |
| 3 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 52 | 98 | 689bb8d5f2d2353c16fa311275fad56a1ccd8902855f31861181d40905190ec8 |
| 4 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 52 | 66 | 83bcf591fb4065af97031950dfca79cb947fb4f7373dd5c2fd1c9585caded7f5 |
| 5 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 53 | 82 | 16201a94d62e8b3490cf29199b2ce49abada65dcd1807ab6897f461ed9873601 |
| 6 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 53 | 306 | 6dc664d31c5eb2c8f8c861b83212139e685eddc723b0f213b6ee0508eb75e605 |
| 7 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 54 | 98 | 68b50e49ca924c2b2bf6fd3ef3efa61f66d629187936b4eb7753044d2f7ec274 |
| 8 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 54 | 66 | 788bca2f1666f04c667c0157a7079e28b4d28b91c77308813ccf9efc92548f48 |
| 9 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 55 | 82 | ed22b12238759b7bac90e7b2ee2e6906013c967849c3d943019f4f410f063a81 |
| 10 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 55 | 306 | 31ccbdec48745acceb1a1a26b5c3bb47b6372445e903428155dd827a35fc4ad6 |
| 11 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 56 | 98 | ca45ae2ba233e5d97378063b9eca797bf2dcc348e3055004543d43f2c38f2807 |
| 12 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 56 | 66 | 9b353cca6d50ecbbcb79ae4c32064ddd6d875c3194d329adef27fd20cb34383f |
| 13 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 57 | 82 | e4fa2fa2b2117f83951739d2a1def1ecbb9c325eccc4a583c2966312303b1264 |
| 14 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 57 | 306 | e9fbd851a2882426df94f15d74486150f2137e2af4d824497fd80d10b13b1caf |
| 15 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 58 | 98 | 056fcc60bbea91fdae3fb548724f62a892832c44ba2be0ca0b422beb74b043bd |
| 16 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 58 | 66 | 2dbb3b7b072b3be9ee2fd9b2e934741f0d89af773a83de96296cae31be210f49 |
| 17 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 59 | 82 | efb8a8a84cb6994357c5f3dee0ffdd21a60399bae1f045d32ba8602f100ea236 |
| 18 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 59 | 306 | 74d4e8e136e15ee168130438f14010ad9b476b04f4c94d31c8612a12188a9b6a |
| 19 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 60 | 98 | 84934ddcab1d7e1aa94cd05694ed699dc2308b99a5b69f2a43165fba0bffd25c |
| 20 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 60 | 66 | d4f6c3c9c88c828e04441466d0b5b0edd0fb7906fc8a86e0346630c6706239ce |
| 21 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 61 | 82 | c26fac7fc805502979da8fe92cd9a59ac530a49643ffab87938b063c1200cfbb |
| 22 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 61 | 306 | a27cf8bc26e1042bd7c9a16f2cc507cd9719c89390bd06f3dc7f58ef6b2d4e1b |
| 23 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 62 | 98 | 3c1fc75d23567ce14954b52c66c423ad2e13892f21eb526609886f7e4113adf8 |
| 24 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 62 | 66 | 78e9f9ca51405b6af6f63f350b51c8b747e63f5ba775dc05491e715931f7b7ee |
| 25 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 63 | 82 | 09d2167cfb0ef04b9f6296a947cd9b518751a504bc82a1b7e88956c50a3b07c2 |
| 26 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 63 | 306 | 7c4372a687a07e210bdfe23c9a62dea21d54b0b1a2ebbd93f9ac1b0ad99e992f |
| 27 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 64 | 98 | b9cbffb9364b3e9ad891afa965d7b2ab24aef177ffb80570af130b9d6703c10a |
| 28 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 64 | 66 | b6aaf0bc5ef677e522a7070f40e367630e142cfc51eb9560e0b6ea87f5768070 |
| 29 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 65 | 82 | 676191f23eb12f3bbd4e54e9706074a63137c22ba93121fd8d4fd62653d40561 |
| 30 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 65 | 306 | 32793e4024f9ee18bb0823819ecc47ac80f59952bf7fd528c5f0fc30a28137ef |
| 31 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 66 | 98 | da1f680880c11c8da0e6eb9604a9027cdca06820f1a2fa0d16de2eec3075c20f |
| 32 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 66 | 66 | 87e2de17f1397ae73edc38d46c36d4dec3e7bd732450ce649566404ad5abb50d |
| 33 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 67 | 82 | 117a3b15f33f2bce32c267a6ed063a7510c8954aa41329fc2f6a9de96cbe7926 |
| 34 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 67 | 306 | 34cbfdc063fcce4073be02b73cb807e6e53f5dfb880abe6b0fecd0ce87297aa5 |
| 35 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 68 | 98 | 6eee93fc0f6ec9619139162890117de534f3adf058cbb40a38ee1148443f6000 |
| 36 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 68 | 66 | 0ad9d8a24309e4036678c6aa16bf206e066427e84e62b608c36453d9769f8947 |
| 37 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 69 | 82 | 56407079b3b0a4bcbeb3b02201d50868d1e36ba1d20420910b394fe605c42836 |
| 38 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 69 | 306 | b890d29b86ef2ab811b6ab5a9ae5f49459a9ec21d1d670ba95116c32ab7f7b9e |
| 39 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 70 | 98 | 2a09dceaf2b85904baa546a1f99d4474d82cb7a74d4b748d438eaf83976af9bf |
| 40 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 70 | 66 | 92ad69fdb8f5a07b5623b17ba4fdb8c0ef8ac7b798d58fb2106ee63d034c1d30 |
| 41 | c0001 | C2S-PLAIN | C2S | 0x86 | 21/5 | 71 | 82 | ec370a9f763d74604bc6fb5c97445fee9937bb9fd81133895a79dc95bd31d549 |
| 42 | c0001 | S2C-PLAIN | S2C | 0x01 | 21/5 | 71 | 306 | 09f2842a7f73aee632a7f372961cf3e820f6981ae5bcbec50636cda2f00a03c1 |
| 43 | c0001 | C2S-PLAIN | C2S | 0x86 | 6/14 | 72 | 98 | b3c0f52dff5098c7fa893246ca7ab8f1f513dc94ed831d873eeec52e0670a437 |
| 44 | c0001 | S2C-PLAIN | S2C | 0x01 | 6/14 | 72 | 66 | b62fbf80285745133ee09b141029873eff78a364d00f1764f18cc48a48b63be2 |

说明: `marker` 为解密明文的第 5 字节 (`0x86`=客户端任务帧, `0x01`=服务端应答)。`svc/task` 列取自解密明文 (客户端帧含 service/task 字段; 服务端应答无 service 字段, task 取自应答 TLV 的 `tag 3`)。

## 3. 关键帧与字段级校验

前 4 帧 (第一个完整循环) 的字段级明细:

| # | dir | svc/task | seq | frame-len | header_total | declared | plain-len | plain SHA-256 |
|---|-----|----------|-----|-----------|--------------|----------|-----------|--------------|
| 1 | C2S | 21/5 | 51 | 82 | 78 | 38 | 48 | b9cfb2936734e4f0d422f2a5ef1abe2b85e6d4348441eb934c3ca9254e57c53e |
| 2 | S2C | 21/5 | 51 | 306 | 302 | 262 | 272 | e0ba7719ac017a78a98ccaafa8b365b287a453dc317318d013661b201061b299 |
| 3 | C2S | 6/14 | 52 | 98 | 94 | 48 | 64 | e956ad416018367c771a4a8dd3600a5da2a2b93764ffb68cfa876d5c595bfdc1 |
| 4 | S2C | 6/14 | 52 | 66 | 62 | 21 | 32 | edba85a68502f2bf2026a3641ea69a538fcd41d07a2ba7e16cce5f5556e07e3b |

### 3.1 `21/5` 响应 (索引 2, 306 B)

- 线路帧: `u32 total_len=302` + `AB 85` + `u32 seq=51` + `iv[16]` + `cipher[272]` + `hmac8[8]` = 306 B。
- 解密明文 272 B: `u32 payload_len=262` + `marker=0x01` + 262 B 应答 TLV (+ 5 B CBC 填充)。
- 应答 TLV 前缀 26 B (= `prefix`): `tag 0x0a`+`u64 reply_id=51`, `tag 0x08`+`u32 status=0`, `tag 0x03`+`u8 task=5`, `tag 0x08`+`u32 对象个数=1`, `tag 0x08`+`u32 个数=1`。
- 之后紧跟**唯一对象** 236 B, 被严格 TLV 遍历完整消费 (33 字段)。注意: 对象区**没有**外层长度前缀, 其边界是由 26 B 前缀之后剩余的全部 payload 反推 = 262-26 = 236 B。

### 3.2 `6/14` mmbook 请求 (索引 3, 98 B)

- 线路帧: `u32 total_len=94` + `AB 85` + `u32 seq=52` + `iv[16]` + `cipher[64]` + `hmac8[8]` = 98 B。
- 解密明文 64 B: `u32 declared=48` + `marker=0x86` + `service=6` + `version=3` + `task=14` + payload 45 B。
- payload 45 B: `tag 0x0a`+`u64=1`, `tag 0x13`(blob)+`0x08`+`u32 inner_len=29`+`u32 str_len=25`+ 25 B UTF-8 字符串 `mmbook 796 AQAAAAAAAAA= 0`。
- 命令文本与 A/B 见 `FIELD_MAPPING` 报告。

### 3.3 `6/14` 应答 (索引 4, 66 B)

- 解密明文 32 B: `u32 declared=21` + `marker=0x01` + 21 B 应答 TLV: `tag 0x0a`+`u64 reply_id=52`, `tag 0x08`+`u32 status=0`, `tag 0x03`+`u8 task=14`, `tag 0x08`+`u32 对象个数=0`。
- 无对象, 无第二个个数域。11 个循环中仅 `reply_id` 随 seq 变化, 其余恒定。

## 4. 四类数据必须严格区分

| 层 | 含义 | 本报告如何使用 |
|----|------|----------------|
| L1 完整线路帧 | `capture-21-5.hex` 中的 0xAB85 帧原始字节 | 只读, 逐步复算长度与 SHA-256 |
| L2 解密明文 | 用会话密钥 AES-128-CBC 解出的字节 | 用于确认 service/task/marker; 密钥仅在内存中使用, 不落入任何产物 |
| L3 解析对象 | 对 L2 明文做 TLV 遍历得到的字段表 | 字段偏移/宽度证据来源 |
| L4 服务端代码重建 | 依据服务端源码"重新生成"的字节 | **不得作为证据**。服务端使用随机 IV, 无法复现字节; 且服务端构造长度声明与实测不一致 (源码 docstring 写 237, 实测对象为 236) |

本报告的一切结论只建立在 L1-L3 之上。L4 仅用于交叉怀疑, 不作为字段大小的判据。

## 5. cid / 方向 / service / task / seq 的确认方式

- **cid**: 来自 meta 每条记录的 `c0001`, 并与解密会话一致。
- **方向**: meta 标签 (`C2S-PLAIN`/`S2C-PLAIN`) 与"实际解密方向"逐一比对。判据不是标签文本, 而是**哪一组密钥能通过 HMAC 并解出合法明文** (客户端密钥 -> marker `0x86`; 服务端密钥 -> marker `0x01`)。44/44 一致。
- **service/task**: 客户端帧直接读解密明文里的 `service`/`version`/`task` 三字节; 服务端应答无 service 字段, 其 task 取自应答 TLV 的 `tag 3`, 并与同 seq 的请求关联。二者一致: 22 条客户端帧 = 21/5 x11 + 6/14 x11。
- **seq**: 取自线路帧头 `u32 seq`, 与 meta 的 `seq=` 一致; 请求/响应成对同 seq, 51..72。

## 6. 限制与停止点

- 本报告只解码并向上一层暴露"真实采集到的字节", 不对 A/B 语义作任何断言 (见 `COMBAT_V0_1_NEXT_011_FIELD_MAPPING.md`)。
- 采集内**不存在** `21/5` accepted 推送 (见 `COMBAT_V0_1_NEXT_011_IMPLEMENTATION_GATE.md`)。
- 不因协议取证有进展就宣称真实战斗连接已成功。
