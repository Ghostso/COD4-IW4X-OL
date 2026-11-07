import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
add = """

---

## 33. 缓冲区数学定死：类型字节 = body[0]，opcode = body[1]

第 32 节缓冲区快照（基址 = 0x3B6EE438），逐字节：

```text
缓冲区索引  0..24 : "3q297x0oMz5JVF9qdYCLlqGst"   25 字节 ASCII 前缀
缓冲区索引 25..28 : c8 00 00 00                     u32 长度 = 200
缓冲区索引 29     : 81                               <- body[0]
缓冲区索引 30     : 00                               <- body[1]
```

`0xB9BB90` 是唯一写 `[reader+0x24]` 的地方：

```asm
00B9BB90  mov eax, [ebp+8]
00B9BB99  cmp eax, 0x1F / mov eax, 0x1F
00B9BBA0  mov [ecx+0x24], eax          ; = min(n, 0x1F)
```

调用点 `0xBA21E4`：`push ebx(=1) ; call 0xB9BB90`，于是 `[reader+0x24] = 1`，
而 `0xB9BBB0 = 基址 - 1 + 0x1F = 基址 + 30` → 缓冲区索引 30 = **body[1]**。

**结论：类型字节 = body[0]；分发 opcode = body[1]。**

（第 30 节的"opcode 在 body[0]"与"在 body 偏移 5"两个说法均作废。）

### 33.1 已验证事实

`[req+0xA8]` 低字节在五次独立运行中都等于 body[0]：

```text
body[0]=0x81 -> a8 低字节 0x81
body[0]=0xC8 -> a8 低字节 0xC8
body[0]=0x00 -> a8 低字节 0x00   （三次）
```

### 33.2 仍失败的一步

run `IFS1_ELEVATED_20260928_210836`（body[0]=0x00, body[1]=0x81）：

```text
t=37.411  C8=1  5e8=0  644=0
t=37.443  C8=2  5e8=1  644=1
t=37.474  C8=4  5e8=0  644=0     <- 未到 5e8=2
```

连接建立、`5e8` 进入 1，但 0x81 处理器未执行（`5e8` 未变 2）。
按本节布局该帧应当命中，说明**除偏移外还有前置条件未满足**
（候选：前缀长度须与票据一致；或 0x81 帧的 4 个字段须同时合法）。

### 33.3 未采到的样本（方法层面的结论）

扫描全部历史运行，**没有一份是在 `C8==2` 时采到 `lobRdBufHex` 的**——
读入器从建立到失败约 30ms，快于 20ms 采样的稳定捕获。要定死填充过程，
必须把采样压进帧处理窗口内，或改为在 `0xBA20A0` 入口/出口成对采样。

在此之前，继续用"静态值推运行偏移"的方式猜测不会收敛：本函数上已
发生四次推断被采样推翻（第 28.5、31、32 节及 body[1] 实验）。
"""
open(p, "a", encoding="utf-8", newline="\n").write(add)
print("ok")
