# 学习报告 046 — capstone：`0x4F7940` 全局状态写 + P4 完整函数

**方法**：capstone 反汇编 `0x4F7940` / `0xBA3C05` / `0xB783C0`
**性质**：权威反汇编
**★★★ 本报告锁定了 LSG 状态的**全局唯一落点** `0x82CA530`**

---

## 一、★★★ `0x4F7940` —— **9 字节的全局状态写**

```asm
004F7940  55              push ebp
004F7941  8bec            mov  ebp, esp
004F7943  8b4508          mov  eax, [ebp + 8]        ← 参数
004F7946  a330a52c08      mov  [0x82CA530], eax      ← ★★★ 全局写！
004F794B  5d              pop  ebp
004F794C  c3              ret
```

★★★ **`0x4F7940(int state)` = `g_lsg_state = state;`**

★★ **只有 4 条有效指令 —— 极简。**

### ★★★ `0x82CA530` 是**唯一的 LSG 状态全局**

★★ **P4 的两条路径都调它**：
```
失败路径 A（0xBA3BE0）: push 4  → call 0x4F7940   ⇒ g_lsg_state = 4
失败路径 B（0xBA3C69）: push 3  → call 0x4F7940   ⇒ g_lsg_state = 3
成功路径（0xBA3C47）:    mov [esi+0x5E8], 3      ⇒ 对象字段 = 3
```

★★★ **⇒ **两个不同的状态变量**：**
```
0x82CA530       全局（通过 0x4F7940 写）
[esi + 0x5E8]   对象字段（直接写）
```

★★ **P4 的 `eax == 0` 路径**只写对象字段（`0x5E8`），**不写全局**。**
**P4 的两条 `eax != 0` 路径**写全局（3 或 4），**不写对象字段**（在 `0xBA3C62` 后直接 jmp 到 `0xBA3BE2`，跳过 `0xBA3C38`）。**

★★★ **⇒ `mov [esi+0x5E8], 3` 是**记忆里的 `5E8=3`**，**
**而 `0x82CA530` 是**另一个**全局。**

---

## 二、★★★ P4 的完整函数（`0xBA3C05` 起）

```asm
00BA3C05  6a08            push 8
00BA3C07  8d55f4          lea  edx, [ebp - 0xc]
00BA3C0A  52              push edx
00BA3C0B  8d86fc050000    lea  eax, [esi + 0x5fc]      ← ★ esi + 0x5FC
00BA3C11  50              push eax
00BA3C12  e8c903fdff      call 0xB73FE0                ← ★ 读/处理 8 字节
00BA3C17  83c40c          add  esp, 0xc
00BA3C1A  85c0            test eax, eax
00BA3C1C  7544            jne  0xBA3C62                ← ★★ P4 补丁点
00BA3C1E  8d5801          lea  ebx, [eax + 1]          ← ebx = 1
00BA3C21  398644060000    cmp  [esi + 0x644], eax
00BA3C27  750f            jne  0xBA3C38
00BA3C29  8b8e40060000    mov  ecx, [esi + 0x640]
00BA3C2F  51              push ecx
00BA3C30  e89bf9c9ff      call 0x8435D0
00BA3C35  83c404          add  esp, 4
00BA3C38  8b4dfc          mov  ecx, [ebp - 4]
00BA3C3B  899eec050000    mov  [esi + 0x5EC], ebx
00BA3C41  899ef0050000    mov  [esi + 0x5F0], ebx
00BA3C47  c786e805000003000000  mov dword ptr [esi + 0x5E8], 3
00BA3C51  5e              pop  esi
00BA3C52  8ac3            mov  al, bl                  ← ★ 返回 ebx（1 或 0）
00BA3C54  33cd            xor  ecx, ebp
00BA3C56  5b              pop  ebx
00BA3C57  e8b3850900      call 0xC3C20F               ← /GS 检查
00BA3C5C  8be5            mov  esp, ebp
00BA3C5E  5d              pop  ebp
00BA3C5F  c20c00          ret  0xC                    ← ★ stdcall，3 参数
```

### ★★★ 关键结构

