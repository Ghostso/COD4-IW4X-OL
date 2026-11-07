# -*- coding: utf-8 -*-
"""041 deliverable generator, part B (02/05/06/07 markdown)."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
ROOT = C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)
def ih(rva,n):
    d=raw(rva,n); return d.hex() if d else "?"
def di(rva):
    i=dis_at(rva); return ("%s %s"%(i.mnemonic,i.op_str)) if i else "?"

# ================================================= 02
W("02_RECEIVE_CALLCHAIN.md", u"""# 02_RECEIVE_CALLCHAIN — 从 socket/event 到接收点的指令级调用链

**模块:** `codoMP_client_shipRetailBase.dll`  SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
**地址约定:** `VA = 0x10000000 + RVA`;`.text` 内 `file_off = RVA - 0xC00`。
**证据等级:** 本节全部为 `CONFIRMED_DIRECT` / `CONFIRMED_DATAFLOW`(机器码直接支持)。

---

## 0. 结论(供 01/05/06 引用)

`RVA 0x235F7E` 的 `recvfrom` 是一个 **ICMP Echo(ping)探测** 的接收端:
先 `sendto` 一个 0x30 字节的 ICMP Echo Request(type=8),再在事件上等待,
用 `recvfrom` 收 ICMP Echo Reply(type=0),只解析 IP/ICMP 头部(id/type/seq/RTT/TTL/长度),
写入一个 16 字节结果结构。**原始缓冲区不离开接收函数,不进入任何游戏协议解析器。**

---

## 1. 调用链总览

```
[.tvm0 0x3512437]  call 0x1022D470        <- 受保护区(上游调用者), BLOCKED
        |
        v
[.text 0x22D470]   ping 线程启动器
        0x22D520  operator new(0x18)            (=?0x1027D8F5)
        0x22D532  push <job obj> ; 0x22D533 push 0x10231050 (lpStartAddress)
        0x22D53C  call [0x10B0232C] = CreateThread
        0x22D549  map.insert(job)               (0x1022D580 -> 0x1022D990)
        |
        v   (新线程入口)
[.text 0x231050]  线程过程  (lpParameter = 0x18 字节 job 对象, 来自 [ebp+8])
        0x23107C  lea esi,[esp+0x24] ; 0x231080 call 0x10235CD0   <- 构造 D 对象(socket+event)
        0x2310AD  mov eax,[job+0x14]  ; 0x2310B1 call 0x1022A670  <- 用 target id 查 ping map
        0x2310D7  mov edx,[rec+0x34]  ; 目标 IPv4
        0x2310DA  lea eax,[esp+0x14]  ; &out
        0x2310DF  lea ecx,[esp+0x28]  ; this = &D
        0x2310E5  call 0x10235E00     <- 发送+接收+解析
        |
        v
[.text 0x235E00]  D::sendrecv(out)   (this = ecx = D 对象)
        0x235E60  inc word [D+0x12]                 ; 序列号++
        ... 构造 ICMP Echo Request(见 §3)...
        0x235EC9  call [0x10B02A4C] = sendto        ; 发 0x30 字节
        0x235F23  call [0x10B02A70] = WSAWaitForMultipleEvents
        0x235F4C  call [0x10B02A64] = WSAEnumNetworkEvents  ; 检查 FD_READ
        0x235F7E  call [0x10B02A48] = recvfrom      ; <<<< 040 接收点
        ... 解析 ICMP Echo Reply -> 写 out ...
```

---

## 2. 对象 D 的构造(`RVA 0x235CD0`)

