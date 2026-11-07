# 08_CORRECTION_LOG — 041 独立复核与勘误

**模块:** `codoMP_client_shipRetailBase.dll` SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
**性质:** 只读静态分析复核(未启动游戏,无动态调试/注入/hook/转储)。日期 2026-10-13。

本文件记录对 041 初稿的**独立重推导**(bit-for-bit)及由此发现的勘误。所有结论均可用
`scripts/` 下脚本与二进制原字节复现。

---

## 1. 复核方法

1. 独立确认 DLL SHA256 与镜像基址(`scripts/_common.py` 读原始字节)。
2. 独立反汇编下列区段并逐字节比对:
   - `0x235CD0..0x235E00`(D 对象构造)、
   - `0x235E00..0x2360B0`(send/recv/解析/校验和)、
   - `0x231050..0x231181`(调用方线程过程)、
   - `0x22D470..0x22D5A0`(线程启动器)、`0x22A670`(map 访问器)。
3. 全文件扫描 `recvfrom`/`sendto` IAT 槽(`0xB02A48`/`0xB02A4C`/`0xB02B3C`)的所有 `FF15` 调用点。
4. 全文件扫描对 `0x22D470`、`0x231050`、`0x235E00`、`0x235CD0`、`0x22A670` 的 rel32 与 imm32 引用。
5. 对调用方 `0x231050` 做**路径敏感 ESP 栈帧建模**(`scripts/frame_model.py`),
   对每次 `push/pop/add esp/sub esp/lea esp` 以及**每个 call(直接/间接,含 `call edi`=SleepEx)**
   按被调方 `ret imm16` 精确折算栈清理。
6. 建模器覆盖 99 条可达指令,0 处 ESP 冲突;输出 `evidence/caller_frame_model.tsv`。

---

## 2. 已独立证实(与初稿一致)

| 结论 | 独立证据 | 等级 |
|---|---|---|
| 接收点 `0x235F7E` = `recvfrom`(WS2_32 序 17),字节 `ff15482ab010` | 原字节 + IAT 槽 `0xB02A48` 内容 `0x80000011` | CONFIRMED_DIRECT |
| 该槽全 DLL 仅 2 个调用点:`.text 0x235F7E`(ping 簇)与 `.text 0x42D97F`(libcurl) | 全文件 `FF15` 扫描 | CONFIRMED_DIRECT |
| `WSASocketW` 全 DLL 唯一创建点为 `0x235D6D`,参数 `af=2/type=3/proto=1` | 原字节 `6a006a006a006a016a036a02` | CONFIRMED_DIRECT |
| 发送缓冲被填为 ICMP Echo Request(`type=8/id/seq/ts` + 反码校验和) | `0x235E8D/0x235E97/0x235E9A/0x235E9E`,`0x2360B0` | CONFIRMED_DATAFLOW |
| `recvfrom` 目标栈缓冲 `[ebp-0x10C]` 全函数仅 3 处引用(`0x235F08/0x235F76/0x235F94`),无 memcpy/rep movs | 原字节扫描 | CONFIRMED_ABSENT(否定) |
| 接收数据仅在函数内按 IP IHL + ICMP type/id/seq/ts/TTL/长度解析,写 16B out 后 `xor eax,eax;ret` | `0x235F94..0x23607C` | CONFIRMED_DATAFLOW |
| 上游启动器 `0x22D470` 全文件仅 1 个 rel32 引用,位于 `.tvm0 0x3512437` | 全文件 rel32 扫描 | CONFIRMED_CROSSREF / BLOCKED |

---

## 3. 勘误(初稿错误 → 已修正)

**问题:** 初稿把调用方 `0x231050` 的两处 out 回读映射为
`0x231171 = out+0x0C(TTL)`、`0x231175 = D+0x04(event)`,并据此声称
"out 仅 +0x0C 被读回、+0x04 无读者"。

**正确结论(路径敏感 ESP 建模):**

| 指令 | esp(相对入口 E) | `[esp+K]` 绝对帧槽 | 相对 out 基址 | 数据流 |
|---|---|---|---|---|
| `0x231171 mov ecx,[esp+0x20]` | `E-96` | `E-64` | **out+0x04 (RTT)** | → `0x231179 mov [job+4],ecx` |
| `0x231175 mov edx,[esp+0x28]` | `E-96` | `E-56` | **out+0x0C (TTL)** | → `0x23117C mov [job+8],edx` |

其中 out 基址 = `[esp+0x14]@0x2310DA`(esp=`E-88`)→ 绝对槽 `E-68`。

**根因:** 进入 `0x231171` 前存在 `0x231161 push 1` 与 `0x231163 push 0x64`(esp 再降 8)。
初稿未把这些压栈计入,导致两条回读被整体错位 8 字节,+0x04(RTT) 被误标成 +0x0C(TTL),
而把 `D+0x04` 事件句柄(经 `0x231129` 用于 `WSACloseEvent`)误当作 out 读回。

**受影响并已修正的文件:** `01_EXECUTIVE_SUMMARY.md`、`02_RECEIVE_CALLCHAIN.md`、
`03_OUT_STRUCTURE_FIELDS.tsv`、`04_BUFFER_CONSUMERS.tsv`、`05_DATAFLOW_GRAPH.md`、`07_UNKNOWN_BLOCKED.md`。
`06_HYPOTHESIS_LEDGER.md` 不受影响(其归因依据为 ICMP 语义,与本映射无关)。

**影响评估:** 该勘误**不改变**任何归因结论。接收数据仍不进入游戏协议解析器;
仍然**没有任何 out 槽承载接收缓冲区的负载字节**。RTT 与 TTL 都只是从 ICMP/IP 头部派生的**标量指标**,
其去向仍是 `.text` 内的 job 对象(→ 最终消费者在 `.tvm0`)。H1–H4 判定不变。

---

## 4. 复现命令

```
python scripts/frame_model.py     # 重推导调用方 ESP 栈帧并写 evidence/caller_frame_model.tsv
python scripts/self_verify.py     # 全部 24 项自校验(含 frame_* 项)
```

`self_verify.py` 的 frame_* 项直接断言:
`0x231171 -> out+0x04`、`0x231175 -> out+0x0C`、`D@+0x10`、`D+0x04 event`。
