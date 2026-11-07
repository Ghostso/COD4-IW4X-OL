# 02 — TLS 输出缓冲区数据流 / TLS OUTPUT BUFFER DATAFLOW

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 输出缓冲区清单（逐处追踪）

| 调用点 | 输出缓冲 | 容量 | 生命周期 | 数据去向 |
|---|---|---|---|---|
| 0x6104E3（0x6104D0） | [ebp+0xb] | 1 字节 | 栈帧内 | 函数返回后丢弃（无存储） |
| 0x67F5F0（0x631E10 区段） | 调用者栈参数 | 调用者指定 | 调用者栈帧 | 需追踪调用者（见第3节） |

## 2. 0x6104D0 的数据流（DIRECT，完整）

    SSL 对象 [obj+0x188]
       到 0x6104E3 call 0x672460
    [ebp+0xb]（1 字节，栈局部）
       到 0x6104EB test eax,eax        <- 只看返回值
    返回值 (1 / 0 / -1)
       到 0x605220 的调用者
    [nothing]                        <- 1 字节从未被读到、保存或转发

结论（PROVEN）：0x6104D0 不产生任何可用的明文数据流。1 字节栈局部在函数返回时失效。这不是"TLS 解密后的应用层明文"。

## 3. 0x67F5F0 调用点（INFERRED）

    67F5B3  mov eax,[esi+0x20]
    67F5B7  call eax                   ; 对象方法（预检）
    67F5BC  test eax,eax
    67F5BE  js 0xA7F606 / jne 0xA7F5E5
    67F5E5  mov ecx,[esp+0x10]         ; 参数3
    67F5E9  mov edx,[esp+0xc]          ; 参数2
    67F5ED  push ecx / push edx / push esi
    67F5F0  call 0xA72460              ; SSL 读（buf, len 来自调用者）

说明：此调用点确实接收调用者提供的 buf/len，是通用读接口。但其所属函数边界在 fs() 启发式下被误判为 0x631E10（跨 317 KB，不合理）——说明该区域缺少标准 push ebp; mov ebp,esp prologue。

裁定：该调用点的直接调用者未能可靠确定（BLOCKED），原因是函数边界启发式失效。

## 4. 是否存在独立缓冲区、队列或共享对象

| 检查 | 结果 |
|---|---|
| 0x6104D0 是否写入对象字段 | 否（只读 1 字节到栈） |
| 0x6104D0 是否写入全局 | 否 |
| 0x605220 是否复制明文到对象 | 否（其 recv 目标为 [ebp+0xB]，2 字节栈局部） |
| 是否存在"读到缓存到回调" | 未发现（在此链内） |

## 5. 与 HTTP/libcurl 模块的归属确认（PROVEN）

客户端网络簇引用以下字符串：

| 字符串 | VA | 引用者 |
|---|---|---|
| libcurl / libcurl error | 0xC36C8F / 0xC373C6 / 0xC3743E | libcurl 内建 |
| GET %s HTTP/1.1 Connection close Host | 0xC5B440 | 0x6B3840 区段 |
| Content-Length | 0xC38340 等 4 处 | libcurl |
| POST request / POST to GET | 0xC383FC / 0xC37CD4 | libcurl |
| HTTP/1.0 connection set to keep alive | 0xC38934 | 0x60C8A0（0x60CE03） |
| http://down-update.qq.com/ | 0xD28CA0 | 0x18C5B0、0x245CE0 |

结论（PROVEN）：0x605220 / 0x6104D0 / 0x672460 所属的网络栈是 HTTP/HTTPS 客户端（libcurl + OpenSSL），服务于更新/下载模块。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 0x6104D0 明文外传 | REFUTED |
| 0x605220 明文外传 | REFUTED |
| 存在独立明文缓冲/队列 | 未发现（限定范围） |
| TLS 栈归属 | PROVEN（HTTP/libcurl，非游戏协议） |
| 0x67F5F0 调用者 | BLOCKED（prologue 启发式失效） |