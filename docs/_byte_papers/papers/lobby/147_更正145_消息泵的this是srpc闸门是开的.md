# 147 · 更正 145：`0xB838A0` 的 `this` 是 srpc，闸门是开的

> 前序：146（真脱壳）、145（断点更正）、144（运行时验证）
> 性质：**用脱壳 PE 做的完整调用者分析**。本卷**推翻 145 卷的核心结论**。

---

## §0 九条结论

1. ★★★★★ **145 卷的核心结论作废**：`0xB838A0` 的 `this` 是 **srpc 单例**，不是 `dwLobbyEventHandler`。
2. ★★★★★ **闸门 `[esi+0x4F4]` 指的是 `srpc+0x4F4`，运行时值 `0x3ACD38A0`（非 0）**
   ⇒ **闸门是开的，消息泵正常工作**。
3. ★★★★★ **145 卷读的 `0xE39B6E8+0x4F4 = 0` 是 handler 单例的字段，不是闸门** —— 读错了对象。
4. ★★★★★ **`0xB838A0` 三个调用者形态完全一致**（`push 0x81A5570` 加锁 → `ecx = srpc` → `call` → 解锁），
   全部传 `ecx = srpc`。
5. ★★★★★ **新发现连接状态机 `0x7F3800`**：
   ```
   [0x84ABA7C] == 0 → 0x7F386B → call 0x7F3890（建立连接）
   [0x84ABA7C] == 1 → call 0xB838A0（消息泵）→ 按 srpc 状态跳表更新状态
   [0x84ABA7C] == 2 → 直接返回
   ```
6. ★★★★ **状态机的 5 项跳转表**（`0x7F3878`）按 srpc 状态分派：
   `0/3/4 → 写 0`；`1 → 保持`；**`2 → 写 2`**。
7. ★★★★ **`srpc+0x4F4 = 0x3ACD38A0`，其 vtable `0xD5A4F4` = `0xBA2800` 创建的对象**，
   而 `0xBA2800` 唯一调用者是 `0xB81FC4`（在 setter `0xB81EF0` 内）。
8. ★★★★ **连接建立链完整**：`0x7F3912 → 0xB82070 → 0xB820D3 → 0xB81EF0 → 0xB81FC4 → 0xBA2800`，
   唯一路径，无分支。
9. ★★★ **`[0x84ABA7C] = 2`**（三个 dump 一致）⇒ **连接已建立**。

---

## §1 ★★★★★ 更正：`0xB838A0` 的 this

### 1.1 三个调用者（脱壳 PE 全量搜索）

| 调用点 | 形态 |
|---|---|
| `0x4A648C` | `push 0x81A5570` / `call [0xCA819C]` / `mov ecx,esi` / `call 0xB838A0` / `call [0xCA8190]` |
| `0x7F3826` | 同上 |
| `0x8037B8` | 同上 |

**三处的 `esi` 都来自 `call 0x803830`（srpc 单例 getter）。**

```asm
0x4A646C  push esi
0x4A646F  xor edi, edi
0x4A6473  call 0x803830       ; ★ esi = srpc
0x4A6478  mov esi, eax
...
0x4A647C  call 0xB838A0
```

### 1.2 闸门字段的运行时值

```
srpc = 0x3AC89CB8
srpc+0x4F0 = 0x0E39B6E8   （dwLobbyEventHandler 单例）
srpc+0x4F4 = 0x3ACD38A0   ★★ 非 0！
srpc+0x4F8 = 0x00000001
srpc+0x5E8 = 0x00000001

handler+0x4F0 = 0
handler+0x4F4 = 0          ← 145 卷读的是这个
```

**⇒ `0xB8392C cmp dword [esi+0x4F4],0 / je` 取的是 `srpc+0x4F4`，值为 `0x3ACD38A0`，不为 0。**

**★ 145 卷「闸门关闭 ⇒ 消息泵跳过所有 opcode」的因果链完全不成立。**

### 1.3 `0x3ACD38A0` 的身份

```
0x3ACD38A0 + 0x00 = 0x00D5A4F4   ← vtable
0x3ACD38A0 + 0x04 = 0x00000002
0x3ACD38A0 + 0x08 = 0x0200007F
```

而 `0xBA2800`（连接对象工厂）构造时：
```asm
0xBA2844  mov dword [esi], 0xD5A4F4    ; ★ vtable 一致
```

**⇒ `srpc+0x4F4` 指向的正是 `0xBA2800` 创建的对象。**

---

## §2 ★★★★★ 新发现：连接状态机 `0x7F3800`

```asm
0x7F3800  mov eax, [0x84ABA7C]      ; ★ 状态变量
0x7F3805  sub eax, 0
0x7F3809  je  0x7F386B              ; == 0 → 建立连接
0x7F380B  dec eax
0x7F380C  jne 0x7F3870              ; != 1 → 直接返回
                                    ; == 1 → 驱动消息泵
0x7F380E  call 0x803830
0x7F3813  mov esi, eax
0x7F3819  push 0x81A5570
0x7F381E  call [0xCA819C]           ; 加锁
0x7F3826  call 0xB838A0             ; ★★★ 消息泵
0x7F3830  call [0xCA8190]           ; 解锁
0x7F3838  call 0xB7A670             ; srpc 状态
0x7F383D  cmp eax, 4
0x7F3840  ja  0x7F3870
0x7F3842  jmp [eax*4 + 0x7F3878]    ; ★ 5 项跳转表
```

