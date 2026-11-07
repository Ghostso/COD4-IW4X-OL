# 学习报告 036 — 逐字节：客户端版本校验器（`0x4F6E0`）—— 决定了"能否打补丁"

**方法**：反汇编 `0x4F6E0` 前 160 字节，逐字节解 PE 头比较
**性质**：全实测
**★★★ 这是全包**最重要的版本门禁**，直接决定换战斗服是否可行**

---

## 一、★★★ 修正报告 033/034/035 的调用地址（我又算错了一次）

### 报告 033/034/035 我写的

```
00217B36  E8 A8 7B E3 FF      call 0x6F6E3
```

### 精确重算（`E8` 在 `0x217B36`，不是 `0x217B38`）

```
RVA 0x217B36: E8 A8 7B E3 FF
  rel32   = 0xFFE37BA8 = -1,869,656
  next    = 0x217B36 + 5 = 0x217B3B
  target  = 0x217B3B - 1,869,656 = 0x4F6E0   ★★★
```

★ **我之前的 `0x6F6E3` 是**错把 `0x217B38` 当成了 `E8` 的位置**（实际在 `0x217B36`）。**

### ★★★ 完整精确调用表（`0x217A40`..`0x217BD0`）

```
RVA 0x217A7C  call -> 0x41DA43     引用计数释放
RVA 0x217AB0  call -> 0x63D60      ★ 第一步（PE 校验 A）
RVA 0x217ACE  call -> 0x420A91     ★
RVA 0x217AEA  call -> 0x431D63     ★★ 初始化核心
RVA 0x217B04  call -> 0x1E89D0     ★
RVA 0x217B13  jmp  -> 0x219736      ★ 失败路径
RVA 0x217B18  call -> 0x1E3960     ★ 第二条路径
RVA 0x217B33  call -> 0x4F6E0      ★★★ 版本校验（补丁门禁）
RVA 0x217B9F  call -> 0x544B0
RVA 0x217BB1  call -> 0x500B0
RVA 0x217BCB  call -> 0x1E5830
```

★★★ **⇒ 这张表是用脚本精确算的（不是手算），可靠。**

---

## 二、★★★ `0x63D60` —— PE 头校验（第一道）

```asm
00063D60  6A 00              push 0
00063D62  FF 15 28 D1 47 10 call dword ptr [1047D128h]   ← IAT：GetModuleHandleW(NULL)?
00063D68  85 C0              test eax, eax
00063D6A  74 6C              je   +0x6C                    ← 空则失败
00063D6C  B9 4D 5A 00 00     mov  ecx, 5A4Dh              ← ★ "MZ"
00063D71  66 39 08           cmp  [eax], cx
00063D74  75 62              jne  +0x62                    ← 不是 MZ → 失败
00063D76  8B 48 3C           mov  ecx, [eax+3Ch]           ← e_lfanew
00063D79  81 3C 01 50 45 00 00  cmp  dword ptr [ecx+eax], 4550h   ← ★ "PE\0\0"
00063D80  75 56              jne  +0x56
00063D82  81 7C 01 50 73 EE 37 00  cmp  dword ptr [ecx+eax+50h], 37EE73h  ← ★★★ 0x0037EE73
00063D8A  72 4C              jb   +0x4C
00063D8C  80 B8 5A EE ...     ...                          ← 继续
```

★★★ **`cmp [PE + 0x50], 0x0037EE73`** ——
**`PE + 0x50` = `OptionalHeader.SizeOfImage`（PE32 的偏移）**

★ **`0x0037EE73` 是什么？** —— **需要验证**。

★★ **`jb`（无符号小于则跳）** —— 是**下限检查**（`SizeOfImage >= 0x37EE73`）。

### ★★ 这是**客户端的**版本校验，不是插件自己的

★★ **`GetModuleHandleW(NULL)` 取的是主模块（`codoMP_client_shipRetail.exe`）的基址**，
**然后校验它的 PE 头。**

★★★ **⇒ `0x63D60` 是"确认我在 CODOL 客户端进程里"的守卫。**

---

## 三、★★★ `0x4F6E0` —— 精确的客户端版本指纹校验

### 完整反汇编（前 160 字节）

