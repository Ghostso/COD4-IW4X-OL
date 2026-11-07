# 8081/UDP QoS 加密通道 —— 密钥来源调查报告

日期：2026-09-25
范围：**只读静态分析**。未注入、未启停游戏、未改网络、未改任何被分析文件。
未触碰 985 组件与 ACE。

输入（只读）：
* `run_codol_001\runs\SINGLE_V3\local_listeners.jsonl`（9 个出向 8081 包）
* `run_codol_001\runs\SINGLE_V0B\local_listeners.jsonl`（8000 参考帧）
* `run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl`（4000 条内存命中）
* `CODOLServer\KEY_CONTEXT_20260925.txt`（274299 B 名称池）
* `run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine\engine_best.bin`（5 MB 运行时快照）
* `COD OL\codoMP_client_shipRetailBase.dll`（60327992 B）
* `C:\ProgramData\Tencent\TAS\TASData.dat`（240 B）、`COD OL\components\tclsqmfix\TclsQmFix.dat`（784 B）

新增脚本（只读）：见文末 §8。

---

## 0. 结论速览

| # | 结论 | 强度 |
|---|---|---|
| 1 | 8081 载荷是**整块分组密码**，**16 字节块**，**`len-4` 恒为 16 的倍数（9/9）** | **HIGH** |
| 2 | 包 #6 在**字节偏移 464 与 592** 出现**完全相同的 16 字节密文块** ⇒ **无 per-packet IV / 块间无链式依赖（ECB 特征）** | **HIGH** |
| 3 | 每包尾部 4 字节 `00 00 | u16be` 是**明文尾**（不是分组、不是 tag 高位）；9/9 高 16 位恒为 0 | **HIGH** |
| 4 | 运行时 `.tls` 镜像里**存在 AES 实现**：AES 逆 S-box 全表 + `AES`/`aes`/`CBC`/`ECB`/`SHA256`/`HMAC`/`EVP_` 字样（`hits` `0x00D3C218`–`0x00D3ED48`） | **HIGH**（存在）/ **MEDIUM**（与本通道相关） |
| 5 | `QOS_CS_MAGIC` = ASCII **`"ru"`**（`0x72 0x75`），`QOS_SS_MAGIC` = ASCII **`"su"`**（`0x73 0x75`） | **HIGH** |
| 6 | `0x18`=24 是**请求长度**，不是"24 项"；与 `ruHeadLen=16 + BodyLen=8` 三处自洽 | **HIGH** |
| 7 | **8081 的密钥不在 EXE/Base.dll 明文与磁盘 `TclsQmFix.dat`/`TASData.dat` 里**；不是 TAS 流密码，也不是候选 AES key | **HIGH（否定）** |
| 8 | 密钥来源（谁派生、如何派生） | **UNKNOWN** |

---

## 1. 判定：8081 是分组密码密文，不是 TAS 流密码、不是压缩

### 1.1 长度对齐（决定性，HIGH）

```
#0  84  -> 80  = 16*5
#1  84  -> 80  = 16*5
#2 708  -> 704 = 16*44
#3 196  -> 192 = 16*12
#4  84  -> 80  = 16*5
#5  84  -> 80  = 16*5
#6 756  -> 752 = 16*47
#7 260  -> 256 = 16*16
#8  84  -> 80  = 16*5
```

9/9 满足 `(len-4) % 16 == 0`。5 个 84 B 包**长度完全一致**但密文全不同，说明
**不是**"定长明文 + 定长密钥流"（那样密文异或应趋近于明文异或，可打印率会偏高）；
实测两两异或可打印率 0.308–0.513，**无结构性泄漏**（`_qoskey_probe.py` §B）。

### 1.2 ECB 特征：包 #6 内 16 字节密文块精确重复（HIGH）

```
包 #6，body 长 752 B = 47 块
块 29 (字节偏移 464) == 块 37 (字节偏移 592) == 88d0dccb61b9677ede97befa6e08e5c5
偏移差 = (37-29)*16 = 128 字节
```

* 在 47 个随机 128 bit 块中出现一对相同的概率约 `47^2 / 2^129 ≈ 10^-34`，
  **不可能是巧合**。
* 只有当**同一明文块用同一密钥加密两次**才会出现。⇒ **无 per-packet IV**，
  **块之间没有前向/后向耦合**（排除了 CBC/CFB/OFB 链式模式；剩下 ECB、
  CTR（同偏移同计数器）或"无 IV 的 ECB"）。
