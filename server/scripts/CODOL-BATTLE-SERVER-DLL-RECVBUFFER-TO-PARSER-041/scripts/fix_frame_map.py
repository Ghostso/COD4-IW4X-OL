# -*- coding: utf-8 -*-
"""041 correction pass — fix the caller frame map for the two out readers.

Verified by independent path-sensitive ESP simulation (scripts/frame_model.py):
  out base  = [esp+0x14] @0x2310DA          (esp=E-84)
  0x231171  mov ecx,[esp+0x20]  (esp=E-96)  -> out+0x04 (RTT) -> job+4 @0x231179
  0x231175  mov edx,[esp+0x28]  (esp=E-96)  -> out+0x0C (TTL) -> job+8 @0x23117C
The earlier draft failed to account for `push 1`/`push 100` at 0x231161/0x231163
(esp -8) ahead of 0x231171, and thus swapped these two fields.
"""
import io, os, re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-RECVBUFFER-TO-PARSER-041"

def rw(rel, subs, must=True):
    p = os.path.join(ROOT, rel)
    s = io.open(p, encoding="utf-8").read()
    orig = s
    for a, b in subs:
        if a not in s:
            if must:
                raise SystemExit("MISSING in %s: %r" % (rel, a[:80]))
            continue
        s = s.replace(a, b)
    if s != orig:
        io.open(p, "w", encoding="utf-8", newline="").write(s)
        print("patched", rel)
    else:
        print("no-change", rel)

# ---- 01 executive summary ----
rw("01_EXECUTIVE_SUMMARY.md", [
 ("调用方线程过程 `0x231050` 读回 out+0x0C(TTL)并写入 job 对象。out 中**仅 +0x0C(TTL)** 被调用方线程过程读回(`0x231171`/`0x231179` 写入 job+4);out 的 +0x00/+0x04/+0x08 在 `.text` 内**无可复核读者**;",
  "调用方线程过程 `0x231050` 读回 out 的 **+0x04(RTT) 与 +0x0C(TTL)** 两个字段并写入 job 对象。out 中**仅 +0x04(RTT) 与 +0x0C(TTL)** 被调用方线程过程读回:`0x231171 mov ecx,[esp+0x20]=out+0x04(RTT)`→`0x231179 mov [job+4],ecx`;`0x231175 mov edx,[esp+0x28]=out+0x0C(TTL)`→`0x23117C mov [job+8],edx`;out 的 +0x00(seq)/+0x08(payload_len) 在 `.text` 内**无可复核读者**;"),
])

# ---- 02 receive callchain ----
rw("02_RECEIVE_CALLCHAIN.md", [
 ("- **out 回读(唯一):** `0x231171 mov ecx,[esp+0x20]` = **out+0x0C(TTL)** -> 写入 job+4;`0x231175 mov edx,[esp+0x28]` = **D+0x04(event)** -> 写入 job+8。out 的 +0x00/+0x04/+0x08 在 `.text` 内**无可复核读者**(写入后未被本模块读回)。",
  "- **out 回读(经路径敏感 ESP 建模确认,esp 槽在两条 `push` 后为 `E-96`):**\n"
  "  - `0x231171 mov ecx,[esp+0x20]`(esp=`E-96`;`E-96+0x20=E-64`=**out+0x04 = RTT**)→ `0x231179 mov [job+4],ecx`。\n"
  "  - `0x231175 mov edx,[esp+0x28]`(esp=`E-96`;`E-96+0x28=E-56`=**out+0x0C = TTL**)→ `0x23117C mov [job+8],edx`。\n"
  "  - 关键:进入 `0x231171` 前有 `0x231161 push 1` / `0x231163 push 0x64`(esp 再降 8),故其 `[esp+0x20]/[esp+0x28]` 相对 out 基址 `[esp+0x14]`(esp=`E-84`)分别落在 **out+0x04** 与 **out+0x0C**。\n"
  "  - out 的 **+0x00(seq) 与 +0x08(payload_len)** 在 `.text` 内**无可复核读者**(写入后未被本模块读回)。"),
 ("- 调用方线程过程读取的 `[esp+0x28]` 槽(紧邻 out 之后)的语义未完全闭合;不影响\"接收数据不进入游戏协议解析器\"的结论。",
  "- 调用方线程过程读取的另一个 `[esp+0x28]` 槽(= D 对象 +0x04 事件句柄,见堆栈模型)在关闭路径中使用,其语义已闭合为 WSAEVENT;不影响\"接收数据不进入游戏协议解析器\"的结论。"),
])

