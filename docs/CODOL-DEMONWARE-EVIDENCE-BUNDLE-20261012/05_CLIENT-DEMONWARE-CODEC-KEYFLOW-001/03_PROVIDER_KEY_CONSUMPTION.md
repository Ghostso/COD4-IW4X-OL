# 03 Provider 密钥消费链（最终消费点）

## 1. Provider 的真实身份（本轮更正）

`this+0x5F0`/`this+0x5F4` **不是**"codec 输出位置"，而是两个独立的 **AES 加密对象指针**：

```asm
00AAB941  mov ecx,[edi+0x5F0]        ; 旧 provider#1
00AAB94B  mov eax,[ecx] / mov edx,[eax] / push 1 / call edx   ; vtable[0] = 析构
00AAB953  mov dword [edi+0x5F0],0    ; 置空
00AAB95D  push 0x394 / call 0xDF9AA45 ; operator new(0x394)
00AAB97A  call 0xA87BA0               ; 构造函数（vtable <- 0x00C5A31C）
00AAB983  mov [edi+0x5F0],eax
00AAB989  mov edx,[eax] / mov edx,[edx+4]  ; vtable[1]
00AAB98E  push 0x10 / push &[ebp-0x80] / call edx   ; setKey(16B)
```

vtable `0x00C5A31C`（由 `0xA87BDE` push 的立即数确证；`0xA87BDC mov dword [esi],0xC5A31C`）：

| 槽 | 目标 VA | 语义（由调用点与函数体确认） |
|---:|---|---|
| 0 | `0x00A87DB0` | 析构 |
| 1 | `0x00A87C30` | **setKey(buf,len)**（限 16/24/32；实际只传 0x10） |
| 2 | `0x00A87CF0` | **encrypt(in, inLen, out, outLen)**（`vtable[2]` = `[vt+8]`） |
| 3 | `0x00A87D50` | **decrypt(in, inLen, out, outLen)**（`vtable[3]` = `[vt+0xC]`） |

`setKey` 函数体（`0x00A87C30`）在 `0xA87C4B` 校验长度 ∈ {16,24,32}，随后 `0xA87C8C–0xA87C9D` 把密钥拷入 provider 内部 `+0xC`。**全程不读写 `+0x5F8`/`+0x60C`。**

## 2. 两个 provider 的密钥来源（与参考对端逐项对齐）

`expandKey(secret,"BDDATA",72)` 的输出位于 `[ebp-0xA8]`，72 字节覆盖 `[ebp-0xA8, ebp-0x60)`。四个切片（与参考 `20/20/16/16` 完全一致）：

| 切片 | 栈地址 | 客户端用途 | 参考对端变量 |
|---|---|---|---|
| `data[0:20]` | `[ebp-0xA8, ebp-0x95)` | `0xAAB92C` **codec A STORE** → `this+0x5F8`；出站时 LOAD 作 HMAC 请求键 | `requestHmac` |
| `data[20:40]` | `[ebp-0x94, ebp-0x81)` | `0xAAB93C` **codec B STORE** → `this+0x60C`；入站时 LOAD 作 HMAC 应答键 | `responseHmac` |
| `data[40:56]` | `[ebp-0x80, ebp-0x71)` | `0xAAB990 lea ecx,[ebp-0x80]` → **provider#1(`+0x5F0`).setKey(16)** | `decrypt`（aes_out） |
| `data[56:72]` | `[ebp-0x70, ebp-0x61)` | `0xAAB9F8 lea ecx,[ebp-0x70]` → **provider#2(`+0x5F4`).setKey(16)** | `encrypt`（aes_in） |

**四个切片的栈地址与长度逐字节吻合**，无复制、无拼接、无截断、无二次变换。

## 3. 最终消费点（def → use 闭合）

### 3.1 出站（客户端加密 + 签名）

```asm
00AAACB5  mov ecx,[edi+0x5F0]        ; provider#1(key=data[40:56])
00AAACBD  mov edx,[edx+8]            ; vtable[2] = encrypt
00AAACC0  push ebx / push eax / push eax / push &[ebp-0x38] / call edx
00AAACD?  ...                        ; IV 16B 写入帧 +0x0A
00AAACE3  call 0xAA8D70 (dl=0)       ; codec A LOAD: [ebp-0x24] = this+0x5F8 ^ maskA
00AAACE8  push 0x14 / 0x00AAACEE 0xDF6216D  ; HMAC_SHA1 上下文（key = 上述 20B）
00AAAD40  call 0xA88400              ; HMAC_Update(frame[0 : len-8])
                                     ; → tag8 写帧尾
```

⇒ 出站帧的 **AES 密钥 = `data[40:56]`（不经 codec）**，**HMAC 密钥 = `data[0:20]`（经 codec 存取往返）**。

### 3.2 入站（客户端验签 + 解密）

