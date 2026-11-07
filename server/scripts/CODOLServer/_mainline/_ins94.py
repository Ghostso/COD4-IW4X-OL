p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.94 ★★★★★★ 桩方案跑通：cl 走的是"读取失败"分支（第十五轮，决定性）

**(a) 桩的最终形态**

```text
落点：obj+0x5E0
  依据：全镜像扫描显示该字节只有 1 处写入（0xBA2950）、0 处读取
        —— 是纯占位字节，写它不会破坏任何逻辑。
  （先前选 obj+0x6D4 是错误：那是 4 字节指针字段，
    被字节写入污染后导致 0xC0000005。）

两处等长 6 字节替换（无需跳转）：
  0xBA3AA3  88 95 77FCFFFF  ->  88 9F E0050000   mov [edi+0x5E0], bl
  0xBA3AE0  8A 8D 77FCFFFF  ->  8A 8F E0050000   mov cl, [edi+0x5E0]
补丁确认生效：okB=True / okC=True
```

**(b) 时序安排（关键）**

```text
--patch-delay 42   ：补丁在 42.0 s 写入（早于此会触发 ~50 s 退出）
--serve-delay 30   ：探针延迟 30 s 握手，使客户端的帧处理整体后移

实测时序：
  42.007 s  PATCH_DISPATCH_STUB  okB=True okC=True
  68.844 s  POST83_WATCH_START（5e8=3）
  69.025 s  FRAMEBUF  ac=382      ← 帧已收到，正在处理
  ⇒ 补丁【早于】帧处理，时序冲突已解决
```

**(c) 决定性读数**

```text
该轮 d4（= obj+0x5E0）在全部 FRAMEBUF 采样中均为 0，
包括帧处理那一刻（69.025 s，ac=382）。

⇒ 0xBA3AA3（mov [edi+0x5E0], bl）【没有被执行】。
⇒ 执行流走的是 0xBA3AAD 的 `xor cl, cl`。
⇒ 即：0xBA3A99 的 `test al, al` 判定为【假】，
   0xBA3A9B 的 `je 0xBA3AAD` 被采用。
⇒ al 来自 0xBA3A45 那次 4 字节读取（0xB783C0 的返回值）。
⇒ ★ 0xBA3A45 的读取【失败】。
```

**(d) 因此 cl 的来源已确定**

```text
cl = 0（由 0xBA3AAD 的 xor cl,cl 写入）
   ← 因为 0xBA3A45 的 4 字节读取失败
   ← 因为 0xB783C0 的边界判据不满足：
        arg3 <= arg2  且  arg3+arg6 <= arg2
   其中（0xBA3A2C 处）：
        arg2 = [ebp-0x39C]
        arg3 = ecx = [ebp-0x3A4]
        arg6 = 4

⇒ 与 §5.27.79 的静态推演一致（当时被误判为"ja 恒成立"），
  现在有了运行时证据：失败发生在【更早的 0xBA3A45】那一步，
  而不是 0xBA3A5F 的 ja。
```

**(e) 本轮的完整链条**

```text
1. 用户放宽边界（仅保留"不得改本机网络"）
2. 发现"补丁致崩"是误判 → §5.27.90 对照否证 4 条旧结论
3. 全套补丁生效后 644 仍恒 0 → §5.27.91
4. 造"分发字节落点桩"（等长替换，无需跳板）→ §5.27.92
5. 测出补丁时机窗口：38 s 失败 / 42 s 成功 → §5.27.93
6. 用 --serve-delay 把帧处理推到补丁之后 → 时序冲突解决
7. ★ 桩读数全 0 ⇒ cl 出自"读取失败"分支 ⇒ 失败点是 0xBA3A45
```

**(f) 下一步**

```text
现在可以确定地放宽 0xBA3A45 的边界判据：
  · 或直接 NOP 掉 0xBA3A4F 的 je（让 al 恒为 1，强行继续）
  · 或修正 arg2/arg3 的取值来源
并同步读取桩，观察 cl 是否变为 0x87。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
