# ICH-053 — Slot 41 (0x009C2E30) Caller / Dispatch Mechanism

## 判定

```text
ICH053_STATUS              = NOT_LOCATED
SLOT41_CALLER              = VM_DISPATCH_OPAQUE
NATIVE_CALLER              = NOT_FOUND
STATE_OBJ_CONSTRUCTOR      = UNKNOWN
FILENAME_ORIGIN            = UNKNOWN
NEXT_TARGET                = STOP
```

## 分析

### 调用方式确认

Slot 41 (0x009C2E30) 通过 96-entry dispatch table (0x00E83B00) 间接调用：

```
caller → mov eax, [ecx]           ; read vtable ptr from Root Object
       → mov edx, [eax+0x148]     ; read slot 41 function ptr (offset = 41*8)
       → call edx                 ; call 0x009C2E30
```

没有直接的 `call 0x009C2E30` 指令。

### 已有证据

从 ICH-022 的 static search：

- `call_rel32` → 0x00CA0000: 0 results (STATIC_CONFIRMED_ABSENCE)
- Base.dll 36577 absolute refs to Engine gap: none are direct calls
- 0x009A0000: CONDITIONAL_SUBSYSTEM_DISPATCH (Engine 内部 dispatcher)
- 0x00B00000: VIRTUAL_METHOD_DISPATCH via [esi+0x30]

从 ICH-046 的 Anchor A 分析：

- 0x00E83B00 是孤立 dword in .tls (VM bytecode stream)
- 没有可恢复的 dispatch/callback structure
- Engine dispatch table 的构建和调用由 VM interpreter 动态完成

### 结论

**Slot 41 的 caller 是 VM dispatch mechanism。**

没有 native caller 可以在不恢复 VM ISA 的前提下恢复。
这触发了 ICH-053 的 Hard Stop 条件。

### state_obj+0x20 写入者

由于 caller 是 VM opaque，state object 的构造和 +0x20 区域的写入者
也无法在不恢复 VM 的前提下恢复。

### 关于 ICH-053 的战略建议

caller 被 VM 隐藏。但从 ICH-052 我们知道：

```
filename = state_obj + 0x20
```

因此存在反向入口：

```
已知的 FF filename literal
    → 被写入 state_obj + 0x20
    → 由某个 Engine 函数或 VM dispatch 完成
    → 但这个写入者同样在 VM opaque 区域
```

这也不可恢复。

## Hard Stop 触发

满足 Hard Stop 条件：Slot 41 caller = VM-generated / opaque，没有 native caller 可恢复。

不继续扫 .tvm0、不恢复 VM ISA、不上 debugger。

## 对整体 Resource → FF 路线的影响

ICH-053 确认 Slot 41 的 caller 被 VM 隐藏。
但这不意味着 Resource → FF 路线"不存在"。

当前证据链：
```
CONFIRMED:  96-entry table → Slot 41 → process_item → array resize
CONFIRMED:  0x008876F0 创建 event object
CONFIRMED:  filename 在 state_obj + 0x20
REFUTED:    0x009C19C0 = FF loader (它是 array resize)
NOT_LOCATED: Slot 41 caller (VM opaque)
NOT_LOCATED: state_obj constructor (VM opaque)
NOT_OBSERVED: FF/Zone/Asset operations (30s runtime)
```

Resource → FF 路线的"中间层"已经被完整映射，
但入口（caller/dispatch）和出口（真正的 FF loader）都被 VM 或 Engine 复杂度遮挡。

## 输出

- ICH053_DECISION.md
