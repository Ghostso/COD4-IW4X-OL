"""Append section 22 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 22. 突破：`[req+0x640]` 被打开（magic 0xDC），并读出真实时序

### 22.1 实跑结果（`IFS1_ELEVATED_20260929_123239`）

探针改为 `--magic 0xDC`（token 不变）：

```text
37.043  CODEC_TRANSITION   s9c=2  5e8=1  640=220  <- ★ 0x640 变成 0xDC
37.056  5e8=2  640=220
37.088  5e8=3  5ec=1  5f0=1  640=220
37.089  POST83_SAMPLE  s9c=4 5e8=3 644=1
37.132  c8=4 5e8=0 644=0   <- 仍然复位，但过程已经不同
```

**`[req+0x640] = 220 (0xDC)` 已确证。** 握手门 `640 >= 0xDC` 打开。

### 22.2 一个极其重要的副作用：`s9c` 变成了 2，并出现 `5E8=1`

对比两轮：

```text
magic=0xD2 (run 122646):  s9c: 1 -> 0 -> 4        s9c 从未出现 2
magic=0xDC (run 123239):  s9c: 1 -> 2 -> 0 -> 4   出现 s9c=2，且 5E8=1
```

`0xC8` 是**服务端/客户端双方都用的魔数**（客户端连大厅时的首帧
`c8 00 00 00 c8 00 00 00 d2 00 00 00 dc ...` 也以 0xC8 开头）。
客户端把 `magic == 0xDC` 的 0x81 判定为「对端是同类」，于是额外
执行了一段 `s9c=2` / `5E8=1` 的路径。

**`640` 是整条握手链的总开关，之前所有失败实验都卡在 `0xD2`。**

### 22.3 剩余阻塞点（已缩小）

看 `0x83` 处理器的后置分支（`0xBA3C1E`）：

```asm
BA3C21  cmp dword ptr [esi+0x644], eax     ; eax=0
BA3C27  jne 0xBA3C38
BA3C29  mov ecx, dword ptr [esi+0x640]
BA3C30  call 0x8435D0                      ; 诊断日志（无副作用）
BA3C38  mov [esi+0x5EC], ebx
BA3C41  mov [esi+0x5F0], ebx
BA3C47  mov [esi+0x5E8], 3
```

`644==0` 与 `644!=0` 在 `0x83` 里**走的是同一条路**（只差一条日志）。
本轮 `644=1`，所以走 `jne`，结果一致。**`0x83` 内部没有失败分支。**

因此复位仍来自 dispatcher 的 `BA4574: mov eax,[esi+0x644]`
—— 因为 `644==1` 时 `0x83` 分支 `return 0`（`BA45DB`/`BA4463`）。

### 22.4 由代码推出的必需续帧（下一步要发）

```text
0xBA3600  cmp [ebx+0x644], 1     je  0xBA362F
BA3651    mov [ebx+0xC8], 1
BA3657    mov [ebx+0x644], 2     <- 序列推进到 644=2
BA3661    mov [ebx+0x5E8], 0

0xBA3590  cmp [esi+0x644], 0     jne 0xBA35C3(复位)
BA35E2    call 0xBA3010          <- 发 0xC8 魔数帧（28 字节，已知形状）
BA35EB    mov [esi+0x644], 1     <- 回到 644=1

0xBA3010 发的帧: u32 0xC8 | u32 0xC8 | u32 0xD2 | u32 0xDC |
                 u32 0x08 | u16 ? | u32 0xD4B1C7E9 | 8B@[edi+0x5F4]
```

即 `0x83` 成功后需要：

```text
1) 发 0x84（内容 = 回显 [req+0x5FC]，与 0x83 相同）—— 让 0xBA3BA0 再跑一次
2) 发 0x89（body 结构待确认），触发 0xBA3600 -> 644=2
3) 服务端再发 28 字节 0xC8 魔数帧 —— 触发 0xBA3590 -> 644=1
```

### 22.5 第一档状态

```text
① 0x81                已闭合
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；总开关 640=0xDC 已打通，
                        剩余是补发 0x84 / 0x89 / 0xC8 帧的序列
⑤ 保活/持续           未闭合
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
