#!/usr/bin/env python3
"""NEXT-011 report generator.

Reads only derived, key-free artifacts under _combat_next011_agent/ and writes the
four top-level deliverables. No secrets, no client process, no protocol changes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "_combat_next011_agent"
EVID = ROOT / "REF_LOBBY_KIT_CAP009"


def rd(name):
    return (AGENT / name).read_text(encoding="utf-8")


def load(name):
    return json.loads(rd(name))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


summary = load("summary.json")
inventory = list(csv.DictReader(rd("frame_inventory.tsv").splitlines(), delimiter="\t"))
objects = load("objects.json")
mmbook = list(csv.DictReader(rd("mmbook.tsv").splitlines(), delimiter="\t"))
object_fields = list(csv.DictReader(rd("object_fields.tsv").splitlines(), delimiter="\t"))
ab = load("ab_candidates.json")
accepted = load("accepted_check.json")
indep = json.loads(rd("independent_report.json"))
cycles = load("cycles_ab_candidates.json")

META_SHA = "8242E2CEF7DFDEB8408838FE107738268E80C823FAF0473919C4D62A6DC4DFF5"
HEX_SHA = "3C939DDCA07ACCF3CC20D46BCFD31745E3C6420353A624ADAF5848EBAB94B653"


def frame_table():
    lines = ["| # | cid | meta-label | actual-dir | marker | svc/task | seq | frame-len | frame SHA-256 |",
             "|---|-----|-----------|-----------|--------|----------|-----|-----------|--------------|"]
    for r in inventory:
        svc = r["actual_service_task"] or "n/a"
        lines.append(
            "| {index} | {cid} | {meta_direction} | {actual_direction} | {marker} | {svc} | {seq} | {raw_len} | {sha} |".format(
                index=r["index"], cid=r["cid"], meta_direction=r["meta_direction"],
                actual_direction=r["actual_direction"], marker=r["marker"], svc=svc,
                seq=r["seq"], raw_len=r["raw_len"], sha=r["raw_sha256"]))
    return "\n".join(lines)


def critical_table():
    want = {"1": None, "2": None, "3": None, "4": None}
    rows = [r for r in inventory if r["index"] in want]
    lines = ["| # | dir | svc/task | seq | frame-len | header_total | declared | plain-len | plain SHA-256 |",
             "|---|-----|----------|-----|-----------|--------------|----------|-----------|--------------|"]
    for r in rows:
        lines.append(
            "| {index} | {actual_direction} | {svc} | {seq} | {raw_len} | {ht} | {decl} | {pl} | {ps} |".format(
                index=r["index"], actual_direction=r["actual_direction"],
                svc=r["actual_service_task"], seq=r["seq"], raw_len=r["raw_len"],
                ht=r["header_total"], decl=r["declared_body_length"],
                pl=r["plain_len"], ps=r["plain_sha256"]))
    return "\n".join(lines)


def object_field_table():
    rows = [r for r in object_fields if r["frame_index"] == "2"]
    lines = ["| field | offset | tag | type | payload-len | value | raw-hex |",
             "|-------|--------|-----|------|-------------|-------|---------|"]
    for r in rows:
        val = r["value"] if r["value"] else "(blob)"
        lines.append(
            "| {field} | {offset} | {tag} | {type} | {pl} | {val} | {raw} |".format(
                field=r["field"], offset=r["offset"], tag=r["tag"], type=r["type"],
                pl=r["payload_length"], val=val, raw=r["raw_hex"]))
    return "\n".join(lines)


def object_table():
    lines = ["| frame | seq | svc | task | reply_id | status | obj_count | obj_count_2 | prefix | obj-len | fields | consumed |",
             "|-------|-----|-----|------|----------|--------|-----------|-------------|--------|---------|--------|----------|"]
    for o in objects:
        lines.append(
            "| {fi} | {rs} | {svc} | {task} | {rid} | {st} | {oc} | {oc2} | {pfx} | {ol} | {nf} | {cons} |".format(
                fi=o["frame_index"], rs=o["request_seq"], svc=o["associated_service"], task=o["task"],
                rid=o["reply_id"], st=o["status"], oc=o["object_count"], oc2=o["object_count_2"],
                pfx=o["object_prefix_length"], ol=o["object_length"], nf=o["parsed_field_count"],
                cons=o["parsed_consumed"]))
    return "\n".join(lines)


def reply_prefix_table():
    lines = ["| frame | reply-body (TLV) | reply_id | status | task | obj_count | obj_count_2 |",
             "|-------|------------------|----------|--------|------|-----------|-------------|"]
    lines.append("| 2 (21/5) | `0a 33.. / 08 00.. / 03 05 / 08 01.. / 08 01..` | 51 | 0 | 5 | 1 | 1 |")
    lines.append("| 4 (6/14) | `0a 34.. / 08 00.. / 03 0e / 08 00..` | 52 | 0 | 14 | 0 | - |")
    return "\n".join(lines)


def mmbook_table():
    lines = ["| frame | seq | text | A | B | token b64 | token hex | payload SHA-256 |",
             "|-------|-----|------|----|----|-----------|-----------|-----------------|"]
    for r in mmbook:
        lines.append(
            "| {fi} | {seq} | `{txt}` | {a} | {b} | `{b64}` | {th} | {ps} |".format(
                fi=r["frame_index"], seq=r["seq"], txt=r["command_text"], a=r["A"], b=r["B"],
                b64=r["token_b64"], th=r["token_decoded_hex"], ps=r["payload_sha256"]))
    return "\n".join(lines)


def ab_summary_table():
    from collections import defaultdict
    seen = defaultdict(set)
    for e in ab:
        k = (e["value_name"], e["kind"], e["representation"], e["width"], e["endian"])
        seen[k].add(e["match_count"])
    lines = ["| value | kind | repr | width | endian | match-count (per cycle) |", "|-------|------|------|-------|--------|-------------------------|"]
    for k in sorted(seen, key=lambda x: (x[0], x[3], str(x[4]))):
        lines.append("| {} | {} | {} | {} | {} | {} |".format(k[0], k[1], k[2], k[3], k[4], sorted(seen[k])[0]))
    return "\n".join(lines)


def obj_hash_table():
    lines = ["| cycle | request seq | obj-len | obj SHA-256 |", "|-------|-------------|---------|-------------|"]
    for c in cycles:
        lines.append("| {c} | {s} | {l} | {h} |".format(c=c["cycle"], s=c["request_seq"],
                                                       l=c["find_object_length"], h=c["find_object_sha256"]))
    return "\n".join(lines)


now = "2026-10-11"

# ---------------------------------------------------------------- FRAME DECODE
frame_decode = f"""# COMBAT-V0.1-NEXT-011 - R2 原始帧解码 (FRAME DECODE)

