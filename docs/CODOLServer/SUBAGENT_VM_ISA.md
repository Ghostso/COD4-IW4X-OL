# `.tvm0` / 引擎区 / AES 装载点 —— 静态取证报告

日期：2026-09-25
目标：`COD OL\codoMP_client_shipRetailBase.dll`（60,327,992 B）
范围：**纯磁盘只读静态分析**。未启动游戏、未注入、未改网络。
证据来源：PE 节表 + capstone + 既有运行时快照
`ENGINE_DUMP_20260925_114204\engine\engine_best.bin`（5,050,368 B）。

---

## 0. 关键结论（先纠正任务前提）

| # | 结论 | 强度 |
|---|---|---|
| 1 | **`0x994000..0xCA7890` 不属于 `.tvm0`。** 该区间落在 `.rdata/.data/.idata2/.rsrc2/.tls`，与 `.tvm0` 重叠 **0 字节** | **HIGH** |
| 2 | **“这段磁盘为零”不成立。** `0x994000` 磁盘实测为 `e3e82c7f8bfe13c0fa548efe...`，不是 0 | **HIGH** |
| 3 | `.tls` 磁盘↔运行时差异是**按块变化的 keystream**，不是固定 XOR；`0xC84C40` 处磁盘 `42ad3fe0...` vs 运行时 `52096ad5...`（AES invS-box） | **HIGH** |
| 4 | 在被认为的引擎窗口内**没有找到 VM dispatch loop**；`.tvm0` 起头 `fa 5b 42 c6…` 反汇编为 `cli; pop ebx; inc edx`，不是合法函数入口 | **HIGH（样本内否定）** |
| 5 | 该 DLL 内嵌 **OpenSSL 0.9.8zg（2015-06-11）和 1.1.0k（2019-05-28）**，含完整 AES S-box / invS-box / Te0 / rcon 表 | **HIGH** |
| 6 | AES **key-expansion 强候选**：`.text` 三处 xref 指向 rcon 表 `.rdata:0x782D04`，位于 RVA `0x32090E / 0x320A48 / 0x320BAE` | **MEDIUM-HIGH** |
| 7 | `.text` 的 AES T-table/invS-box 轮函数分布在 RVA `0x3218EB` 一带（x86 片段见 §4） | **HIGH（代码事实）** |
| 8 | **AES key 的静态装载点：UNKNOWN**。密钥是运行时参数，不在磁盘镜像里；`.tvm0` VM ISA：**UNKNOWN / 未证实存在** | — |

---

## 1. `.tvm0` 的真实位置与形态

节表：

| 节 | RVA 起 | raw 起 | raw 大小 |
|---|---:|---:|---:|
| `.text` | `0x001000` | `0x000400` | `0x741C00` |
| `.rdata` | `0x743000` | `0x742000` | `0x26B200` |
| `.data` | `0x9AF000` | `0x9AD200` | `0x14AA00` |
| `.idata2` | `0xB02000` | `0xAF7C00` | `0x5000` |
| `.rsrc2` | `0xB07000` | `0xAFCC00` | `0x2C00` |
| `.tls` | `0xB0A000` | `0xAFF800` | `0xED2600` |
| **`.tvm0`** | **`0x19DD000`** | **`0x19D1E00`** | **`0x1F5D600`** |

`0x994000..0xCA7890` 与各节重叠量：

```
.rdata   107008 B
.data   1354240 B
.idata2   20480 B
.rsrc2    11264 B
.tls    1693840 B
.tvm0         0 B
```

**⇒ `.tvm0` 与所谓“引擎代码区”完全不是同一对象。**

`.tvm0` 头 64 B：

```
019DD000  fa 5b 42 c6 e7 49 f1 1a 6a 7c fe b7 0d 0a ee 47
019DD010  c6 5c 67 91 35 6a 7c fe b7 0d 0a ee 47 c6 4d 0c
019DD020  4b 4e d5 27 01 b8 0d fa 5b 42 c6 bf cb 74 dc d5
019DD030  27 01 b8 0d ca 78 9d c4 3b 95 54 c5 d5 27 01 b8
019DD040  0d fa 5b 42 c6 e4 3e f2 dc fa 88 04 b8 0d fa 5b
019DD050  42 c6 19 1c 59 36 d5 27 01 b8 0d fa 5b 42 c6 cc
```

capstone(x86-32) 从 `.tvm0` 起头：

```
119DD000  cli
119DD001  pop ebx
119DD002  inc edx
```

