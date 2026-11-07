# CODOL 第一档阻断证据报告 — 静态复核（修正版）
日期：2026-09-30
作者：静态逆向分析（纯静态搜索，无游戏运行）

## 前提

基于盘镜像 `image_best.bin`，使用 capstone + 自研 xref 脚本 `_tier1_disasm.py` / `_tier1_static_search.py` / `_archscan.py`。
**未读盘 EXE 密文段、未运行游戏、未写入内存。**

## ⚠️ 修正说明

早期草案存在严重错误，依据离线静态反汇编修正如下：

- `0x8083B3` 的指令是 `cmp byte [0xE57A5C], 0`（dispatch enable），**不是** `cmp [0xE60B80]`。
- `0x8083C0` 是 `mov al, byte [0xC7AF440]`，常量是 **8** (`mov eax, 8`) 而非 6。
- `0x4A8F00` **写入** `[0xE60B80]`，不是读取 — 因果关系反了。
- 关键门控变量是 `[0x82C4A88]`（必须为 3），不是 `[0xE60B80]`。
- 状态机 `0x808240` 有直接调用者 (`0x4F8AD3`, `0x4F8AF2`, `0x4F8B0A`, `0x5C29CE`)。

---

## 1. 关键函数 `0x4A93E0` — marketplace.json 获取函数

```asm
004A93E0  cmp          byte ptr [0x84ABB2F], 0  ← 守卫 G2F
004A93E8  mov          dword ptr [0x82C4AEC], 1 ← GEC := 1
004A93F2  je           0x4A9455                   ← 若 G2F=0，提前返回
004A93F4..004A944D 完整的市场 JSON 获取逻辑      ← 仅 G2F≠0 时执行
004A9443  mov          dword ptr [0x82C4A88], 1 ← GATE := 1
004A944D  call         0x4A80C0                   ← 进入资源注册块
004A9455  pop          esi
004A9456  ret
```

| 全局 | VA | 功能 | 静态初始值 | 写入点 |
|---|---|---|---|---|
| `[0x84ABB2F]` | 0x084ABB2F | G2F 守卫 | **0** | `0x80A36E` (唯一) |
| `[0x82C4A88]` | 0x082C4A88 | GATE 标记 | 0 | `0x4A7E37`(val=3),`0x4A9443`(val=1),`0x4A80FD`(val=2) + 5 处动态 |
| `[0x82C4AEC]` | 0x082C4AEC | GEC 标记 | 0 | `0x4A93E8` |

**推论**：G2F=0 ⇒ `0x4A93E0` 跳过函数体 ⇒ GATE/GEC 永不设。

### 1.1 GATE=3 的前提

```asm
004A7E20  cmp          dword ptr [0x82C4A88], 1        ← GATE 必须为 1
004A7E27  jne          0x4A7E56
004A7E37  mov          dword ptr [0x82C4A88], 3        ← GATE := 3
```


---

## 2. State Machine Initialization Chain (Corrected)

The state machine at `0x808240` is a **sequential initialization chain**, not a simple dispatch table. Each state is gated by enable flag + primary check + secondary check:

| State | Enable Flag | Enable Value | Primary Flag | Secondary Flag | Status |
|---|---|---|---|---|---|
| 1 | `0xE57A55` | **1** ✓ | `0xC7AEBF0` | `0x337E301` | Enabled |
| 0 | `0xE57A54` | **1** ✓ | `0xC7AEAC0` | `0x337E27D` | Enabled |
| 3 | `0xE57A58` | **1** ✓ | `0xC7AEF80` | `0x337E48D` | Enabled |
| 2 | `0xE57A56` | 0 ✗ | `0xC7AED20` | — | Disabled |
| 5 | `0xE57A59` | 0 ✗ | `0xC7AF0B0` | `0x337E511` | Disabled |
| 6/8 | `0xE57A5C` | **0** ✗ | `0xC7AF440` | `0x337E69D` | ★ Marketplace gate |
| 6 | `0xE57A5A` | 0 ✗ | `0xC7AF1E0` | `0x337E595` | Disabled |
| 7 | `0xE57A5B` | 0 ✗ | `0xC7AF310` | `0x337E619` | Disabled |
| 9 | `0xE57A5D` | 0 ✗ | `0xC7AF570` | `0x337E721` | Disabled |

