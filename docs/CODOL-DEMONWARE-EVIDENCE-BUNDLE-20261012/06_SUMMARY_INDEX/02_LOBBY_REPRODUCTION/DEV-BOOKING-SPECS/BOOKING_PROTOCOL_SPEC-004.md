# BOOKING_PROTOCOL_SPEC-004

> 第五阶段：`0xB82034` callback 槽最后边界
> 纯静态。未修改 Golden / Server / 4 个 patch / KDF hook。
> 未启动游戏，未发送 Booking response。
>
> 分析源：`image_best.bin`（VA 0x400000..0xE65000，10,899,456 B，已解壳）

---

## 0. 一句话结论

`0xB82034` 读取的 `[obj+0x1610]` **不是被直接间接调用**。
它被传给 `0xBA0DE0`，存进内部连接对象的 `+0xAE4`；
该字段仅在两处被读取，且两处都只是对回调对象做 vtable[0] 调用（清理/析构），
随后进入连接创建 / 状态机路径，**不进入**：

```
0x633FE0 → 0x634240 → 0x634080 → 0x632680
```

因此：

```
RESPONSE_CHANNEL = NOT_ESTABLISHED
NO_BOOKING_RESPONSE_LINK_ESTABLISHED
STATIC_RECOVERY_LIMIT_REACHED
```

继续纯静态扫描不会得到 Booking 响应入口。

---

## 1. `0xB82034` 所属函数

`0xB82034` 不是独立函数，它位于 `0xB81EF0` 尾部（入口 `0xB81EF0`，
`ret 0x98`）。完整上下文：

```asm
00B82011  mov ecx, [ebx+0x4F4]          ; connection object
00B82017  lea eax, [ebx+0x500]
00B8201D  push eax
00B8201E  mov byte [ebx+0x4F8], 0
00B82025  call 0xBA4080                 ; 建立/重启连接
00B8202A  mov ecx, ebx
00B8202C  mov [ebp-0xD], al
00B8202F  call 0xB7F7F0
00B82034  mov eax, [ebx+0x1610]         ; ← callback slot
00B8203A  mov ecx, [ebx+0x4F4]
00B82040  push eax
00B82041  call 0xBA0DE0                 ; 存进 connection+0xAE4
```

### 关键事实（CONFIRMED）

```
0xB82034 只是 READ，不是 CALL。
真正消费 callback 的地方在 connection object 内部。
```

---

## 2. callback 值去了哪里

```asm
00BA0DE0  push ebp
00BA0DE1  mov ebp, esp
00BA0DE3  mov eax, [ebp+8]              ; callback pointer
00BA0DE6  mov [ecx+0xAE4], eax          ; connection+0xAE4
00BA0DEC  pop ebp
00BA0DED  ret 4
```

`0xBA0DE0` 的直接调用者仅两处：

```
0xB7A657
0xB82041
```

即：

```
0xB7A640 setter（+0x1610 赋值）
0xB82034 读取后转存
```

callback 被保存到内部连接对象的 `+0xAE4`，类型为对象指针（后续通过 vtable 调用）。

---

## 3. `[connection+0xAE4]` 的全部访问

全镜像 `disp=0xAE4` 命中 20 处，与本对象相关的关键点：

```
0xBA0DE6  WRITE   [ecx+0xAE4] = callback        （0xBA0DE0）
0xBA29E0  WRITE   [esi+0xAE4] = 0               （清理）
0xBA24C9  READ    ecx = [esi+0xAE4]             （0xBA24C0）
0xBA3396  READ    ecx = [esi+0xAE4]             （0xBA3370）
其它命中为不同结构体偏移巧合
```

### 3.1 `0xBA24C0` 路径

```asm
00BA24C0  push ebp / mov ebp,esp / sub esp,0xC
00BA24C7  mov esi, ecx
00BA24C9  mov ecx, [esi+0xAE4]
00BA24CF  test ecx, ecx
00BA24D2  je 0xBA24DA
00BA24D4  mov eax, [ecx]                 ; vtable
00BA24D6  mov edx, [eax]                 ; slot 0
00BA24D8  call edx                       ; ★ 析构/释放，不是包处理
00BA24DA  lea ecx, [esi+0x510]
00BA24E0  call 0xC73030                  ; 容器/队列清理
...
00BA24FC  call 0xC739C0
00BA251A  mov dword [esi+0xC8], 2
00BA2524  call 0xBA32A0                  ; 状态转移
```

`0xBA24C0` 的直接调用者：

```
0xBA2EC7, 0xBA2FC7, 0xBA4479
```

均属于连接生命周期路径，不是 Booking 分发。

### 3.2 `0xBA3370` 路径

```asm
00BA3370  push ebp / mov ebp,esp
00BA3394  mov esi, ecx
00BA3396  mov ecx, [esi+0xAE4]
00BA339C  test ecx, ecx
00BA33A5  je 0xBA33AD
00BA33A7  mov eax, [ecx]
00BA33A9  mov edx, [eax]
00BA33AB  call edx                       ; ★ vtable[0]，清理
...
00BA33B6  push 0x86
...
00BA33D8  call 0xBA2A60                  ; 连接/状态机
```

同样，`+0xAE4` 只是被当作一个可清理对象，
没有出现 packet / message / opcode / service / task 参数。

---

## 4. callback signature 判定

### 4.1 setter 侧

```asm
00B7A640  mov eax, [ebp+8]
00B7A646  mov [ecx+0x1610], eax
00B7A64C  mov ecx, [ecx+0x4F4]
00B7A65C  ret 4
```

