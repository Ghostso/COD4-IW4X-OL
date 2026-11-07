p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.62 ⚠️ 否证 §5.27.61(e) 甲：改 0xBA3A90 会破坏启动（第十二轮收官）

**(a) 实验**

```text
补丁：0xBA3A90  53 -> 56   （push ebx -> push esi）

结果（IFS1_ELEVATED_20261002_020244，4/4 尝试）
  4.468  PATCH_SRCBASE  pre9=53 post9=56  ok9=True    ← 补丁生效
  4.468  PATCH_ARM      pre7=74d6 post7=9090 ok7=True
  7.243  WINDOW_NEW     class=iipsinit
 12.175  PROCESS_END    exited=True  exitcode=0xFFFFFFFF  lifetime=12.2
```

⇒ 进程在 **iipsinit 阶段**（远早于 0x85 交互）即以 `0xFFFFFFFF` 退出。

**(b) ⇒ 结论**

```text
0xBA3A90 不是 0x85 专属的读取点；
它所在的代码路径【启动阶段也会经过】。
把源基址从 ebx 换成 esi，破坏了早期流程使用的同一段代码。
⇒ §5.27.61(e) 甲方案不可行，已回退（写入禁用，读取保留用于观测）。
```

**(c) 这与 §5.27.11 是同一类错误**

```text
§5.27.11：patch 0xBA3A2A（内层 provider 判定）→ 启动 10.4 s 崩溃
§5.27.62：patch 0xBA3A90（第三处读取源基址）→ 启动 12.2 s 崩溃

共同点：这两处都不是"只被大厅 0x85 使用"的站点，
       而是被多个阶段共用的通用代码。
⇒ 教训：对 0xBA3xxx 段内的站点做代码级修改前，
  必须先确认其调用者集合；仅凭"它在 0x85 处理函数体内"不足以下结论。
```

**(d) 仍然成立的结论**

```text
· 0xB783C0 的参数语义（arg1=源基址, arg3=源偏移, arg5=目标, arg6=长度）
· 三处调用的源基址差异（esi / esi / ebx）
· b0 != b4（POST83_SAMPLE 实测）
· cl != 0x87 ⇒ 0x87 arm 不进入 ⇒ 644 恒 0（§5.27.52 实验）
```

**(e) 剩余可行路径（只剩数据级）**

```text
甲. 确认 bufB（第三处读取的源基址）的内容由谁写入。
    若它是某个可被服务端流程影响的缓冲，
    则让内容在读取时恰好为 0x87 即可 —— 不动代码。

乙. 在 0xBA3A90 处不做指令替换，改为在【进入该调用前】
    把 ebx 的值临时改为 esi（需要写寄存器，属调试器手段，已否证）。

丙. 放宽边界、接受 ACE 告警，在 0xBA3A90 用
    "仅当调用栈来自 0x85 路径时才改写"的条件补丁
    （实现代价高，且 ACE 风险明确）。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
