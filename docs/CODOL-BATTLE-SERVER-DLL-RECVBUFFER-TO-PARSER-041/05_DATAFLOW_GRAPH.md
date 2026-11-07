# 05_DATAFLOW_GRAPH — 接收数据流图(已证实 / 未闭合)

**证据等级图例:** `[D]` CONFIRMED_DIRECT(机器码直接) · `[F]` CONFIRMED_DATAFLOW(可追踪数据流) · `[X]` CONFIRMED_CROSSREF · `[?]` UNKNOWN · `[B]` BLOCKED(保护区)

地址 `VA = 0x10000000 + RVA`。

---

## 1. 主数据流(接收侧)

```
                         +-------------------------------+
                         |  .tvm0 0x3512437              |  [B] 上游发起者(受保护)
                         |  call 0x1022D470              |      无法静态展开
                         +---------------+---------------+
                                         | (线程启动, 受保护区来源)
                                         v
                         +-------------------------------+
                         |  .text 0x22D470 ping 线程启动器|
  [D] CreateThread(0x22D53C, lpStart=0x10231050, lpParam=job)  |
  [F] map.insert(0x22D549->0x22D990)  job 对象                |
                         +---------------+---------------+
                                         | lpParameter = job (0x18 B)
                                         v
                         +-------------------------------+
                         |  .text 0x231050 线程过程       |
  [D] 0x231080 call 0x235CD0  -> 构造 D(socket+event+buf)       |
  [D] 0x2310B1/0x2310C1 call 0x22A670 -> 用 job+0x14 查 ping map   |
  [F] 0x2310D7 target_ip = rec[+0x34] -> D[+0] ... (send target) |
  [F] 0x2310DA out = &[esp+0x14]  (16B, 先清零)                 |
  [D] 0x2310E5 call 0x235E00(out, D)                            |
                         +---------------+---------------+
                                         |
                                         v
   +----------------------------------------------------------------+
   |  .text 0x235E00  D::sendrecv(out)                              |
   |                                                                |
   |  [D] 0x235E60 inc seq [D+0x12]                                 |
   |  [D] 0x235E8D 发送buf[0]=8 (ICMP Echo Request)                 |
   |  [D] 0x235E97 buf[+4]=pid  [D] 0x235E9A buf[+8]=seq            |
   |  [D] 0x235E9E buf[+0xC]=tick  [D] 0x2360B0 校验和              |
   |  [D] 0x235EC9 sendto(s,buf,0x30,...)  ----> 网络                 |
   |  [D] 0x235F23 WSAWaitForMultipleEvents(100ms)                  |
   |  [D] 0x235F4C WSAEnumNetworkEvents -> FD_READ                  |
   |  [F] 0x235F7E recvfrom(s, [ebp-0x10C], 0x100,...) <---- 网络    |
   |                                   |                            |
   |                          (栈缓冲: 原始 IP 包, <=256B)           |
   |                                   v                            |
   |  [F] 0x235F94 ihl = buf[0]&0xF  -> icmp_off = ihl*4             |
   |  [F] 0x235FAD id  = buf[icmp_off+4]  == D[+8] (pid)            |
   |  [F] 0x235FC0 type= buf[icmp_off+0]  == 0 (Echo Reply)         |
   |  [F] 0x235FCB seq = buf[icmp_off+8]  == D[+0x12]               |
   |  [F] 0x236058 rtt = tick() - buf[icmp_off+0xC]                 |
   |  [F] 0x236061 ttl = buf[8] (IP header TTL)                     |
   |  [F] 0x23606E plen= recvlen - icmp_off - 0x10                  |
   |  [F] 0x236068..0x236079 写 out{seq,rtt,plen,ttl}               |
   |  [D] 0x23607C xor eax,eax ; return 0   <-- NO payload copy     |
   +----------------------------------------------------------------+
                                         | out (16B) only
                                         v
                         +-------------------------------+
                         |  .text 0x231050 (续)            |
  [F] 0x231112 释放 D(closesocket/WSACloseEvent/free)            |
  [F] 0x231171 out+0x4(RTT) -> job+4                              |
  [F] 0x231175 out+0xC(TTL) -> job+8                              |
                         +---------------+---------------+
                                         |
                                         v
                         +-------------------------------+
                         |  job 对象(全局 map 0x22D470 管理)|  [X] job+4 = out+0x04(RTT); job+8 = out+0x0C(TTL)
                         |  结果字段 job+4/+8             |      最终消费者在 .tvm0 -> BLOCKED
                         +-------------------------------+
```

## 2. 已证实边(可复核)

| 边 | 从 | 到 | 证据 | 等级 |
|---|---|---|---|---|
| E1 | socket 创建 | D[+0] | `0x235D6D WSASocketW` -> `0x235D73` | [D] |
| E2 | event 创建 | D[+4] | `0x235D4F` -> `0x235D55` | [D] |
| E3 | event 绑定 | D[+4] FD_READ | `0x235D81` | [D] |
| E4 | ICMP Echo Request 构造 | 发送 buf | `0x235E8D..0x235EAC` | [D] |
| E5 | Request 发送 | 网络 | `0x235EC9 sendto`,len 0x30 | [D] |
| E6 | **接收** | 栈缓冲 `[ebp-0x10C]` | `0x235F7E recvfrom`,len 0x100 | [F] |
| E7 | recv 长度 | EDI -> out+0x08 | `0x235F84` / `0x23606E` | [F] |
| E8 | buf[0]&0xF | icmp_off | `0x235F94..0x235FAA` | [F] |
| E9 | ICMP id/type/seq | 校验分支 | `0x235FAD/0x235FC0/0x235FCB` | [F] |
| E10 | ICMP 时间戳 | out+0x04(RTT) | `0x236058` | [F] |
| E11 | IP TTL | out+0x0C | `0x236061` | [F] |
| E12a | out+0x04(RTT) | job+4 | `0x231171`/`0x231179` | [F] |
| E12b | out+0x0C(TTL) | job+8 | `0x231175`/`0x23117C` | [F] |
| E13 | CreateThread | 线程过程 | `0x22D53C` -> `0x10231050` | [D] |

## 3. 未闭合边(明确标注)

| 边 | 状态 | 说明 |
|---|---|---|
| U1 | [?] | 谁调用 ping 线程启动器 `0x22D470` —— 唯一引用在 `.tvm0 0x3512437`(受保护) |
| U2 | [?] | ping 结果结构在游戏逻辑中的最终消费点(是否存在 UI/HUD 显示)未定位 |
| U3 | [?] | job 对象 `+0x14`(map 键/target id)的上游填充点在 `.tvm0` 内 |
| U4 | [B] | `.tvm0` / `.tls` 内调用关系不可线性反汇编,相关边均标记 BLOCKED |

## 4. 明确不存在的边(否定证据)

| 边 | 判定 | 依据 |
|---|---|---|
| 接收缓冲 -> 游戏协议解析器 | **不存在** | 缓冲区未离开 `0x235E00`;无 memcpy/rep movs;函数直接返回 |
| 接收缓冲 -> opcode/handler 表 | **不存在** | 无跳转表索引;`buf[0]&0xF` 是 IP IHL,非 opcode |
| 接收缓冲 -> 解密/解压/分片重组 | **不存在** | 该路径无相关调用;无持久缓冲 |
| 接收 -> netchan 序列状态 | **不存在** | 无 netchan 结构/序号空间操作 |

