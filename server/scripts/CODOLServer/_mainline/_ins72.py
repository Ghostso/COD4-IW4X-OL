p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.72 ★★★★★★ obj+0xAC 就是帧内的长度字段本身（第十三轮终局）

**(a) `obj+0xAC` 的写入者（0xBA4000 附近）**

```asm
0xBA4000  lea edx, [esi + 0xA0]     ; ★ 源基址 = obj + 0xA0
0xBA4006  push 4                    ; 读 4 字节
0xBA4008  push edx
0xBA4000..0x10  call 0xB783C0       ; 同一读取器
0xBA4018  test al, al
0xBA401A  je  0xBA4025
0xBA401C  mov eax, [ebp - 8]        ; 读到的值
0xBA401F  mov [esi + 0xAC], eax     ; ★★ obj+0xAC = 它
0xBA4025  mov eax, [esi + 0xAC]
0xBA402B  test eax, eax
0xBA402D  jne 0xBA403D              ; 非 0 才继续
```

⇒ **`obj+0xAC` = 从 `obj+0xA0` 起读出的 4 字节值**，
  而该处正是【帧内的 u32 长度字段】。

**(b) ⇒ 判据退化为一个恒假式**

```text
0xBA3AC2 要求：  frame_len + 游标 <= obj+0xAC

但 obj+0xAC 就是 frame_len 本身（同一个字段被解析出来）
⇒ 判据等价于：   游标 <= 0
而游标在 0xBA3A2C..45 处被 +4 更新过（§5.27.70a）
⇒ 游标 >= 4 > 0
⇒ 判据【恒不成立】
```

**(c) ⇒ 这是终局结论**

```text
第一档⑤的失败不是"我们把 frame_len 写错了"，
而是【客户端的这条判据本身就要求游标 <= 0】，
而该函数在任何正常调用下都会先把游标推进至少 4。

⇒ 两种解读：
  甲. 我们对该函数路径的理解仍有偏差
      （可能 0xBA3A2C 那次读取在某些条件下不会执行，
        从而游标保持 <= 0）；
  乙. 或者这条路径本就是"错误处理路径"，
      正常流程应走别的分支（例如 0xBA3A2A 的 je 之前就应返回）。

⇒ 建议下一步：检查 0xBA3A2C 之前的所有分支
   （0xBA39E0 / 0xBA39E2 / 0xBA3A28 / 0xBA3A2A），
   确认在正常入站帧下应当走到哪里。
```

**(d) 附：与 §5.27.71 的关系**

```text
§5.27.71 已证"frame_len 不能单独改小"（会破坏切分），
本节进一步说明：即使字段合法，判据仍恒假。
两者一致：该判据在正常帧下不可能成立。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
