# 04 — 静态解码结果 / STATIC DECODING RESULTS

> 等级：`VERIFIED`（双 CRC32 + 逐字节比对）
> 原始输出：`_data\RAW_RESULTS.txt`；脚本：`_tools\t08_depack_fixed.py`、`_tools\t10_all_ap32_fixed.py`、`_tools\t11_lasttp3_recover.py`
> 产物：`_work\depacked_text.bin`、`_work\depacked_tvm0.bin`、`_work\lasttp3_blocks.bin`

---

## 1. 解码方法（可复现）

```
对某个伪装区段（如 .tvm0）：
  1) 在节起始后 64 字节内定位 "AP32"
  2) 读 24 字节头部：
        S+0x04 = hdr_size (0x18)
        S+0x08 = packed_len
        S+0x0C = packed_crc32
        S+0x10 = orig_len
        S+0x14 = orig_crc32
  3) 压缩流 = file[ S+0x18 : S+0x18+packed_len ]
  4) 校验 crc32(压缩流) == packed_crc32
  5) out = aplib_decompress(压缩流)
  6) 校验 len(out) == orig_len 且 crc32(out) == orig_crc32
```

## 2. `.text` 解包（作为方法验证 + 提供 ground truth）

| 项 | 值 |
|---|---|
| AP32 位置 | 文件 0x00000404（节内偏移 0x04） |
| packed_len / packed_crc32 | 3,752,773 / `0xBBAC1898` |
| orig_len / orig_crc32 | 8,047,104 / `0x76992F27` |
| `crc32(压缩流) == +0x0C` | ✔ |
| `len(out) == +0x10` | ✔（8,047,104） |
| `crc32(out) == +0x14` | ✔（`0x76992F27`） |
| 与恢复镜像 `.text` 比对 | **逐字节相同，100.0000%** |

**结论：** 解码链**自洽**，且与**独立产出的既有恢复镜像**吻合。这为 `.tvm0` 提供可信 ground truth。

## 3. `.tvm0` 解包（本轮目标）

| 项 | 值 |
|---|---|
| AP32 位置 | 文件 0x00529804（节内偏移 0x04） |
| 前缀 u32 | `0xB1BBB432` |
| packed_len / packed_crc32 | 1,115,300 / `0x86F5A4DC` |
| orig_len / orig_crc32 | 2,853,888 / `0x0EE5F1F3` |
| `crc32(压缩流) == +0x0C` | ✔ |
| `len(out) == +0x10` | ✔（2,853,888） |
| `crc32(out) == +0x14` | ✔（`0x0EE5F1F3`） |
| 与恢复镜像 `.tvm0` 比对 | **逐字节相同，100.0000%** |
| 产物 SHA-256 | `_work\depacked_tvm0.bin`（= 恢复镜像 `.tvm0` 段） |

**裁定：`VERIFIED`。** `.tvm0` 的**容器格式已还原**，且**输出完全确定**（有双 CRC 与既有镜像双重锚定）。

## 4. 全量 AP32 块（10/10 全部通过双 CRC）

| # | 文件偏移 | 区段 | packed | orig | 压缩流CRC | 原数据CRC | 结果 |
|---|---|---|---|---|---|---|---|
| 0 | 0x00000404 | `.tp3`(0x1000) | 3,752,773 | 8,047,104 | ✔ | ✔ | **= 恢复镜像 .text** |
| 1 | 0x00529804 | `.tvm0`(0xD958000) | 1,115,300 | 2,853,888 | ✔ | ✔ | **= 恢复镜像 .tvm0** |
| 2 | 0x0063A523 | `.tp3`(0xDC11000) | 1,260 | 1,216 | ✔ | ✔ | 已解出 |
| 3 | 0x0063AA2B | 同上 | 11,942 | 13,664 | ✔ | ✔ | 已解出 |
| 4 | 0x0063D8ED | 同上 | 4,931 | 11,573 | ✔ | ✔ | 已解出 |
| 5 | 0x0063EC4C | 同上 | 602 | 1,073 | ✔ | ✔ | 已解出 |
| 6 | 0x0063EEC2 | 同上 | 127 | 321 | ✔ | ✔ | 已解出 |
| 7 | 0x0063EF5D | 同上 | 3,916 | 16,054 | ✔ | ✔ | 已解出 |
| 8 | 0x0063FEC5 | 同上 | 3,339,519 | 5,115,080 | ✔ | ✔ | 已解出 |
| 9 | 0x0096F3E0 | 同上 | 4,200 | 3,858 | ✔ | ✔ | 已解出 |

**10/10 双向 CRC 通过。** 其中 #0 与 #1 与恢复镜像**逐字节一致**，构成对解码链的**强独立验证**。

## 5. 重大附带发现：最后一节 `.tp3` 的真实内容

先前档案把 VA 0xDC11000 起的最后一节 `.tp3` 记为"未恢复、52.5 MB"。本轮从其中解出 **8 个 AP32 块（合计 5,162,839 字节）**，并在其中**切出 12 个完整 PE 模块**：

