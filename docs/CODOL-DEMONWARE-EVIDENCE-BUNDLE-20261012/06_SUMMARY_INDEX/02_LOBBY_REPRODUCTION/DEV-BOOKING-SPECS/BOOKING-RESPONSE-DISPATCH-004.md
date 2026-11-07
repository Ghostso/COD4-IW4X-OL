# BOOKING-RESPONSE-DISPATCH-004
# 静态闭合 service=21 -> type=2 -> mmbook -> vtable -> 0x632680 分派链

> 2026-10-08 执行。纯静态逆向，镜像源 `image_best.bin`（base 0x400000，10,899,456 B）。
> 未修改 Golden/Server/PE/patch/KDF hook，未启动游戏，未发送任何 response。

---

## 1. Scope

只做静态：定位客户端从「大厅 TCP 收到 service=21 即时消息」到「调用 booking handler」
的完整分派链，并核对上一阶段给出的 vtable 槽位与 handler 归属是否准确。

```
目标链： Lobby TCP → decrypt/frame parser → service=21 → type=2 immediate-message
        → message dispatch → booking object → vtable → 0x632680
```

---

## 2. Previous Confirmed Evidence（承接 003）

```
BOOKING_RESPONSE_CHANNEL = SHARED_CONNECTION_CONFIRMED
6/14 mmbook = 大厅 TCP (127.0.0.1:ephemeral -> 127.0.0.2:3074)，service=6/task=14
服务端 booking 开启后：同一连接回 type=2 push，envelope=service 21，
  message = "mmbook accepted\0"
此前静态结论（本阶段将被修正）：
  accepted handler = 0x632680   @ vtable +0x140
  timeout handler  = 0x632A00   @ vtable +0x13C
```

---

## 3. Service=21 Entry（即时消息入口）

服务端即时消息信封（`codol_crypto.py: instant_push_body`，与 C# BuildPushFrameWithSender 逐字节一致）：

```
08 <u32 service=21> | 0A <u64 senderId> | 10 <string senderName>\0 | 13 08 <u32 len> <blob message>
```

客户端在 0x85 解密后的明文里读 marker 字节（`plain[4]`）；marker=2 即 push，
进入即时消息路径。信封内 `08` 字段 = service（21 = InstantMessage）。

本阶段实际定位到的是**信封解包之后的命令分派器**（见 §5），即 service=21
消息内容进入 dispatcher 的入口。frame 层「marker=2 → service=21 → 该 dispatcher」
的上游一跳见 §13 的 UNKNOWN#1（未追到具体地址，但数据流与 message 命令一致）。

```
SERVICE_21_ENTRY = HIGH-CONFIDENCE
  （"mmbook"/"mmrsv"/"mminvite" 命令分派器已定位；marker/service 帧路由上游为推断）
```

---

## 4. Type=2 Dispatcher（命令分派器）

位于 `0x7F15xx`（网络/大厅分派模块，非 matching 模块 0x62Cxxx）。核心片段：

```asm
0x7F1533  lea edi, [esp+0x30]         ; 指向解析出的消息数据
0x7F1537  call 0x7f3440               ; 解析即时消息信封 -> 消息命令串(ebx)

0x7F153C  push 6                      ; "mmbook" 长度 6
0x7F153E  push ebx                    ; 消息命令串
0x7F153F  push 0xdc6724               ; "mmbook"
0x7F1544  call 0xc3c678               ; strncmp(msg, "mmbook", 6)
0x7F154E  jne 0x7f1576                 ; 非 mmbook -> 试下一命令
  ; == mmbook ==
0x7F1550  mov edx, [esp+0x14]         ; arg5
0x7F1554  mov ecx, [0x82e13fc]        ; ★ 全局对象（matchmaking/booking manager）
0x7F155A  mov eax, [ecx]              ; eax = vtable
0x7F155C  mov eax, [eax+0x13c]        ; ★ vtable+0x13C = 0x632680
0x7F1562  push edx                    ; arg5
0x7F1563  push ebx                    ; arg4 = 消息串("mmbook accepted\0")
0x7F1566  push edi                    ; arg3 = &解析数据
0x7F156A  push [ebp+0xc]              ; arg2 = B
0x7F156E  push [ebp+8]                ; arg1 = A
0x7F156F  call eax                    ; ★ 调用 0x632680(this, A, B, ptr, msg, arg5)
```

同函数的兄弟分支（同一 dispatcher）：

```asm
0x7F1576  strncmp(msg, "mmrsv",   5)   -> [0x82e13fc]->vtable+0x140 (0x62E9F0)
0x7F15B2  strncmp(msg, "mminvite",8)   -> [0x82e1404]+0xc
0x7F15EB  strncmp(msg, "mmrespondinvitec", ...) -> ...
```

