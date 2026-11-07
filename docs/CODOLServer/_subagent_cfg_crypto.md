# CODOL `players\config_mp.cfg` 加解密逆向 —— 中间状态报告

日期：2026-09-25
状态：**未解出明文（结论已收窄，失败假设已逐条排除）**
方式：纯只读静态分析 + 离线密码学试探。未启动游戏、未注入、未改网络/路由/DNS/防火墙/网卡，未触碰 985 与 ACE。

---

## 0. 结论先行（中间状态）

1. **加密类型判定：高置信排除"明文/简单混淆/单字节 XOR/直接 zlib 封装"；无法排除"流密码（含 CTR/OFB 类）或"先生成密钥流再做整文件封装"。**
   - 判据：整文件熵 **7.9821 / 8.0**，每 512 字节熵 7.50–7.65，无任何重复 16 字节块（490 个块几乎全不同），无 NUL，无魔数命中。
   - 长度 **7846 = 16×490 + 6**，不是 16 的倍数 ⇒ 若为分组密码，**必然是流式模式（CTR/OFB/CFB）或带尾部残块处理**，不可能是裸 ECB/CBC（否则尾部无法对齐）。
2. **`config_mp.cfg` 不是 zlib/gzip 容器**：对偏移 0..63 全部尝试 `zlib.decompress` 与 raw deflate，**零命中**。
3. **单字节 XOR / 单字节加减全部失败**：256 个 key 全试，最高可打印率仅 **0.447**（正常 `set`/`bind` 文本 cfg 应在 0.9 以上）。键长 1..8 的周期异或同样无结构。
4. **EXE 内部没有解开所需的 API 面**：`codoMP_client_shipRetail.exe` 的导入表**只有一项** —— `codoMP_client_shipRetailBase.dll` 的序号 1（IAT `0x00E9DC665`）。**没有任何 KERNEL32/ADVAPI32 文件或加密 API 的静态导入**（下面 §2 给出字节级证据）。
5. **`config_mp.cfg` 字符串位于数据区、不是代码直接引用**：字符串本体在 RVA `0x009BCFE0`（VA `0x00DBCFE0`），全文件对该 VA 的 32 位立即数引用**只有 1 处**，位于 RVA `0x000AF56D`，而该处与 `0x000A7FDC`（`.cfg` 引用点）都落在**不可执行的 `.tp3` 数据区**，反汇编为无效指令流。⇒ 它是 dvar/资源索引表项，**不能当作"读取该文件的函数"的锚点**。
6. 因此：**cfg 的真实读取/解密实现位于 `codoMP_client_shipRetailBase.dll`（60,327,992 字节）或 EXE/Base 的 `.tvm0`（VMProtect）区**，需要用"API 字符串 + `GetProcAddress` 动态解析"的思路去追，而不是靠字符串交叉引用。

---

## 1. 文件字节级事实（可复核）

### 1.1 三个文件的基础测量

| 文件 | 大小 | SHA-256 | 熵 | 首 16 字节 |
|---|---|---|---|---|
| `COD OL\players\config_mp.cfg` | 7846 | `f1bfbf230c684ec87e2ad2ea520f0d7a8501d2c61215f056472a917e9bac1e22` | 7.9821 | `bf c2 09 76 95 29 11 ca 82 70 9e ac 4a 65 4e e1` |
| `COD OL\players\settings_m.zip.iw4` | 82 | `ae34e92443f1ab90ed4e4fe886a57b44cb6174370f8b9f702c203c7f798cdc9a` | 3.3695 | `53 45 4d 56` = ASCII **`SEMV`** |
| `COD OL\players\settings_c.zip.iw4` | 167 | `77af851aec423408fe584871738a9c2d6e0e06f64233fd275343ebb5bec52a1c` | 4.4083 | `53 45 4d 56` = ASCII **`SEMV`** |
| `COD OL\components\tclsqmfix\TclsQmFix.dat` | 784 | `ddd605bdff41a9847a1770689021cecc237178fc647ea34a5e19c99ef3f33670` | 7.7661 | `bd ee 29 fa 2a 48 d4 15 67 e8 2f 69 83 19 7d 40` |

`config_mp.cfg` 分块熵（每 512 字节）：

```
0000 7.5246   0600 7.6238   0c00 7.6493   1200 7.5900   1800 7.6054
0200 7.5728   0800 7.6269   0e00 7.6014   1400 7.6242   1a00 7.5643
0400 7.6170   0a00 7.6401   1000 7.6467   1600 7.5058   1c00 7.5991
                                   1e00 6.8508   <- 尾块（7846-7680=166 字节）
```

尾部一块熵 6.85 是**尾部长度效应**（只有 166 字节），不是结构性变化。

### 1.2 长度对齐分析（关键判据）

```
len = 7846 = 16 × 490 + 6   (mod16 = 6, mod8 = 6, mod4 = 2)
```

