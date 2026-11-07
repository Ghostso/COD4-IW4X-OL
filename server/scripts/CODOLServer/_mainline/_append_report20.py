"""Append section 20 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 20. 推翻 §3.6：dispatcher 的真实形状与「握手后必死」的根因

本轮把 `[req+0x644]` / `[req+0x640]` / `[req+0x5E8]` 的全部访问点扫了出来，
结论是**手册第 3.6 节的分发表是错的**，而且 0x83 之后必死的根因不在 0x83。

### 20.1 真实的三分支判据是 `644`，不是 `5E8`

```asm
BA44E8  mov eax,[esi+0x5E8]        ; 只用于 BA44EE 的 cmp eax,1 一次
BA44EE  cmp eax,1
BA44F1  jne  BA454B
BA44F6  cmp al,0x81 / jne BA450C   ; 5E8==1: 只接受 0x81
BA450C  cmp al,4    -> 复位
BA454B  cmp eax,2 / jne BA46A2
BA4557  cmp al,0x83 / jne BA45F0   ; 5E8==2: 0x83 -> BA3BA0；0x84 -> BA0E20
BA46A2  cmp eax,3 / jne BA4781
BA46AE  cmp al,0x85                ; 5E8==3: 0x85 -> BA3710；0x84 -> BA0E20
```

即 `5E8` 只是「当前期望哪个 opcode」的过滤器。真正决定**下一步**的是
`BA4574: mov eax,[esi+0x644]`：

```text
0x83 校验通过 且 644 == 0 -> BA457E..BA45B2: call 0x7F9350（COM 赋值），[out]=4
0x83 校验通过 且 644 == 1 -> BA45DB: cmp eax,3 -> 否 -> BA4463: return 0
0x83 校验通过 且 644 == 3 -> BA45E4: call 0xBA3E20
```

**`644==1` 时 0x83 分支直接 `return 0`。** 这就是 31 ms 复位的入口：
返回 0 → 泵 `0xBA24C0` 侧放弃 → 复位。

### 20.2 但真正的「必死」在 0x83 之前：`0xC8` 魔数门

`0xBA3BA0` 的函数头有一条此前完全遗漏的守卫：

```asm
BA3B2A  call 0xBA3600              ; <- 由 opcode 0x89 / 0x87 触发

BA360D  cmp dword ptr [ebx+0x644], 1
BA3613  je  BA362F                 ; 必须恰好 644 == 1
BA3621  call 0xBA3420              ; ★ 否则直接复位（return 0）
BA362F  ... call 0xBA0FF0 ...
BA3651  mov dword ptr [ebx+0xC8], 1
BA3657  mov dword ptr [ebx+0x644], 2   ; ★ 644 = 2
BA3661  mov dword ptr [ebx+0x5E8], 0
BA366B  call 0xC73A20                  ; 重置读游标
```

而 `0xBA3590`（`644 != 0` 时的另一条 0x87 路径）里：

```asm
BA35D7  cmp dword ptr [esi+0x644], 0
BA35DE  jne BA35C3                 ; 644 != 0 -> 复位
BA35E2  call 0xBA3010              ; ★ 发 0xC8 魔数帧（644 必须 == 0）
BA35EB  mov dword ptr [esi+0x644], ebx   ; ebx = 1
```

`0xBA3010` 发出的帧内容（`0xBA319B..0xBA31F0`）：

```text
u32 0xC8
u32 0xC8
u32 0xD2
u32 0xDC
u32 0x08, u16 ?, u32 0xD4B1C7E9
8B at [edi+0x5F4]
```
（与探针实际收到的首个 28 字节**完全同形**，只是长度/尾部不同。）

### 20.3 被遗漏的门：`[req+0x640] >= 0xDC`

`0xBA3BA0` 里 opcode 0x87 / 0x89 的入口守卫（`0xBA3AE0` 区域）：

```asm
BA3AE6  cmp cl,0x87 / jne BA3B0E
BA3AEB  cmp dword ptr [edi+0x640], 0xDC
BA3AF5  jb  BA3B36                 ; ★ 0x640 < 0xDC -> 整帧被丢弃！
BA3B02  call 0xBA3590

BA3B0E  cmp cl,0x89 / jne BA3B36
BA3B13  cmp dword ptr [edi+0x640], 0xDC
BA3B1D  jb  BA3B36                 ; ★ 同样丢弃
BA3B2A  call 0xBA3600
```

`[req+0x640]` 的唯一非零写入点是 `0xBA3D53`（`0xBA3BA0` 内部）。
也就是说：**握手帧 `0x87`/`0x89` 只有在 `0xBA3BA0` 已经被调用过一次
（从而把 `0x640` 置为 `0xDC`）之后才会被处理。**

### 20.4 由此得到完整的真实协议（全部来自反汇编）

```text
0x81         -> 5E8=2            （已确证）
0x83         -> 5E8=3, 5EC=1, 5F0=1
              且 644==1 时 dispatcher 直接 return 0   <- 卡点
0x84         -> 经 0xBA0E20 调用 0xBA3BA0
                 首帧把 [req+0x640] 置 0xDC（=220）
                 此后 0x87/0x89 才被接受
0x89 + 640>=0xDC -> call 0xBA3600
                 要求 644==1 -> 置 C8=1, 644=2, 5E8=0, 重置读游标
0x87 + 640>=0xDC -> call 0xBA3590
                 要求 644==0 -> 发 0xC8 魔数帧, 置 644=1
```

**`0x640` 的实际取值 = 客户端在首帧里收到的 body 长度。**
探针目前发的是 `u32 frame_len = 0xC8 = 200`。若该长度被原样读入
`[req+0x640]`，则 `0xC8 (200) < 0xDC (220)` 始终成立，
`0x87`/`0x89` 永远被丢弃 —— 这正好解释「0x83 之后客户端无论如何都死」。

### 20.5 本轮待验证预测（优先级最高）

```text
把服务端帧的 u32 frame_len 从 0xC8 提到 >= 0xDC（例如 0xDC=220），
期望：
  a) [req+0x640] 从 0xC8 变成 >= 0xDC
  b) 客户端不再在 32 ms 内复位
  c) 0xBA3BA0 被 0x84 再次调用后，握手继续推进
注意：探针早期实验曾试过 --frame-len 196，方向相反，故无结论。
```

### 20.6 第一档状态（本轮更正）

```text
① 0x81                已闭合
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；新定位到 0x640>=0xDC 门与 644==1 直返两条边
⑤ 保活/持续           未闭合
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
