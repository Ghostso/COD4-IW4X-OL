# -*- coding: utf-8 -*-
"""041 part E: index + analysis summary json + validation."""
import sys, os, io, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
ROOT=C.ROOT

W = lambda n,t: io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("00_INDEX.md", u"""# CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041

**目标:** 从 `recvfrom RVA 0x235F7E`(040 确认)及调用方 `RVA 0x2310E5` 的 out 结构出发,追踪接收数据完整消费者链并判断是否进入游戏协议解析路径。
**模块:** `codoMP_client_shipRetailBase.dll`  SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
**日期:** 2026-10-13 (Asia/Shanghai)  **性质:** 只读静态分析(未启动游戏,无动态调试/注入/hook/转储)

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
| `SHA256SUMS.txt` | 完整性校验 |
| `evidence/` | 反汇编转储 + IAT 解析 + 调用点 |
| `scripts/` | 只读分析脚本 |

## 证据等级

`CONFIRMED_DIRECT` / `CONFIRMED_DATAFLOW` / `CONFIRMED_CROSSREF` / `CONFIRMED_ABSENT` / `UNKNOWN` / `BLOCKED`
""")

summary = dict(
  module="codoMP_client_shipRetailBase.dll",
  dll_sha256=hashlib.sha256(C._b).hexdigest(),
  image_base=hex(IB),
  recv_site=dict(rva="0x235F7E", va="0x10235F7E", file_off="0x23537E",
                 iat_slot_rva="0xB02A48", iat_slot_va="0x10B02A48",
                 api="recvfrom (WS2_32 ordinal 17)", insn_bytes="ff15482ab010"),
  socket=dict(site_rva="0x235D6D", af=2, type=3, protocol=1,
              meaning="AF_INET / SOCK_RAW / IPPROTO_ICMP", unique_wsasocketw_in_dll=True),
  callers=dict(
    threadproc_rva="0x231050", threadproc_via="CreateThread @0x22D53C (0x22D470 launcher)",
    recv_call_in_threadproc="0x2310E5", out_struct_stack_slot="[esp+0x14] (16B)"),
  classification=dict(primary="H2 ICMP/network diagnostic (ping)",
                      h1_game_protocol="not supported (counter-evidence)",
                      game_protocol_parser_reached=False),
  out_fields=[dict(off="+0x00",size=2,name="seq"),dict(off="+0x04",size=4,name="rtt"),
              dict(off="+0x08",size=4,name="payload_len"),dict(off="+0x0C",size=4,name="ttl")],
  negative_evidence=[
    "no memcpy/rep movs of [ebp-0x10C] to heap or persistent buffer",
    "no opcode/handler-table dispatch (buf[0]&0xF is IP IHL)",
    "no netchan / fragmentation / decrypt / decompress on this path",
    "function returns 0 at 0x23607C without payload copy"],
  blockers=[".tvm0 0x3512437 upstream caller (protected)",
            "job+0x14 ping map key fill site (protected)",
            "ping result ultimate consumer (protected)"],
)
io.open(os.path.join(C.EV,"analysis_summary.json"),"w",encoding="utf-8").write(
    json.dumps(summary,indent=2,ensure_ascii=False))
print("index + summary written")
