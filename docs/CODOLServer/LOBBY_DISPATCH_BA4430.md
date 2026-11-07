# 大厅消息分发器 0xBA4430 —— 0x85 处理器对象定位（2026-09-30）

来源：可读运行期镜像
`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
（`0xBA3710` / `0xBA4430` 在该镜像中是**真实代码**）。

---

## 1. 分发器骨架

```asm
00BA4430  push ebp / mov ebp,esp
00BA4458  mov esi, ecx                 ; ecx = 连接对象（this）
00BA445A  cmp dword [esi+0xC8], 4      ; 状态 4 -> 直接返回
00BA4479  call 0xBA24C0                ; 预处理
00BA447E  cmp dword [esi+0xC8], 2      ; 状态 2 分支
00BA448F  mov ecx,esi / call 0xBA41D0
00BA449E  mov ecx,esi / call 0xBA0CC0
00BA44AD  mov ecx,[esi+0xB0] / call 0xB9BBB0   ; 取消息流 -> ebx
00BA44B8  mov edi,[esi+0xAC]                   ; 长度 -> edi（dec edi）
00BA44D8  call 0xB765A0                        ; 解帧：取 opcode 与长度
00BA44E8  mov eax,[esi+0x5E8]                  ; 阶段标志
```

分派（按 `[esi+0x5E8]` 与 opcode）：

| 阶段 | opcode | 处理 |
|---|---|---|
| 1 | `0x81` | `call 0xBA3C70` |
| 2 | `0x83` | `call 0xBA3BA0`（含检查 `[esi+0x644]`） |
| 2 | `0x84` | `call 0xBA0E20` |
| 2 | 其它 | `call 0xBA3420`（复位）+ 错误码 |
| **3** | **`0x85`** | **`call 0xBA3710`** ← 本节关注 |
| 3 | `0x84` | `call 0xBA0E20` |

---

## 2. ★ 0x85 处理器的调用约定（逐条实证）

```asm
00BA46AE  cmp al, 0x85                 ; 阶段==3 且 opcode==0x85
00BA46B2  mov ecx, [ebp+0x0C]          ; 参数3
00BA46B5  mov edx, [ebp+0x08]          ; 参数1
00BA46B8  mov eax, [ebp-0x14]          ; 解出的消息长度
00BA46BB  push ecx                     ;  [ebp+0x18] = 参数3
00BA46BC  push edx                     ;  [ebp+0x14] = 参数1
00BA46BD  push edi                     ;  [ebp+0x10] = 长度
00BA46BE  push eax                     ;  [ebp+0x0C] = 消息长度
00BA46BF  push ebx                     ;  [ebp+0x08] = 消息缓冲
00BA46C0  mov ecx, esi                 ;  this = 连接对象
00BA46C2  call 0xBA3710
```

⇒ **`0xBA3710` 的 `edi` 就是 `esi`，也就是 `ecx` 传入的连接对象。**

处理器内部对该对象的引用（与反汇编一致）：

| 偏移 | 用途 |
|---|---|
| `+0x0C8` | 连接状态（2/3/4） |
| `+0x5E8` | 阶段标志（1/2/3） |
| `+0x5EC` | **收包计数器**（0x85 seq 闸） |
| `+0x644` | 0x83 后的分支标志 |
| `+0xB0` | **消息流对象**（`call 0xB9BBB0` 取其内容） |
| `+0xAC` | 消息长度 |
| `+0x620` | **握手密钥材料**（喂 `0xBA02A0`） |
| `+0x638` / `+0x63C` | token（0x81 阶段写入） |
| `+0x328` | **MAC 密钥材料**（`0xC77ED0` 里 `xor 0x5C`） |

---

## 3. 对服务端实现的意义

先前 SESSION 文档记录："`0x85` 处理器的 `edi` 对象地址仍未定位"，
并两次把 `[mgr+0x4F4]` 误当成该对象。

**现在确定**：该对象 = **分发器 `0xBA4430` 的 `ecx` / `esi`**，
即**大厅连接对象本身**（不是 `[mgr+0x4F4]` 指向的请求对象）。

因此运行期只需求一次该对象的地址，即可同时读出：

| 字段 | 用途 |
|---|---|
| `+0x620` | 握手密钥 → `0xBA02A0` → key20 |
| `+0x328` | MAC 密钥材料 |
| `+0xB0` / `+0xAC` | 报文流 / 长度 |
| `+0x5EC` | 收包计数器（seq 闸） |

这四者正是复刻 `0x85` keyed-SHA1 MAC 所需的全部输入（见
`LOBBY_0x85_MAC_20260930.md`）。

---

## 4. 边界

纯离线反汇编，只读。
