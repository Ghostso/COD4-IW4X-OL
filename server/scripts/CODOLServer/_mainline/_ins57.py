p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.57 ★★★★★ 0xBA3710 的调用链与三处读取器实参（第十二轮）

接 §5.27.56(e)/TLDR §4.6 的问题："三处 0xB783C0 调用的数据源分别是什么"。

**(a) `0xBA3710` 是独立函数（有 SEH 帧）**

```asm
0xBA3710  push ebp / mov ebp,esp
0xBA3713  push -1 / push 0xC8EA3B     ; SEH
0xBA3721  sub esp, 0x3B0
0xBA3731  push ebx / push esi / push edi
0xBA373E  mov eax, [ebp+0x14]         ; arg4
0xBA3741  mov ebx, [ebp+0x10]         ; arg3  ← ebx
0xBA3744  mov esi, [ebp+8]            ; arg1  ← esi
0xBA3747  mov edi, [ebp+0xC]          ; arg2
```

⇒ 内部约定：**`esi` = arg1，`ebx` = arg3，`edi` = arg2**。

**(b) 唯一调用者 `0xBA46C2`（在 0x85 分发的上层）**

```asm
0xBA46A2  cmp eax, 3                  ; 帧类型 == 3 ?
0xBA46AB  mov al, [ebp-0xE]
0xBA46AE  cmp al, 0x85                ; ★ opcode 必须 0x85
0xBA46B2  mov ecx, [ebp+0xC]
0xBA46B5  mov edx, [ebp+8]
0xBA46B8  mov eax, [ebp-0x14]
0xBA46BB  push ecx                    ; arg5
0xBA46BC  push edx                    ; arg4
0xBA46BD  push edi                    ; arg3  → 进入函数后成为 ebx
0xBA46BE  push eax                    ; arg2  → 进入函数后成为 edi
0xBA46BF  push ebx                    ; arg1  → 进入函数后成为 esi
0xBA46C0  mov ecx, esi
0xBA46C2  call 0xBA3710
```

⇒ `0xBA3710(arg1 = 外层 ebx, arg2 = 外层 [ebp-0x14],
            arg3 = 外层 edi, arg4/5 = 外层 [ebp+8]/[ebp+0xC])`

**(c) 三处 `0xB783C0` 的实参（按 cdecl，最后 push = arg1）**

第 1 处 `0xBA3794`（该函数的第一次读取）：

```asm
0xBA374C  push 4            ; arg6 = 4
0xBA3754  push &[ebp-0x3A8] ; arg5
0xBA3761  push &[ebp-0x3A0] ; arg4
0xBA376B  push [ebp+0xC]    ; arg3
0xBA376C  push ebx          ; arg2 = 函数 arg3（边界）
0xBA376D  push esi          ; arg1 = 函数 arg1（dst）
0xBA3794  call 0xB783C0
```

⇒ **dst = 函数 arg1，边界 = 函数 arg3。**

第 2 处 `0xBA37C2`（读帧内 16 字节密钥块）：

```asm
0xBA37A6  push 0x10         ; len = 16
0xBA37AB  push &[ebp-0x50]  ; dst = 密钥块缓冲
0xBA37B2  push &[ebp-0x3A0]
0xBA37BF  push [ebp-0x3A0]
0xBA37C0  push ebx
0xBA37C1  push esi
0xBA37C2  call 0xB783C0
```

第 3 处 `0xBA3A45`（内层分发用）：

```asm
0xBA3A2C  push 4            ; len = 4
0xBA3A34  push &[ebp-0x3A4]
0xBA3A41  push &[ebp-0x390]
0xBA3A42  push ecx
0xBA3A43  push [ebp-0x39C]  ; = 函数 arg3（见 0xBA3774：ebx）
0xBA3A44  push ebx
0xBA3A45  call 0xB783C0
```

**(d) ⇒ 关键结论：三处用的是同一对源（函数 arg1 / arg3）**

```text
0xBA3774  mov [ebp-0x39C], ebx     ; ebx = 函数 arg3   （边界）
0xBA376E  mov [ebp-0x3AC], esi     ; esi = 函数 arg1   （dst/base）
0xBA3A44  push ebx                 ; arg1 = ebx
0xBA3A43  push [ebp-0x39C]         ; arg2 = ebx（同一个值）
```

⇒ 第 3 处把**同一个 ebx 既当 arg1 又当 arg2**，
  这与其他两处（arg1=esi/dst、arg2=ebx/边界）**用法不同**。

**(e) 因此 §5.27.54 的"参数错位"结论需要修正**

```text
不是"读取器拿错缓冲"，而是这一处调用【字节码与其它两处不同】：
  0xBA3794 / 0xBA37C2：push ... push ebx ; push esi   （dst=esi）
  0xBA3A45            ：push ... push ecx ; push ebx   （dst=ebx）
⇒ 第 3 处一旦 dst=ebx 且 len=4，写入位置与其他调用重叠，
  会破坏 [ebp-0x390] 游标所依赖的缓冲布局。
```

**(f) 下一步**

```text
确认 0xBA3A42 的 ecx 来自何处（它是该处的 arg3）。
若 ecx 与 ebx 指向同一缓冲，则这三处读取在互相覆盖；
若不同，则需给出各自来源，才能判断内层流的真实数据源。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("inserted before line", idx+1)
