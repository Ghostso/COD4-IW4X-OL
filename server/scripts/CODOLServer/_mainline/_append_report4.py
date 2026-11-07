import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 23. 服务端应答：类型字节语义与「只接受一帧」特性

### 23.1 发包侧已定位

`0xBA2F20` 是发送路径：

```asm
00BA2F4A  push 0x1c ; call 0xB74220     ; 分配 0x1c 字节的消息对象
00BA2F6B  call 0x4F3F60                 ; 序列化到该对象
00BA2FA6  call 0xBA0EB0                 ; 构造临时位写入器(ebp-0x28)
00BA2FC0  call 0xBA1720                 ; 入队: ([edi+0xb8], [edi+0xbc], tmp)
00BA2FC7  call 0xBA24C0                 ; pump
```

即 `[obj+0xB8]` 是**发送队列**，帧内容同样由 5 位写入器生成。客户端首帧
那 28 字节就是这条路径产出的。

### 23.2 收帧类型字节决定帧头长度，且值 2 会被拒绝

`0xBA20A0` 读 1 字节后：

```asm
00BA20E9  mov al, byte ptr [edi]     ; 从连接读到的类型字节
00BA20F0  cmp al, 1
00BA20F4  cmp al, 2
00BA20F8  mov ebx, 9                 ; 1/2 -> 帧头 9 字节
                                     ; 其它 -> 帧头 1 字节
```

实测对照：

| 应答帧首字节（长度字段之后） | 客户端反应 |
|---|---|
| `0xC8`（非 1/2） | **接受**，推进到 `sub-state 3`，`uA50` 可达 5 |
| `0x02` | **立即拒绝**：`t=37.198 reqC8=4`、`conn+0xC4=-1`、连接关闭 |
| 3 份帧连续发（612B） | **失败**：`DW_LOBBY_ERROR`，握手在第 3 阶段断掉 |

结论：

1. 类型字节必须**不是 1 或 2**，或必须是内容正确的 1/2——值 2 配零填充
   会被判定非法。
2. 客户端**只接受一帧**。多发一帧、或事先塞多帧，都会破坏握手。

### 23.3 目前唯一可复现的可用配置

```text
单次回送 204 字节：
  u32 长度 = 200
  负载 200 字节，首字节 0xC8，余下为零
=> uA50 走到 5（DWLOBBY_PUMP_SUCCESS）
=> 约 50 秒后仍弹「与大厅服务失去连接」
```

### 23.4 排除的路径

```text
周期重发同一帧 (--repeat-every 2)   -> 握手在第 3 阶段失败
一次性多发多帧 (3 x 204B)            -> 握手在第 3 阶段失败
类型字节 = 2                         -> 立即断连
```

说明保活与应答都必须是**内容语义正确**的帧，而不是靠数量或节奏凑。

### 23.5 下一步

需要还原 5 位字段语义。已定位可用的三个抓手：

```text
0x00BA0EB0   构造发送用位写入器
0x00BA1720   把位写入器结果入发送队列 ([obj+0xb8])
0x00BA20A0   收帧解析；后续由 0x00BA0FF0 / 0x00BA12E0 消费负载
0x00B78350   位写入原语(dst, bitOffset, src, bitCount)
0x00B9BEB0   位读取器构造(size, ...)
```

建议下一步在 `0x00BA20A0` 解析成功分支上打断点/加探针，读出
`[req+0xB4]` 指向对象的实际字段值，据此反推应答所需的 5 位字段。
"""

s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