对比参照物：`settings_*.zip.iw4` 是**未加密**、长度任意、低熵（3.4/4.4）的紧凑 `SEMV` 二进制设置块 ——
说明 IW4 原生设置块本身**不需要加密**，`config_mp.cfg` 的高熵只能来自额外的加密/封装层。

### 1.3 排除"明文/弱混淆"的量化证据

* 全文件熵 7.9821（8.0 为随机上限）；单字节直方图接近均匀。
* 16 字节重复块：**0 个真正重复块**（490 个 16B 块几乎全不同）。
* 移位自相关（`D[i] == D[i-lag]`）在 lag 1..256 上全部落在 **0.0027–0.0048**，与随机期望（1/256 = 0.0039）一致 —— 无周期结构，排除"重复密钥流短周期"和"块内填充模式"。
* 单字节 XOR：256 个 key 全试，最高可打印率 **0.447**。
* 单字节加法：256 个 key 全试，最高可打印率 **0.457**。
* zlib/gzip/deflate：偏移 0..63 全部尝试 `zlib.decompress` 与 raw deflate(-15)，**零命中**；头部无 `78 01/5e/9c/da`、无 `1f 8b`、无 `PK\x03\x04`。

> 结论强度：**HIGH**（对"明文/单字节混淆/直接压缩"的排除）、**MEDIUM**（对"流密码"的判定，因为密钥流不可从密文单独证伪）。

---

## 2. EXE 导入面证据（决定性）

`codoMP_client_shipRetail.exe`（32 位，ImageBase `0x00400000`，入口 RVA `0x0E5DC690`）：

```
节表（raw / vsize / rva）：
  .tp3  0x001000  0x593000  0x001000    (可执行+只读)
  .tp3  0x594000  0x016E000 0x8A8000    (哨兵表，只读)
  .tp3  0x702000  0x062000  0xA16000    (读写)
  .tp3  0x764000  0x001000  0xE5C8000
  .tp3  0x765000  0x00A000  0xE5C9000
  .tvm0 0x76F000  0x002000  0xE5D3000   (VMProtect，未读取)
  .tp3  0x771000  0x006000  0xE5D7000

导入表：总项数 = 1
  codoMP_client_shipRetailBase.dll  序号导入 IAT = 0x00E9DC665
```

即：**文件 IO（`CreateFileW`/`ReadFile`）与密码学 API（`CryptDecrypt`/`CryptEncrypt`）都没有静态导入**。
对这 10 个目标 API 做 `FF 15 <IAT>` 全 `.text` 扫描：**0 命中** —— 与"导入表只有 1 项"一致。

`codoMP_client_shipRetailBase.dll`（32 位，ImageBase `0x10000000`）：

```
节表：
  .text   0x000400   0x741C00   0x001000
  .rdata  0x742000   0x26B200   0x743000
  .data   0x9AD200   0x14AA00   0x9AF000
  .idata2 0xAF7C00   0x005000   0xB02000
  .rsrc2  0xAFCC00   0x00002C 0xB07000
  .tls    0xAFF800   0xED2600 0xB0A000
  .tvm0   0x19D1E00  0x1F5D600 0x19DD000
  .reloc  0x392F400  0x055E00   0x393B000

导入表：总项数 = 3
  kernel32.dll!LoadLibraryA     IAT = 0x109F6800
  kernel32.dll!GetProcAddress   IAT = 0x109F6804
  libcef.dll!cef_string_utf16_clear  IAT = 0x109F6841
```

Base.dll 同样**没有**静态文件/加密 API，只有 `LoadLibraryA` + `GetProcAddress` 这一对 ——
**所有文件读写与加解密都通过运行时动态解析**。这就是为什么"在导入表里找 `ReadFile` 调用点"这条路彻底走不通。

Base.dll 中相关字符串（供后续定位动态解析点使用）：

```
LoadLibrary  ascii  0x7AB7FC 0x950568 0x9505F6 0x9506A4 0x950A68 0x95631E 0x9671E8 0x9ABBF8 0x9ACB08 0x9F4A1B 0xAFA234 …
GetProcAddress ascii 0x7454D8 0x95032E 0x95B8D2 0x95B9C6 0x95C10A 0x95C1F3 0x9ABBE6 0x9F4A2A 0xAF9FDA 0xAFAFE6
CreateFileW  ascii  0x950670 0x9ABD30 0xAFA348 0xAFB142
CreateFileA  ascii  0x950778 0x9ABBB0 0xAFA458 0xAFAFAE
ReadFile     ascii  0x88B77B 0x88B960 0x88D7CC 0x88D7E0 0x950638 0x9ABB96 0x9DE74A 0x9DE7B6 0xAFA30E …
CryptDecrypt ascii  0x951792 0xAF9846
zlib / inflate / deflate / uncompress：0x74DD9C、0x7781A0、0x7A79F9、0x85175C、0x9830E9、0x9A1528 等多处
```

