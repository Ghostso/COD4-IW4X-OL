# BOOKING_PROTOCOL_SPEC-003

> 第四阶段：收束两个剩余静态边界
> 分析源：`image_best.bin`（VA 0x400000..0xE65000，已解壳）
> 纯静态。未修改 Golden / Server / patch / KDF hook。
> 未启动游戏，未发送 Booking response。

---

## 0. 本阶段结论

| 项目 | 等级 | 结论 |
|---|---|---|
| A_SOURCE | CONFIRMED | `item+0x168` |
| B_SOURCE | CONFIRMED | `item+0x16C` |
| A/B real writer | CONFIRMED | `0x62F6F0` |
| reservation index slot | CONFIRMED | `[this+0xE360]` |
| reservation index source | **CONFIRMED（本地匹配结果下标）** | `0x637720` 选择后写入 |
| reservation array fill | CONFIRMED | `0x6379E0` 从 `this+0x340` 拷贝到 `this+0x7470` |
| reservation array clear | CONFIRMED | `0x62CD30` |
| `0x62F840` ARG1 | CONFIRMED | 模式/标志字节，`[ebp+8]` |
| `0x62F840` ARG2 | CONFIRMED | reservation index，`[ebp+0xC]` |
| `0x62F840` ARG3 | CONFIRMED | 字节，`[ebp+0x10]` |
| accepted handler | CONFIRMED | `0x632680` |
| accepted handler caller | UNKNOWN | 未定位 |
| response channel | UNKNOWN | 不能由 `0x803830` 状态推出 |
| `0x803830` 对象 | CONFIRMED | 全局网络单例 getter |
| `0x803830` 返回对象 vtable | CONFIRMED | `0xD599DC` |
| `0xB7A670` | CONFIRMED | 连接/会话状态查询（非对象类型） |
| callback slot | CONFIRMED | `+0x1610`，由 `0xB7A640` 写入 |
| Booking → 28960 | UNKNOWN | 未找到字段 |
| Base.dll attribution | NOT_ESTABLISHED | 保持第三阶段结论 |

---

## P0：`0x62F840` ARG2 来源闭环

### 1. `0x62F840` 的真实调用类型

`0x62F840` 没有直接 `call rel32` 调用者。

全镜像扫描结果：

```
0x62F840  dword refs = { 0xDC72B0, 0xDC7750 }
           direct calls = none
```

即它是 `vtable 0xDC7270 + 0x40` 的成员函数。

### 2. 参数语义（CONFIRMED）

```
ARG1 = [ebp+8]   byte mode / flag
ARG2 = [ebp+0xC] reservation index
ARG3 = [ebp+0x10] byte value
```

证据：

```asm
0062F8E4  cmp byte [ebp+8], 0
0062F8E8  mov al, byte [ebp+0x10]
0062F8FB  mov eax, [ebp+0xC]
0062F8FE  test eax, eax
0062F900  js 0x62F936
0062F902  mov [ebx+0xE360], eax       ; reservation index
0062F908  imul eax, eax, 0x238
0062F90E  lea edi, [eax+ebx+0x7470]
0062F917  call 0x62F6F0               ; 写 A/B
```

### 3. `0x62F6F0` 写 A/B（CONFIRMED）

```asm
0062F736  mov ecx, [edi+0x168]
0062F73C  mov [esi+0x3A048], ecx      ; A
0062F742  mov edx, [edi+0x16C]
0062F748  mov [esi+0x3A04C], edx      ; B
```

### 4. ARG2 的真正来源（本阶段关键结论）

`0x637720` 直接建立了 index 与 item 的对应关系：

```asm
00637735  mov [esi+0x7230], eax        ; count
0063773B  imul eax, eax, 0x238
...
0063776A  mov [esi+0xE360], ebx        ; index = 0
...
006377D1  mov edi, [esi+0x7230]        ; count
...
0063785E  inc ecx
...
0063787E  mov [esi+0xE360], ecx        ; ← 选中 index 写回
0063788A  mov edx, [esi+0xE360]
00637890  imul edx, edx, 0x238
00637896  lea edi, [edx+esi+0x7470]
0063789D  call 0x62F6F0                ; 用该 item 写 A/B
```

因此：

```
ARG2
 → [this+0xE360]
 → reservation[index]
 → item
 → item+0x168 = A
 → item+0x16C = B
```

