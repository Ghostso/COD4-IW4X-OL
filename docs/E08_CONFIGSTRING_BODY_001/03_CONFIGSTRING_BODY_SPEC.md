# 03 — Configstring Body 规格 / CONFIGSTRING BODY SPEC

> 等级：`DIRECT`（指令级）/ `CROSS`（与既有报告一致）/ `INFERRED`（语义推断）/ `BLOCKED`
> 全部字段宽度与顺序均来自 `_CODOL2697_WriteConfigstrings`（RVA 0xA0468）的**指令**。

---

## 1. 消息总布局（DIRECT）

```
+----------------------+----------------------------------------+
| 0x04                 | WriteByte(4)                @ RVA 0xA07F8 |
| <count-field>        | WriteShort(count1)          @ RVA 0xA0807 |  ← 见 §3 冲突
| <A1 组>              | 第一组（字符串表）                       |
| <A2 组>              | 第二组（索引+10bit 值）                  |
| <A3 组>              | 第三组（定长记录数组）                   |
| 0x06                 | WriteByte(6)                @ RVA 0xA0997 |
+----------------------+----------------------------------------+
```

**注意（DIRECT）：** `0x04` 与 `0x06` 是**普通字节写**（`WriteByte`，即 `WriteBits(...,8)`），不是位字段。它们是**先于/后于**位字段而写的整字节，但由于位写入按 LSB-first 共享同一缓冲区，**若前序位字段未按字节对齐，`0x06` 会落在非字节边界上**。

**关键推论（INFERRED）：** `0x06` 的写点是 `WriteByte(6)`（8 位），其**起始位偏移取决于前面三组的位长总和**。因此 `0x06` **不保证**出现在字节边界，这与"内部 `0x06` 是子记录标记"的既有观察一致 —— 它是**位流中的 8 位常量**，不是"整字节 0x06"。

## 2. 三组字段规格（DIRECT）

### 2.1 第一组 A1 — 字符串表

```
count1 : 8 bits                       (位长由注释字符串 "* %u" 佐证；见 §3)
repeat count1 times:
    index_delta : 变长（1 或 1+13=14 bits）
    strlen_plus_1 : 8 bits  ...  （0x99651 先 strlen 再 +1，随后按字节写）
    data : (strlen_plus_1) bytes（含 NUL）
```

| 项 | 值 | 等级 |
|---|---|---|
| 索引编码 | 连续→`1`(1bit)；否则→`0`+13bit | DIRECT |
| 首索引 | `lastIdx=-1` ⇒ 索引 0 仅 1 bit | DIRECT |
| 索引范围 | `≤ 0x1DD6`（0x1DD7 为 sentinel/跳过） | DIRECT |
| 索引去重 | `seen[]` 表；重复 → 失败返回 0 | DIRECT |
| 索引合法区间 | 在 0..0x13（跳过 0x12）的区间表内校验 | DIRECT |
| 字符串长度上限 | `0x1FFF`（8191）；超出 → 失败 | DIRECT |
| 字符黑名单 | `0x25`(`%`)、`0x92` → 失败 | DIRECT |
| 字符串终止 | `strlen+1` 字节（**含 NUL**） | DIRECT |
| 字符串写入位对齐 | 逐字节（`WriteData`），**不**强制字节对齐 | DIRECT |

### 2.2 第二组 A2 — 索引 + 10 位值

```
count2 : 10 bits
repeat count2 times:
    index_delta : 变长（同 §2.1）
    value       : 10 bits
```

| 项 | 值 | 等级 |
|---|---|---|
| 记录步长（描述符） | 8 字节（`[base + i*8]` 索引 / `+4` 值） | DIRECT |
| 计数位长 | **10** | DIRECT |
| 值位长 | **10** | DIRECT |
| 索引上限校验 | `≤ 0x1DD6`，去重，同 §2.1 | DIRECT |
| 无字符串 | — | DIRECT |

### 2.3 第三组 A3 — 定长记录数组

```
count3 : 10 bits
repeat count3 times（记录步长 0x4C）:
    index_delta      : 变长（同 §2.1）
    field_A          : 10 bits      （记录 +0x04）
    field_B          :  7 bits      （记录 +0x08）
    n                :  4 bits      （记录 +0x0C）
    extras           : n × 12 bits  （记录 +0x10 + k*4）
```

| 项 | 上限校验（DIRECT） |
|---|---|
| `field_A` | `≤ 0x3FF`（10 位） |
| `field_B` | `≤ 0x7F`（7 位） |
| `n` | `≤ 0xF`（4 位） |
| `extras[k]` | `≤ 0xFFF`（12 位） |
| 索引 | `≤ 0x1DD6`，去重 |

## 3. 计数位长冲突（必须保留）

| 侧 | 说法 | 依据 |
|---|---|---|
| 本轮实测 | `count1` 由 **`WriteShort`（2 字节 = 16 位）** 写入 | `0xA0807: call 0x499566`；`0x99566` 内 `mov ecx,2` |
| 内联注释串 | `"* %u"` / `"** %u %u"` 暗示 **8 位** | 字符串 @ VA 0x7C0A00 / 0x7C0A05 |
| 既有 E1 报告 | `count` 为 **u16（little-endian）** | E1 `configstring` 段 |

**裁定：** `DIRECT` 证据（`mov ecx,2`）支持 **16 位（2 字节）**；注释串可能属于**另一处同类写入**（例如 payload 位计数），不应据此覆盖指令证据。
**状态：`CROSS` 冲突已登记**（`06` §2），本轮以**指令级 16 位**为准，但**不删除**其他说法。

## 4. 失败语义（DIRECT）

任一前置/逐项校验失败时，函数执行：

```asm
0A04D2  mov dword [edi+0x14], 1     ; msg->overflow = 1
0A04D9  mov eax, 0                  ; 返回 0
```

即：**置 msg 溢出标志 + 返回 0**，**不**做部分回滚、**不**重试、**不**降级。调用方须以返回值为准（0 = 未发布）。

## 5. 终止语义（DIRECT + INFERRED）

| 项 | 结论 | 等级 |
|---|---|---|
| `0x06` 由 `WriteByte(6)` 产生 | 是 | DIRECT |
| `0x06` 出现在位流（可能非字节对齐） | 是（取决于前三组位长） | INFERRED |
| `0x04`/`0x06` 是"configstring 上下文"的外层标识 | 与既有观测一致（新通道 `04…06`） | CROSS |
| `0x06` 在**其它**上下文（gamestate 尾 / snapshot 内部）语义相同 | **不得假定** | 任务约束 3 |

**强制声明：** 本报告**不**主张 `0x06` 在 configstring、gamestate、snapshot 之间语义相同。三者的写入点不同（0xA0997 / 0xA22F8 / 0xA4CAF 与 0x87104），须分别验证。

## 6. Body 规格摘要（可直接实现）

```
04                          # 1 byte
count1                      # 2 bytes (LE)  [16 bits]
A1: count1 x { indexdelta; u8 len1; len1 bytes }
A2: 10-bit count2; count2 x { indexdelta; u10 value }
A3: 10-bit count3; count3 x { indexdelta; u10; u7; u4 n; n*u12 }
06                          # 8 bits
```

其中 `indexdelta = 1bit(1)` 若 `idx == last+1`，否则 `1bit(0) + 13bit(idx)`；`last` 初值 `-1`；每条记录后 `last = idx`。

**注意：** 上述是**服务端写入顺序**。客户端**读取顺序是否相同**，本轮**未能**从客户端侧独立证实（见 `04`/`06`）。