# ---- 03 out fields ----
rw("03_OUT_STRUCTURE_FIELDS.tsv", [
 ("OUT-004\t+0x04\t4\trtt\tround-trip time\t0x236068\tmov dword ptr [esi + 4], eax\t8946040f\teax = tick(0x236110) - [ecx+0xC]\tnow minus echoed timestamp buf[ihl*4+0xC] (written 0x235E9E)\tno direct reader found in thread proc 0x231050; downstream consumer UNKNOWN\t-\tCONFIRMED_DATAFLOW\techoed tick set at 0x235E9E",
  "OUT-004\t+0x04\t4\trtt\tround-trip time\t0x236068\tmov dword ptr [esi + 4], eax\t8946040f\teax = tick(0x236110) - [ecx+0xC]\tnow minus echoed timestamp buf[ihl*4+0xC] (written 0x235E9E)\tthread proc 0x231050 reads [esp+0x20] = out+0x04\t0x231171\tCONFIRMED_DATAFLOW\tread back into job+4 at 0x231179 (esp=E-96+0x20=E-64=out+0x04)"),
 ("OUT-008\t+0x08\t4\tpayload_len\trecvlen - ihl*4 - 0x10\t0x236076\tmov dword ptr [esi + 8], edi\t897e08\tedi = recvlen - ihl*4 - 0x10\trecvfrom return EDI + IP IHL\tno direct reader found in thread proc 0x231050; downstream consumer UNKNOWN\t-\tCONFIRMED_DATAFLOW\tfixed 0x10 overhead; NO payload bytes copied",
  "OUT-008\t+0x08\t4\tpayload_len\trecvlen - ihl*4 - 0x10\t0x236076\tmov dword ptr [esi + 8], edi\t897e08\tedi = recvlen - ihl*4 - 0x10\trecvfrom return EDI + IP IHL\tno reader found in .text reachable range; downstream consumer UNKNOWN\t-\tCONFIRMED_DATAFLOW\tfixed 0x10 overhead; NO payload bytes copied"),
 ("thread proc 0x231050 reads [esp+0x20] = out+0x0C\t0x231171\tCONFIRMED_DATAFLOW\tIP TTL of ICMP echo reply; value stored into job+4 at 0x231179",
  "thread proc 0x231050 reads [esp+0x28] = out+0x0C\t0x231175\tCONFIRMED_DATAFLOW\tread back into job+8 at 0x23117C (esp=E-96+0x28=E-56=out+0x0C)"),
])

# ---- 04 buffer consumers ----
rw("04_BUFFER_CONSUMERS.tsv", [
 ("C-006\trtt_extract\t0x236058\tsub eax, dword ptr [ecx + 0xc]\t2b410c8b\t[ecx+0xC] = ICMP[0xC]\teax = now_tick - [ecx+0xC]\tround-trip time\tout+0x04\tCONFIRMED_DATAFLOW\ttimestamp echoed from request at 0x235E9E",
  "C-006\trtt_extract\t0x236058\tsub eax, dword ptr [ecx + 0xc]\t2b410c8b\t[ecx+0xC] = ICMP[0xC]\teax = now_tick - [ecx+0xC]\tround-trip time\tout+0x04 (read back at 0x231171 -> job+4)\tCONFIRMED_DATAFLOW\ttimestamp echoed from request at 0x235E9E"),
 ("C-007\tttl_extract\t0x236061\tmovzx ecx, byte ptr [ebp - 0x104]\t0fb68dfcfeffff\t[ebp-0x104] = buf + 8\tecx = movzx byte buf[8]\tIP TTL of reply\tout+0x0C\tCONFIRMED_DATAFLOW\tIP header offset 8 = TTL",
  "C-007\tttl_extract\t0x236061\tmovzx ecx, byte ptr [ebp - 0x104]\t0fb68dfcfeffff\t[ebp-0x104] = buf + 8\tecx = movzx byte buf[8]\tIP TTL of reply\tout+0x0C (read back at 0x231175 -> job+8)\tCONFIRMED_DATAFLOW\tIP header offset 8 = TTL"),
])

# ---- 05 dataflow graph ----
rw("05_DATAFLOW_GRAPH.md", [
 ("  [F] 0x231171 out+0xC(TTL) -> job+4 (job+8 = D+4 event)         |",
  "  [F] 0x231171 out+0x4(RTT) -> job+4                              |\n  [F] 0x231175 out+0xC(TTL) -> job+8                              |"),
 ("|  job 对象(全局 map 0x22D470 管理)|  [X] job+4 = out+0x0C(TTL)",
  "|  job 对象(全局 map 0x22D470 管理)|  [X] job+4 = out+0x04(RTT); job+8 = out+0x0C(TTL)"),
 ("| E12 | out+0x0C(TTL) | job+4 | `0x231171`/`0x231179` | [F] |",
  "| E12a | out+0x04(RTT) | job+4 | `0x231171`/`0x231179` | [F] |\n| E12b | out+0x0C(TTL) | job+8 | `0x231175`/`0x23117C` | [F] |"),
])

# ---- 07 unknown/blocked ----
rw("07_UNKNOWN_BLOCKED.md", [
 ("| U-041-03 | 下游 | job 对象结果字段(job+4 = out+0x0C TTL;job+8 = D+0x04)在游戏逻辑中的最终用途(选服/HUD/日志) | `UNKNOWN` | job 对象由全局 map `0x22D470` 管理,其读者在受保护区;out 的 +0x00/+0x04/+0x08 在 `.text` 内无读者 | 定位 job map 消费者的调用点;或运行期观测 |",
  "| U-041-03 | 下游 | job 对象结果字段(job+4 = out+0x04 RTT;job+8 = out+0x0C TTL)在游戏逻辑中的最终用途(选服/HUD/日志) | `UNKNOWN` | job 对象由全局 map `0x22D470` 管理,其读者在受保护区;out 的 +0x00/+0x08 在 `.text` 内无读者 | 定位 job map 消费者的调用点;或运行期观测 |"),
 ("| U-041-04 | 下游 | 调用方线程帧 `[esp+0x28]` 槽(紧邻 out 之后)的语义 | `UNKNOWN` | 该槽由 `0x2310C6..0x2310D7` 的 map 记录对象派生,外部无进一步闭合 | 需要 map 记录结构完整类型恢复 |",
  "| U-041-04 | 下游 | 调用方线程帧中 out 之后紧邻槽(`E-52` = D 对象基址 / `E-48` = D+0x04 事件句柄)的语义 | `RESOLVED` | 经路径敏感 ESP 建模:D 对象 = `[esp+0x24]@0x231112`(关闭 socket)与 `[esp+0x28]@0x231129`(WSACloseEvent 参数) | 已闭合为 socket/event 句柄 |"),
])

print("done")
