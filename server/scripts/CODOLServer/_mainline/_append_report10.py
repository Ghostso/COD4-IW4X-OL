import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 29. 大厅握手三个处理器完整逆向

### 29.1 分发器（0xBA4440）操作码全表

```text
[req+0x5E8]==1 : 0x81 -> 0xBA3C70   (带内容)    0x04 -> 失败
[req+0x5E8]==2 : 0x83 -> 0xBA3BA0   (带内容)
[req+0x5E8]==3 : 0x85 -> 0xBA3710   0x84 -> 0xBA0E20
其余           -> 失败
```

### 29.2 opcode 0x81 -> 0xBA3C70

```asm
00BA3CBC  call 0xB783C0     ; 字段1: u32 -> [ebp-0x434]
00BA3CEB  call 0xB783C0     ; 字段2: u64 -> [esi+0x638], [esi+0x63C]
00BA3D25  call 0xB78430     ; 字段3: 读 8 字节
00BA3D3B  cmp ebx, 0xD2
00BA3D43  cmp ebx, 0xDC
00BA3D49  ja  0xBA3DBF      ; 字段1 必须 ∈ [0xD2,0xDC]
00BA3D53  mov [esi+0x640], ebx
00BA3D6E  push 0x418 / push &len / push &buf(0x400)
00BA3D83  call 0xBA1850     ; 生成/写入回帧
00BA3D9E  call 0xBA2F20     ; 入发送队列
00BA3DA3  mov dword [esi+0x5E8], 2   ; 子状态 1 -> 2
```

### 29.3 opcode 0x83 -> 0xBA3BA0（8 字节令牌回显校验）

```asm
00BA3BB5  push 8
00BA3BCD  call 0xB783C0     ; 读 8 字节 -> [ebp-0xC]
00BA3C05  push 8
00BA3C0B  lea  eax,[esi+0x5FC]
00BA3C12  call 0xB73FE0     ; memcmp(读到的8字节, this+0x5FC)
00BA3C1C  jne  0xBA3C62     ; 不等 -> 报错 3
00BA3C3B  mov  [esi+0x5EC], 1
00BA3C41  mov  [esi+0x5F0], 1
00BA3C47  mov  dword [esi+0x5E8], 3   ; 子状态 2 -> 3
```

**关键：0x83 是纯回显校验**——服务端把客户端在 0x81 里给的 8 字节原样回发
即可，不需要服务端自己生成密钥。

### 29.4 opcode 0x85 -> 0xBA3710

```asm
00BA374C  push 4            ; 读 u32 -> [ebp-0x3A8]
00BA3794  call 0xB783C0
00BA37A6  push 0x10         ; 读 16 字节 -> [ebp-0x50]
00BA37C2  call 0xB783C0
00BA37ED  cmp ebx, 8        ; 另有长度约束
```

### 29.5 写帧函数 0xBA1850 的三个常量

```asm
00BA18DE  mov byte [ebp-0x4F5], 0xAB   ; 无条件写 1 字节 0xAB
00BA18F7  cmp dword [ebx+0x644], 3
00BA191E  mov byte [ebp-0x4F5], 0x90   ; 仅 644==3 时写 0x90
00BA1931  cmp dword [ebx+0x6DC], 0x400 ; payload < 1024
00BA195C  call 0xB78350                ; 写 2 字节 payload 长度
```

即 `[req+0x644]` 是握手进度计数器，3 是第二阶段的门限。

### 29.6 握手全貌

```text
1. C -> S   28B 首帧: len=200 | 200 | 210 | 220 | 0x00080000 | rand64
2. S -> C   opcode 0x81: u32∈[0xD2,0xDC], u64=令牌, 8B
3. C        [req+0x5E8] 1 -> 2
4. S -> C   opcode 0x83: 8 字节 == 第 2 步的 u64
5. C        [req+0x5E8] -> 3, [0x5EC]=[0x5F0]=1
6. S -> C   opcode 0x85: u32 + 16B
7. C        [req+0x644] -> 3
```

### 29.7 实测（run `IFS1_ELEVATED_20260928_202352`）

按第 2 步格式回帧（0x81 + 魔数 0xD2 + 令牌 + 8B，共 204 字节）：

```text
t=36.942  DW_LOBBY_CONNECTED   uA50=4  C8=2  9c=3  a8=34210177  5e8=1  644=1
t=83.966  DWLOBBY_PUMP_SUCCESS uA50=5  C8=2  9c=3  a8=34210177  5e8=1  644=1
```

结果：**连接保持健康（C8 稳定为 2 不再掉到 4），状态机到终态 uA50=5**，
但 `5e8` 仍停在 1、`644` 停在 1 —— 说明 **0x81 处理器并未真正执行**。

### 29.8 尚未闭合：opcode 的实际偏移

```text
全零体帧            a8 = 0        (连接保持)
全 0x81 体帧        a8 = 129      (C8 掉到 4，失败)
本轮 0x81+魔数帧    a8 = 34210177 (C8 保持 2)
```

三次采样互相矛盾，说明 `[req+0xA8]` 并非简单取体偏移 0。opcode 的
实际读取偏移仍需定位；在该点确认之前，握手第 3 步之后无法推进。

### 29.9 归档

本轮运行已纳入归档；三个处理器反汇编已写入本节。
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
