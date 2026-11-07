# 09 — 证据登记（E-16 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/_EVIDENCE_REGISTER.md 及 E-10..E-15 的同名追加。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-16-01 | IAT | 0x1B0430..0x1B0F30 | 核心网络原语为 ICMP 四件套：IcmpCreateFile(0xBAE098)、IcmpSendEcho2(0xBAE09C)、IcmpParseReplies(0xBAE094)、IcmpCloseHandle(0xBAE090) | out_t02_iat | PROVEN |
| EV-16-02 | SEMANTICS | 0x1B0430 | 服务器延迟测量（ping）：getaddrinfo 解析 0x2CCA3C8 服务器表 -> socket -> IcmpSendEcho2 -> recvfrom/IcmpParseReplies -> RTT | out_1b0430_full.txt | PROVEN |
| EV-16-03 | BRANCH | 0x1B086D/0x1B0991/0x1B0A25/0x1B0ADF | 四者非并列事件类型，而是 ICMP ping 的四个顺序阶段 | out_t08_branches | PROVEN |
| EV-16-04 | INBOUND | 0x1B0BA1 | 唯一入站点：recvfrom，缓冲 [esp+0x50]（栈上） | out_1b0430_full.txt | PROVEN |
| EV-16-05 | RESULT | 0x1B097A | RTT 写入 [obj+ebx+0x934]；无应用层消费者 | out_1b0430_full.txt | PROVEN |
| EV-16-06 | REFUTE | 0x1B0430 | 无分帧/队列/应用层分派（限定范围） | 03 第4节 | REFUTED |
| EV-16-07 | SEMANTICS | 0x78772D | 64 位时间戳换算（GetSystemTimeAsFileTime 0xBAE1C0 + 除法 0xB50980） | out_78772d.txt | PROVEN |
| EV-16-08 | REFUTE | 0x78772D | 无调用者、无数据指针引用、无 .tvm0 调用；与 0x1B0430 无调用/数据流边 | out_t06_verify | REFUTED |
| EV-16-09 | SECTION | 0xDBEF28A | 属 .data(BSS) 段（0x8F1000..0xD945420），非 .tvm0（0xD958000..）；E-13 的 tvm0 定性为 .rimp 修复伪影 | 04 第5节 | REFUTED（tvm0） |
| EV-16-10 | HASH | 三样本 | 冻结基线开工/收工各复核一次，均一致 | Get-FileHash | PROVEN |
