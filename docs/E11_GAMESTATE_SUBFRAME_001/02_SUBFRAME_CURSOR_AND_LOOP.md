# 02 — 子帧游标与循环 / SUBFRAME CURSOR AND LOOP

> 等级：`DIRECT` / `INFERRED` / `BLOCKED`

---

## 1. 子帧分派器 `0x354100`（DIRECT）

```asm
354100  push ebp / mov ebp,esp
354117  mov eax,[0x7454988]
35411C  mov eax,[eax*4+0x1A65E0C]
354123  xor eax,0x20FD39B9
354150  movzx eax, byte [ebp+0xc]     ; 子帧编号
35415A  cmp eax, 8
35415D  ja  0x75479A                  ; 越界直接返回
354163  jmp dword [eax*4 + 0x7547AC]  ; 9 项跳转表
```

**跳转表 `0x7547AC`（DIRECT）：**

| 编号 | 目标 | 读取 |
|---|---|---|
| 0 | `0x35416A` | 1 字节 → 格式化 |
| 1 | `0x3541C4` | 4 字节 → float |
| 2 | `0x354200` | 1 字节 |
| 3 | `0x354264` | 1 字节 + 分支 |
| 4 | `0x354366` | 1 字节 + 3×float |
| 5 | `0x354468` | 4 字节 + 4 字节 |
| **6** | **`0x354697`** | **u32 len → len 字节载荷 → `0x352F80`** |
| 7 | `0x354740` | 1 字节 → `[esi+0x723C24]` |
| 8 | `0x354766` | 4 字节 |

## 2. 子帧循环 `0x3547D0`（DIRECT）

```asm
3547DF  mov ebx,1
3547ED  mov ecx,[esi+0x89244]
3547F3  push ebx / push eax / call ecx    ; 读 1 字节 → [ebp-4]
3547F7  mov eax,[ebp-4]
3547FD  cmp al,9
3547FF  je  0x75482A                      ; 9 → 退出检查
354801  cmp al,0xA
354803  je  0x75482E                      ; 10 → 返回 0
354805  push 1 / push eax / push edi
354809  call 0x754100                     ; 以该字节为子帧编号分派
35480E  mov eax,[esi+0x89244]
354817  push edi / push 1 / push [ebp-4]
35481E  call eax                          ; 再读 1 字节
354820  mov eax,[ebp-4]
354826  cmp al,9
354828  jne 0x754801                      ; 继续
35482A  cmp al,0xA
35482C  jne 0x754836
35482E  xor eax,eax / pop / ret           ; 返回 0
354836  mov eax,ebx / pop / ret           ; 返回 1
```

**游标关系（DIRECT）：**

| 步骤 | 读取 | 游标推进 |
|---|---|---|
| 入口 | 1 字节 = 子帧编号 | +1 |
| 子帧处理 | 由 case 决定 | 见 `03` |
| 每轮末 | 再读 1 字节 | +1 |
| 退出条件 | 读到 `0x09` 或 `0x0A` | — |

**关键（DIRECT）：** 循环**不是**由 `0x04`/`0x06` 驱动的；退出值是 `0x09`/`0x0A`。子帧编号来自每轮首字节，范围 0..8（越界直接返回）。

## 3. 循环的两条进入路径

| 路径 | 进入点 | 上游 |
|---|---|---|
| A | `0x350238 call 0x3547D0` | `0x350170`（顶层 opcode 4） |
| B | `0x351569 call 0x3547D0` | `0x3512A0`（网络 Gamestate 候选） |

两条路径在 `0x3547D0` 汇合，共用同一 9 项子帧分派器（DIRECT）。

## 4. `0x3512A0` 的游标序列（DIRECT）

```asm
35141E  mov [ecx+0x89244], 0x752570      ; 安装网络读取器
351433  push 4                            ; 读 4 字节
35143C  call 0x752570
351484  push 4                            ; 再读 4 字节
3514A3  call 0x752570
3514B6  call 0x752570                     ; 读长度字节载荷
3514F0  call 0xA2660                      ; Configstring body reader
3514F6  call 0x352FC0
351504  call 0x3530E0
35150D  call 0x3532F0
351516  call 0x3537D0
351561  push 1 / call [edx+0x89244]       ; 再读 1 字节
351569  call 0x3547D0                     ; 子帧循环
```

**`0x3512A0` 与 case 6 的后继完全一致**（`0x352FC0`/`0x3530E0`/`0x3532F0`/`0x3537D0`），说明二者是同一条消息链的两个入口（DIRECT）。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 子帧分派器与编号范围 | **PROVEN**（`0x354100`，0..8） |
| 子帧循环退出值 | **PROVEN**（`0x09`/`0x0A`） |
| 每轮字段宽度 | **PROVEN**（首字节 1 字节编号；case 内宽度见表） |
| 循环与 `0x04`/`0x06` 的耦合 | **REFUTED**：退出由 `0x09`/`0x0A` 决定 |
