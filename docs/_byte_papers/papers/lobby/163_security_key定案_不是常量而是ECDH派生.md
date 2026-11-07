# 163 · `security_key` 定案：它不是常量，是**双方协商出来的一段字节**

> 卷次：163（大厅↔战斗服交接 · 收掉 162 卷最后一个待查项）
> 起因：162 卷留了「客户端期望 `security_key` 是 `0x00…` 还是 `0x01…`」。
> 结论：**这个问法本身是错的。它两边都不是常量。**

---

## 一、直接回答

| 162 卷的疑问 | 本卷答案 |
|---|---|
| 客户端期望 `security_key = 0x00…` 还是 `0x01…`？ | **都不是**。它在客户端是**从 ECDH 共享秘密派生的运行时数据** |
| 那战斗服写死 `0x01` 对不对？ | **不对**，但原因不是「值错了」，是「**它不该是常量**」 |
| 大厅写 `0x00` 有没有用？ | **没用**：那个文件没人读，且值本身也不对 |

---

## 二、客户端侧证据（逐指令）

### 2.1 `BDDATA` 的完整调用上下文

`0xBA1F60` — `0xBA1F76`（`0xBA1850` 函数内）：

```asm
0xBA1F60  push 0x48                 ; 输出缓冲大小 72
0xBA1F62  lea ecx,[ebp-0xA8]        ; 输出缓冲
0xBA1F68  push ecx
0xBA1F69  push 6                    ; 标签长度 6
0xBA1F6B  push 0xD5A4E0             ; ★ "BDDATA"
0xBA1F70  lea edx,[ebp-0x4C]        ; ★★ 输入缓冲（20 字节）
0xBA1F73  push 0x14                 ; 输入长度 20
0xBA1F75  push edx
0xBA1F76  call 0xBA13D0             ; KDF
```

### 2.2 `[ebp-0x4C]` 从哪来 —— **这是关键**

全函数只有 **3 处** 引用 `[ebp-0x4C]`：

```
0xBA1E88  lea ecx,[ebp-0x4C]        ← 写入（作为输出参数）
0xBA1EEC  lea edx,[ebp-0x4C]        ← 读（给 CLIENTCHAL KDF 当输入）
0xBA1F70  lea edx,[ebp-0x4C]        ← 读（给 BDDATA KDF 当输入）
```

写入点是 `0xBA1E88`，上下文：

```asm
0xBA1E72  push 0                    ; 参数
0xBA1E74  lea eax,[ebp-0x38]
0xBA1E77  push eax
0xBA1E78  mov ecx,ebx
0xBA1E7A  call 0xBA0750             ; 前置步骤
0xBA1E88  lea ecx,[ebp-0x4C]        ; ★ 输出缓冲
0xBA1E8B  push ecx
0xBA1E8C  push 0x18                 ; ★ 输出长度 24（32 字节？0x18=24）
0xBA1E8E  lea edx,[ebp-0x38]        ; 输入
0xBA1E91  push edx
0xBA1E92  lea eax,[ebp-0x60]
0xBA1E95  push eax
0xBA1E96  call 0xBA0D20             ; ★★★ 产生 [ebp-0x4C]
```

### 2.3 `0xBA0D20` 是什么

```asm
0xBA0D20  jmp 0x16320000            ; ★ VMProtect thunk（首字节 E9）
...
0xBA0D57  push 0x14                 ; 20 字节
0xBA0D59  push eax
0xBA0D5A  lea ecx,[ebp-0x348]
0xBA0D60  call 0xC73800             ; ★ EC 点/标量初始化
0xBA0D75  call 0xC73760             ; ★ EC 运算
0xBA0D9B  call 0xC737A0             ; ★ EC 输出
0xBA0DB3  call 0xC73750             ; ★ EC 清理
```

**⇒ 这是一个 EC（椭圆曲线）秘密计算函数**，与战斗服的 `codol_p224_*`（P-224）**同构**。

**结论：`[ebp-0x4C]` = ECDH 共享秘密（28 字节前段 / 0x14 的 20 字节部分）。**

### 2.4 两次 KDF 都用它

```asm
0xBA1EE7  push 0xD5A4E8   ; "CLIENTCHAL"
0xBA1EEC  lea edx,[ebp-0x4C]
0xBA1EF2  call 0xBA13D0   ; KDF(shared, "CLIENTCHAL", 10, out16, 0x10)

0xBA1F6B  push 0xD5A4E0   ; "BDDATA"
0xBA1F70  lea edx,[ebp-0x4C]
0xBA1F76  call 0xBA13D0   ; KDF(shared, "BDDATA", 6, out72, 0x48)
```

**⇒ 客户端从 ECDH 共享秘密出发，用两个不同标签派生两套密钥。这是标准 KDF 结构。**

