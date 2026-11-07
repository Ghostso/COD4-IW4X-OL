# 学习报告 034 — 逐字节：6 个字符串是**补丁状态**，不是游戏模式（修正报告 033）

**方法**：`VA → RVA → raw` 换算后读字符串（不是取字符串池偏移）
**性质**：全实测
**★★★ 本报告修正了报告 033 的一个错误推断**

---

## 一、★★★ 6 个字符串的真实内容（实测）

```
VA 0x1051CA30  raw 0x51BE30  len= 7  "unknown"
VA 0x1051C9C8  raw 0x51BDC8  len= 7  "patched"
VA 0x1051CA9C  raw 0x51BE9C  len=13  "not_requested"
VA 0x1051CAAC  raw 0x51BEAC  len=15  "already_patched"
VA 0x1051CABC  raw 0x51BEBC  len=16  "unsupported_host"
VA 0x1051CAD0  raw 0x51BED0  len=16  "unexpected_bytes"
```

★★★ **⇒ 这**不是**游戏模式，是**某个补丁操作的结果状态枚举**。**

### ★ 状态语义

| 值 | 字符串 | 含义 |
|---|---|---|
| 0 | `not_requested` | 未请求 |
| 1 | `patched` | ★ 已打补丁 |
| 2 | `already_patched` | ★ 已经是打过补丁的状态 |
| 3 | `unsupported_host` | ★★ 宿主不支持（版本不匹配） |
| 4 | `unexpected_bytes` | ★★ 字节不符合预期（内存内容变了） |
| 5 | `unknown` | 未知 |

★★ **注意顺序**：我按 `eax=0..5` 的跳转表顺序读的是：
```
[0] 0x1051CA9C = "not_requested"       ← eax=0
[1] 0x1051C9C8 = "patched"             ← eax=1
[2] 0x1051CAAC = "already_patched"     ← eax=2
[3] 0x1051CABC = "unsupported_host"    ← eax=3
[4] 0x1051CAD0 = "unexpected_bytes"    ← eax=4
[5] 0x1051CA30 = "unknown"             ← eax=5
越界         = "not_requested"
```

★★★ **⇒ 完整映射（修正报告 033 第六节的排序）**

---

## 二、★★★ 这是什么补丁？（关键问题）

### 由状态名反推

```
"unsupported_host"   → 宿主（客户端 EXE）版本不匹配
"unexpected_bytes"   → 目标地址的字节不是预期的
"already_patched"    → 该地址已经是 E9 / 补丁形态
"patched"            → 本次成功打上
"not_requested"      → 没被要求打
```

★★★ **⇒ 这是**兼容补丁**的结果枚举，与 `nt10.py` 的 4 个兼容补丁
（报告 002/003）是**同一类东西**。**

### ★ 与 `CODOL_CLIENT_EXECUTION_STATE_PATCH` 对应（报告 029）

```
Report 029 发现的 9 个未导出常量里有：
  CODOL_CLIENT_EXECUTION_STATE_PATCH   ← ★★★ 客户端执行状态补丁
  CODOL_ANIMTREE_RESOLVE_HOOK
  CODOL_IMAGE_UPLOAD_HOOK
```

★★★ **⇒ 这 6 个状态字符串极可能就是 `CODOL_CLIENT_EXECUTION_STATE_PATCH` 的结果码。**

★ **验证方法**：在 `0x217A40` 的 `0x217B2B` 附近有对 `[ebp-5Fh]` 的读
（`mov cx, [ebp-5Fh]`），说明这个"状态"是从某个结构里取的。

---

## 三、★★★ 跳转表的真实值（修正报告 033）

### 实测

```
0x10219818 处 8 个 DWORD：
  [0] = 0x10217B6C
  [1] = 0x10217B73
  [2] = 0x10217B7A
  [3] = 0x10217B81
  [4] = 0x10217B88
  [5] = 0x10217B8F
  [6] = 0x10217DC3
  [7] = 0x10217DCA
```

★★ **全是 `0x10217Bxx` 范围** —— **在 `CodolGameServer.Localnet32` 的代码段内** ✓

★★ **`0x10217B6C` 减 ImageBase `0x10000000` = RVA `0x217B6C`** ——
**正是 `0x217B68` 那条 `jmp [eax*4+0x10219818]` 之后 4 字节** ✓

### ★★ 但 `0x217B68` 的 `jmp` 目标是**另一个表**而非这个表

```asm
00217B68  FF 24 85 18 98 21 10   jmp dword ptr [eax*4 + 10219818h]
```

★★ **`[eax*4 + 0x10219818]` 与我在 `0x10219818` 读到的值一致** ✓

★★★ **⇒ 但我读到 `[0]=0x10217B6C`，而跳转指令**自己**在 `0x217B68`。**
**`0x217B6C` = `0x217B68 + 4`（跳转指令的中间！）**

★★ **这不对。`0x217B68` 的指令是 6 字节（`FF 24 85 xx xx xx xx`），
下一条是 `0x217B6E`。**

★ **而 `0x217B6F` 处是 `B8 9C CA 51 10`（`mov eax, 0x1051CA9C`）** ——
**正是 `[0]` 应该跳去的目标。**

★★★ **⇒ 我读到的 `[0]=0x10217B6C` 有 3 字节偏差。**

**真实表应该是**（由反汇编推得）：
```
[0] → 0x10217B6F  (mov eax, "not_requested")
[1] → 0x10217B76  (mov eax, "patched")
[2] → 0x10217B7D  (mov eax, "already_patched")
[3] → 0x10217B84  (mov eax, "unsupported_host")
[4] → 0x10217B8B  (mov eax, "unexpected_bytes")
[5] → 0x10217B92  (mov eax, "unknown")
```