`config_mp.cfg` / `players\` / `SEMV` 在 **Base.dll 中零命中** ⇒ 这些名字只由 EXE 侧的 dvar 表携带。

---

## 3. `config_mp.cfg` 字符串的引用落点（为什么它不是函数锚点）

字符串位置（EXE）：

```
config_mp.cfg      raw 0x006A8FE0  RVA 0x009BCFE0  VA 0x00DBCFE0
settings_c.zip.iw4 raw 0x006A11F8  RVA 0x009B51F8  VA 0x00DB51F8
settings_m.zip.iw4 raw 0x006A120C  RVA 0x009B520C  VA 0x00DB520C
players            raw 0x006A11F0  RVA 0x009B51F0  VA 0x00DB51F0
SEMV               raw 0x00697754  RVA 0x009AB754  VA 0x00DAB754
exec configure_mp.cfg  raw 0x006A93DC
```

对这些 VA 做全文件 32 位立即数扫描：

| 目标 | 引用文件偏移 | 所在区 | 说明 |
|---|---|---|---|
| `config_mp.cfg` VA `0x00DBCFE0` | **`0x000AF56D`**（唯一） | `.tp3` 数据区 | 反汇编为 `loopne 0x004af53e` 等无效流 |
| `.cfg` VA `0x00DBCFF0` | `0x000A7FDC`（唯一） | `.tp3` 数据区 | 同上，非代码 |
| `settings_c.zip.iw4` | `0x00054C50` | `.tp3` 数据区 | — |
| `players` | `0x00054AE9`、`0x000A9408`、`0x000AF500` | `.tp3` 数据区 | — |
| `SEMV` | `0x00054792` | `.tp3` 数据区 | — |
| `tencent_config` | `0x0007BB2E` | `.tp3` 数据区 | — |
| `dw_config` | `0x000BBCE1`、`0x0027DF4D`、`0x0027FE80` | `.tp3` 数据区 | — |

**结论（HIGH）**：这些引用点都落在不可执行的数据区，**不是被代码 `push`/`lea` 引用的字符串**。
因此 `0x237C15` 这类"疑点"与 `config_mp.cfg` 没有可证实的因果关系 ——
独立审计（`COD OL\scripts\_out\sentinel_context_audit.txt`，同 SHA-256 `36997674b18f…`）已给出：

```
Raw bytes at RVA 0x237C15: ff 15 00 80 ca 00 a1 5c 41 49 86 00 f1 16 07 50
Self decode    : 00637C15 | ff150080ca00 | call dword ptr [0xca8000]
In STRICT_BOUNDARY graph : YES
In loose E8 graph        : NO
In ENTRY_CFG_STATIC graph: NO
Conventional raw prologue candidates [0x237400,0x237C15): 0
结论：MEDIUM —— 0x237C15 有重叠解码，未被确立为活函数边界；可能是重叠指令流或内嵌数据。
```

⇒ **先前"0x237C15 附近是 cfg 读取/解密函数"的猜测，本轮判定为不成立（UNSUPPORTED）。**
它属于 `0x00CA8000` 哨兵表（值形如 `0x800000xx`）的间接调用点族，与 dvar/cfg 无证据关联。

---

## 4. 已排除的算法假设（逐条）

| # | 假设 | 检验方式 | 结果 |
|---|---|---|---|
| 1 | 明文 / 简单混淆 | 熵 7.98、可打印率极低、无 ASCII 串 | **排除** |
| 2 | 单字节 XOR（256 key） | 全 key 扫描 | **排除**，最高可打印率 0.447 |
| 3 | 单字节加减（256 key） | 全 key 扫描 | **排除**，最高 0.457 |
| 4 | 周期 ≤8 的循环密钥 XOR | 由 `D[i]^D[i+p]` 反推周期 key，无可读输出 | **排除** |
| 5 | 直接 zlib/gzip/deflate | 偏移 0..63 全试 `zlib.decompress` / raw deflate | **排除**，零命中 |
| 6 | 裸 ECB/CBC 分组密码 | 长度 7846 非 16 倍数 | **排除**（除非带流式尾部处理） |
| 7 | Tenio TAS 流密码（MASK=`8A E6 9B F3 C1 7D 40 25` + MSVCRT LCG） | 既有 `_try_decrypt_cfg.py`，默认 key / 各文件时间 key / 全 0 / 全 11 | **排除**，可打印率 0.36–0.39 |
| 8 | TEA（16 轮大端） | 既有 `tea_cfg.py`，key=`1111111111111111` / `configconfigconf` | **排除** |
| 9 | EXE 静态导入 `ReadFile`/`CryptDecrypt` | 导入表 + `FF 15` 扫描 | **排除**，EXE 仅导入 1 项 |
| 10 | `0x237C15` 是 cfg 解密函数 | 引用点全在数据区 + 独立哨兵审计 | **排除（UNSUPPORTED）** |

---

## 5. 下一步应查的函数 / 偏移（按优先级）

1. **Base.dll `.text` 中 `GetProcAddress` 的 10 个调用点**
   `0x7454D8`（.rdata 串）、`0x95032E`、`0x95B8D2`、`0x95B9C6`、`0x95C10A`、`0x95C1F3`、`0x9ABBE6`、`0x9F4A2A`、`0xAF9FDA`、`0xAFAFE6`
   目标：找出为 `CreateFileW`/`ReadFile`/`CryptDecrypt` 填充 IAT 的那一处（字符串近邻为 `0x950638`、`0x950670`、`0x951792`、`0xAF9846`）。
2. **Base.dll IAT 槽 `0x109F6800` / `0x109F6804` 的写入点**
   即 `mov [0x109F6804], eax` 型指令 —— 这些是动态解析的唯一收口，能反向定位"谁在申请文件/加密 API"。
3. **Base.dll `.tvm0`（raw `0x19D1E00`，size `0x1F5D600`）**
   60 MB 模块里唯一的虚拟化区，体量与"整个游戏逻辑"相当；cfg 读取很可能在其中。需先确认 `.tvm0` 是否只是 `LoadLibrary` 目标（如反作弊），再决定是否触碰（**受"不要碰 ACE"约束，本轮未读取**）。
4. **`TclsQmFix.dat`（784 字节）与 `config_mp.cfg` 的同源判定**
   两者熵分别 7.7661 / 7.9821，长度恰好 784 与 7846 = 784×10 + 6。**这是目前唯一的结构线索**，但尚不足以证明同算法；需在拿到任一明文后回验。

---

## 6. 交付物状态

| 交付项 | 状态 |
|---|---|
| 判定加密类型 | 部分完成：**排除明文/单字节混淆/直接压缩/裸分组**；判定为流式或封装的密钥流（MEDIUM） |
| 定位读取代码 | **未定位**：EXE 无静态 API 面，字符串引用全在数据区（见 §3） |
| 反推 key 并解出明文 | **未完成**（因此 `CODOLServer\config_mp.decrypted.bin` 未生成） |
| 明文搜索服务器地址 | 无法执行（无明文） |

**未生成 `config_mp.decrypted.bin` 是刻意的**：在没有可验证明文的情况下写出猜测文件会污染后续分析。

---

## 7. 复现命令（只读）

```powershell
# 1) 基础测量（熵 / 魔数 / 重复块 / 可打印串）
python .\COD OL\scripts\cfgid.py players/config_mp.cfg --head 256