```asm
00AAB046  call 0xAA8BF0 (dl=0)       ; codec B LOAD: [ebp-0x40] = this+0x60C ^ maskB
00AAB04B  push 0x14 / 0x00AAB051 0xDF6216D  ; HMAC_SHA1 上下文（key = 上述 20B）
00AAB085  call 0xA88400              ; HMAC_Update(frame[0 : total-8])
00AAB0E6  ...                        ; 8B tag 比较 → HMAC mismatch
00AAB140  mov eax,[edi+0x5F4] / mov edx,[edx+0xC]    ; provider#2(key=data[56:72]).decrypt
00AAB151  push ... / call edx
```

⇒ 入站帧的 **HMAC 密钥 = `data[20:40]`（经 codec 存取往返）**，**AES 密钥 = `data[56:72]`（不经 codec）**。

### 3.3 与参考对端的方向交叉验证（独立佐证）

参考对端同时存在两套实现，且**方向赋值一致**：

| 证据 | `data[0:20]` | `data[20:40]` | `data[40:56]` | `data[56:72]` |
|---|---|---|---|---|
| `ol-mod` C++ `Crypto.cpp:205-212` + `LobbyProtocol.cpp:382/415` | 校验客户端帧（request） | 签服务端应答（response） | 解客户端帧（decrypt） | 加密服务端应答（encrypt） |
| `REF_LOBBY_KIT/codol_crypto.py:643-651` | `request_hmac` | `response_hmac` | `decrypt` | `encrypt` |
| **2697 客户端实测** | 出站 HMAC（`0xAAACE3`→`0xAAB884` 前） | 入站 HMAC（`0xAAB046`） | 出站 AES（`0xAAACB5`） | 入站 AES（`0xAAB140`） |
| 匹配 | ✅ | ✅ | ✅ | ✅ |

四路方向**全部匹配**，无一处交叉或镜像。

## 4. 情况归类（任务书 §4 的 A–E）

| 情况 | 是否成立 | 依据 |
|---|---|---|
| A. codec 输出直接作为 provider 输入 | **否** | codec 输出（`+0x5F8`/`+0x60C`）只进 HMAC，**从不进 AES provider**；AES 直接用 `data[40:56]`/`[56:72]` |
| B. 复制/拼接/截断/再变换 | **否** | 四切片栈地址与长度逐项吻合，无中间副本 |
| C. 与参考对端派生值存在等价抵消 | **是（本轮证明）** | STORE 与 LOAD 使用同一常量表+同一置换，两次 XOR 同掩码 ⇒ 恒等；参考消费的正是 `expandKey` 原值 |
| D. 只确认字段相关 | 否 | 已到指令级 def-use 闭合 |
| E. VM/间接导致无法闭合 | 否（就本链而言） | codec 为纯直线代码、4 个直接调用者、无字面量函数指针；provider 虚表槽可由静态表确证 |

**关键论证（逐字节等价）**：

```text
设 clientStore(x) = x XOR M
   clientLoad(y)  = y XOR M          （同一 M：同一常量表 + 同一置换）
则 clientLoad(clientStore(x)) = (x XOR M) XOR M = x      —— 逐字节恒等

其中 x = expandKey(secret,"BDDATA",72)[0:20] 或 [20:40]
      = 参考对端 deriveSessionKeys 的 requestHmac / responseHmac（输入、标签、长度均相同）

⇒ K_client,consumed(HMAC) = K_reference,derived(HMAC)   （bit-exact）
⇒ K_client,consumed(AES)  = data[40:56] / data[56:72]   （不经 codec，本身就相同）
```

codec 的**唯一净效果**是把密钥在内存中留成"掩码态"，降低明文搜索命中率；它**不改变任何被消费的密钥字节**。

## 5. 证据等级

| 结论 | 等级 |
|---|---|
| `+0x5F0`/`+0x5F4` = AES provider 指针（vtable `0x00C5A31C`，0x394 字节） | PROVEN |
| AES 密钥 = `data[40:56]` / `data[56:72]`，不经 codec | PROVEN（栈地址+长度逐项） |
| HMAC 密钥 = `data[0:20]` / `data[20:40]`，经 codec 存取往返 | PROVEN |
| codec STORE/LOAD 同掩码 ⇒ 净恒等 | PROVEN（同一函数、同一常量表、同一置换表） |
| 四路方向与参考对端全部匹配 | PROVEN（两套独立参考实现 + 客户端实测） |
| `K_client,consumed = K_reference,derived` | **PROVEN（静态、bit-exact）** |

## 6. 限制说明

- 本品为**静态**等价性证明：未采样运行时密钥，未做逐字节运行时比对。其成立前提是"同一函数在同一常量表/置换表下按 `dl` 两分支执行"，该前提已由指令级证据完全确定。
- 参考对端是否**主动**实现该掩码层不影响客户端等价性：客户端消费的是去掩码后的原值，故 `ol-mod` C++/Python 直接使用 `deriveSessionKeys` 输出即为正确值。
