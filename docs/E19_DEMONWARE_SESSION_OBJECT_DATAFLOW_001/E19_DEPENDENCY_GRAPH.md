# E19 — 依赖图 / DEPENDENCY GRAPH

> 图例：✔ 已满足 / ✘ 未满足 / ⚠ 部分

---

## 1. 本轮闭合的协议接收链（PROVEN）

    [socket] ──► 0xB83B70 (Demonware recv 封装, E-17/E-18)
                    │  recv(sock, dst, len, 0)
                    ▼
    0x6ABBC0 帧头读取器 (this = 会话对象)
        │  dst = this+0xA0 (4 字节头缓冲)
        │  used = this+0xA4
        ▼  满 4 字节
    0x6878A0 边界检查 + memcpy
        │  长度 → this+0xAC
        ▼
    cmp len, this+0x98 (上限)
        │
        ├─ len==0  → this+0x9C = 0 (回状态 0)
        ├─ len>上限 → 报错 + 0x6AA770 → 返回 -11
        └─ 正常     → this+0x9C = 2 (状态 2)
                        ▼
    0x6A9920 类型码 + 载荷
        │  1 字节类型码 → this+0xA8
        ├─ 类型1 → size 1
        ├─ 类型2 → size 9
        ▼
    0xAA84E0 分配 → this+0xB0
    0x6A9A30 第二次 memcpy (长度 5)

## 2. 状态机（PROVEN）

    this+0x9C 状态 ∈ {0,1,2,3}
        │  jmp [ebx*4 + 0x6AC090]
        ├─ 0 → 0x6ABE99 reset + 释放 +0xB0/+0xB4
        ├─ 1 → 0x6ABF1D 调 0x6ABBC0（读头）
        ├─ 2 → 0x6ABF47 调 0x6A9920（读类型码+载荷）
        └─ 3 → 0x6ABF52 调 0x989230/0xAC4070 → 0xB83B70

## 3. 未闭合依赖（关键）

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| 游戏会话消息承载 | 类型码 1/2 语义未定；未见游戏 opcode | BLOCKED |
| 应用层消费者 | 4 层闭包无游戏解析候选 | BLOCKED |
| 会话对象构造者 | 未定位 vptr 写入 | BLOCKED |
| 与 0xA2660 等连接 | 闭包不相交 | REFUTED（限定范围） |

## 4. 与已知游戏解析器的间隔

    E19 会话对象状态机 (0x6ABE80)
        │  ✘ 无调用边
        ▼
    0xA2660 / 0xA2E50 / 0x350170 / 0x3547D0 / 0x354100
        （4 层闭包 48 函数内均不出现）

## 5. 全项目视角

| 已归属的网络入口 | 归属 | 等级 |
|---|---|---|
| 0x775A6C / 0x775ADE | libcurl recv/recvfrom（E-18） | PROVEN |
| 0x6B4E3C / 0x784F7D | Demonware recv 封装（E-17） | PROVEN |
| 0x1B0BA1 | ICMP ping（E-16） | PROVEN |
| 0x6052AB | TLS/HTTP 更新（E-15） | PROVEN |
| 0x602441 / 0x6029BE | 错误日志（E-15） | PROVEN |
| **0x6ABBC0 链** | **Demonware 协议分帧 + 状态机（E-19）** | **PROVEN（分帧）/ BLOCKED（游戏归属）** |
| 0x788133 | 独立 recv 点；与 0x6ABBC0 无关（E-19） | PROVEN（归属） |

**这是首个找到"长度前缀分帧 + 状态机 + 类型码"的客户端协议栈。**
