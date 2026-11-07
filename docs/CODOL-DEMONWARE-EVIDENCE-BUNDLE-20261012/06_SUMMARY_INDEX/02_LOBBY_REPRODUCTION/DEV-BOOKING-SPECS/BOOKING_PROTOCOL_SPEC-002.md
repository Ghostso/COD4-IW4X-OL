# BOOKING_PROTOCOL_SPEC-002

> 第三阶段静态恢复规格（P0-P7 收束版）
> 分析源：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
> 运行期镜像 VA：`0x00400000..0x00E65000`，10,899,456 B，已解壳
> 状态：纯静态，未修改 Golden / Server / 4 个 Lobby patch / KDF hook
> 未发送任何 Booking response

---

## 0. 本阶段结论摘要

| 环节 | 等级 | 结论 |
|---|---|---|
| `+0x278` 守卫 | STRONG_CANDIDATE | 1 字节 `BOOKING_PENDING/ACTIVE` |
| reservation 数组基址 | CONFIRMED | `this+0x75D8`，stride `0x238` |
| reservation 索引 | CONFIRMED | `[ebp+0xC]` 写入 `[this+0xE360]` |
| reservation 填充者 | CONFIRMED | `vtable+0x40` = `0x62F840` |
| A/B 真实写入 | CONFIRMED | `0x62F6F0` 从 `[edi+0x168]` / `[edi+0x16C]` 写入 |
| A/B 在 mmbook 请求中读取 | CONFIRMED | `0x62F7F9` / `0x62F809` |
| accepted parser | CONFIRMED | `0x632680`，`ret 0x14` |
| accepted 成功副作用 | CONFIRMED | `0x632745` 写 `[esp+0x28]=1` |
| accepted handler 调用者 | UNKNOWN | EXE 内未找到 5 参数虚调用点 |
| timeout handler | CONFIRMED | vtable `+0x13C` = `0x632A00` |
| response channel | UNKNOWN | 不能证明 TCP/UDP/IPC/0x85 |
| Booking -> 28960 linkage | UNKNOWN | 未找到字段 |
| Base.dll response caller | UNKNOWN | Base.dll 无 mmbook/mmstart/booking 字符串 |

**STATIC_RECOVERY_LIMIT_REACHED 尚未宣告。**
原因是本轮新增了 reservation/A-B 的真实写入链，静态图上仍有可追的
`0x62F6F0` 参数来源与 `0x633FE0` 回调注册边界。下一阶段优先做这两项。

---

## 1. P0：`[this+0x278]` 状态位

### 访问统计

在匹配模块 `0x62C000..0x63A000` 内，`+0x278` 全部为 **byte ptr** 访问：

```
WRITE 1  : 0x0062CCCD  mov byte [ebx+0x278], 1
WRITE 1  : 0x0062FBBB  mov byte [esi+0x278], 1
WRITE 0  : 构造/复位路径
READ     : 其余 26 处均为 cmp byte ptr [...+0x278], 0
```

### 守卫证据

```
0x0063268D  cmp byte [esi+0x278], 0
0x00632694  je  0x006328EB          ; 非零才继续进入 accepted parser
```

### 判定

```
[this+0x278] = BOOKING_PENDING / BOOKING_ACTIVE
等级 = STRONG_CANDIDATE
```

没有找到字符串、枚举或状态机表给它命名，因此不升级为 CONFIRMED。

---

## 2. P1：reservation 数组来源（本阶段最大进展）

### 2.1 已知布局

```
array base   = this + 0x75D8
stride       = 0x238
index slot   = this + 0xE360
item +0x00   = A
item +0x04   = B
```

### 2.2 填充函数 `0x62F840`（vtable `+0x40`）

入口：

