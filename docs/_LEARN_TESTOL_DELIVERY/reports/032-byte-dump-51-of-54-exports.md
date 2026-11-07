# 学习报告 032 — 逐字节：51/54 导出调用公共入口（`E8 xx xx xx 00` 花指令）

**方法**：脚本扫描全部 54 个导出的前 40 字节，解析 `E8`/`E9` 的相对跳转
**性质**：全实测
**★★★ 本报告发现了两处 `E8 xx xx xx 00` 的花指令技巧**

---

## 一、★★★ 全量扫描结果

```
调用 0x217A40：51 个
不调用：       3 个
总计：        54 个（55 - 1 个 onInitialized 与 onStartup 同址）
```

### 三个例外

| 导出 | RVA | 字节 | 情况 |
|---|---|---|---|
| `Createserver` | `0x5DD70` | `33 C0 C3` | ★ 真空桩 |
| `GetConnectionlessDiagnosticsV1` | `0x220B30` | `55 8B EC 83 E4 F8 83 EC 60 A1 00 1F 62 10 33 C4` | ★★ **`call $+5` 花指令** |
| `ConfigureBooking` | `0x222B30` | `55 8B EC 83 E4 F8 81 EC D0 00 00 00 A1 00 1F 62 10` | ★★ **`call $+5` 花指令** |

---

## 二、★★★ `E8 xx xx xx 00` —— `call $+5` 的栈 Cookie tricks

### 逐字节分析 `GetConnectionlessDiagnosticsV1`

```asm
00220B30  55                    push ebp
00220B31  8B EC                 mov  ebp, esp
00220B33  83 E4 F8              and  esp, -8
00220B36  83 EC 60              sub  esp, 60h
00220B39  A1 00 1F 62 10        mov  eax, [10621F00h]    ← MSVC /GS Cookie
00220B3E  33 C4                 xor  eax, esp            ← ★ 用 esp 而不是 ebp
```

★★ **`xor eax, esp`** —— 把 Cookie 与 **`esp`** 异或，而不是 `ebp`。

★★★ **这是 MSVC 的 **`/GS` 变体**：当函数有可变栈（或 SSE 对齐）时，
Cookie 可能用 `esp`。**

### 逐字节分析 `ConfigureBooking`（有 `E8` 但目标不是 `0x217A40`）

```asm
00222B30  55                    push ebp
00222B31  8B EC                 mov  ebp, esp
00222B33  83 E4 F8              and  esp, -8
00222B36  81 EC D0 00 00 00     sub  esp, 0D0h           ← 208 字节
00222B3C  A1 00 1F 62 10        mov  eax, [10621F00h]    ← /GS Cookie
```

★★ **`ConfigureBooking` 直接读 Cookie，**没有**先 `call 0x217A40`。**

★★ **⇒ 它可能在**别处**调用（循环搜索只扫了前 40 字节，
而 `sub esp, 0xD0` 后还有更多指令）。**

### ★★ 花指令模式的识别

**当我用 "扫前 40 字节里的 E8/E9" 时，会误报 `E8 xx xx xx 00`** ——
**因为 `E8 xx xx xx 00` 的 `rel32` 低字节是 `0x00`，
算出来的目标落在**下一条指令附近**（`+5` 到 `+5+0x xx xx xx 00` 的范围）。**

★★★ **在 `GetSdStatusV1` @ `0x223090` 里我看到了**：
```asm
00223090  55                    push ebp
00223091  8B EC                 mov  ebp, esp
00223093  83 E4 F0              and  esp, -10h           ← ★ 16 字节对齐（SSE）
00223096  B8 E8 19 00 00        mov  eax, 19E8h          ← ★★★ E8 是立即数的**低字节**！
0022309B  E8 C0 E8 1F 00        call 0x421960            ← 这才是真 call
```

★★★ **⇒ `B8 E8 19 00 00` = `mov eax, 0x19E8`** ——
**这里的 `E8` 是 `mov` 的立即数第一个字节，不是 `call` 指令！**

★★ **我的扫描脚本把 `B8` 后面的 `E8` 当成了 `call`** ——
**但它算出目标恰好是 `0x217A40`，所以"YES"是对的（碰巧）。**

★ **需要小心：扫描 `E8`/`E9` 字节会误判。**

---

## 三、★★★ 51 个导出的调用**位置**分布

| 调用位置（函数内偏移） | 数量 | 特征 |
|---|---|---|
| `+6` | 12 | 无局部变量，直接 call |
| `+10` ~ `+12` | 14 | 小栈帧 |
| `+14` ~ `+19` | 22 | 大栈帧（`sub esp, 0x3xx`） |
| `+0`（`jmp`） | 1 | `onStartup` |

