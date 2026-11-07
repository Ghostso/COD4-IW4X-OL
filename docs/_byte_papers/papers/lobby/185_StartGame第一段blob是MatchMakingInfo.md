# 185 · `StartGame` 第 1 段 blob = **`MatchMakingInfo`**（RTTI 铁证）

> 卷次：185（房间类 · 184 卷追问的答案，链条闭合）
> 方法：`0x637D55 mov [ebx+0x7238], 0xDC79F0` → RTTI 点名
> 结论：`dwRoomImp + 0x7238` **就是 `MatchMakingInfo` 对象**。第 1 段 blob 是它的 `+0x18` 缓冲。

---

## §0 RTTI 直证

```
vtable 0x00DC79F0
  COL              = 0x00DF84AC
  TypeDescriptor   = 0x00E6EEF0
  name             = ".?AVMatchMakingInfo@@"
```

**⇒ `dwRoomImp + 0x7238` = `MatchMakingInfo` 实例。**

### 0.1 初始化点

```asm
0x637D55  mov dword ptr [ebx + 0x7238], 0xDC79F0   ; ★ 设 vtable
0x637D94  lea esi, [ebx + 0x7238]                  ; ★ 取地址继续初始化
```

`0x637C00` 是该整套结构的初始化函数（同时初始化 `+0x3a098` 队列、`+0x106xx` 若干缓冲、`+0xe368` 等）。

### 0.2 与之呼应的已知事实

★★ 记忆条目 `codol-myhandler-never-created-root-cause` 曾记录：

> **`dwRoomMatchUber` 从未创建**

而本卷定案：`dwRoomImp+0x7238` = **`MatchMakingInfo`**（不是 `dwRoomMatchUber`）。
两者是**不同的类**。⇒ 此前把"MatchMakingInfo 存在"误当成"MatchMaking 可用"是一个坑。

---

## §1 完整链条（182 → 183 → 184 → 185）

```
StartGame::serialize (0x625BE0)
  └─ [this+8] = dwRoomImp + 0x7238      ← 184 卷
       └─ 该对象的类 = MatchMakingInfo   ← ★ 本卷
            ├─ +0x18   → blob#1 数据（256 容量）
            ├─ +0x118  → blob#1 实际长度
            ├─ +0x10   → blob#2 数据（u64）
            └─ +0x1CC  → blob#3 数据（128 位）
```

★★ **三段 blob 全部是 `MatchMakingInfo` 里的字段切片。**

---

## §2 `MatchMakingInfo` 的 vtable 槽

| 槽 | 地址 | 备注 |
|---|---|---|
| `+0x00` | `0x806F20` | |
| `+0x04` | `0x8072A0` | |
| `+0x0C` | `0x806C90` | |
| `+0x10` | `0xB87DA0` | |
| `+0x18` | `0x4F4010` | |
| `+0x20` | `0x4F40B0` | |
| `+0x24` | `0xB87DA0` | 与 +0x10 同 |
| `+0x28` | `0x4F40C0` | |

★ 与 `0x4F3Exx`/`0x4F40xx` 同一段（`0x4F3EB0` = blob 读取器就在这条链附近）⇒ **`MatchMakingInfo` 的读写函数族在 `0x4F40xx`**。

---

## §3 对我们的实现意味着什么

`build_startgame_payload` 现在写：

```python
w.write_blob(addr_67)   # 67 字节 bdCommonAddr
```

**应该是**：从 `MatchMakingInfo` 的 `+0x18` 缓冲（256 容量）里取 `+0x118` 字节。

★★★ **服务端没有 `MatchMakingInfo` 对象** —— 那个对象只存在于**客户端进程内存**里。

⇒ **服务端无法"抄"这个字段，只能自己构造一个合理的 `MatchMakingInfo` 序列化块。**

⇒ **这就是房间类最硬的黑箱：** 这个块的内容完全由客户端的 matchmaking 子系统在运行时填充，服务端只能猜。

---

## §4 本卷结论

| 项 | 状态 |
|---|---|
| `dwRoomImp+0x7238` 的类 | ✅ **`MatchMakingInfo`**（RTTI 铁证） |
| 三段 blob 的归属 | ✅ 全部是 `MatchMakingInfo` 字段 |
| 字段偏移 `+0x10/+0x18/+0x118/+0x1CC` | ✅ 定案 |
| `MatchMakingInfo` 的 vtable | ✅ 全表 |
| **`+0x18` 缓冲该装什么** | ⬜ **客户端运行时填充，服务端无法静态确定** |

---

## §5 诚实边界（这次是硬边界）

1. **`MatchMakingInfo+0x18` 的 256 字节内容，本卷仍未解。** 它是运行时由客户端 matchmaking 子系统填充的。
2. **但这不等于"无法分析"：** 可以继续追 `MatchMakingInfo` 的成员函数（`0x806C90`/`0x806F20`/`0x8072A0`），看谁写 `+0x18`。
3. **`dwRoomMatchUber` 与 `MatchMakingInfo` 是两个类**，此前记忆里可能混淆。

---

## §6 方法论

1. **★★★ vtable 初始化点（`mov [X], <常量>`）是识别"未命名结构"的最快入口。** 一旦拿到 vtable，RTTI 直接给类名。
2. **★★ `lea reg,[base+disp]` 且该 disp 处被写过 vtable ⇒ 那是内嵌对象，不是裸结构。**
3. **★★ 服务端与客户端的内存对象不可互换。** 客户端 `MatchMakingInfo` 的字段值只能"猜一个合理值"，不能"读出来"。
4. **★★ 记忆条目要定期与新证据对账。** 本次发现 `dwRoomMatchUber` ≠ `MatchMakingInfo`。