```asm
0062F840  push ebp
0062F841  mov ebp, esp
0062F857  push ebx
0062F858  mov ebx, ecx                  ; ebx = this
0062F85A  cmp byte [ebx+0x278], 0
0062F861  je 0x62FB86                   ; 未处于 booking pending -> 拒绝
0062F874  movzx eax, byte [ebx+0x105FE]
0062F87B  cmp dword [ebx+0x105D8], eax
0062F881  jle 0x62F8C3
```

参数入口：

```asm
0062F8E4  cmp byte [ebp+8], 0          ; ARG1: 模式/标志
0062F8E8  mov al, byte [ebp+0x10]      ; ARG3: 字节
0062F8FB  mov eax, dword [ebp+0xC]     ; ARG2: reservation index
0062F8FE  test eax, eax
0062F900  js 0x62F936                  ; 负数 -> 另一条清理分支
0062F902  mov dword [ebx+0xE360], eax  ; CONFIRMED index 写入
0062F908  imul eax, eax, 0x238
0062F90E  lea edi, [eax+ebx+0x7470]
0062F915  mov esi, ebx
0062F917  call 0x62F6F0                ; 填充 A/B
```

### 2.3 `0x62F6F0` 真正写 A/B（CONFIRMED）

```asm
0062F736  mov ecx, dword [edi+0x168]
0062F73C  mov dword [esi+0x3A048], ecx   ; A
0062F742  mov edx, dword [edi+0x16C]
0062F748  mov dword [esi+0x3A04C], edx   ; B
```

其中：

```
edi = base_item + 0x168 附近的源结构
esi = matching object
```

`0x62F840` 计算 `edi = eax*0x238 + ebx + 0x7470`，因此
`[edi+0x168]` / `[edi+0x16C]` 位于 item 内部偏移 `0x168` / `0x16C`
（item 起点按 `0x7470` 计）。

### 2.4 数组清零/初始化

`0x62CD30`（vtable `+0x48`）在重置路径中：

```asm
0062CD54  push 0x238
0062CD59  lea esi, [edi+0x7238]
0062CD60  lea eax, [edi+0x7470]
0062CD66  push 0x6EF0
0062CD6B  push eax
0062CD6C  mov dword [edi+0x7230], 1
0062CD76  mov dword [edi+0xE360], 0
0062CD80  call 0xC3C603              ; memset-like
```

即数组 stride `0x238`，元素数 `0x6EF0`，总大小与该对象布局一致。

### 2.5 其它 `0xE360` 写入点

```
0x0062C0E8  ctor 初始化 -1
0x0062CD76  重置为 0
0x0062DF5E  置 -1
0x0062F48D  启动清理置 -1
0x0062F902  ← ARG2 写入，唯一“真实值”入口
0x0062F975  另一分支置 0
0x00633E77  置 -1
0x0063776A / 0x0063787E / 0x006378AB  容器相关写入
```

### 2.6 本项结论

```
reservation array 不是 findSessions 直接写出来的。
它由客户端匹配对象自身的 vtable+0x40 填充；
填充输入来自 ARG2（index）与 item 内的 +0x168/+0x16C。

RESERVATION_ARRAY_FILLER = 0x62F840   CONFIRMED
A/B_REAL_WRITER          = 0x62F6F0   CONFIRMED
```

**仍未确认**：`0x62F840` 的外部调用者是谁、`ARG1/ARG2/ARG3` 由谁构造。

---

## 3. P2：`+0x140` 真实调用者

### 3.1 已扫类别

使用“寄存器同源”扫描，覆盖：

```
mov reg,[obj+disp]
call reg
```

对 `disp = 0x140` 的结果：全镜像仅 1 处：

```
0x0091B19C  mov edx,[eax+0x140]
0x0091B1A3  call edx
```

该点已在前一阶段 REFUTED：

```
0x91B190 函数无 5 个栈参数
调用后立即 test al,0xf
与 0x632680 ret 0x14（5 参数）签名不匹配
```

### 3.2 未命中说明

对 vtable 表项 `0xDC7270 + 0x140` 的 dword 引用扫描结果：