* 跨包**没有**任何重复块 ⇒ 每包有独立密钥流起点（计数器初值/密钥不同）。

**判定：整块分组密码，16 字节块，本次抓包中最像 ECB。强度 HIGH（结构），
算法族= AES 候选。强度 MEDIUM。**

### 1.3 尾部 4 字节是明文（HIGH）

9/9 包的 `tail4` 都是 `00 00 XX XX`：

```
#0 00007f11  #1 00000202  #2 00002c54  #3 00007a59  #4 00003609
#5 00002baf  #6 000042c9  #7 00007ec9  #8 00004a91
```

`tail4` 当 u16be 对 = `(0, 32529) (0,514) ...`，**高 16 位 9/9 恒为 0**。
`len-4` 已满足 16 对齐，故这 4 字节**不参与分组**，是明文尾。

> 修正旧报告的分割：旧报告看到的 `len-6` 处 `u16 A` **不是独立的明文字段**，
> 它是**最后一个 16 B 密文块的最后 2 字节**；真正落在分组外的是
> `tail4 = 00 00 | u16be`（`B` 可为 0x0202/0x2c54/…）。

> 这是一条**强 oracle**：任何候选 key 解密出的结果，其**明文块边界**都必须与
> `len-4` 对齐且尾 4 字节落在分组外，否则 key 立即被否定。

### 1.4 已排除 TAS 流密码（HIGH）

用 `COD OL\scripts\tas_crypt.py`（KSA + MSVCRT LCG + `MASK=8AE69BF3C17D4025`）
配合 **1177 个候选 key**（游戏树内所有 `.exe/.dll/.dat/.cfg/.ini/.iw4/.zip` 的
mtime/ctime/atime 转 FILETIME，加 `TASData`/`tcls`/`qmfix` ASCII、TAS 默认
`46D14CF9/EF1DC888`），对 9 个 8081 包与 `TASData.dat`/`TclsQmFix.dat`：

* **没有任何一个 key** 产出以 `ru`/`su`/`SEMV`/`QOSC` 开头的输出。
* 仅 2 条"命中"是随机噪声（`ur` 出现在第 0–1 字节之外，且长度/结构不自洽）。

⇒ **TAS 流密码不适用于 8081 通道，也不是这两个 `.dat` 的算法。强度 HIGH（否定）。**

### 1.5 已排除候选 AES key（HIGH）

140 个候选 key（16/24/32 字节）：`codol/CODOL/qos/QOS/tencent/tqos/QOSCSPkg/
qos_cs/qos_ss/356c4bc3/356C4BC3/DW-Ticket-Seed/config_mp.cfg/TCLS`
× {zero-pad, repeat, MD5, SHA-256} + 数值 `0x356C4BC3`/`0x1109`/`0x1120`/`0x1121`
四种字节序 + 运行时 `43FCB2AC…` 十六进制串的 raw/MD5。

AES-ECB 与 AES-CBC(IV=0) 解密首块，**无一**产出 `ru`/`su`/`QOSC`/小整数长度头。
⇒ **密钥不是这些常量。强度 HIGH（否定）。**

> 注意：**未见** `CryptImportKey`/`CryptEncrypt`；AES 是**内置/静态链接**实现，
> 不是 CryptoAPI。见 §3。

---

## 2. `qos_cs` / `qos_ss` 两张紧凑表的真实结构（HIGH）

这两张表在磁盘上位于 `Base.dll .tls`（raw=`0xAFF800`，rva=`0xB0A000`），**是密文**：

| 项 | 磁盘 | 运行时 |
|---|---|---|
| `qos_cs` 标签 | raw `0xE39CEC`，字节 `7c 50 b8 63 …` | VA `0x00E444EC`，ASCII `"qos_cs"` |
| `qos_ss` 标签 | raw `0xE35C2C`，字节 `62 0a a5 7c …` | VA `0x00E4042C`，ASCII `"qos_ss"` |

**关键新证据：`ENGINE_DUMP_20260925_114204\engine\engine_best.bin` 是 `.tls`
运行时镜像的明文快照**（5 MB，VA `0x994000`–`0xE65000`），其中 `0x00E444EC`
处就是明文 `qos_cs`。据此得到该表真实布局（LE32 / C 结构）：

