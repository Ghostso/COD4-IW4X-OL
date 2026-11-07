p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.59 ★★★★★ 游标 [ebp-0x390] 的语义与两次赋值（第十二轮）

**(a) 全函数内 `[ebp-0x390]` 只有两个写入点**

```asm
0xBA383A  mov [ebp-0x390], eax     ; 第一次
0xBA3A18  mov [ebp-0x390], ecx     ; 第二次（ecx = [ebp-0x3A4]，读取器返回值）
```

其余 6 处都是读取或取地址。

**(b) 第一次赋值：游标 = arg1 - 8 - 偏移**

```asm
0xBA37F8  mov eax, [ebp-0x39C]     ; base（函数 arg3）
0xBA37FE  mov ecx, [eax + esi - 8] ; 取首字段
0xBA3802  lea eax, [eax + esi - 8] ; eax = base + arg1 - 8
0xBA37DA  lea edx, [esi + eax_old] ; edx = base + 偏移
0xBA3813  cmp eax, edx
0xBA3838  sub eax, edx             ; ★ eax = arg1 - 8 - 偏移
0xBA383A  mov [ebp-0x390], eax     ; 游标
```

⇒ **`[ebp-0x390]` 是一个【相对偏移量】，不是绝对指针。**

**(c) 第二次赋值：游标被"重置"为读取器的返回值**

```asm
0xBA3A2C..45  call 0xB783C0        ; 读取器，arg4 = &[ebp-0x3A4]
0xBA3A07  mov ecx, [ebp-0x3A4]     ; ★ 读取器写回的"新偏移"
0xBA3A18  mov [ebp-0x390], ecx     ; ★ 直接覆盖游标
```

而 `0xB783C0` 内部（§5.27.53c）：
```asm
0xB783D2  lea ecx, [edx + edi]     ; arg3 + arg6
0xB783D7  mov [esi], ecx           ; *arg4 = arg3 + arg6
```

⇒ 读取器返回的是 **`arg3 + arg6`**。

**(d) 关键疑点**

```text
第一次赋值给的是 "arg1 - 8 - 偏移"（一个相对量）
第二次赋值给的是 "arg3 + arg6"（读取器算出的新位置）

若这两者的【基准不同】，游标就会在一次读取后跳到错误位置，
于是 0xBA3A91 处读到的"内层首字节"来自错误的偏移，
自然不会是 0x87。
```

**(e) 需要确认的一点**

```text
0xBA3A42 处传给 0xB783C0 的 arg3 是 ecx（该处第 4 个 push 的值）。
而 0xBA3A3B lea edx,[ebp-0x390] 之后 0xBA3A41 push edx 是 arg4。

⇒ 需要回溯 0xBA3A42 的 ecx 来源，
  并与 0xBA383A 写入的基准做差，判断二者是否同一坐标系。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
