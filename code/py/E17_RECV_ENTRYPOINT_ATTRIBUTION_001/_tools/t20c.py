# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001"
F={}
F["E17_GAME_SESSION_ATTRIBUTION.md"]="""# E17 — 游戏会话归属判定 / GAME SESSION ATTRIBUTION

> 任务书第六节给出 6 条 PROVEN 判据。本节逐条核对两个候选。

---

## 1. 判据核对表

| # | 判据 | 0x6B4DE0 | 0x784F60 |
|---|---|---|---|
| 1 | 存在可验证的接收原语 | ✔ recvfrom @0x6B4E3C | ✔ recv @0x784F7D |
| 2 | 能追踪接收数据或明确派生副本 | ✔ 交付 0x783F00 的 0x84 字节栈副本 | ✔ 透传给调用者 |
| 3 | 能证明数据交给**游戏会话**处理逻辑 | ✘ 交 Demonware 传输对象 | ✘ 同 |
| 4 | 至少一个具指令级证据的应用层消费者 | ✘ 未见 | ✘ 未见 |
| 5 | 消费者职责有充分证据 | ✘ 未定位 | ✘ 未定位 |
| 6 | 关键跨函数链无未解释断点 | ✘ 断在传输层 | ✘ 同 |

**结论：6 条判据中仅 2 条满足，第 3–6 条均不满足 → 不能判定为 PROVEN 游戏会话入站路径。**

## 2. 模块归属证据（INFERRED 强）

两候选的调用者簇与 Demonware 字符串同处一个模块：

| 证据 | VA / RVA | 内容 |
|---|---|---|
| Demonware 域名 | 0xC5B324 / 0xC5B33C / 0xC5B354 | `demonware.net` |
| 端口映射 | 0xC5B7B3 | `DemonwarePortMapping</NewPortMappingDescription>` |
| 会话票据 | 0xC5ADD0 | `DW-Client-Ticket-Size: %u` |
| 会话票据 | 0xC5ADEC | `DW-Client-Ticket: %s` |
| 会话票据 | 0xC5AE04 | `DW-Server-Ticket-Size: %u` |
| C++ 类型名 | 0xD36C70 | `bdSessionParams@@` |
| RSA/ECC 库 | 0xC9F734/0xC9F768/0xC9F8FC | `rsa_import` / `DW-RSAENC` / `ECC-521` |

调用者簇（0x6A9xxx / 0x6ABxxx / 0x6B3xxx / 0x783xxx）与上述字符串同属 Demonware 网络栈。

**DW-Client-Ticket / bdSessionParams 是 COD 系列 Demonware 后端的会话认证接口**（这是业界已知的命名，但本报告不以其为唯一依据——见 §3）。

## 3. 7 层闭包不含游戏解析器（PROVEN 负，决定性）

| 根 | 闭包(7) 大小 | 含 0xA2660 | 含 0x3547D0 | 含 0x350170 | 含 0x34FD80 | 含 0xA2E50 | 含 0x3524F0 | 含 0x352570 |
|---|---|---|---|---|---|---|---|---|
| 0x6B3310 | 14 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |
| 0x6ABBC0 | 48 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |
| 0x6A9920 | 20 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |
| 0x783F00 | 10 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |
| 0x783B70 | 6 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |

**这是本轮最重要的否定性证据：Demonware 传输簇与所有已知游戏解析候选在 7 层内不相交。**

## 4. 与任务书指定的已知地址的关系

| 地址 | 历史归属 | 本轮关系 |
|---|---|---|
| 0xA2660 | Configstring body reader（demo 链） | **无连接** |
| 0xA2E50 | reliable payload 候选 | **无连接** |
| 0x350170 | demo 顶层分派器 | **无连接** |
| 0x3547D0 | 子帧循环（demo） | **无连接** |
| 0x354100 | 子帧分派器（demo） | **无连接** |
| 0x3524F0 | 环形缓冲写侧（发送暂存） | **无连接** |
| 0x352570 | 环形缓冲读侧 | **无连接** |

**纪律遵守：** 未因"都操作缓冲区"或"都是网络函数"把它们连接起来。

## 5. 归属裁定

| 候选 | 归属类别（任务书第六节） | 等级 |
|---|---|---|
| 0x6B4DE0 | **5. 通用 socket 包装层**（Demonware 传输层内） | PROVEN（职责） |
| 0x784F60 | **5. 通用 socket 包装层**（Demonware 传输层内） | PROVEN（职责） |

**限定范围声明：** 本裁定限于 0x6B4DE0 与 0x784F60 及其 7 层闭包，**不推广**为"全镜像不存在游戏收包路径"。
"""
F["E17_CALLGRAPH_AND_DATAFLOW.md"]="""# E17 — 调用图与数据流图 / CALLGRAPH AND DATAFLOW

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 调用图（实线 = 直接 call；虚线 = 未证）

```
               [Demonware 会话／传输层]
                        │
      ┌─────────────────┼──────────────────┐
      │                 │                  │
  0x6ABBC0          0x6A9920           0x6B3310
      │                 │                  │
      └────────┬────────┘                  │
               │                           │
          0x783B70 ──call──> 0x784F60 ──> recv
                                              
          0x783F00 ──call──> 0x6B4DE0 ──> recvfrom
               │
        0x84 字节栈副本
               │
         0xA84CE0（Demonware 对象交付）

  ---- 未证/不存在 ----
  0x784F60 - - X -> 0xA2660
  0x6B4DE0 - - X -> 0x3547D0 / 0x350170
  两者   - - X -> 0x3524F0 / 0x352570
```

## 2. 上游调用者（PROVEN）

| 目标 | 调用者 |
|---|---|
| 0x6B4DE0 | 0x783F00（唯一） |
| 0x784F60 | 0x783B70（唯一） |
| 0x783F00 | 无直接调用者（经虚表 0xC9F794[4] = 0x784000？需运行时确认；本轮无静态调用边） |
| 0x783B70 | 0x6A9920、0x6ABBC0、0x6ABBC0、0x6B3310 |

## 3. 下游（PROVEN）

| 函数 | 下游 |
|---|---|
| 0x6B4DE0 | recvfrom、ntohs、0x43A7C0（错误上报） |
| 0x783F00 | 0xAB4800、0xAB4DE0、0xA86220、0xA84CE0 |
| 0x784F60 | recv、0x43A7C0、0xB84B40（错误处理） |

## 4. 未闭合边界（BLOCKED）

| 边界 | 说明 |
|---|---|
| 0x783F00 的无直接调用者 | 经虚表 `.rdata 0xC9F794` 分派（槽位 [4] = 0x784000，非 0x783F00）；真实分派路径需对象实例信息 |
| 0xA84CE0 的语义 | Demonware 对象交付点；未展开（超出本轮范围） |
| 0x6ABBC0 / 0x6B3310 的会话状态机 | 未展开（Demonware 内部） |

## 5. 数据流摘要

| 流 | 内容 | 等级 |
|---|---|---|
| socket -> 0x6B4DE0 buf | 调用者传入 | PROVEN |
| 0x6B4DE0 -> 0xD47388 统计 | 累加字节数 | PROVEN |
| 0x784F60 -> 0xD47370/0xD47374 | 错误码/状态 | PROVEN |
| 0x783F00 -> 0xA84CE0 | 0x84 字节定长交付 | PROVEN |
| -> 游戏解析器 | 无路径 | REFUTED（限定范围） |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