### 2.1 跳转表 `0x7F3878`

| srpc 状态 | 目标 | 动作 |
|---|---|---|
| 0 | `0x7F3849` | `mov [0x84ABA7C], 0` |
| 1 | `0x7F3870` | 读取返回（保持不变）|
| **2** | **`0x7F385A`** | **`mov [0x84ABA7C], 2`** |
| 3 | `0x7F3849` | `mov [0x84ABA7C], 0` |
| 4 | `0x7F3849` | `mov [0x84ABA7C], 0` |

### 2.2 语义

```
[0x84ABA7C] = 0  未连接   → 调 0x7F3890 尝试建立
[0x84ABA7C] = 1  连接中   → 驱动消息泵，按 srpc 状态决定升到 2 还是回退 0
[0x84ABA7C] = 2  已连接   → 不再驱动
```

★ **状态 2 时不再驱动消息泵** —— 那消息泵由另外两个调用者（`0x4A648C` / `0x8037B8`）驱动。

### 2.3 dump 实测

```
[0x84ABA7C] = 2   （三个 dump 一致）
```

**⇒ 连接已建立。**

---

## §3 连接建立链（唯一路径）

```
0x7F3912  call 0xB82070      ← 唯一调用者
0xB82070  连接建立函数
0xB820C5  mov byte [esi+0x4E8], 1
0xB820D3  call 0xB81EF0      ← 唯一调用者
0xB81EF0  参数校验 + 分配
0xB81F42  test esi,esi / jne  ← 参数非空才继续
0xB81FC4  call 0xBA2800      ← 唯一调用者
0xBA2800  构造连接对象（vtable 0xD5A4F4）
0xB81FFD  mov [ebx+0x4F4], esi   ★ 挂到 srpc+0x4F4
```

**★ 这条链没有分支，全部单调用者 ⇒ 一旦跑到就必然成功。**

---

## §4 145 卷哪些成立、哪些作废

| 145 卷结论 | 状态 |
|---|---|
| `0xE39B6E8` 的 vtable `0xDE07A4` RTTI 是 `.?AVdwLobbyEventHandler@@` | ✅ **成立** |
| `dwLobbyImp` 这个类不存在 | ✅ **成立** |
| `+0x4F4` 的 setter 是 `0xB81FFD` | ✅ **成立** |
| 连接建立链 `0xB82070 → 0xB81EF0 → 0xBA2800` | ✅ **成立** |
| **`0xB838A0` 的闸门 = `dwLobbyEventHandler+0x4F4 = 0`** | ❌ **作废**（应为 `srpc+0x4F4 = 0x3ACD38A0`）|
| **「野指针 ⇒ 闸门关闭 ⇒ 房间按钮无反应」因果链** | ❌ **作废** |
| **`[0x84ABB14]` 是野指针**（`0x3AC8B310` / `0x397D4FD0`）| ⚠️ **待复核**（见 §5）|

---

## §5 未解决的问题

1. **`[0x84ABB14]` 到底是不是野指针？**
   - 145 卷据 `DUMP_221458` 读 `0x3AC8B310`，判为垃圾
   - 146 卷据 `DUMP_194250` 读 `0x397D4FD0`，未复核内容
   - **需要重新读那个地址的内容才能定论**
2. **既然连接已建立、闸门开着，房间按钮为什么还无反应？**
   —— **dump 时 `clientState = 0`、房间未建立**，无法验证房间内行为。
3. **消息泵（srpc 方法）与 `dwLobbyEventHandler`（`srpc+0x4F0`）的分工未明**。

---

## §6 诚实边界

1. **本卷的唯一硬证据是「srpc+0x4F4 = 0x3ACD38A0 ≠ 0」**（三个 dump 一致）+
   三个调用者的 `ecx` 来源。
2. **未做「进房间后」的 dump**，因此**无法回答用户的实际问题**。
3. **`0xB838A0` 的完整函数体（含 76 项 opcode 表）未逐条重读** ——
   145 卷引用的 `0xB8392C cmp [esi+0x4F4]` 位置正确，只是 `esi` 的对象认错了。

---

## §7 工具

| 工具 | 用途 |
|---|---|
| `tools/s147a_xref.py` / `s147b_write.py` | 全局变量的引用/写点扫描 |
| `tools/s147c_jt.py` | 状态机跳转表解码 |
| `tools/s147d_verify.py` | srpc 与 handler 字段对比（**关键证据**）|
| `tools/s147e_srpcvt.py` | srpc vtable 与 RTTI |
| `tools/s147f_callers.py` / `s147g_fix.py` | 调用者搜索（**修正了 file offset / VA 混用**）|
| `tools/s147h_ctx.py` | 三个调用者的上下文比对 |

## §8 方法论

1. ★★★★★ **`this` 的身份决定字段归属** —— `mov ecx,esi` 而 `esi = call 0x803830` ⇒ this 是 srpc。
2. ★★★★★ **同名偏移（`+0x4F4`）在不同对象上含义不同** —— 必须先确定对象。
3. ★★★★ **call 目标的计算必须用指令 VA，不能用 file offset** ——
   `target = VA + 5 + rel32`，用 file offset 会得到 0 命中。
4. ★★★ **"全部调用者形态一致"是强证据**：三个调用点都是 `push 锁 / ecx=esi / call`。