```
0xDC7270 自身引用 = 0
0xDC7274 被 0x62C025 引用（构造函数安装）
```

也就是说，`+0x140` 槽的调用不是普通 `mov reg,[obj+0x140]; call reg`
形式，可能来自：

1. 表指针别名/复制后的间接调用；
2. 通过事件对象 + 成员函数指针分发；
3. 运行期解密/注册的 callback；
4. EXE 外部模块调用。

当前无任何一条被证明。因此：

```
ACCEPTED_HANDLER_CALLER = UNKNOWN
RESPONSE_CHANNEL        = UNKNOWN
```

---

## 4. P3：Base.dll 边界检查（限定范围）

### 4.1 检查对象

```
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll
size = 60,327,992 B
imagebase = 0x10000000
.text VA=0x1000 VS=0x742000
```

### 4.2 字符串命中

| Needle | 命中 |
|---|---:|
| `mmbook` | 0 |
| `mmbook accepted` | 0 |
| `mmbook timedout` | 0 |
| `mmstart` | 0 |
| `booking` / `Booking` | 0 |
| `DedicatedControl` | 0 |
| `dedicated` | 0 |
| `bridge` | 0 |
| `sharedRoomClient` | 0 |
| `bookingDispatcher` | 0 |
| `MM_RESERVE_CMD_REQUEST` | 0 |
| `callback` | 44（均为 OpenSSL/cv/tencent 无关字符串） |

### 4.3 结论

```
BASE_RESPONSE_CALLER = UNKNOWN
```

当前没有静态证据表明 Base.dll 处理 `mmbook` Booking 响应。
不能在报告中写成“响应在 Base.dll 中”。

---

## 5. P4：A/B 外部写入者

### 5.1 本镜像内写入点

```
disp=0x3A048:
  0x62C282  清零
  0x62F6C5  清零
  0x62F717  清零
  0x62F73D  真实写入 ← 0x62F6F0 内，来自 [edi+0x168]
  0x62F809  读取（mmbook 请求）
  0x6326BB  读取（accepted parser）
  0x6328F7  清零（拒绝路径）
  0x632FBE  读取（timeout 路径）
```

上一阶段写的 `A_SOURCE = EXTERNAL_MODULE_WRITE / UNKNOWN`
**需要更新**：

```
A/B 的真实写入在 EXE 内已找到，位于 0x62F6F0。
外部模块是否再写 = UNKNOWN（没有证据支持，也没有证据排除）。
```

### 5.2 时序

```
0x62F840 (vtable+0x40)
  → 写 [this+0xE360] = ARG2
  → call 0x62F6F0
       → A = [item+0x168]
       → B = [item+0x16C]
  → 后续 mmbook 构造读取 A/B
```

因此前一阶段“请求-应答配对号”的判断仍然成立，但**赋值者已不再是未知**。

---

## 6. P5：accepted handler 的 5 个参数

已知签名：

```
0x632680  ret 0x14  → 5 个栈参数
[ebp+8]   = A（与 [esi+0x3A048] 比对）
[ebp+0xC] = B（与 [esi+0x3A04C] 比对）
[ebp+0x14]= 响应字符串指针
[ebp+0x10]= 未在本路径使用/未知
[ebp+0x18]= 未在本路径使用/未知
```

### 参数来源

```
ARG1 = UNKNOWN（未追踪到写入 0x632680 调用栈的代码）
ARG2 = UNKNOWN
ARG3 = UNKNOWN
ARG4 = UNKNOWN
```

但已经证明：

```
ARG1/ARG2 最终必须分别等于 [this+0x3A048] / [this+0x3A04C]
```

因此“必须回显 A/B”是 CONFIRMED；“由哪个帧字段携带”仍是 UNKNOWN。

---

## 7. 新增：matching 状态机的可观测边界

### 7.1 状态码处理 `0x634080`

