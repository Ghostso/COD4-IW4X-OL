p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.69 ★★★★★ [ebp-0x394] 的来源已确定：帧内首 u32（第十三轮）

**(a) `[ebp-0x3A8]` 与 `[ebp-0x394]` 的关系**

```asm
0xBA374C  push 4 / lea edx,[ebp-0x3A8]
0xBA3794  call 0xB783C0            ; ★ 读 4 字节 → [ebp-0x3A8]
0xBA37A0  mov edx, [ebp-0x3A8]
0xBA37B3  mov [ebp-0x394], edx     ; ★ [ebp-0x394] = 帧内首 u32
...
0xBA3924  push edx                 ; edx = [edi+0xAC] - 4
0xBA392C  call 0xC73760            ; HMAC_SHA1 update
0xBA393B  mov [ebp-0x3A8], 0x14    ; ★ 此时才被改写成 20（摘要长度）
```

⇒ **`[ebp-0x394]` 保存的是"帧内第一个 u32"**，
  即我们发出去的 `frame_len` 字段（= 382）。
  它在 `0xBA37B3` 被保存后不再变化
  （`0xBA393B` 改写的是 `[ebp-0x3A8]`，是另一个槽）。

**(b) 于是 0xBA3AC2 的判据可以代入具体值**

```asm
0xBA3AAF  mov edx, [ebp - 0x394]   ; = 382（我们发的长度字段）
0xBA3AB5  mov esi, [ebp - 0x390]   ; = 游标
0xBA3ABB  lea eax, [edx + esi]     ; eax = 382 + 游标
0xBA3ABE  test cl, cl
0xBA3AC0  je  0xBA3ACA             ; 读取失败 → 错误出口
0xBA3AC2  cmp eax, [ebp - 0x39C]   ; 382 + 游标  vs  arg3
0xBA3AC8  jbe 0xBA3AE0             ; <= 才继续
```

而 `[ebp-0x39C]` = 保存的原 ebx = `0xBA3710` 的 **arg3** = `[obj+0xAC]`（帧长）。

**(c) ⇒ 关键判断**

```text
若 arg3 == 382（帧长），则要求：
    382 + 游标 <= 382   ⇒  游标 <= 0

而游标 [ebp-0x390] 在 0xBA383A 被设为 "arg1 - 8 - 偏移"，
随后在 0xBA3A18 被读取器更新为 "该次读取的新偏移"。

⇒ 游标几乎必然 > 0 ⇒ eax > arg3 ⇒ 0xBA3AC8 不跳转
    ⇒ 落到 0xBA3ACA 错误出口 ⇒ 复位返回 ⇒ 644 = 0。

这与实测完全一致，且是【纯静态推导】，不依赖任何未观测值。
```

**(d) 但需先确认 arg3 的精确值**

```text
0xBA44B8  mov edi, [esi + 0xAC]    ; arg3 = obj+0xAC
POST83_SAMPLE 实测 ac 在 0 → 382 → 0 循环。
若我们发帧时 ac == 0（已处理完上一帧、尚未收到新帧），
则 arg3 == 0，那么 eax = 382 + 游标 <= 0 永不成立 ⇒ 必失败。

⇒ 这就把 §5.27.65(d) 的预测形式化了：
  必须让 arg3 == 382，即发帧时刻 ac 必须处于"刚收到帧"的窗口。
```

**(e) 下一步**

```text
1. 用运行时可观测的方式确认：我们发帧时 ac 的实际值。
   （观察器已能读 obj+0xAC；只需把采样与探针的 sent_85 对齐）
2. 若 ac == 0 → 失败原因确定，修法是"让服务端在客户端等待接收时才发"。
   但这又回到 §5.27.66 的相位差问题。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