```c
int func(void* a, void* b, void* c) {      // ret 0xC = 3 参数
    // 0xBA3C05: 读 [esi+0x5FC] 的 8 字节到 [ebp-0xC]
    char buf[8];
    int r = sub_0xB73FE0(&buf[0], [esi+0x5FC], 8);

    if (r != 0) {                          // ← ★ P4 补丁在这里
        // 失败路径 B
        bl = 0;
        sub_0x8435D0();
        g_lsg_state = 3;                   // call 0x4F7940(3)
        // 跳到 0xBA3BE2（同一提交点）
        return 0;
    }
    // 成功路径
    bl = 1;
    [esi+0x5EC] = 1;
    [esi+0x5F0] = 1;
    [esi+0x5E8] = 3;                       // ★★★ 对象字段 = 3
    return 1;
}
```

★★★ **⇒ P4 补丁（NOP 掉 `jne`）后**：
```c
    // if (r != 0) 被 NOP 掉 ⇒ 永远走成功路径
    bl = 1;
    [esi+0x5EC] = 1;
    [esi+0x5F0] = 1;
    [esi+0x5E8] = 3;
    return 1;
```

★ **⇒ **函数恒返回 1，且对象字段全部正确设置。**

★★ **但**全局 `0x82CA530` 不再被写**（原本失败路径会写 3）。**

**★ 这是一个副作用差异，可能影响其他代码（如果有代码读 `0x82CA530`）。**

---

## 三、★★★ `0xBA3C05` 前的逻辑（`0xBA3BC0` 已见）

```asm
00BA3BC0  lea  edx, [ebp - 0x10]
00BA3BC3  push edx
00BA3BC4  push ecx
00BA3BC5  mov  [ebp - 0x10], ecx
00BA3BC8  mov  ecx, [ebp + 0x10]
00BA3BCB  push ecx
00BA3BCC  push eax
00BA3BCD  call 0xB783C0                ← ★ 前置检查
00BA3BD2  add  esp, 0x18
00BA3BD5  test al, al
00BA3BD7  jne  0xBA3C05                ← 成功 → 进入主逻辑
--- 失败 ---
00BA3BD9  xor  bl, bl
00BA3BDB  call 0x8435D0
00BA3BE0  push 4                        ← ★ 全局状态 = 4
00BA3BE2  call 0x4F7940
```

★★ **⇒ 完整三层**：
```
层 1：0xB783C0（前置检查）  → 失败则 g_state = 4
层 2：0xBA3C05 主逻辑       → [esi+0x5FC] 的 8 字节处理
      ├─ 失败（r != 0）    → g_state = 3，返回 0
      └─ 成功（r == 0）    → 对象字段 = 3，返回 1
```

---

## 四、★★★ `0xB783C0` —— 一个边界检查函数

```asm
00B783C0  55              push ebp
00B783C1  8bec            mov  ebp, esp
00B783C3  837d1800        cmp  [ebp + 0x18], 0     ← 参数 5 == 0?
00B783C7  8b5510          mov  edx, [ebp + 0x10]   ← 参数 3
00B783CA  56              push esi
00B783CB  8b7514          mov  esi, [ebp + 0x14]   ← 参数 4
00B783CE  57              push edi
00B783CF  8b7d1c          mov  edi, [ebp + 0x1c]   ← 参数 6
00B783D2  8d0c3a          lea  ecx, [edx + edi]    ← ecx = p3 + p6
00B783D5  b001            mov  al, 1               ← ★ 默认真
00B783D7  890e            mov  [esi], ecx          ← ★ *p4 = p3 + p6
00B783D9  7444            je   0xB7841F            ← p5 == 0 → 返回真
00B783DB  837d0800        cmp  [ebp + 8], 0        ← 参数 1 == 0?
00B783DF  743e            je   0xB7841F            ← p1 == 0 → 返回真
00B783E1  8b750c          mov  esi, [ebp + 0xc]    ← 参数 2
00B783E4  3bd6            cmp  edx, esi            ← p3 vs p2
00B783E6  53              push ebx
00B783E7  0f96c3          setbe bl                 ← bl = (p3 <= p2)
00B783EA  3bce            cmp  ecx, esi            ← (p3+p6) vs p2
00B783EC  0f96c0          setbe al                 ← al = (p3+p6 <= p2)
00B783EF  84c0            test al, al
00B783F1  7510            jne  0xB78403
00B783F3  57              push edi
00B783F4  e8d7b1ccff      call 0x8435D0            ← 越界处理
00B783F9  83c404          add  esp, 4
00B783FC  5b              pop  ebx
00B783FD  5f              pop  edi
00B783FE  32c0            xor  al, al              ← ★ 返回假
```

