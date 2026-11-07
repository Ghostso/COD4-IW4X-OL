p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.71 ⚠️ 否证 §5.27.70(d)：改长度字段会立即破坏帧解析（第十三轮收官）

**(a) 实验**

```text
探针新增 --reply-85-len-field <n>，只覆盖帧内的 u32 长度字段，
不改动实际发出的字节数（仍为 386）。

IFS1_ELEVATED_20261002_022808，--reply-85-len-field 4

  1790879328.077  sent_85        len=772
  1790879328.078  hold_recv      386      ← 客户端仍回 seq=1
  1790879328.078  reply_85_cbc   hex = 04 00 00 00 00 85 01 00 00 00 ...   ★ 字段已改
  1790879328.124  hold_recv_error          ← ★ 46 ms 后连接出错

  644 全程 = 0
  85.9 s 仍弹"与致命错误/与大厅服务失去连接"
  170 s 观察器到期主动终止
```

**(b) ⇒ 结论**

```text
客户端是【按长度字段切分帧】的。
把 382 改成 4 之后，客户端只取走 4+4 = 8 字节就当做一个完整帧处理，
剩下的 378 字节被当成后续帧的开头 → 解析立刻失败 → 连接出错。
⇒ frame_len 字段不能独立于实际帧长修改。
```

**(c) 那么 §5.27.70 的算术结论仍然成立，但修法要换**

```text
仍然成立：
  0xBA3AC2 要求  frame_len + 游标 <= obj+0xAC
  我们发 382 时该式为  382 + 游标 <= 382，游标 > 0 ⇒ 失败

但"改小 frame_len"会破坏切分 ⇒ 必须换思路：
  甲. 让 obj+0xAC 变大（客户端侧状态，服务端不可控）
  乙. 让游标 <= 0（游标由客户端内部逻辑决定，服务端不可控）
  丙. 不再试图让 arm 成功，而是接受该判定，
      改由其它方式推进（例如让 0x89 分支在 644 == 0 时也能被受理）
```

**(d) 由 (c) 丙 引出的新观察**

```text
0xBA3B0E  cmp cl, 0x89        ; 0x89 分支
0xBA3B13  cmp [edi+0x640], 0xDC
0xBA3B1F  ...
0xBA3B2A  call 0xBA3600
而 0xBA3600 又要求 [obj+0x644] == 1（§5.27.9）

⇒ 0x89 分支同样以 644 == 1 为前提，没有旁路。
   而 644 只能由 0xBA35EB（arm 成功）写入。
⇒ 除非能改变客户端对"长度匹配"的判定，否则 644 无解。
```

**(e) 第一档⑤的最终状态（第十三轮末）**

```text
失败点的算术表述已确定：
  frame_len + 游标 > obj+0xAC   （恒成立，因为 frame_len == obj+0xAC == 382）

该式两侧都由【协议约定】决定：
  · frame_len 必须等于实际帧长（否则切分错位，§5.27.71b）
  · obj+0xAC 是客户端记录的本帧长度
⇒ 服务端无法在保持协议一致的前提下让该式成立。
⇒ 第一档⑤在当前协议理解下【不可闭合】，
   除非发现"合法帧长应当更小"这类协议细节。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
