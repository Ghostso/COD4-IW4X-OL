# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001"
F={}
F["11_EVIDENCE_REGISTER_ADDENDUM.md"]=r"""# 11 — 证据登记（E-14 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 及 E-10..E-13 的同名追加。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-14-01 | REFUTE | `0x60E5B0` | **非协议状态机**，是 vsnprintf 风格格式化器：`0x60E625 cmp al,0x25`（`'%'`）+ `0x60E73E jmp [eax*4+0xA0EF84]`（7 项转换符表） | `_data/out_60e5b0_head.txt`、`_data/out_fmt_vtable.txt` | PROVEN |
| EV-14-02 | CALLBACK | `0x60E470` | putc 回调：`mov [edx],cl` + `inc [eax]` + `cmp ecx,[eax+8]`（容量检查） | `_data/out_60e5b0_head.txt` | PROVEN |
| EV-14-03 | CALLPATH | `0x6029A0`→`0x602760`→`0x60E5B0` | recv **错误日志**路径：`push 0xC37244`（`"Recv failure: %s"`）→ `0x60E5B0` 格式化；`mov [ecx+0x85F4],edx` 记错误码 | `_data/out_paths.txt` | PROVEN |
| EV-14-04 | CRYPTO | 客户端镜像 | 内联 **OpenSSL 0.9.8p 16 Nov 2010**：字符串 `0xC3D0D2` 等 5 处 + `"SSL routines"` `0xC9F428` | `_data/out_t08_sslver` | PROVEN |
| EV-14-05 | SSLOBJ | `0x672460` | OpenSSL 对象方法分派：`cmp [eax+0x20],0` → 错误报告（`push 0xC5650C`）→ `mov ecx,[eax+8]` → `mov eax,[ecx+0x1c]` → `jmp eax` | `_data/out_paths.txt` | PROVEN |
| EV-14-06 | TLSPATH | `0x605220`→`0x5FB510`→`0x6104D0`→`0x672460` | TLS 读路径：`cmp [edi+0x5b8],0`（SSL 对象）+ `call 0x9FB510`（SSL_pending 类）+ `recv` 2 字节 peek | `_data/out_paths.txt` | PROVEN |
| EV-14-07 | VTABLE | `.rdata` `0x898580`–`0x898600` | `0x898588` 含 `0xb75a50`（recv）；`0x898590` 含 `0xb75ab0`（recvfrom） | `_data/out_paths.txt` | PROVEN |
| EV-14-08 | MERGE | `0x605220` vs `0x6029A0` | 6 层下游闭包大小 7 vs 39；**共享下游 = 0** | `_data/out_t09_merge` | REFUTED（汇合） |
| EV-14-09 | BITWIDTH | 服务端 `0xA085F` | A2 段计数 `mov dword [esp+8],0xB`（**11 bit**）→ 与客户端 `0xA2765 push 0xB` 一致 | `_data/out_t14_bits` | PROVEN（修订 E-08） |
| EV-14-10 | CONST | 客户端 `.text` | CODOL 分片常量 `0x489`/`0x70CC729` 命中 **0** | `_data/out_t08_sslver` | PROVEN（负） |
| EV-14-11 | REPO | 本地 git 副本 | IW4X `d1b175da1a25d31043246de103a702b206269e5a`；CoD4x `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | `git rev-parse HEAD` | PROVEN |
| EV-14-12 | REMOTE | GitHub API | `iw4x/iw4x-client` 默认分支 `main`（pushed 2026-10-07）；`callofduty4x/CoD4x_Server` 默认分支 `master`（pushed 2026-09-18） | `api.github.com` HTTP 200 | PROVEN |
| EV-14-13 | BFS | `0x350170` 上游 | 反向 4 层收敛为 9 函数；`0x34E7C0` = `cl_demo_jumptostart` 回调（E-12 已证） | `_data/out_bfs_up.txt`（E-12） | PROVEN |
| EV-14-14 | REFUTE | E-13 §候选 | E-13 登记的 4 条候选（`0x6029A0`/`0x605220`/`0x60E5B0`/`0x1B0430`+`0x78772D`）中 **3 条被排除** | 本表 EV-14-01..06 | REFUTED |
"""