### 2.1 `qos_cs` 表（VA `0x00E4444C` 起）

```
00E4444C  00 42 6f 64 79 00   = "\0Body\0"        结构名尾
00E44452  00 x 6
00E44458  d6 02 0b 00      = 0x000b02d6 = 721622   (表 ID / magic2)
00E4445C  20 00 00 00      = 32                  (字段区/槽大小)
00E44460  72 51 00 00      = 0x5172 = 20850      (字段数 / seq)
00E44464  4b df 40 7e      = 0x7e40df4b          (hash / fletcher)
00E44468  00 00 00 00 00 00 00 00 00 00 00 00
00E44474  ff ff ff ff      = -1                  (哨兵)
00E44478  01 00 00 00      = 1
00E4447C  00 00 00 00      = 0
00E44480  13 00 00 00      = 19      ┐
00E44484  13 00 00 00      = 19      │ 表内常量 0x13 = 19
00E44488  18 00 00 00      = 24      │ 表内常量 0x18 = 24
00E4448C  18 00 00 00      = 24      ┘ 表内常量 0x18 = 24
00E44490  00 x 16
00E444A0  0b 00 00 00      = 11                  (TQOS_CS_STRING_LEN)
00E444A4  00 00 00 00      = 0
00E444A8  80 01 00 00      = 384     ┐
00E444AC  18 02 00 00      = 536     │ 4 个子表偏移
00E444B0  b0 02 00 00      = 688     │
00E444B4  48 03 00 00      = 840     ┘
00E444B8  14 47 00 00      = 18196   ┐
00E444BC  00 00 00 00      = 0       │ 字符串池回指
00E444C0  14 47 00 00      = 18196   │
00E444C4  5e 50 00 00      = 20574   │
00E444C8  5e 50 00 00      = 20574   │
00E444CC  5e 50 00 00      = 20574   ┘
00E444D0  00 00 00 00
00E444D4  ff ff ff ff ff ff ff ff 00 00 00 00 ff ff ff ff ff ff ff ff ff ff ff ff
00E444EC  "qos_cs"        表名字面量（后面是 0 填充）
00E4456C  14 47 00 00       = 0x4714
00E44570  72 75 00 00       = ASCII "ru"  ← QOS_CS_MAGIC
00E44574  ff ff ff ff 00 00 00 00
00E4457C  21 47 00 00  20 00 00 00  ff ff ff ff  00 00 00 00
00E4458C  34 47 00 00  40 00 00 00  ff ff ff ff  00 00 00 00
00E4459C  47 47 00 00  20 00 00 00  ff ff ff ff  00 00 00 00
00E445AC  5a 47 00 00  20 00 00 00  ff ff ff ff  00 00 00 00
00E445BC  6d 47 00 00  08 00 00 00  ff ff ff ff  00 00 00 00
00E445CC  7c 47 00 00  80 00 00 00  ff ff ff ff  00 00 00 00
00E445DC  92 47 00 00  00 02 00 00  ff ff ff ff  00 00 00 00
00E445EC  a9 47 00 00  1e 00 00 00  ff ff ff ff  00 00 00 00
00E445FC  bf 47 00 00  0a 00 00 00  ff ff ff ff  00 00 00 00
00E4460C  d5 47 00 00  b8 0b 00 00  ff ff ff ff  00 00 00 00
00E4461C  e1 47 00 00  b8 0b 00 00  ff ff ff ff  00 00 00 00
00E4462C  f0 47 00 00  02 00 00 00  ff ff ff ff  00 00 00 00
00E4463C  02 48 00 00  04 00 00 00  ff ff ff ff  00 00 00 00
00E4464C  16 48 00 00  08 00 00 00  ff ff ff ff  00 00 00 00
00E4465C  2f 48 00 00  10 00 00 00  ff ff ff ff  00 00 00 00
```

**第 0 行就是 `QOS_CS_MAGIC` 的字面值：ASCII `"ru"`（`0x7275`）。强度 HIGH。**

每行 16 字节的 `{u32 相对偏移, u32 长度, ffffffff, 00000000}` 是
**字段/子表描述符数组**，长度值为
`0x20/0x40/0x20/0x20/0x08/0x80/0x200/0x1e/0x0a/0xbb8/0xbb8/0x02/0x04/0x08/0x10`。
这些长度与该名称池的顺序**高度一致**，但本报告不把每一项强行绑定到单个宏名；
可机械确认的只有：`0x0a`=10、`0xbb8`=3000 是两个数值上限，
`0x18`=24 在 `qos_cs` 表中出现两次（与 8000 帧的 `0x18` 长度字段同值）。

