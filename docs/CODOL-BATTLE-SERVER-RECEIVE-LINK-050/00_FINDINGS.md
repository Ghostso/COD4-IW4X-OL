# 050 — P5 收包与读取器的字节来源复核

日期：2026-10-14。目标沿用 049 的 050-T1：核实 0x7A20A0 中 recv 的数据是否流入 0x7A44D8 调用的单字节读取器。全部工作基于静态映像和现有历史记录；没有启动或修改游戏客户端。

## 输入身份

- 静态映像：CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin，SHA-256 17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045，大小 10,899,456 字节。
- 地址口径：文中地址均为 RVA；VA = RVA + 0x400000。没有把超出映像的虚拟地址当作可读数据。
- 既有反汇编：049/evidence 中的 d40_p5_loop、d42_p5_recv、d44_p5_msgreader、d45_p5_7A20A0。从同一映像另复核 0x79BBB0、0x79BEB0、0x79BD40、0x778350。

## 已证实的数据流

1. 0x7A20C8 将 ecx 保存到 esi；0x7A20CC 设置 edi = esi+0xA8；0x7A20D2 将其作为缓冲参数传给 0x873A00。该包装在 0x873A0E 调用 0x876ED0，后者在 0x876EED 调用 recv。所以 [esi+0xA8] 是本次单字节收包的目的地。
2. 0x7A20E9 立即读取该字节，比较 1 / 2；ebx 因此为 9 或 1。0x7A2118 从 [esi+0xAC] 读长度，扣除 ebx+1，0x7A2125 用这个值构造对象。0x7A2161 将新对象保存在 [esi+0xB0]。这证明长度和类型影响了对象构造。
3. 0x7A44AD 读取 [esi+0xB0]，0x7A44B3 调用 0x79BBB0 获取其数据指针。0x7A44CC 将指针传给 0x7765A0；0x7A44CB 传入 [esi+0xAC]-1 作为边界，0x7A44C3/C4 传出字节和游标地址。0x7765BA 再调用 0x7783C0，0x7765CC 写出所读的字节。
4. 0x7A44F6、0x7A4557、0x7A45F0、0x7A46AE 分别比较输出字节与 0x81、0x83、0x84、0x85。分支地址已证实；这些数值的最终游戏协议语义未证实。

## 首个未证实的字节级步骤

0x79BEB0 只接收长度和标志，并调用 0x79BD40 分配对象内部缓冲；它没有收到 esi+0xA8 的指针。0x7A21B0 和 0x7A21D6 的 0x778350 调用分别从局部长度值和那个类型字节写入 5 位字段，未显示剩余包体的拷贝。0x7A21E4 把对象前缀设置为 ebx；0x79BBB0 根据 [object+0x1C] - [object+0x24] + 0x1F 返回指针。

因此，目前不能证明 0x7765A0 读取的字节就是 recv 的后续 payload。可以证明两端使用同一个会话对象、同一长度/类型控制链，不能把“对象构造”写成“payload 已复制”。这也不能构成“读取器绝不消费 recv 数据”的否定证明：包体可能经对象内部机制填入，仍需其写入点。

历史动态记录 CODOLServer/CONFIRMED_RESULTS_20260928.md 第 31–33 节提供读入器内存快照和旧实验，但同一文档明确写着没有在 C8==2 时抓到该缓冲区快照，并记录多次偏移推断被推翻。它支持继续定位缓冲区写入点，不能填上这一条精确的指令级边。该历史路径描述的是大厅 TCP 收帧；048 的业务归属审计也把 P5 归为客户端传输候选，没有证实其为最终战斗消息路径。

## 实施与验收

- 工程分支：CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047 的 050/recv-to-consumer-trace。新增 P5ReceiveTrace 记录地址链与缺口；更新 ProtocolModuleReadiness，保留四个接收依赖模块的阻塞状态；新增一项对应测试。没有注册未知 opcode，也没有输出猜测的线上包。
- Release 构建：0 warning / 0 error；离线测试 66 passed / 0 failed。历史 040–046 的 547 个文件完整性复核为 0 failure。
- 本轮未完成客户端连通、战斗对局或“恢复全部功能”。CODOL-Combat-Server-v0.1 仍是可启动、自测通过的独立基线；其 README 明确记录了真实客户端未连上、地图碰撞和伤害系统未实现。
- 额外复核了该基线现有 build/bin/CODOLCombatServer.exe 的 --selftest：251 passed / 0 failed。其默认配置同时写着 map=mp_firingrange、gametype=coop 与 session_map=mp_crash_tropical；这会让导出的会话地图与服务器实际地图不一致。另有独立问题：SessionDescriptor.BuildMissionSessionObject 的地址块将 127.0.0.1:28960 写死，SessionExporter.Build 调用它时未传递配置的 session_endpoint，因此宣称会话端点与监听端点一致的校验并没有覆盖 mission 对象。由于该描述符也包含历史黄金向量和大厅契约，本轮只记录这些不一致，没有未经验证地重写权威字节。

## 下一条可执行证据

定位对象 [esi+0xB0] 的内部写入点，优先从 0x7A21B0 / 0x7A21D6 调用的 0x778350、0x7A21E5 的 0x79BB90、以及 0x7A42C2 状态 3 的第二次 recv 回溯。完成条件是给出 recv(buf) -> payload 字节 -> [esi+0xB0] 数据区 -> 0x7765A0 的逐指令、逐偏移链；若源自另一数据源，给出对应的写入与调用链。其后仍须确定 opcode 的语义、gamestate/snapshot 和 usercmd 的真实线上格式，并做真实客户端端到端验证，才能称为可玩战斗。
