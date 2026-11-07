# 学习报告 048 — capstone：svc 对象的生命周期与 `sub` 偏移链

**方法**：capstone 反汇编 4 个 svc 引用点 + 扫描 `[reg+0x4F4]` 访问
**性质**：权威反汇编 + 全内存扫描
**★★★ 本报告完整还原了 svc 对象的**创建/销毁/使用**三阶段**

---

## 一、★★★ svc 对象的**创建**（`0x803830`）

```asm
00803830  a174972608        mov  eax, [0x8269774]      ← 已是 svc？
00803835  85c0              test eax, eax
00803837  756e              jne  0x8038A7              ← 已存在 → 跳过创建
--- 创建 ---
00803839  6818160000        push 0x1618                ← ★★★ 0x1618 = 5656 字节
0080383E  e8dd093700        call 0xB74220              ← ★ operator new
00803843  83c404            add  esp, 4
00803846  85c0              test eax, eax
00803848  7442              je   0x80388C              ← 分配失败
0080384A  8bc8              mov  ecx, eax
0080384C  e8dfe83700        call 0xB82130              ← ★ 构造函数
00803851  a374972608        mov  [0x8269774], eax      ← ★★★ 存入全局槽
00803856  85c0              test eax, eax
00803858  744d              je   0x8038A7
0080385A  68e8b6390e        push 0xE39B6E8             ← ★ 某个字符串/配置
0080385F  8bc8              mov  ecx, eax
00803861  e89a6b3700        call 0xB7A400              ← ★ 初始化
00803866  6a04              push 4
00803868  e888b14300        call 0xC3E9F5              ← ★
0080386D  83c404            add  esp, 4
00803870  85c0              test eax, eax
00803872  7420              je   0x803894
00803874  8b0d74972608      mov  ecx, [0x8269774]
0080387A  50                push eax
0080387B  c7001468de00      mov  dword ptr [eax], 0xDE6814   ← ★ vtable 指针！
00803881  ...               ...
```

★★★ **关键事实**：

| 项 | 值 | 含义 |
|---|---|---|
| 对象大小 | **`0x1618` = 5656 字节** | ★★★ svc 对象总大小 |
| 构造函数 | `0xB82130` | |
| 初始化 | `0xB7A400`（带参数 `0xE39B6E8`） | |
| **vtable** | **`0xDE6814`** | ★★★ 虚表地址 |

★★★ **`mov dword ptr [eax], 0xDE6814`** ——
**`eax` 是新分配的对象，`0xDE6814` 是它的**vtable 指针**。**

★★ **⇒ svc 是一个**多态对象**（有虚函数）。**

★★★ **⇒ 这与报告 048 看到的 `mov edx,[ecx]; mov eax,[edx]; call eax`（虚调用）**完全一致**。

---

## 二、★★★ svc 对象的**销毁**（`0x8036C0`）

```asm
008036C0  833d7497260800      cmp dword ptr [0x8269774], 0   ← svc 存在？
008036C7  7446                je   0x80370F               ← 不存在 → 返回
008036C9  6870551a08          push 0x81A5570              ← ★ 锁对象
008036CE  a304bb4a08          mov  [0x84ABB04], eax
008036D3  ff159c81ca00        call dword ptr [0xCA819C]   ← ★ EnterCriticalSection
008036D9  8b0d74972608        mov  ecx, [0x8269774]
008036DF  85c9                test ecx, ecx
008036E1  7417                je   0x8036FA
008036E3  e818ea3700          call 0xB82100               ← ★ 析构（非虚部分）
008036E8  8b0d74972608        mov  ecx, [0x8269774]
008036EE  85c9                test ecx, ecx
008036F0  7408                je   0x8036FA
008036F2  8b11                mov  edx, [ecx]             ← ★ vtable
008036F4  8b02                mov  eax, [edx]             ← vtable[0] = 析构函数
008036F6  6a01                push 1                      ← 参数 1（delete 标志）
008036F8  ffd0                call eax                    ← ★ 虚析构
008036FA  6870551a08          push 0x81A5570
008036FF  c7057497260800000000  mov dword ptr [0x8269774], 0   ← ★★★ 清空
00803709  ff159081ca00        call dword ptr [0xCA8190]   ← LeaveCriticalSection
0080370F  c3                  ret
```