闭环成立。

### 5. reservation 数组从哪里来

`0x6379E0` 将 `this+0x340` 的副本数组拷入 `this+0x7470`：

```asm
0063795D  mov [ebx+0x7230], 0
00637969  test ecx, ecx
0063797D  mov ecx, [ebx+0x7230]
00637983  imul ecx, ecx, 0x238
00637989  lea edi, [ecx+ebx+0x7470]
0063798E  mov esi, eax
00637997  rep movsd
00637999  add [ebx+0x7230], edx
0063799F  add eax, 0x238
```

`0x637590` 则负责把匹配结果按条件写入 `this+0x340`：

```asm
006375C1  add ebx, 0x340
00637687  imul ecx, ecx, 0x238
0063768D  lea edi, [ecx+ebx+0x340]
0063769C  mov [ebx+0x334], eax
006376A2  rep movsd
```

### 6. 与 findSessions / playlist=10 的关系

当前能够确认的是：

- reservation 数组由客户端本地匹配结果结构填充；
- `0x637720` 只在本地副本数组内选择 index；
- 没有找到把 31 次 findSessions 原始 payload 直接映射为该 index 的指令；
- `findSessions` / `playlist=10` 是否通过上层匹配结果进入 `this+0x340`，
  当前没有直接证据。

```
reservation index source = LOCAL_MATCH_RESULT_COPY   CONFIRMED
direct_findSessions_link = UNKNOWN
direct_playlist10_link   = UNKNOWN
```

不能把“本地匹配结果数组”错误写成“findSessions 原始下标”。

---

## P1：`0x7E7E30` 网络对象 / callback 链

### 1. `0x803830` 的真实语义

`0x803830` 是全局网络单例 getter：

```asm
00803830  mov eax, [0x8269774]
00803835  test eax, eax
00803837  jne 0x8038A7
00803839  push 0x1618
0080383E  call 0xB74220
...
0080384C  call 0xB82130
00803851  mov [0x8269774], eax
...
0080388B  ret
```

### 2. 对象构造

```asm
00B82130  ...
00B82173  mov dword [esi], 0xD599DC      ; vtable
00B82404  mov dword [esi+0x4F4], ebx     ; 子对象/连接接口
00B8240A  mov byte  [esi+0x4F8], bl
00B824D2  mov dword [esi+0x1610], ebx    ; callback slot 初始 0
```

### 3. `0xB7A670` 不是类型判断

```asm
00B7A670  mov esi, ecx
00B7A673  mov ecx, [esi+0x4F4]
00B7A679  test ecx, ecx
00B7A681  call 0xBA0780
00B7A686  cmp byte [esi+0x4F8], 0
00B7A68F  cmp eax, 2
00B7A694  mov eax, 1
00B7A699  ret
```

`0xBA0780` 读取 `[ecx+0xC8]` 与 `[ecx+0x644]`，返回状态值。
因此前面记录的“type == 2”必须修正为：

```
0xB7A670 = CONNECTION/SESSION STATE QUERY
不是对象类型字段
```

### 4. callback slot

`+0x1610` 只有 3 个写入/读取点：

```
0xB7A646  mov [ecx+0x1610], eax    ; setter 0xB7A640
0xB82034  mov eax, [ebx+0x1610]    ; 读取
0xB824D2  mov [esi+0x1610], ebx    ; ctor 清零
```

`0xB7A640` 的签名：

```asm
00B7A640  mov eax, [ebp+8]
00B7A646  mov [ecx+0x1610], eax
00B7A64C  mov ecx, [ecx+0x4F4]
00B7A65C  ret 4
```

当前**没有**找到 `call [reg+0x1610]` 的直接调用点。
因此 callback 触发者仍是 UNKNOWN。

### 5. `0x633FE0` 回调注册

`0x633FE0` dword refs：

```
0x7E7E8D, 0x7E7F46
```

`0x7E7E30` 注册流程：

```asm
007E7E36  call 0x7E7D30
007E7E3E  call 0x803830            ; 全局网络单例
007E7E4F  call 0xB7A670            ; 状态查询
007E7E54  cmp eax, 2
007E7E57  jne 0x7E7ED8
007E7E6E  call 0xB8E7B0            ; 取 payload / 事件
007E7E8C  mov esi, 0x633FE0        ; callback
007E7EA5  call 0x7FAB70            ; 注册
```

