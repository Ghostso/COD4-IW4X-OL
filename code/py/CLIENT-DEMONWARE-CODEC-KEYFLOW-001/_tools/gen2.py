# -*- coding: utf-8 -*-
import os, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
D = lambda n: os.path.join(root, n)
docs = {}

docs["03_PROVIDER_KEY_CONSUMPTION.md"] = r"""# 03 Provider 密钥消费链（最终消费点）

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
"""

docs["04_TVM0_RELEVANT_PATHS.md"] = r"""# 04 `.tvm0` 相关路径检查

> 范围限定：只追踪与 `0xAA8D70`/`0xAA8BF0` 两 codec 或其相关字段（`+0x5F0/+0x5F4/+0x5F8..+0x61F`）有**明确交集**的分派路径。
> 不要求完整逆向 `.tvm0`。

## 0. `.tvm0` 口径更正

| 项 | 本任务实测 | 上轮报告 |
|---|---|---|
| RVA | `0x0D958000` | （未标） |
| VA | **`0x0DD58000`** | `0x0D955000` ← **笔误，既非 VA 也非 RVA** |
| VS | `0x002B9000` | `0x002B9000` ✓ |
| raw size | `0x002B8C00` | — |
| 属性 | 可执行（`x=True`） | ✓ |

## 1. 问题一：是否存在其他写入/覆盖这些字段的 VM 路径？

### 1.1 字段偏移在 `.tvm0` 内的字面量命中

全 `.tvm0` 原始字节（`0x2B8C00`）内按 dword 精确搜索：

| 目标偏移 | 命中 | 判定 |
|---|---:|---|
| `0x5F0` | **0** | 无 |
| `0x5F4` | 2（`0xDE0FEB1`、`0xDFC3AE5`） | **均为误命中**，见 1.2 |
| `0x5F8` | **0** | 无 |
| `0x5F9` | **0** | 无 |
| `0x5FC` | **0** | 无 |
| `0x60C` | **0** | 无 |
| `0x60D` | **0** | 无 |

### 1.2 两处 `+0x5F4` 命中的逐一核验（误命中）

```asm
; 0xDFC3AE3
0DFC3AE3  81ec f4050000   sub esp, 0x5F4        ; <- 栈帧大小立即数，非对象偏移
; 0xDE0FEB1（该地址处于一条立即数/数据串中，非指令边界）
0DE0FE81  a4 ...
```

⇒ 两处都不是对"会话对象 `+0x5F4`"的访问。**`.tvm0` 内不存在对该字段窗口的字面量访问。**

### 1.3 codec 常量与置换在 `.tvm0` 内的命中

| 模式 | 命中 |
|---|---:|
| Codec A 20B 常量块（`411309ae…`） | **0** |
| Codec B 20B 常量块（`8022deaa…`） | **0** |
| `411309ae`（A 首 dword） | **0** |
| `8022deaa`（B 首 dword） | **0** |
| `BDDATA` / `CLIENTCHAL` 标签 | **0** |

⇒ `.tvm0` 内**不含** codec 的任何表数据，也就不存在"从 VM 段取另一张表覆盖"的路径。

### 1.4 codec 函数是否可被 VM 段间接调用

| 检查 | 结果 |
|---|---|
| `.text` 内 `E8 rel32` 直接调用者 | Codec A = 2，Codec B = 2（见 01 §5） |
| 全镜像（含 `.tvm0`/`.rima`/`.data`）内 4 字节函数地址字面量 | `0x00AA8D70` **0**；`0x00AA8BF0` **0** |
| 两函数是否为 `ret` 终结的纯函数 | 是（`ret 8`，无跳转表、无 `jmp [reg]`） |

⇒ 两 codec **不可经函数指针被 VM 调用**；唯 4 个调用者即全部。

## 2. 问题二：是否存在绕过 codec 的 provider 初始化路径？

AES 密钥安装路径（`+0x5F0`/`+0x5F4` 的 `setKey`）**本来就绕开 codec**——这是设计事实，不是缺陷。需要排除的是"存在第二条绕过正规派生、直接注入 AES 密钥的路径"。

| 检查 | 结果 |
|---|---|
| `+0x5F0` 的写入点 | 仅 `0xAAB983`（KDF 内 new）与 `0xAAA6E9`（重置置 0） |
| `+0x5F4` 的写入点 | 仅 `0xAAB9E7`（KDF 内 new）与 `0xAAA6EF`（重置置 0） |
| 两个 provider 的 `setKey`（vtable[1]）调用点 | 各 **1** 处：`0xAAB99A`、`0xAAB9FE`（均在 `0x00AAB310` 内） |
| KDF 握手内调用 provider 的 `setKey` 是否有第二条路径 | 无（`0x00AAB310` 是唯一构造者） |

⇒ **不存在第二条 AES 密钥注入路径**；AES 密钥 100% 来自 `expandKey(secret,"BDDATA",72)` 的后 32 字节。

## 3. 问题三：是否存在能改变结论的替代密钥来源？

| 候选 | 检查 | 判定 |
|---|---|---|
| `secret` 是否有第二条来源 | `0x00AA95C0`（HMAC-SHA1）唯一调用者 `0xAAB884`；其 key = `[ebp-0x60]` = `0xAAB856` 的 SHA-1 输出 | 无第二条 |
| `expandKey` 是否有第二条实例 | 全 `.text` 仅 `0x00AA9CE0` 一个实现，`0xAA9CE0` 在全镜像无字面量引用 | 无 |
| `BDDATA`/`CLIENTCHAL` 是否有第二处引用 | 各 1 处（见 01） | 无 |
| `.tvm0` 是否含协议标签或 KDF 表 | 全部 0 命中 | 无 |

## 4. `.text → .tvm0` 调用边界（说明性）

全 `.text` 内指向 `.tvm0` 的 `E8/E9` rel32 共 **3871** 处，目标映射到 **844 个不同入口**，最高频的 6 个为：

| 目标 VA | 次数 | 身份（由调用点上下文确认） |
|---|---:|---|
| `0x0DDAB8AC` | 601 | 运行时通用分发/跳板 |
| `0x0DF9AA45` | 345 | **operator new / 分配器**（`0xAAB962`、`0xAAB9C2` 直接调用） |
| `0x0DEDEC1D` | 189 | 序列化辅助 |
| `0x0DF94575` | 173 | 缓冲区辅助 |
| `0x0DF5510E` | 154 | 通用工具 |
| `0x0DEB13C5` | 142 | 通用工具 |

**关键点**：`0x00AA8D70`/`0x00AA8BF0` **自身不调用 `.tvm0`**（函数体为纯直线代码，无 `E8` 指向 `.tvm0`）；KDF 对 `.tvm0` 的唯一依赖是分配器 `0x0DF9AA45`，其用途是分配 provider 对象，不涉及密钥字节。

## 5. 证据等级与边界

| 结论 | 等级 | 边界 |
|---|---|---|
| `.tvm0` 内无对 `+0x5F0/+0x5F4/+0x5F8..+0x61F` 的字面量访问 | PROVEN | 字面量字节扫描 |
| `.tvm0` 内无 codec 常量/置换/协议标签 | PROVEN | 精确字节扫描 |
| codec 不可被函数指针调用 | PROVEN | 全镜像字面量 0 命中 + `ret` 纯函数 |
| AES 密钥无第二条注入路径 | PROVEN | `setKey` 调用点唯一 |
| **`.tvm0` 完整程序语义** | **BLOCKED（有意不解析）** | 未逐指令还原 VM；但上述字段窗口、常量、标签三条交集均已 0 命中，足以支撑本任务的闭合结论 |

> 说明：本任务按任务书 §6 只做"明确交集"检查。若将来需要"证明 `.tvm0` 一定不参与该链"这一**更强命题**，仍需完整 VM 语义还原；本报告不作该更强声明。
"""

for name, text in docs.items():
    with open(D(name), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", name, len(text))
