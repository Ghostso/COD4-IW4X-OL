# 145 · 断点更正与真根因：`dwLobbyEventHandler+0x4F4` 与野指针

> ⚠️⚠️ **本卷的核心因果链已被 147 卷推翻，引用前必读。**
> **错误根因：`0xB838A0`（消息泵）的 `this` 是 `srpc` 单例，不是 `dwLobbyEventHandler`。**
> - `0xB8392C cmp dword [esi+0x4F4],0` 取的是 **`srpc+0x4F4`**，运行时值 **`0x3ACD38A0`（非 0）**
> - 本卷读的 `0xE39B6E8+0x4F4 = 0` 是 **handler 单例的无关字段**，不是闸门
> - **⇒ 闸门是开的，消息泵正常工作，「房间按钮无反应」的原因不在本条链上**
>
> **本卷仍然成立的部分**：① `0xE39B6E8` 的 RTTI 是 `.?AVdwLobbyEventHandler@@`；
> ② `dwLobbyImp` 这个类不存在；③ 连接建立链 `0xB81FC4 → 0xBA2800` 与 setter `0xB81FFD`。
> **作废部分**：闸门归属、「野指针 ⇒ 闸门关闭」因果链。
> 详见 [147](147_更正145_消息泵的this是srpc闸门是开的.md)。
>
> 前序：144（脱壳成功）、141（服务注册链）、139（五层注册门）
> 性质：**逐指令追踪 + 运行时验证**。本卷**更正 144 卷的一处重大归属错误**，
> 并把断点从 `+0x4F0` 修正为 `+0x4F4`，最终追到野指针。

---

## §0 十二条结论

1. ★★★★★ **144 卷归属错误**：`0xE39B6E8` 的 vtable 是 `0xDE07A4`，
   RTTI 为 **`.?AVdwLobbyEventHandler@@`** —— 它是 **`dwLobbyEventHandler` 单例**，
   **不是 `dwLobbyImp`**。
2. ★★★★★ **`dwLobbyImp` 这个类根本不存在**：全镜像 RTTI 里只有 `dwPartyImp` / `dwRoomImp`，
   没有 `dwLobbyImp`。141/144 卷沿用了这个错名。
3. ★★★★★ **真断点是 `dwLobbyEventHandler+0x4F4`，不是 `+0x4F0`**：
   ```asm
   0xB8392C  cmp dword [esi+0x4F4], 0
   0xB83933  je  0xB83ADE        ; ★ == 0 ⇒ 跳过整个消息分发
   ```
4. ★★★★★ **`+0x4F4` 三个 dump 全部为 0**（`DUMP_194250` / `200456` / `221458`）。
5. ★★★★ **`+0x4F4` 的 setter 是 `0xB81FFD`**，由 `0xB81EF0` 执行，
   唯一调用者是 **`0xB820D3`（连接建立函数 `0xB82070`）**。
6. ★★★★ **连接建立函数的入口参数检查在 `0xB81F42`**：
   ```asm
   0xB81F35  mov esi, [ebp+0x90]
   0xB81F42  test esi, esi
   0xB81F44  jne 0xB81F52        ; 非空才继续
   0xB81F46  call 0x8435D0       ; 失败
   0xB81F4B  xor bl, bl          ; 返回 false
   ```
7. ★★★★ **参数来自 `0x7F38F0 call 0xB9A0E0`**，而 `0xB9A0E0` 只有一条指令：
   ```asm
   0xB9A0E0  lea eax, [ecx + 0x28]
   0xB9A0E3  ret
   ```
   **不做任何有效性校验。**
8. ★★★★★ **`ecx` 来自全局 `[0x84ABB14]`，而该值是野指针**：
   ```
   [0x84ABB08] = 0
   [0x84ABB0C] = 0
   [0x84ABB14] = 0x3AC8B310   ← 野指针
   ```
9. ★★★★★ **`0x3AC8B310` 的内容是垃圾**（不是有效对象）：
   ```
   +0x008 = 0x0776E035   ← 非法地址
   +0x028 = 0xFFE0C1A2   ← 负数
   +0x240 = 0x426E6A63   ← "cj nB" 文本
   ```
   **⇒ 传进连接函数的地址是无效的，`[ebp+0x90]` 虽非 0 但指向垃圾。**
10. ★★★★ **`[0x84ABA7C]`（连接结果标志）= 2**，说明连接函数**跑过了**，
    但返回值被 `setne cl` 记录 —— 而 `+0x4F4` 仍为 0，说明 setter 未成功执行。
11. ★★★ **`[0x76446B0]`（clientState）= 0**（CA_DISCONNECTED），
    与「连接未真正建立」一致。