F["12_HYPOTHESIS_LEDGER_ADDENDUM.md"]=r"""# 12 — 假设台账（E-14 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\17_HYPOTHESIS_LEDGER.md` 及 E-10..E-13 的同名追加。

---

### H-E14-01：`0x60E5B0` 是实时协议状态机
- 类别：**实时链（被否定）**
- 支持：（E-13 曾据"20+ 函数指针调用"推断）
- 反证：`0x60E625 cmp al,0x25`（`'%'`）+ `0x60E73E jmp [eax*4+0xA0EF84]`（7 项转换符表）+ `0x60E470` putc 回调（EV-14-01/02）
- 状态：**REFUTED**
- 可证伪：找到同一函数内的消息类型比较（不存在）
- 下一步：无

### H-E14-02：`0x60E5B0` 是 vsnprintf 风格格式化器
- 类别：运行时库
- 支持：格式引入符、转换符跳转表、putc 回调、容量检查（EV-14-01/02）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E14-03：`0x6029A0` → `0x60E5B0` 是 recv 错误日志路径
- 类别：**实时链（被否定）**
- 支持：`push 0xC37244`（`"Recv failure: %s"`）；仅 `recv == -1` 时进入（EV-14-03）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E14-04：CODOL 客户端网络栈与 IW4X/CoD4x 架构相同
- 类别：**跨项目对应（被否定）**
- 支持：（无）
- 反证：客户端为虚表分派（`.rdata 0x898588`）+ 内联 OpenSSL 0.9.8p（EV-14-04/05/06/07）；IW4X/CoD4x 无 TLS
- 状态：**REFUTED**
- 下一步：无

### H-E14-05：`0x605220` 是独立实时协议路径
- 类别：**实时链（被否定）**
- 支持：（E-13 曾列为候选）
- 反证：`[edi+0x5b8]` SSL 对象 + `0x5FB510` → `0x6104D0` → `0x672460`（OpenSSL 对象方法分派）（EV-14-05/06）
- 状态：**REFUTED**（是 TLS 层）
- 下一步：定位 TLS 解密后的明文去向

### H-E14-06：`0x605220` 路径与 `0x6029A0` 路径汇合
- 类别：**路径汇合（被否定）**
- 支持：（无）
- 反证：6 层闭包 7 vs 39，共享下游 0（EV-14-08）
- 状态：**REFUTED**
- 下一步：无

### H-E14-07：网络虚表 `0x898588`/`0x898590` 是 socket 抽象族
- 类别：架构
- 支持：相邻槽位 `0xb75a50`(recv)/`0xb75ab0`(recvfrom)；同类语义（EV-14-07）
- 反证：构造函数未定位
- 状态：**STRONG_INFERENCE**
- 可证伪：找到该虚表被用于非 socket 用途
- 下一步：定位虚表构造者（BLK-14-2）

### H-E14-08：A2 段计数位宽两侧一致（11 bit）
- 类别：字段格式
- 支持：服务端 `0xA085F mov [esp+8],0xB`；客户端 `0xA2765 push 0xB`（EV-14-09）
- 反证：E-08 曾记 10 bit（本轮判定为记录错误）
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E14-09：CODOL 分片传输是客户端机制
- 类别：**跨项目对应（被否定）**
- 支持：（无）
- 反证：`0x489`/`0x70CC729` 在客户端 `.text` 命中 0（EV-14-10）
- 状态：**REFUTED**
- 下一步：无

### H-E14-10：服务端引擎层可复用 CoD4x 实现
- 类别：可复用性
- 支持：`huffman.c` Jaccard 99.7%、`cvar.c` 97.9%、`cmd.c` 97.6%、`sv_init_mp.cpp` 100%（E-13 血统报告 + 本轮复核）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无
"""

F["13_CLAIM_EVIDENCE_DEPENDENCY_GRAPH_ADDENDUM.md"]=r"""# 13 — 结论—证据依赖图（E-14 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\21_CLAIM_EVIDENCE_GRAPH.md` 及 E-10..E-13 的同名追加。

---

```
◆ C-14-01  0x60E5B0 是 vsnprintf 格式化器（非协议状态机）
   ├─✔ EV-14-01（'%' 比较 + 7 项转换符跳转表）
   └─✔ EV-14-02（putc 回调 + 容量检查）

◆ C-14-02  0x6029A0 → 0x60E5B0 是 recv 错误日志路径
   └─✔ EV-14-03（"Recv failure: %s"）

◆ C-14-03  CODOL 客户端网络栈含 TLS（OpenSSL 0.9.8p）
   ├─✔ EV-14-04（版本字符串 5 处）
   ├─✔ EV-14-05（OpenSSL 对象方法分派）
   └─✔ EV-14-06（TLS 读路径）

◆ C-14-04  两条候选路径无汇合
   ├─✔ EV-14-08（闭包 7 vs 39，共享 0）
   └─✔ EV-14-05/06（一条是 TLS）

◆ C-14-05  网络虚表是 socket 抽象族
   ├─✔ EV-14-07（相邻槽位 recv/recvfrom）
   └─⚠ 构造者未定位（BLK-14-2）—— **STRONG_INFERENCE**

◆ C-14-06  A2 段计数两侧均为 11 bit
   └─✔ EV-14-09（服务端 0xA085F + 客户端 0xA2765）

◆ C-14-07  CODOL 分片传输属服务端侧
   └─✔ EV-14-10（客户端 0 命中）

◆ C-14-08  源码血统
   ├─✔ EV-14-11（本地提交 SHA）
   ├─✔ EV-14-12（线上仓库身份）
   └─✔ E-13 血统报告（字面证据 + Jaccard）

◆ C-14-09  客户端网络栈不能映射到 IW4X/CoD4x
   ├─✔ EV-14-04/05/06（TLS）
   └─✔ EV-14-07（虚表分派）

◆ C-14-10  实时 Gamestate 0x03 消费者
   ├─✔ E-13 EV-13-13（收包与环形缓冲不相交）
   └─⚠ 应用层分派器未定位 —— **BLOCKED**
```

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-14-05 虚表归属 | 构造者未定位 | INFERRED |
| C-14-10 实时消费者 | 应用层分派器未定位 | BLOCKED |
| 风险加权解决率 | 权重未定义 | 无法计算 |
"""