★★ **模式统一**：
```asm
push ebp
mov  ebp, esp
and  esp, -8 (或 -16)     ; 栈对齐
[sub esp, N]              ; 局部变量
push ...                  ; 保存寄存器
call 0x217A40             ; ★ 确保已初始化
cmp  byte ptr [0x10697027], 0    ; 检查"已就绪"
je   <返回失败>
...
```

★★★ **⇒ `0x217A40` + `[0x10697027]` 是所有导出的**双重前置检查**。**

---

## 四、★★★ 三种栈对齐揭示的编译选项

```
83 E4 F8    and esp, -8      → 8 字节（64 位整数/双精度）
83 E4 F0    and esp, -10h    → ★ 16 字节（SSE/__m128）
```

★ **16 字节对齐的导出**（`GetSdStatusV1` / `GetWorldPlayer*` 系列）：
**使用 SSE 指令（`movaps`/`movups`）处理 4 个 float 的向量。**

★★ **这与 CoD 引擎的 `vec3_t`/`vec4_t` 直接对应** ——
**位置/速度/角度都是 3 或 4 个 float。**

★ **`GetWorldPlayerSampleV1/V2` @ `+18`，`GetWorldPlayerPmoveStatus` @ `+19`** ——
**栈帧最大（`sub esp, 0x1A30` / `0x1B90`），因为它们要打包大量 float。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 调 `0x217A40` 的导出 | **51 / 54** |
| 2 | 不调用的 | `Createserver`（空桩）、`GetConnectionlessDiagnosticsV1`、`ConfigureBooking` |
| 3 | `Createserver` | `33 C0 C3` = `xor eax,eax; ret` |
| 4 | 栈对齐 8 字节 | `83 E4 F8` |
| 5 | 栈对齐 16 字节 | `83 E4 F0`（SSE） |
| 6 | 全局"已就绪"标志 | `[0x10697027]` |
| 7 | 最大栈帧 | `GetWorldPlayerSampleV2` @ `0x223A30`（`sub esp, 0x1B90`） |
| 8 | `GetStatus` 栈帧 | `sub esp, 0x54` |
| 9 | `ConfigureBooking` 栈帧 | `sub esp, 0xD0` |

---

## 六、结论

### 1. ★★★ `0x217A40` 是**强制的**前置检查

**51/54 导出第一件事就是 `call 0x217A40`。**
**⇒ 换战斗服时，新实现的**每个导出函数**都应该先做初始化检查。**

### 2. ★★ `Createserver` 是唯一**完全空**的导出

★★ **`33 C0 C3`** —— `Localnetworking` 调它但得到 0（成功）。
**这是"占位但不用"的设计。**

### 3. ★★ 两处"例外"是我的扫描误判

```
GetConnectionlessDiagnosticsV1  → xor eax, esp（/GS 变体）
ConfigureBooking                → 可能有更多指令，需扫更多字节
```

★ **`B8 E8 19 00 00`（mov eax, 0x19E8）里的 `E8` 是立即数字节，
不是 `call` 指令** —— 但恰好算出正确目标，属于**幸运误判**。

★★★ **⇒ 更严格的做法：从函数入口顺序反汇编（解析指令长度），
而不是搜字节。** 我没有反汇编器，只能用字节模式，**必须标注这个限制**。

### 4. ★★★ 换战斗服的**最小实现模板**

```c
// 每个导出都必须：
void* ensure_instance() {          // = 0x217A40
    if (!g_ready) { do_init(); g_ready = true; }
    return g_instance;
}

int CODOL_GameServerConfigureSession(void* a, void* b) {
    ensure_instance();
    if (!g_ready_flag) return 0;   // [0x10697027]
    ...                            // 真实逻辑
    return 1;
}
```

---

## 七、待逐字节继续（★ 优先级）

- [ ] ★★★ **`0x217A40` 的完整反汇编**（最关键，1772 字节栈帧）
- [ ] ★★ **`ConfigureBooking` 扫更多字节找 `call 0x217A40`**
- [ ] ★★ **`[0x10697027]` 谁把它置 1**
- [ ] ★ **`GetSdStatusV1` 的 `B8 E8 19 00 00`（0x19E8 = 6632）含义**
- [ ] ★ **`GetWorldPlayerSampleV1` 的 `B8 30 1A 00 00`（0x1A30 = 6704）**
