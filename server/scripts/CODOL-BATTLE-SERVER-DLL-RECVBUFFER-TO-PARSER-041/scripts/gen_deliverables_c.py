# -*- coding: utf-8 -*-
"""041 deliverable generator, part C (05/06/07/01)."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT = C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("05_DATAFLOW_GRAPH.md", u"""# 05_DATAFLOW_GRAPH — 接收数据流图(已证实 / 未闭合)

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
  [F] map.insert(0x22D549->0x22D990)  job/job.id                |
                         +---------------+---------------+
                                         | lpParameter = job (0x18 B)
                                         v
                         +-------------------------------+
                         |  .text 0x231050 线程过程       |
  [D] 0x231080 call 0x235CD0  -> 构造 D(socket+event+buf)       |
  [D] 0x2310B1/0x2310C1 call 0x22A670 -> 用 job.id 查 ping map   |
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
  [F] 0x231171 out+0xC(TTL) -> job[+4]/job[+8] writeback         |
                         +---------------+---------------+
                                         |
                                         v
                         +-------------------------------+
                         |  ping map (0x22A670 访问器族)  |  [X] 结果被管理侧读取
                         |  键 = job.id; 值含 RTT/TTL/长度|      具体游戏内消费点未闭合
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
| E12 | out | 调用方线程帧 | `0x2310DA push &out` | [F] |
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
""")

W("06_HYPOTHESIS_LEDGER.md", u"""# 06_HYPOTHESIS_LEDGER — 传输用途归因(H1–H4)

任务要求:针对 040 提出的 SOCK_RAW/ICMP 可能性,对以下四个竞争假设给出支持/反证/缺失证据/下一步静态检查。**不得仅凭 `WSASocketW` 参数或相邻字符串定论。**

- **H1**:游戏业务数据接收路径。
- **H2**:ICMP 或网络诊断路径。
- **H3**:平台服务、探测或其他辅助通信路径。
- **H4**:受保护或静态恢复限制,无法可靠归类。

---

## 判定摘要

| 假设 | 判定 | 置信度 |
|---|---|---|
| H1 游戏业务数据接收 | **不支持(有反证)** | 高 |
| H2 ICMP/网络诊断 | **强支持** | 高 |
| H3 平台服务/探测/辅助 | **部分支持(与 H2 兼容的辅助层)** | 中 |
| H4 无法归类 | **不成立(本路径可归类)** | 高 |

**综合结论:** 该接收点属于 **ICMP Echo(ping)诊断/延迟探测子系统**(H2);它是辅助通信层,不是游戏业务数据通道(H1)。其发起者与结果用途仍在保护区(H4 仅适用于"谁发起/谁消费",不适用于"这条路径是什么")。

---

## H1 游戏业务数据接收路径

- **支持证据:** 位于 `codoMP_client_shipRetailBase.dll`(游戏客户端主模块);有 socket/event 接收循环。
- **反证(关键):**
  1. socket 协议为 `SOCK_RAW`+`IPPROTO_ICMP`(`0x235D6D`);业务通道不会是 ICMP。
  2. 发送缓冲被填为 `type=8`(Echo Request)且带标准 ICMP 校验和(`0x235E8D`,`0x2360B0`)。
  3. 接收侧强制 `type==0`(Echo Reply)、校验 ICMP id、回显 seq/时间戳(`0x235FC0/0x235FCB/0x236058`)。
  4. 接收缓冲区内**无 opcode/handler 分派**;`buf[0]&0xF` 是 IP IHL。
  5. 缓冲区不离开函数,无持久缓冲/分片重组/解密(`0x23607C` 直接返回)。
- **缺失证据:** 无。
- **下一步静态检查:** 已充分;若仍要证伪,可在 `.tvm0` 内定位 `0x22D470` 的调用者并确认其语义(见 H4)。

## H2 ICMP / 网络诊断路径

- **支持证据:**
  1. `WSASocketW(AF_INET, SOCK_RAW, 1=IPPROTO_ICMP)`(`0x235D6D`),全 DLL 唯一 socket-create 点。
  2. 发送 `type=8 / code=0`、含 id/seq/时间戳、16 位反码校验和(`0x2360B0`)—— 标准 ICMP Echo Request。
  3. 接收校验 `type=0`(Echo Reply)、id 匹配、seq 匹配。
  4. 从回显时间戳计算 RTT、读取 IP TTL、推导载荷长度 —— 典型 ping 指标。
  5. 结果结构仅含 `{seq, rtt, payload_len, ttl}`,与"延迟探测"一致。
- **反证:** 无直接反证。
- **缺失证据:** 无字符串直接标注 "ping"(见下"相邻字符串"说明),但不影响机器码层面的判定。
- **下一步静态检查:** 可交叉在 `.tvm0` 内查找消费 `job[+4]/job[+8]`(RTT/TTL)的位置以确认用于延迟显示/选服。

## H3 平台服务 / 探测 / 其他辅助通信

- **支持证据:** 该子系统是一个后台线程 + 全局 map(键=target id),形态上属"对若干目标的探测服务",可被延迟测量/选服逻辑复用;与 H2 不冲突。
- **反证:** 无独立反证;但它**不能**升级为游戏业务数据通道。
- **缺失证据:** 该 map 的键空间来源(job `+0x14`)与结果最终消费点在 `.tvm0` 内未闭合。
- **下一步静态检查:** 定位 `.tvm0` 中对 `0x22D470` 的调用者,检查其是否传入"服务器列表/候选目标"。

## H4 受保护/恢复限制导致无法归类

- **支持证据:** 发起者(`.tvm0 0x3512437`)、job 键填充、结果消费点均位于受保护区。
- **反证:** **本路径本身(0x235CD0/0x235E00/0x231050/0x22D470 等)完全在 `.text` 内且线性可反汇编**,机器码证据充分,足以把这条接收路径归类为 ICMP Echo 探测。
- **缺失证据:** 上游/下游的**业务语境**无法静态恢复。
- **下一步静态检查:** 需要 `.tvm0` 解码/去保护(需单独授权),或运行时观测该 socket 流量(需单独授权)。

---

## 相邻字符串(仅作旁证,不作为判定依据)

- `.rdata` 内 `WSAEnumNetworkEvents failed (%d)`、`WSAEnumNetworkEvents` 位于 libcurl 语境(`0x7AEB60/0x7AEBD4`),与该 ping 簇**无归属关系**,已排除。
- `.tls`(受保护/加密)内出现 `@icmp`、`PING`、`latency`、`LATENCY` 等字样,但 `.tls` 不可线性反汇编,仅作旁证。
- 依据任务约束,**判定依据是机器码语义(ICMP type/code/checksum/id/seq/TTL),不是字符串**。
""")
print("05, 06 written")