常量串（image 内验证）：

```
0xDC6724 "mmbook"          0xDE076C "mmrsv"          0xDE0774 "mminvite"
0xDE0780 "mmrespondinvitec"   0xDE078? 后续...
```

```
TYPE2_ROUTING = CONFIRMED
  （"mmbook" 命令串 -> vtable+0x13C(0x632680) 的直接跳转已逐条确认）
```

---

## 5. Payload Routing（消息串如何被比较/路由）

分派是**明文字符串前缀比较**，不是 hash、不是注册表 ID：

```
消息 blob（u32 len + "mmbook accepted\0"）
  -> 0x7f3440 解出命令串（前 N 字节）
  -> 0x7F1544 strncmp(cmd, "mmbook", 6)
       命中 -> vtable+0x13C(0x632680)
  -> 0x632680 内部 strncmp(cmd, "mmbook accepted", 15)
       命中 -> success；否则 -> timeout/failure
```

即**两级字符串比较**：dispatcher 用 6 字节前缀「mmbook」选 handler，
handler 用 15 字节「mmbook accepted」区分 accepted / timedout。

```
PAYLOAD_ROUTING = CONFIRMED
```

---

## 6. Booking Object Identification

- booking/matching 对象 vtable 基址 = **0xDC7274**（构造函数 `0x62C000` 内
  `mov dword [ebx], 0xDC7274`，见 0x62C025）。0xDC7270 是 RTTI COL（`0xDF96D8`），
  不是 vtable 首槽。
- 派生类 vtable = 0xDC7714（构造函数 `0x638244` 内写入），方法表与基类同构。
- dispatcher 通过全局 `[0x82e13fc]` 取得该对象（该全局被全镜像 ~200 处引用，
  是 matchmaking/manager 单例，非仅 booking 专用）。

```
BOOKING_OBJECT_BINDING = CONFIRMED
  （0x7F1554 读全局 -> vtable -> vtable+0x13C -> 0x632680）
```

---

## 7. vtable Analysis（★ 修正上一阶段）

构造函数写 `0xDC7274`，故对象 vtable 以 0xDC7274 为基。关键槽位：

```
+0x138  [78]  0x632A00    （ret 4，复制 0x1D0 字节结构；非 timeout handler）
+0x13C  [79]  0x632680    ★ "mmbook accepted" handler（ret 0x14，5 参数）
+0x140  [80]  0x62E9F0    （"mmrsv" 处理器，见 §4 dispatcher）
```

**修正**：上一阶段（BOOKING_EVIDENCE-002 / PROTOCOL-004）以 0xDC7270（含 RTTI COL）
为基，得出「accepted=+0x140、timeout=+0x13C」。实际对象 vtable 基 = 0xDC7274：

```
旧（错）： +0x140 = 0x632680(accepted)   +0x13C = 0x632A00(timeout)
新（对）： +0x13C = 0x632680(mmbook 统一 handler)   +0x140 = 0x62E9F0(mmrsv)
```

dispatcher 反汇编（§4）是决定性证据：`mmbook -> vtable+0x13C`，`mmrsv -> vtable+0x140`。

```
VTABLE_OFFSET_CORRECTED = CONFIRMED
```

---

## 8. 0x632680 Analysis（统一 booking 响应 handler）

签名：`thiscall(ecx=this) + 5 栈参数`，`ret 0x14`。

参数（与 timeout 调用点 0x632FCD 的压栈一一对应）：
```
arg1 [ebp+8]  = A   （比对 [this+0x3a048]）
arg2 [ebp+0xc]= B   （比对 [this+0x3a04c]）
arg3 [ebp+0x10]= &解析数据 [this+0x3a050]
arg4 [ebp+0x14]= msg 字符串
arg5 [ebp+0x18]= 长度/状态（15）
```

控制流（关键）：