### 2.2 `qos_ss` 表（VA `0x00E4038C` 起）

同构，仅常量不同：

```
00E4038C  94 26 00 00      = 0x2694 = 9876
00E40390  fe ff ff ff      = -2
00E40394  00 00 00 00
00E40398  d6 02 0b 00      = 0x000b02d6   ← 与 qos_cs 完全相同
00E4039C  20 00 00 00      = 32
00E403A0  ba 40 00 00      = 0x40ba = 16570
00E403A4  4e 76 52 80      = 0x8052764e
00E403A8  00 x 12
00E403B4  ff ff ff ff / 01 00 00 00 / 00 00 00 00
00E403C0  0d 00 00 00 = 13
00E403C4  0d 00 00 00 = 13
00E403C8  0f 00 00 00 = 15
00E403CC  0f 00 00 00 = 15
00E403D0  00 x 12
00E403DC  00 00 00 00
00E403E0  0b 00 00 00 = 11   TQOS_SS_STRING_LEN
00E403E4  00 00 00 00
00E403E8  f0 00 00 00 = 240 ┐
00E403EC  58 01 00 00 = 344 │ 4 个子表偏移
00E403F0  c0 01 00 00 = 448 │
00E403F4  28 02 00 00 = 616 ┘
00E403F8  34 39 00 00 = 14644
00E403FC  00 00 00 00
00E40400  34 39 00 00 / a6 3f 00 00 a6 3f 00 00 a6 3f 00 00
00E4042C  "qos_ss"
00E404AC  34 39 00 00       = 0x3934
00E404B0  73 75 00 00       = ASCII "su"  ← QOS_SS_MAGIC
00E404B4  ff ff ff ff / 00 00 00 00
00E404BC  41 39 00 00  20 00 00 00 …
00E404EC  76 39 00 00  80 00 00 00 …
00E404FC  8c 39 00 00  00 02 00 00 …
00E4052C  cf 39 00 00  00 01 00 00 …
00E4053C  e2 39 00 00  00 00 00 00  …  ← 0 ⇒ 该字段无上限
```

**`QOS_SS_MAGIC` = ASCII `"su"`（`0x7375`）。强度 HIGH。**

### 2.3 关键推论

* 两个 24 位"magic"**不是数值常量，而是 2 字节 ASCII `"ru"` / `"su"`**
  —— 正与 8000/UDP 实测帧首 `75 72`（`"ur"`，小端读作 `0x7275`）自洽。
  **`QOSCSPkgHead.Magic` = u16 = `'ur'`。强度 HIGH。**
* 两张表**跨两次独立运行时快照（`112143` 与 `114204`）逐字节完全一致**
  （`qos_cs` 256 B / `qos_ss` 256 B / `QOS_CS_MAGIC` 256 B / ticket 640 B
  **均 0 字节差异**）⇒ 这些是**编译期常量表**，**不是** 8081 的会话密钥。

---

## 3. `.tls` 与运行时镜像的关系（新证据，影响可达性）

`Base.dll` 节表：

| 节 | rva | raw | rawsz | vsz |
|---|---|---|---|---|
| `.text` | `0x1000` | `0x400` | `0x741C00` | `0x742000` |
| `.rdata` | `0x743000` | `0x742000` | `0x26B200` | `0x26C000` |
| `.data` | `0x9AF000` | `0x9AD200` | `0x14AA00` | `0x153000` |
| `.idata2` | `0xB02000` | `0xAF7C00` | `0x5000` | |
| `.rsrc2` | `0xB07000` | `0xAFCC00` | `0x2C00` | |
| **`.tls`** | **`0xB0A000`** | **`0xAFF800`** | **`0xED2600`** | `0xED3000` |
| `.tvm0` | `0x19DD000` | `0x19D1E00` | `0x1F5D600` | |
| `.reloc` | `0x393B000` | `0x392F400` | `0x55E00` | |

**结论 A（HIGH）**：运行时引擎窗口 `VA 0x994000..0xE65000`
（= `ENGINE_DUMP_*` 5,050,368 B）在**同一 rva 上**给出 `.tls` 的**明文**版本：
磁盘 `0xE39CEC`=`7c 50 b8 63…` vs 运行时 `0xE444EC`=`"qos_cs"`。
⇒ **`.tls` 是"加载时才解密的代码/数据段"**，其磁盘字节（熵 7.6321）不是源码。

