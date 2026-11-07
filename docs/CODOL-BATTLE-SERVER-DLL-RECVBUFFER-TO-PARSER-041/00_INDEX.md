# CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041

**目标:** 从 `recvfrom RVA 0x235F7E`(040 确认)及调用方 `RVA 0x2310E5` 的 out 结构出发,追踪接收数据完整消费者链并判断是否进入游戏协议解析路径。
**模块:** `codoMP_client_shipRetailBase.dll`  SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
**日期:** 2026-10-13 (Asia/Shanghai)  **性质:** 只读静态分析(未启动游戏,无动态调试/注入/hook/转储)
**复核:** 2026-10-13 独立重推导 + ESP 栈帧建模;发现并修正 1 处 out 回读映射错误(见 `08_CORRECTION_LOG.md`)

---

## 结论(一句话)

`0x235F7E recvfrom` 属于 **ICMP Echo(ping)探测** 子系统:接收数据在同一函数内被解析为 ICMP Echo Reply(id/type/seq/RTT/TTL/长度)并写入 16 字节结果结构,**不进入游戏协议解析器**;上游发起者在 `.tvm0` 受保护区,标记 `BLOCKED`。

## 三层判定

- 接收函数已确认: **是**(`0x235F7E recvfrom`)
- 消费者已定位: **是**(out -> 线程过程 `0x231050` -> ping map)
- 协议解析已确认: **是,但为 ICMP,不是游戏业务协议**

## 交付物

| 文件 | 内容 |
|---|---|
| `01_EXECUTIVE_SUMMARY.md` | 结论/限制/下一步 |
| `02_RECEIVE_CALLCHAIN.md` | socket/event -> 接收点指令级调用链 |
| `03_OUT_STRUCTURE_FIELDS.tsv` | out 字段与来源/读取 |
| `04_BUFFER_CONSUMERS.tsv` | 缓冲区消费者 + 否定证据 |
| `05_DATAFLOW_GRAPH.md` | 数据流图(已证实/未闭合/不存在) |
| `06_HYPOTHESIS_LEDGER.md` | H1–H4 归因 |
| `07_UNKNOWN_BLOCKED.md` | 未解决/阻断项 |
| `08_CORRECTION_LOG.md` | 独立复核方法与勘误记录 |
| `TEST_AND_VALIDATION_RESULTS.md` | 24 项自校验结果 |
| `SHA256SUMS.txt` | 完整性校验 |
| `evidence/` | 反汇编转储 + IAT 解析 + 调用点 + 调用方栈帧模型 |
| `scripts/` | 只读分析脚本 |

## 证据等级

`CONFIRMED_DIRECT` / `CONFIRMED_DATAFLOW` / `CONFIRMED_CROSSREF` / `CONFIRMED_ABSENT` / `UNKNOWN` / `BLOCKED`
