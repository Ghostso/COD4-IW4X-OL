# 学习报告 053 — capstone：三个写入点全是**构造函数**，读点是 **LSG 消息处理**

**方法**：反汇编 `0x6E1226` / `0x6F42DB` / `0xBA2964` / `0xBA44E8` 的上下文
**性质**：权威反汇编
**★★★ 本报告揭示了 `0x5E8` 所在字段簇的**完整布局**与**三种构造形态**

---

## 一、★★★ 三个写入点全是**批量字段初始化**

### 写入点 A：`0x6E1226`（`edi=0`? `ebx=?`）

```asm
006E1228  mov dword ptr [esi + 0x5C4], ebx
006E122E  mov dword ptr [esi + 0x5C8], edi
006E1234  mov dword ptr [esi + 0x5CC], edi
006E123A  mov dword ptr [esi + 0x5E0], ebx
006E1240  mov dword ptr [esi + 0x5E4], ebx
006E1246  mov dword ptr [esi + 0x5E8], edi    ← ★ 目标
006E124C  mov dword ptr [esi + 0x5EC], edi
006E1252  mov dword ptr [esi + 0x600], ebx
006E1258  mov dword ptr [esi + 0x604], ebx
006E125E  mov dword ptr [esi + 0x608], edi
006E1264  mov dword ptr [esi + 0x60C], edi
006E126A  pop edi
006E126B  mov eax, esi
006E126D  pop ebx
006E1271  ret
```

★★ **`ret`（无参数）+ `mov eax, esi`（返回 this）** ——
**这是**构造函数**的标准形态。**

*★★ **`ebx` 与 `edi` 交替使用（`ebx` / `edi` / `edi` / `ebx` / `ebx` / `edi`...）** ——
**两种不同的初值，可能是 `0` 和 `-1`（`0xFFFFFFFF`）。***

### 写入点 B：`0x6F42DB`

```asm
006F42DD  mov dword ptr [esi + 0x590], ecx
006F42E3  mov dword ptr [esi + 0x5D8], edi
006F42E9  mov dword ptr [esi + 0x5DC], edi
006F42EF  mov dword ptr [esi + 0x5E0], edi
006F42F5  mov dword ptr [esi + 0x5E4], edi
006F42FB  mov dword ptr [esi + 0x5E8], ebx    ← ★ 目标
006F4301  mov dword ptr [esi + 0x5EC], ebx
006F4307  mov byte ptr  [esi + 0x600], bl
006F430D  lea eax, [esi + 0x5FC]
006F4313  mov dword ptr [esi + 0x604], eax    ← ★ 存自己字段的地址！
006F4319  mov dword ptr [esi + 0x608], eax
006F431F  mov dword ptr [esi + 0x5D0], ecx
006F4325  mov dword ptr [esi + 0x618], edi
...
006F4349  mov byte ptr  [esi + 0x640], bl
006F434F  lea eax, [esi + 0x63C]
006F4355  mov dword ptr [esi + 0x644], eax    ← ★ 同样存自己字段地址
```

★★★ **关键**：
```
[esi + 0x604] = &  [esi + 0x5FC]     ← 自引用！
[esi + 0x608] = &  [esi + 0x5FC]     ← 同一地址
[esi + 0x644] = &  [esi + 0x63C]     ← 另一个自引用
```

★★★ **⇒ `+0x604` / `+0x608` 是**指向 `+0x5FC` 的指针**，
`+0x644` 是**指向 `+0x63C` 的指针**。**

★★ **这是 C++ **`std::string` / `std::vector` 的 SSO（小字符串优化）** 或
**`std::span` / `std::string_view` 的初始化**。**

★★★ **⇒ `[esi+0x5FC]` 起是一个 **0xC 字节（12）的缓冲区**
（`+0x5FC..0x608`），被 `+604`/`+608` 自引用。**
**`[esi+0x63C]` 起是另一个（`+0x63C..0x644`）。**