★★★ **⇒ `0xB783C0(p1, p2, p3, p4, p5, p6)` 是**范围检查**：**
```c
bool range_check(void* p1, size_t p2, size_t p3, size_t* p4, size_t p5, size_t p6) {
    size_t end = p3 + p6;
    *p4 = end;
    if (p5 == 0) return true;
    if (p1 == 0) return true;
    if (end > p2) return false;      // ★ 越界
    return (p3 <= p2);
}
```

★★ **这是 `std::span` / `MemRange` 的边界检查。**

★ **6 个参数（`cmp [ebp+0x18]` = 参数 5，`[ebp+0x1c]` = 参数 6）。**

---

## 五、逐字节证据总表

| # | VA | 指令 | 说明 |
|---|---|---|---|
| 1 | `0x4F7940` | `mov [0x82CA530], eax` | ★★★ 全局 LSG 状态写 |
| 2 | `0x4F7940` 长度 | **9 字节**（`55 8bec 8b4508 a3… 5d c3`） | 极简 setter |
| 3 | `0xBA3C05` | `push 8` / `lea [esi+0x5FC]` | 读 8 字节字段 |
| 4 | `0xBA3C12` | `call 0xB73FE0` | 处理函数 |
| 5 | `0xBA3C1C` | `jne 0xBA3C62` | ★ P4 补丁点 |
| 6 | `0xBA3C47` | `mov [esi+0x5E8], 3` | ★★★ 对象字段 state = 3 |
| 7 | `0xBA3C5F` | `ret 0xC` | stdcall，3 参数 |
| 8 | `0xBA3BE0` | `push 4` | 全局状态 4（前置检查失败） |
| 9 | `0xBA3C69` | `push 3` | 全局状态 3（主逻辑失败） |
| 10 | `0xB783C0` | 6 参数范围检查 | `bool range_check(...)` |
| 11 | `0xB783FE` | `xor al,al` | 越界返回假 |

---

## 六、结论

### 1. ★★★ `0x82CA530` 是全局 LSG 状态（唯一的全局）

★★ **`0x4F7940` 是 9 字节的 setter。**

★★★ **⇒ 这个地址**不在**记忆里的链条（`0x08269774` → `+1268` → `+1512`）里，
是**另一个独立的全局**。**

★ **需要确认它和记忆里的 `state` 是不是同一个语义。**

### 2. ★★★ 两个状态变量必须分清

```
0x82CA530        全局（setter 写）
[esi + 0x5E8]    对象字段（直接写）
```

★★ **P4 成功路径只写对象字段，不写全局。**
★★ **P4 失败路径写全局（3 或 4），不写对象字段。**

★★★ **⇒ 补丁改变了**哪个变量被更新**。**

### 3. ★★★ P4 补丁后函数恒返回 1

★★ **且对象字段（`5EC` / `5F0` / `5E8`）全部正确。**

★ **代价：全局 `0x82CA530` 不再被更新。**

### 4. ★★ `0xB783C0` 是通用的范围检查（`std::span` 风格）

---

## 七、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **找出所有读 `0x82CA530` 的地方**（决定副作用影响）
- [ ] ★★★ **确认 `0x82CA530` 与记忆里 `[sub+0x5E8]` 的关系**
- [ ] ★★ **反汇编 `0xB73FE0`（读 8 字节字段的处理）**
- [ ] ★★ **`[esi+0x5FC]` / `[esi+0x640]` / `[esi+0x644]` 的语义**
- [ ] ★ **`0x8435D0`（错误处理/日志）**
- [ ] ★ **验证我们的固化链是否写 `0x82CA530`**