**结论 B（HIGH）**：**不存在**简单逐字节 XOR 关系。
在 `0x00D5A000` / `0x00E40400` / `0x00E44400` / `0x00E48C00` / `0x00D85A00`
五个采样点，磁盘 vs 运行时 **equal = 0/32**，且 XOR 差**无 ≤16 周期**
（`_qoskey_transform.py`）。⇒ 是**流/块加密或按页重映射**，不是固定 XOR 表。

> **对逆向的直接意义**：`.tls` 中**任何**常量（含 §2 表、§4 字符串）在磁盘上
> 都是密文，**必须**靠运行时镜像（`ENGINE_DUMP`）或运行中读内存才能取到。
> 这也解释了为什么静态扫 `Base.dll` 全部零命中。

### 3.1 运行时 `.tls` 里存在 AES 实现（HIGH）

在 `engine_best.bin` 中按精确字节搜索：

| 目标 | 命中 VA | 说明 |
|---|---|---|
| **AES 逆 S-box 全表（256 B）** | `0x00C84C40` | 精确 256 字节匹配 ⇒ **内置 AES 解密** |
| `AES` | `0x00D3DA28, 0x00D3DA48, 0x00D3DA68, 0x00D3DA88, 0x00D3DAA8, 0x00D3DAC8` | 名称 |
| `aes` | `0x00D3CE73, 0x00D3CE83, 0x00D3CE93, 0x00D3DA18, 0x00D3DA38, 0x00D3DA58` | 名称 |
| `CBC` | `0x00D3CFCD, 0x00D3D325, 0x00D3D34D, 0x00D3D375, 0x00D3ECD0, 0x00D3ED30` | 模式名 |
| `ECB` | `0x00D3CFE5, 0x00D3D2AD, 0x00D3D2D5, 0x00D3D2FD, 0x00D3ECE8, 0x00D3ED48` | 模式名 |
| `RC4` | `0x00D36AC7, 0x00D4056F, 0x00D4057D, 0x00D40598, 0x00D405A5, 0x00D40A3C` | 另一族 |
| `SHA256` | `0x00D3CD8D, 0x00D3CDCC, 0x00D3CE23, 0x00D3D828, 0x00D3D8B8` | 摘要 |
| `HMAC` | `0x00D3C5A8, 0x00D3CC84, 0x00D3CC9B, 0x00D3CF68, 0x00D3CF80, 0x00D5A4FC` | 认证 |
| `EVP_` | `0x00D3C218, 0x00D49220, 0x00D4A670, 0x00D4A694, 0x00D4CFB7, 0x00D4CFEC` | OpenSSL 风格 |
| `PKCS7` | `0x00D42518, 0x00D49A38, 0x00D49A4C, 0x00D49A5C, 0x00D49A70, 0x00D49A84` | 填充 |
| `CTR` | `0x00D55B0D, 0x00D55B19, 0x00D55B8E, 0x00D88D22, 0x00D8EEE4, 0x00D8F168` | 模式名 |

**这是软件静态链接的 OpenSSL 风格 AES 套件**（`EVP_`+`PKCS7`+`HMAC`+`SHA256`
同时出现是 OpenSSL 的强指纹）。**强度 HIGH（存在）/ MEDIUM（与 8081 绑定，
因为 16 B 块与 ECB 特征独立成立）。**

> 与主线的既有结论不冲突：主线验证的是 `Base.dll` **导入表**里没有 CryptoAPI。
> AES 是**内置**的，所以当然不在导入表里。

---

## 4. 密钥来源：已排查的方向与否定结果

### 4.1 TASData.dat / TclsQmFix.dat / TCLS 交接块

| 文件 | 大小 | SHA-256（前 16） | 首 8 字节 |
|---|---|---|---|
| `C:\ProgramData\Tencent\TAS\TASData.dat` | 240 | `2d55070d4e235c38` | `92 6f 7b d9 e9 2f 31 1a` |
| `CODOLServer\tasdata_sample.bin` | 240 | `2d55070d4e235c38` | 同上（**同一文件副本**） |
| `COD OL\components\tclsqmfix\TclsQmFix.dat` | 784 | `ddd605bdff41a984` | `bd ee 29 fa 2a 48 d4 15` |

