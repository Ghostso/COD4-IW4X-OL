# 200 · vtable 尾部合并（COMDAT folding）：`0xDC79E8` 与 `0xDC79F0` 共享函数槽

> 卷次：200（房间类 · vtable 结构最终解释）
> 结论：`0xDC79E8`(`bdSingletonRegistryImpl`) 与 `0xDC79F0`(`MatchMakingInfo`) **共享同一段函数槽**，
> 只是起点差 2 槽。这是 MSVC 的 **COMDAT folding**（相同函数序列合并）。

---

## §0 两个 vtable 并排

```
0xDC79E8 (bdSingletonRegistryImpl)        0xDC79F0 (MatchMakingInfo)
[+0x00] 0x4F3FD0  (dtor)                  [+0x00] 0x806F20   ← 同 0xDC79E8[+0x08]
[+0x04] COL 0xDF84AC (= MMI 的 COL!)      [+0x04] 0x8072A0
[+0x08] 0x806F20   ←─────────────────────[+0x08] COL 0xDF8498
[+0x0C] 0x8072A0                          [+0x0C] 0x806C90
[+0x10] COL 0xDF8498                      [+0x10] 0xB87DA0
[+0x14] 0x806C90                          [+0x14] COL 0xDF8484
[+0x18] 0xB87DA0                          [+0x18] 0x4F4010
[+0x1C] COL 0xDF8484                      [+0x1C] COL 0xDF83F4
[+0x20] 0x4F4010                          [+0x20] 0x4F40B0
[+0x24] COL 0xDF83F4                      [+0x24] 0xB87DA0
[+0x28] 0x4F40B0                          [+0x28] 0x4F40C0
[+0x2C] 0xB87DA0                          [+0x2C] COL 0xDF83E0
[+0x30] 0x4F40C0                          [+0x30] 0x4F40D0
[+0x34] COL 0xDF83E0                      [+0x34] COL 0xDF8388
```

★★★ **`0xDC79E8[+0x08:]` 与 `0xDC79F0[+0x00:]` 完全相同**（12 个槽逐项一致）。

⇒ `0xDC79E8` = `[dtor] [COL]` + `0xDC79F0` 的全部槽

---

## §1 为什么

### 1.1 `0x4F3FD0` 是 `bdSingletonRegistryImpl` 的析构

```asm
0x4F3FD6  mov dword [esi], 0xDC79E8      ; vtable
0x4F3FDC  mov eax, [esi+4] / push / call 0xB74240   ; free(+0x04)
0x4F3FEE  mov dword [esi+4], 0
0x4F3FF1  mov dword [esi+0xC], 0
0x4F3FF4  mov dword [esi+8], 0
0x4F3FFA  call 0xB74240                  ; free(this)
```

★ 只碰 `+0x04`（ptr）/ `+0x08` / `+0x0C` —— 一个 `{ptr,size,cap}` 结构。

### 1.2 COMDAT folding 的解释

MSVC 会把**完全相同的函数指针序列**合并（`/OPT:ICF`）。
`bdSingletonRegistryImpl` 的 vtable 后半段与 `MatchMakingInfo` 的 vtable **完全相同**，
所以链接器让它们**指向同一段内存**，只在前面多加了 2 个槽（`dtor` + `COL`）。

⇒ **`0xDC79E8[+0x08]` 就是 `0xDC79F0[+0x00]` 的物理地址。**

---

## §2 更正 189 卷

| 189 卷说法 | 更正 |
|---|---|
| 「三个 vtable 是同一槽序列的三个起点（`a[3:]==b`）」 | 现象对，但**根因不是"三个接口"**，是 **COMDAT folding** |
| 「每基类接口占 3 槽」 | 实际是**链接器合并的相同函数序列** |

★ `0xDC79FC` = `0xDC79F0 + 0x0C`（跳过 3 槽），`0xDC7A08` = `0xDC79F0 + 0x18`（跳过 6 槽）
—— 同样是折叠产生的偏移视图，**不是三个不同基类**。

### 2.1 那 `+0`/`+4`/`+8` 三个 vtable 指针是什么

从 MMI ctor `0x806B50`：
```asm
0x806B89  mov dword [esi],   0xDC79F0   ; +0x00
0x806B8F  mov dword [esi+8], 0xDC79FC   ; +0x08
0x806B99  mov dword [ecx+esi+4], 0xDC7A08 ; +0x04
```

★ 三个指针，指向**同一段函数序列的三个起点**（0 / +0x0C / +0x18 偏移）。

⇒ **这是多重继承的 vtable 布局**（每个基类子对象一个 vtable），
   **但因为函数实现相同，链接器把它们折叠到了同一段内存。**

★ **两者都对**：是多重继承（三个接口），也是 COMDAT folding（物理合并）。

---

## §3 `0x4F4480` 的最终归属

`0x4F4480` **没有任何 vtable 引用**（data ref 为空），也不在 `0xDC79E8`/`0xDC79F0` 里。

⇒ 它是**内联/静态函数**，被直接 `call`（但 `calls_to` 也是空）。

★★ **`0x4F4480` 可能是死代码，或者被间接调用（通过函数指针表）。**

★ 它操作的字段 `+0x08/+0x10/+0x0C`（元素 4B 数组）和 `+0x18/+0x20/+0x1C`（元素 132B 数组）
与 MMI **完全不重叠** ⇒ **确实不是 MMI**。

---

## §4 本卷确定结论

| 项 | 状态 |
|---|---|
| `0xDC79E8` = `bdSingletonRegistryImpl` | ✅ RTTI |
| **`0xDC79E8[+0x08:] == `0xDC79F0[+0x00:]`** | ✅ 12 槽逐项一致 |
| 根因 = **COMDAT folding** | ✅ 本卷定案 |
| `0x4F3FD0` = `bdSingletonRegistryImpl` 析构 | ✅ |
| `0x4F4480` 无 vtable 引用、无 call ⇒ 死代码/间接调用 | ✅ |
| `0x4F4480` 不是 MMI（字段不重叠） | ✅ 保持 199 卷 |
| MMI 三个 vtable 指针 = 多重继承（物理折叠） | ✅ 189+200 综合 |

---

## §5 方法论

1. **★★★ vtable 相邻且内容重叠 ⇒ 先怀疑 COMDAT folding，不是"多个类"。** RTTI 会给出两个不同的类名，但函数槽是共享的。
2. **★★ `vtable[-4]` 的 COL 是判定"这个 vtable 属于哪个类"的唯一依据。** `0xDC79E8` 的 COL 指向 `bdSingletonRegistryImpl`，尽管它的槽与 MMI 相同。
3. **★★★ 没有 vtable 引用 + 没有 call 的函数 ⇒ 死代码或间接调用。** 不能因为它"看起来像析构"就认定它是。
4. **★★ 字段重叠检查是判定"两个函数是否操作同一个类"的硬标准。** MMI ctor 初始化 `+0x128/+0x1CC`，`0x4F4480` 析构 `+0x08/+0x18` ⇒ 不同类。
