"""Append section 26 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 26. 首帧闸假设的实跑检验：证伪

### 26.1 实跑（`IFS1_ELEVATED_20260929_125948`）

探针新增 `--seq-after-81`，把 `0x89` 与 `0x81` 放在**同一次 sendall**
（客户端处理 0x81 时 `[req+0x5EC]` 仍为 0，理论上应能通过首帧闸）：

```text
sent_81  len=204  pre_len=204  pre="c8 00 00 00 00 89 ..."
37.289  c8=2 5e8=1                     <- 0x81 通过
37.352  c8=2 5e8=2                     <- 0x81 完成
sent_83  (probe 在收到 0x82 后发出)
37.384  c8=4 5e8=0                     <- 复位；从未出现 5e8=3
RST 26 ms 后
```

**证伪**：`0x89` 与 `0x81` 同段后，`0x83` **再也没有成功**
（`5e8` 从未到 3）。首帧闸理论在运行期不成立 —— 说明
`0x89` 不是在 0x81 之后立刻被处理的，或者它本身把状态带偏。

### 26.2 累计证伪清单（第一档第 ④ 步）

```text
1  frame_len 0xC8 / 0xDC / 196 影响握手
2  0x84 单独 / 分离发送
3  0x85 全零 / 内嵌 0x89 + 0xBA02A0 tag
4  644 写 0 / 写 3
5  4 字节全零保活
6  0x83+0x84+0x89 同段发送
7  0x84+0x89 分两次发送（间隔 30ms）
8  0x89 与 0x81 同段（本轮）
9  外部覆盖 [req+0x644]
10 magic 0xD2（0x640 门未开）
11 探针关连接导致复位
12 32ms 是超时
```

### 26.3 本轮唯一仍成立的正面结论

```text
magic 必须 0xDC —— [req+0x640]=220 已实跑确证，
且 0x87/0x89 的门 (640>=0xDC) 只在 0xDC 时打开。
这是第一档目前唯一「已知为真且必需」的新条件。

[req+0x5EC]：唯一写入点 = 0x83 成功(=1)；大分发器首帧闸要求其旧值为 0。
0x83 之后客户端不再处理任何入站帧 —— 该现象已被两次不同实验证实
（同段发送、先发 0x89 都救不回来）。
```

### 26.4 第一档状态

```text
① 0x81                已闭合（魔数必须 0xDC）
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；阻塞点 = 0x83 成功后 [req+0x644] 停在 1，
                        0x83 分支 return 0 -> 复位；而 644 的后续值
                        只能由「客户端处理入站 0x87/0x89」产生，
                        该处理路径与 0x83 互斥
⑤ 保活/持续           未闭合
```

### 26.5 接手建议（按性价比）

```text
1. 不要再猜「补发哪个帧」。先解决观测：需要拿到 0xBA3420 的调用者。
   现有 EIP 采样太慢（SuspendThread+GetThreadContext）；可考虑
   在 0xBA3420 入口做 code-cave 式记录（属改 .text，超出当前安全边界），
   或在 0xBA4440 的返回处采样 al。
2. 客户端真实首帧是 200 字节；把 200 字节内容整体取回并解码，
   很可能直接给出 0x87/0x89 的正确顺序与 body 语义。
3. magic 0xDC 这个新条件必须保留在所有后续实验里。
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
