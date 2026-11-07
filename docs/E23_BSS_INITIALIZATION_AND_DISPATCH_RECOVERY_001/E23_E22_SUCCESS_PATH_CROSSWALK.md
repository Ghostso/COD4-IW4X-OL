# E23 与 E-22 成功路径交叉核对

## 1. E-22 主张 vs 本轮实测

| 编号 | E-22 主张 | 本轮实测 | 裁定 |
|---|---|---|---|
| E22-1 | `0x6AC0C0` 为 thiscall，返回 bool，两个栈输出参数，`ret 8` | 序言 `8B F1`(this=ECX)；`ret 8`；`0x6AC234 mov byte [eax],4` 证实输出状态字节 | 一致（PROVEN） |
| E22-2 | `0x6AAE70` 唯一调用点 `0x6AC2F0`，thiscall + 5 栈参，`ret 0x14` | 调用者命中仅 `0x6AC2F0`；尾声 `ret 0x14` | 一致（PROVEN） |
| E22-3 | `0x6AC3D0` 是跳板 | `push ebp; mov ebp,esp; pop ebp; jmp 0xAAC0C0` | 一致（PROVEN） |
| E22-4 | `0x6AC3D0` 调用者 `0x68EEF1`/`0x68F02C` | rel32 命中恰为 `0x68EEF1`、`0x68F02C` | 一致（PROVEN） |
| E22-5 | 接收计数器 `[edi+0x5D0]` 读/递增/比较 | `0x6AAFA4/6AAFAD` 读写，失败置 `Bad recv counter` | 一致（PROVEN） |
| E22-6 | 16 字节 XOR/OR 比较 → `HMAC mismatch` | `0x6AB0E6..0x6AB12D` 吻合 | 一致（PROVEN） |
| E22-7 | `0xA85AD0` 等位于 `.data` BSS 虚拟尾部，磁盘无字节 | 按 **VA**→`.text`（有无字节、可反汇编）；仅按 RVA 才是 `.data` BSS | **REFUTED**（基准错误） |
| E22-8 | `[edi+0x5F4]` 为虚表调用（成功路径） | 确为虚表调用，但 `[edi+0x5F4]` 是**对象指针**，vtable `0xC5A31C`，slot+3 `0xA87D50` | 部分一致（已细化） |

## 2. 成功路径完整交叉核对

```text
0x68EEF1/0x68F02C  会话循环
        call 0x6AC3D0            ; 跳板
 0x6AC3D4   jmp 0xAAC0C0         ; 0x6AC0C0 实体
 0x6AC0EA   cmp [esi+0xC8],4     ; 已失败即返回 false
 0x6AC109   call 0xAAA7B0        ; 维护
 0x6AC10E   cmp [esi+0xC8],2     ; 非 2 跳过
 0x6AC13D   mov ecx,[esi+0xB0]; call 0xDF4A028  ; 取帧缓冲
 0x6AC148   mov edi,[esi+0xAC]; dec edi         ; 有效长
 0x6AC168   call 0xA85AD0        ; 解析（本论目标 #1）
 0x6AC178   mov eax,[esi+0x5CC] ; 消息码
   ├─ ==1: 0x81 -> 0xAAB310 ; 0x04 -> 0xAAA770
   ├─ ==2: 0x83 -> 0xAAB260 ; 0x84 -> (分配对象)
   └─ ==3: 0x85 -> call 0x6AAE70
 0x6ACE70   0x6AAE70 内 HMAC/计数器校验
   ├─ 失败: 日志 0x43A7C0 -> 0xAAA770 置状态 4
   └─ 成功 0x6AB140:
         mov ecx,[edi+0x5F4]        ; 协商对象
         mov edx,[ecx]; mov edx,[edx+0xC]
         push len; push buf; push buf; push tmp
         call edx                   ; slot+3 = 0xA87D50
```

## 3. E-22 成功路径 `[edi+0x5F4]` 调用的最终解释

- E-22 若把该调用归因于"BSS 虚表（0xA85AD0 一族）"，则**不成立**：vtable 在 `.rdata`（`0xC5A31C`），目标是 `.text` 的 `0xA87D50`。
- 该调用可解释为：**HMAC/计数器校验通过后，把已解析的载荷（span 缓冲，长 `[ebp-0x220]`）经协商对象 slot+3 递交（做二次长度/摘要校验后流入 0xACE1B0）**。
- 因此 E-22 的"成功返回后缓冲区交接"在**对象层面**得到解释（交给 `[edi+0x5F4]` 对象的 slot+3），但该对象**与五个目标无指针关系**。

## 4. 修正后的方向判定

| 假设 | E-22 | 本轮修正 |
|---|---|---|
| H1 入站 HMAC 验证 | INFERRED（强） | 维持（帧码 0x85 + recv counter + HMAC 串） |
| H2 出站签名 | WEAK | 维持弱 |
| H3 收发共用会话/计数器 | INFERRED（强） | 维持 |
| "五地址为 BSS 隐藏目标" | E-22 结论 | **REFUTED**：五地址为 `.text` 辅助函数 |

方向判定本身未因基准修正而改变；改变的是"下游目标不可静态分析"的阻塞强度。