12. ★★★ **三个 dump 的 `[0x84ABA7C]` 都是 2、`+0x4F4` 都是 0** —— 状态稳定，不是时序问题。

---

## §1 归属更正（本卷最重要）

### 1.1 `0xE39B6E8` 是谁

```
静态：0x7F097F  mov dword [0xE39B6E8], 0xDE07A4
     0xDE07A4 的 RTTI（vt[-1] → COL 0xE081F8 → ti 0xE772C8 → name）
     = .?AVdwLobbyEventHandler@@

运行时：dump 读 [0xE39B6E8+0] = 0x00DE07A4   ✓ 一致
```

**⇒ `0xE39B6E8` = `dwLobbyEventHandler` 单例。**

### 1.2 `dwLobbyImp` 不存在

全镜像 RTTI 里含 `Imp@@` 且与 Lobby/Room/Party 相关的只有：
```
.?AVMyRoomEventHandler@dwPartyImp@@
.?AVMyRoomImp@dwPartyImp@@
.?AVdwPartyImp@@
.?AVdwRoomImp@@
```
**没有 `dwLobbyImp`。** 141/144 卷的命名是错的（可能是从 ol-mod 借来的名字）。

★ 按 AGENTS.md 的权威分级，**ol-mod 不是本 build 的参照**，这个名字不该沿用。

### 1.3 更正后 144 卷的结论

| 144 卷原文 | 145 更正 |
|---|---|
| 「`[dwLobbyImp+0x4F0] = 0` 是断点」 | **断点是 `dwLobbyEventHandler+0x4F4 = 0`** |
| 「`dwLobbyEventHandler` 从未创建」 | **handler 单例存在（`+0x0C=1`），缺的是它内部的连接对象 `+0x4F4`** |
| 「`+0x4F0` 只有 ctor/dtor 两个清零写点」 | 属实，但 `+0x4F0` **不是闸门** |

★ **144 的「对象未创建」方向对，但对象认错了。**

---

## §2 真正的消息泵闸门

```asm
0xB838A0  dwLobbyEventHandler::handleMessage
0xB838C7  mov esi, ecx              ; this
0xB838D7  cmp byte [esi+0x5E8], 0   ; 时间戳闸门
0xB8392C  cmp dword [esi+0x4F4], 0  ; ★★★ 连接对象闸门
0xB83933  je  0xB83ADE              ; == 0 ⇒ 全部跳过
0xB83951  mov ecx, [esi+0x4F4]      ; 用连接对象
```

**`+0x4F4` = 底层连接对象（由 `0xBA2800` 创建）。为 0 ⇒ 消息泵不处理任何消息。**

---

## §3 `+0x4F4` 的完整赋值链

```
0x7F3890  某个上层入口
0x7F38A4  call 0x803830              ; srpc 单例
0x7F38AB  test esi,esi / je 失败
0x7F38B3  movzx eax, word [0x81A9780]
0x7F38BB  push 0xE3EC988             ; 地址串对象
0x7F38C0  call 0xB75370              ; 构造 std::string
0x7F38CB  mov eax, [0x84ABB08]       ; 地址槽 1
0x7F38D0  test eax,eax / jne 0x7F38DD
0x7F38D4  mov eax, [0x84ABB14]       ; 地址槽 2
0x7F38D9  test eax,eax / je 0x7F38F7
0x7F38DD  mov ecx, [0x84ABB0C]       ; 地址槽 3
0x7F38E3  test ecx,ecx / je 0x7F38EE
0x7F38E7  call 0xB983C0              ; 分支 A
0x7F38EE  mov ecx, eax
0x7F38F0  call 0xB9A0E0              ; ★ lea eax,[ecx+0x28]  —— 无校验
0x7F38FB  push eax                   ; → 0xB82070 的 [ebp+0x90]
0x7F3912  call 0xB82070              ; 连接建立
0x7F3919  test al,al / setne cl
0x7F391E  mov [0x84ABA7C], ecx       ; ★ 连接结果标志
```

### 3.1 连接建立函数 `0xB82070`

```asm
0xB82070  ...
0xB82095  mov eax, [ebp+0x90]        ; ★ 参数
0xB8209B  mov esi, ecx               ; this = handler
0xB820C5  mov byte [esi+0x4E8], 1
0xB820D3  call 0xB81EF0              ; → setter
```

### 3.2 setter `0xB81EF0`

```asm
0xB81F35  mov esi, [ebp+0x90]        ; ★ 参数
0xB81F42  test esi, esi
0xB81F44  jne 0xB81F52               ; 非空才继续
0xB81F46  call 0x8435D0              ; 失败
0xB81F4B  xor bl, bl                 ; 返回 false
...
0xB81F7C  push 0xAE8 ; call 0xB74220 ; 分配
0xB81FC4  call 0xBA2800              ; ★ 创建连接对象
0xB81FFD  mov [ebx+0x4F4], esi       ; ★★★ 赋值
0xB8201E  mov byte [ebx+0x4F8], 0
```

