p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.65 ★★★★★ 帧缓冲生命周期：[obj+0xAC] 0→382→0 循环（第十三轮）

**(a) 观测数据（POST83_SAMPLE，同一轮）**

```text
t=38.578  ac=0    b0=0x00000000  b4=0x00000000     ← 空闲
t=38.606  ac=382  b0=0x3C7EF2A8  b4=0x3C181F00     ← 收到帧
t=38.635  ac=382  b0=0x3C7EEFD0  b4=0x3C181C98
t=38.685  ac=382  b0=0x3C7EE9B8  b4=0x3C181FB0
t=38.700  ac=0    b0=0x00000000  b4=0x00000000     ← 处理完，清零
t=85.602  ac=382  b0=0x3C7EEF68  b4=0x3C181C98     ← 再次收到帧
t=85.656  ac=0    b0=0                b4=0
```

⇒ **`[obj+0xAC]` 在 0 ↔ 382 之间循环**，每收一帧置 382、处理完清零。
   `[obj+0xB0]` / `[obj+0xB4]` 是**每次动态分配的缓冲指针**（地址每帧不同）。

**(b) 与 `0xBA3710` 实参的对应**

```asm
0xBA44AD  mov ecx, [esi + 0xB0]    ; → 传给 0xB9BBB0
0xBA44B3  call 0xB9BBB0            ; 返回 ctx+0x1C - ctx+0x24 + 0x1F
0xBA44B8  mov edi, [esi + 0xAC]    ; = 382（帧长）
0xBA44BE  mov ebx, eax
...
0xBA46BF  push ebx                 ; arg1
0xBA46BE  push eax                 ; arg2 = [ebp-0x14]
0xBA46BD  push edi                 ; arg3 = 382
0xBA46C2  call 0xBA3710
```

⇒ `0xBA3710` 的 **arg3 = 382**（帧长，一个数值）；
   arg1 = `0xB9BBB0(...)` 的返回值（同样是数值）。
   **两者都不是缓冲指针** —— 再次印证 §5.27.63(b) 的撤回。

**(c) 由此可推出的重要事实**

```text
`ac` 在 38.700 被清零后，直到 85.602（下一帧）才重新为 382。
而我们发帧在 t≈78.9（观察器时间轴），此时若 ac == 0，
则 0xBA3710 收到的 arg3 == 0，
`0xBA3A91` 处 `lea ecx,[edx+edi]`（edi=长度）会算出 0，
读取长度为 1 的字节时即落在缓冲起点 —— 内容当然不是 0x87。
```

**(d) ⇒ 这给出一个可检验的预测**

```text
若把"发帧时刻"严格对齐到 ac == 382 的窗口（即客户端刚收到帧、
尚未处理完的瞬间），则 0xBA3A91 的读取应落在合法数据上。

对齐办法（纯数据级/流程级，不改代码）：
  · 观察器在 ac 从 0→382 的变化瞬间写一个标记文件；
  · 探针等到该标记出现后再发帧。
  这与 §5.27.43 的"相位差"问题同源，但门槛值从 t>=30 改成
  "ac 见到 382"，是【条件触发】而非【时间触发】。
```

**(e) 下一步**

```text
1. 在观察器里把已有的 ac 采样点（CODEC_TRANSITION/POST83_SAMPLE）
   接一个副作用：ac 由 0 变 382 时写 ac_ready.flag；
2. 探针增加 --wait-ac-flag <path>，等该文件出现后再发 0x85；
3. 重跑，观察 644 是否变化。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
