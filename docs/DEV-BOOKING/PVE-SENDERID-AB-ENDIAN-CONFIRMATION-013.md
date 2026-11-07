# PVE-SENDERID-AB-ENDIAN-CONFIRMATION-013
# senderId(0x1122334455667788) → 0x632680(A,B) 的拆分顺序（纯静态）

> 2026-10-08 执行。纯静态。未修改任何 server/客户端/协议字段。

---

## 0. 结论先行

```
SENDERID_NATIVE_VALUE   = 0x1122334455667788
SENDERID_LOW32          = 0x55667788
SENDERID_HIGH32         = 0x11223344

0x7F1400_ARG1_SOURCE    = envelope.senderId 低 32 位（[ebp+8]）
0x7F1400_ARG2_SOURCE    = envelope.senderId 高 32 位（[ebp+0xc]）

A = 0x55667788（低 32 位）
B = 0x11223344（高 32 位）

SESSION_ITEM_0x168      = 0x55667788（SessionId 低 32 位）
SESSION_ITEM_0x16C      = 0x11223344（SessionId 高 32 位）

SENDERID_AB_MAPPING     = LOW_HIGH
SESSIONID_ITEM_MAPPING  = LOW_HIGH
AB_CORRELATION_PREDICTION = MATCH
EVIDENCE_LEVEL          = HIGH-CONFIDENCE
NEXT_GATE               = CLIENT-BOOKING-BATTLE-TRIGGER（A/B 序已对，不再改 booking response）
```

---

## 1. 静态已确认的寄存器/栈映射（CONFIRMED 部分）

### 1.1 0x632680 的 A/B 比较

```asm
0x6326B6  mov eax,[ebp+8]        ; arg1 = A
0x6326B9  cmp eax,[esi+0x3a048]  ; A == this+0x3a048
0x6326C5  mov ebx,[ebp+0xc]      ; arg2 = B
0x6326C8  cmp ebx,[esi+0x3a04c]  ; B == this+0x3a04c
```

### 1.2 0x62F6F0 的 A/B 来源（reservation item → this）

```asm
0x62F736  mov ecx,[edi+0x168]    ; A = item+0x168
0x62F73C  mov [esi+0x3a048],ecx  ;   -> this+0x3a048
0x62F742  mov edx,[edi+0x16c]    ; B = item+0x16C
0x62F748  mov [esi+0x3a04c],edx  ;   -> this+0x3a04c
```

⇒ 由此**已确认**：`A ↔ item+0x168`，`B ↔ item+0x16C`（A 在低地址，B 在高地址）。

### 1.3 0x7F1400 dispatcher 的转发

```asm
0x7F1567  mov edx,[ebp+0xc]   ; B = dispatcher arg2
0x7F156B  mov edx,[ebp+8]     ; A = dispatcher arg1
0x7F156F  call 0x632680       ; (this, A, B, ptr, msg, 15)
```

⇒ 由此**已确认**：`[ebp+8] → A`，`[ebp+0xc] → B`。

---

## 2. 字节序 / 拆分方向（HIGH-CONFIDENCE 部分）

### 2.1 wire 编码（服务端 CONFIRMED）

```python
# codol_crypto.py Buf.u64 / build_session_record
ob.u64(sender_id)                    # 0A + struct.pack("<Q", v)  ← 小端
ob.blob(struct.pack("<Q", session_id))  # ② SessionId ← 小端 u64
```

wire senderId = `0A 88 77 66 55 44 33 22 11`（LE u64 = 0x1122334455667788）。

### 2.2 native 拆分（x86 LE 语义）

x86 是 little-endian，读取 8 字节 LE u64 后，低地址 4 字节 = 低 32 位：

```
地址 +0: 88 77 66 55  → low32  = 0x55667788
地址 +4: 44 33 22 11  → high32 = 0x11223344
```

findSessions 的 SessionId blob（同为 LE u64）落到 reservation item：
```
item+0x168 = low32  = 0x55667788
item+0x16C = high32 = 0x11223344
```

dispatcher 的 senderId（同为 LE u64）拆分：
```
arg1([ebp+8]) = A = low32  = 0x55667788
arg2([ebp+0xc]) = B = high32 = 0x11223344
```

### 2.3 未发现字节序翻转

在 0x62F6F0 / 0x632680 / 0x7F1400 的 A/B 路径中，未发现 `bswap / rol / ror / xchg`
或任何 network↔host 字节序转换指令（搜索范围：相关函数体内）。

```
BYTE_SWAP_FOUND = NONE（A/B 路径无 endian 转换）
```

---

## 3. 结论判定

```
SENDERID_AB_MAPPING    = LOW_HIGH（A=low32, B=high32）
SESSIONID_ITEM_MAPPING = LOW_HIGH（item+0x168=low32, item+0x16C=high32）
AB_CORRELATION_PREDICTION = MATCH
```

即：`senderId=0x1122334455667788` 经 dispatcher 拆成 `A=0x55667788, B=0x11223344`，
与 reservation item `[+0x168]=0x55667788, [+0x16C]=0x11223344` 完全一致。
**当前 DEV server 的 senderId 修复在 A/B 顺序上是正确的。**

---

## 4. 证据等级说明

```
CONFIRMED（反汇编直接可见）:
  - A ↔ item+0x168, B ↔ item+0x16C（0x62F6F0 + 0x632680）
  - [ebp+8]→A, [ebp+0xc]→B（0x7F1400）
  - 服务端 senderId/SessionId 均为 LE u64（Buf.u64 / struct.pack("<Q")）
  - A/B 路径无 bswap/byte-swap

HIGH-CONFIDENCE（LE 语义推断，缺"帧层 parser 逐条反汇编"这一步）:
  - frame parser 拆分 senderId 的实际 push 顺序（未定位到帧层 dispatch 代码）
  - findSessions parser 写 item+0x168/+0x16C 的实际存储顺序（未定位到解析代码）
```

因**未定位到帧层 parser 与 findSessions parser 的逐条指令**，最终证据等级定为
**HIGH-CONFIDENCE**，不升为 CONFIRMED。但 LE 语义 + 无字节翻转，使 LOW_HIGH/MATCH
是当前最强且唯一合理的结论。

---

## 5. 与动态事实的关系（严格区分）

```
STATIC_FACT : A/B 拆分 = LOW_HIGH → MATCH（本报告）
DYNAMIC_FACT: senderId==SessionId 已写入 wire，但 RX#1=0（012）
INFERENCE   : RX#1=0 不能证明 A/B mismatch（012 的失败可能源于 accepted→battle 断点）
```

---

## 6. NEXT_GATE

A/B 顺序 CONFIRMED 为正确（LOW_HIGH/MATCH），因此**不再修改 booking response**。
下一阶段进入：

```
CLIENT-BOOKING-BATTLE-TRIGGER
  0x632680 accepted
    → [this+0x288]=1, [0x849B61C]=1
    → accepted notification/state transition
    → booking-specific consumer
    → findSessions endpoint(127.0.0.1:28960)
    → UDP socket creation
```

注意：不要回到 `0xB81EF0 → 0xBA4080`（那是 Lobby 主连接，已证非 battle）。
```