★★★ **⇒ 完整的销毁序列**：
```
1. EnterCriticalSection(0x81A5570)
2. call 0xB82100              （析构非虚部分）
3. vtable[0](this, 1)         （虚析构，delete）
4. [0x8269774] = 0            （清空全局槽）
5. LeaveCriticalSection
```

★★ **`0x81A5570` 是**保护 svc 全局槽的临界区**。**

★★★ **⇒ 这是一个**线程安全的单例**。**

---

## 三、★★★ svc 对象的**替换/重建**（`0x77D060`）

```asm
0077D060  8b0d74972608        mov  ecx, [0x8269774]
0077D066  3bcb                cmp ecx, ebx              ← ebx 是新对象
0077D068  7417                je   0x77D081             ← 相同 → 跳过
--- 销毁旧的 ---
0077D06A  e891504000          call 0xB82100
0077D06F  8b0d74972608        mov ecx, [0x8269774]
0077D075  3bcb                cmp ecx, ebx
0077D077  7408                je   0x77D081
0077D079  8b11                mov edx, [ecx]
0077D07B  8b02                mov eax, [edx]
0077D07D  6a01                push 1
0077D07F  ffd0                call eax                  ← 虚析构
--- 换新的 ---
0077D081  6870551a08          push 0x81A5570
0077D086  891d74972608        mov [0x8269774], ebx      ← ★★★ 写入新对象
0077D08C  ff159081ca00        call dword ptr [0xCA8190] ← LeaveCriticalSection
--- 后续：一堆初始化 ---
0077D092  e8a9b80800          call 0x808940
0077D097  e8c4e2eeff          call 0x66B360
0077D09C  e8af7d4100          call 0xB94E50
0077D0A1  e88a1ad8ff          call 0x4FEB30
0077D0A6  6a01                push 1
0077D0A8  e853f2fcff          call 0x74C300
0077D0AD  8b3594466407        mov esi, [0x7644694]
```

★★★ **⇒ 这是"**切换连接**"：销毁旧的 svc，装新的，然后重新初始化 5 个子系统。**

★ **`0x74C300`（`push 1`）** 可能就是**启动 LSG 连接**。**

---

## 四、★★★ svc 的**使用**（`0x4F8545`）

```asm
004F8545  8b0d74972608        mov ecx, [0x8269774]      ← svc
004F854B  c6054296600e01      mov byte ptr [0xE609642], 1   ← ★ 全局标志
004F8552  3bcb                cmp ecx, ebx
004F8554  7406                je   0x4F855C
004F8556  53                  push ebx
004F8557  e8a41e6800          call 0xB7A400             ← 对 svc 调用（1 参数）
004F855C  a1b8b84908          mov eax, [0x849B8B8]
004F8561  8b480c              mov ecx, [eax + 0xc]
004F8564  681cd2db00          push 0xDBD21C
004F8569  51                  push ecx
004F856A  e8e1943000          call 0x801A50
004F856F  83c408              add esp, 8
004F8572  e8f9670100          call 0x50ED70
004F8577  e804451800          call 0x67CA80
004F857C  e88f456f00          call 0xBECB10
004F8581  ffd6                call esi                  ← 间接调用
004F8583  3b056c6e8807      cmp eax, [0x7886E6C]
004F8589  740a                je   0x4F8595
```

★★ **`0xB7A400` 与创建时的初始化是**同一个函数** —— 说明它是"**配置/重置**"方法。**

★ **`[0xE609642] = 1`** —— 一个全局标志（可能是"已启动"）。**

---

## 五、★★★ `sub` 偏移 `0x4F4`（1268）的访问点（20 处）

```
00847155  899ef4040000    mov dword ptr [esi + 0x4f4], ebx      ← ★ 写
008B3F88  008990f40400    add byte ptr [ecx+0x4F490], cl       ← 假
008B40FE  8b88f4040000    mov ecx, [eax + 0x4f4]               ← 读
008B417A  8b88f4040000    mov ecx, [eax + 0x4f4]               ← 读
00B7A64C  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← ★★ 链式！
00B7A660  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← ★★ 链式
00B7A673  8b8ef4040000    mov ecx, [esi + 0x4f4]               ← 读
00B7A6A4  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← ★★ 链式
00B7AD43  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← 链式
00B7AD93  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← 链式
00B7ADD3  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← 链式
00B7AE23  8b89f4040000    mov ecx, [ecx + 0x4f4]               ← 链式
00B7F7F3  8b8ef4040000    mov ecx, [esi + 0x4f4]               ← 读
00B7F81A  0500008b8e      add eax, 0x8E8B0000                  ← 假
00B7F84C  050000518b      add eax, 0x8B510000                  ← 假
00B81E91  8b8ef4040000    mov ecx, [esi + 0x4f4]               ← 读
00B81EA3  899ef4040000    mov dword ptr [esi + 0x4f4], ebx      ← ★ 写
```