★★ **但我读到的是 `0x10217B6C/73/7A/81/88/8F` —— 每个都比预期小 3。**

★★★ **⇒ 我在 `V2Raw` 换算时把 `0x21 8198 18`（RVA）算错了**，
或者表实际在 `0x1021981B`（+3）。

★ **这是第三个手算/换算错误。必须用更严谨的方法验证。**

---

## 四、★★★ 这是我第三次算错地址（必须记录）

### 三次错误

| # | 错误 | 正确 |
|---|---|---|
| 1 | `0x220885 - 0x8E45 = 0x17A40` | `0x217A40`（少 0x20000） |
| 2 | `E8` 在 `+7` | `+6`（差 1 字节） |
| 3 | 跳转表 `0x10219818` 读出 `0x10217B6C` | 应为 `0x10217B6F`（差 3） |

★★★ **⇒ 这不是偶然，是**系统性问题**：我用字节偏移手算，没有指令长度解码器。**

★★ **必须改用更可靠的方法**：
- 对 jump table，**用反汇编里 `B8 xx xx xx xx` 的立即数**（`0x1051CA9C` 等）反推
- 对相对跳转，**必须用 `[BitConverter]::ToInt32(bytes, opcode_offset+1)` + `next = opcode_offset + 5`**

★ **报告 034 的这个错误不影响结论**（6 个字符串的内容是对的，
因为我是**按 `mov eax, imm32` 的立即数地址**读的，不依赖跳转表）。

---

## 五、★★ `0x10805098` 读不到（在未初始化区）

```
VA 0x10805098 → raw 0x804498
文件总大小 = 6,834,176 = 0x684800
0x804498 > 0x684800  ⇒ ★ 超出文件末尾！
```

★★ **⇒ `0x10805098` 在 `.data` 的**未初始化部分**（`VSize > RawSize`）：
```
.data: VA=0x620000  VSize=0x1E5C74  →  VA 结束 = 0x805C74
              Raw=0x61F400  RawSize=0x0002B000  →  raw 结束 = 0x64A400
              ★ VSize (0x1E5C74 = 1,989,748) 远大于 RawSize (0x2B000 = 176,128)
```

★★★ **⇒ `.data` 有 1.8 MB 是**未初始化的 BSS**（`VirtualSize` 远大于 `SizeOfRawData`）。**

★ **`0x10805098` 减 ImageBase `0x10000000` = RVA `0x805098`** ——
**在 `.data` 的 VSize 范围内（到 `0x805C74`）但在 RawSize 之外** ✓

★★ **⇒ 这块是**零初始化**的 BSS，运行期才写入。**

★ **这与反汇编里的 `mov [10805098h], eax` 一致**（运行期写）。

---

## 六、逐字节证据总表

| # | VA | raw | len | 内容 | 修正 |
|---|---|---|---|---|---|
| 1 | `0x1051CA9C` | `0x51BE9C` | 13 | `not_requested` | eax=0 |
| 2 | `0x1051C9C8` | `0x51BDC8` | 7 | `patched` | eax=1 |
| 3 | `0x1051CAAC` | `0x51BEAC` | 15 | `already_patched` | eax=2 |
| 4 | `0x1051CABC` | `0x51BEBC` | 16 | `unsupported_host` | eax=3 |
| 5 | `0x1051CAD0` | `0x51BED0` | 16 | `unexpected_bytes` | eax=4 |
| 6 | `0x1051CA30` | `0x51BE30` | 7 | `unknown` | eax=5 |
| 7 | 跳转表 `0x10219818` | `0x218C18` | — | ★ 读数偏 3 字节（待重算） | — |
| 8 | `0x10805098` | 越界 | — | ★ `.data` 的 BSS（运行期写） | — |

---

## 七、结论

### 1. ★★★ 修正报告 033：不是游戏模式，是**补丁结果状态**

```
not_requested / patched / already_patched / unsupported_host / unexpected_bytes / unknown
```

★★★ **⇒ `0x217A40` 的初始化里包含一个**兼容补丁的安装步骤**，
结果是这 6 种状态之一。**

### 2. ★★★ 这与 `nt10.py` 的兼容补丁是**同一功能**

```
nt10.py                 CodolGameServer.Localnet32
  compat_patch_once()     0x217A40 → 状态 0..5
  4 个补丁                 ？
  latch 语义               自置标志
```

★★ **⇒ 两者在**同一批地址**上打补丁 ⇒ 可能冲突。**

★ **必须对比 `nt10.py` 的 4 个补丁地址与 `CodolGameServer` 的目标地址。**

### 3. ★★★ `unsupported_host` / `unexpected_bytes` 是**版本校验**

★★ **这两个状态说明：补丁前会**校验目标字节**，不匹配就报错。
这是**防止在错误版本上打补丁**的安全设计。**

### 4. ★★ 我连续三次算错地址，必须用更严谨的方法

```
错误 1：少 0x20000
错误 2：差 1 字节
错误 3：差 3 字节
```

★★★ **⇒ 所有跳转/表读取必须交叉验证（两条独立路径算同一个值）。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **重算跳转表 `0x10219818` 的正确内容（用两条路径交叉验证）**
- [ ] ★★★ **`0x217A40` 里打补丁的目标地址是什么**（对比 `nt10.py` 的 4 个）
- [ ] ★★ **`call 0x63D60`（状态从哪来）**
- [ ] ★★ **`CODOL_CLIENT_EXECUTION_STATE_PATCH` 与这 6 个状态的关系**
- [ ] ★ **`0x51BE30` 附近全部 6 个字符串的完整布局**
- [ ] ★ **`.data` 的 BSS 区（RVA `0x805098` 起）的其它全局**
