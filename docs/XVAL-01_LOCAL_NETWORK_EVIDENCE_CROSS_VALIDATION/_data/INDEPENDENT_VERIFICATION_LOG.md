# XVAL-01 独立复核日志 / INDEPENDENT VERIFICATION LOG

> 本文件记录 **XVAL-01 本轮亲自重算/反汇编** 得到的证据。目的：使关键主张不依赖既有报告的转录。
> 工具：Python 3.11.9 + capstone 5.0.7 + pefile 2024.8.26（`_tools\verify_claims.py`）。
> 方式：只读打开冻结样本；未运行、未注入、未读进程内存。地址口径 **RVA**（VA = RVA + 0x400000）。

---

## V-01 冻结样本哈希（本任务活体重算）

| 样本 | 本任务 SHA-256 | 与档案登记 |
|---|---|---|
| 2.6.9.7 客户端 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | ✅ 一致 |
| 恢复镜像 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | ✅ 一致 |
| 2697 服务端 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | ✅ 一致 |
| 1113 客户端 | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` | ✅ 一致 |
| 1113 服务端 | `a96c5dfb5386f166a0e1d4262b8fdecf9835b856cf1a863f891ead4eda5cb6e9` | ✅ 一致 |
| OLD 服务端 | `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a` | ✅ 一致 |
| 3.3.3.3 客户端 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | ✅ 一致 |

## V-02 恢复镜像区段布局（活体 PE 解析）

```
ImageBase = 0x00400000   EntryPoint RVA = 0x0074FF4F
.text   VA=0x00001000  VSize=0x007AC90B  RawPtr=0x00000400  RawSize=0x007ACA00
.rdata  VA=0x007AE000  VSize=0x00142880  RawPtr=0x007ACE00  RawSize=0x00142A00
.data   VA=0x008F1000  VSize=0x0D05C420  RawPtr=0x008EF800  RawSize=0x00049600   <-- 覆盖率 0.138%
.tls    VA=0x0D94E000  VSize=0x00000019  RawPtr=0x00938E00  RawSize=0x00000200
.rsrc   VA=0x0D94F000  VSize=0x00008DF8  RawPtr=0x00939000  RawSize=0x00008E00
.tvm0   VA=0x0D958000  VSize=0x002B9000  RawPtr=0x00941E00  RawSize=0x002B8C00
.rimp   VA=0x0DC11000  VSize=0x00002964  RawPtr=0x00BFAA00  RawSize=0x00002A00
```

**结论（独立证实 EV-C2697-DataGap）：** `.data` 声明 218,120,224 B，文件中仅 300,544 B → **99.86% 不在镜像内**。这**直接**支撑"客户端分派搜索空间不完备"是结构性的，而非工具缺陷。

## V-03 服务端 configstring A2 段计数 = 11 bit（活体反汇编）

文件：`...\server2697\native\bin2697\codol_dedrun.exe`，`_CODOL2697_WriteConfigstrings` RVA 0xA0468 内：

```
0x0A084D  mov  dword ptr [esp + 8], 0xb      <-- A2 段计数，11 bit
0x0A085F  call 0x499590                       <-- MSG_WriteBits
0x0A088A  mov  dword ptr [esp + 8], 0xa      <-- A2 条目值，10 bit
0x0A08A0  call 0x499590
0x0A08AD  mov  dword ptr [esp + 8], 0xa      <-- A3 段计数，10 bit
0x0A0922  mov  dword ptr [esp + 8], 7        <-- A3 field_B，7 bit
```

→ **服务端 A2 段计数 = 11 bit**（独立证实 E-14 §3 对 E-08 的修订；E-08 的 "10 bit" 记录为错误）。

## V-04 客户端 configstring 消费器 `0xA2660` = 11 bit 计数（活体反汇编）

文件：`...\aplib-recovered\codol2697-static-candidate.bin`，RVA 0xA2660 起：

```
0x0A26A5  cmp   edi, ecx
0x0A26AF  push  2                          <-- count1 长度 = 2 字节
0x0A26B2  call  0x5AC1D0                   <-- MSG_ReadData
0x0A26B7  movsx eax, word ptr [ebp-0x108]  <-- 按 16 位有符号解释
0x0A26F0  push  0xD                        <-- 非连续索引 = 13 bit
0x0A2702  cmp   edi, 0x1DD7                <-- 索引上限 sentinel 0x1DD7
0x0A2728  ...   cmp cl,0x14 / cmp cl,0x12  <-- 合法索引区间（0x12 跳过）
0x0A2765  push  0xB                        <-- A2 段计数 = 11 bit
0x0A276C  call  0x5AC670                   <-- MSG_ReadBits
0x0A27A4  push  0xD                        <-- 13 bit 索引
0x0A27D7  call  0x5AC670                   <-- 10 bit 值
```

→ 客户端**独立**读 count1=2 字节、A2 段计数=11 bit、13 bit 索引、上限 0x1DD7。**与服务端逐字段一致**。

## V-05 OLD 源码 wire 常量（活体读取）

`...\CODOL_Server\dedicated\src\codol\net\codol_wire.h`：

```c
#define CODOL_PROTOCOL      187
#define CODOL_PORT          17733
#define CODOL_FRAGMENT_SIZE 1162u
#define CODOL_MAX_FRAGMENTS 128u
#define CODOL_SEQUENCE_MASK UINT32_C(0x1fffffff)
#define CODOL_FRAGMENT_BIT  UINT32_C(0x80000000)
#define CODOL_FORCE_ACK_BIT UINT32_C(0x40000000)
#define CODOL_ACK_BIT       UINT32_C(0x20000000)
```

→ 独立证实 2697 二进制中的 `0x489(=1161)`、`0x24500(=1162×128)`、`0x1fffffff` 与 OLD 源码常量同源（2697 侧常量见 `2697_SA 04 §` 与 R-17）。

## V-06 开源副本 git HEAD（活体）

| 仓库副本 | HEAD |
|---|---|
| CoD4x_Server | `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` |
| iw4x-client | `d1b175da1a25d31043246de103a702b206269e5a` |
| ol-mod-olfinal | `2a75bdd8872bb9f54006382a924c3006ec9affc2` |

→ 与 `E14\01` / `_EVIDENCE_REGISTER` 登记一致，引用可复现。

---

## 本轮未能独立复核（如实声明）

- `0xA2E50` 的**调用者分派**、`0x06` 的**客户端读取点**：受 `.data` 99.86% 缺失 + `.tvm0` 未解码限制，**本轮同样未能闭合**（与 E-09..E-19 一致，非新缺口）。
- `0x6ABBC0` Demonware 分帧器：本轮**未**重复反汇编（沿用 E-19 的 `_data\out_6abbc0.txt`），故其在主张表中标为"单一来源（E-19）"。
- 握手/加密字节（189 vs 219、XOR 密钥）：需抓包或合成对等体，**静态不可裁决**。