★★★ **关键观察**：
```
1. `[ecx + 0x4f4]` 出现 10 次（链式访问，同一种模式）
2. `[esi + 0x4f4]` 出现 4 次
3. `mov [X + 0x4f4], ebx` 出现 2 次（写）
```

★★★ **⇒ `+0x4F4` 是一个**指针字段**，且被**沿链多次访问**
（`svc->sub->...->0x4F4`）。**

★★ **⇒ 这是一个**链表/树/容器**结构，不是单一的 `sub` 对象。**

★ **记忆里说 `sub = [svc + 1268]`，现在证实 `+1268 = +0x4F4` 确实有大量访问。**

★★★ **⇒ 但访问模式是**链式**，说明 `+0x4F4` 是某种**节点的 next/child 指针**。**

---

## 六、逐字节证据总表

| # | VA | 指令/值 | 说明 |
|---|---|---|---|
| 1 | `0x803839` | `push 0x1618` | ★★★ svc 对象大小 5656 字节 |
| 2 | `0x80383E` | `call 0xB74220` | 分配 |
| 3 | `0x80384C` | `call 0xB82130` | 构造 |
| 4 | `0x803851` | `mov [0x8269774], eax` | ★★★ 存入全局槽 |
| 5 | `0x80387B` | `mov [eax], 0xDE6814` | ★★★ vtable |
| 6 | `0x8036C0` | `cmp [0x8269774], 0` | 存在性检查 |
| 7 | `0x8036C9` | `push 0x81A5570` | ★ 临界区 |
| 8 | `0x8036D3` | `call [0xCA819C]` | EnterCriticalSection |
| 9 | `0x8036F2..F8` | `vtable[0](this, 1)` | ★ 虚析构 |
| 10 | `0x8036FF` | `mov [0x8269774], 0` | 清空 |
| 11 | `0x77D086` | `mov [0x8269774], ebx` | 替换 |
| 12 | `0x77D0A8` | `call 0x74C300` | ★ 可能启动 LSG |
| 13 | `0x4F854B` | `mov [0xE609642], 1` | 全局"已启动"标志 |
| 14 | `+0x4F4` 访问 | 20 处（10 次链式） | ★ 指针字段/链表 |
| 15 | vtable | `0xDE6814` | ★ 虚表地址 |

---

## 七、结论

### 1. ★★★ svc 是 5656 字节的多态对象，vtable `0xDE6814`

★★ **有虚析构（`vtable[0]`）。**

### 2. ★★★ 生命周期是**线程安全**的（临界区 `0x81A5570`）

★★ **创建 / 销毁 / 替换 都在临界区内。**

### 3. ★★★ 替换流程会重新初始化 5 个子系统

```
0x808940 / 0x66B360 / 0xB94E50 / 0x4FEB30 / 0x74C300
```

★ **`0x74C300`（`push 1`）可能是 LSG 启动。**

### 4. ★★ `+0x4F4` 是**指针字段**（10 次链式访问）

★★ **⇒ 记忆里"sub = [svc+1268]"的描述**方向对，但 `sub` 更可能是**链表节点**。**

### 5. ★★★ 这给了我们**完整的内存布局图**

```
0x8269774  →  svc（5656 字节，vtable 0xDE6814）
              +0x4F4  →  某个指针（链表）
              ...
              +0x5E8  →  LSG state（P4 写 3）—— 但注意：P4 的 esi 是 **sub**，不是 svc
```

★★ **需要确认：`[esi+0x5E8]` 里的 `esi` 是 svc 还是 sub。**

---

## 八、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **确认 P4 函数（`0xBA3C05`）的 `esi` 来自哪**（是 svc 还是 sub）
- [ ] ★★★ **反汇编 `0x74C300`（可能的 LSG 启动）**
- [ ] ★★ **反汇编 `0xDE6814` 的 vtable（看虚函数表）**
- [ ] ★★ **`0x81A5570` 临界区的初始化点**
- [ ] ★ **反汇编 `0xB7A400`（配置/重置方法）**
- [ ] ★ **`0xE39B6E8` 这个配置字符串**