`.tvm0` 统计（首 1 MB）：
* 熵 6.63–7.41 / 8.0
* `55 8B EC` 函数序言 **435** 次
* `CC CC CC CC` 填充 **1** 次（整段 12.13% 为零字节）

⇒ 它不是典型 x86 `.text`；更像**高熵打包数据/编码块**。
但“它是 VM bytecode、存在 dispatch loop”**没有证据**。**VM ISA = UNKNOWN。**

---

## 2. 引擎窗口的真实归属与磁盘字节

| RVA | 归属节 | 磁盘字节（前 64 B） | 运行时快照 |
|---|---|---|---|
| `0x994000` | `.rdata` | `e3e82c7f8bfe13c0fa548efe3473fdbf…` | `d28b464080785400742d8b45ec8b7508…` |
| `0x9A0000` | `.rdata` | `696e20646174616261736500496e7661…` | `16c1e8098d4d90a8…` |
| `0xA00000` | `.data` | `01000000ffffffff…` | `3fff9f004bff9f00…` |
| `0xB0A000` | `.tls` | `98931fb24c5a3400c2ed9b0162900145…` | `e85b0fffff83c40485c07e63…` |
| `0xC84C40` | `.tls` | `42ad3fe071f99ceac2faed661f6cf9fc…` | `52096ad53036a538bf40a39e81f3d7fb…` |
| `0xCA0000` | `.tls` | `68989b7ef990f493b46987ca6cf93f74…` | `b8009c9b0033c9a3183ce800…` |

**⇒ “0x994000 区磁盘为零、运行时由 `.tvm0` 解密写入”这一前提不成立。**

### 2.1 `.tls` 磁盘→运行时的关系

对同一 RVA 做 `runtime ^ disk`，8 字节块：

```
0xB0A000  xor = 70c8104db3d9f004
0xC84C40  xor = 10a4553541cf39d27dba4ef89e9f2e07…
```

* 不是固定 4/8/16 字节周期；
* 抽 414 页，所有 8 字节 xor 块互不相同；
* 运行时的 `.tls`（`0xB0A000` 起）具有 x86 代码字节分布（`0x00` 362/4096、`0x8B` 192、`0xFF` 186、`0x83` 156），并含 `CC` 填充。

⇒ **是“密文磁盘 → 运行时明文代码/数据”的变换**；具体算法 **UNKNOWN**。

### 2.2 引擎区的“写引用”

* 对运行时窗口做线性 capstone 反汇编（146,988 条指令）：
  **没有** `mov [绝对地址], …` 命中 `0x994000..0xCA7890`；
* 对磁盘做绝对 dword 搜索：
  * `0x00994000` 仅 2 处：`.tls@0x173FFA8`、`.tls@0x178943D`
  * `0x009A0000` 多处，分布在 `.rdata/.data/.tls`
  * `.tvm0` 中**只有零散命中的 `0x9A0000 / 0xC00000` 字面量**
* **没有找到** `DEST=0x994000` 的明确 `rep movs` / `memcpy` 调用。

⇒ **“由 `.tvm0` 把字节写进 0x994000”无法机械证明；写引用 = UNKNOWN。**

---

## 3. `.tvm0` 与 0x994000 的关系：排除性证据

这三条同时成立时，`.tvm0` 不可能是 0x994000 的写入方：

1. 0x994000 区间与 `.tvm0` **0 字节重叠**（§1）。
2. 该区间磁盘**非零**（§2），并且运行时是另一份不同的字节。
3. 在该区间运行时镜像里，**没有绝对写指令**；`.tvm0` 也不含指向 `0x994000` 的集中指针表。

因此，任务 a/b 的预期对象应是 `.tls`/`.rdata` 的加载/解密链，而不是 `.tvm0` VM。
如果主线坚持研究 `.tvm0`，需要先回答它**到底映射到何处、由谁消费**；目前
`UNKNOWN`。

---

## 4. AES 实现与 key-expansion 的精确位置

### 4.1 内嵌 OpenSSL

```
.rdata 0x968A60  "OpenSSL 0.9.8zg 11 Jun 2015"
.rdata 0x7C48AC  "OpenSSL 1.1.0k  28 May 2019"
.rdata 0x74D2C8  "aes-128-ecb"
.rdata 0x74D208  "aes-256-ecb"
.rdata 0x989E54  "AES_INIT_KEY"
```

### 4.2 AES 表的精确位置

