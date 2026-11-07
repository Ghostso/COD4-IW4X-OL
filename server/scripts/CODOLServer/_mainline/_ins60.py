p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.60 ★★★★★★ 0xB783C0 的语义确证与源基址差异（第十二轮终局）

**(a) `0xB783C0` 的完整参数语义（逐条对照反汇编）**

```asm
0xB783C0(arg1..arg6)
0xB783C3  cmp [ebp+0x18], 0      ; arg5 必须非 0（== 目标缓冲）
0xB783C7  mov edx, [ebp+0x10]    ; edx = arg3（源偏移）
0xB783CB  mov esi, [ebp+0x14]    ; esi = arg4（输出：新偏移指针）
0xB783CF  mov edi, [ebp+0x1C]    ; edi = arg6（长度）
0xB783D2  lea ecx, [edx + edi]
0xB783D7  mov [esi], ecx         ; *arg4 = arg3 + arg6
0xB783E4  cmp edx, [ebp+0xC]     ; 源偏移 <= arg2（边界）
0xB783EA  cmp ecx, [ebp+0xC]
0xB78407  mov eax, [ebp+8]       ; arg1（源基址）
0xB7840A  mov ecx, [ebp+0x18]    ; arg5（目标）
0xB7840E  add eax, edx           ; arg1 + arg3
0xB78414  call 0xC3E400          ; memcpy(arg5, arg1+arg3, arg6)
```

⇒ **语义确定**：

```text
arg1 = 源基址
arg2 = 边界（源偏移的上限）
arg3 = 源偏移
arg4 = &新偏移（输出）
arg5 = 目标缓冲
arg6 = 长度
```

**(b) 三处调用按此语义重新对照**

```text
0xBA3794（读 4 字节）
  arg1 = esi        = 函数 arg1        ← 源基址 A
  arg3 = [ebp+0xC]  = 函数 arg4
  arg5 = &[ebp-0x3A0]                 ← 目标
  arg6 = 4

0xBA37C2（读 16 字节密钥块）
  arg1 = esi        = 函数 arg1        ← 源基址 A（同一个）
  arg5 = &[ebp-0x50]                  ← 目标
  arg6 = 16

0xBA3A91（读内层首字节 1 字节）
  arg1 = ebx        = 函数 arg3        ← 源基址 B（不同！）
  arg3 = [ebp-0x390]                  （游标）
  arg5 = &[ebp-0x38a]                 ← 目标
  arg6 = 1
```

**(c) ⇒ 根因（决定性）**

```text
前两处读取用【函数 arg1】作源基址；
第三处（决定内层首字节 cl 的那一处）用【函数 arg3】作源基址。

两者是不同的缓冲。若 arg3 指向的不是解密后的明文区，
则 cl 必然不等于 0x87 —— 与 §5.27.52 的实验结论完全吻合。
```

**(d) 与此前分析的关系**

```text
· §5.27.54 / §5.27.57(e) 曾提"参数错位"，方向正确但定位不准；
· §5.27.58 更正了 [ebp-0x39C] 是缓冲指针；
· 本节给出最终形态：不是某个参数被传错，
  而是【第三处读取刻意换了源基址】（arg1 → arg3）。
```

**(e) 下一步（机制已明确，只剩一个值待确认）**

```text
需要确认 0xBA3710 的 arg1 与 arg3 是否指向同一缓冲：
  · 若同一 → 差异只是视角，问题在别处
  · 若不同 → arg3 指向什么，就是 provider 输出应到达的地方；
              需要查明"谁把解密结果写入 arg3 指向的缓冲"

线索：调用者 0xBA46C2 的 arg1 = 外层 ebx、arg3 = 外层 edi；
      再由外层反查这两个指针的来源即可。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