```asm
0x63268D  cmp byte [esi+0x278], 0        ; 守卫：booking pending（[this+0x278]）
0x632695  je  0x6328eb                    ; 未启动 -> 清 A/B 返回
0x6326B9  cmp [ebp+8],  [esi+0x3a048]     ; A 必须匹配
0x6326C8  cmp [ebp+0xc],[esi+0x3a04c]     ; B 必须匹配
0x6326DA  push 0xdc69b0                   ; "mmbook accepted"
0x6326DF  call 0xc3c678                   ; strncmp(msg, "mmbook accepted", 15)
0x6326E9  jne 0x632876                    ; 非 accepted -> timeout/failure 路径
  == accepted ==
0x6326EF  imul eax,[esi+0xe360],0x238     ; reservation[i]（stride 0x238）
0x6326FB  mov edx,[eax+esi+0x75d8]        ; item.A
0x632707  mov eax,[eax+esi+0x75dc]        ; item.B
0x632710  je 0x632736                     ; 匹配 -> success
0x632736  mov [esp+0x28], 1               ; ★ 成功副作用 [esp+0x28]=1
0x632761  call 0x771320                   ; 日志/遥测 -> 状态迁移
  == 非 accepted（0x632876，timeout/failure）==
0x632876  cmp byte [esi+0x280], 0
0x63287F  cmp [esi+0x10780], 0xa
0x63288C  call 0x62f6c0                   ; 复位 A/B
0x6328BB  mov edx,[eax+0x148]             ; vtable+0x148
0x6328E0  call edx                       ; 清理/状态迁移
0x6328E8  ret 0x14
```

结论：**0x632680 不是单独的 accepted handler，而是统一的 mmbook 响应 handler**，
内部按「mmbook accepted」的 strncmp 分流 accepted / timeout(failure)。

```
0x632680_ROLE = CONFIRMED（统一 handler）
"mmbook accepted" 仅被 0x632680 引用（xref 唯一 = 0x6326DB）
```

---

## 9. 0x632A00 对比（★ 修正）

上一阶段把 0x632A00 标为「timeout handler」。实际：

```asm
0x632A00  prologue; sub esp,0x1e4
0x632A1C  mov esi,[ebp+8]        ; 1 个参数（源结构指针）
0x632A1F  mov ebx,ecx            ; this
0x632A4F  rep movsd (0x74 dwords) ; 复制 0x1D0 字节结构到本地
0x632A36  call 0x623770          ; 构造子对象（vtable 0xDC7534）
0x632A51  call 0x62c380          ; 处理
0x632A6A  ret 4                  ; 只有 1 个栈参数
```

- 签名 `ret 4`（1 参数），与 timeout 调用点 0x632FCD 压 5 参数的形态**不符**。
- 它**不引用** "mmbook timedout"（该串唯一 xref = 0x632FB2，timeout 调用点）。
- 它是「复制 0x1D0 字节 reservation item / 构造子对象」的 set/copy 方法。

```
REFUTED：0x632A00 = timeout handler
REFUTED：vtable+0x13C = 0x632A00(timeout)
```

---

## 10. Full Call-Path（完整调用链）

```
大厅 TCP (127.0.0.1:ephemeral -> 127.0.0.2:3074)
  -> 0x85 帧解密（AES-CBC + HMAC8）
  -> 明文 marker=2（push）-> service=21 即时消息信封解包（0x7f3440 系）
  -> 命令串 "mmbook accepted\0" 取出
  -> 0x7F1544  strncmp(cmd,"mmbook",6) == 0            [DISPATCH_ENTRY]
  -> 0x7F1554  读全局 [0x82e13fc]（matchmaking/booking manager）
  -> 0x7F155C  vtable[+0x13C] = 0x632680
  -> 0x7F156F  call 0x632680(this, A, B, ptr, msg, 15)  [ACCEPTED_CALL]
  -> 0x6326DF  strncmp(msg,"mmbook accepted",15)
        ==0 -> 0x632736  success（[esp+0x28]=1，状态迁移）
        !=0 -> 0x632876  timeout/failure（复位 A/B，清理）
```

对照（内部 timeout 路径，同 handler 不同入参）：

```
内部计时器到期
  -> 0x632FCD  call vtable[+0x13C] = 0x632680
        (this, A, B, ptr, "mmbook timedout", 15)
  -> 0x6326E9  jne 0x632876（走 timeout/failure 分支）
```

即：**accepted（网络）与 timedout（内部计时器）最终收敛到同一个 0x632680**，
由消息串决定走 success 还是 failure 分支。

---

## 11. Evidence Classification

| 节点 | 地址 | 等级 |
|---|---|---|
| 命令分派入口 strncmp "mmbook" | 0x7F1544 | CONFIRMED |
| 全局对象读取 | 0x7F1554 ([0x82e13fc]) | CONFIRMED |
| vtable+0x13C = 0x632680 | 0x7F155C / image 直接读槽 | CONFIRMED |
| 调用 handler | 0x7F156F | CONFIRMED |
| handler 签名 this+5arg, ret 0x14 | 0x632680 | CONFIRMED |
| "mmbook accepted" strncmp(15) | 0x6326DF | CONFIRMED |
| success 副作用 [esp+0x28]=1 | 0x632745 | CONFIRMED |
| 内部 timeout 调用点 | 0x632FCD | CONFIRMED |
| 对象 vtable 基 = 0xDC7274 | 0x62C025 (ctor) | CONFIRMED |
| "mmbook accepted" 唯一 xref | 0x6326DB | CONFIRMED |
| "mmbook timedout" 唯一 xref | 0x632FB2 | CONFIRMED |
| 兄弟命令 mmrsv->vtable+0x140 | 0x7F1576-0x7F15AB | CONFIRMED |
| 0x632A00 = timeout handler | — | REFUTED |
| marker=2 -> service=21 -> dispatcher 的上游帧路由地址 | — | HIGH-CONFIDENCE/UNKNOWN#1 |

