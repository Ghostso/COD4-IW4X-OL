# -*- coding: utf-8 -*-
import os, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
D = lambda n: os.path.join(root, n)

# --- fix 01/02 based on the final verified readings (tables are 20 items; DecodeKey mirrors them) ---
p=os.path.join(root,"01_CODEC_FUNCTIONS.md"); t=open(p,encoding="utf-8").read()
t=t.replace("- Codec B：[19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11]（**仅 19 项**，`0x00AA8C3C`–`0x00AA8CB6`；第 4 轮第 5 项由 `mov dword [ebp-0x1C]` 占据，见 §2.1）",
"- Codec B：[19,18,9,4,17,1,10,8,13,2,15,3,12,**16**,5,7,0,14,6,11]（**20 项**，`0x00AA8C3C`–`0x00AA8CB6` + `0x00AA8C12` 处 `mov [ebp-0x34],edx`（`edx=0x10`）补第 14 项）")
t=t.replace("""### 2.1 关于 Codec B"19 项"的判定与更正

`0xAA8CB6 c7 45 e4 0b 00 00 00` = `mov dword [ebp-0x1C], 0x0B`，是置换表第 20 项（值 11），紧随其后：

```asm
00AA8CBD 05 0d060000   add eax, 0x60D
```

上一轮报告把此处读作 `add eax, 0x60D` 之前缺一项，属**读取顺序问题**而非真实缺项。**结论：Codec B 同样是完整 20 项置换**，与 Codec A 等长。""",
"""### 2.1 Codec B 的 20 项完整性（含两处 `mov [ebp-x],edx` 填充项）

Codec B 的置换表有两点需要特别指出：

- `0x00AA8C12  mov dword [ebp-0x34], edx`（此时 `edx=0x10`=16）写入的是表项；对应第 **14** 项（索引 13）。
- `0x00AA8CB6  mov dword [ebp-0x1C], 0x0B` 是第 20 项（值 11），紧随其后 `0x00AA8CBD add eax,0x60D`。

因此 Codec B 的完整置换为 `[19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]`，**20 项**，与 Codec A 等长。（Codec A 亦有同类填充项 `0x00AA8D95 mov [ebp-0x58],edx`（`edx=9`），其表 20 项完整。）

**该方法学更正的意义**：Codec B 常被误读为"19 项、缺一项"，从而被当成"与 C# 参考实现不一致"。本轮以指令编码逐项核对，确认**两侧表完全一致**（见 03 §3）。""")
t=t.replace("""```text
Codec A mask = f3421112 72f43241 09ae3f18 13eabca3 54bc09cc
Codec B mask = 213cff0b f422ee00 92deceaa 271cf480 102137??  (第 20 字节由第 4 轮第 5 项补齐)
常量表（原始顺序）A = 411309ae 3fa3bcf3 1872eabc 093211cc 124254f4
常量表（原始顺序）B = 8022deaa 0b1c21f4 00ffee37 279210ce aaf43c21
```""",
"""```text
常量表（原始顺序）A = 411309ae 3fa3bcf3 1872eabc 093211cc 124254f4
常量表（原始顺序）B = 8022deaa 0b1c21f4 00ffee37 279210ce aaf43c21
置换 A = [7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]
置换 B = [19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]
等价掩码 M_A[i] = CONST_A[PERM_A[i]] = f3 42 11 12 72 f4 32 41 09 ae 3f 18 13 ea bc a3 54 bc 09 cc
等价掩码 M_B[i] = CONST_B[PERM_B[i]] = 21 3c ff 0b f4 22 ee 00 92 de ce aa 27 1c f4 80 10 21 37 09
```""")
open(p,"w",encoding="utf-8").write(t)

p=os.path.join(root,"02_FIELD_DEF_USE_CHAINS.md"); t=open(p,encoding="utf-8").read()
t=t.replace("| `this+0x5F9` | \"codec 输出候选位置\" | **20B codec 暂存区 `[+0x5F8, +0x60C)` 的第 1 字节**（基址常量 `0x5F9`，配合 `input+1`/`store-1` 的写法定址） | `0xAA8E3C` |",
"| `this+0x5F9` | \"codec 输出候选位置\" | **20B codec 暂存区 `[+0x5F8, +0x60C)` 的写法定址常量**（`0xAA8E3C add eax,0x5F9`；循环中 `[eax-1]` 是首字节，故真实首字节为 `+0x5F8`） | `0xAA8E3C` |")
t=t.replace("| `this+0x60D` | 同上 | **20B codec 暂存区 `[+0x60C, +0x620)` 的第 1 字节**（基址常量 `0x60D`） | `0xAA8CBD` |",
"| `this+0x60D` | 同上 | **20B codec 暂存区 `[+0x60C, +0x620)` 的写法定址常量**（`0xAA8CBD add eax,0x60D`；真实首字节为 `+0x60C`） | `0xAA8CBD` |")
t=t.replace("即：两个 **20 字节** 缓冲区连续存放，整体覆盖 `[+0x5F8, +0x620)`；`0x5F9`/`0x60D` 只是\"基址-1\"写法定址下的地址常量。",
"即：两个 **20 字节** 缓冲区连续存放，整体覆盖 `[+0x5F8, +0x620)`；`0x5F9`/`0x60D` 是\"基址+1、循环内以 `[eax-1]` 访问首字节\"这一写法定址下的地址常量。（上一轮报告称之为\"输出位置\"，措辞不准确但不影响其结论。）")
open(p,"w",encoding="utf-8").write(t)
print("patched 01/02")
