import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 32. 读入器缓冲区的原始内存快照（首次拿到）

给观察器加了对 `[req+0xB0]` 读入器对象的**整块 hex 转储**（`lobRdHex`）
及其缓冲区（`lobRdBufHex`），20ms 采样。运行 `IFS1_ELEVATED_20260928_204256`：

### 32.1 读入器对象（`lobRdHex`，0x40 字节）

```text
64 a3 d5 00   ; +0x00  vtable 0x00D5A364
02 00 00 00   ; +0x04  2
c6 00 00 00   ; +0x08  size = 0xC6 = 198 = 帧长度(200) - 2
57 e4 6e 3b   ; +0x0C  游标起点
57 e4 6e 3b   ; +0x10  读游标
57 e4 6e 3b   ; +0x14  写游标
01 01 00 00   ; +0x18=1  +0x19=1  +0x1A=0
38 e4 6e 3b   ; +0x1C  缓冲区基址 = 0x3B6EE438
fd 00 00 00   ; +0x20  分配量 0xFD = 253 = 198 + 0x37  ✓
01 00 00 00   ; +0x24  = 1   ← 不是 0x1F
18 00 00 00   ; +0x28  = 0x18
```

注意 **`+0x24 = 1`**，与 `0xB9BD40` 里写死的 `0x1F` 不同——说明这一
读入器不是走 `0xB9BEB0` 的默认路径建的，或后续被改写。而
`+0x0C - +0x1C = 0x1F`，说明游标起点 = 基址 + 31。

于是 `0xB9BBB0 = [+0x1C] - [+0x24] + 0x1F = 基址 - 1 + 31 = 基址 + 30`。

### 32.2 缓冲区内容（`lobRdBufHex`，基址 + 0）

```text
offset 0..24 : "3q297x0oMz5JVF9qdYCLlqGst"   ← 25 字节 ASCII
offset 25..28: c8 00 00 00                    ← u32 帧长度 = 200
offset 29    : 81                             ← 我们的 opcode
offset 30..  : 00 00 00 ...
```

**决定性发现：缓冲区不是一个干净的帧缓冲，前面塞了 25 字节的
ASCII 前缀，内容是 /auth/ 响应的 `client_ticket` 串开头。**

```text
/auth/ 响应里的 client_ticket:
  3q297xEWGyAlKi80OT5DSE1SV1xhZmtwdXp/hImOk5idoqessba7wMXKz9TZ3uPo...
读入器缓冲区前缀:
  3q297x0oMz5JVF9qdYCLlqGst
```

两者**前缀相同、后续不同** —— 说明这是从票据派生的密钥流/会话材料，
被当作帧的加密或混淆前缀使用。

### 32.3 由此定位 opcode 的偏移

```text
帧长度字段位置 = 缓冲区 offset 25
opcode 位置    = 缓冲区 offset 29   (= 长度字段 + 4)
0xB9BBB0 返回  = 缓冲区 offset 30
```

`0xB9BBB0` 取的是 offset 30，与 opcode(29) 差 1。结合 `+0x24 = 1`，
真实公式很可能是 `基址 + ([+0x24] 调整前的 31) - ([+0x24]=1) + ...`，
即该字段在运行期被改写，导致偏移整体后移 1。

**这是当前唯一未对齐的 1 字节。** 若要闭合，需要确认 `[reader+0x24]`
在构造之后的写入者。

### 32.4 状态

```text
第一档  未闭合，缺口缩小到 reader+0x24 的写入者（1 字节偏移）
第二档  未开始
```
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
