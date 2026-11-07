# 08 — 证据登记（E-15 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/_EVIDENCE_REGISTER.md 及 E-10..E-14 的同名追加。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-15-01 | SEMANTICS | 0x672460 | OpenSSL 读方法薄包装；引用 ".\\ssl\\ssl_lib.c"（0xC5650C）；对象方法虚分派 | out_6104d0.txt | PROVEN |
| EV-15-02 | CALLSITE | 0x672460 | 全镜像仅 2 处调用：0x6104E3、0x67F5F0 | out_sslmethods.txt | PROVEN |
| EV-15-03 | BUFFER | 0x6104D0 | 输出缓冲 = [ebp+0xb]，容量 1 字节，栈局部，返回后失效 | out_6104d0.txt | PROVEN |
| EV-15-04 | SEMANTICS | 0x6104D0 | 布尔探测（peek）：>0 返回 1；<=0 返回 0/-1；1 字节被丢弃 | out_6104d0.txt | PROVEN |
| EV-15-05 | SEMANTICS | 0x605220 | 连接就绪探测：超时检查 + 1 字节探测 + recv 2 字节探测 | out_6104d0.txt | PROVEN |
| EV-15-06 | REFUTE | 0x6104D0 / 0x605220 | 无明文外传（E-14 的 TLS 明文假设被否定） | 02 第2节 | REFUTED |
| EV-15-07 | MODULE | 客户端镜像 | 内联 libcurl：0xC36C8F libcurl、0xC373C6 libcurl error、0xC3743E libcurl! Edit at your own risk. | out_t14_owner.txt | PROVEN |
| EV-15-08 | MODULE | 0xC5B440 / 0xC38340 / 0xC38934 | HTTP 报文串：GET %s HTTP/1.1、Content-Length、HTTP/1.0 keepalive | out_t13_xrefs.txt | PROVEN |
| EV-15-09 | HOST | 0xD28CA0 | http://down-update.qq.com/ ；引用者 0x18C5B0、0x245CE0 | out_t13_xrefs.txt | PROVEN |
| EV-15-10 | REFUTE | 0x602BC0 | 对象状态重置/清理函数（fldz 清字段 + free 旧对象）；其簇为属性 getter 分派器 | out_callers.txt | REFUTED（应用层入口） |
| EV-15-11 | REFUTE | 0x612E80 | 与 0x602BC0 同模块（共享 0x5F9070）；就绪探测 | out_t08_up.txt | REFUTED（应用层入口） |
| EV-15-12 | NULL | 0x605220 六层闭包 | 不含 0xA2660 / 0x3547D0 / 0x350170 / 0x34FD80 / 0xA2E50 | out_t15_final.txt | 未发现（限定） |
| EV-15-13 | BOUNDARY | 0x67F5F0 | 所属函数无标准 prologue；fs() 误判为 0x631E10（跨 317 KB） | 02 第3节 | BLOCKED |
| EV-15-14 | HASH | 三样本 | 冻结基线本轮复核一致 | Get-FileHash | PROVEN |