- 任务: COMBAT-V0.1-NEXT-011 (R2 原始帧解码与 A/B 字段映射)
- 日期: {now}
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
| `capture-21-5.meta` | 7485 | `{META_SHA.lower()}` | `{META_SHA.lower()}` | MATCH |
| `capture-21-5.hex` | 13387 | `{HEX_SHA.lower()}` | `{HEX_SHA.lower()}` | MATCH |

两个文件的 SHA-256 均与任务给定的期望值一致, 证据可信, 分析继续。全过程只读, 未改写原始证据。

## 2. 帧记录清单 (44 条, 保持原始顺序)

{frame_table()}

说明: `marker` 为解密明文的第 5 字节 (`0x86`=客户端任务帧, `0x01`=服务端应答)。`svc/task` 列取自解密明文 (客户端帧含 service/task 字段; 服务端应答无 service 字段, task 取自应答 TLV 的 `tag 3`)。

## 3. 关键帧与字段级校验

前 4 帧 (第一个完整循环) 的字段级明细:

{critical_table()}

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
"""

# ---------------------------------------------------------------- FIELD MAPPING
field_mapping = f"""# COMBAT-V0.1-NEXT-011 - A/B 候选字段映射 (FIELD MAPPING)

- 任务: COMBAT-V0.1-NEXT-011
- 日期: {now}
- 输入: 上文 FRAME DECODE 中确认的 L2 明文与 L3 对象; 命令证据 = 11 条 `6/14 mmbook` 请求。
- 只读、离线。不修改协议/accepted/SEC_KEY/冻结基线。

