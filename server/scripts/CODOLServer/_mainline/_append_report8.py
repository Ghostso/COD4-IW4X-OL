import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 27. `0x00BA0FF0` / `0x00BA12E0` 字段消费逻辑完整逆向

### 27.1 先修正一个关键前提：这是字节序，不是位流

`0x00B783C0` 的完整语义（逐条反汇编确认）：

```asm
; 0xB783C0(src, size, off, &pos, dst, count)
00B783C3  cmp dword ptr [ebp+0x18], 0   ; dst != 0
00B783C7  mov edx, [ebp+0x10]          ; edx = off
00B783CB  mov esi, [ebp+0x14]          ; esi = &pos
00B783CF  mov edi, [ebp+0x1c]          ; edi = count
00B783D2  lea ecx, [edx+edi]           ; ecx = off + count
00B783D7  mov [esi], ecx               ; *pos = off + count
00B783E1  mov esi, [ebp+0x0c]          ; esi = size
00B783E4  cmp edx, esi                 ; off  <= size ?
00B783EA  cmp ecx, esi                 ; off+count <= size ?
00B783F1  jne -> 0x8435D0 (抛出越界)    ; 任一不满足则抛异常
00B7840E  add eax, edx                 ; src + off
00B78414  call 0xC3E400                ; memcpy(dst, src+off, count)
```

即 **`(src, size, 字节偏移, &游标, 目标, 字节数)`，带双向边界检查的顺序字节读取**。

由此修正 `0x00BA0FF0` 的签名：

```text
0xBA0FF0(this, src, size, &offset)
          esi   edi   ebx = 游标指针
```

前几节的「5 位字段 / 位打包」描述作废——该层是**纯字节字段**。

### 27.2 `0x00BA0FF0` 字段序列（完整）

逐字段反汇编：

```asm
; --- 字段1: 1 字节，必须 == 1 ---
00BA1057  cmp byte ptr [ebp-0xDB], 1
00BA105E  jne 0xBA1296            ; 否则抛错

; --- 字段2: 1 字节，必须 == 2 或 == 1 ---
00BA1093  cmp al, 2
00BA1095  je  0xBA109F
00BA1097  cmp al, 1
00BA1099  jne 0xBA1296

; --- 字段3: 1 字节 (sub) ---
00BA10BE  mov cl, byte ptr [ebp-0xDB]   ; sub
00BA10C4  mov al, byte ptr [ebp-0xDD]   ; 字段2
00BA10CA  test cl, cl
00BA10CC  je  0xBA10D6
00BA10CE  cmp al, 2
00BA10D0  jne 0xBA1296            ; sub != 0 时字段2 必须 == 2
00BA10D6  cmp al, 2
00BA10D8  jne 0xBA1286

; 字段2 == 1 且 sub != 0 -> 失败
00BA1286  cmp al, 1
00BA1288  jne 0xBA11AE
00BA128E  test cl, cl
00BA1290  je  0xBA11AE
          ; 否则落入 0xBA1296 抛错
```

```asm
; --- 字段2 == 2 时才有：一个 u16 值，带游标回滚 ---
00BA10DE  lea ecx, [ebp-0xD8]      ; 新建 TaggedString
00BA10E4  call 0xB75320
00BA1108  call 0xB756A0            ; 读 u16 -> TaggedString.value(+0x84)
00BA110D  test al, al
00BA110F  je   0xBA127A            ; 读失败 -> 回滚 *offset，再走公共尾部
                                   ; 0xB756A0 内部失败时 *out = 起始位置
```

```asm
; --- 公共尾部 ---
00BA11BD  call 0xB783C0            ; 字段4: u16 -> [ebp-0xDC]
00BA11D4  mov edx, 0x400
00BA11D9  cmp ax, dx
00BA11DC  ja  0xBA1296             ; 字段4 必须 <= 0x400 (1024)
00BA11FE  call 0xB783C0            ; 复制 字段4 个字节 -> this+0x6E0
00BA1223  mov [eax+0x6DC], edx     ; this+0x6DC = 字段4 (负载长度)
00BA122F  call 0xB783C0            ; 字段5: u32 -> [ebp-0xEC]
00BA1241  fild dword ptr [ebp-0xEC]
00BA124D  fadd dword ptr [0xde7bc0]  ; 负数当无符号修正
00BA1253  fdiv qword ptr [0xde7b98]  ; / 1000.0
00BA1270  fstp dword ptr [eax+0xAE0] ; this+0xAE0 = 字段5 / 1000.0
00BA1276  mov al, cl                 ; 返回 true
```

### 27.3 由此得到的完整帧契约

