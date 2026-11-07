# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001"
F={}
F["E17_EVIDENCE_REGISTER.md"]="""# E17 — 证据登记 / EVIDENCE REGISTER

> 新增证据 ID（E-17 系列）。所有证据来自本轮自建脚本与恢复镜像原始字节；无 IDA/Ghidra 人工标注被当作原始事实。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-17-01 | IDENTITY | 0x6B4DE0 | recvfrom 薄封装：入口 55 8B EC 83 EC 18（标准 prologue）；调用 recvfrom@0x6B4E3C、ntohs@0x6B4E92/0x6B4F10；唯一调用者 0x783F00@0x783F5E | out_candidates.txt | PROVEN |
| EV-17-02 | IDENTITY | 0x784F60 | recv 薄封装：入口 55 8B EC 57 8B 7D 08；调用 recv@0x784F7D；唯一调用者 0x783B70@0x783B7E | out_candidates.txt | PROVEN |
| EV-17-03 | GLOBAL | 0xD47388/0xD4738C/0xD47398/0xD4739C | 0x6B4DE0 累加 socket 字节/计数统计（0x6B4F25/0x6B4F2E/0x6B4F34/0x6B4F3D） | out_t09_final | PROVEN |
| EV-17-04 | GLOBAL | 0xD47370/0xD47374 | 0x784F60 写 WSA 错误码与状态码（0x784FC9/0x784FD0/0x784FE3/0x784FE9）；读取者 0x6B4920 | out_t09_final | PROVEN |
| EV-17-05 | BOUNDARY | 0x783F00 | 分配栈缓冲 [ebp-0x118]，交 recvfrom 封装，再复制 0x84 字节并交 0xA84CE0 | out_783cluster.txt | PROVEN |
| EV-17-06 | MODULE | 0xC5B324/0xC5ADD0/0xD36C70 | Demonware 标识串：demonware.net、DW-Client-Ticket-Size、bdSessionParams@@ | out_t06_dw | PROVEN（字符串存在） |
| EV-17-07 | VTABLE | .rdata 0xC9F794 | 0x783xxx 簇虚表；紧邻 rsa_import/DW-RSAENC/ECC-521 常量 | out_t05_vtable | PROVEN |
| EV-17-08 | NULL | 5 个 Demonware 根 × 7 层 | 不含 0xA2660/0x3547D0/0x354100/0x350170/0x34FD80/0xA2E50/0x3524F0/0x352570 | out_t07_reach | PROVEN（负） |
| EV-17-09 | INVENTORY | 全 .text | recv 7 / recvfrom 3 / send 5 / sendto 4 个调用点（含 jmp thunk） | out_t08_allrecv | PROVEN |
| EV-17-10 | HASH | 三样本 | 冻结基线开工/收工各复核一次，均一致 | Get-FileHash | PROVEN |

## 证据等级说明

- PROVEN：指令字节/调用边/数据流可复核。
- PROVEN（负）：在明确限定范围内未命中。
- INFERRED：模块归属（Demonware）依赖字符串与调用簇同处一节，但无源码或符号级直接对应。
"""
F["E17_HYPOTHESIS_LEDGER.md"]="""# E17 — 假设台账 / HYPOTHESIS LEDGER

> 格式：陈述 / 支持 / 反证 / 状态 / 下一步

---

### H-E17-01：0x6B4DE0 是 recvfrom 薄封装
- 支持：入口标准 prologue；调用 recvfrom@0x6B4E3C；参数 (sock,buf,len,flags,from,fromlen) 直接转（EV-17-01）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E17-02：0x784F60 是 recv 薄封装
- 支持：入口标准 prologue；调用 recv@0x784F7D（EV-17-02）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E17-03：两候选属 Demonware 传输/会话栈
- 支持：调用者簇与 demonware.net / DW-Client-Ticket / bdSessionParams@@ / DW-RSAENC 同镜像（EV-17-06/07）
- 反证：无源码或公开符号直接对应
- 状态：**STRONG_INFERENCE**
- 下一步：若有公开 Demonware 文档/符号，交叉验证

### H-E17-04：两候选是游戏会话入站路径
- 支持：（无）
- 反证：7 层闭包不含任何游戏解析候选（EV-17-08）；数据交 Demonware 对象（EV-17-05）
- 状态：**REFUTED（限定范围）**
- 下一步：无

### H-E17-05：两候选写入环形缓冲或消息队列
- 支持：（无）
- 反证：仅写 socket 统计/状态全局（EV-17-03/04）；无 0x3524F0/0x352570 引用
- 状态：**REFUTED**
- 下一步：无

### H-E17-06：0xD47370/0xD47374 是消息状态
- 支持：（曾疑为消息状态）
- 反证：消费者 0x6B4920 是错误/状态查询函数；写入的是 WSA 错误码与状态码 2（EV-17-04）
- 状态：**REFUTED**
- 下一步：无

### H-E17-07：游戏协议入站路径仍存在（未定位）
- 支持：E-12..E-16 已排除多条非游戏路径
- 反证：本轮又排除 2 个候选
- 状态：**BLOCKED**
- 下一步：审计 0x775A50/0x775AB0 虚表实例化路径

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-15：TLS 栈属 HTTP 更新模块 | 保留（CONFIRMED） |
| E-16：0x1B0430 属 ICMP ping | 保留（CONFIRMED） |
| E-16：0x78772D 是时间戳工具 | 保留（CONFIRMED） |
| E-13：0x3524F0 是环形缓冲写侧 | 保留（但属发送暂存） |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
