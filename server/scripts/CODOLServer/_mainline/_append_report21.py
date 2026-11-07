"""Append section 21 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 21. `[req+0x640]` 解密：它就是 0x81 的魔数，只有 `0xDC` 才能开门

### 21.1 17 行 `0x83` 处理器（`0xBA3BA0`）

```asm
BA3BA0  ; 参数: [ebp+8]=buf, [ebp+0xC]=rd?, [ebp+0x10]=len
BA3BBD  ecx = buf+1                ; 跳过 type 字节
BA3BCD  call 0xB783C0(..., 8)      ; 读 8 字节 -> [ebp-0xC]
BA3BD5  test al,al / jne BA3C05
BA3BE0  push 4 / call 0x4F7940     ; 错误 0x04 -> 复位

BA3C05  push 8
BA3C0B  lea eax,[esi+0x5FC]
BA3C12  call 0xB73FE0              ; memcmp(this+0x5FC, recv8, 8)
BA3C1A  test eax,eax / jne BA3C62  ; 不等 -> 错误 0x03 -> 复位

BA3C1E  lea ebx,[eax+1]            ; ebx = 1
BA3C21  cmp [esi+0x644], eax       ; 与 0 比较
BA3C27  jne BA3C38
BA3C29  mov ecx,[esi+0x640]        ; 只是把 0x640 传进去打日志
BA3C30  call 0x8435D0              ; ★ 纯诊断，无副作用
BA3C38  mov [esi+0x5EC], ebx       ; = 1
BA3C41  mov [esi+0x5F0], ebx       ; = 1
BA3C47  mov [esi+0x5E8], 3
BA3C51  mov al, bl / ret 0xC       ; 返回 1（成功）
```

**结论：0x83 处理器不写 `0x640`，也不写 `0x644`。**
`0xBA3D53` 从来不是它执行的 —— `0x640` 的写入只发生在 `0x0x81` 处理器
（`0xBA3C70`）里。

### 21.2 `0x81` 处理器里的魔数校验（`0xBA3D35`）

```asm
BA3D35  mov ebx,[ebp-0x434]        ; 读到的第一个 u32
BA3D3B  cmp ebx, 0xD2
BA3D41  jb  BA3DBF                 ; < 0xD2 -> 错误 7 -> 复位
BA3D43  cmp ebx, 0xDC
BA3D49  ja  BA3DBF                 ; > 0xDC -> 错误 7 -> 复位
BA3D53  mov [esi+0x640], ebx       ; ★ 640 = 0x81 的魔数
```

### 21.3 被遗漏的门（`0xBA3AE0` 区域）

```asm
BA3AE6  cmp cl,0x87 / jne BA3B0E
BA3AEB  cmp [edi+0x640], 0xDC
BA3AF5  jb  BA3B36                 ; ★ 640 < 0xDC -> 整帧丢弃
BA3B02  call 0xBA3590

BA3B0E  cmp cl,0x89 / jne BA3B36
BA3B13  cmp [edi+0x640], 0xDC
BA3B1D  jb  BA3B36                 ; ★ 640 < 0xDC -> 整帧丢弃
BA3B2A  call 0xBA3600
```

两处都要求 `[req+0x640] >= 0xDC`，而 `0x640` 的取值范围是 `[0xD2,0xDC]`。
**唯一满足的取值是 `0xDC`。**

### 21.4 实跑验证（`IFS1_ELEVATED_20260929_122646`）

把服务端帧的 `u32 frame_len` 从 `0xC8` 提到 `0xDC`（`--frame-len 220`）：

```text
37.317  640=210 (0xD2)   <- 没有变化
37.346  5e8=3, 5ec=1, 5f0=1
37.348  POST83_SAMPLE  s9c=4 5e8=3 644=1
37.382  复位
```

**证伪**：`frame_len` 与 `[req+0x640]` 无关。`640` 仍然 `= 0xD2`，
因为探针发的 0x81 魔数是 `0xD2`。

### 21.5 这一轮真正证实的结论

```text
[req+0x640]  == [0x81 帧里的 magic u32]   （取值域 [0xD2,0xDC]）
握手 0x87 / 0x89 只在 [req+0x640] == 0xDC 时被处理
因此：探针必须发 magic = 0xDC，而不是 0xD2
```

### 21.6 修正后的完整握手时序（全部有反汇编依据）

```text
服务端 -> 0x81  (magic=0xDC, token=u64)
          客户端: 0x81 处理器 640=0xDC, 638/63C=token 两半
客户端 -> 0x82  (回帧，含 [req+0x5FC] 8 字节)
服务端 -> 0x83  回显那 8 字节
          客户端: 5E8=3, 5EC=1, 5F0=1
          客户端: dispatcher BA4574 读 644
                    644==1 -> 直接 return 0  ← 旧实验停在这里
服务端 -> 0x84
          客户端: BA0E20 -> BA3BA0；0x84 未命中 0x87/0x89 ->
                  memcmp(this+0x5FC, recv8) —— 必须回显 [req+0x5FC]
服务端 -> 0x89  (第一份 body 长度 >= 0xDC 的帧)
          客户端: BA3600 要求 644==1 -> C8=1, 644=2, 5E8=0
服务端 -> 0x87  (下一帧)
          客户端: BA3590 要求 644==0 -> 发 0xC8 魔数帧, 644=1
...
```

### 21.7 下一轮的第一个动作

```text
探针改为 --magic 0xDC 重跑，确认 [req+0x640] 变成 220，
并且 0x83 之后的复位点发生变化（0x84/0x89 能被处理）。
```

### 21.8 第一档状态

```text
① 0x81                已闭合（但魔数须为 0xDC）
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；门已定位 = 640(魔数)==0xDC，
                        且 0x83 后必须补发 0x84 与 0x89
⑤ 保活/持续           未闭合
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