* 两者都**高熵、无 ASCII**，与 `config_mp.cfg` 同族外观。
* 与 `TASData.dat` 同目录下**没有**任何 key/iv 伴随文件。
* 用 §1.4 的 1177 key 双重尝试（enc/dec）**全部失败**。

**TCLS 交接块**：`hits.jsonl` 给出唯一来源 ——
`VA 0x146C4861` / `0x146C487E`：
```
"%allusersprofile%...\application data\tencent\tas\TASData.dat"
"%s%s"
"TCLS_SHAREDMEMEMORY.%s%d"
```

即映射名格式 = `TCLS_SHAREDMEMEMORY.<exeName><pid>`，**大小固定 1964 B**
（`logs\shm_*.jsonl` 中 6 次独立运行全部 `"size": 1964`）。

**本机实测**：用 `OpenFileMappingW(FILE_MAP_READ)` 只读尝试
`TCLS_SHAREDMEMEMORY{9684|14232|9768}`（及 `Local\`/`Global\` 前缀）
**全部 `GetLastError=2 (FILE_NOT_FOUND)`** ⇒ 当前进程树**未创建**该映射
（`_read_tcls_shm.py`）。**1964 B 也装不下任何 256 B 密钥表 + 上下文**。

⇒ **TASData/TclsQmFix/TCLS 交接块不是 8081 密钥来源。强度 MEDIUM（否定，
依据是密钥长度与作用域不匹配 + 1177-key 全失败）。**

### 4.2 运行时 ticket / seed 字段：**是 Demonware/Blaze，不是 TQoS**

`hits.jsonl` 中 `iv_seed` / `lsg_server_ticket` / `server_ticket` /
`client_ticket` / `cd_key` / `auth_task` 全部聚在 **`VA 0x00D5A0EC`–`0x00D5A233`**
一个连续簇里。运行时明文（`engine_best.bin`，VA `0x00D5A0E8`）：

```
00D5A0E8  "lsg_server_ticket" 00 00 00
00D5A0FC  "lsg_server_ticket_size" 00 00
00D5A114  "iv_seed" 00
00D5A11C  "%s://%s:%d/%s/title/%d/queue/%d/member/%llu" 00
00D5A148  "https" 00 00 00
00D5A150  "v1.0" 00 00 00 00
00D5A158  "DW-Ticket-Seed" 00 00
00D5A168  "DW-Client-Ticket-Size" 00 00 00
00D5A180  "DW-Client-Ticket" 00 00 00 00
00D5A194  "DW-Server-Ticket-Size" 00 00 00
00D5A1AC  "DW-Server-Ticket" 00 00 00 00
00D5A1C0  "Transfer-Encoding" 00 00 00
00D5A1D8  "Content-Type" 00 00 00 00
00D5A1E8  "application/json" 00 00 00 00
00D5A228  "auth_task" 00*7
00D5A238  "43FCB2ACF2D72593DD7CD1C69E0F03C07229F4C83166F7B05BA0C5FE3AA3A2D93EK2"
00D5A290  "extended_data"
00D5A2A0  "license_id" 00 00
00D5A2AC  "user_id" 00
00D5A2B4  "time_to_live" 00 00 00 00
00D5A2C4  "cd_key" 00 00
00D5A2CC  "https://%s:%d/auth/" 00
00D5A2DD  "ciphertext"
00D5A31C  "server_ticket" 00 00 00
00D5A32C  "client_ticket" 00 00 00
00D5A33C  "356c4bc3" 00 00 00 00
```

**判定（HIGH）**：`iv_seed` 与 `DW-Ticket-Seed` / `DW-Client-Ticket` /
`DW-Server-Ticket` 是 **Demonware (Blaze) 的 HTTP 头族**，服务于
`https://%s:%d/auth/` 这条**认证通道**，**与 8081 的 TQoS 二进制通道无关**。

* `43FCB2AC…`（末尾 `3EK2` 是变体 `3DES`/`2KEY` 风格标记）也是**同一
  `auth_task` 族**（紧邻 `auth_task\0` + 7 个 NUL 填充），**不是 TQoS 密钥**。
  → 主报告 §「`VA 0x00D5A228` 常量用途未证」**现在已证：Blaze auth_task 材料**。