F["14_START_GATING_AUDIT_ADDENDUM.md"]=r"""# 14 — 开工准入审计（E-14 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\22_SERVER_START_GATING_AUDIT.md` 及 E-09..E-13 的对应审计。

---

## 1. 判据状态变化（相对 E-13）

| # | 判据 | E-13 | E-14 | 依据 |
|---|---|---|---|---|
| G-19 | 实时网络底锚 | ✅ | ✅ | 维持 |
| G-20 | 环形缓冲读写原语 | ✅ | ✅ | 维持（发送暂存） |
| G-21 | 收包 → 环形缓冲 | ❌ | ❌ | 维持（REFUTED，限定范围） |
| G-22..G-24 | 收包 I/O、方向、读取器指针 | ✅ | ✅ | 维持 |
| G-25 | 实时消息入口 | ❌ | ❌ | 仍未定位 |
| **G-26（新）** | 候选路径归属（3 条被排除） | — | ✅ | EV-14-01..08 |
| **G-27（新）** | A2 计数位宽一致 | — | ✅ | EV-14-09 |
| **G-28（新）** | 源码血统（仓库 + SHA） | — | ✅ | EV-14-11/12 |
| **G-29（新）** | 客户端网络栈可映射 IW4X/CoD4x | — | ✅（否定） | EV-14-04..07 |

**E-13：通过 16 / 部分 4 / 未通过 3 → E-14：通过 20 / 部分 4 / 未通过 3。**

## 2. 阻断项状态

| ID | E-13 | E-14 | 说明 |
|---|---|---|---|
| BLK-13-1 `0x60E5B0` 函数指针 | 阻断 | **RESOLVED（REFUTED）** | 实为 putc 回调 |
| BLK-13-2 `0x78772D` `.tvm0` | 阻断 | 阻断 | 未触及 |
| BLK-13-3 虚表构造者 | 阻断 | 阻断 | 未定位 |
| BLK-12-2 实时 `0x03` 消费者 | 阻断 | 阻断 | 候选收窄为 2 条 |
| **BLK-14-1（新）** | — | **阻断** | TLS 解密后明文去向未定位 |
| **BLK-14-2（新）** | — | **阻断** | 虚表实例化路径 |
| **BLK-14-3（新）** | — | **阻断** | 应用层消息分派器 |

## 3. 准入裁定

### 3.1 可继续（纯静态，无需授权）

| 工作 | 目标 |
|---|---|
| A-14-1 | 定位 `0x605220` 调用者（`0x602BC0`/`0x612E80`）的明文入口（BLK-14-1） |
| A-14-2 | 解析 `0x1B0430` 的 30+ IAT 间接调用（剩余候选） |
| A-14-3 | 定位 `.rdata 0x898588` 虚表构造者（BLK-14-2） |
| A-14-4 | 建立问题项全集与风险权重（供 Q12 计算） |

### 3.2 仍不可宣称

- 不得宣称实时 Gamestate 消费路径已定位。
- 不得宣称 `0x60E5B0`/`0x6029A0`/`0x605220` 属协议处理（均已 REFUTED）。
- 不得宣称客户端网络栈可移植自 IW4X/CoD4x（架构 + TLS 差异）。
- 不得宣称 `0xA2660` 是实时 Configstring body reader。
- 不得在 BLK-14-1/2/3 解除前宣称互操作性。

### 3.3 裁定

**`CONDITIONAL GO（维持放宽；候选路径收窄）`**

- 服务端实现放宽**不变**：Huffman/cvar/cmd 可直接复用 CoD4x；netchan/Gamestate/Snapshot 改造后复用；可靠命令需重新实现。
- **新增否定性结论**：3 条 E-13 候选路径被排除；CODOL 客户端网络栈含 TLS，与 IW4X/CoD4x 不同。
- **新增修订**：A2 计数两侧均为 11 bit（E-08 记录为错）。
- 服务器 Gamestate 编码器可实现，但客户端验证仍 **BLOCKED**。
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