**Key finding**: `E57A5C=0` → state 6/8 block skipped (`je 0x8085CD`) → `0xC7AF440` **never read**.

---

## 3. Blockage Closure

```
[0x84ABA50]=0 → state 0 → return → never reaches state 5
[0x84ABB2F]=0 → 0x4A93E0 guard fails → GATE/GEC never set
[0x82C4A88]=0 → cmp [0x82C4A88], 3 fails → state 5 adjudication skipped
[0xC7AF1E0]=0 → 0x50DF80 skipped → gates 1/2/3 never initialized
[0xC7AF440] unreachable → state 6 never dispatched
[E57A5C]=0 → entire state-6 block skipped → 0xC7AF440 never read
[0xE60B80]=0 → triple gate (0x4A9990/999C/99A8) all unsatisfied
```

---

## 4. Writable Flag Map

| Global | Write Site | Type |
|---|---|---|
| `[0x84ABB2F]` | `0x80A36E` | Data write (G2F guard) |
| `[0x82C4A88]` | `0x4A7E37`(val=3), `0x4A9443`(val=1), `0x4A80FD`(val=2) + 5 dynamic | GATE |
| `[0x82C4AEC]` | `0x4A93E8`(val=1) | GEC |
| `[0xE60B80]` | `0x4A8F53`, `0x50E008` | Written (not read) |
| `[0x84ABA50]` | 30+ refs (`0x5E8F11` has `cmp ... 5`) | State index |
| `[0x849BA3D]` | 16 refs | Substate flag |
| `[0xC7AF1E0]` | No direct write | BSS init gate |
| `[0xC7AF440]` | No direct write | BSS state-6 enable |
| `[0x33E6A18]` | No direct write | DW config object |
| `[0xE57A5C]` | No direct write (static=0) | Dispatch enable |

---

## 5. Verifiable Evidence List

| # | Type | Location | Evidence |
|---|---|---|---|
| 1 | disassembly | `0x4A93E0`–`0x4A9456` | G2F guard + GEC/GATE writes |
| 2 | disassembly | `0x4A7E20`/`0x4A7E37` | GATE=3 depends on GATE=1 |
| 3 | disassembly | `0x4A9850`–`0x4A9932` | GATE check (`cmp [0x82C4A88], 3`) |
| 4 | disassembly | `0x4A8F00`–`0x4A8F8F` | Writes `[0xE60B80]` (not reads) |
| 5 | disassembly | `0x50DF80`–`0x50E07B` | `[0xC7AF1E0]=0` → skip |
| 6 | disassembly | `0x808240`–`0x8085E0` | State jump table `0x808634` |
| 7 | data | `0x808634` | 6 entries: state 0-4→cleanup, 5→`0x808295` |
| 8 | data | `0x7F25DC` | lobby state 5 → `0x7F25D6` (`mov eax,3; ret`) |
| 9 | disassembly | `0x7EEBF0`–`0x7EEC8D` | state 5 handler, only caller of `0x4A9850` |
| 10 | disassembly | `0x4FE120`–`0x4FE13B` | G2F write chain |
| 11 | disassembly | `0x80A36E` | `mov byte [0x84ABB2F], 1` — unique writer |
| 12 | disassembly | `0x50EA88` | `0x50E930` jump table, state 6 → `0x50EA12` |
| 13 | disassembly | `0x4F8AD0`–`0x4F8B11` | Callers of `0x808240`: `0x4F8AF2`, `0x4F8B0A`, `0x5C29CE` |
| 14 | disassembly | `0x8083B3` | `cmp byte [0xE57A5C], 0` — dispatch enable gate |
| 15 | runtime | `0xE57A40`–`0xE57A5F` | 76 samples (40.7s–116.8s): E57A58=1, E57A5C=0, rest=0 |

> All evidence from static analysis of `image_best.bin` using `_tier1_disasm.py` / `_tier1_static_search.py` / `_archscan.py`.
> Runtime sampling by user (E57A4x table, 2026-09-30).
> Scripts archived at `D:\BaiduNetdiskDownload\使命召唤OL\`.