p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.68 ★★★★★ 精确定位：cl 在 0xBA3A99 段是"成功标志"，分发字节在 0xBA3AE0（第十三轮）

**(a) 反汇编（0xBA3AAF..0xBA3AE6）**

```asm
0xBA3A99  test al, al
0xBA3A9B  je  0xBA3AAD          ; 读取失败
0xBA3A9D  mov dl, [ebp - 0x38A] ; 读到的 1 字节
0xBA3AA3  mov [ebp - 0x389], dl
0xBA3AA9  mov cl, 1             ; ★ cl = "成功" 标志
0xBA3AAB  jmp 0xBA3AAF
0xBA3AAD  xor cl, cl            ; ★ cl = "失败" 标志
0xBA3AAF  mov edx, [ebp - 0x394]
0xBA3AB5  mov esi, [ebp - 0x390]
0xBA3ABB  lea eax, [edx + esi]
0xBA3ABE  test cl, cl
0xBA3AC0  je  0xBA3ACA          ; 失败 → 错误出口（0x8435D0 + 0x4F7940 + 复位）
0xBA3AC2  cmp eax, [ebp - 0x39C]
0xBA3AC8  jbe 0xBA3AE0
0xBA3ACA  xor bl, bl            ; 错误出口
...
0xBA3AE0  mov cl, [ebp - 0x389] ; ★★ 真正的分发字节在这里读入
0xBA3AE6  cmp cl, 0x87
```

**(b) ⇒ 精确结论**

```text
0xBA3A99..0xBA3AB0 段的 cl 是【读取成功标志】，不是分发字节。
分发字节 = [ebp-0x389] 的内容 = [ebp-0x38A] 的内容
         = 0xBA3A91 从【源基址 + 游标】读到的 1 字节。
```

**(c) 候选收敛（对应 §5.27.67(e)）**

```text
甲. 读取失败 → 走 0xBA3ACA 错误出口（复位并返回），
    不会到达 0xBA3AE6，644 自然为 0。
乙. 读取成功但 [ebp-0x38A] != 0x87 → 到达 0xBA3AE6，但 jne 走 0xBA3B0E
    （0x89 分支），而 0x89 要求 644 == 1 → 又被复位。
```

两种情形最终都是 `644 == 0`，**与实测一致**，但**区分它们需要一个运行时观测**：
`0xBA3A99` 处 `al` 的值（或 `[ebp-0x38A]` 的内容）。

**(d) 新增一个可静态推进的点**

```text
0xBA3AC2  cmp eax, [ebp-0x39C]
0xBA3AC8  jbe 0xBA3AE0
其中 eax = [ebp-0x394] + [ebp-0x390]（起点 + 游标）
     [ebp-0x39C] = 保存的原 ebx（= 0xBA3710 的 arg3）

若 eax > [ebp-0x39C]，则不跳转 → 落到 0xBA3ACA 错误出口。
⇒ 这给出了一个【纯静态可算】的失败条件：
     [ebp-0x394] + 游标  >  arg3
   若已知 arg3 的语义（= [obj+0xAC] = 帧长 382）与 [ebp-0x394] 的来源，
   就能判断这一步是否会失败。
下一步：回溯 [ebp-0x394] 的赋值（0xBA378A 置 0，0xBA37B3 置 [ebp-0x3A8]）。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
