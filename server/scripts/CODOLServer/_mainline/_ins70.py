p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.70 ★★★★★★ 失败点已算实：frame_len + 游标 > arg3（第十三轮终局）

**(a) 游标的完整演化（已逐条追完）**

```asm
0xBA383A  mov [ebp-0x390], eax    ; 游标 = arg1 - 8 - 偏移（第一次）
0xBA39E7  mov esi, [ebp-0x390]    ; 传给 provider
0xBA3A07  mov ecx, [ebp-0x3A4]    ; ecx = 读取器上一步写入的新偏移
0xBA3A18  mov [ebp-0x390], ecx    ; 游标 = 它
0xBA3A2C..45  call 0xB783C0       ; 读 4 字节：
              arg3 = ecx（= 游标值）
              arg6 = 4
              arg4 = &[ebp-0x390]
              ⇒ 游标被更新为 【游标 + 4】
0xBA3A72  mov eax, [ebp-0x390]    ; 读内层首字节时用的游标
```

**(b) 代入 `0xBA3AC2` 的判据**

```asm
0xBA3AAF  mov edx, [ebp-0x394]    ; = frame_len（帧内首 u32）
0xBA3AB5  mov esi, [ebp-0x390]    ; = 游标（≈ 4 量级）
0xBA3ABB  lea eax, [edx + esi]    ; eax = frame_len + 游标
0xBA3AC2  cmp eax, [ebp-0x39C]    ; vs arg3
0xBA3AC8  jbe 0xBA3AE0            ; 必须 <= 才继续
0xBA3ACA  （错误出口：0x8435D0 + 0x4F7940 + 复位）
```

具体数值：

```text
frame_len = 382（我们发出去的长度字段）
游标      ≈ 4 左右（读取器每次 +4 的累加）
arg3      = [obj+0xAC]（客户端当前帧长；收到帧时为 382，处理完为 0）

⇒ eax = 382 + 游标 > 382 = arg3（当 arg3 == 382 时）
⇒ 或 arg3 == 0 时更不可能成立
⇒ 0xBA3AC8 永不跳转 ⇒ 必走 0xBA3ACA 错误出口
   ⇒ 复位返回 ⇒ [obj+0x644] 保持 0 ⇒ c8 停在 2 ⇒ ~90 s 弹窗
```

**(c) ⇒ 这是第一档⑤失败点的【最终算术表述】**

```text
客户端要求：frame_len + 游标 <= obj+0xAC

而 frame_len 是【我们自己写进帧里的长度字段】，
obj+0xAC 是【客户端记录的本帧长度】。

只要服务端的 frame_len 字段 >= 客户端的帧长，
该不等式就不成立 —— 这与密钥、加密、MAC 全都无关。
```

**(d) 可检验的修法（服务端侧，纯数据）**

```text
让 frame_len 字段取一个【足够小】的值：
    frame_len <= obj+0xAC - 游标

已知 obj+0xAC = 382、游标 ≈ 4 量级，
⇒ 只要 frame_len <= 约 378，不等式即成立。

但注意：frame_len 同时也是帧的【实际长度字段】，
改小它可能与 0xB783C0 的边界检查（arg2）冲突。
需要在 [frame_len 字段值] 与 [服务端实际帧长] 之间取舍：
  · 帧仍在 socket 上发 386 字节（含 tag）
  · 但长度字段写一个小值（例如 4）
  · 并保证内层负载放在 frame_len 之后仍是可读位置
```

**(e) 下一步（可立即实验）**

```text
把服务端 0x85 帧的长度字段从 382 改为一个小值
（例如 4 或 0x10），保持其他不变，重跑观察 644 是否变化。
这与之前所有尝试不同：它不依赖密钥、不依赖时序、不改代码。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