### 写入点 C：`0xBA2964`（★ 与 P4 同族）

```asm
00BA2966  mov dword ptr [esi + 0x5C4], eax
00BA296C  mov dword ptr [esi + 0x5C8], eax
00BA2972  mov dword ptr [esi + 0x5CC], eax
00BA2978  mov dword ptr [esi + 0x5D0], eax
00BA297E  mov dword ptr [esi + 0x5D4], eax
00BA2984  mov dword ptr [esi + 0x5E8], ebx    ← ★ 目标
00BA298A  mov dword ptr [esi + 0x604], ebx
00BA2990  mov dword ptr [esi + 0x608], ebx
00BA2996  mov dword ptr [esi + 0x640], ebx
00BA299C  mov dword ptr [esi + 0x644], ebx
00BA29A2  lea ecx, [ebp + 8]
00BA29A5  push ecx
00BA29A6  lea ecx, [esi + 0x648]
00BA29AC  call 0xB75340                       ← ★ 构造 +0x648 的子对象
00BA29B1  mov dword ptr [esi + 0x6D0], ebx
...
00BA29C3  fld dword ptr [0xDBE6CC]            ← ★ float 常量
00BA29CA  fstp dword ptr [esi + 0xAE0]        ← ★★ 写到 +0xAE0（超出 0x648）
00BA29D0  lea ecx, [esi + 0xC4]
```

★★★ **⇒ 这是**P4 对象的构造函数**（同一 `0xBAxxxx` 族）。**

★★ **`+0xAE0` 远超过 `0x648`，`+0x6D8`，证实对象**远大于 1608 字节**。**
（与 svc 的 `0x1618` = 5656 匹配）。

---

## 二、★★★ `0x5E8` 所在字段簇的完整布局（累计实测）

```
+0x590    ← 0x6F42DD 写 (ecx)
+0x5B4    ← 0xB7A410 返回
+0x5C4    ← 0x6E1228 / 0xBA2966
+0x5C8    ← 0x6E122E / 0xBA296C
+0x5CC    ← 0x6E1234 / 0xBA2972
+0x5D0    ← 0x6F431F / 0xBA2978
+0x5D4    ← 0xBA297E
+0x5D8    ← 0x6F42E3
+0x5DC    ← 0x6F42E9
+0x5E0    ← 0x6E123A / 0x6F42EF
+0x5E4    ← 0x6E1240 / 0x6F42F5
+0x5E8    ★★★ LSG state
+0x5EC    ← 0x6E124C / 0x6F4301 / P4
+0x5F0    ← P4
+0x5FC    ★ 12 字节缓冲（被 +604/+608 自引用）
+0x600    ← byte
+0x604    ★ = &+0x5FC
+0x608    ★ = &+0x5FC
+0x60C    ← 0x6E1264
+0x618 / 0x61C / 0x620 / 0x624  ← 0x6F4325..
+0x628 / 0x62C  ← 0x6F433D..
+0x63C    ★ 另一个 12 字节缓冲
+0x640    ← byte（0x6F4349 / 0xBA2996）
+0x644    ★ = &+0x63C（或 0xBA299C 清 0）
+0x648    子对象（0xBA29A6 构造）
+0x6D0 / 0x6D4 / 0x6D8
+0xAE0    ← float（0xBA29CA）
```

★★★ **⇒ 这是一组**密集的 LSG 协议字段**（总共约 0x5A0 = 1440 字节）。**

---

## 三、★★★ `0xBA44E8` —— **LSG 消息处理**（读点）

```asm
00BA44D8  call 0xB765A0                   ← 收包/解包
00BA44DD  add  esp, 0x14
00BA44E0  test al, al
00BA44E2  je   0xBA4799                   ← 失败 → 返回
00BA44E8  mov  eax, [esi + 0x5E8]         ← ★ 读 state
00BA44EE  cmp  eax, 1                     ← ★★ state == 1?
00BA44F1  jne  0xBA454B                   ← 不是 → 另一分支
00BA44F3  mov  al, [ebp - 0xe]            ← 消息类型
00BA44F6  cmp  al, 0x81                   ← ★★★ 0x81！
00BA44F8  jne  0xBA450C
00BA44FA  mov  edx, [ebp - 0x14]
00BA44FD  push edi
```