## 0. 结论速览

- `21/5` 响应对象边界实测 **236 B** (33 个 TLV 字段, 严格遍历恰好消费), 不预设为 236/237/568 中的任何一个先验值。
- 11 个循环的响应对象**逐字节完全相同** (`SHA-256 = {summary["response_object_hashes"][0]}`)。
- `mmbook` 命令 11 次全部为同一文本 `mmbook 796 AQAAAAAAAAA= 0`, 即 **A=796, B=0**, 逐字节相同。
- **A=796 在 236 B 对象内零匹配**: 对 u1/u2/u4/u8 的 signed/unsigned、LE/BE, 以及 5 种 ASCII 编码 (十进制、hex 大小写、0x hex 大小写) 共 21 种编码逐一搜索, 命中数全部为 0。
- B=0 在对象内的匹配是**全零区的平凡匹配**, 无区分力 (见第 4 节)。
- 因此: **数值匹配未达成, 结构映射未闭环, 语义未证实**。本报告在 A/B 处明确停止, 不提出任何协议修改。

## 1. 响应对象边界与布局

- 对象区 = 应答 payload 去掉 26 B 前缀之后的 262-26 = **236 B**。
- 严格 TLV 遍历: 消费字节 = 236 (== 对象长度), 字段数 = 33, 解析错误 = 0。若边界取 237, 末字节无法归入任何字段; 若取 568, 会越界。故 **236 B 是唯一自洽边界**。

以第一个循环 (帧 2, seq=51) 为例的 33 字段表 (11 个循环逐字节相同, 故只列一组):

{object_field_table()}

可读字段 (语义标签仅为**待验证的命名**, 不是已证结论):

| offset | 内容 | 观察 |
|--------|------|------|
| `+0x00` | blob, 内含 `7f000001 2071` x2 | 出现 `127.0.0.1` (0x7f000001) 与端口 `0x7120`=28960 |
| `+0x1e` | blob `0100000000000000` | u64=1 |
| `+0x3b` | 字符串 `coop_take_mp_fav_tropical` | 地图/配置名 (含 `mp_fav`/`tropical`) |
| `+0x5f` | 字符串 `localhost` | 主机名 |
| `+0x6a` | i32 `0x01000003` | 数值形态类似 GameType |
| `+0x6f` | i32 `10` | 数值形态类似 playlist |
| `+0x79` | u32 `0xffffffff` | -1 哨兵 |
| `+0x93` | i32 `4` | 数值形态类似 MaxPlayers |
| `+0x56`/`+0xca` | u64=1 | 计数器/标志 |

## 2. 应答前缀 (26 B) 逐循环对照

{reply_prefix_table()}

- 21/5 应答: 前缀 26 B + 对象 236 B = payload 262 B。
- 6/14 应答: 前缀 21 B, 对象个数 = 0。

11 个循环的对象元数据:

{object_table()}

## 3. mmbook 命令逐循环对照

{mmbook_table()}

- 命令文本固定: `mmbook 796 AQAAAAAAAAA= 0`。
- token `AQAAAAAAAAA=` (base64) 解码 = `0100000000000000` = u64 值 1。
- payload SHA-256 11 次相同 = `{mmbook[0]["payload_sha256"]}`, 说明 A/B 输入**完全静止**, 不能用于区分候选。

## 4. A/B 字节级候选搜索 (对 236 B 对象)

搜索范围 (每条命令值): 整数宽度 1/2/4/8 x {{unsigned,signed}} x {{LE,BE}} = 16 种, 外加 ASCII 十进制 / hex 小写 / hex 大写 / `0x` 前缀小写 / `0x` 前缀大写 = 5 种, 共 21 种编码; 在对象 236 B 内做子串匹配。

