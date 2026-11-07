# 190 · `0x634B0D` 路径可达性定案 + 发现第四条 StartGame 构造路径是 `StartGameFailed`

> 卷次：190（房间类 · 189 卷疑问的答案 + 新发现）
> 结论：`[0x76446B0]==0` 只在 `0x77C343` 一处被写 0，`0x634B0D` 路径**可达但时机极窄**；且 `0x634C3C` 那段是 **`StartGameFailed`（`0xDC7528`）**，不是 StartGame。

---

## §0 `[0x76446B0]`（clientState）的 5 个写点

| 地址 | 写入值 | 含义 |
|---|---|---|
| `0x470467` | **3** | |
| `0x5BE90A` | **7** | |
| `0x5BEA8B` | **4** | |
| `0x77C343` | **0** | ★ **唯一写 0 处** |
| `0x813D34` | **7** | |

★ 与记忆条目 `codol-lobby-battle-handoff-138` 一致：「`[0x76446B0]` = clientState(CA_*)，开局闸门 <3」。

⇒ `cmp dword [0x76446B0], 0 / jne` 只有在 `0x77C343` 执行过之后才为真。

### 0.1 结论

`0x634B0D`（把 `ebx+0x7238` 挂到消息对象 `+8`）**可达，但只在 clientState 刚被重置为 0 的窗口内**。

★★ 这解释了为什么这条路径"看起来像正常转发"却从未在日志里出现：
**它只在"未连接/刚重置"时跑，此时根本收不到 StartGame。**

---

## §1 ★ 新发现：`0x634C3C` 是 `StartGameFailed`，不是 StartGame

```asm
0x634C3C  lea eax, [ebp+0x1c] / push
0x634C40  lea ecx, [ebp-0xbf0]           ; 栈上临时对象
0x634C46  mov dword [ebp-0xbec], 4       ; +4 = type 4
0x634C50  mov dword [ebp-0xbf0], 0xDC7528 ; ★★★ vtable = StartGameFailed!
0x634C5A  mov dword [ebp-0xbe8], 0
0x634C64  call 0x625DB0                  ; ★ 通用的 [tag/len] 读器
```

★ `0xDC7528` = `dwRoomMessageStartGameFailed`（172 卷全表）。

⇒ **`0x634C29` 分支（clientState != 0 时）构造的是 `StartGameFailed`，不是 `StartGame`。**

### 1.1 这修正了什么

189 卷我以为两条路径都是 StartGame。实际：

| 路径 | 条件 | 构造的类 | vtable |
|---|---|---|---|
| `0x634B0D` | `clientState == 0` | `StartGame` | `0xDC751C` |
| `0x634C3C` | `clientState != 0` | **`StartGameFailed`** | **`0xDC7528`** |

★★★ **逻辑完全合理**：客户端在**未连接**时收到 StartGame 会回 `StartGameFailed`（拒绝）；
连接正常时才真正处理 StartGame。

⇒ **`0x634B0D` 那条路（`clientState==0`）是"拒绝路径"的前置**，不是正常转发！

---

## §2 修正后的正确理解

```
0x634870 (Manifold 分发)
  └ case StartGame:
      if clientState == 0:                 ← 未连接
          构造 StartGame 消息对象（vtable 0xDC751C, +8 = ebx+0x7238）
          call 0x625CE0 (deserialize)      ← 解析一下（可能只为跳过）
          ...
      else:                                ← 已连接
          构造 StartGameFailed（vtable 0xDC7528, type=4）
          call 0x625DB0 (通用读器)
```

★★ **`0x625CE0` 在 `clientState==0` 时被调，只是为了"消费掉这段位流"** ——
它写进 `+0x18`/`+0x118` 的那些值，**随后就被丢弃，因为不连接就没房间**。

---

## §3 对本轮修复的意义

| 项 | 影响 |
|---|---|
| `build_startgame_payload` 的第 1 段该装什么 | ★ **仍然未知，但优先级下降** —— 客户端在"未连接"时即使解析了也不使用 |
| 服务端推送 StartGame 的意义 | ⚠️ **客户端可能一律回 StartGameFailed**，除非 clientState 已 ≥3 |
| `srpc+0x4F4` 闸门（173 卷） | ★★ **与本卷结论一致**：clientState 与 HMAC 会话是两道独立门 |

---

## §4 本卷确定结论

| 项 | 状态 |
|---|---|
| `[0x76446B0]` 5 个写点（3/7/4/**0**/7） | ✅ |
| `0x634B0D` 路径只在 `clientState==0` 可达 | ✅ |
| `0x634C3C` 是 `StartGameFailed`（`0xDC7528`, type=4） | ✅ **新发现** |
| `StartGame` vs `StartGameFailed` 的分叉条件 | ✅ `clientState` |
| 第 1 段 blob 的真实用途 | ⬜ 仍是"未连接时解析后丢弃" |

---

## §5 这对"房间动作失灵"的解释

★★★ **房间动作（准备/开始）失灵的机制现在更清楚了：**

```
客户端点"准备" → 交给 dwRoomImp
  → 发 11/4 setRoomData（已证：客户端确实发）
  → 服务端要回 6/5 Manifold（格式已定，但客户端 clientState 必须 >= 3）
  → 若 clientState == 0，客户端收到 StartGame 只会回 StartGameFailed
```

⇒ **服务端再怎么修推送格式，如果客户端 clientState 不 ≥3，都会被拒。**

这与 173 卷 `srpc+0x4F4`（HMAC 会话）是**并列的两道门**。

---

## §6 方法论

1. **★★★ 分叉条件决定了"这段代码到底服务于哪种状态"。** `cmp [0x76446B0],0 / jne` 一条指令就把"正常处理"和"拒绝处理"分开了。
2. **★★ 同一个分发分支里可能有多个类。** `0xDC751C` 和 `0xDC7528` 在同一 case 的两个条件分支里。
3. **★★★ "被解析"不等于"被使用"。** `clientState==0` 时 `deserialize` 只是消费位流。
4. **★★ 全局状态变量的写点清单能直接给出"这台状态机的可能取值"。** 5 个写点 = 5 个状态迁移源。
