p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.73 ★★★★★ 更正 §5.27.70/5.27.72：0xBA3A57 会覆盖 [ebp-0x394]（第十三轮终局）

**(a) 正确的指令对齐（从 0xBA3A4A 起）**

之前的反汇编从 `0xBA3A48` 起切分，导致 `0xBA3A48..0xBA3A4F` 被错解；
正确切分如下：

```asm
0xBA3A45  call 0xB783C0          ; 4 字节读取（游标推进 4）
0xBA3A4A  add esp, 0x18
0xBA3A4D  test al, al
0xBA3A4F  je  0xBA3A65           ; 读取失败 → α 出口
0xBA3A51  mov eax, [ebp - 0x3A4] ; 读取器写回的新偏移
0xBA3A57  mov [ebp - 0x394], eax ; ★★ 覆盖 [ebp-0x394]
0xBA3A5D  cmp eax, esi           ; vs [ebp-0x3B0]（帧尾）
0xBA3A5F  ja  0xBA3A65           ; 超过帧尾 → α 出口
0xBA3A61  mov al, 1
0xBA3A63  jmp 0xBA3A67
0xBA3A65  xor al, al             ; α 出口
0xBA3A67  mov byte [ebp - 0x389], 0
0xBA3A6E  test al, al
0xBA3A70  je  0xBA3AAD           ; 失败 → cl = 0
0xBA3A72..0xBA3A91  读 1 字节（内层首字节）
0xBA3A9D  mov dl, [ebp - 0x38A]
0xBA3AA3  mov [ebp - 0x389], dl  ; ★ 分发字节
```

**(b) ⇒ 撤回 §5.27.69/5.27.70 的数值代入**

```text
§5.27.69(a) 说 "[ebp-0x394] 保存的是帧内第一个 u32"  —— 错。
  0xBA37B3 确实写过一次（= 0xBA3794 读到的 4 字节），
  但 0xBA3A57 在 0xBA3A2C 那次读取之后又把它【覆盖】为"新偏移"。

§5.27.70(b) 据此代入 "eax = frame_len + 游标" —— 错。
  该式用的是 [ebp-0x394] + [ebp-0x390]，
  而此时 [ebp-0x394] 已是"新偏移"，[ebp-0x390] 也是"游标"，
  二者高度相关（都由同一次读取更新），不是"帧长 + 游标"。

§5.27.72(b) 的 "判据退化为 游标 <= 0" —— 随之作废。
```

**(c) 仍然成立的部分**

```text
· 0xBA3AC2（实为 0xBA3A5D）是 cmp eax, esi，其中 esi = [ebp-0x3B0]（帧尾）
· 0xBA3A2C 那次 4 字节读取会推进游标
· 0xBA3A91 读 1 字节得到 [ebp-0x38A] → [ebp-0x389] → cl
· cl 必须 == 0x87 才能进入 arm（§5.27.52 实验已证未进入）
· 三处 0xB783C0 调用参数一致（§5.27.67）
```

**(d) 我在本轮犯的错误模式（第四次同类）**

```text
从任意地址起始反汇编会产生错误的指令边界，
进而得出错误的"指令语义"。
本次 0xBA3A48 起的切分把 0xBA3A4A 的 add esp,0x18 误读成别的指令，
连带把 0xBA3A51/0xBA3A57 的作用判断错。

⇒ 教训：在关键判据处，必须
   ① 用函数入口顺序反汇编，或
   ② 在多个候选起始地址下交叉验证指令边界。
```

**(e) 下一步**

```text
重新从 0xBA3710 入口顺序反汇编，把
  [ebp-0x394] / [ebp-0x390] / [ebp-0x3A4] / [ebp-0x3B0] / esi
  五个量的演化一次性列全，再判断 0xBA3A5D 的
  `cmp eax, esi` 在正常入站帧下是否可能成立。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
