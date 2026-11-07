p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.58 ★★★★★ 更正 §5.27.54(a)：[ebp-0x39C] 是缓冲指针，不是连接对象（第十二轮）

**(a) 决定性证据**

```asm
0xBA37D4  mov eax, [ebp-0x3A0]
0xBA37DA  lea edx, [esi + eax]
0xBA37DD  mov [ebp-0x3B0], edx        ; 边界 = base(arg1) + 偏移
0xBA37E3  mov [ebp-0x3A4], eax
0xBA37E8  ...
0xBA37F8  mov eax, [ebp-0x39C]        ; ★ 取出
0xBA37FE  mov ecx, [eax + esi - 8]    ; ★★ 按【基址】解引用
0xBA3802  lea eax, [eax + esi - 8]
0xBA3809  mov ecx, [eax + 4]
```

`[ebp-0x39C]` 被用作 `[base + arg1 - 8]` 的基址 ——
**它是数据缓冲指针**，而不是"连接对象指针"。

**(b) 更正 §5.27.54(a)**

```text
§5.27.54(a) 依据 0xBA36C8 `mov [ebx+0xC8], 2` 判断 ebx = 连接对象。
但 0xBA3600 与 0xBA3710 是【两个不同的函数】：
  0xBA3600：0xBA3605 mov ebx, ecx → ebx = this（连接对象）
  0xBA3710：0xBA3741 mov ebx, [ebp+0x10] → ebx = arg3（缓冲指针）
同名寄存器在不同函数里含义不同，此前把二者混为一谈。
```

**(c) 于是 §5.27.54 与 §5.27.57(e) 的"参数错位"结论也需重估**

```text
三处 0xB783C0 调用的实参对照（0xBA3710 内，esi=arg1, ebx=arg3）：

  0xBA3794： dst=esi(arg1)      边界=ebx(arg3)  len=4
  0xBA37C2： dst=&[ebp-0x50]    其余同上         len=16
  0xBA3A45： dst=ebx(arg3)      边界=[ebp-0x39C](=arg3)

⇒ 第 3 处的 dst 与边界【是同一个值】，确实与另两处不同，
  但这不必然意味着错误——需结合 [ebp-0x390] 游标的语义判断。
```

**(d) 仍然成立的结论**

```text
· 0xBA3710 是 0x85 的入站处理器（唯一调用者 0xBA46C2，且入口判 opcode==0x85）
· 帧缓冲指针 = 函数 arg1（esi），边界 = 函数 arg3（ebx）
· [ebp-0x50] 是帧内 16 字节密钥块的落地位置（§5.27.56）
· provider 调用 0xBA3A05 用 [ebp-0x50] 作为输入
· 内层分发字节 cl 来自 [ebp-0x389]，由 0xBA3AA3 写入
· 0xBA35E9 已 NOP 仍不置 644 ⇒ 0xBA3590 未被调用（§5.27.52）
```

**(e) 下一步**

```text
逐字节跟踪 [ebp-0x390]（游标）在三处读取后的取值变化：
  0xBA37E3  [ebp-0x3A4] = 偏移
  0xBA3818  [ebp-0x390] = ?
  0xBA3A18  [ebp-0x390] = [ebp-0x3A4]
若第 3 处的读取发生在游标已被推进到帧尾之后，
则它读到的就是越界/零数据 ⇒ cl != 0x87。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
