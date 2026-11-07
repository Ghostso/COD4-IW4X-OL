# 20 — 大厅技术最终评估

---

## 1. 直接回答任务书 §十三 的 15 个问题

**1. CODOL 大厅完整业务流程是什么？**

```
握手(0x81/0x82/0x83+KDF)
 → bootstrap 35 请求
 → 档案确认
 → 21/5 findSessions(playlist)
 → 分叉：
    A  PvE:  mmbook → mmstart(map)
    B  房间: createRoom → setRoomData×N → (mmbook → mmstart(playlist))
 → 客户端连 UDP 28960
```
详见 `02_LOBBY_COMPLETE_STATE_MACHINE.md`。

**2. 当前哪些阶段已经真正完成？**
握手、bootstrap（35 个都通）、档案、配置、频道订阅、findSessions、createRoom、setRoomData、mmbook、mmstart 收发。共 **8/18** 行 `VERIFIED_COMPLETE`。

**3. 哪些阶段只是服务端模拟实现？**
- 商城（80/x、93/1）：空应答占位
- 12 个 bootstrap 空 ACK 服务
- 房间推送的 Ready/RoomStateUpdated/StartGame（我们自造）

**4. 哪些阶段有官方客户端实机证据？**
- 全部 56 个 run 的 bootstrap
- 32 个 run 的建房与 setRoomData
- 46 个 run 的 mmbook/mmstart
- **8 个 run 的战斗服连接（全部 10-26，全部 PvE 路径）**

**5. 哪些阶段尚未实现？**
- 成员列表协议（BP-03）
- 20 个 MM 事件推送（BP-07）
- 12 个 bootstrap 服务语义（BP-08）

**6. 哪些阶段虽然实现但客户端没有消费？**
- 房间下行推送（Ready / RoomStateUpdated / StartGame）—— 发了，未证被解析
- `dwRoomMessageStartGame`（10-28 起推，客户端无后续动作）

**7. 当前最早的业务流程断裂点在哪里？**
**BP-06：mmstart 之后客户端不建 UDP socket。**
但注意 **BP-01（准备按钮）在房间路径上更早**——只是 PvE 可以绕过它。

**8. 准备按钮为什么没有产生预期请求？**
**UNKNOWN。** 已确定：客户端本地就丢了事件（无上行、无状态变化）。
停在 Flash/Scaleform 层，三层都不可达（加密 `.ff`、无 `.gfx` 工具、ACE 拦内存）。

**9. 房间成员为什么没有正确初始化？**
因为**没有成员列表协议**。服务端只回 `memberCount` 一个标量。
`memberCount=1` 能让 `dwRoomMatchUber` 出现，但不等于初始化完成（状态机停状态 1）。

**10. 房间事件为什么没有完成状态转换？**
两个独立原因：
(a) 20 个订阅事件服务端零推送；
(b) 我们自造的推送从未证明被客户端解析（缺畸形对照）。

**11. PvE 和 BOT 房间的业务流程有什么不同？**
| | PvE | BOT |
|---|---|---|
| 21/5 请求尺寸 | 35 B（playlist=10） | 75 B（playlist=50） |
| 建房 | ❌ | ✅ |
| setRoomData | ❌ | ✅ |
| mmstart 内容 | 带 `map` | 带 `playlist 37` |
| channelID | `0` | `roomId` |
| 战斗连接 | ✅ 8/8 | ❌ 0/32 |

**12. 为什么历史成功运行可以进入战斗连接，而当前运行不能？**
**UNKNOWN（两个候选，完全共线）**：
(a) mmstart 缺 map；(b) 客户端在房间里。

已排除：102/7、memberCount、StartGame 推送、战斗服未启动、地址未下发。

**13. mmbook 和 mmstart 在真实流程中的准确位置是什么？**
```
21/5 findSessions  →  6/14 mmbook  →  6/14 mmstart  →  客户端连战斗服
        ↑                    ↑               ↑
   拿到地址            预约战斗服实例     下发开局指令
```
**mmbook 不是匹配服务，是预约；mmstart 是客户端给服务端的开局指令。**

**14. 当前大厅全部未解决问题有哪些？**
8 个，详见 `CODOL_LOBBY_ALL_UNRESOLVED_PROBLEMS.md`。

**15. 这些问题之间有什么因果关系和依赖关系？**
```
问题4(MyEventHandler) → 问题1(准备按钮)
问题2(20事件) ←→ 问题3(下行解析) → 问题6(状态机)
问题5(成员协议) → 问题1
问题7(mmstart→不连) ★ 唯一总开关，PvE 路径不依赖 1~6
```

---

## 2. 无法回答的部分（按要求说明）

| 问题 | 查到哪里 | 已证明 | 未闭合链 | 缺什么 |
|---|---|---|---|---|
| 准备按钮的 UI 回调 | Flash/Scaleform 边界 | 客户端本地丢事件 | 点击→回调 | `.gfx` 反编译或行为对照 |
| mmstart 为何不触发连接 | 两种 mmstart 形态的字段差异 | 8 成 26 败 | mmstart 解析→socket 创建 | 一次成功+一次失败的同客户端抓包 |
| playlist 37 的语义 | 三种解释 | 37≠50 | 编号空间 | 客户端代码或更多样本 |

---

## 3. 最终判定

| 项 | 结论 |
|---|---|
| 大厅骨架 | ✅ 8/18 阶段 `VERIFIED_COMPLETE` |
| 大厅肌肉（房间 UI/成员/事件） | ❌ 2 `NOT_IMPLEMENTED`、4 `BLOCKED` |
| 最后一米（连战斗服） | ⚠️ 曾成功一次（8 轮），当前不可复现 |
| 房产是否可交付 | **否**：房间路径从未产生过一次战斗连接 |

**一句话**：
**大厅已经能"走流程"，但还走不到"进游戏"。**
而且唯一走通过的那条路（PvE），现在也复现不了。
