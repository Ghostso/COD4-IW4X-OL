# E17 — 证据登记 / EVIDENCE REGISTER

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
