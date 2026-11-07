# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def patch(name, pairs):
    p=os.path.join(ROOT,name)
    t=io.open(p,encoding="utf-8").read()
    for a,b in pairs:
        if a not in t:
            print("WARN not found in %s: %s" % (name, a[:60]))
        t=t.replace(a,b)
    io.open(p,"w",encoding="utf-8",newline="").write(t)

# 01
patch("01_EXECUTIVE_SUMMARY.md", [
 ("结果由 ping map 访问器族(`0x22A670`/`0x22A770`/`0x22B010`)管理。**040 的 out 消费者阻塞项(BLK-040-01)已解除。**",
  "out 中**仅 +0x0C(TTL)** 被调用方线程过程读回(`0x231171`/`0x231179` 写入 job+4);out 的 +0x00/+0x04/+0x08 在 `.text` 内**无可复核读者**;job 对象(含结果字段)由全局 map `0x22D470` 管理,其最终消费者在 `.tvm0`。**040 的「out 消费者未定位」阻塞项已解除**(消费者 = 线程过程 `0x231050`,读取点已定位)。"),
 ("接收数据在**同一函数** `0x235E00` 内被解析(IP IHL、ICMP id/type/seq、RTT、IP TTL、载荷长度),写入一个 **16 字节 out 结构**;调用方线程过程 `0x231050` 读取 out 并把 TTL 写回 job 对象。",
  "接收数据在**同一函数** `0x235E00` 内被解析(IP IHL、ICMP id/type/seq、RTT、IP TTL、载荷长度),写入一个 **16 字节 out 结构**;调用方线程过程 `0x231050` 读回 out+0x0C(TTL)并写入 job 对象。"),
])
# 05
patch("05_DATAFLOW_GRAPH.md", [
 ("""                         +-------------------------------+
                         |  ping map (0x22A670 访问器族)  |  [X] 结果被管理侧读取
                         |  键 = job.id; 值含 RTT/TTL/长度|      具体游戏内消费点未闭合
                         +-------------------------------+""",
  """                         +-------------------------------+
                         |  job 对象(全局 map 0x22D470 管理)|  [X] job+4 = out+0x0C(TTL)
                         |  结果字段 job+4/+8             |      最终消费者在 .tvm0 -> BLOCKED
                         +-------------------------------+"""),
 ("| E12 | out | 调用方线程帧 | `0x2310DA push &out` | [F] |",
  "| E12 | out+0x0C(TTL) | job+4 | `0x231171`/`0x231179` | [F] |"),
 ("| [F] 0x2310B1/0x2310C1 call 0x22A670 -> 用 job.id 查 ping map   |",
  "| [F] 0x2310B1/0x2310C1 call 0x22A670 -> 用 job+0x14 查 target 映射|"),
 ("|  [F] 0x2310DA out = &[esp+0x14]  (16B, 先清零)                 |",
  "|  [F] 0x2310DA out = &[esp+0x14]  (16B, 先清零)                 |\n   |  [F] 0x231171 out+0xC(TTL) -> job+4 ; job 存全局 map           |"),
 ("  [F] 0x231112 释放 D(closesocket/WSACloseEvent/free)            |\n  [F] 0x231171 out+0xC(TTL) -> job[+4]/job[+8] writeback         |",
  "  [F] 0x231112 释放 D(closesocket/WSACloseEvent/free)            |\n  [F] 0x231171 out+0xC(TTL) -> job+4 (job+8 = D+4 event)         |"),
])
# 06
patch("06_HYPOTHESIS_LEDGER.md", [
 ("    5. 结果结构仅含 `{seq, rtt, payload_len, ttl}`,与\"延迟探测\"一致。",
  "    5. 结果结构仅含 `{seq, rtt, payload_len, ttl}`,与\"延迟探测\"一致(其中 ttl 被调用方读回)。"),
])
# 02
patch("02_RECEIVE_CALLCHAIN.md", [
 ("- **out 回读:** `0x231171 mov ecx,[esp+0x20]` = **out+0x0C(TTL)**;`0x231175 mov edx,[esp+0x28]` = **D+0x04(event)**;随后写入 job 对象 `+4`/`+8`。",
  "- **out 回读(唯一):** `0x231171 mov ecx,[esp+0x20]` = **out+0x0C(TTL)** -> 写入 job+4;`0x231175 mov edx,[esp+0x28]` = **D+0x04(event)** -> 写入 job+8。out 的 +0x00/+0x04/+0x08 在 `.text` 内**无可复核读者**(写入后未被本模块读回)。"),
])
patch("07_UNKNOWN_BLOCKED.md", [
 ("| U-041-03 | 下游 | ping 结果(RTT/TTL)在游戏逻辑中的最终用途(选服/HUD/日志) | `UNKNOWN` | 结果被 ping map 访问器(`0x22A670`/`0x22A770`/`0x22B010`)读取,但再上层消费者在受保护区 | 定位 ping map 访问器调用者;或运行期观测 |",
  "| U-041-03 | 下游 | job 对象结果字段(job+4 = out+0x0C TTL;job+8 = D+0x04)在游戏逻辑中的最终用途(选服/HUD/日志) | `UNKNOWN` | job 对象由全局 map `0x22D470` 管理,其读者在受保护区;out 的 +0x00/+0x04/+0x08 在 `.text` 内无读者 | 定位 job map 消费者的调用点;或运行期观测 |"),
])
print("patched")