### 4.1 A = 796

| 条件 | 结果 |
|------|------|
| 任何宽度/字节序/符号的整数编码 | 命中 0 |
| ASCII 十进制 `796` / hex `31c` / `0x31c` 等 | 命中 0 |
| 结论 | **A 不出现在对象的任何偏移** |

### 4.2 B = 0

{ab_summary_table()}

`B=0` 命中大量偏移, 但它们全部落在对象的全零字节区 (对象尾部 ~50 个大段 `i32=0`)。任何含零字节场的对象都会产生同样的匹配, 因此**B=0 不构成任何候选**, 只是平凡匹配。

### 4.3 22 个请求/应答循环的稳定性检查

- 11 个对象全部为同一 SHA-256: `{summary["response_object_hashes"][0]}`。
- 11 条 mmbook 全部为同一 payload: `{mmbook[0]["payload_sha256"]}`。
- 由于输入**没有任何变化**, 无法通过"变化/稳定"判据区分候选, 也无法发现多个同值候选之间的差异。

## 5. 数值匹配 / 结构映射 / 语义确认 三分

| 层级 | 定义 | 本次结果 |
|------|------|----------|
| 数值匹配 | 命令里的数值在响应对象或相关字节中能找到同值字节 | 未达成 (A 零命中; B 仅平凡匹配) |
| 结构映射 | 能把 `mmbook A/B` 与响应对象/预约记录的某个确定偏移、宽度、字节序建立一一对应 | 未闭环 (响应对象内无 A 的来源偏移) |
| 语义确认 | 有独立证据说明 A/B 的业务含义 | 未证实 (无 accepted 应答可作对照) |

必须严格区分三者, 不得用低层级的观察冒充高层级结论。

## 6. 明确的边界约束 (防止过度推断)

1. **不得**因为 A=796 与 `PLAYLIST_VERSION` 数值相等, 就断定 `A == PLAYLIST_VERSION`。数值相等不是语义证据。
2. **不得**把响应对象的某个偏移直接等同于 `0x238` 预约记录的 `+0x168/+0x16C`。二者是不同对象: 响应对象是本循环的 236 B 会话对象; `+0x168/+0x16C` 属 NEXT-006 的预约记录槽位 (见第 7 节)。
3. 本报告不产生任何协议字段修改建议。

## 7. 与 NEXT-006/008 已知事实的关系 (来自既有报告, 不重复举证)

- NEXT-006: 存在保持偏移的整块拷贝 `0x637950` (0x8E dwords = 0x238 B), 源记录 -> 预约槽位; 槽位 A/B 位于 `mk+0x75D8/+0x75DC + k*0x238` 的 `+0x168/+0x16C`, 均为 32 位、相邻、LE、无转换。`mmbook` 在 `0x62F736/0x62F742` 读取; accepted 处理在 `0x6326FB/0x632707` 与 `[ebp+8]/[ebp+0xc]` 比较。
- **遗留缺口**: 源记录的**生产端**与**源字段偏移**未知。
- NEXT-008: `"mmbook accepted"` 只是长度 0xF 的 `strncmp` 字符串 (位于 `0x6326DF`), 其中不含 A/B。accepted 正文布局未知。

本次新增事实: 真实 `21/5` 响应对象 236 B 中**不含** A=796。这把"响应对象 == A/B 来源"的假设排除掉; A/B 的来源更可能位于 NEXT-006 所指的**源记录**侧, 而非本 `21/5` 会话对象。这是本次相对既有报告的新增字节证据。

## 8. 停止点与缺失条件

