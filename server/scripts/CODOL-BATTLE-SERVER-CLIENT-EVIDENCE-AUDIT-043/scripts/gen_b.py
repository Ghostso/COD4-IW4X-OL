# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("02_DECODER_INSTRUCTION_AUDIT.md", """# 02_DECODER_INSTRUCTION_AUDIT — 解码器指令级审计

**审计对象:** 042 报告的 `0x87A890`(sizeinfo/长度)、`0x87C110`、`0x87D5A0`。
**镜像:** S-IMG `17cef6e0…` (ImageBase 0x400000, `file_off = RVA`)。
**方法:** 043 独立反汇编(不引用 042 描述);每条规则给指令地址。
**证据文件:** `evidence/dis_87A890_full.txt`,`dis_87A8xx_boundaries.txt`,`dis_sizeinfo_helpers.txt`,`dis_deser_boundaries.txt`,`b_final_checks.txt`。

---

## 1. `0x87A890` — netfield 长度编码**写入器**(非纯检查器)

### 1.1 边界(与 042 不同)

- **函数入口:** `0x87A890`;函数体尾 `ret` 于 **`0x87A8EE`**(+0x5E)。
- `0x87A8EF` 起是同函数内的分支跳转目标(阈值判定),并非新函数。
- 该 `ret` **不是**唯一出口:`0x87A928`、`0x87AA3F` 亦在此逻辑内。
- 紧邻 `0x87AA40` 是**同族第二个写入器**(另一个 `ret 0x87AA78`),`0x87AB30/0x87AB40` 是第三处。
  **042 把 `0x87A890..0x87A980` 描述为单一"帮助函数"不精确。**

### 1.2 真实语义:计算长度并按 sizeinfo 编码**写入输出缓冲**

| 步骤 | RVA | 指令 | 语义 |
|---|---|---|---|
| 累计元素字节 | `0x87A8A8` | `movzx ecx,word[eax+esi*2]` | 读元素尺寸表 `[ebp+8]` 第 i 项(16 位) |
| 判是否 netfield | `0x87A8AD` | `call 0x744B20` | 该函数 `mov eax,1; ret` → **恒返回 1**;`eax==0` 分支(`0x87A8B7`)为**死代码** |
| 元素字节数 | `0x87A8C1` | `call 0x7CD790` | 16 位 varint 宽度:≤0x7F→1,≤0x7FF→2,否则 2(`0x7CD797/0x7CD7A9`) |
| 累加 | `0x87A8CA` | `add edi,eax` | `edi` = 累计编码字节数 |
| 阈值 | `0x87A8D3` | `cmp edi,0x80` | <128 → 头部 2 字节 |
| 阈值 | `0x87A8EF` | `cmp edi,0x100` | <256 → 3 字节 |
| 阈值 | `0x87A8FC` | `cmp edi,0x10000` | <65536 → 4 字节 |
| 阈值 | `0x87A909` | `cmp edi,0x1000000` | ≥2^24 → 走错误出口(`0x87A8E3` 返回 0x10) |
| 剩余检查 | `0x87A914/0x87A917` | `mov ecx,[ebp+0x14]; cmp eax,[ecx]` | **需要宽度 vs 调用者可用长度**;`jbe` 通过 |
| 写 tag | `0x87A92F` | `mov byte[ebx],0xC` | **写出 sizeinfo 标签字节 0xC** |
| 写 payload | `0x87A939/0x87A94A/0x87A95F/0x87A980` | `mov [ebx+1],…` | 按宽度写 1/2/3 字节大端 |
| 逐元素写 | `0x87A9C0..0x87AA27` | 位域拆解 + `mov [esi+ebx],…` | 将每个 16 位 netfield 拆成 1/2/3 字节流 |

### 1.3 对 042 的裁定

| 042 表述 | 043 裁定 |
|---|---|
| "sizeinfo 帮助" | **不完整**:实测为**写入器**(含 `mov byte[ebx],0xC` 与 payload 写出)。`INFERRED`→**修正为 CONFIRMED(写入器)**。 |
| "按阈值 128/256/65536 选择 sizeinfo 宽度" | **成立**(`0x87A8D3/0x87A8EF/0x87A8FC/0x87A909`)。 |
| "与剩余可用长度比较" | **成立**(`0x87A917`),在**写入前**执行(读侧对应检查在 `0x87C7FB`)。 |
| "帮助 `0x744B20` 判 netfield" | **不成立**:`0x744B20` 恒 `return 1`,其分支为死代码。 |
| 阈值比较对象 | **修正**:比较的是**元素累计字节数 `edi`**,不是"sizeinfo 本身"。 |

---

## 2. `0x87C110` — netfield/元素**解码器入口**

### 2.1 边界与调用约定

- 入口 `0x87C110`;结尾 `ret 0x87D592`;尾随 `0x87D593..0x87D5A0` 为 `0xCC` 填充。
- 栈帧 `mov eax,0x17F4`(`0x87C110`)→ 大栈帧,证明**非小工具**。
- 参数(读 `[esp+0x1800]` 等)表明 `__cdecl`/多参数。
- 栈 cookie:`mov eax,[0xE3F240]; xor eax,esp`(标准 /GS)。

### 2.2 元素类型"分派"的真实范围(对 042 的收紧)

- **全函数仅 2 处 `[ebx+8]`**:`0x87C767`(`cmp [ebx+8],1`)、`0x87C794`(`mov eax,[ebx+8]`)。
- `0x87C797/0x87C7A0/0x87C7A9` 是 `cmp eax,1; jle; sub eax,0x15; je; dec eax; je` —— **一小组取值**(范围窄),
  不是 042 描述的"typed element 多路分派"。