`0x634080` 的第二个参数是状态码，入口先清理
`[esi+0x1C]`、`[esi+0x283]`、`[esi+0x1061F]`，然后比较
`[esi+0x27C]`：

```
0x6340DF  cmp eax, 8       ; 状态 8 分支
0x63410F  cmp eax, 0x2A    ; 状态 0x2A 分支
0x634114  cmp eax, 0x1E    ; 状态 0x1E / 0x26 分支
0x634119  cmp eax, 0x26
```

### 7.2 回调桥 `0x634240`

```asm
00634240  push ebp / mov ebp,esp
00634246  mov eax,[ebp+0xC]
00634249  push eax
0063424A  mov eax,[ebp+8]
0063424D  mov ecx,[eax+0x25C8]      ; 取匹配对象
00634253  push eax
00634254  call 0x634080
```

`0x634240` 的引用：

```
0x62F533  作为 callback 传给 0x7E8120
0x633E19  作为 callback 传给 0x7E8120
```

### 7.3 回调注册 `0x633FE0`

`0x633FE0` 的引用：

```
dword refs: 0x7E7E8D, 0x7E7F46
direct calls: 0x62CCFA, 0x62DF95
```

`0x7E7E30` / `0x7E7EE0` / `0x7E7FD0` 都通过 `0x803830` 取网络对象，
校验 `类型 == 2`，再注册 `0x633FE0` 回调。

### 7.4 结论

```
matching 状态机响应边界 = 0x634080  CONFIRMED
callback 桥             = 0x634240  CONFIRMED
回调注册点              = 0x633FE0  CONFIRMED
```

这证明客户端确实通过一个网络抽象对象接收匹配/预约状态，
但 `0x803830` 返回对象的底层传输类型仍未确认。

---

## 8. P6：response channel 判定

```
CHANNEL = UNKNOWN
```

已排除：

```
✗ 直接 call 0x632680
✗ 普通 mov reg,[obj+0x140]; call reg
✗ Base.dll 含 mmbook 字符串
```

未证实：

```
? 0x85 push
? DedicatedControl
? client bridge
? TCP / UDP / IPC / shared memory
```

**不允许**在本规格基础上直接发送猜测性 response。

---

## 9. P7：最终验收表

| 环节 | 状态 | 证据 |
|---|---|---|
| 6/14 request 构造 | CONFIRMED | `0x62F7E0` |
| A/B 随 request 外发 | CONFIRMED | `0x62F7F9` / `0x62F809` |
| A/B 真实写入 | CONFIRMED | `0x62F6F0` |
| reservation index 写入 | CONFIRMED | `0x62F902` |
| reservation array 填充器 | CONFIRMED | `0x62F840` |
| accepted parser | CONFIRMED | `0x632680` |
| accepted 成功副作用 | CONFIRMED | `0x632745` |
| timeout handler | CONFIRMED | `0x632A00` |
| accepted handler 调用者 | UNKNOWN | 无匹配虚调用 |
| response channel | UNKNOWN | 无跨模块证据 |
| Base.dll 响应处理 | UNKNOWN | 全限定字符串扫描 0 命中 |
| Booking -> 28960 | UNKNOWN | 未找到字段 |

---

## 10. 下一阶段最短路径（仍纯静态）

1. 追 `0x62F6F0` 的 `edi` 来源与 `0x62F840` 的 ARG2 调用者。
   成功标准：找到真正构造 reservation index 的代码。

2. 追 `0x633FE0` 回调注册对象的接口。
   成功标准：确定 `0x803830` 返回的是哪一类网络对象，
   从而把 channel 从 UNKNOWN 降级为 TCP/UDP/IPC 之一。

3. 若 1、2 均无新引用，再宣告：

```
STATIC_RECOVERY_LIMIT_REACHED
```

---

## 11. 纪律核对

```
Golden 修改             = 无
Server 修改             = 无
4 个 Lobby patch 修改   = 无
KDF hook 修改           = 无
猜测性 Booking response = 未发送
```