```text
u32  frame_len                       ; 0xBA20A0 读取，作为 [req+0xAC]
u8   frame_type                      ; 0xBA20A0 读取；1/2 -> 帧头 9 字节，其它 -> 1 字节
--------------------------------- 以下由 0xBA0FF0 解析 ---------------------------------
u8   f1            ; 必须 == 1
u8   f2            ; 必须 == 2 或 1
u8   f3  (sub)     ; f2==1 时必须 == 0
if f2 == 2:
     u16 v         ; 存入 TaggedString(+0x84)；读取失败则游标回滚
u16  payload_len   ; 必须 <= 0x400 (1024)
u8[payload_len] payload   ; 复制到 this+0x6E0，长度记入 this+0x6DC
u32  t_ms          ; 秒数 = t_ms / 1000.0，结果存入 this+0xAE0
```

成功时返回 `true`，失败时抛异常并回到 `0xBA1296` 的错误路径。

### 27.4 `0x00BA12E0` 结果对象构造（完整）

```asm
; 0xBA12E0(this, arg1=位读取器对象, arg2=dword, arg3=byte)
00BA1309  mov dword ptr [esi], 0xDB6AE4      ; 先装基类 vtable
00BA1316  mov dword ptr [esi+4], 0
00BA1320  mov dword ptr [esi], 0xD5A4DC      ; 换成真实 vtable
00BA1326  mov [esi+8], ecx                   ; this+8  = arg1
00BA1331  call dword ptr [0xca8128]          ; AddRef(arg1+4)
00BA133E  call 0xB9BBB0                      ; eax = available
00BA1346  mov [esi+0xc], eax                 ; this+0xC  = available
00BA1349  neg eax / sbb eax,eax / and eax,[ebp+0xc]
00BA1353  mov [esi+0x10], eax                ; this+0x10 = (available!=0) ? arg2 : 0
00BA1350  mov byte ptr [esi+0x14], cl        ; this+0x14 = arg3 (byte)
```

字段表：

```text
this+0x00  vtable = 0xD5A4DC
this+0x04  (0)
this+0x08  arg1  位读取器对象（持引用，AddRef 其 +4 计数器）
this+0x0C  available = 0xB9BBB0(reader)
this+0x10  (available != 0) ? arg2 : 0
this+0x14  arg3（字节）
```

调用点 `0xBA222C` 的三个实参：

```asm
00BA2204  mov ecx, [esi+0xac]      ; 帧长度
00BA220A  mov eax, [esi+0xb0]      ; 位读取器
00BA2210  dec ecx                   ; arg2 = frame_len - 1
00BA2213  push ecx                  ; arg2
00BA2217  ... 把 eax(读取器) 压栈     ; arg1
00BA222C  call 0xBA12E0
```

即 `arg2 = 帧长度 - 1`（扣掉 1 字节帧类型）。

### 27.5 与客户端首帧的对照

客户端首帧（28 字节）：

```text
c8 00 00 00 | c8 | 00 00 00 | d2 00 00 00 | dc 00 00 00
00 00 08 00 | <rand32> <rand32>
```

按 27.3 的契约套进去：

```text
frame_len  = 0x000000C8 = 200
frame_type = 0xC8        ; 非 1/2 -> 帧头 1 字节
f1         = 0x00        ; 契约要求 == 1  <-- 不满足
```

**这就是 28 字节首帧被拒的直接原因**：`f1` 既不是 1，`f2` 也不是 1/2。
客户端是在 `0x00BA1057` 的第一道校验上就失败的，随后 `[req+0x9C]=3`
后不再推进，约 50 秒超时弹「与大厅服务失去连接」。

（该 28 字节是客户端**发**出的首包，走 `0xBA2F20` 发送队列；服务端
应答需要的是上面这套 **f1=1** 的格式，两者不是同一张表。）

### 27.6 可直接构造的服务端应答

```python
import struct
payload = b""                      # 业务负载，可先留空
body  = bytes([1, 2, 0])           # f1=1, f2=2, f3(sub)=0
body += struct.pack("<H", 0)       # if f2==2: u16 v
body += struct.pack("<H", len(payload))   # payload_len <= 0x400
body += payload
body += struct.pack("<I", 0)       # t_ms -> 0.000 s
frame = struct.pack("<I", 1 + len(body)) + bytes([0xC8]) + body
```

注意 `frame_len` 的语义、以及 `frame_type` 取非 1/2 时的帧头长度，仍需
以运行验证确认（第 23 节实测：长度字段 200、首字节非 1/2 时被接受）。

### 27.7 仍待确认

```text
1) frame_type 取 1 与 2 时多出的 8 字节帧头内容
2) f2 == 2 分支那个 u16 v 的语义（进入 TaggedString，疑似通道/会话号）
3) payload 的期望内容（this+0x6E0 / +0x6DC 之后由谁消费）
4) 字段5 t_ms 是否参与超时判定（当前 50 秒超时与之是否相关）
```
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
