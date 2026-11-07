# E17 — 依赖图 / DEPENDENCY GRAPH

> 图例：✔ 已满足 / ✘ 未满足 / ⚠ 部分

---

## 1. 网络输入 → 应用层 依赖链

```
[socket API]
   ├─ recv (7 处) ──┬─ 0x602441  -> 错误日志 ✘非游戏
   │                ├─ 0x6029BE  -> "Recv failure" ✘
   │                ├─ 0x6052AB  -> TLS 探测 ✘(HTTP 更新)
   │                ├─ 0x76D65C  -> thunk ✘
   │                ├─ 0x775A6C  -> socket 抽象 ⚠未归属
   │                ├─ 0x784F7D  -> 0x784F60 (Demonware) ✘
   │                └─ 0x788133  -> 未闭合 ⚠
   │
   ├─ recvfrom (3 处) ─┬─ 0x1B0BA1 -> ICMP ping ✘
   │                   ├─ 0x6B4E3C -> 0x6B4DE0 (Demonware) ✘
   │                   └─ 0x775ADE -> socket 抽象 ⚠未归属
   │
   └─ (无 WSARecv/WSARecvFrom 导入)

   应用层游戏消息分派器：✘ 未定位
        实时 Gamestate 0x03 消费者：✘ 未定位
        Configstring body 0xA2660 实时归属：✘ BLOCKED
```

## 2. 本轮闭合的子图

```
0x783B70 ──call──> 0x784F60 ──call──> recv
   │                    │
   │                    └──> [0xD47370] = WSA 错误码
   │                    └──> [0xD47374] = 状态 2
   │
0x783F00 ──call──> 0x6B4DE0 ──call──> recvfrom
   │                    │
   │                    ├──> ntohs -> [ebx]
   │                    └──> [0xD47388/0xD47398] += 统计
   │
   └──> 0x84 字节栈副本 -> 0xA84CE0（Demonware 交付）
```

## 3. 关键未闭合依赖

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| 游戏入站路径 | 未定位任何游戏特征消费者 | BLOCKED |
| 0x775A50/0x775AB0 归属 | 虚表实例化路径未定位 | BLOCKED |
| 0x788133 (recv) 归属 | 未审计 | BLOCKED |

## 4. 与 E-16 依赖图的衔接

E-16 结论：E-13 的 2 条候选（0x1B0430、0x78772D）被排除。
E-17 结论：E-13 清单中另外 2 条候选（0x6B4DE0、0x784F60）也被排除。

累计：E-13 的 9 个收包函数中，已归属 7 个（均非游戏）；剩余 2 个为 0x775A50/0x775AB0（socket 抽象虚表）。
