"""Append section 25 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 25. 找到「0x83 之后再也吃不下任何帧」的真因：`[req+0x5EC]` 首帧闸

### 25.1 大分发器（含 0x87/0x89 分支）的首帧闸

`0xBA3AE0`（0x87/0x89 分支）属于一个很大的帧分发函数，其首帧判定在
`0xBA3840`：

```asm
BA3840  test bl,bl
BA3842  je   BA3867                ; bl=0 -> 失败
BA3844  mov  eax, dword ptr [edi+0x5EC]
BA384A  lea  edx,[eax+1]
BA384D  mov  [edi+0x5EC], edx      ; ★ 自增
BA3853  cmp  [ebp-0x394], eax      ; [ebp-0x394] 在 BA3A1E 被置 0
BA3859  je   BA38A4                ; 旧值==0 -> 继续处理这一帧
BA385B  xor  bl,bl
BA385D  mov  [ebp-0x398], 0xD5A520
BA387D  mov  ecx,edi
BA387F  call 0xBA3420              ; ★ 否则复位
```

`[req+0x5EC]` 的全部访问点：

```text
00BA3844  读  (就是上面这条首帧闸)
00BA3C3B  写 1   <- 0x83 处理器成功路径 (BA3C38 mov [esi+5EC], ebx)
```

**即：`5EC` 只有一处写 = `0x83` 成功时置 1。**
而首帧闸要求「读到 `5EC` 后，旧值必须 == 0」。

### 25.2 由此得到的硬结论

```text
0x83 成功 -> [req+0x5EC] = 1
之后大分发器每读一帧 -> [req+0x5EC] 变 2、旧值 1 != 0 -> 复位
=> 0x83 一旦成功，客户端就再也无法处理任何后续入站帧
```

这解释了本轮全部实测：

```text
0x84/0x89 单独发      -> 被首帧闸挡下 -> 32ms 复位
0x84+0x89 与 0x83 同段 -> 同上（0x83 已把 5EC 置 1）
0x83 之后 25s 无字节   -> 同上
```

**所以问题不是「续帧发得太晚」，而是 0x83 一旦被成功处理就关闭了
自己的入站通道。** 之前所有「补发 0x84/0x85/0x89」的实验注定失败。

### 25.3 644 的完整写入表（据全镜像扫描）

```text
00BA299C  mov [esi+0x644], ebx(=0)   构造/重置
00BA3E5D  mov [ebx+0x644], 0         0xBA3E20（644==3 分支）
00BA346A  mov [esi+0x644], 0         0xBA3420 复位
00BA35EB  mov [esi+0x644], ebx(=1)   0xBA3590 发完 0xC8 帧之后
00BA3657  mov [ebx+0x644], 2         0xBA3600（opcode 0x89 路径）
00BA325E  mov [edi+0x644], 3         0xBA31F0 内，C8==2 且 644!=0
(0xBA4080 的 BA412D 写 1 —— 连接建立时)
```

从 1 出发只有两条出路：

```text
1 -> 2   需要 0xBA3600 被调用 = 需要客户端处理 opcode 0x89
1 -> 3   需要 0xBA31F0 被调用（其内要求 C8==2 且 644!=0），
         该函数由 opcode 0x88 的 0xBA2F50 分支进入
两者都在大分发器里 —— 而大分发器已被 0x83 关闭（§25.1）
```

### 25.4 下一轮的第一个动作（据此改）

```text
把 0x89 放进**服务端发出的第一帧**（与 0x81 同一个帧体内），
使其在 5EC 尚为 0 的那一次分发里被处理；
或者先让客户端跑完 0x89 路径（644=2）再进入 0x81/0x83。
验证判据：POST83 之外新增一条 c8/644 变化记录，
特别是 644 出现 2，或 c8 由 2 变 1。
```

### 25.5 第一档状态

```text
① 0x81                已闭合（魔数必须 0xDC）
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；真因 = 0x83 成功即关闭入站通道(5EC=1)，
                        因此 0x89/0x87 必须排在首帧之前/之内
⑤ 保活/持续           未闭合
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