---

## 12. Refuted Paths

```
REFUTED: vtable+0x140 = 0x632680（accepted）     → 实为 +0x13C；+0x140=0x62E9F0(mmrsv)
REFUTED: 0x632A00 = timeout handler               → 实为 ret4 复制方法，不引用 timedout 串
REFUTED: 0x91B19C 的 [reg+0x140] 是 accepted 调用 → 签名不符（1 参 vs 5 参），维持 003 结论
REFUTED: 0x632680 有直接 call（镜像内 direct call = 0，仅 vtable 间接）
REFUTED: accepted 与 timeout 是 vtable 两个不同槽位 → 实为同一槽位 +0x13C，按消息串分流
```

---

## 13. Remaining UNKNOWN

```
1. 帧层「marker=2 → service=21 → 0x7F15xx dispatcher」的上游一跳具体地址
   （0x85 解密后 marker 字节如何索引到该即时消息处理器）
2. 0x7f3440 信封解包的精确字段->寄存器映射（senderId/name/blob 如何落到 ebx/edi）
3. arg1=A、arg2=B 的精确来源（[ebp+8]/[ebp+0xc]：senderId u64 拆两半？booking token？）
4. [0x82e13fc] 全局在启动时由谁赋值（哪个初始化函数写入 booking/matching 单例）
5. 0x632680 success 分支后续（0x632736 之后）的完整状态迁移终点（是否触发连 28960）
```

---

## 14. Conclusion

```ini
BOOKING_RESPONSE_DISPATCH = CONFIRMED
```

分派链已静态闭合到 handler 本体，并对上一阶段做两处关键修正：

1. **槽位修正**：`vtable+0x13C = 0x632680`（不是 +0x140）；`+0x140 = 0x62E9F0(mmrsv)`。
   根因是 vtable 基应为 0xDC7274（RTTI COL 之后），上一阶段误用 0xDC7270。
2. **handler 合并**：0x632680 是**统一 mmbook 响应 handler**，内部按
   `strncmp(msg,"mmbook accepted",15)` 分流 accepted / timeout(failure)；
   0x632A00 不是 timeout handler（是 ret4 复制方法）。

```
DISPATCH_ENTRY_CONFIRMED           = CONFIRMED  (0x7F1544)
TYPE2_ROUTING_CONFIRMED            = CONFIRMED  ("mmbook"->vtable+0x13C)
BOOKING_OBJECT_BINDING_CONFIRMED   = CONFIRMED  ([0x82e13fc]->vtable)
ACCEPTED_HANDLER_CALLPATH_CONFIRMED= CONFIRMED  (0x7F156F->0x632680)
```

---

## 15. Next Recommended Step

1. **补帧层上游（UNKNOWN#1）**：从 0x85 解密后的 marker 字节索引跳表出发，定位
   service=21 的 handler 表项，确认它指向 0x7F15xx。目标：把 §3 的 HIGH-CONFIDENCE
   升为 CONFIRMED，彻底闭合「marker=2 → service=21 → dispatcher」。
2. **追 A/B 来源（UNKNOWN#3）**：在 0x7f3440 或调用者里确认 [ebp+8]/[ebp+0xc] 是否
   senderId(u64) 或 booking token —— 这决定服务端回 accepted 时 A/B 必须回显什么值。
3. **追 success 终点（UNKNOWN#5）**：0x632736 之后是否最终触发连 28960，与
   BOOKING_RESPONSE-CHANNEL-003 的「mmbook accepted 是 28960 的门」对齐。
4. 上述完成后，才具备「按真实 wire 格式构造 PvE coop accepted 应答」的静态依据；
   在此之前不发任何 response（遵守纪律）。

---

## 16. 纪律核对

```
Golden 修改        = 无
Server 修改        = 无
客户端 PE/DLL 修改 = 无
patch/hook/KDF hook = 无
伪造/发送 response  = 无
启动游戏           = 无
改变网络行为       = 无
为验证假造动态数据 = 无
```