---

## 三、战斗服侧对照

```c
// p224.c:313-323
void codol_derive_transport_key(const uint8_t shared_x28[28],
                                const uint8_t security_key16[16],
                                uint8_t out24[24])
{
    memcpy(buf, shared_x28, 28);
    memcpy(buf + 28, security_key16, 16);   // ★ security_key16
    codol_sha1(buf, 44, d);
```

**⇒ 战斗服把 `shared_x28` 和 `security_key16` 拼接后 SHA1。**

而 `security_key16` 是：

```c
// battle.c:43
memset(b->security_key, 0x01, sizeof(b->security_key));   // 全 0x01
```

### 对比结论

| | 客户端 | 战斗服 |
|---|---|---|
| 输入 1 | ECDH shared（运行时算） | `shared_x28`（运行时算）✅ |
| 输入 2 | **KDF 标签**（`"BDDATA"`/`"CLIENTCHAL"`） | **16 字节常量 `0x01…`** ❌ |
| 派生方式 | 带标签的 KDF（`0xBA13D0`） | 裸 SHA1 拼接 |
| 标签个数 | **2 个**（BDDATA 6B + CLIENTCHAL 10B） | **0 个** |

**⇒ 这不只是「值不同」，是「计算方法根本不同」。**

---

## 四、所以 162 卷那个缺陷要重新表述

**162 卷我写**：

> 「大厅 `0x00` vs 战斗服 `0x01`，两边不一致」

**更准确的说法**：

> **战斗服根本没用客户端那套 KDF。** 它用 `SHA1(shared ‖ 0x01×16)`，
> 客户端用 `KDF(shared, "BDDATA", …)` 与 `KDF(shared, "CLIENTCHAL", …)`。
> **两者算出来的 `transport_key` 必然不同 ⇒ HMAC 必然对不上。**

**`0x00` / `0x01` 之争是个伪问题——真问题是「算法不同」。**

---

## 五、修正 162 卷的修法建议

162 卷我建议「统一 security_key」。**不够。**

**正确修法**：

```c
// 战斗服应改成：
// 1) 从 ECDH 得到 shared_x28
// 2) 用与客户端相同的带标签 KDF：
//    key_16 = KDF(shared, "CLIENTCHAL", 10, 16)   // 与客户端 0xBA1EEC 对应
//    out_24 = KDF(shared, "BDDATA",     6, 24)    // 与客户端 0xBA1F6B 对应
// 3) 不要用 SHA1(shared || 0x01×16)
```

**但这里有个未定的点**：客户端有两个标签（`BDDATA` / `CLIENTCHAL`），战斗服只用一个 `transport_key`。
**哪个标签对应 transport_key，本卷未定** —— 需要解 `0xBA13D0` 的 6 参数语义（已读到：`[+8]=输出大小`,`[+C]=输出buf`,`[+10]=标签长`,`[+14]=标签`,`[+18]=输入长`,`[+1C]=输入`），以及两个输出（`0x48`=72 字节 / `0x10`=16 字节）各自喂给谁。

---

## 六、这一项现在算不算黑箱

**不算。** 状态是：

| 项 | 状态 |
|---|---|
| `security_key` 是常量 | ❌ **已否定**（它是 ECDH 共享秘密派生物） |
| 客户端用带标签 KDF | ✅ **已确证**（`0xBA13D0` + 2 个标签） |
| 战斗服用裸 SHA1+常量 | ✅ **已确证**（`p224.c:313`） |
| **两者算法不同** | ✅ **已确证** ⇒ HMAC 必错 |
| **`BDDATA`/`CLIENTCHAL` 哪个是 `transport_key`** | ⚠️ **待定**（下一步：解两个输出的consumer） |

**⇒ 五分之四已定。剩下的一个「哪个标签对应哪个」，是有明确下一步的待定项，不是黑箱。**

---

## 七、方法论

1. **★★ 「两边值不一样」的下一步是「两边算法是否一样」。** 162 卷我只比了值，没比算法；本卷发现**算法根本不同**。
2. **★ KDF 标签（`BDDATA`/`CLIENTCHAL`）比密钥本身更能定性。** 有标签 = 标准 KDF；无标签拼接 = 自制。
3. **★ 「暂用全 0」这类注释，往往掩盖的是「算法还没对上」。** 不是填个值就好。
4. **★ VMProtect thunk（`E9 jmp` 打头）要看它跳去哪、以及调用点的参数形状。** 参数形状（`push 0x14` + EC 调用序列）足以定性它是 ECDH。
5. **★ 一次只问「A 还是 B」，容易漏掉「其实两个都不是」。** 162 卷的提问方式本身就是错的。
