"""Append section 24 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 24. 32 ms 复位：排除超时，锁定「待发消息从未发出」

### 24.1 合帧实跑（`IFS1_ELEVATED_20260929_124635`）—— 证伪

把 `0x83 + 0x84 + 0x89` 合成**同一个 612 字节 TCP 段**一次 `sendall`
（`lobby_plain_probe.py` 已改：`--seq-after-83` 现与 0x83 同段发送）：

```text
37.389  s9c=4 5e8=3 5ec=1 5f0=1 640=220
37.391  POST83_SAMPLE  s9c=4 5e8=3 644=1
37.421  c8=4 5e8=0 644=0      <- 仍是 32 ms
```

**证伪**：`0x84`/`0x89` 即使与 0x83 同段到达，客户端也不处理它们。
它读完 0x83、置 `5E8=3`、`return 0`，然后直接放弃连接，
缓冲区里剩下的 0x84/0x89 从未被解析。

### 24.2 `[req+0xAE0]` 不是 32 ms —— 超时假设全部排除

```asm
BA29C3  fld  dword ptr [0xDBE6CC]
BA29CA  fstp dword ptr [esi+0xAE0]
```

`[0xDBE6CC] = 0x41F00000 = 30.0f`。`[req+0x508]` 的比较基
`[0xDE7C18]` 同样是 `30.0`。

→ 泵里两个时间分支（`BA2646` 比 30.0、`BA2670` 比 `[req+0xAE0]`=30.0）
**都是 30 秒上限**。32 ms 复位与超时无关。

### 24.3 决定性采样：`b8=0 c0=0 6d8=1`

给观察器 `POST83_SAMPLE` 增加 `[req+0xB8]`（待发链表头）、
`[req+0xC0]`（计数）、`[req+0x6D8]`（`0x6D0` 任务表计数）后实跑
（`IFS1_ELEVATED_20260929_125147`）：

```text
38.371  POST83_SAMPLE  s9c=4 5e8=3 644=1 a8=0 ac=200 b8=0 c0=0 6d8=1
38.401  POST83_SAMPLE  s9c=0 5e8=0 644=0 a8=0 ac=200 b8=0 c0=0 6d8=0
```

解读：

```text
[req+0xB8]=0 且 [req+0xC0]=0  -> 泵的 B8 链表是空的，
                                  所以 BA254D..BA26B9 那段（含 BA2625 复位）
                                  根本没有执行
[req+0x6D8]=1                 -> 0x6D0 任务表里有且仅有 1 条待发消息
复位后 6d8=0                   -> 由 0xBA3420（BA3497）清零
```

### 24.4 32 ms 复位的原因（收敛后的结论）

```text
客户端在 5E8=3 时手上已经有一条待发消息（6d8=1），
但 dispatcher 的 0x83 分支因为 644==1 走了 BA45DB -> BA4463
（return 0 = 未消费），泵随后调用 0xBA3420：
  清 C8=4 / 5E8=0 / 644=0，并把 6d8 清零（消息被丢弃）
```

即：**不是超时、不是缓冲区没数据、不是服务端关连接，
而是一条本应发出的消息被 644==1 卡住后随复位一起丢弃。**

`0x83` 处理器只读 `[req+0x644]`（`BA3C21`），不写它；`0xBA4080`
在连接建立时把它写成 `1`。因此 644 由 `1 -> 2/3` 只能靠
`0xBA32A0(arg)`：`arg=1` 只在 `0xBA3590`（opcode 0x87）与
`0xBA3E20`（644==3）路径里出现，两条都需要客户端先处理一个
`[req+0x640] >= 0xDC` 的入站帧 —— 而那个入站帧就是服务端要发的。

### 24.5 已确证 / 已证伪（累计到本轮）

```text
已确证
  [req+0x640] = 0x81 的 magic，域 [0xD2,0xDC]；只有 0xDC 开门（640=220 实跑）
  0x83 处理器只写 5E8=3 / 5EC=1 / 5F0=1，只读 644、640
  0xBA3420 = 复位原语：C8=4, 5E8=0, 644=0, 清 6d0/6d4/6d8, 清读游标
  32 ms 复位时 b8=0, c0=0, 6d8=1 -> 复位前有一条待发消息
  两个时间分支都是 30.0 秒

已证伪
  624 行 frame_len（0xC8/0xDC/196）影响握手
  0x84 / 0x89 单独或与 0x83 同段发送可以推进
  探针关连接导致复位
  644=0 是 dispatcher 所需（实为 644==1 时 0x83 分支 return 0）
  32 ms 是超时
```

### 24.6 第一档状态

```text
① 0x81                已闭合（魔数必须 0xDC）
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；阻塞点收敛为「644 必须从 1 走到 2 或 3」，
                        而这一步需要客户端先处理一条 640>=0xDC 的入站帧
⑤ 保活/持续           未闭合
```

### 24.7 下一步（唯一未试过的干净路径）

```text
不再覆盖 644，而是让 0x84 成为「同一次连接的第二个入站帧」且
在 0x83 之前先发 0x84（顺序：0x84, 0x83），使 0xBA3BA0 先被
0x84 调用一次（把 640 写到 0xDC 的入口已满足），再看 644 是否变化；
若仍不变，则需要在 0xBA3420 下断点式采样返回地址来确认调用者，
这需要比 SuspendThread+GetThreadContext 更快的观测手段。
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
