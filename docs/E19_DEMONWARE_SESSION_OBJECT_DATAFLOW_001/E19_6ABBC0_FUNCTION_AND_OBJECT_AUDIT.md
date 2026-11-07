# E19 — 0x6ABBC0 函数与对象审计 / FUNCTION AND OBJECT AUDIT

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 函数边界与调用约定（PROVEN）

| 项 | 值 |
|---|---|
| RVA | 0x6ABBC0 |
| 边界 | 0x6ABBC0 .. 0x6ABC7D（`ret` @0x6ABC4C / 0x6ABC6B / 0x6ABC7C；其后 int3） |
| 大小 | 0xBE 字节 |
| 调用约定 | `thiscall`（ECX=this）+ 无参数 |
| 直接调用者 | **唯一**：`0x6ABF1F`（在 `0x6ABE80` 内） |
| 数据指针引用 | 0 |
| 立即数引用 | 1（`0x6ABF1F`） |

## 2. 完整指令（PROVEN）

    6ABBC7  mov esi,ecx
    6ABBC9  mov eax,[esi+0xA4]        ; 已缓冲字节数
    6ABBD5  sub ecx,eax               ; 4 - 已读
    6ABBD7  push ecx                  ; 剩余长度
    6ABBD8  lea edx,[eax+esi+0xA0]    ; dst = headerBuf + used
    6ABBDF  push edx
    6ABBE0  lea ecx,[esi+0xC4]        ; 传输对象
    6ABBE6  call 0xB83B70             ; → Demonware recv 封装（E-17 的 0x784F60 族）
    6ABBED  test edi,edi / jle
    6ABBF5  add [esi+0xA4],edi        ; used += n
    6ABBFB  cmp dword [esi+0xA4],4
    6ABC02  jne 0xAABC78              ; 未满 4 字节 → 返回
    6ABC04  push 4 / lea eax,[ebp-8] / lea ecx,[ebp-4] / push 0
    6ABC10  lea edx,[esi+0xA0]        ; src = headerBuf
    6ABC20  call 0xA878A0             ; 边界检查 + memcpy（→ 0x6878A0）
    6ABC28  test al,al / je
    6ABC2C  mov eax,[ebp-8]           ; 解析出的长度
    6ABC2F  mov [esi+0xAC],eax        ; 存长度
    6ABC35  mov eax,[esi+0xAC]
    6ABC3B  test eax,eax / jne
    6ABC3F  mov [esi+0x9C],eax        ; 长度为 0 → 状态 0
    6ABC4D  cmp eax,[esi+0x98]        ; 与上限比较
    6ABC53  jbe 0xAABC6C
    6ABC55  call 0x43A7C0             ; 超限：错误上报
    6ABC5C  call 0x6AA770             ; 清理/置错误状态
    6ABC62  mov eax,0xFFFFFFF5        ; 返回 -11
    6ABC6C  mov [esi+0x9C],2          ; 状态 = 2（读体）
    6ABC76  mov eax,edi / ret

## 3. 对象字段映射（PROVEN）

| 偏移 | 语义 | 写入点 / 读取点 |
|---|---|---|
| +0x98 | **长度上限** | 读 @0x6ABC4D |
| +0x9C | **接收状态**（0/1/2/3/4） | 写 @0x6ABC3F/0x6ABC6C |
| +0xA0 | **4 字节头缓冲** | 写 @0x6ABBD8；读 @0x6ABC10 |
| +0xA4 | **已缓冲字节数** | 读写 @0x6ABBC9/0x6ABBF5/0x6ABBFB |
| +0xA8 | 类型码字节（E19 第二阶段） | 写 @0x6A994C |
| +0xAC | **解析出的帧长度** | 写 @0x6ABC2F |
| +0xB0 / +0xB4 | 两个 C++ 对象指针（经 `operator delete` 释放） | 0x6ABEB8..0x6ABF08 |
| +0xC4 | 传输对象（传给 0xB83B70） | @0x6ABBE0 |
| +0xC8 | 连接状态（1/2/4） | 0x6AA773/0x6AA791 |

## 4. 返回值

| 情况 | 返回 |
|---|---|
| 未读满 4 字节 | `n`（本次读到的字节数） |
| 长度为 0 | `n`，状态 0 |
| 长度超限 | **-11**（0xFFFFFFF5） |
| 正常解析 | `n`，状态 2 |

## 5. 类别判定（任务书第三节分类）

| 类别 | 判定 |
|---|---|
| socket 操作 | 否（经 0xB83B70 封装间接读取） |
| socket 对象接口方法 | 否 |
| 事件调度/回调 | 否 |
| 仅管连接状态 | 否 |
| **协议帧解析** | **是（PROVEN）** |
| **游戏应用层消息消费** | **BLOCKED**（类型码 1/2 语义未定） |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 函数边界与调用约定 | PROVEN |
| 4 字节长度前缀分帧 | **PROVEN** |
| 边界检查与长度上限 | PROVEN |
| 接收状态字段 +0x9C | PROVEN |
| 是否为协议帧读取器 | **PROVEN** |
| 是否游戏消息 | BLOCKED |
