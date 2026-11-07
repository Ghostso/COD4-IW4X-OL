# E22 调用点与参数恢复

## 地址口径

- 镜像 ImageBase：`0x400000`
- 本文地址均为 RVA
- `.text`：VA `0x1000`，RawSize `0x7ACA00`，可执行
- `.data`：VA `0x8F1000`，VirtualSize `0x0D05C420`，RawSize `0x00049600`，**BSS 占绝大部分**

## 0x6AC0C0

调用约定：`thiscall`（ECX=this），两个栈参数，返回 `bool` 到 AL。

| 栈参数 | 来源 | 类型推断 | 证据 |
|---|---|---|---|
| [ebp+8] | 调用者 `0x68EEF1` 传入 `[ebp-0xD]` | 输出状态字节指针 | `6AC234 mov byte [eax],4` |
| [ebp+0xC] | 调用者传入对象指针 | 输出对象指针 | `6AC20A mov edi,[ebp+0xC]`；`6AC229 mov ecx,[edi]` |

调用点 `0x68EEF1` / `0x68F02C` 前的实参：

```asm
68EEED  mov byte ptr [ebp-0xD],0
68EEE1  push eax          ; [ebp-0x14] 输出对象指针
68EEE5  push edx          ; [ebp-0xD] 输出状态字节
68EEF1  call 0x6AC3D0
```

## 0x6AAE70

调用约定：`thiscall` + 5 个栈参数，`ret 0x14`。调用点 `0x6AC2F0`。

| 参数 | 调用前来源 | 推断 |
|---|---|---|
| [ebp+8] | 局部 `[ebp-0x14]`（`0x6A85AD0` 解析出的载荷长度/偏移） | 长度或数据指针 |
| [ebp+0xC] | 局部 `[ebp-0x14]`（消息数据指针） | 缓冲区指针 |
| [ebp+0x10] | `edi = [esi+0xAC]-1` | 有效载荷长度 |
| [ebp+0x14] | `ebx = object+0xB0` 解引用结果 | 载荷对象/缓冲区 |
| [ebp+0x18] | `[ebp+8]` 调用者输出状态 | 状态输出 |

## 返回路径

`0x6AAE70` 在 `0x6AB16B` 之后根据 `AL` 决定后续：
- 失败：设置错误状态并返回 false。
- 成功：继续处理，最终返回 true。

`0x6AC2F5 test al,al` → `0x6AC2F7 setne [ebp-0xD]`，说明 `0x6AAE70` 的返回值直接作为 `0x6AC0C0` 的输出状态标志。

## 不可追踪项

- `0xA85AD0` 位于 BSS，无磁盘字节，无法恢复参数/返回约定。
- `0x6AAE70` 调用内部对 `0xA878A0`、`0x6A8BF0` 的语义依赖 BSS/运行时函数。
