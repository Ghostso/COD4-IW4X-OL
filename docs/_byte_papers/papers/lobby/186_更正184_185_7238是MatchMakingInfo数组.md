# 186 · ★★★ 更正 184/185：`+0x7238` 是 `MatchMakingInfo[49]` **数组的最后一个元素**，不是单个对象

> 卷次：186（**第三次更正卷** —— 推翻 184/185 的"单个内嵌对象"结论）
> 方法：读到循环体 `dec [ebp+8] / jns`，看到步进 `0x238` 与初值 `0x31=49`
> 结论：`dwRoomImp + 0x7238` = **`MatchMakingInfo` 数组的最后 1 个元素**（共 49 个）。

---

## §0 真相

```asm
0x637D8D  mov dword ptr [ebp+8], 0x31      ; ★ 循环计数 49
0x637D94  lea esi, [ebx + 0x7238]          ; 起始 = 最后一个元素
0x637DA0  mov edx, [esi - 0x23C]           ; (下一元素+4 的字段)
0x637DA6  sub esi, 0x238                   ; ★ 步进 0x238 往前
0x637DAC  mov [esi - 8], 0xDC79F0          ; vtable#1
0x637DB3  mov [esi],     0xDC79FC          ; vtable#2
0x637DBC  lea ecx, [esi + 0x120]
0x637DC2  mov [eax+esi-4], 0xDC7A08        ; vtable#3
0x637DCA  call 0xB95AA0                    ; 构造 [+0x120]
0x637DCF  lea ecx, [esi + 0x228]
0x637DD5  call 0xB757E0                    ; 构造 [+0x228]
0x637DDA  dec dword ptr [ebp+8]
0x637DDD  jns 0x637DA0                     ; ★ 循环 49 次
```

★★ **这是一个 49 元素的 `MatchMakingInfo` 数组**，每个 `0x238` 字节，总长 `49 × 0x238 = 0x6C98 = 27800` 字节。
数组末尾恰好在 `ebx + 0x7238`，所以数组起点 = `ebx + 0x7238 - 48*0x238 = ebx + 0x7238 - 0x6A80 = ebx + 0x7B8`。

### 0.1 三个 vtable 都是 `MatchMakingInfo`

```
vt 0xDC79F0 -> .?AVMatchMakingInfo@@
vt 0xDC79FC -> .?AVMatchMakingInfo@@
vt 0xDC7A08 -> .?AVMatchMakingInfo@@
```

**三重继承的三个基类子对象**（`+0` / `+8` / `+4 经派生调整`）。

### 0.2 `v[0x04] = 0x8072A0` 返回 `0x238`

```asm
0x8072A0  mov eax, 0x238
0x8072A5  ret
```

★ **`sizeof(MatchMakingInfo) = 0x238`** —— 与循环步进完全吻合。这是**独立第二证据**。

---

## §1 更正 184/185 的什么

| 卷 | 原说法 | 更正 |
|---|---|---|
| 184 | 「`[this+8]` = `dwRoomImp+0x7238` 的**内嵌结构**」 | 是**数组的最后一个元素** |
| 184 | 「`+0x10/+0x18/+0x118/+0x1CC` 是结构字段」 | 是**元素内偏移**，不是结构基址后的固定字段 |
| 185 | 「`+0x7238` = `MatchMakingInfo` 实例」 | 是 `MatchMakingInfo[49]` 的**末元素**，类名没错，但"单实例"错 |
| 185 | 「三段 blob 全部来自 MatchMakingInfo」 | ★ **仍存疑** —— `0x806C90` 里没有 `+0x18`/`+0x118` |

### 1.1 关键矛盾（未解）

```
0x625BE0 (serialize) 读 [子对象+0x18] / [子对象+0x118]
0x806C90 (MMI 读写) 读 [+0x120] [+0x160] [+0x164] [+0x168] [+0x1a8..+0x218]
                     ★ 没有 +0x18 / +0x118
```

★★ **所以 `[this+8]`（`0x625BE0` 的子对象）不是 `MatchMakingInfo`。**

⇒ `0x634B0D mov [ebp-0xc90], edi`（`edi=ebx+0x7238`）**可能不是**给 `[this+8]` 赋值。

需要一个更精确的读法：`[ebp-0xc98]` 是消息对象起点，`+8` = `[ebp-0xc90]`。
但栈布局 `vtable(+0) / type(+4) / sub(+8)` 是我从 `0x634B00..0x634B13` 推断的，**未逐字节验证**。

---

## §2 本卷确定结论

| 项 | 状态 |
|---|---|
| `dwRoomImp+0x7238` = `MatchMakingInfo[49]` 末元素 | ✅ **RTTI + 循环 + sizeof 三重证据** |
| `sizeof(MatchMakingInfo) = 0x238 = 568` | ✅ `0x8072A0` 直证 |
| 数组总长 `49 × 0x238 = 27800` 字节 | ✅ |
| 数组起点 ≈ `dwRoomImp+0x7B8` | ✅ 推算 |
| `StartGame` 的 `[this+8]` 是否 = 该末元素 | ⬜ **存疑（§1.1 矛盾）** |

---

## §3 为什么这个矛盾重要

★★★ 如果 `[this+8]` **不是** `MatchMakingInfo`，那 183/184/185 三卷关于"第 1 段 blob 来源"的链条就要重来。

**但 182/183 卷的"三段容量 255/8/16"结论不受影响** —— 那是从 `0x625CE0` 读出的，与 `[this+8]` 是什么类无关。

⇒ **下一步必须精确确定 `0x634B00..0x634B2B` 的栈布局。**

---

## §4 方法论

1. **★★★ `lea reg,[base+big_disp]` 后面若有 `sub reg, stride` 循环 ⇒ 那是数组。** 单个对象不会有倒序步进。
2. **★★ `v[+4] mov eax, imm; ret` 通常是 `sizeof`。** 拿到它就直接得到结构大小，可校验步进。
3. **★★ 多个 vtable 指向同一 RTTI ⇒ 多重继承的基类子对象。**
4. **★★★ 链条上的每一环都要独立验证，不能靠"看起来对"接下去。** 185 卷我说"三段 blob 都来自 MatchMakingInfo"，被 `0x806C90` 缺 `+0x18` 直接推翻。