| # | 切出偏移 | 位数 | SizeOfImage | 区段名 | 识别 |
|---|---|---|---|---|---|
| 0 | 0xC505 | PE32+ | 0x1DC000 | `.text .rdata .data .pdata INIT .rsrc .vmp0 .vmp1 .vmp2 .reloc` | Tencent（VMProtect 保护） |
| 1 | 0xFD345 | PE32+ | 0x1DF000 | 同上 | Tencent |
| 2 | 0x1EEB9D | PE32+ | 0x7000 | 无 vmp | `tessafe2-alternative\Bin\amd64\Proxy64.pdb` |
| 3 | 0x1F0DE5 | PE32+ | 0x7000 | 无 vmp | `tessafe2\Bin\amd64\Proxy64.pdb` |
| 4 | 0x1F262D | PE32+ | 0x1B000 | `.vmp0` | `TesSafe64.pdb` |
| 5 | 0x208E75 | PE32+ | 0x1C000 | `.vmp0` | `TesSafe64.pdb` |
| 6 | 0x21F2BD | PE32 | 0xE0000 | 含 `.tvm0` | `i386\Loader.pdb` |
| 7 | 0x2FDB7D | PE32 | 0xFF000 | 含 `.tvm0` | `i386\Loader.pdb` |
| 8 | 0x3FAF25 | PE32 | 0x7000 | — | `i386\Proxy.pdb` |
| 9 | 0x3FD16D | PE32 | 0x7000 | — | `i386\Proxy.pdb` |
| 10 | 0x3FE7B5 | PE32 | 0x173000 | 含 `.tvm0` | **`TenProtect`** / `TesSafe.pdb` |
| 11 | 0x4859FD | PE32 | 0x153000 | 含 `.tvm0` | **`TenProtect`** / `TesSafe.pdb` |

**关键含义（改变此前判断）：**

- 先前档案的表述"最后一节 `.tp3`（VA 0xDC11000，52.5 MB）**未恢复**"**不准确**，需修订：
  - 该节**确实未按 `.text`/`.tvm0` 那样整体恢复**；
  - 但其中**8 个 AP32 块可 100% 还原**，其真实内容是 **TenProtect/TesSafe 反作弊载荷**（TesSafe64 / TesSafe / Loader / Proxy，x64 + x86 双架构，VMProtect 保护），**不是游戏逻辑**。
- 因此：**该节的缺失对"客户端游戏协议分派链"解释力有限** —— 它是反作弊/保护模块，不是消息解析器所在。

## 6. `.tvm0` 解包内容的性质（语义层，仍未闭合）

| 指标 | 值 |
|---|---|
| 长度 | 2,853,888 B |
| 全局熵 | 5.6555 bit/byte |
| 零字节 | 21.39% |
| `0xCC`(int3) | 0.06% |
| 内含 `"AP32"` / `PE\0\0` | 0 / 0 |
| 是否被 `call` | **是**：`.text` 有 50 次 `call`（5 个入口） |

**反汇编特征（入口处）：**

```asm
; 最强入口 RVA 0xD9AB8AC（45 次 call）
0DDAB8AC  push 0x5ca82aa5
0DDAB8B1  push ecx
0DDAB8B2  push edx
0DDAB8B3  push ebx
0DDAB8B4  push eax
0DDAB8B5  push esi
0DDAB8B6  jmp  0xde0f616
```

即：`push imm32` + 寄存器压栈 + `jmp` **远跳**，是典型的**栈混淆/花指令**形态。

**线性反汇编对齐检查：** `.text` 对 `.tvm0` 的 5 个入口**没有一个**落在"从节首线性解码"得到的指令边界上（对齐率 0%）——说明 `.tvm0` **不能**从节首线性解码，必须**从入口点**解码。

**裁定：`PARTIAL`** —— 格式已还原（VERIFIED）；**控制流语义未还原**（入口处的远跳目标 `0xDE0F616` 落在 `.tvm0` 内，但后续流被混淆打断）。

## 7. 产物清单

| 文件 | 内容 | 校验 |
|---|---|---|
| `_work\depacked_text.bin` | 解包 `.text`（8,047,104 B） | = 恢复镜像 `.text` |
| `_work\depacked_tvm0.bin` | 解包 `.tvm0`（2,853,888 B） | = 恢复镜像 `.tvm0` |
| `_work\lasttp3_blocks.bin` | 末节 8 个 AP32 块串接（5,162,839 B） | 块级双 CRC ✔ |

## 8. 结论

| 结论 | 等级 |
|---|---|
| `.tvm0` 是 aPLib（AP32）压缩块，头部 24 字节 | **VERIFIED** |
| `.tvm0` 可完整解包并获得唯一确定输出 | **VERIFIED** |
| 解包结果与既有恢复镜像**逐字节相同** | **VERIFIED** |
| 同一容器格式覆盖 10 处，10/10 双 CRC 通过 | **VERIFIED** |
| 末节 `.tp3` 含 12 个 PE（TenProtect/TesSafe 载荷） | **VERIFIED** |
| `.tvm0` 被 `.text` 以 `call` 直接进入（5 入口 / 50 次） | **VERIFIED** |
| `.tvm0` 的控制流语义 | **PARTIAL / BLOCKED**（需从入口解码，且被混淆打断） |