# 2) 既有失败假设复现（TAS / TEA）
python .\CODOLServer\_try_decrypt_cfg.py
python .\CODOLServer\_try_decrypt_startup.py

# 3) EXE / Base.dll 导入面与字符串位置
#    见本报告 §2、§3 的偏移；扫描脚本可复用 COD OL\scripts\_inspect_cfg_237c15.py 的 PE+capstone 基础设施
```

---
---

# 附录 A —— A/B/C 项机械证明（2026-09-25 追加）

本附录只记录**可机械复核**的事实（字节序列、偏移、指令编码），不含推测。
所有偏移原始数据源：`COD OL\codoMP_client_shipRetailBase.dll`
SHA-256 = `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`（60,327,992 字节）
ImageBase = `0x10000000`，PE32 (machine `0x14c`)，导出序号 1/2/3（无名）。

---

## A.1 修正：上一轮的 IAT 结论有误，此处更正

上一轮我写的 "IAT 槽 `0x109F6800` / `0x109F6804`" 是**把 `pefile` 报出的 `imp.address` 直接当成槽地址**。
本轮用原始 PE 头复核，结论**不变但需要精确化**：

原始导入目录（`ImportTable` RVA = `0x9F67B8`，size = `0x3C`，文件偏移 `0x9F49B8`）：

```
0x9F49B8  f4 67 9f 00 00 00 00 00 ff ff ff ff 0c 68 9f 00   OrigFT=0x9F67F4 Name=0x9F680C FT=0x9F6800
0x9F49CC  00 68 9f 00 39 68 9f 00 00 00 00 00 ff ff ff ff   OrigFT=0x9F6839 Name=0x9F6849 FT=0x9F6841
0x9F49D8  49 68 9f 00 41 68 9f 00 00 00 00 00 00 00 00 00   (空描述符结束)
```

即 **FirstThunk 数组的 RVA = `0x9F6800`**，其 VA = `0x109F6800`：

| 槽位 RVA | 槽位 VA | 名称 | hint |
|---|---|---|---|
| `0x9F6800` | `0x109F6800` | `LoadLibraryA` | 753 |
| `0x9F6804` | `0x109F6804` | `GetProcAddress` | 544 |
| `0x9F6841` | `0x109F6841` | `cef_string_utf16_clear`（libcef）| 0 |

**注意 `0x9F6841` 不是 4 字节对齐**（`0x9F6841 = 4×0x27DA10 + 1`）—— 这是 libcef 描述符 `FT=0x9F6841` 直接给出的，
说明第二个描述符的 FirstThunk 与第一个**不连续**，不能用"两个槽相邻"的假设。

原始 PE 头复核（`e_lfanew = 0x110`）：

```
machine                0x014c
NumberOfSections       8
SizeOfOptionalHeader   0x00E0
Magic                  0x010B   (PE32)
ImageBase              0x10000000
DataDirectory[1] ImportTable RVA 0x9F67B8  size 0x3C
DataDirectory[12] IAT      RVA 0x00000000  size 0x00000000   <-- 未声明
```

**IAT 目录为空是 Base.dll 的结构性特征**（与它自定义 `.idata2` 名称表一致）。

---

## A.2 IAT 槽的代码级引用：**零命中**（机械可证伪）

对 `LoadLibraryA`/`GetProcAddress` 两个槽，在**全部可执行节**（`.text`、`.tls`，排除 `.tvm0`）做穷举扫描。

### A.2.1 原始 dword 扫描（整个 60 MB 文件）

```
pattern  struct.pack('<I', 0x109F6800)   -> 命中 0 处
pattern  struct.pack('<I', 0x109F6804)   -> 命中 0 处
pattern  struct.pack('<I', 0x109F6841)   -> 命中 0 处
```

### A.2.2 全部常见间接调用/取址编码（整个文件字节扫描）

```
FF 15 00 68 9F 00   call dword ptr [0x109F6800]   -> 0
FF 15 04 68 9F 00   call dword ptr [0x109F6804]   -> 0
FF 25 00 68 9F 00   jmp  dword ptr [0x109F6800]   -> 0
FF 25 04 68 9F 00   jmp  dword ptr [0x109F6804]   -> 0
8B 05 00 68 9F 00   mov  eax, [0x109F6800]        -> 0
8B 05 04 68 9F 00   mov  eax, [0x109F6804]        -> 0
A3 00 68 9F 00      mov  [0x109F6800], eax        -> 0
A3 04 68 9F 00      mov  [0x109F6804], eax        -> 0
68 00 68 9F 00      push 0x109F6800                -> 0
68 04 68 9F 00      push 0x109F6804                -> 0
B9 00 68 9F 00      mov  ecx, 0x109F6800           -> 0
B9 04 68 9F 00      mov  ecx, 0x109F6804           -> 0
C7 05 00 68 9F 00 … mov  dword ptr [0x109F6800], imm32 -> 0
C7 05 04 68 9F 00 … mov  dword ptr [0x109F6804], imm32 -> 0
89 05 00/04 68 9F 00  mov  [slot], eax             -> 0
89 0D 04 68 9F 00     mov  [slot], ecx             -> 0
89 15 04 68 9F 00     mov  [slot], edx             -> 0
```

### A.2.3 反汇编级扫描（capstone，全部可执行节）

对 `.text`（RVA `0x1000`，size `0x742000`）与 `.tls`（RVA `0xB0A000`，size `0xED3000`）线性反汇编，
统计所有 `call dword ptr [绝对地址]` / `jmp dword ptr [绝对地址]`：

```
=== .text ===   (无输出：0 条)
=== .tls  ===   (无输出：0 条)
```

**A 项结论（强度：HIGH —— 机械可证伪的否定）**

> 在 Base.dll 的**可见原生代码**（`.text` + `.tls`，共 `0xED3000 + 0x742000 ≈ 15.5 MB`）中，
> **不存在任何对 IAT 槽 `0x109F6800` / `0x109F6804` 的指令级引用**——
> 既没有读（`call`/`jmp`/`mov r, [slot]`），也没有写（`mov [slot], r`）。
>
> ⇒ **"定位 GetProcAddress 的动态解析收口"这一任务，在可见原生代码范围内无解。**
> 该收口要么位于 `.tvm0`（VMProtect，未读取），要么由加载器直接完成而不经代码引用。

这不是"没找够"，而是穷举了 13 种编码 + 全节反汇编后的**确定性否定**。

---

## A.3 GetProcAddress / 目标 API 的名称常量：`hint + name` 自定义表

Base.dll 的 `.idata2`（RVA `0xB02000`，raw `0xAF7C00`，size `0x5000`，**不可执行**）
是一个**非标准导入表**：结构与 PE 标准 Import Name Table 相同（`u16 Hint` + NUL 结尾 ASCII），
但它不是被 PE 加载器消费的标准表（标准表只有 kernel32 的 2 项 + libcef 的 1 项）。

`.idata2` 共解析出 **660 条** `hint + name` 条目，覆盖 ADVAPI32 / KERNEL32 / GDI32 / USER32 / WS2_32 /
NETAPI32 / PSAPI / OLEAUT32 / SHELL32 / ole32 等。

已知 DLL 名称位置（全部在 `.idata2`）：

```
ADVAPI32.dll   raw 0xAF95BC  RVA 0xB039BC
USER32.dll     raw 0xAFBF4C  RVA 0xB0634C
GDI32.dll      raw 0xAF9BB6  RVA 0xB03FB6
WS2_32.dll     raw 0xAFC504  RVA 0xB06904
NETAPI32.dll   raw 0xAFBCA8  RVA 0xB060A8
PSAPI.DLL      raw 0xAFBCD0  RVA 0xB060D0
OLEAUT32.dll   raw 0xAFBCC2  RVA 0xB060C2
SHELL32.dll    raw 0xAFBE7A  RVA 0xB0627A
ole32.dll      raw 0xAFC90C  RVA 0xB06D0C
KERNEL32.dll   raw 0xAF9D5A  RVA 0xB0415A
kernel32.dll   raw 0x9F4A0C  RVA 0x9F680C  (标准导入描述符的 Name)
libcef.dll     raw 0x9F4A49  RVA 0x9F6849  (标准导入描述符的 Name)
```

---

## A.4 B 项：名称字符串 → 解析调用点 → 使用点 xref 表

方法：对每条 API 的名称 RVA `nrva = entry_rva + 2`，全文件搜索 `struct.pack('<I', nrva)`（即 32 位指针引用），
再对命中位置尝试以 1..15 字节回退反汇编，判定该引用是否落在**真指令的立即数/位移字段**内。

**结论：只有 2 个 API 名称有 32 位 RVA 引用，且都不在合法指令内。**

| API | hint | entry RVA | name RVA | name 文件偏移 | 指针引用文件偏移 | 引用 RVA | 所在节 | 是否指令边界 | 指令 |
|---|---|---|---|---|---|---|---|---|---|
| `CreateFileA` | 120 | `0xB04856` | `0xB04858` | `0xAFA456` | **`0x181D9FB`** | `0x18281FB` | **`.tls`** | **NO** | — |
| `ReadFile` | 872 | `0xB0470C` | `0xB0470E` | `0xAFA30C` | **`0x1700523`** | `0x170AD23` | **`.tls`** | **NO** | — |
| `CreateFileW` | 127 | `0xB04746` | `0xB04748` | `0xAFA346` | NONE | — | — | — | — |
| `CreateFileW` | 127 | `0xB05540` | `0xB05542` | `0xAFB140` | NONE | — | — | — | — |
| `CreateFileA` | 120 | `0xB053AC` | `0xB053AE` | `0xAFAFAC` | NONE | — | — | — | — |
| `ReadFile` | 872 | `0xB05390` | `0xB05392` | `0xAFAF90` | NONE | — | — | — | — |
| `WriteFile` | 1165 | `0xB04BF4` | `0xB04BF6` | `0xAFA7F4` | NONE | — | — | — | — |
| `WriteFile` | 1165 | `0xB055C4` | `0xB055C6` | `0xAFB1C4` | NONE | — | — | — | — |
| `SetFilePointer` | 991 | `0xB045EA` | `0xB045EC` | `0xAFA1EA` | NONE | — | — | — | — |
| `SetFilePointer` | 991 | `0xB05B52` | `0xB05B54` | `0xAFB752` | NONE | — | — | — | — |
| `SetFilePointerEx` | 992 | `0xB04C02` | `0xB04C04` | `0xAFA802` | NONE | — | — | — | — |
| `GetProcAddress` | 544 | `0xB043D8` | `0xB043DA` | `0xAF9FD8` | NONE | — | — | — | — |
| `GetProcAddress` | 544 | `0xB053E4` | `0xB053E6` | `0xAFAFE4` | NONE | — | — | — | — |
| `LoadLibraryA` | 753 | `0xB0477C` | `0xB0477E` | `0xAFA37C` | NONE | — | — | — | — |
| `LoadLibraryA` | 753 | `0xB053F6` | `0xB053F8` | `0xAFAFF6` | NONE | — | — | — | — |
| `LoadLibraryW` | 756 | `0xB046C8` | `0xB046CA` | `0xAFA2C8` | NONE | — | — | — | — |
| `LoadLibraryW` | 756 | `0xB05C44` | `0xB05C46` | `0xAFB844` | NONE | — | — | — | — |
| `CryptAcquireContextA` | 172 | `0xB03B44` | `0xB03B46` | `0xAF9744` | NONE | — | — | — | — |
| `CryptAcquireContextW` | 173 | `0xB03BD4` | `0xB03BD6` | `0xAF97D4` | NONE | — | — | — | — |
| `CryptDecrypt` | 176 | `0xB03C44` | `0xB03C46` | `0xAF9844` | NONE | — | — | — | — |
| `CryptCreateHash` | 175 | `0xB03C54` | `0xB03C56` | `0xAF9854` | NONE | — | — | — | — |
| `CryptGenRandom` | 189 | `0xB03B6E` | `0xB03B70` | `0xAF976E` | NONE | — | — | — | — |
| `CryptDestroyKey` | 179 | `0xB03BAA` | `0xB03BAC` | `0xAF97AA` | NONE | — | — | — | — |
| `CryptReleaseContext` | 199 | `0xB03B2C` | `0xB03B2E` | `0xAF972C` | NONE | — | — | — | — |
| `CryptImportKey` | — | — | — | — | **NOT PRESENT** | — | — | — | — |
| `CryptEncrypt` | — | — | — | — | **NOT PRESENT** | — | — | — | — |
| `CryptDeriveKey` | — | — | — | — | **NOT PRESENT** | — | — | — | — |

> 补充机械事实：`CryptImportKey`、`CryptEncrypt`、`CryptDeriveKey` 在 `.idata2` 的 660 条名称中
> **完全不存在** ⇒ "用 `CryptImportKey` 导入会话密钥再 `CryptDecrypt`" 这条最典型的
> CryptoAPI 路径，**在 Base.dll 的名称表层面就被否定**。

### A.4.1 那两个 `.tls` 引用点的字节证据

`CreateFileA` name RVA `0xB04858` 的唯一引用，文件偏移 `0x181D9FB`（RVA `0x18281FB`，节 `.tls`）：

```
0x181D9DF: 12 00 6b 00 0f 0f 04 15 1f 1c 6a 0a 06 40 5f 45 58 48 b0 00 00 23 03 0e 5a 4c ...
                                                    ^^^^^^^^^^^ 引用位置（dword = 0x00B04858）