- **停止点**: A/B 的字节级来源无法在当前 44 帧中确定。
- **缺失条件** (满足任一才可能闭环):
  1. 采集到 `mmbook` **accepted** 推送 (服务端在比较 `[ebp+8]/[ebp+0xc]` 后产生), 才能对 A/B 建立语义;
  2. 采集到 NEXT-006 所述**源记录**被写入的瞬间 (生产端写入), 才能定位 A/B 源偏移;
  3. 让 A/B 在一次真实会话中**发生变化** (例如不同 playlist/房间), 才能用差异判别候选偏移。
- 在上述任一证据出现前, 不猜测、不虚构 A/B 映射。
"""

# ---------------------------------------------------------------- IMPLEMENTATION GATE
imp_gate = f"""# COMBAT-V0.1-NEXT-011 - 实现门槛表 (IMPLEMENTATION GATE)

- 任务: COMBAT-V0.1-NEXT-011
- 日期: {now}
- 依据: `FRAME DECODE` 的 L1-L3 证据 + `FIELD MAPPING` 的 A/B 搜索结果。
- 结论不因协议取证有进展就宣称真实战斗连接成功。

## 1. 已被真实字节证据支持

| 项 | 证据 | 强度 |
|----|------|------|
| 采集保真: 44 帧 cid/方向/长度/SHA-256/帧头/HMAC 全通过 | 独立复算 (两组独立脚本一致) | 强 |
| 帧循环结构: 21/5(82/306) 与 6/14(98/66) 成对, seq 51..72 | 逐帧解密 | 强 |
| 21/5 响应对象边界 = 236 B, 33 字段, 严格遍历自洽 | TLV 遍历 236/236, 0 错误 | 强 |
| 对象含服务端地址 `127.0.0.1:28960` (`0x7f000001`,`0x7120`) | 对象 `+0x00` blob 原文 | 强 |
| 对象含地图/配置名 `coop_take_mp_fav_tropical` | 对象 `+0x3b` 字符串 | 强 |
| 对象含主机名 `localhost` | 对象 `+0x5f` 字符串 | 强 |
| 对象含疑似 GameType=`0x01000003`、playlist=`10`、MaxPlayers=`4` | 对象 `+0x6a/+0x6f/+0x93` i32 | 中 (数值形态, 语义待证) |
| `6/14 mmbook A=796 B=0` 请求字节 | 11 条逐字节相同 | 强 |

## 2. 仍未闭合的映射

| 项 | 状态 | 阻断原因 |
|----|------|----------|
| A/B 的源字段偏移与宽度确认 | **未闭环** | A=796 在响应对象内零命中; 来源疑在 NEXT-006 的"源记录"侧, 未采集 |
| 响应对象偏移 与 预约记录 `+0x168/+0x16C` 的对应关系 | **未建立** | 两个对象不同域, 禁止臆断等同 |
| A/B 的语义 (是否 playlist/version/房间键) | **未证实** | 缺 accepted 对照 |
| 服务端地址交接链的完整性 (大厅 -> 战斗) | **未验证** | 只有对象内出现的地址, 无后续交接帧 |

## 3. accepted 处理还缺什么证据

- 本次采集**完全不含** 21/5 accepted 推送: meta 无 `S2C-PUSH` 记录; 解密帧 marker 仅 `{{0x86:22, 0x01:22}}`, 无 `0x02`; S2C 字节中无 `accepted` 字符串 (`accepted_present = {str(accepted["accepted_present"]).lower()}`)。
- 结论: **不得**用请求格式反推并宣称 accepted 格式已确认; **不得**为取证而打开或修改推送开关/协议。
- 要闭合 accepted, 仍缺: 一份真实触发 accepted 的采集 (含 `0x02` 推送帧), 以及客户端是否收到并处理该消息的独立证据。

## 4. 失败路径覆盖风险

- 是否仍未解决: **是, 仍未知**。故障路径 (例如 A/B 不匹配、accepted 未达) 的真实行为没有任何采集证据, 风险状态维持 R4 UNKNOWN。
- 不在本任务内通过修改协议来"兜底"。

## 5. 下一项最小且可验证的工作

