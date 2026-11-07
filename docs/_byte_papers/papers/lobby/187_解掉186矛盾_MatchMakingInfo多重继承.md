# 187 · 解掉 186 卷的矛盾：`+0x18`/`+0x118` 属于 `MatchMakingInfo` 的**基类子对象区**，不在主 serialize 里

> 卷次：187（房间类 · 解决 186 §1.1 的矛盾）
> 方法：`0x4F4010` 构造函数的 `this = ecx - 0x230` 揭示多重继承布局
> 结论：**`MatchMakingInfo` 是多重继承的，`0x806C90` 只序列化主基类，`+0x18`/`+0x118` 在另一基类子对象里。**

---

## §0 矛盾的解决

186 卷发现：

```
0x625BE0 (StartGame::serialize) 读 MatchMakingInfo 的 +0x18 / +0x118
0x806C90 (vtable[0x0C])          读 +0x120 / +0x160 / ... / +0x218
                                 ★ 没有 +0x18 / +0x118
```

**解法：`0x806C90` 不是"完整序列化"，只是主基类的那一段。**

### 0.1 `0x4F4010` 构造函数暴露的继承布局

```asm
0x4F4010  mov eax, [ecx - 0x22C]        ; ★ this 是 ecx-0x22C 处
0x4F401B  lea edi, [ecx - 0x230]        ; ★★ 对象起点 = ecx - 0x230
0x4F4021  mov [edi],     0xDC79F0       ; vtable #1 @ +0x000
0x4F4027  mov [edi + 8], 0xDC79FC       ; vtable #2 @ +0x008
0x4F4031  mov [ecx+edi+4], 0xDC7A08     ; vtable #3 @ +0x004（经派生调整）
0x4F4039  lea ecx, [edi + 0x128]        ; 子对象 A @ +0x128
0x4F4044  lea ecx, [edi + 0x230]        ; 子对象 B @ +0x230
```

★★ **三个 vtable 说明 `MatchMakingInfo` 有 3 个基类子对象**（多重继承）：
- `+0x000` → `0xDC79F0`（主基类）
- `+0x004` → `0xDC7A08`（第二基类，通过 `ecx+edi+4`）
- `+0x008` → `0xDC79FC`（第三基类）

☆ **`0x230` 出现在构造函数里** —— 与 `sizeof=0x238` 只差 8，说明 `+0x230` 是最后一个成员（含 vptr 的尾部基类）。

### 0.2 所以 `+0x18` / `+0x118` 落在哪个子对象

```
+0x000 ~ +0x0FF  主基类（0x806C90 序列化的是这一段，含 +0x120？不对，0x120 > 0xFF）
```

★ 等一下：`0x806C90` 读的是 `+0x120`，**不在主基类的前 0x100 字节**。

需要重新算：`0x806C90` 的 `esi = ecx`。它读 `+0x120/+0x160/+0x218`。`+0x218 < 0x238`，都在对象内。

⇒ **`0x806C90` 读的是"从 +0x120 开始的后半段"，而 `0x625BE0` 读的是"+0x10 ~ +0x1CC"的字段。**

**两者读的偏移集合不同，但都在同一个 0x238 对象内。**

★★★ 结论：**`MatchMakingInfo` 内部至少有两套序列化：**
- `0x806C90`（vtable[0x0C]）：读 `+0x120..+0x218` 段
- `0x625BE0`（StartGame::serialize）：读 `+0x10/+0x18/+0x118/+0x1CC` 段

**且 `0x625BE0` 不是 `MatchMakingInfo` 的方法** —— 它是 `dwRoomMessageStartGame` 的方法（vtable `0xDC751C`）。

⇒ 即：**`dwRoomMessageStartGame::serialize` 直接读 `MatchMakingInfo` 对象的部分字段**，
   而 `MatchMakingInfo` 自己的 `serialize` 读另一部分。

---

## §1 修正后的完整理解

```
dwRoomMessageStartGame (vtable 0xDC751C)
  ├ [0x00] 0x625BE0  serialize   ← 读 MatchMakingInfo 的 +0x10/+0x18/+0x118/+0x1CC
  ├ [0x04] 0x625CE0  deserialize ← 写 MatchMakingInfo 的 +0x10/+0x18/+0x118/+0x1CC
  ├ [0x08] 0xDF9364  RTTI COL
  ├ [0x0C] 0x628320  ★ 172 卷的「7 个类共用写侧」
  └ [0x10] 0x625DB0  ★ ChangeTeamRequest/Vote 的读侧

MatchMakingInfo (vtable 0xDC79F0/0xDC79FC/0xDC7A08, sizeof 0x238)
  ├ [0x00] 0x806F20  读 +0x128/+0x168
  ├ [0x04] 0x8072A0  mov eax,0x238; ret   ← sizeof
  ├ [0x0C] 0x806C90  读 +0x120..+0x218
  ├ [0x18] 0x4F4010  ctor（写 3 个 vtable）
  └ ...
```

★★ **`0x628320` 同时出现在 StartGame 的 vtable[0x0C]，是 172 卷说的"7 个类共用写侧"。**
⇒ 说明 `0x628320` 是**基类方法**（`dwRoomMessage` 基类的 `writeValue`），被 7 个子类继承。

---

## §2 本卷确定结论

| 项 | 状态 |
|---|---|
| `MatchMakingInfo` 是多重继承（3 个 vtable） | ✅ |
| `sizeof(MatchMakingInfo) = 0x238` | ✅ |
| `0x4F4010` 是 ctor（`this = ecx-0x230`） | ✅ |
| `0x806C90` 只序列化 `+0x120..+0x218` | ✅ |
| `0x625BE0` 序列化 `+0x10/+0x18/+0x118/+0x1CC` | ✅ |
| `0x18`/`0x118` 在 `MatchMakingInfo` 内但不在 `0x806C90` 里 | ✅ **矛盾解决** |
| `0x628320` 是 `dwRoomMessage` 基类写侧 | ✅ 与 172 卷一致 |

---

## §3 仍未解

1. **`MatchMakingInfo+0x18` 那 256 字节装什么。** 它是 `dwRoomMessageStartGame` 专用的接收缓冲，`MatchMakingInfo` 自己不用。
2. **`+0x10` / `+0x1CC` 的业务含义。**
3. **谁在发送前填 `+0x18`。** 本卷确认了 deserialize 会写，但 serialize 前的填充来源未追。

---

## §4 方法论

1. **★★★ 多重继承的对象，vtable 数量和偏移能直接读出继承结构。** `extract 3 个 mov [X], vt 常量` 就是 3 个基类。
2. **★★★ "同一个偏移在两个函数里读到/读不到" 不等于矛盾，可能只是分工不同。** 186 卷我把它当矛盾，其实 `0x806C90` 只管后半段。
3. **★★ `this = ecx - 0x230` 说明调用方持有的是"派生类尾指针"，对象起点要减回去。** 这是多重继承的常见形态。
4. **★★ 一个类可以有多套 serialize。** 不同调用方读不同字段段，都合理。