---

## §4 野指针证据

```
[0x84ABB08] = 0x00000000
[0x84ABB0C] = 0x00000000
[0x84ABB14] = 0x3AC8B310     ← 唯一非 0
```

`0x3AC8B310` 的内容：

```
+0x000: f8 a1 d5 00   (0x00D5A1F8 —— 看似 vtable)
+0x004: 00 00 00 00
+0x008: 35 e0 76 07   ★ 0x0776E035 —— 非法地址
+0x00C: 0e d3 96 98
+0x010: ea 03 00 00   (1002)
+0x014: 0a 00 00 00   (10)
+0x018: 0b 00 00 00   (11)
+0x028: a2 c1 e0 ff   ★ 0xFFE0C1A2 —— 负数
+0x240: 0x426E6A63    ★ "cj nB" 文本
```

**⇒ 这不是一个构造完整的对象，是已释放/未初始化的堆内存。**

★ `0xB9A0E0` 只做 `lea eax,[ecx+0x28]`，**不校验 `ecx` 是否有效**，
于是把 `0x3AC8B338`（野指针+0x28）传给了连接函数。

---

## §5 因果链（终稿）

```
[0x84ABB14] = 0x3AC8B310  （野指针，内容为垃圾）
  ⇒ 0xB9A0E0 lea eax,[ecx+0x28] = 0x3AC8B338  （无校验）
  ⇒ 0xB82070 / 0xB81EF0 收到无效地址
  ⇒ 0xB81F42 test esi,esi —— 非 0（所以不触发失败分支）
  ⇒ 但后续 0xBA2800 创建连接对象失败 / 或用无效地址初始化失败
  ⇒ dwLobbyEventHandler+0x4F4 保持 0
  ⇒ 0xB8392C cmp [esi+0x4F4],0 / je 0xB83ADE
  ⇒ ★ 消息泵跳过所有 opcode
  ⇒ 0xB7B210 / 0xB7B300 永不调用
  ⇒ 0x6371F0 房间消息处理器永不执行
  ⇒ rec+0x01 永远 0
  ⇒ 三条派发静默跳过
  ⇒ 房间内按钮全部无反应，客户端不报错
```

★ **与用户描述完全吻合。**

---

## §6 诚实边界

1. **`0xBA2800` 创建连接对象时为何失败未逐指令追** —— 只知结果（`+0x4F4 = 0`）。
2. **`[0x84ABB14]` 这个野指针是谁写的、何时释放的未定**。
   三个 dump 都是同一个地址 `0x3AC8B310`，但内容都是垃圾。
3. **`0x7F3890` 这个上层入口的调用者未追**。
4. **dump 时未进房间**（`clientState = 0`、成员数 = 0），
   无法排除"进房间后 `+0x4F4` 会被填上"的可能。
   ★ **但 `[0x84ABA7C]=2` 说明连接函数跑过且返回了值**，与 `+0x4F4=0` 矛盾。

---

## §7 工具

| 工具 | 用途 |
|---|---|
| `tools/s145a_read4f0.py` | 全镜像读 `[reg+0x4F0]` 的点 |
| `tools/s145b_vtslot.py` | `0xDE07A4` 的 64 个槽位 |
| `tools/s145c_fix.py` / `s145d_ident.py` | 单例身份复核（RTTI 反查）|
| `tools/s145e_findimp.py` | 证明 `dwLobbyImp` 不存在 |
| `tools/s145f_handler.py` / `s145g_gate.py` | handler 字段与闸门 |
| `tools/s145h_w4f4.py` / `s145i_setter.py` / `s145j_connect.py` | `+0x4F4` 赋值链 |
| `tools/s145k_flag.py` / `s145l_param.py` | 全局标志与野指针验证 |

## §8 方法论

1. ★★★★★ **类名要拿 RTTI 验，不能沿用外部项目的命名** ——
   `dwLobbyImp` 不存在，是我从 ol-mod 语境带进来的错名。
2. ★★★★ **"对象未创建"要先确认是哪个对象** —— 144 认错了对象。
3. ★★★★ **闸门要读的是 `cmp` 那一条，不是相邻字段** —— `+0x4F0` 与 `+0x4F4` 只差 4 字节。
4. ★★★ **"非 0"不等于"有效"** —— 野指针也非 0，`test esi,esi` 挡不住。
5. ★★★ **dump 内容要按结构读**：`0x3AC8B310` 的 `+0x240` 是 `"cj nB"` 文本，
   一眼就能看出不是对象。
