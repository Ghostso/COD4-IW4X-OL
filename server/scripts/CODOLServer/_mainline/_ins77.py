p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.77 ★★★★★★ 用观察器实测判定：静态推演确认有误（第十四轮）

**(a) 判定原理**

```asm
0xBA3840  test bl, bl
0xBA3842  je  0xBA3867            ; ★ bl == 0 → 跳到失败出口
0xBA3844  mov eax, [edi+0x5EC]
0xBA384A  lea edx, [eax+1]
0xBA384D  mov [edi+0x5EC], edx    ; ★★ 仅当 bl != 0 才执行
0xBA3853  cmp [ebp-0x394], eax    ; seq 门
0xBA3859  je  0xBA38A4
0xBA385B  xor bl, bl              ; seq 不匹配 → 失败出口
0xBA3867  （失败出口：0x8435D0 + 0x4F7940 + call 0xBA3420 复位）
```

⇒ **`[edi+0x5EC]`（收包计数）是否递增，
   直接等价于 `bl` 是否非 0。**

**(b) 实测数据（POST83_SAMPLE，已同时含 ac/b0/b4/5ec）**

```text
t=39.104  ac=0    b0=0          5ec=1
t=39.159  ac=382  b0=1000265248 5ec=2      ← 收到帧
t=39.186  ac=382  b0=1000264624 5ec=3      ← ★ 递增
t=39.220  ac=382  b0=1000265456 5ec=4      ← ★ 递增
t=39.263  ac=0    b0=0          5ec=4      ← 处理完
t=86.005  ac=382  b0=1000266704 5ec=5
t=86.023  ac=382  b0=1000267432 5ec=6
t=86.051  ac=382  b0=1000266496 5ec=7
t=86.066  ac=0    b0=0          5ec=7
```

⇒ **`5ec` 确实递增（1→2→3→4、5→6→7）**
⇒ **`bl != 0`**
⇒ **§5.27.70 / §5.27.74 的"0xBA3A5D 的 ja 恒成立 ⇒ cl 恒 0"推演【错误】**

**(c) 附带确认**

```text
· b0 每次都不同（1000265248 / 1000264624 / 1000265456）
  ⇒ 每帧重新分配缓冲，不是复用同一块
· ac 在 382 ↔ 0 之间循环，与 §5.27.65 一致
· 两组递增分别发生在 t≈39.2（我们发帧后）与 t≈86.0
```

**(d) 意义**

```text
本轮之前，我一直把"静态推演与事实矛盾"记为待解疑点（§5.27.75）。
现在用观察器【已有】的数据（无需新实验）判定：
  矛盾的责任在【静态推演】，不在观测。

⇒ 说明我对 0xBA3710 内层控制流的理解仍有缺口，
  但缺口位置可以继续用同一方法（读已采样的 obj 字段）缩小。
```

**(e) 下一步**

```text
`bl` 由 0xBA37E9 / 0xBA380F / 0xBA3828 三处共同决定，
其中：
  0xBA37E9  test cl, cl        （cl 来自 0xBA3794 那次读取的结果）
  0xBA37ED  cmp ebx, 8
  0xBA380F  test bl, bl
  0xBA3813  cmp eax, edx       （eax/edx 均为地址）
  0xBA381B  test cl, 0xf       （16 字节对齐检查）
  0xBA3820  cmp ecx, 0xFFFFFF

⇒ 这些条件都依赖 0xBA3794 那次读取的返回值与地址；
  而这些地址（b0 等）观察器已经在采。
  下一步：用 b0 的逐帧变化 + ac 的值，反推 0xBA3794 的返回是否成功，
  从而定位我推演中出错的那一项。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
