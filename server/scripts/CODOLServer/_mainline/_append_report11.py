import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 30. 类型字节偏移已锁定；opcode 偏移仍未定

### 30.1 已确认：`[req+0xA8]` = 长度前缀之后的第一字节

`0xBA20A0` 开头就是一次**单字节 recv**：

```asm
00BA20CA  push 1
00BA20CC  lea edi, [esi+0xA8]
00BA20D2  push edi
00BA20D3  lea ecx, [esi+0xC4]
00BA20D9  call 0xC73A00        ; recv(conn, &[req+0xA8], 1)
00BA20DE  mov [ebp-0x1c], eax
00BA20E1  test eax, eax
00BA20E3  jle 0xBA2289
00BA20E9  mov al, byte ptr [edi]   ; al = 该字节
00BA20F0  cmp al, 1
00BA20F4  cmp al, 2
00BA20F8  mov ebx, 9               ; 1/2 -> 帧头 9 字节；其它 -> 1 字节
```

而 `0xBA3FB0` 在此之前已读过 4 字节长度。所以帧布局为：

```text
u32 frame_len | u8 type | ...
```

四次独立运行验证（`[req+0xA8]` 视为 u32 时只有低字节有意义）：

```text
body[0]=0x00 -> a8=0x060D0000  低字节 0x00  ✓
body[0]=0x81 -> a8=0x00000081  低字节 0x81  ✓
body[0]=0xC8 -> a8=0x000000C8  低字节 0xC8  ✓
body[0]=0x00 -> a8=0x060D0000  低字节 0x00  ✓
```

### 30.2 已确认：type ∈ {1,2} 会导致失败

```text
type = 0x02  -> ebx=9 -> 立即 RST，C8 掉到 4
type = 0xC8 / 0x81 / 0x00 -> ebx=1 -> 连接保持，C8 稳定为 2
```

### 30.3 仍未定：分发器读 opcode 的偏移

`0xBA4440` 用 `edi = [req+0xAC] - 1` 作为偏移（`0xBA44B8/0xBA44CA`）。
用 `frame_len = 204`（含 4 字节前缀）并把 `0x81` 放在 body 末字节（offset 199）
测试，`5e8` **仍停在 1**，opcode 未被识别。

即该偏移相对哪个缓冲、以及 `frame_len` 是"含前缀"还是"不含"，仍需一步定位。

### 30.4 结论

```text
0x81 / 0x83 / 0x85 处理器     已完整逆向（第 29 节）
帧布局 u32 len | u8 type       已确认
type 字节取值规则              已确认
分发器 opcode 偏移             未定  <-- 当前唯一卡点
opcode 处理器是否被执行过      从未（5e8 在所有运行中都停在第 1 步）
```

**第一档仍未闭合**：`[req+0x5E8]` 在所有实跑里都没有从 1 前进过，说明
握手第一步（0x81）从未真正被分发器执行。第二档因此尚未开始。
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
