# 04 — 应用层入口候选 / APPLICATION ENTRY CANDIDATES

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 0x602BC0 的真实性质（PROVEN）

    602BC0  push ebp / mov ebp,esp / fldz
    602BCA  fst qword [esi+0x4F0]      ; 清多个浮点/状态字段
    ...
    602BF6  mov eax,[esi+0x8734]       ; 释放旧对象
    602C23  call [0xD07E80]            ; free
    602C2C  mov [esi+0x8734],0
    ...
    602C5D  xor eax,eax / ret

裁定（PROVEN）：0x602BC0 是对象状态重置/清理函数（reset/cleanup），不是消息处理入口。

其兄弟函数（0x602C70 到 0x602E00）是属性 getter 分派器：

    602C76  cmp edx,0x28 / ja 0xA02CE8
    602C82  jmp dword [edx*4 + 0xA02CF0]   ; 属性 ID 跳转表
    602C89  mov eax,[eax+0x478] ...

即：0x602BC0 所在簇是"连接对象属性访问器"，0x605220 调用只是其中一个属性分支（0x602DD9）。

## 2. 0x612E80 的真实性质（INFERRED）

0x612E80 的唯一调用者是 0x600630（深度 2 上游收敛到 0x5F9070、0x601270 等）。该簇与 0x602BC0 簇共享深度 3 上游（0x5F9070），属同一模块。

裁定（INFERRED）：0x612E80 与 0x602BC0 同属"连接/传输对象"模块；其 0x605220 调用同为就绪探测。

## 3. 应用层入口候选评估

| 候选 | 证据 | 裁定 |
|---|---|---|
| 0x602BC0 | 状态重置 + 属性 getter 簇 | REFUTED（非入口） |
| 0x612E80 | 同模块，就绪探测 | REFUTED（非入口） |
| 0x605220 | 就绪探测（1 字节 peek + recv 2 探测） | REFUTED（非入口） |
| 0x6104D0 | 1 字节探测，数据丢弃 | REFUTED（非入口） |
| 0x60E5B0 | vsnprintf（E-14 已证） | REFUTED |
| 0x6029A0 | recv 错误日志（E-14 已证） | REFUTED |
| 0x245CE0 | 引用 down-update.qq.com（更新模块） | REFUTED（非游戏协议） |
| 0x1B0430 | 通用 socket 事件（E-13） | BLOCKED |
| 0x78772D | 含 .tvm0 调用（E-13） | BLOCKED |

## 4. 剩余候选（收窄后）

E-13 的 4 条候选经 E-14/E-15 排除 3 条后，仅剩 2 条：

| 候选 | 上游 | 状态 |
|---|---|---|
| 0x1B0430 | 无直接调用者（数据指针 .text@0x1B007F） | BLOCKED |
| 0x78772D | 无直接调用者 | BLOCKED（含 .tvm0） |

## 5. 关键结论：TLS 栈与游戏协议无关（PROVEN）

0x605220 所属模块引用 "http://down-update.qq.com/"、libcurl 与 HTTP 报文串。该模块是更新/下载器，不是游戏网络协议栈。

这意味着：E-14 提出的"TLS 解密后明文，到应用层分派，到 Gamestate"假设，其起点即被否定。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 0x602BC0 是应用层入口 | REFUTED |
| 0x612E80 是应用层入口 | REFUTED |
| 0x605220 是应用层入口 | REFUTED |
| TLS 栈服务 HTTP 更新 | PROVEN |
| 游戏协议走 TLS | REFUTED（至少不走该 TLS 栈） |
| 剩余实时候选 | 0x1B0430、0x78772D（BLOCKED） |