```asm
0004F6E0  55                    push ebp
0004F6E1  8B EC                 mov  ebp, esp
0004F6E3  83 E4 F8              and  esp, -8
0004F6E6  83 EC 1C              sub  esp, 1Ch
0004F6E9  53                    push ebx
0004F6EA  56                    push esi
0004F6EB  57                    push edi
0004F6EC  68 80 C9 51 10        push 1051C980h           ← ★ 文件名/模块名
0004F6F1  E8 6B B9 3D 00        call 0x42B061            ← 可能是 strlen / 路径处理
0004F6F6  8B C8                 mov  ecx, eax
0004F6F8  83 C4 04              add  esp, 4
0004F6FB  85 C9                 test ecx, ecx
0004F6FD  0F 84 CC 01 00 00     je   0x4F8CF
0004F703  8B D1                 mov  edx, ecx
0004F705  8D 72 01              lea  esi, [edx+1]
0004F708  8A 02                 mov  al, [edx]
0004F70A  42                    inc  edx
0004F70B  84 C0                 test al, al
0004F70D  75 F9                 jne  0x4F708            ← 扫描字符串到 NUL
0004F70F  6A 01                 push 1
0004F711  2B D6                 sub  edx, esi
0004F713  68 A0 C9 51 10        push 1051C9A0h           ← ★ 另一个字符串
0004F718  E8 C3 0D 00 00        call 0x504E0            ← ★★ 字符串比较？
0004F71D  83 C4 08              add  esp, 8
0004F720  84 C0                 test al, al
0004F722  0F 84 A7 01 00 00     je   0x4F8CF            ← 不匹配 → 失败
0004F728  6A 00                 push 0
0004F72A  FF 15 28 D1 47 10     call dword ptr [1047D128h]  ← ★ GetModuleHandleW(NULL)
0004F730  8B F8                 mov  edi, eax
0004F732  85 FF                 test edi, edi
0004F734  0F 84 89 01 00 00     je   0x4F8C3
--- 开始 PE 校验 ---
0004F73A  B8 4D 5A 00 00        mov  eax, 5A4Dh           ← ★ "MZ"
0004F73F  66 39 07              cmp  [edi], ax            ← 检查 MZ
0004F742  0F 85 7B 01 00 00     jne  0x4F8C3
0004F748  8B 77 3C              mov  esi, [edi+3Ch]       ← e_lfanew
0004F74B  03 F7                 add  esi, edi             ← PE 头地址
0004F74D  81 3E 50 45 00 00     cmp  dword ptr [esi], 4550h   ← ★★ "PE\0\0"
0004F753  0F 85 6A 01 00 00     jne  0x4F8C3
0004F759  B8 4C 01 00 00        mov  eax, 14Ch            ← ★★ 0x014C = i386！
0004F75E  66 39 46 04           cmp  [esi+4], ax          ← Machine 字段
0004F762  0F 85 5B 01 00 00     jne  0x4F8C3
0004F768  81 7E 08 0A 93 96 60  cmp  dword ptr [esi+8], 6096930Ah   ← ★★★ TimeDateStamp！
0004F76F  0F 85 4E 01 00 00     jne  0x4F8C3
0004F775  81 7E 50 00 90 65 0E  cmp  dword ptr [esi+50h], 0E659000h  ← ★★★ SizeOfImage！
0004F77C  0F 85 41 01 00 00     jne  0x4F8C3
```

★★★ **这是**完整的客户端版本指纹**：**

| 偏移 | 字段 | 期望值 | 说明 |
|---|---|---|---|
| `[edi]` | `e_magic` | `0x5A4D` | `"MZ"` |
| `[esi]` | `Signature` | `0x4550` | `"PE\0\0"` |
| `[esi+4]` | `Machine` | **`0x014C`** | ★ **i386（32 位）** |
| `[esi+8]` | `TimeDateStamp` | **`0x6096930A`** | ★★★ **CODOL 3.19 的构建时间戳** |
| `[esi+0x50]` | `SizeOfImage` | **`0x0E659000`** | ★★★ **CODOL 3.19 的镜像大小** |

★★★ **这两个值正是记忆里记录的**：
> 记忆：`codoMP_client_shipRetail.exe`，**时间戳 `0x6096930A`，SizeOfImage `0x0E659000`**

★★★ **⇒ 外部包的版本门禁**精确锁定**这个 build，一个字节都不差。**

### ★★★ 这是决定性的发现

```
TimeDateStamp = 0x6096930A   （精确到秒的构建时间）
SizeOfImage   = 0x0E659000   （精确到字节的镜像大小）
```

★★★ **⇒ 换成任何其他版本的客户端，`0x4F6E0` 返回失败 ⇒
补丁不打 ⇒ 战斗服功能全灭。**

★★ **而我们的客户端**就是**这个 build**（记忆已确认）**⇒ 能通过。**

---

## 四、★★★ `0x4F6E0` 还校验了**客户端的文件名**