```

`ReadFile` name RVA `0xB0470E` 的唯一引用，文件偏移 `0x1700523`（RVA `0x170AD23`，节 `.tls`）：

```
0x1700507: 3e 01 21 5f 74 33 2a 09 88 07 0f 08 02 17 0d e7 05 05 e0 00 1f 9d 1d 01 11 0f 0a ...
                                              ^^^^^^^^^^^ 引用位置（dword = 0x00B0470E）
```

两处的共同机械特征：

* 128 字节窗口熵 **5.13 / 5.48**（不是代码，也不是纯随机）
* 后文出现可打印片段：`SETTING_VALUE`、`LAUNCH`、`anceID`、`corecrt_wstring_h`、`_Destin`、`_SizeInWords`、`_Source`
* 出现构建路径串：`E:\Git\ten...`、`ect3\tools\Python-3.5.0\`
* **±4 KB 内 `55 8B EC` 函数序言数量 = 0**
* 以 1..15 字节任意回退反汇编，都无法让该 dword 落在合法指令的立即数/位移字段内

⇒ 这是**编码后的字符串/元数据 blob**（把 API 名称 RVA 当普通数据引用），
**不是代码路径**。它不能作为"解析调用点"。

---

## A.5 C 项判定：cfg 逻辑在可见原生代码，还是在 `.tvm0`／运行时生成区

### A.5.1 节级机械事实

| 节 | raw | size | RVA | 可执行 | 前 64 KB 熵 |
|---|---|---|---|---|---|
| `.text` | `0x000400` | `0x741C00` | `0x001000` | 是 | 7.2991 |
| `.rdata` | `0x742000` | `0x26B200` | `0x743000` | 否 | 5.7832 |
| `.data` | `0x9AD200` | `0x14AA00` | `0x9AF000` | 否 | 5.0533 |
| `.idata2` | `0xAF7C00` | `0x005000` | `0xB02000` | 否 | 6.8436 |
| `.rsrc2` | `0xAFCC00` | `0x00002C` | `0xB07000` | 否 | 7.3732 |
| **`.tls`** | `0xAFF800` | **`0xED2600`** | `0xB0A000` | **是** | **7.6321** |
| `.tvm0` | `0x19D1E00` | **`0x1F5D600`** | `0x19DD000` | 是 | 7.3219 |
| `.reloc` | `0x392F400` | `0x055E00` | `0x393B000` | 否 | 6.7129 |

`config_mp.cfg` / `players\` / `SEMV` 在 Base.dll **零命中**（见正文 §2）。

### A.5.2 判定

**结论：UNKNOWN（不可判定），但有强约束。**

机械可证的部分：

1. **IAT 收口不在可见代码内**：A.2 已穷举 13 种编码 + 全可执行节反汇编，零命中。
2. **名称 → 解析点链路不在可见代码内**：A.4 只有 2 条名称指针引用，都在 `.tls` 的非指令 blob 中。
3. **`.text` 不引用 `.tvm0` 之外的 API 名称**：660 条 `.idata2` 名称中，仅 2 条被 32 位指针引用（均在 `.tls` blob）。
4. `.text` 原始字节中，落在 `.tvm0` RVA 范围内的 32 位小端值有 **130,961 处**
   （前若干例：文件偏移 `0x401 -> 0x1A89E98`、`0x465 -> 0x1E85000`、`0x470 -> 0x1A0126E` …）。
   这是**原始 dword 出现统计，不是已校验的指令引用**；仅能证明 `.text` 字节流中存在大量指向 `.tvm0` 的
   32 位值，不能单独证明它们全是被执行的引用。

无法机械判定的部分：

* **无法证明** cfg 读取/解密发生在 `.text`、`.tls` 还是 `.tvm0`。
* **无法排除** `.tls` 的 15.5 MB 可执行高熵区本身就是一套**编码后的原生代码**（自解密后才成为有效指令）。
* **无法排除** 逻辑在运行时由 `.tvm0` 生成（JIT/解包后执行）。

⇒ 因此 C 项记为 **UNKNOWN**，并附以下**可机械否定的子命题**：

> **已否定：** "cfg 读取函数是 `.text` 中某个通过 IAT 槽 `0x109F6800/0x109F6804` 间接调用 `CreateFileW`/`ReadFile` 的普通函数。"
> 理由：A.2 的 13 种编码零命中 + A.4 的名称指针引用仅落在 `.tls` 非指令 blob。

---

## A.6 追加的失败假设（本轮新增）

| # | 假设 | 机械检验 | 结果 |
|---|---|---|---|
| 11 | `call dword ptr [0x109F6800]` 形态调用 `LoadLibraryA` | 字节扫描 `FF 15 00 68 9F 00` | **排除**（0 命中）|
| 12 | `call dword ptr [0x109F6804]` 形态调用 `GetProcAddress` | 字节扫描 `FF 15 04 68 9F 00` | **排除**（0 命中）|
| 13 | 任何 `mov [0x109F6804], reg` 形态写入 IAT | 字节扫描 4 种寄存器编码 | **排除**（0 命中）|
| 14 | `CreateFileA` 名称以 32 位 VA 指针被代码引用 | 扫描 `0x00B04858` | **排除**（唯一引用在 `.tls` blob，非指令）|
| 15 | `ReadFile` 名称以 32 位 VA 指针被代码引用 | 扫描 `0x00B0470E` | **排除**（唯一引用在 `.tls` blob，非指令）|
| 16 | cfg 解密走 `CryptImportKey` + `CryptDecrypt` | `.idata2` 660 条名称检索 | **排除**（`CryptImportKey` 不存在）|
| 17 | cfg 解密走 `CryptEncrypt` / `CryptDeriveKey` | 同上 | **排除**（均不存在）|

---

## A.7 下一步唯一可机械推进的方向

1. **`.tls` RVA `0xB0A000` 起 `0xED2600` 字节** —— 可执行、熵 7.63、`0x18281FB`/`0x170AD23` 两个 API 名称引用所在。
   需先判定它是"编码后的原生代码"还是"数据池"，判定手段：找它的解码器（`.text` 中对 `.tls` 的**写**引用）。
2. **`.text` 中对 `.tls` 范围的 32 位引用**（130,961 条中有多少落在 `.tls`，多少落在 `.tvm0`）——
   这是把 `.tls` 与 `.text` 建立因果的唯一机械通道。
3. **`.tvm0`**（raw `0x19D1E00`，size `0x1F5D600`）—— 受"不要碰 ACE"约束，本轮**未读取**。

以上三项之外的路径，本轮已机械否定，不再重复。

---

## A.8 本附录复现命令（只读）

```python
# A.1 原始导入描述符
pe = pefile.PE(r'COD OL\codoMP_client_shipRetailBase.dll')
pe.get_offset_from_rva(0x9F67B8)   # -> 0x9F49B8，读 0x3C 字节

# A.2 IAT 引用穷举（示例：call 形态）
D = open(r'COD OL\codoMP_client_shipRetailBase.dll','rb').read()
D.find(bytes.fromhex('ff1500689f00'))   # -1
D.find(bytes.fromhex('ff1504689f00'))   # -1

# A.3/A.4 .idata2 的 hint+name 表
#   遍历 raw 0xAF7C00..0xAFFC00：u16 hint + ASCII + 0x00
#   对每条 name 的 RVA 搜 struct.pack('<I', name_rva)

# A.5 节熵
#   ent(D[0x400:0x400+65536]) == 7.2991  (.text)
#   ent(D[0xAFF800:0xAFF800+65536]) == 7.6321  (.tls)
```

CSV 版本见 `CODOLServer\_subagent_cfg_crypto_xref.csv`。
