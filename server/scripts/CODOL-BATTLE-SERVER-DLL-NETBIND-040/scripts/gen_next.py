# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("NEXT_TASK_RECOMMENDATION.md", u"""# NEXT_TASK_RECOMMENDATION — 唯一下一任务

**建议编号:** `CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041`
**目标:** CODOL 3.19.26.22 / Build 1649370 — `codoMP_client_shipRetailBase.dll`
**性质:** 只读静态逆向 + 离线验证; 不启动游戏, 不做 E2E。

---

## 1. 唯一推荐 (只推荐一个)

> **从 040 已闭合的接收调用点 (`recvfrom` @ RVA 0x235F7E, 返回长度 → 调用方 out 结构) 出发, 向下追踪 out 结构消费者, 定位从接收缓冲区到消息解析入口的可复核数据流。**

040 已把链路推到"栈缓冲区 `[ebp-0x10C]` + 返回长度 → 调用方 `0x2310E5` 的 out 结构 (`[esp+0x14]`)"。041 的**唯一**目标是接续这一段。

---

## 2. 为什么是它

040 已确认:
- 接收 API 已解析: `recvfrom`(序 17) 3 个真实 FF15 调用点; `recv`(序 16) 12 个真实 FF15 调用点。
- 函数指针存储位置已定位: `.idata2` 隐藏 IAT 中 72 个 Winsock 固定槽 (`0xB02A40..0xB02B5C`)。
- socket/event → 栈缓冲区写入链已闭合 (`CONFIRMED_DATAFLOW`)。
- 但 **缓冲区 → 解析器** 段为 UNKNOWN: 接收后只做了 `buf[0]&0xF` 索引 + 源身份校验 + 写 out 结构, 未定位 netchan/opcode 分派。

不接续这段, 后续任何 opcode/协议分析都无基础。

---

## 3. 输入

- DLL SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
- 040 证据: `evidence/winsock_callsites.tsv`, `evidence/winsock_slots.tsv`, `SOCKET_EVENT_RECEIVE_CHAIN.md`, `BUFFER_WRITE_AND_LENGTH_FLOW.tsv`
- 已定位关键点: 接收函数 `0x235E00`, 调用方 `0x2310E5`, out 结构 `[esp+0x14]`/`[esp+0x28]`

---

## 4. 输出 (建议)

- `00_INDEX.md`
- `RECV_OUT_STRUCT_CONSUMERS.tsv`
- `BUFFER_TO_PARSER_DATAFLOW.md`
- `OPCODE_DISPATCH_CANDIDATES.tsv`
- `NETCHAN_STATE_VS_BUFFER.tsv`
- `STATIC_ANALYSIS_BLOCKERS.md`
- `SERVER_IMPLEMENTATION_GAP.tsv`
- `TEST_AND_VALIDATION_RESULTS.md`
- `FILE_HASH_MANIFEST.tsv` / `SHA256SUMS.txt`

---

## 5. 验收标准

1. 给出 `0x2310E5` 调用方栈上 out 结构 (`[esp+0x14]`, `[esp+0x28]`) 的字段布局与全部写入点。
2. 追踪 out 结构全部下游读取者, 形成可复核数据流 (RVA/VA/文件偏移/机器码)。
3. 若找到消息解析入口: 给出 opcode 读取点 (缓冲区偏移)、分派表地址、handler 数量。
4. 若未找到: 给出系统性反证范围 (已扫描区域、已排除模式), 明确标 `UNKNOWN`。
5. 明确区分 netchan 状态与消息缓冲状态。
6. 不将 `.tvm0`/`.tls` 字节按普通 x86 生成调用图。
7. 不将字符串存在误报为 API 调用存在。
8. 未修改 FREEZE-005 与正式服务器; 明确声明未做真实客户端 E2E。
9. 新增交付文件 SHA256 全部通过。

---

## 6. 阻塞条件 (若出现, 记录而非绕过)

- out 结构消费者位于 `.tvm0`/`.tls` 且无静态可达路径。
- 需要运行时内存观测 (需单独授权)。
- 只能得到 out 结构字段而无法得到其下游消费者。
""")
print("NEXT_TASK_RECOMMENDATION.md done")
