p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.92 ★★★★★ 补丁时机确实有影响，但方向与旧结论相反（第十五轮）

**(a) 新增的"分发字节落点桩"**

```text
目的：让观察器能读到 cl（分发字节），以确认它到底是不是 0x87。

做法（两处等长 6 字节替换，无需跳转/跳板）：
  0xBA3AA3  88 95 77FCFFFF  mov [ebp-0x389], dl
        ->  88 97 D4060000  mov [edi+0x6D4], dl       ; edi = 连接对象
  0xBA3AE0  8A 8D 77FCFFFF  mov cl, [ebp-0x389]
        ->  8A 8F D4060000  mov cl, [edi+0x6D4]

观察器 FRAMEBUF 事件已加 " d4=" 字段读取 obj+0x6D4。
实测补丁生效：okB=True / okC=True。
```

**(b) 时机对照（多轮，同一配置只改 --patch-delay）**

```text
--patch-delay 45 : 有效 1 轮（life=110.2），d4 读到 0（补丁晚于帧处理）
--patch-delay 15 : 5 轮全部未达 110 s

  带 STUB 的轮次   life = 49.8 / 50.0     ← 稳定在 ~50 s
  未打补丁的轮次   life =  9.7 / 11.1 / 11.7
```

**(c) ⇒ 关键读数**

```text
打上补丁的轮次【稳定在 50 s 退出】，未打补丁的则是 10 s 级启动偶发。

⇒ 50 s 是【补丁导致的确定性行为】，不是随机波动。
⇒ 在 t = 15 s 写入补丁，会让进程在约 50 s 时退出；
   而在 t = 45 s 写入则不会（110 s 存活）。

⇒ 时机窗口是真实存在的：
     t ≈ 15 s  打补丁 → 50 s 退出（确定性）
     t ≈ 45 s  打补丁 → 存活到 110 s
```

**(d) 与旧结论的关系**

```text
旧的 §5.27.22 / 62 / 64 说"打补丁→9-11 s 崩溃"，已被 §5.27.90 的对照否证
（那是启动偶发，与补丁无关）。

但本节显示：补丁确实会改变存活时间，只是量级和方向不同 ——
  · 不是"打补丁就秒退"
  · 而是"过早打补丁 → 约 50 s 退出"
  · 45 s 之后打 → 正常
```

**(e) 下一步**

```text
要把桩用到帧处理那一刻（t≈38.9 s），补丁必须早于 38.9 s 写入；
但早于 ~45 s 又会导致 50 s 退出 —— 两者冲突。

需要找一个折中窗口：既早于帧处理，又不触发 50 s 退出。
候选：t = 38.0 s（帧处理前 ~1 s）。
若 38 s 也会 50 s 退出，则说明"任何早于 45 s 的写入都触发退出"，
桩方案不可行，需改用其它观测手段。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
