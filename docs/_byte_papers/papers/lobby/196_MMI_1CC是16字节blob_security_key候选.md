# 196 · `MMI+0x1CC` = 16 字节 blob（`security_key` 强候选）—— blob#3 结构完全对

> 卷次：196（房间类 · 195 卷结论的字段级确认）
> 结论：`0x806F20` 用 `0xB76AF0`（tag 0x13 blob 读器）读 `[esi+0x1CC]`，容量 `0x10` = **16 字节**。

---

## §0 直接证据

```asm
0x807020  mov dword [ebp-4], 0x10        ; ★ 容量 = 16
0x807033  lea eax, [ebp-4] / push
0x807037  lea ecx, [esi + 0x1CC]         ; ★ 目标 = MMI+0x1CC
0x80703E  mov ecx, [ebp+8]
0x807041  call 0xB76AF0                  ; ★ blob 读器（tag 0x13）
```

`0xB76AF0` 内部：
```asm
0xB76AF5  push 0x13 / call 0xB76310      ; 读 tag 0x13
0xB76B11  call 0xB761E0                  ; 读 8 位长度
0xB76B26  mov edx, [ebp+0xC]             ; 容量指针
0xB76B29  mov eax, [edx]                 ; = 16
0xB76B2B  cmp eax, esi / jb              ; min(16, 声明长度)
```

★★★ **`MMI+0x1CC` = 一个最多 16 字节的 blob。**

---

## §1 与 `dwRoomMessageStartGame` blob#3 的完全对应

| 项 | `0x625BE0` serialize | `0x806F20` MMI serialize |
|---|---|---|
| 目标偏移 | `[this+8]+0x1CC` = **MMI+0x1CC** | `[esi+0x1CC]` = **MMI+0x1CC** |
| 长度 | `W_VAL(0x10, 32)` = **16** | `mov [ebp-4], 0x10` = **16** |
| 编码 | `W_TAG(19) + W_TAG(8) + W_VAL(32,16) + W_VAL(128)` | `0xB76AF0` → `tag 0x13 + 8位长度 + 数据` |

★★ **两者是同一个字段的两种编码视图：**
- `0x625BE0`（StartGame 消息内）：`tag19 + tag8 + len + data`
- `0x806F20`（MMI 自身）：`tag0x13 + len + data`

★ 编码不同（A 路径 5 位标签 / B 路径 1 字节 tag），但**目标字段和长度完全一致**。

---

## §2 `security_key` 的确认度

| 证据 | 强度 |
|---|---|
| 长度 = 16 字节（`0x10`） | ✅ 与 `security_key` 完全一致 |
| 是 `MatchMakingInfo` 的正式字段（`0x806F20` 读） | ✅ |
| 163 卷：`security_key` 是 ECDH 派生的 16 字节 | ✅ 长度吻合 |
| `0x625BE0` 里 `W_VAL(128)` = 128 位 = 16 字节 | ✅ |

★★ **强候选：`MMI+0x1CC` = `security_key`。**
但**不能 100% 断言** —— 也可能是别的 16 字节字段（GUID / session token）。

---

## §3 `build_startgame_payload` 的正确性评估

```python
w.write_blob(addr_67)                              # blob#1 → MMI+0x18（低区不透明）  ⚠️
w.write_blob(struct.pack("<Q", session_id_int))    # blob#2 → MMI+0x10（低区不透明）  ⚠️
w.write_blob(security_key_16)                      # blob#3 → MMI+0x1CC（正式字段）   ✅
```

| 段 | 结构 | 内容 |
|---|---|---|
| #1 | ✅ 格式对（tag19/tag8/len/data） | ⚠️ 67 字节 `bdCommonAddr` vs 客户端期望的 256B 缓冲 |
| #2 | ✅ 格式对（8 字节 / 64 位） | ⚠️ session_id vs MMI+0x10 的真实内容 |
| **#3** | ✅ **格式 + 长度都对** | ✅ **`security_key` 强候选** |

★★ **三段格式全部正确，两段内容不确定。**

---

## §4 剩余两个低区字段的推断

### 4.1 `MMI+0x10`（blob#2，64 位）

MMI 低区 POD 字段。64 位。可能：
- session id（u64）
- 时间戳
- 玩家 ID

★ `build_startgame_payload` 传 `session_id`（u64），**结构吻合**。

### 4.2 `MMI+0x18`（blob#1，256 字节缓冲，长度 `MMI+0x118`）

★★ **`0x118 - 0x18 = 0x100 = 256`** —— 这是一个**自描述长度的 256 字节缓冲**。

可能：
- `bdCommonAddr`（67 字节）+ 填充
- 或别的地址结构

★ `build_startgame_payload` 传 67 字节 `bdCommonAddr`，**长度可能对**（若真实长度就是 67）。

---

## §5 本卷确定结论

| 项 | 状态 |
|---|---|
| `MMI+0x1CC` = 16 字节 blob | ✅ |
| `0x806F20` 用 `0xB76AF0` 读它 | ✅ |
| 与 StartGame blob#3 完全对应 | ✅ |
| `MMI+0x1CC` = `security_key` | ★ **强候选**（长度+语义） |
| `MMI+0x10` = 64 位（session_id 候选） | ★ 中 |
| `MMI+0x18` = 256B 缓冲（长度在 +0x118） | ✅ |
| 三段格式全部正确 | ✅ |

---

## §6 下一步

1. **`MMI+0x10` 的写入者**（找 `[reg+0x10]` 在 MMI 区的写点，但注意 `0x10` 极常见，需按 func 筛）
2. **`MMI+0x18` 的写入者**（同上）
3. **`0x806F20` 读 `+0x128`（第一个字段）是什么** —— 可能是 `bdCommonAddr`

---

## §7 方法论

1. **★★★ 同一个字段在两个类里用不同编码时，用"目标偏移 + 长度"对账，比用编码对账可靠。**
2. **★★ `lea ecx,[esi+0x1CC]` + `push 0x10` + `call <blob读器>` 三连，是"读一个 16 字节 blob"的标准形态。**
3. **★★ 低区字段（`+0x10`/`+0x18`）虽不被 MMI 序列化，但可被其他消息类借用 —— 这是"透传字段"的常见设计。**
4. **★★ 服务端能确认的是"格式"，不能确认的是"内容" —— 后者需要真实样本。**
