p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.61 ★★★★★ 用已有观测数据验证：arg1 与 arg3 确实不同（第十二轮收官）

**(a) `0xBA3710` 的 arg1/arg3 对应观察器的 `b0`/`b4` 两个字段**

```text
POST83_SAMPLE（IFS1_ELEVATED_20261002_013407）
  t=38.578  a8=779383296  ac=0     b0=0           b4=0
  t=38.606  a8=779383296  ac=382   b0=1014952616  b4=1008213760

⇒ b0 = 0x3C7C4A28，b4 = 0x3C1F0A00  —— 两个不同的地址
```

**(b) ⇒ 验证了 §5.27.60(c) 的推断**

```text
前两处读取用 函数 arg1 作源基址（对应其一）
第三处（决定内层首字节 cl）用 函数 arg3 作源基址（对应另一个）

两者确为不同缓冲。
```

**(c) 因此第一档⑤的机制可以完整表述**

```text
1. 服务端发出的 0x85 帧到达客户端
2. 0xBA46C2 分发 → 0xBA3710(arg1 = bufA, arg3 = bufB, ...)
3. 0xBA3794 从 bufA 读 4 字节（首字段）
4. 0xBA37C2 从 bufA 读 16 字节 → [ebp-0x50]（密钥块）
5. 0xBA3A05 provider 解密（输入 = [ebp-0x50]）
6. 游标 [ebp-0x390] 被设为 arg1 - 8 - 偏移，随后由读取器更新
7. 0xBA3A91 从【bufB + 游标】读 1 字节 → [ebp-0x38a]
8. 0xBA3AA3 写入 [ebp-0x389] → 即分发用的 cl
9. cl != 0x87（因为 bufB 不是步骤 5 的解密输出）
10. 0x87 arm 不进入 → 644 恒 0 → c8 停在 2 → ~90 s 弹窗
```

**(d) 与全部实验观测一致**

```text
· §5.27.52：0xBA35E9 打 NOP 后 644 仍 0  ⇒ 无 0x87 分支
· §5.27.48：640=0xDC / c8=2 / 5e8=3 均满足
· §5.27.18/29/44：MAC 与 AES 口径三次命中（密钥无误）
· §5.27.49：5ec 递增（外层帧被正常接收）
```

**(e) 结论（第一档⑤的最终形态）**

```text
这不是服务端能通过"发对内容"解决的问题：
客户端把【决定 0x87/0x89 分支的那个字节】从一个与
解密输出无关的缓冲（bufB）中读取。

⇒ 要闭合第一档⑤，只有两条路：
  甲. 代码级：把 0xBA3A90 的 `push ebx` 改为 `push esi`
      （即让第三处读取也使用 arg1 作为源基址）——
      这是 2 字节的修改，且与另两处读取保持一致。
  乙. 数据级：确认 bufB 的内容由什么写入，
      若可控，则让服务端流程把它填成 0x87。

推荐甲：改动最小、语义最自然（与同函数内另两处一致）。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