### 6. `0x634240 → 0x634080`

`0x634240` 是 callback wrapper：

```asm
00634240  ...
0063424A  mov eax, [ebp+8]
0063424D  mov ecx, [eax+0x25C8]    ; matching object
00634254  call 0x634080
```

`0x634080` 是状态码处理器（不是网络 handler）：

```
比较 [esi+0x27C] ∈ {8, 0x1E, 0x26, 0x2A}
```

它在以下情况下被调用：

```
0x62F5FE
0x633E39
0x633E50
0x634254（0x634240 wrapper 内）
```

当前未找到它直接：

- 修改 `+0x278`
- 调用 `+0x140`
- 修改 `+0xE360`
- 修改 reservation array
- 修改 A/B

它是匹配状态机的 transition/event adapter，不能直接称为 Booking response handler。

---

## P2：accepted handler 的 5 个参数

### 已知签名

```
0x632680  thiscall，ret 0x14，5 个参数

ARG0 = this
ARG1 = [ebp+8]    与 [this+0x3A048] 比对
ARG2 = [ebp+0xC]  与 [this+0x3A04C] 比对
ARG3 = [ebp+0x10] 当前未读到用途
ARG4 = [ebp+0x14] 响应字符串指针，与 "mmbook accepted" 比较
```

### 参数来源

在镜像内没有找到 5 参数形式的调用点。
因此：

```
ARG0/ARG1/ARG2/ARG3/ARG4 调用来源 = UNKNOWN
```

只能确认：

```
ARG1 必须等于 A
ARG2 必须等于 B
ARG4 必须指向 15 字节 "mmbook accepted"
```

不能把第 4 参数写成 reservation 或 endpoint。

---

## P3：Base.dll

保持第三阶段：

```
BOOKING_REFERENCE = NOT_FOUND
```

本轮没有发现 `0x633FE0 / 0x634240 / 0x634080` 的跨 DLL 调用。
不继续扩大 Base.dll 搜索。

---

## P4：响应通道判定

```
RESPONSE_CHANNEL = UNKNOWN
```

原因：

- `0x803830` 只是全局网络单例，不对应 Booking；
- `0xB7A670` 是通用状态查询；
- `+0x1610` callback 触发者未定位；
- `0x633FE0` 注册的是通用事件回调；
- 没有出现 packet/opcode/service/task → handler → `0x632680` 的证据。

不得提前升级。

---

## P5：最终验收

| 检查项 | 状态 |
|---|---|
| `0x62F840` caller | 只有 vtable 引用；行为已由 `0x637720` 覆盖 |
| `0x62F840` ARG1 | CONFIRMED（mode/flag） |
| `0x62F840` ARG2 | CONFIRMED（reservation index） |
| `0x62F840` ARG3 | CONFIRMED（byte） |
| ARG2 source | CONFIRMED（本地匹配结果副本下标） |
| reservation item | CONFIRMED（`this+0x7470 + i*0x238`） |
| A/B | CONFIRMED（`item+0x168/+0x16C`） |
| `0x803830` object | CONFIRMED（全局网络单例） |
| `0xB7A670` | CONFIRMED（状态查询，非类型） |
| callback slot | CONFIRMED（`+0x1610`） |
| callback trigger | UNKNOWN |
| response channel | UNKNOWN |
| accepted handler caller | UNKNOWN |
| Booking → 28960 | UNKNOWN |

---

## 最终判断

第四阶段成功完成了 P0：

```
0x62F840 ARG2
 → [this+0xE360]
 → reservation[index]
 → item
 → item+0x168 = A
 → item+0x16C = B
```

但 P1 只完成到通用网络单例与 callback 注册层，
没有把 callback 触发者追到 `0x632680`。

因此本轮不报告 BATTLE_ENTRY，也不实现 Server。

```
RESPONSE_CHANNEL = UNKNOWN
ACCEPTED_HANDLER_CALLER = UNKNOWN
BOOKING_28960_LINKAGE = UNKNOWN
```

下一阶段若仍纯静态，唯一值得继续的边界是：

```
0xB82034 读取 [ebx+0x1610] 的完整调用者
```

否则应宣告：

```
STATIC_RECOVERY_LIMIT_REACHED
```

