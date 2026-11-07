p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.64 ★★★★★ 0xBA3710 确认是 0x85 专属；但改它仍致启动崩溃（第十三轮）

**(a) 全镜像调用者分析（新增证据）**

```text
0xBA3710 的直接调用者：仅 1 个
  0x00BA46C2（位于 0xBA4430 分发器内，且入口判 opcode == 0x85）
0xBA3710 作为数据（跳转表）被引用：0 次
0xBA3600（0x89 分支）的直接调用者：仅 1 个（0xBA3B2A）
0xBA4430 作为数据被引用：0 次
```

⇒ **`0xBA3710` 是 0x85 专属代码，不存在"其它路径复用"的情况。**

**(b) 但实测仍然崩溃**

```text
IFS1_ELEVATED_20261002_021212
  4.191  PATCH_SRCBASE  pre9=53 post9=56  ok9=True   （已加严格门控：
         要求 0xBA3A8D 处 4 字节 == 52505153 且 0xBA3A96 处 == 83c418）
  4.192  PATCH_ARM      pre7=74d6 post7=9090 ok7=True
  8.864  PROCESS_END    exited=True exitcode=0xFFFFFFFF lifetime=8.9
```

⇒ 门控满足（说明写入的不是打包占位符）、补丁确实写入、
  但进程仍在 8.9 s 以 `0xFFFFFFFF` 退出。

**(c) ⇒ 结论：崩溃不是"代码被其它路径复用"，而是别的原因**

```text
可能：
  甲. .tp3 段存在运行时完整性校验（自校验/CRC），
      任何写入都会在稍后被检出并强制退出；
      —— 这也能解释为何 §5.27.11（改 0xBA3A2A）同样崩溃。
  乙. 该写入触发了 ACE 的代码段保护（历史实测的告警码 3/1023/61022）。
  丙. 写入位置虽在 0x85 处理器内，但该处理器在启动阶段
      也被"预初始化"调用（未被静态调用图捕获，例如通过函数指针数组的
      间接调用，而该数组是运行时构造的）。
```

**(d) 因此代码级路线在本环境【整体不可用】**

```text
已试并失败：
  · patch 0xBA3A2A（provider 判定）        → 10.4 s 崩溃  §5.27.11
  · patch 0xBA3A90（读取源基址）            → 12.2 s 崩溃  §5.27.62
  · patch 0xBA3A90（带严格门控）            →  8.9 s 崩溃  §5.27.64
  · BreakpointProbe 迟附加                  → ~3 s 崩溃   §5.27.6e
  · patch 0xC78212（cipher-init）           → 9–11 s 崩溃  §5.27.22（写 p604 那次）

⇒ 本环境对 .tp3 段的代码改写有强约束，
  任何写入都会导致进程在数秒内退出。
```

**(e) 剩余唯一可行路径：纯数据级（不改代码）**

```text
目标：让 0xBA3A91 读取时的源内容恰好给出 cl = 0x87。
需要先确定该处读取的源基址（0xBA3710 内 arg3 → ebx）在运行时的实际值，
以及该缓冲内容由谁写入。

观测手段（不改代码）：
  · 观察器已能读任意地址（ReadProcessMemory 在本环境对 .data 有效）
  · 需要一次"命中 0xBA3A99 时把 ebp 附近读出来"的采样，
    而 EIP 采样已证命中率不足（§5.27.10b）。
  ⇒ 因此该路径也需要新的观测手段，与代码级同样受限。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
