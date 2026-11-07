import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001"
F={}
F["E19_EXECUTIVE_SUMMARY.md"]="""# E19 — 执行摘要 / EXECUTIVE SUMMARY

> 任务编号：E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001
> 模式：只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> **冻结基线（开工与收工各复核一次，均一致）：**
> - 客户端 codoMP_client_shipRetail.exe = 353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1
> - 恢复镜像 codol2697-static-candidate.bin = 24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4
> - 服务端 codol_dedrun.exe = 80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1
> 地址口径：RVA；VA = RVA + 0x400000。

---

## 1. 核心发现：找到了真正的协议分帧器与接收状态机

**`0x6ABBC0` 是带 4 字节长度前缀的帧读取器（PROVEN）；其调用者 `0x6ABE80` 是 4 状态接收状态机（PROVEN）。**

这是本项目（E-12 起）**首次**定位到具备以下特征的客户端代码：

| 特征 | 证据 |
|---|---|
| 长度前缀分帧 | `0x6ABBC0` 累计 4 字节到 `[esi+0xA0]`，满 4 字节后解析 |
| 边界检查 + 拷贝 | `0x6878A0`（cmp/setbe + memcpy） |
| 长度校验与上限 | `cmp [esi+0xAC], [esi+0x98]` → 超限报错 |
| 接收状态机 | `0x6ABE80`：`jmp [ebx*4+0xAAC090]`，4 状态表 |
| 类型码分派 | `0x6A9920` 读 1 字节类型码，`cmp al,1` / `cmp al,2` |

## 2. 但归属仍未确认到游戏协议（关键限定）

| 命题 | 裁定 |
|---|---|
| 存在长度前缀分帧与接收状态机 | **PROVEN** |
| 该状态机属 Demonware 相关模块 | **STRONG_INFERENCE**（E-17：同簇含 DW-Client-Ticket / bdSessionParams） |
| 承载游戏会话消息 | **BLOCKED**（未见游戏 opcode 1..4 / 子帧 0..8） |
| 与已知游戏解析候选连接 | **REFUTED（限定范围）** |

**类型码是 `1` / `2`（Demonware 自己的消息分类），与 CODOL 游戏 opcode（`0x01`..`0x04`）不是同一编码空间。**

## 3. 状态机结构（PROVEN）

| 状态 | 目标 | 语义 |
|---|---|---|
| 0 | `0x6ABE99` | 初始化：清 `[esi+0xA4]`/`[esi+0xA8]`/`[esi+0xAC]`，释放旧 `[esi+0xB0]`/`[esi+0xB4]` |
| 1 | `0x6ABF1D` | 调 `0x6ABBC0`（读 4 字节头） |
| 2 | `0x6ABF47` | 调 `0x6A9920`（读类型码 + 载荷） |
| 3 | `0x6ABF52` | 调 `0x989230`/`0xAC4070` → `0xB83B70`（另一读路径） |

状态字段为 `[esi+0x9C]`；接收状态为 `[esi+0xC8]`。

## 4. `0x788133` 的归属（本轮闭合）

| 项 | 裁定 |
|---|---|
| 真实所属函数 | `0x78772D` 区段（**非**独立函数；真实 prologue 在 `0x787B2F` 附近） |
| 是否网络原语调用点 | 是（`call [0xBAE490]` = recv） |
| 与 `0x6ABBC0` 的关系 | **无调用边**；仅共享底层工具函数（`0x749B31` cookie 检查、`0x3622AC`） |
| 4 层闭包比较 | `0x6ABBC0`=48 函数，`0x78772D`=140 函数，共享 3 个通用工具 |

**裁定（REFUTED，限定范围）：`0x788133` 与 `0x6ABBC0` 状态机不属同一路径。**

## 5. 与已知游戏解析候选

`0x6ABBC0` 4 层闭包内**不含**：`0xA2660`、`0xA2E50`、`0x350170`、`0x3547D0`、`0x354100`。

## 6. 最小阻塞点

**Demonware 应用层消息语义。** 分帧与状态机已定位，但类型码 `1`/`2` 的语义、以及载荷进入应用层后的去向未闭合。

**已知的下一步范围：**
1. `0x6A9920` 的 `cmp al,1` / `cmp al,2` 分支目标（Demonware 消息分类）；
2. `[esi+0xB0]`/`[esi+0xB4]` 两个对象指针（`operator delete` 释放，说明是 C++ 对象）；
3. 状态 3 的 `0x989230` / `0xAC4070` 路径。

## 7. 问题库与解决率

新增 Q-29（`0x6ABBC0` 分帧器身份，权重 5，PROVEN=1.0）、Q-30（`0x6ABE80` 状态机身份，权重 5，PROVEN=1.0）、Q-31（`0x788133` 归属，权重 3，REFUTED/闭合=1.0）、Q-32（Demonware 类型码语义→游戏协议，权重 8，BLOCKED=0.0）。

- 旧总权重 142（E-18）→ **新总权重 163**
- 新增加权得分 = 5 + 5 + 3 + 0 = 13
- 新加权得分 = 53 + 13 = 66
- **风险加权解决率 = 66 / 163 = 40.49%**

（E-18 为 37.32%；本轮 +3.2 个百分点。）
"""
F["E19_6ABBC0_FUNCTION_AND_OBJECT_AUDIT.md"]="""# E19 — 0x6ABBC0 函数与对象审计 / FUNCTION AND OBJECT AUDIT

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 函数边界与调用约定（PROVEN）

| 项 | 值 |
|---|---|
| RVA | 0x6ABBC0 |
| 边界 | 0x6ABBC0 .. 0x6ABC7D（`ret` @0x6ABC4C / 0x6ABC6B / 0x6ABC7C；其后 int3） |
| 大小 | 0xBE 字节 |
| 调用约定 | `thiscall`（ECX=this）+ 无参数 |
| 直接调用者 | **唯一**：`0x6ABF1F`（在 `0x6ABE80` 内） |
| 数据指针引用 | 0 |
| 立即数引用 | 1（`0x6ABF1F`） |

## 2. 完整指令（PROVEN）

    6ABBC7  mov esi,ecx
    6ABBC9  mov eax,[esi+0xA4]        ; 已缓冲字节数
    6ABBD5  sub ecx,eax               ; 4 - 已读
    6ABBD7  push ecx                  ; 剩余长度
    6ABBD8  lea edx,[eax+esi+0xA0]    ; dst = headerBuf + used
    6ABBDF  push edx
    6ABBE0  lea ecx,[esi+0xC4]        ; 传输对象
    6ABBE6  call 0xB83B70             ; → Demonware recv 封装（E-17 的 0x784F60 族）
    6ABBED  test edi,edi / jle
    6ABBF5  add [esi+0xA4],edi        ; used += n
    6ABBFB  cmp dword [esi+0xA4],4
    6ABC02  jne 0xAABC78              ; 未满 4 字节 → 返回
    6ABC04  push 4 / lea eax,[ebp-8] / lea ecx,[ebp-4] / push 0
    6ABC10  lea edx,[esi+0xA0]        ; src = headerBuf
    6ABC20  call 0xA878A0             ; 边界检查 + memcpy（→ 0x6878A0）
    6ABC28  test al,al / je
    6ABC2C  mov eax,[ebp-8]           ; 解析出的长度
    6ABC2F  mov [esi+0xAC],eax        ; 存长度
    6ABC35  mov eax,[esi+0xAC]
    6ABC3B  test eax,eax / jne
    6ABC3F  mov [esi+0x9C],eax        ; 长度为 0 → 状态 0
    6ABC4D  cmp eax,[esi+0x98]        ; 与上限比较
    6ABC53  jbe 0xAABC6C
    6ABC55  call 0x43A7C0             ; 超限：错误上报
    6ABC5C  call 0x6AA770             ; 清理/置错误状态
    6ABC62  mov eax,0xFFFFFFF5        ; 返回 -11
    6ABC6C  mov [esi+0x9C],2          ; 状态 = 2（读体）
    6ABC76  mov eax,edi / ret

## 3. 对象字段映射（PROVEN）

| 偏移 | 语义 | 写入点 / 读取点 |
|---|---|---|
| +0x98 | **长度上限** | 读 @0x6ABC4D |
| +0x9C | **接收状态**（0/1/2/3/4） | 写 @0x6ABC3F/0x6ABC6C |
| +0xA0 | **4 字节头缓冲** | 写 @0x6ABBD8；读 @0x6ABC10 |
| +0xA4 | **已缓冲字节数** | 读写 @0x6ABBC9/0x6ABBF5/0x6ABBFB |
| +0xA8 | 类型码字节（E19 第二阶段） | 写 @0x6A994C |
| +0xAC | **解析出的帧长度** | 写 @0x6ABC2F |
| +0xB0 / +0xB4 | 两个 C++ 对象指针（经 `operator delete` 释放） | 0x6ABEB8..0x6ABF08 |
| +0xC4 | 传输对象（传给 0xB83B70） | @0x6ABBE0 |
| +0xC8 | 连接状态（1/2/4） | 0x6AA773/0x6AA791 |

## 4. 返回值

| 情况 | 返回 |
|---|---|
| 未读满 4 字节 | `n`（本次读到的字节数） |
| 长度为 0 | `n`，状态 0 |
| 长度超限 | **-11**（0xFFFFFFF5） |
| 正常解析 | `n`，状态 2 |

## 5. 类别判定（任务书第三节分类）

| 类别 | 判定 |
|---|---|
| socket 操作 | 否（经 0xB83B70 封装间接读取） |
| socket 对象接口方法 | 否 |
| 事件调度/回调 | 否 |
| 仅管连接状态 | 否 |
| **协议帧解析** | **是（PROVEN）** |
| **游戏应用层消息消费** | **BLOCKED**（类型码 1/2 语义未定） |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 函数边界与调用约定 | PROVEN |
| 4 字节长度前缀分帧 | **PROVEN** |
| 边界检查与长度上限 | PROVEN |
| 接收状态字段 +0x9C | PROVEN |
| 是否为协议帧读取器 | **PROVEN** |
| 是否游戏消息 | BLOCKED |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
