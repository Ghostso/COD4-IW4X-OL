p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.95 实验：NOP 掉三道 je 后 cl 仍为 0 —— 流程在更早处跳出（第十五轮）

**(a) 新 NOP 的三道守卫**

```text
0xBA3A4F  74 14  je 0xBA3A65   ->  90 90
0xBA3A70  74 3B  je 0xBA3AAD   ->  90 90
0xBA3A9B  74 10  je 0xBA3AAD   ->  90 90
（连同此前的 0xBA3A5F  77 04 ja -> 90 90）
```

补丁确认生效（`PATCH_GUARDS` 事件，`okE=True / okF=True`）。

**(b) 结果**

```text
有效轮次（life 76-79 s）：
  FRAMEBUF 的 d4 取值 = [0]
  POST83_SAMPLE 的 644 取值 = [0]

⇒ 三道 je 全部 NOP 后，obj+0x5E0 仍为 0
⇒ 0xBA3AA3（mov [edi+0x5E0], bl）依然没有被执行
```

**(c) ⇒ 推论**

```text
0xBA3AA3 位于 0xBA3A6E → 0xBA3A70 → 0xBA3A91 → 0xBA3A9B → 0xBA3A9D 之后。
把这四道分支全部门控打开后仍到达不了，
⇒ 说明执行流【根本没有进入 0xBA3A2C 那一段】。

⇒ 跳出点在更早处，候选：
    · 0xBA3A2A  74 39  je 0xBA3A65     ← --patch-85-pass 已处理？
    · 0xBA3A28  84 C0  test al,al
    · 0xBA39E2  jmp 0xBA3867
    · 或 0xBA3842 的 je（bl 判定）
    · 或 0xBA3987 的 je（已 NOP）
```

**(d) 下一步**

```text
用一个"更靠前"的桩来定位真实执行流：
  把桩从 0xBA3AA3 前移到 0xBA3A18（mov [ebp-0x390], ecx）
  或 0xBA39E7 处，记录流程是否到达 0xBA3A 段。

更简单：既然 obj+0x5E0 空闲，可以先在 0xBA39E7
（provider 调用前的固定点）写一个标记，确认流程是否进入该函数尾部。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