* `356c4bc3`（`0x00D5A33C`）是 `server_ticket`/`client_ticket` 之间的
  **16 字节对齐后的字符串**，前后是 `00 00 00 00`，之后唯一（引用/长度/字符串）
  结构 ⇒ **是字符串字面量，不是 IV**。

**否定**：这些字段**不是** 8081 密钥来源。**强度 HIGH。**

### 4.3 8081 的密钥来源

**UNKNOWN。**

已确证：
1. 不在 `Base.dll` 磁盘明文（`.tls` 全程密文，且 `CryptImportKey` 等 CryptoAPI 零命中）。
2. 不在 `TASData.dat` / `TclsQmFix.dat`（1177-key 全失败）。
3. 不是 `qos_cs`/`qos_ss` 表（跨快照 0 字节差异 ⇒ 编译期常量）。
4. 不是 `iv_seed`/`356c4bc3`/`43FCB2AC…` 这一族（属 Demonware auth）。

**最可能（待验证，MEDIUM）**：密钥来自 **TQoS 会话建立期**，
即 8000/UDP 的 `QOS_GET_REQ`/`QOS_GET_RES` 握手（`Seq` 回显 `0x7da1`、
`BusinessID=100`）之后，由服务器应答携带的 `QosList` 里的密钥材料派生 ——
但**本报告输入中 8000 只有 24 B 骨架，BodyLen=8 装不下密钥**，
所以**该方向无法用现有输入证实或否证**。

---

## 5. 8000/UDP 参考帧与 `0x18` 的最终语义（HIGH）

实测唯一一手字节对（`SINGLE_V0B\local_listeners.jsonl`）：

```
REQ   75 72 0010 0008 0003 0000 000b 00007da1 00000064 0018 0000   (24 B)
       'ur'      8     3      11    seq      BizID=100  0x18
```

字段（大端）：

| 偏移 | 宽 | 值 | 语义 | 强度 |
|---|---|---|---|---|
| 0 | u16 | `'ur'` | `QOSCSPkgHead.Magic` | **HIGH**（=`QOS_CS_MAGIC` 表值） |
| 2 | u16 | 16 | `ruHeadLen` | **HIGH** |
| 4 | u16 | 8 | `BodyLen` | **HIGH** |
| 6 | u16 | 3 | `Cmd` = `QOS_GET_REQ` | HIGH |
| 8 | u16 | 0 | `ProtoVer` | HIGH |
| 10 | u16 | 11 | (未命名) | LOW |
| 12 | u32 | `0x00007da1` | `Seq`（应答回显） | HIGH |
| 16 | u32 | 100 | `BusinessID`（应答回显） | HIGH |
| 20 | u16 | **`0x18`=24** | **整个包的长度 = `ruHeadLen`+`BodyLen` = 16+8 = 24** | **HIGH** |
| 22 | u16 | 0 | 填充/保留 | MEDIUM |

> **`0x18` = 24 是请求字节长度，不是"24 项"。** 三处自洽
> （`16+8=24`，包长 24，字段值 24）。**强度 HIGH。**

与 `qos_cs` 表交叉验证：`QOS_CS_MAX_GAMESVR = 24`、`QOS_CS_MAX_CONNDIP = 24`
**恰好也是 24**，说明 `0x18` 这个数在该协议族里被复用为"上限/长度"，
但**在这一帧里它就是长度**。

---

## 6. 能否造应答？—— 直接可用的回答

**不能可靠造出合法 8081 应答。** 原因（全部机械可证）：

1. **必须**先有正确的 AES key（或等价块密码 key）——**UNKNOWN**（§4.3）。
2. 密钥用了 **16 字节块 + 无 IV**（§1.2），所以**逐块 ECB 加密**：
   `ciphertext_block = E_key(plaintext_block)`，
   明文长度必须**恰好填满 16 B 的整数倍**，最后 4 字节**明文**尾。
3. 因此合法应答的构型是：
   ```
   [ k 个 16 B 密文块 ]  ||  tail4
   其中 k*16 = len - 4，tail4 = 00 00 <u16be>
   ```
   **但没有 key，这个式子无法求值。**

可以用作**探测**（不依赖 key）的最小改动：

```python
def build_8081_echo(req: bytes) -> bytes:
    """复用请求的密文块（合法 ECB 密文，因为块是自洽的），只改明文尾。
       若客户端只校验长度/尾部，可能被接受；若校验明文内容，则被丢弃。
       len 保持为 4 的倍数且 (len-4)%16==0。"""
    assert (len(req) - 4) % 16 == 0
    return req[:-4] + b'\x00\x00' + req[-2:]
```