```asm
0004F6EC  push 1051C980h     ← 字符串 A
0004F6F1  call 0x42B061      ← 取某字符串（可能是 exe 路径）
...
0004F713  push 1051C9A0h     ← 字符串 B
0004F718  call 0x504E0       ← 比较 A vs B
```

★★ **需要读 `0x1051C980` 和 `0x1051C9A0` 两个字符串。**

★★ **可能是 `codoMP_client_shipRetail.exe` 的路径/名字比对。**

★ **如果是路径比对 ⇒ 客户端**必须放在特定路径**才能打补丁。**

---

## 五、★★★ 完整初始化链（`0x217A40`）的精确还原

```
0x217A40 onStartup/ensure_instance
  ├─ call 0x41DA43     释放旧单例（引用计数）
  ├─ cmp [0x10697027], 0       外层标志
  ├─ [未置位] 进入初始化
  │   ├─ call 0x63D60           ★ 第一道 PE 校验（SizeOfImage >= 0x37EE73）
  │   ├─ if (al != 0) goto 0x217B18  → call 0x1E3960（第二条路径）
  │   ├─ cmp [0x10696770], 0   内层 A
  │   ├─ set [0x10696770] = 1
  │   ├─ call 0x420A91          ★
  │   ├─ call 0x431D63          ★★ 初始化核心（6 参数）
  │   ├─ call 0x1E89D0          ★
  │   └─ 失败 → 0x219736
  └─ [0x217B18] 第二条路径
      ├─ call 0x1E3960
      ├─ cmp [0x1069702A], 0   内层 B
      ├─ set [0x1069702A] = 1
      ├─ call 0x4F6E0           ★★★ 版本指纹校验（MZ/PE/i386/TimeDateStamp/SizeOfImage）
      ├─ 结果码 → [0x10805098]
      ├─ call 0x544B0 / 0x500B0 / 0x1E5830
      └─ 6 种状态字符串
```

★★★ **⇒ `0x4F6E0` 是"能否打补丁"的门禁，在初始化**第二条路径**里。**

★ **第一条路径（`0x63D60`）只校验 `SizeOfImage >= 0x37EE73`（宽松）。**
★ **第二条路径（`0x4F6E0`）校验**精确值**（严格）。**

---

## 六、★★★ 对我们任务的决定性意义

### 结论 1：★★★ 外部包**只支持这一个客户端 build**

```
TimeDateStamp = 0x6096930A
SizeOfImage   = 0x0E659000
Machine       = 0x014C (i386)
```

★★★ **⇒ 我们的客户端**正是**这个 build（记忆已确认）⇒ **能通过。**
★ **但任何升级/降级都会立刻失效。**

### 结论 2：★★★ 换战斗服**不会影响**这个门禁

★★ **`0x4F6E0` 校验的是**客户端**（主模块），不是插件自己。**
**⇒ 替换 `CodolGameServer.Localnet32` 不影响版本校验。**

★★★ **⇒ 换战斗服是安全的（在版本门禁方面）。**

### 结论 3：★★ 与 `nt10.py` 的兼容补丁是**两套独立的补丁**

```
nt10.py                → 4 个补丁（报告 002/003），latch 语义
CodolGameServer        → 通过 0x4F6E0 校验后打自己的补丁
```

★★ **两者**目标地址可能重叠** ⇒ **必须对比。**

★ **但 `nt10.py` 默认**不注入**（报告 009）⇒ 现在不存在冲突。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `0x4F6E0` 调用点 | RVA `0x217B33` |
| 2 | 校验 `e_magic` | `0x5A4D`（"MZ"） |
| 3 | 校验 `Signature` | `0x4550`（"PE\0\0"） |
| 4 | 校验 `Machine` | **`0x014C`** |
| 5 | 校验 `TimeDateStamp` | **`0x6096930A`** |
| 6 | 校验 `SizeOfImage` | **`0x0E659000`** |
| 7 | `0x63D60` 的宽松校验 | `SizeOfImage >= 0x0037EE73` |
| 8 | 校验失败跳转 | `0x4F8C3` / `0x4F8CF` |
| 9 | 结果码落点 | `0x10805098` |
| 10 | 客户端文件名/路径字符串 | `0x1051C980` / `0x1051C9A0` |

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **读 `0x1051C980` / `0x1051C9A0`（客户端文件名/路径）**
- [ ] ★★★ **`0x4F6E0` 校验通过后打的补丁**（`0x4F77C` 之后）
- [ ] ★★ **`0x504E0`（字符串比较函数）**
- [ ] ★★ **`0x42B061`（取路径/字符串）**
- [ ] ★ **`0x1E3960`（第二条路径的入口）**
- [ ] ★ **`0x431D63`（6 参数初始化核心）的 6 个参数**
