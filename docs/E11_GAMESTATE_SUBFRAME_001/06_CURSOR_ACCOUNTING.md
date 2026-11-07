# 06 — 游标记账 / CURSOR ACCOUNTING

> 全部为 DIRECT，除标注处。位偏移从服务端 `0x04` 首位起算。

---

## 1. 服务端写入游标（DIRECT）

msg 结构：`[+0]=buf`，`[+4]=used(字节)`，`[+8]=cap`，`[+0x10]=bitpos`，`[+0x14]=overflow`。

| 写入 | 位置 | 字节增量 | bitpos 行为 |
|---|---|---|---|
| bitpos 归零 | `0xA07E6` | — | `[+0x10]=0` |
| `WriteByte(4)` | `0xA07F8` | +1 | 8 bit 写 |
| `WriteShort(count1)` | `0xA0807` | +2 | 16 bit 写 |
| A1 字符串 | `0x99651` | +len+1 | **不更新 bitpos** |
| A2/A3 位字段 | `0x99590` | 视内容 | 位推进，边界重同步 |
| `WriteByte(6)` | `0xA0997` | +1 | 8 bit 写 |

**重同步规则（DIRECT，`0x9960A`）：** `bitpos % 8 == 0` 时 `bitpos = used*8`，随后 `used++` 并追加 0 字节。

**A1 不占位（DIRECT）：** `WriteLenStr` `0x99651` 内无 `[msg+0x10]` 写入（脚本自检结果 `False`）。

## 2. 累计位模型（服务端，count1=16）

| 场景 | 0x06 起始 bitpos | 模 8 |
|---|---|---|
| A1=A2=A3 空 | 44 | 4 |
| A1=[(0,'')] | 53 | 5 |
| A1=[(0,'a')] | 61 | 5 |
| A1=[(0,'a')], A2=[(0,1)] | 72 | 0 |
| 完整示例 | 129 | 1 |

**结论：** `0x06` 起始位置**依输入变化**，不保证字节对齐。

## 3. 客户端读取游标（DIRECT）

| 操作 | 位置 | 游标变化 |
|---|---|---|
| `MSG_InitReadOnly` | `0x1AC190` | `[+0x14]=0`（offset）、`[+0x1C]=0`（pos） |
| `MSG_ReadData(msg,dst,2)` | `0x1AC1D0` | 逐字节读，`pos += len` |
| `MSG_ReadBits(msg,bits)` | `0x1AC670` | 用 `[+0x20]` bitpos；`and 7`/`sar 3` |
| `0x352FA1` | `0x352F80` | `pos += 1`（跳过子帧头） |
| case 6 外层读 | `0x3546D4` | 读 4 字节 `LEN` |
| case 6 载荷读 | `0x3546EE` | 读 `LEN` 字节 |

**`MSG_ReadBits` 结构（DIRECT）：** 使用 `[msg+0x20]` 作 bitpos（不是 `[+0x10]`），说明客户端 MSG 结构与服务端 msg 结构**布局不同**，不能直接套用服务端字段偏移。

## 4. 两侧游标对照（CROSS）

| 阶段 | 服务端字节 | 客户端字节 |
|---|---|---|
| 子帧头 | `0x04` = 1 | `0x352FA1` 跳过 1 |
| count1 | 2 | `MSG_ReadData` 2 |
| A1 | 索引位 + 字符串字节 | `MSG_ReadBits` + NUL 扫描 |
| A2 | 11/13/10 bit | 同 |
| A3 | 10/7/4/n×12 bit | 同 |
| 子帧尾 | `0x06` = 1 | **未定位** |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 服务端位记账可复算 | **PROVEN** |
| 客户端读取游标推进 | **PROVEN**（除 0x06） |
| 两侧 count1/A1/A2/A3 对齐 | **CROSS** |
| 子帧尾游标 | **BLOCKED** |
| 客户端 MSG 与服务端 msg 同布局 | **REFUTED**（bitpos 偏移 `+0x20` vs `+0x10`） |