- 主体(`0x87C7B0+`)是**按元素尺寸 `[ebx+0x18]`/`[ebx+0x1C]` 乘法 + 边界比较**(`0x87C7B9 imul`、`0x87C7BE cmp`、
  `0x87C7FB cmp`)和 **8 字节元素搬运循环**(`0x87C830..0x87C8E0`,`shld/shrd`,`mov [edi],ecx`)。

| 042 表述 | 043 裁定 |
|---|---|
| "按 `[ebx+8]` 类型/元素多路分支" | **过度表述**。实际为**单一字段的少数取值判断**(≤2 处引用)。→ `UNKNOWN`(真实取值域未穷举)。 |
| "8 字节元素搬运循环" | **成立**(`0x87C830..`)。 |
| "元素类型/宽度多路" | 部分成立:有 `imul` 尺寸乘与 `dec` 级联,但**未证明是完整类型表**。 |

### 2.3 net-buffer 边界检查(命令级证据)

- `0x87C7FB cmp ecx,[esp+0x30]` → `0x87C801` 溢出分支,`push 0xD9EFB8`(`net-buffer NOT enough … unit_size/count`)
  于 `0x87C809`,`jmp 0x87CDDF`(错误处理)。
- 长度不足串 `0xD9EE98` 由 `0x87CDDB` 引用(同函数错误路径)。

---

## 3. `0x87D5A0` — 第二解码器入口(与 #1 **独立**)

### 3.1 边界与关系

- 入口 `0x87D5A0`,`ret 0x87ED58` 等,尾随 `0x87ED59..0x87ED60` 为 `0xCC`。
- **与 `0x87C110` 无互相调用**:`0x87C110` 体内无任何 call/jmp 进入 `0x87D5A0` 区间;反之亦然
  (见 `evidence/b_final_checks.txt`)。→ 二者的关系是 **COMMON_STYLE**(同 net-buffer 编解码族),
  **不是** wrapper/core。
- **共享辅助**:两者都调用 `0x87ED70`(缓冲池/临时缓冲获取)与 `0x87EDB0`(UTF-16 长度计数)。

### 3.2 双缓冲参数校验(具体含义)

```
0087d5b9  mov ebx,[esp+0x181C]     ; arg (buffer B)
0087d5c1  mov ebp,[esp+0x1818]     ; arg (context)
0087d5c9  mov edi,[esp+0x1820]     ; arg (buffer A)
0087d60f  mov esi,[ebx]            ; B->data
0087d619  mov eax,[ebx+4]          ; B->len
0087d628  mov edx,[edi]            ; A->data
0087d632  mov eax,[edi+4]          ; A->len
```
两对 `{data,len}` + context;`0x87D5F4 cmp [ebp+0x10],0` 校验 context 有效。
**判定:** 输入/输出缓冲对(或两段消息),非"分派表"。

---

## 4. 辅助函数(独立确认,修正 042 缺失)

| VA | RVA | 语义 |
|---|---|---|
| `0xB44B20` | `0x744B20` | `mov eax,1; ret` —— **恒真**(042 未提及;其死分支) |
| `0xBCD790` | `0x7CD790` | 16 位 varint 宽度:≤0x7F→1,≤0x7FF→2 |
| `0xBCD7C0` | `0x7CD7C0` | 元素宽度累加(0x7CD7C0..);阈值 0x80/0x100 |
| `0xBCD950` | `0x7CD950` | 长度估算(0x7CD950),F-B 调用 |
| `0x87ED70` | `0x87ED70` | 缓冲池获取(`[0x196C7E8]`,`call [0xCA8330]`) |
| `0x87EDB0` | `0x87EDB0` | UTF-16 串长度计数(`cmp word[ecx],0`) |

---

## 5. 诊断字符串 ↔ 代码关联(独立核验)

| 串 RVA | 串 | 引用码点 | 所在函数 |
|---|---|---|---|
| `0x99EE98` | `; net-buffer NOT enough: real_len<%d> sizeinfo_size<%u> net_start<%p> net_end<%p>` | `0x87CDDB` | `0x87C110` |
| `0x99EEF0` | `; string length error …` | `0x87CDAA` | `0x87C110` |
| `0x99EF50` | `; wstring length error …` | `0x87CB98` | `0x87C110` |
| `0x99EFB8` | `; net-buffer NOT enough: net_start… unit_size<%u> count<%d>` | `0x87C80A`,`0x87DECC` | `0x87C110`,`0x87D5A0` |
| `0x99F290` | `; string from net-buffer format error …` | `0x87E5BA` | `0x87D5A0` |
| `0x99F428` | `; wstring from net-buffer format error …` | `0x87E306` | `0x87D5A0` |

**关联强度:** 每个串均有**同函数内的 imm32 push + 错误分支**,即"串—指令"互相印证。
但如 042 所述,串本身**不构成**完整语义证明;此处语义由**指令**(长度运算/边界比较/搬运)支撑。

---

## 6. 结论

| 结论 | 状态 |
|---|---|
| `0x87A890` 为 netfield **长度编码写入器**(非纯检查) | **CONFIRMED(修正 042)** |
| 阈值 128/256/65536/2^24 与"可用长度"检查 | **CONFIRMED** |
| `0x744B20` 恒真 → 042 的"netfield 判定"分支无效 | **CONFIRMED(修正)** |
| `0x87C110` 为 netfield 解码入口;类型"分派"范围窄(仅 2 处 `[ebx+8]`) | **CONFIRMED / 042 收紧** |
| `0x87D5A0` 与 `0x87C110` **独立**,共享 `0x87ED70`/`0x87EDB0` | **CONFIRMED** |
| 6 串与代码的关联 | **CONFIRMED** |
""")
print("wrote 02")
