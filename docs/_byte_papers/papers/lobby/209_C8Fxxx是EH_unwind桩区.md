# 209 · `0xC8Fxxx` 全是 EH unwind 桩 —— MSVC 异常表的形态确认

> 卷次：209（房间类 · EH 表形态定案）
> 结论：`0xC8F000-0xC90000` 是一段 **EH unwind 桩密集区**，每个桩 0x30~0x50 字节。

---

## §0 桩的形态

```
0xC8F000  0xC8F050  0xC8F0A0  0xC8F0F0  0xC8F120  0xC8F150
0xC8F1A0  0xC8F1D0  0xC8F210  0xC8F240  0xC8F280  0xC8F2B0
0xC8F310  0xC8F350  0xC8F390  0xC8F3C0  0xC8F450  ...
```

★ **间距 0x30~0x50 字节** —— 典型 unwind 桩大小（`mov ecx,[ebp-X]; add ecx,N; jmp <dtor>` ≈ 10 字节 + int3 填充）。

### 0.1 典型内容

```asm
0xC8FAE0  mov ecx, [ebp-0x10]
0xC8FAE3  add ecx, 8
0xC8FAE6  jmp 0x4F44A0
0xC8FAEB..0xC8FADF  int3 填充
```

★★ **这是 MSVC 的 `_except_handler4` unwind 动作序列。**

---

## §1 结构

```
0xC8Fxxx 区（约 4KB）
  每个桩: [mov ecx,[ebp-X]] [add ecx,N] [jmp <dtor>] [int3 填充]
  作用: 异常展开时按表顺序调用各栈对象的析构
```

★ 真正的业务函数**不在这里**，它们通过 `_except_handler` 的 SEH 链表引用这些桩。

---

## §2 本卷结论

| 项 | 状态 |
|---|---|
| `0xC8F000-0xC90000` = EH unwind 桩密集区 | ✅ |
| 每个桩 0x30~0x50 字节 | ✅ |
| 桩模式 `mov ecx,[ebp-X]; add ecx,N; jmp <dtor>` | ✅ |
| 业务函数不在本区 | ✅ |

---

## §3 对房间类的意义

★★ **本区与房间协议无关** —— 是编译器生成的 EH 元数据。

⇒ **`0x4F44A0`（那个 132B 数组析构）服务于某个"含大栈对象的函数"，
    但那个函数在别处，需要从 SEH 表反查。**

★ 优先级降低：它与房间 blob 无关（208 卷已证）。

---

## §4 下一步（回到房间主线）

`dwRoomMessageStartGame` 的 4 个构造点：
- `0x62FB3E`（func `0x62F840`）
- `0x6327ED`（func `0x632680`）
- `0x63460C`（func `0x634340`）
- `0x634B09`（func `0x634870`）✅ 已查（190 卷）

★ 前两个未查，它们可能是"真正的发送路径"（不是 `clientState==0` 的丢弃路径）。

---

## §5 方法论

1. **★★★ 密集的 `mov ecx,[ebp-X]; add ecx,N; jmp <dtor>` 序列 = MSVC EH unwind 表。** 见到就跳过，不是业务代码。
2. **★★ 桩间距 0x30~0x50 是 EH 表的强指纹。**
3. **★★ 从 EH 表反查业务函数需要读 SEH 链表（`fs:[0]` 链），成本高且与协议无关时不做。**