**判定客户端是否真的校验 8081 明文的可靠判据**：观察是否出现**新包**
（新长度 / 新端口 / TCP 连接 / `[100]` 之后的下一阶段）。

---

## 7. 结论强度汇总

| 结论 | 强度 |
|---|---|
| 8081 = 16 B 块分组密码，`(len-4)%16==0`（9/9） | **HIGH** |
| 无 per-packet IV（包 #6 内精确重复块，偏移 464/592） | **HIGH** |
| `tail4 = 00 00 \|\| u16be`，在分组之外 | **HIGH** |
| `QOS_CS_MAGIC` = ASCII `"ru"`；`QOS_SS_MAGIC` = ASCII `"su"` | **HIGH** |
| `0x18`=24 是请求长度，不是项数 | **HIGH** |
| `qos_cs`/`qos_ss` 表是编译期常量（跨快照 0 字节差） | **HIGH** |
| `.tls` 磁盘为密文，运行时镜像为明文；无固定 XOR 关系 | **HIGH** |
| `.tls` 内置 OpenSSL 风格 AES（逆 S-box 精确匹配） | **HIGH**（存在）|
| `iv_seed`/`DW-*-Ticket`/`43FCB2AC…`/`356c4bc3` 属 Demonware/Blaze auth | **HIGH** |
| 8081 不是 TAS 流密码（1177 key 全失败） | **HIGH** |
| 8081 不是候选 140-key 的 AES | **HIGH** |
| 8081 密钥来自 8000 握手期派生 | MEDIUM（方向） |
| **8081 密钥的具体来源/派生函数** | **UNKNOWN** |

---

## 8. 本次新增脚本（全部只读）

| 脚本 | 用途 |
|---|---|
| `CODOLServer\_qoskey_probe.py` | KEY_CONTEXT 区域 + 8081 结构 + shm 证据 + TAS 文件 |
| `CODOLServer\_qoskey_probe2.py` | ticket/iv_seed 簇 + `qos_cs`/`qos_ss` 命中定位 |
| `CODOLServer\_qoskey_probe3.py` | 磁盘 `.tls` 原始十六进制（证明是密文） |
| `CODOLServer\_qoskey_probe4.py` | 运行时快照逐字节布局 + 跨快照差分 |
| `CODOLServer\_qoskey_probe5.py` | `.tls` 运行时窗口范围 + magic 前导 |
| `CODOLServer\_qoskey_ecb.py` | 16 B 对齐与重复块检测 + 密码学指纹 |
| `CODOLServer\_qoskey_transform.py` | 磁盘↔运行时关系（证明非 XOR） |
| `CODOLServer\_qoskey_aes.py` | 140 候选 key 的 AES 试探（全失败） |
| `CODOLServer\_qoskey_final.py` | 8081 块计数/尾部分解 + 8000 参考帧 |
| `CODOLServer\_read_tcls_shm.py` | 只读打开 TCLS 命名映射（未找到） |
| `CODOLServer\_verify_tls_mirror.py` | `.tls` 镜像关系验证 |
| `CODOLServer\_scan_engine_dumps.py` | 运行时快照关键字/标记扫描 |
| `CODOLServer\_try_tas_filetime.py` | FILETIME 派生 key 的 TAS 全面尝试 |

---

## 9. 下一步（按性价比排序）

1. **确定 AES mode 与 key 位置**：在运行时快照里定位
   `0x00C84C40`（逆 S-box）附近的 **key expansion 例程**，
   反查其 `memcpy` 源头 —— 这是找 key 材料最直接的路径。
2. **抓一份 `BodyLen>8` 的 8000/UDP 应答**（当前只有 24 B 骨架），
   其中可能直接携带 `QosList`/密钥材料。
3. **确认 AES 是否真用于 8081**：把 §1.2 的"块 29==块 37"作为落点，
   在解密例程上下断/插桩（**需另开授权**，本报告未做）。
4. 若要绕过而不是破解：8081 是**出向上报**，`host_redirect.log` 显示
   `tqos.gamesafe.qq.com` 已被重定向到本机 8081。
   可直接观察客户端是否**等待** 8081 应答；若否，此路非关键路径。