| 偏移 | 字段 | 写入点 | 机器码 | 语义 |
|---|---|---|---|---|
| +0x00 | SOCKET | `0x235D73` | `mov [esi],eax` | `WSASocketW(2,3,1,...)` 于 `0x235D6D` = AF_INET/SOCK_RAW/IPPROTO_ICMP |
| +0x04 | WSAEVENT | `0x235D55` | `mov [esi+4],eax` | `WSACreateEvent()` @`0x235D4F` |
| +0x08 | ICMP id | `0x235D6A` | `mov [esi+8],eax` | `GetCurrentProcessId()` @`0x235D58` |
| +0x0C | 发送缓冲 ptr | `0x235D96` | `mov [esi+0xc],eax` | `operator new(0x30)`+`memset`(`0x235D87..0x235D9E`) |
| +0x10 | 有效标志 | `0x235DA1` | `mov byte [esi+0x10],1` | |
| +0x12 | 序列计数器 | `0x235E60` | `inc word [esi+0x12]` | ICMP Echo 序列号 |
| +0x14 / +0x18 | tick 基准 | `0x235D01` / `0x235D44` | | `GetTickCount` / 0x236110 结果 |

**socket 创建唯一性:** 全 DLL 内 `WSASocketW` 的 `FF15` 调用点仅 `0x235D6D` 一处(见 `evidence/all_receive_callsites.tsv` 与 040 `WINSOCK_FUNCTION_POINTERS.tsv`)。参数 `type=3`=SOCK_RAW,`protocol=1`=IPPROTO_ICMP。

---

## 3. 构造并发送 ICMP Echo Request(`0x235E84..0x235ECF`)

接收函数先把 0x30 字节发送缓冲填成 ICMP Echo Request(this = D,`edi = [D+0x0C]`):

| 偏移 | 内容 | 写入点 | 机器码 | 来源 |
|---|---|---|---|---|
| +0x00 | `0x08` | `0x235E8D` | `mov byte [edi],8` | **ICMP type 8 = Echo Request** |
| +0x01 | `0x00` | `0x235E90` | `mov byte [edi+1],0` | ICMP code |
| +0x02 | 校验和 | `0x235EAC` | `mov word [edi+2],ax` | `0x2360B0`(见下) |
| +0x04 | id | `0x235E97` | `mov [edi+4],ecx` | `ecx=[D+8]=GetCurrentProcessId()` |
| +0x08 | seq | `0x235E9A` | `mov word [edi+8],bx` | `bx=inc([D+0x12])` |
| +0x0C | 时间戳 | `0x235E9E` | `mov [edi+0xC],edx` | `0x236110`(10ms 精度 tick) |

- 校验和 `0x2360B0`:6 次循环 × 每轮累加 `[eax+0],[+2],[+4],[+6]` 四个 16 位字 = 24 字 = 0x30 字节,
  折叠进位后 `not eax`(标准 ICMP 16 位反码和)。
- `0x235EBC..0x235EC9`: `push &from ; push 0 ; push 0x30 ; push buf ; push s`,调 `sendto`(WS2_32 序 20)。

---

## 4. 等待并接收(`0x235F17..0x235F86`)

| 步骤 | 地址 | 机器码/调用 | 语义 |
|---|---|---|---|
| 缓冲清零 | `0x235F08` | `mov word [ebp-0x10C],cx` + `memset(leа [ebp-0x10A],0,0xFE)` @`0x235F0F` | 接收缓冲 0x100 清 0 |
| 等待 | `0x235F23` | `call [0x10B02A70]` | `WSAWaitForMultipleEvents(1,&D[+4],FALSE,100,FALSE)` |
| 事件解码 | `0x235F4C` | `call [0x10B02A64]` | `WSAEnumNetworkEvents(s,&D[+4],&netevents[ebp-0x170])` |
| 读事件 | `0x235F52` | `test byte [ebp-0x170],1` | FD_READ 位 |
| **recvfrom** | **`0x235F7E`** | `call [0x10B02A48]` | `recvfrom(s,[ebp-0x10C],0x100,0,&from,&fromlen)` |
| 返回值 | `0x235F84` | `mov edi,eax` | 实际接收字节数 -> EDI |
| 错误判断 | `0x235F86` | `cmp edi,-1` | SOCKET_ERROR -> 放弃本轮 |