| 表 | 文件/RVA 位置 |
|---|---|
| AES S-box | `.data 0x9CD470`、`.data 0xA04608`、`.data 0xAF61B8` |
| AES invS-box | `.rdata 0x782C00`、`.rdata 0x983F10` |
| AES Te0 | `.rdata 0x780C00`、`.rdata 0x981F10` |
| AES Te0 变体 | `.rdata 0x781000`、`.rdata 0x982310` |
| AES rcon | `.rdata 0x782D04`、`.data 0x9C…` |

（另有 `.tls` 副本 `0xF69B09`、`0x1237668`，属于运行时区。）

### 4.3 key-expansion 的三个 xref（最强定位）

`.rdata 0x782D04`（rcon）被 `.text` 三处代码引用：

```
file_off 0x31FD0E -> .text RVA 0x32090E  (link VA 0x1032090E)
file_off 0x31FE48 -> .text RVA 0x320A48
file_off 0x31FFAE -> .text RVA 0x320BAE
```

这三处正落在 AES key schedule 通常访问 rcon[] 的位置。按 OpenSSL 0.9.8 的
`AES_set_encrypt_key` 语义，**该函数体极可能包含 RVA `0x320900..0x320C00`**。
**强度 MEDIUM-HIGH**；精确函数边界尚未用调试/符号验证。

### 4.4 AES 轮函数的 x86 片段（精确）

`.text` 的 AES T-table 轮函数引用 `.rdata 0x782C00`（invS-box）。代表性指令：

```
103218E8  movzx eax, byte ptr [eax + 0x10782C00]
1032192B  xor   eax, dword ptr [ebx]
1032192D  mov   edi, eax
1032192F  ror   edi, 8
10321932  and   edi, 0xff00ff00
10321938  rol   eax, 8
1032193B  and   eax, 0xff00ff
10321940  or    edi, eax
10321946  mov   dword ptr [eax], edi
```

同族代码还引用 `.rdata 0x782000 / 0x782400 / 0x782800` 的 T-table。
该代码块的具体函数名未证；按 OpenSSL 结构，属于 AES 加解密/模式实现。

### 4.5 key 装载点

* “AES key 的装载点”= **调用 key-expansion 函数前把 16/24/32 字节 key
  传给 RVA `0x320900` 一族的调用者**；
* 静态镜像中**没有**可直接称为“key”的常量；
* 因此 **key 装载调用者 = UNKNOWN**，需在 `0x320900` 函数入口下断或
  做调用图回溯源。

---

## 5. 结论强度汇总

| 结论 | 强度 |
|---|---|
| `.tvm0` 与 0x994000 区间 0 重叠 | **HIGH** |
| 0x994000 区磁盘非零 | **HIGH** |
| `.tls` 磁盘↔运行时为非固定 XOR 变换 | **HIGH** |
| 运行时 0x994000 区无绝对写指令 | **HIGH** |
| `.tvm0` 为高熵数据块（非典型 x86） | **HIGH** |
| `.tvm0` 存在 VM dispatch loop | **UNKNOWN（未证实）** |
| 内嵌 OpenSSL 0.9.8zg/1.1.0k + AES 全套表 | **HIGH** |
| key-expansion 候选 RVA 0x32090E/0x320A48/0x320BAE | **MEDIUM-HIGH** |
| AES 轮函数 RVA 0x3218EB 一带 | **HIGH** |
| AES key 装载调用者 | **UNKNOWN** |

---

## 6. 本次新增只读脚本

| 脚本 | 用途 |
|---|---|
| `_vm_isa_probe1.py` | PE/节/`.tvm0` 头/字符串/绝对引用 |
| `_vm_isa_probe2.py` | engine 窗口归属 + `.tvm0` 统计 |
| `_vm_isa_probe3.py` | 磁盘/运行时节覆盖与零值验证 |
| `_vm_isa_probe4.py` | `.tls` 磁盘↔运行时 XOR keystream |
| `_vm_isa_probe5.py` | `.tls` 掩码分布/代码性判定 |
| `_vm_isa_probe6.py` | 引擎窗口 capstone、S-box/窗口 xref |
| `_vm_isa_probe7.py` | 全文件 AES S-box/T-table/字符串 |
| `_vm_isa_probe8.py` | OpenSSL 版本、AES 表、`.tvm0` 形态 |
| `_vm_isa_probe9.py` | AES invS-box 代码 xref 反汇编 |
| `_vm_isa_probe10.py` | AES rcon xref / key-expansion 候选 |