以及 `0xBA0DE0: ret 4`：

```
callback 被当成 **1 个参数** 传入。
```

### 4.2 消费侧

`0xBA24C0` / `0xBA3370` 只调用 `callback->vtable[0]`，
且在调用前后没有压入 5 个参数、没有 `0x632680` 的 `ret 0x14` 形状。

因此：

```
0x1610 callback signature = thiscall/void(), vtable slot 0
参数来源 = callback 对象自身
message/packet pointer = NOT_OBSERVED
status code            = NOT_OBSERVED
```

这与 `0x632680`（thiscall，ret 0x14，5 个栈参数，
需要 A/B 与 "mmbook accepted" 字符串）**完全不匹配**。

### 4.3 REFUTED

```
REFUTED: +0x1610 callback 直接调用 0x632680
REFUTED: +0x1610 callback 是 Booking accepted handler
REFUTED: 0xBA24C0 / 0xBA3370 是 Booking response parser
```

---

## 5. 与 `0x633FE0` / `0x634240` / `0x634080` 的关系

已确认：

```
0x633FE0  注册进通用网络回调链（0x7E7E8E / 0x7E7F46）
0x634240  callback wrapper
0x634080  处理状态码 {8, 0x1E, 0x26, 0x2A}
```

本阶段补充确认：

```
0x633FE0 的注册路径不读取 [obj+0x1610]
0x634240 / 0x634080 不读取 [obj+0xAE4]
0x634080 不调用 vtable +0x140
0x634080 不调用 0x632680
```

因此：

```
network callback
  → 0x633FE0
  → 0x634240
  → 0x634080
  → 匹配状态机

不是

network callback
  → decoder
  → booking dispatcher
  → vtable +0x140
  → 0x632680
```

### 结论

```
NO_BOOKING_RESPONSE_LINK_ESTABLISHED
```

网络 callback 存在，但它通往其它状态机，与
`0x632680` 没有已证实的连接。

---

## 6. 其它消费者检查

对 `+0x1610` 与 `+0xAE4` 的限定检查结果：

| 检查项 | 结果 |
|---|---|
| callback replacement | `0xB7A640` setter 覆盖写 |
| callback chaining | NOT_OBSERVED |
| wrapper | 存在（`0xBA0DE0` 转存） |
| indirect call | 仅 vtable[0] 清理调用 |
| deferred dispatch | NOT_OBSERVED（未见保存后用于包分发） |
| 包 / opcode / service / task | NOT_OBSERVED |

---

## 7. 最终证据等级表

| 项目 | 等级 |
|---|---|
| A_SOURCE = `item+0x168` | CONFIRMED |
| B_SOURCE = `item+0x16C` | CONFIRMED |
| reservation index = `[match+0xE360]` | CONFIRMED |
| index source = `0x637720` 本地匹配结果副本下标 | CONFIRMED |
| `0x6379E0` 拷贝 `this+0x340` → `this+0x7470` | CONFIRMED |
| `0x637590` 填充 `this+0x340` | CONFIRMED |
| `0x62F840` ARG1/ARG2/ARG3 | CONFIRMED |
| accepted handler = `0x632680` | CONFIRMED |
| accepted handler caller | UNKNOWN |
| `0x803830` = 全局网络单例 getter | CONFIRMED |
| `0xB7A670` = 连接/会话状态查询 | CONFIRMED |
| callback slot = `+0x1610` | CONFIRMED |
| callback 转存到 `connection+0xAE4` | CONFIRMED |
| `+0xAE4` 只被 vtable[0] 清理调用 | CONFIRMED |
| callback → `0x632680` | **REFUTED** |
| callback → `0x633FE0` / `0x634240` / `0x634080` | **REFUTED**（无调用边） |
| RESPONSE_CHANNEL | **NOT_ESTABLISHED** |
| Booking → 28960 linkage | UNKNOWN |
| findSessions / playlist=10 → `this+0x340` | UNKNOWN |
| Base.dll Booking reference | NOT_FOUND |

---

## 8. 收束判定

按第五阶段收束条件逐条对照：

```
A. network callback → decoder → booking dispatcher → 0x632680 ？
   → 未成立（REFUTED）

B. 网络 callback 存在，但通往其它状态机，与 0x632680 无连接 ？
   → 成立

C. 0xB82034 调用者跨出当前可见镜像/模块边界 ？
   → 未成立：调用者、转存点、消费点均在 EXE 内
```

因此：

```
RESPONSE_CHANNEL = NOT_ESTABLISHED
NO_BOOKING_RESPONSE_LINK_ESTABLISHED
```

并且因为 `+0x1610` 与 `+0xAE4` 的两条消费路径都已在 EXE 内穷尽，
没有新的静态引用可追：

```
STATIC_RECOVERY_LIMIT_REACHED
```

**静态阶段结束。**不再做第六轮、第七轮无边界静态扫描。

---

## 9. 下一阶段原则

转向运行期观测，目标严格限定为：

```
6/14
 → response
 → 0x632680
 → success
```

观测点：

```
0x632680 入口（thiscall，5 参数）
0x632680 成功分支 0x632736
0x632745  [esp+0x28]=1
0x62F902  [this+0xE360] 写入
0x62F6F0  A/B 写入
```

Golden 必须继续保持只读。
不得发送猜测性 Booking response。

---

## 10. 纪律核对

```
Golden 修改             = 无
Server 修改             = 无
4 个 Lobby patch 修改   = 无
KDF hook 修改           = 无
游戏启动                = 无
Booking response 发送   = 无
```

