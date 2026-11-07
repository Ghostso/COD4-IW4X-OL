# E19 — 会话状态与数据流 / SESSION STATE AND DATAFLOW

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 接收状态机（PROVEN）

调用者 `0x6ABE80`：

    6ABE80  mov ebx,[esi+0x9C]        ; 接收状态
    6ABE89  cmp ebx,3
    6ABE8C  ja 0xAAC084               ; 越界
    6ABE92  jmp [ebx*4+0xAAC090]      ; 4 状态跳转表

**跳转表（RVA 0x6AC090，PROVEN）：**

| 状态 | 目标 RVA | 语义 |
|---|---|---|
| 0 | 0x6ABE99 | 重置 + 释放子对象 + 状态→1 |
| 1 | 0x6ABF1D | 调 0x6ABBC0 读 4 字节头 |
| 2 | 0x6ABF47 | 调 0x6A9920 读类型码 + 载荷 |
| 3 | 0x6ABF52 | 调 0x989230/0xAC4070 → 0xB83B70 |

## 2. 状态迁移（PROVEN）

```
state 0 (reset)
   └─ +0x9C = 1 ─────────────► state 1: 0x6ABBC0 读 4 字节头
                                     │
                    ┌────────────────┴────────────────┐
                长度=0                         长度>0 且 <= 上限
                    │                                │
              +0x9C = 0                      +0x9C = 2
              （回到 state 0）                       │
                                        ┌───────────┴───────────┐
                                   进入 state 2            长度 > 上限
                                           │                     │
                          0x6A9920 读 1 字节类型码        报错 + 0x6AA770
                                  + 载荷                  返回 -11
                                           │
                              类型码==1 → size=1
                              类型码==2 → size=9
                                           │
                              0xAA84E0（分配 +0xB0）
                                           │
                              0x6A9A30（第二次 memcpy，长度 5）
```

## 3. 数据流（PROVEN，关键）

```
[网络 socket]
   └─ 0xB83B70（E-17 的 Demonware recv 封装）
         └─ recv(sock, dst, len, 0)
    ↓
0x6ABBC0（帧头读取器）
   ├─ dst = [esi+0xA0]（4 字节头缓冲）
   ├─ used = [esi+0xA4]
   └─ 满 4 字节 → 0x6878A0（边界检查 + memcpy）
         └─ 长度 → [esi+0xAC]
   ↓
0x6A9920（状态 2：类型码 + 载荷）
   ├─ 读 1 字节 → [esi+0xA8]（类型码）
   ├─ cmp al,1 → size 1 ; cmp al,2 → size 9
   ├─ 0xAA84E0(this, len, 1) → 分配 [esi+0xB0]
   └─ 0x6A9A30（第二次 memcpy，长度 5）
```

## 4. 类型码分派（PROVEN 存在，语义 BLOCKED）

```asm
6A9969  mov al,[edi]              ; edi = &[esi+0xA8]（类型码）
6A996B  mov ebx,1
6A9970  cmp al,1
6A9972  je  0xAA9978
6A9974  cmp al,2
6A9976  jne 0xAA997D
6A9978  mov ebx,9                 ; 类型码 2 → size 9
6A997D  push 0x2C / lea edi,[ebx+1]   ; 分配 edi 字节
```

| 类型码 | size | 说明 |
|---|---|---|
| 1 | 1 | 短消息 |
| 2 | 9 | 长消息 |
| 其他 | 1 | 默认 |

**关键（PROVEN）：这是**单一 1 字节类型码 + 二值分支**，**不是** CODOL 游戏 opcode 表（游戏为 `0x01`..`0x04` 顶层分派 + 0..8 子帧）。**

## 5. 与游戏 opcode 的对比

| 层 | CODOL 游戏（E-11..E-17） | E-19 Demonware 会话 |
|---|---|---|
| 消息类型编码 | 1..4（顶层，表在 0x75025C） | 1 或 2（单一字节，二值分支） |
| 分帧 | 未定位 | **4 字节长度前缀** |
| 子帧 | 0..8（表在 0x7547AC） | 无 |
| 状态机 | 未定位 | **4 状态** |

**裁定（BLOCKED）：两者**可能**是不同协议层，但**未建立数据连接**。不能因"都有类型码"就视为同一分派。**

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 4 状态接收状态机 | PROVEN |
| 状态迁移路径 | PROVEN |
| 长度前缀数据流 | PROVEN |
| 类型码 1/2 分派 | PROVEN（存在） |
| 类型码语义 | BLOCKED |
| 与游戏 opcode 同源 | BLOCKED（未连接） |
