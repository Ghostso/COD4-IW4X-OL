# 01_EXECUTIVE_SUMMARY — CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041

**任务:** 从 040 确认的 `recvfrom RVA 0x235F7E` 及调用方 `RVA 0x2310E5` 出发,追踪接收数据完整消费者链,判断是否进入游戏协议解析路径。
**目标模块:** `codoMP_client_shipRetailBase.dll`
**指纹:** SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`(60327992 B,与 040 一致)
**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态二进制分析。**未启动游戏,无动态调试/注入/hook/内存转储**,未修改原始 EXE/DLL/恢复镜像/正式源码/FREEZE-005。

---

## 1. 核心结论

1. **接收点已完全定性:** `RVA 0x235F7E` 的 `recvfrom`(WS2_32 序 17)属于一个 **ICMP Echo(ping)探测** 子系统。该函数先用 `sendto` 发送 0x30 字节 **ICMP Echo Request(type=8)**(含 pid 作 id、递增 seq、时间戳、标准 16 位反码校验和),再 `WSAWaitForMultipleEvents`/`WSAEnumNetworkEvents` 等待 `FD_READ`,`recvfrom` 收 **ICMP Echo Reply(type=0)**。
2. **消费者链已闭合到"结果结构 + ping map":** 接收数据在**同一函数** `0x235E00` 内被解析(IP IHL、ICMP id/type/seq、RTT、IP TTL、载荷长度),写入一个 **16 字节 out 结构**;调用方线程过程 `0x231050` 读回 out 的 **+0x04(RTT) 与 +0x0C(TTL)** 两个字段并写入 job 对象。out 中**仅 +0x04(RTT) 与 +0x0C(TTL)** 被调用方线程过程读回:`0x231171 mov ecx,[esp+0x20]=out+0x04(RTT)`→`0x231179 mov [job+4],ecx`;`0x231175 mov edx,[esp+0x28]=out+0x0C(TTL)`→`0x23117C mov [job+8],edx`;out 的 +0x00(seq)/+0x08(payload_len) 在 `.text` 内**无可复核读者**;job 对象(含结果字段)由全局 map `0x22D470` 管理,其最终消费者在 `.tvm0`。**040 的「out 消费者未定位」阻塞项已解除**(消费者 = 线程过程 `0x231050`,读取点已定位)。
3. **接收数据不进入游戏协议解析路径:** 原始接收缓冲区 `[ebp-0x10C]` 不离开 `0x235E00`;**无 memcpy/rep movs 拷贝到堆或持久缓冲区**;**无 opcode/handler 表分派**;**无 netchan / 分片重组 / 解密 / 解压**。函数仅读取头部字段后 `xor eax,eax` 返回。
4. **040 的 SOCK_RAW/ICMP 悬念已判定:** 该通道为 **H2(ICMP/网络诊断)**,非 **H1(游戏业务数据)**。判定基于机器码语义(ICMP type/code/id/seq/checksum/TTL),**非**仅凭 `WSASocketW` 参数或相邻字符串。
5. **上游/下游业务语境受保护区阻断:** 谁发起 ping、job 键从何而来、结果最终用途,均在 `.tvm0`(受保护)内,**标记 BLOCKED**,未伪造闭环。

---

## 2. 三层验收口径

| 口径 | 本任务判定 | 依据 |
|---|---|---|
| 接收函数已确认 | **是** | `0x235F7E recvfrom`,参数与 IAT 槽 `0x10B02A48` 机器码级确认(`02_RECEIVE_CALLCHAIN.md` §4) |
| 消费者已定位 | **是** | out 字段消费者 = 线程过程 `0x231050` + ping map;字段级表见 `03` / `04` |
| 协议解析已确认 | **是,但为 ICMP 协议,不是游戏业务协议** | ICMP Echo Reply 解析链 `0x235F94..0x23607C` |

> **接收函数 ≠ 游戏协议解析器。** 本路径已确认是 ICMP;游戏业务协议消费者在 `.text` 可达范围内**未发现**(否定证据,非"不存在"的绝对断言)。

---

## 3. 与 040 的关系

- 040 结论"缓冲区 → 解析器 UNKNOWN"**被 041 修正并闭合**:缓冲区消费者就在同一函数内,且解析的是 ICMP 头部,**不存在通往游戏协议解析器的边**。
- 040 未决的 **H2(ICMP 可能性)** 在 041 升为**判定结论**;**H1(游戏业务接收)** 被 ICMP type/id/seq/checksum 语义**反证**。
- 040 的 `WSASocketW(AF_INET/SOCK_RAW/proto=1)` 观察被 041 的完整 ICMP Echo 往返语义证实,不再停留于"参数疑似"。

---

## 4. 限制

1. 上游调用者位于 `.tvm0 0x3512437`(受保护),不可静态展开 → `BLOCKED`。
2. `.tvm0`(熵 7.023)/`.tls`(熵 7.532)未做线性反汇编;其中 `@icmp`/`PING`/`latency` 字样仅作旁证,不作证据。
3. 本报告仅覆盖 `.text` 可达范围;不能据此断言客户端整体"没有"游戏业务接收通道(仅声明:凡 `recv`/`recvfrom` 站点中,仅 `0x235F7E` 属该独立 ping 簇,其余属 libcurl/OpenSSL)。
4. 未执行真实客户端 E2E;不宣布与 OLD/2697/OL-mod/CoD4x/IW4x 协议相同。

---

## 5. 交付物

| 文件 | 内容 |
|---|---|
| `01_EXECUTIVE_SUMMARY.md` | 本文件 |
| `02_RECEIVE_CALLCHAIN.md` | socket/event → 接收点指令级调用链 |
| `03_OUT_STRUCTURE_FIELDS.tsv` | out 结构字段/来源/读取位置 |
| `04_BUFFER_CONSUMERS.tsv` | 全部已确认缓冲区消费者 + 否定证据 |
| `05_DATAFLOW_GRAPH.md` | 已证实边 / 未闭合边 / 明确不存在的边 |
| `06_HYPOTHESIS_LEDGER.md` | H1–H4 证据对比与判定 |
| `07_UNKNOWN_BLOCKED.md` | 未解决项、阻断项、解除所需证据 |
| `SHA256SUMS.txt` | 交付物完整性校验 |
| `evidence/` | 反汇编转储、IAT 槽解析、全接收调用点、汇总 JSON |
| `scripts/` | 全部只读分析脚本(可复现) |

---

## 6. 下一步建议

1. **（唯一推荐主任务）** 在受控授权下解码 `.tvm0`,定位 `0x22D470` 的调用者与 job `+0x14`(ping map 键)的填充点,确认 ping 目标来源与结果用途。
2. 若无法解码 `.tvm0`,则退而求其次:在 **单独授权** 的运行时观测中确认该 socket(AF_INET/SOCK_RAW/ICMP)的实际流量与调用栈。
3. 暂**不**将任何 041 发现加入跨项目协议矩阵:本任务只补足"接收数据流证据",未提供游戏业务消息语义。

---

## 7. 证据等级定义

- `CONFIRMED_DIRECT`: 机器码/PE 结构直接支持。
- `CONFIRMED_DATAFLOW`: 可追踪参数/缓冲区数据流。
- `CONFIRMED_CROSSREF`: 可复核交叉引用,语义未完全闭合。
- `CONFIRMED_ABSENT`: 指定范围内经穷举确认不存在(否定证据)。
- `UNKNOWN` / `BLOCKED`: 证据不足 / 受保护区阻断。
