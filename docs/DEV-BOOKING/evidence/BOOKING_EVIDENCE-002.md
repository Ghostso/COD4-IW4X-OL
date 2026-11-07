# BOOKING_EVIDENCE-002

本文件记录第三阶段（P0-P7）使用的可复现证据。
只读分析，未修改 Golden / Server / patch / KDF hook。

## 分析源

```
CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
size   = 10,899,456
VA     = 0x00400000 .. 0x00E65000
Base.dll = COD OL\codoMP_client_shipRetailBase.dll
size   = 60,327,992
imagebase = 0x10000000
```

## 关键 VA 表

| VA | 含义 | 等级 |
|---|---|---|
| `0x00632680` | accepted handler，thiscall，ret 0x14 | CONFIRMED |
| `0x006326DB` | `"mmbook accepted"` 字符串引用 | CONFIRMED |
| `0x00632745` | 成功副作用 `[esp+0x28]=1` | CONFIRMED |
| `0x00632A00` | timeout handler（vtable +0x13C） | CONFIRMED |
| `0x0062F7E0` | mmbook 请求构造/外发 | CONFIRMED |
| `0x0062F6F0` | 从 `[edi+0x168]/[edi+0x16C]` 写 A/B | CONFIRMED |
| `0x0062F840` | reservation 数组填充（vtable +0x40） | CONFIRMED |
| `0x0062F902` | `[this+0xE360] = [ebp+0xC]` | CONFIRMED |
| `0x0062F908` | `imul eax,eax,0x238` | CONFIRMED |
| `0x0062F9C8` | `lea eax,[edx+ebx+0x75D8]` | CONFIRMED |
| `0x0062CD30` | reservation 数组清零（vtable +0x48） | CONFIRMED |
| `0x0062CD76` | `[this+0xE360]=0` | CONFIRMED |
| `0x00DC7270` | matching object vtable | CONFIRMED |
| `0x00DC72B0` | vtable +0x40 = 0x62F840 | CONFIRMED |
| `0x00DC73B0` | vtable +0x140 = 0x632680 | CONFIRMED |
| `0x00DC73BC` | vtable +0x14C = 0x62C580 | CONFIRMED |
| `0x00634080` | matching 状态码处理器 | CONFIRMED |
| `0x00634240` | callback 桥 → 0x634080 | CONFIRMED |
| `0x00633FE0` | 回调注册函数 | CONFIRMED |
| `0x007E7E30` | 网络对象取包 + 注册回调 | CONFIRMED |

## 复现命令

```powershell
python DEV-BOOKING\scripts\booking_trace.py vtable 0xDC7270 100 0x62F840 0x632680
python DEV-BOOKING\scripts\booking_trace.py refs 0x62F840 0x62F7E0 0x62F6F0
python DEV-BOOKING\scripts\booking_trace.py disasm 0x62F6F0 0x62F840
python DEV-BOOKING\scripts\booking_trace.py vcall 0x140 0x13C 0x40 0x48
python DEV-BOOKING\scripts\base_boundary_scan.py
```

## Base.dll 限定扫描结果

```
mmbook                  0
mmbook accepted         0
mmbook timedout         0
mmstart                 0
booking / Booking       0
DedicatedControl        0
dedicated               0
bridge                  0
sharedRoomClient        0
bookingDispatcher       0
MM_RESERVE_CMD_REQUEST  0
```

结论：`BASE_RESPONSE_CALLER = UNKNOWN`。

## 仍为 UNKNOWN

```
ACCEPTED_HANDLER_CALLER
RESPONSE_CHANNEL
0x62F840 的 ARG2 调用者
0x803830 返回对象的底层传输类型
Booking -> 28960 linkage
A/B 是否被外部模块再次写入
```

## 纪律

```
Golden 修改             = 无
Server 修改             = 无
4 个 Lobby patch 修改   = 无
KDF hook 修改           = 无
猜测性 Booking response = 未发送
```