★★★ **`cmp al, 0x81`** ——
**这正是报告 012 的 `buildHeaderAck` 里那个 `0x81`（header ACK 类型）！**

★★★ **⇒ `0xBA44E8` 是**LSG 消息分派器**，按 `state` 和**消息类型**分流。**

### ★★ 完整状态机（结合所有证据）

```
state = 0  →  未连接（清理后）
state = 1  →  ★ 握手中（等 0x81 header ACK）
state = 3  →  ★ 已连接（P4 写）
```

★★★ **⇒ 记忆里的 `5E8=3` = "已连接"完全吻合。**

★ **而 `state == 1` 时处理 `0x81` 消息** ——
**这是 LSG 握手的第一步。**

---

## 四、逐字节证据总表

| # | 地址 | 内容 | 说明 |
|---|---|---|---|
| 1 | `0x6E1228..0x6E1264` | 批量字段初始化 | ★ 构造函数 A |
| 2 | `0x6F42DD..0x6F4355` | 批量 + 自引用 | ★★ 构造函数 B |
| 3 | `0xBA2966..0xBA29CA` | 批量 + 子对象 + float | ★★★ 构造函数 C（P4 族） |
| 4 | `0x6F4313` | `mov [+0x604], &[+0x5FC]` | ★ 自引用 |
| 5 | `0x6F4355` | `mov [+0x644], &[+0x63C]` | ★ 自引用 |
| 6 | `0xBA44EE` | `cmp eax, 1` | ★ state == 1 |
| 7 | `0xBA44F6` | `cmp al, 0x81` | ★★★ header ACK 类型 |
| 8 | `0xDBE6CC` | float 常量 | 构造参数 |
| 9 | `+0xAE0` | float 字段 | 对象 ≥ 2784 字节 |

---

## 五、结论

### 1. ★★★ 三个写入点都是**构造函数**，不是运行时状态转移

★★★ **⇒ `0x5E8` 的 5 个写入点里，3 个是构造（初值），2 个是运行时（0 / 3）。**

★★ **⇒ **真正改变状态**的只有 2 处**：
```
0xBA3460  → 0（清理）
0xBA3C47  → 3（P4 成功）
```

★ **这是极简的状态机。**

### 2. ★★★ `0xBA44E8` 是 LSG 消息分派器（`0x81` 类型）

★★★ **⇒ 与 `nt10.py` / `LobbyProtocol.cpp` 的 `0x81` header ACK 一致。**

★ **`state == 1` 是"等 header ACK"阶段。**

### 3. ★★★ 完整的状态语义

```
0 = 未连接
1 = 握手中（等 0x81）
3 = 已连接
```

★★ **（缺 2 —— 可能是"认证中"或从未使用）**

### 4. ★★ 对象远大于 1608 字节（字段到 `+0xAE0`）

★ **与 svc 的 5656 字节吻合。**

### 5. ★★ 有**自引用指针**（`+0x604`/`+0x608` → `+0x5FC`）

★★ **⇒ 是 `std::string`/`std::vector` 的 SSO 缓冲区。**

---

## 六、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **反汇编 `0xBA454B`（`state != 1` 分支）和 `0xBA450C`（非 0x81 消息）**
- [ ] ★★★ **找写 `state = 1` 的地方**（我的扫描没找到！只有 0 和 3）
- [ ] ★★ **反汇编 `0xB765A0`（收包函数）**
- [ ] ★★ **`0xDBE6CC` 的 float 值**
- [ ] ★ **反汇编 `0x6E1226` 和 `0x6F42DB` 的完整函数（找函数入口）**
- [ ] ★ **`0x5FC` 缓冲的实际用法**