`recvfrom` 参数机器码见 `evidence/recv_cluster_disasm.txt`;IAT 槽 `0x10B02A48` = WS2_32 序号 17 = `recvfrom`。

---

## 5. 接收后处理:解析 ICMP Echo Reply(`0x235F94..0x23607C`)

| 语义 | 地址 | 机器码 | 读取 |
|---|---|---|---|
| 取 IP IHL | `0x235F94` | `mov cl,[ebp-0x10C] ; and cl,0x0F` | `buf[0]&0x0F` = IP 头长度/4 |
| icmp_off | `0x235F9D..0x235FAA` | `add dx,dx ; add dx,dx` | `icmp_off = (buf[0]&0xF)*4` |
| id 匹配 | `0x235FAD` | `mov ebx,[ebp+ecx-0x108]` | `buf[icmp_off+4]`(ICMP id)== `[D+8]` |
| type 检查 | `0x235FC0` | `cmp byte [ecx],0` | `ICMP[0]==0` = Echo Reply |
| seq 匹配 | `0x235FCB` | `cmp word [ecx+8],bx` | `ICMP[8]==` 期望 seq |
| RTT | `0x236058` | `sub eax,[ecx+0xC]` | `now - ICMP[0xC]`(回显时间戳) |
| payload len | `0x23606E` | `sub edi,eax ; sub edi,0x10` | `recvlen - icmp_off - 0x10` |
| TTL | `0x236061` | `movzx ecx,byte [ebp-0x104]` | `buf[8]` = IP 头 TTL |
| 写 out | `0x236068..0x236079` | `mov [esi+4],[esi+8],[esi],[esi+0xC]` | out 结构(见 03) |

**关键否定证据:** `0x235F94..0x23607C` 全程只读缓冲区内的**头部字段**;
`lea`/`mov` 使用 `[ebp-0x10C]` 仅出现在 `0x235F76`(传给 recvfrom)、`0x235F94`(读 buf[0])两处,
其余经 `ecx=[ebp+ecx-0x10C]` 索引头部;**无 memcpy/rep movs 到堆或持久缓冲区**;
函数结尾 `0x23607C xor eax,eax` 直接返回,缓冲区的负载字节从未被读出。

---

## 6. 调用方 `RVA 0x2310E5` 的 out 结构使用

- `out` 位于调用方栈帧 `[esp+0x14]`(16 字节),call 前由 `0x23109D..0x2310A9` 清零。
- 传参: `0x2310DA lea eax,[esp+0x14]`(out)、`0x2310DE push eax`、`0x2310DF lea ecx,[esp+0x28]`(this=D)。
- 返回后按返回值分派(`0x2310EA..0x2310F2`): `1`=结束;`5`=置错误 `0xFFFFFFFE`;其余走 `0x231161`。
- `0x231171 mov ecx,[esp+0x20]` = **out+0x0C**(TTL),`mov edx,[esp+0x28]` = 相邻栈槽,写入 job 对象 `+4/+8`。
- 结束后 `0x231112` 释放 D: `closesocket([esp+0x24]=D+0)` @`0x23111C`,`WSACloseEvent([esp+0x28]=D+4)` @`0x23112E`,free 发送缓冲。
- out 的字段级对应见 `03_OUT_STRUCTURE_FIELDS.tsv`;缓冲区消费点见 `04_BUFFER_CONSUMERS.tsv`。

---

## 7. 未闭合边

- 上游公开入口位于 `.tvm0` `0x3512437`(受保护代码),**无法静态确认谁在何处发起 ping** —— 见 `07_UNKNOWN_BLOCKED.md`。
- 调用方线程过程读取的 `[esp+0x28]` 槽(紧邻 out 之后)的语义未完全闭合;不影响"接收数据不进入游戏协议解析器"的结论。
""")
print("02 written")