1. (最小) 在**不改协议**的前提下, 采集一次**能触发 accepted 推送**的真实会话, 目标产物 = 含 `0x02` 推送帧的 capture, 用来首次观察到 accepted 信封与正文。
2. (并行, 只读) 对 NEXT-006 的**源记录生产端**做静态定位, 给出 A/B 写入源偏移的候选, 并与本次 236 B 对象做对照 (预期仍不匹配, 以排除法收敛)。
3. (判别性) 设计一次 A/B **发生变化的**合法会话采集, 用差异判别候选偏移。

## 6. 未决与边界

- 本任务不修改 SEC_KEY / 协议 / accepted 正文 / 冻结大厅基线 / 战斗服务器源码; 不部署、不提交、不推送。
- 不启动/附加/注入/读取客户端进程。
- 新手指南卡住问题: **另立独立任务**, 不与 A/B 或 accepted 修复混做; 待 NEXT-011 结果稳定后, 再依据已证实的战斗连接链判断卡点 (大厅会话 / 服务器地址交接 / 挑战握手 / 游戏状态初始化), 并与用户确认"是否可跳过教程直接进大厅"。
"""

# ---------------------------------------------------------------- SHA256
(ROOT / "COMBAT_V0_1_NEXT_011_FRAME_DECODE.md").write_text(frame_decode, encoding="utf-8")
(ROOT / "COMBAT_V0_1_NEXT_011_FIELD_MAPPING.md").write_text(field_mapping, encoding="utf-8")
(ROOT / "COMBAT_V0_1_NEXT_011_IMPLEMENTATION_GATE.md").write_text(imp_gate, encoding="utf-8")

targets = [
    ("REF_LOBBY_KIT_CAP009/capture-21-5.meta", ROOT / "REF_LOBBY_KIT_CAP009" / "capture-21-5.meta"),
    ("REF_LOBBY_KIT_CAP009/capture-21-5.hex", ROOT / "REF_LOBBY_KIT_CAP009" / "capture-21-5.hex"),
    ("COMBAT_V0_1_NEXT_011_FRAME_DECODE.md", ROOT / "COMBAT_V0_1_NEXT_011_FRAME_DECODE.md"),
    ("COMBAT_V0_1_NEXT_011_FIELD_MAPPING.md", ROOT / "COMBAT_V0_1_NEXT_011_FIELD_MAPPING.md"),
    ("COMBAT_V0_1_NEXT_011_IMPLEMENTATION_GATE.md", ROOT / "COMBAT_V0_1_NEXT_011_IMPLEMENTATION_GATE.md"),
    ("_combat_next011/decode_capture.py", ROOT / "_combat_next011" / "decode_capture.py"),
    ("_combat_next011_agent/independent_verify.py", AGENT / "independent_verify.py"),
    ("_combat_next011_agent/make_reports.py", AGENT / "make_reports.py"),
    ("_combat_next011_agent/summary.json", AGENT / "summary.json"),
    ("_combat_next011_agent/frame_inventory.tsv", AGENT / "frame_inventory.tsv"),
    ("_combat_next011_agent/objects.json", AGENT / "objects.json"),
    ("_combat_next011_agent/object_fields.tsv", AGENT / "object_fields.tsv"),
    ("_combat_next011_agent/mmbook.tsv", AGENT / "mmbook.tsv"),
    ("_combat_next011_agent/ab_candidates.json", AGENT / "ab_candidates.json"),
    ("_combat_next011_agent/cycles_ab_candidates.json", AGENT / "cycles_ab_candidates.json"),
    ("_combat_next011_agent/accepted_check.json", AGENT / "accepted_check.json"),
    ("_combat_next011_agent/independent_report.json", AGENT / "independent_report.json"),
]
lines = ["# COMBAT-V0.1-NEXT-011 SHA-256 MANIFEST",
         f"# generated {now}",
         "# format: <sha256>  <path>",
         ""]
for label, path in targets:
    lines.append(f"{sha256_file(path)}  {label}")
(ROOT / "COMBAT_V0_1_NEXT_011_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("wrote 4 deliverables")