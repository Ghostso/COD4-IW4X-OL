# 208 · `0x4F44A0` 是栈对象的析构 —— 被 MSVC 异常展开（EH）代码调用

> 卷次：208（房间类 · `0x4F44A0` 归属最终定案）
> 结论：`0x4F44A0` **零数据引用**是因为它由 **MSVC 的 EH unwind 桩**通过 `jmp` 调用。

---

## §0 四处 `jmp 0x4F44A0` 的模式

### 0.1 `0xC8FAE0`

```asm
0xC8FAE0  mov ecx, [ebp-0x10]      ; 取栈对象指针
0xC8FAE3  add ecx, 8                ; ★ +8（析构第二子对象）
0xC8FAE6  jmp 0x4F44A0              ; 析构
```

### 0.2 `0xC8FB30` —— 完全相同的模式

```asm
0xC8FB30  mov ecx, [ebp-0x10]
0xC8FB33  add ecx, 8
0xC8FB36  jmp 0x4F44A0
```

### 0.3 `0xC8FC40` —— 栈对象直接析构

```asm
0xC8FC40  lea ecx, [ebp-0x984]      ; ★ 栈上局部对象
0xC8FC46  jmp 0x4F44A0
0xC8FC4B  lea ecx, [ebp-0x984]      ; 另一个 unwind 状态
0xC8FC51  jmp 0x4F44A0
0xC8FC56  lea ecx, [ebp-0x7EC]
0xC8FC5C  jmp 0xB76E50              ; 写 0xDEADBEEF
```

### 0.4 相邻的其它 unwind 桩

```asm
0xC8FAAE  add ecx, 0x18 / jmp 0x643280
0xC8FAB9  add ecx, 0x24 / jmp 0x4F4480   ; = jmp 0xB76E50
0xC8FAEE  add ecx, 0x1A0 / ...
```

★★★ **这是 MSVC 的 `_except_handler3` unwind 动作表**：
每个栈对象在作用域退出/异常展开时，由一张"地址 → 析构桩"表驱动。

---

## §1 这意味着什么

| 事实 | 解释 |
|---|---|
| `0x4F44A0` 零数据引用 | ✅ 它只在 **unwind 表**里（`0xC8Fxxx` 是 EH 代码段） |
| `0x4F44A0` 有 4 个 `jmp` | ✅ 4 个不同的 unwind 状态需要析构 |
| `0x4F4480` = `jmp 0xB76E50` | ✅ 它是"把子对象打成 0xDEADBEEF"的 unwind 桩 |

⇒ **`0x4F44A0` 是一个栈对象的析构函数**，该对象在 `0xC8FC40` 所在函数的栈上（`ebp-0x984`，约 2.4KB）。

---

## §2 那个对象是什么

从析构内容：
- 数组 A：`+0x18`(ptr)/`+0x20`(size)/`+0x1C`(cap)，元素 **132 字节**
- 数组 B：`+0x08`/`+0x10`/`+0x0C`，元素 **4 字节**
- 子对象 `+0x24`、`+0xD8`

★ 对象大小 > `0xD8 + 4 = 0xDC`，且是**栈对象**（`ebp-0x984` 起）。

⇒ **约 2.4KB 的栈上临时对象，含两个动态数组。**

候选：
- 房间列表快照（132B × N）
- matchmaking 查询结果集

★ **元素 132 字节** 是关键指纹。

---

## §3 本卷确定结论

| 项 | 状态 |
|---|---|
| `0x4F44A0` 零数据引用 | ✅ 因为在 EH unwind 表里 |
| `0xC8FAE0/FB30/FC40` = EH unwind 桩 | ✅ |
| `0x4F44A0` = 栈对象析构 | ✅ |
| `0x4F4480` = `jmp 0xB76E50`（0xDEADBEEF 桩） | ✅ |
| 该对象含 132B/4B 两个数组 + `+0x24`/`+0xD8` 子对象 | ✅ |
| 该对象的类名 | ⬜ 待定（栈对象，无 vtable） |

---

## §4 与房间类的关系

★ **这个类是"栈上临时对象"，不是 MMI/房间的持久成员。**

⇒ **它与 `dwRoomMessageStartGame` 的 blob 无关**（那些是 MMI 成员）。

★★ **本卷彻底排除 `0x4F44A0` 与房间 blob 的关系。**

---

## §5 方法论

1. **★★★★★ "零数据引用"的函数，先查 EH unwind 表。** MSVC 的 `_except_handler` 用 `jmp` 调析构桩，不产生数据引用。
2. **★★★ `mov ecx,[ebp-X]; add ecx,N; jmp <dtor>` 是标准 unwind 桩模式。**
3. **★★ 同一区域出现多个 `jmp <同一个 dtor>` ⇒ 是 unwind 表的多个状态，不是多次调用。**
4. **★★ 栈对象（`lea ecx,[ebp-X]`）无 vtable，靠 EH 表管理生命周期。**
