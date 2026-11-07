p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.67 ★★★★★ 更正 §5.27.60/61：三处调用参数【一致】（第十三轮）

**本节推翻 §5.27.60(c) 与 §5.27.61 的核心结论（"第三处用了不同源基址"）。**

**(a) 关键遗漏：0xBA3A0D 把 ebx 恢复成了 esi**

```asm
0xBA376E  mov [ebp - 0x3AC], esi    ; 保存 esi
0xBA3774  mov [ebp - 0x39C], ebx    ; 保存 ebx
...
0xBA3A0D  mov ebx, [ebp - 0x3AC]    ; ★★ ebx = esi（被恢复了）
0xBA3A81  mov ecx, [ebp - 0x39C]    ; ecx = 原 ebx
0xBA3A8F  push ecx                  ; arg2
0xBA3A90  push ebx                  ; arg1 —— 此刻 ebx == esi
0xBA3A91  call 0xB783C0
```

**(b) 三处调用的实参对照（修正后）**

```text
call#1  0xBA376C push ebx / 0xBA376D push esi   → arg1 = esi, arg2 = ebx
call#2  0xBA37C0 push ebx / 0xBA37C1 push esi   → arg1 = esi, arg2 = ebx
call#3  0xBA3A8F push ecx / 0xBA3A90 push ebx   → arg1 = esi, arg2 = 原 ebx
```

⇒ **三处的源基址（arg1）全部是 `esi`，完全一致。**
  第三处的差异只是 arg2 用了 `[ebp-0x39C]`（保存的原 ebx），
  而 `[ebp-0x39C]` 与 `ebx` 在 call#1/#2 里本就是同一个值 —— **无实质差异**。

**(c) ⇒ 因此以下结论全部作废**

```text
作废 §5.27.60(c)  "第三处换了源基址（arg1 → arg3）"
作废 §5.27.61     "用 b0/b4 验证 arg1 ≠ arg3"
作废 §5.27.61(e)  "两条闭合路径（改 0xBA3A90 / 改缓冲内容）"
作废 §5.27.62(e)  "确认 bufB 的写入者"
作废 §5.27.64(e)  "纯数据级：让源内容为 0x87"
```

**(d) 我在此处的错误模式**

```text
在 0xBA3A8F/0xBA3A90 处读到的 ebx，其值由 0xBA3A0D 决定；
而我当时只回溯到 0xBA3774 的 `mov [ebp-0x39C], ebx`，
漏看了 0xBA3A0D 这条"恢复"指令，于是误以为 ebx 仍是函数入口的 arg3。
⇒ 教训：追寄存器值时，必须覆盖【该点到使用点之间的所有写指令】，
  而不是只看函数入口的赋值。
```

**(e) 那么"cl != 0x87"的原因仍未确定**

```text
已知（仍然成立）：
  · 0xB783C0 参数语义（arg1 源基址 / arg2 边界 / arg3 源偏移 /
    arg4 &新偏移 / arg5 目标 / arg6 长度）
  · 三处调用参数一致，源基址 = 0xBA3710 的 arg1（esi）
  · provider 解密 0xBA3A05 的输入是 [ebp-0x50]（帧内 16B 密钥块）
  · 0xBA35E9 打 NOP 后 644 仍为 0（§5.27.52）⇒ 0x87 分支未进入
  · 640=0xDC / c8=2 / 5e8=3 均满足

未确定：
  cl（[ebp-0x389]，由 0xBA3AA3 从 [ebp-0x38a] 写入）为何不是 0x87。
  三个候选：
    甲. 0xBA3A91 的读取失败（返回假 → 走 0xBA3AAD 把 cl 置 0）
    乙. 读取成功但内容不对（源数据不是我们的帧）
    丙. 0xBA3AE6 之前还有别的路径改写了 [ebp-0x389]
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
