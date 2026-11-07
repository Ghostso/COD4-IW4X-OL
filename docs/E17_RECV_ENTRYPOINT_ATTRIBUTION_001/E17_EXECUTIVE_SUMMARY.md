# E17 — 执行摘要 / EXECUTIVE SUMMARY

> 任务编号：E17_RECV_ENTRYPOINT_ATTRIBUTION_001
> 模式：只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> **冻结基线（开工与收工各复核一次，均一致）：**
> - 客户端 `codoMP_client_shipRetail.exe` = `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`
> - 恢复镜像 `codol2697-static-candidate.bin` = `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`
> - 服务端 `codol_dedrun.exe` = `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`
> 地址为 RVA（VA = RVA + 0x400000）。
> 工具来源：自建脚本（`_tools/`）+ E-06 恢复镜像；无 IDA/Ghidra 数据库人工标注被当作原始事实。

---

## 1. 三句话结论

1. **`0x6B4DE0` 与 `0x784F60` 都是 `recv`/`recvfrom` 的薄封装（PROVEN）**，不是应用层消费者。
2. **两者的调用者簇（`0x783xxx` / `0x6A9xxx` / `0x6ABxxx` / `0x6B3xxx`）属 Demonware 传输/会话栈（INFERRED 强）**——镜像含 `DW-Client-Ticket`、`demonware.net`、`bdSessionParams@@` 字符串。
3. **两者 7 层闭包内不接触任何游戏协议解析器（PROVEN 负）**：`0xA2660`/`0x3547D0`/`0x354100`/`0x350170`/`0x34FD80`/`0xA2E50`/`0x3524F0`/`0x352570` 全部不在闭包内。

## 2. 归属裁定

| 候选 | 真实职责 | 归属 | 等级 |
|---|---|---|---|
| `0x6B4DE0` | `recvfrom` 薄封装 + socket 统计累加 | **Demonware 传输层（非游戏应用层）** | PROVEN（职责）/ INFERRED（模块） |
| `0x784F60` | `recv` 薄封装 + socket 状态记录 | **Demonware 传输层（非游戏应用层）** | PROVEN（职责）/ INFERRED（模块） |

## 3. 是否找到游戏会话入站路径

**否（BLOCKED，限定范围）。** 本轮审计的 2 个候选均已归属到非游戏功能（Demonware 传输层）。

## 4. 最小阻塞点

**游戏协议的应用层入口仍未定位。** 当前收包原语总台账（本轮全量）：

| 原语 | 调用点数 |
|---|---|
| recv | 7 |
| recvfrom | 3 |
| send | 5 |
| sendto | 4 |

其中已归属：ICMP ping（`0x1B0BA1`/`0x1B09EF`）、HTTP 更新（`0x60522*`/`0x6104D0` 链）、Demonware 传输（`0x6B4E3C`/`0x784F7D`）、错误日志（`0x602441`/`0x6029BE`）、socket 抽象（`0x775A6C`/`0x775ADE`）。

## 5. 建议

1. 对 **`0x775A50`/`0x775AB0` 虚表** 的实例化路径做定向审计（这是最后一个有 socket 语义但未归属完整的簇）。
2. 若虚表归属后仍无游戏特征，则需转向 `.tvm0` 之外的间接分派审计（函数指针表枚举）。
3. **不**建议继续扩大 recv/recvfrom 调用点普查——边际收益已下降。

## 6. 问题库与解决率

依 E-15 权重标度：新增 Q-20（`0x6B4DE0` 归属，权重 3，PROVEN=1.0）、Q-21（`0x784F60` 归属，权重 3，PROVEN=1.0）、Q-22（Demonware 栈是否为游戏路径，权重 5，BLOCKED=0.0）。

- 旧总权重 103（E-16）-> **新总权重 114**
- 新增加权得分 = 3 + 3 + 0 = 6
- 新加权得分 = 36 + 6 = 42
- **风险加权解决率 = 42 / 114 = 36.8%**

（E-16 为 34.9%；本轮 +1.9 个百分点。）
