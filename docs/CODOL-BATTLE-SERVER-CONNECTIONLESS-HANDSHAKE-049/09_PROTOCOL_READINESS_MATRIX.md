# 09 — D4 连接注册与函数指针 + 协议实现准备度矩阵

---

## Part A — D4:连接注册与函数指针

**目标:** 对 socket 生产者、消费者循环及相关注册点,检查 vtable/回调表/函数指针写入、
间接调用目标及参数来源、队列生命周期。

### A1. 立即数 dword 指针引用(VA 立即数搜索)

对下列入口搜索全映像内的 4 字节立即数引用(`mov [reg+imm], imm32` / 表项):

| 入口 | RVA | dword 立即数引用数 |
|---|---|---|
| P5 消费循环 | `0x7A41D0` | **0** |
| P5 子消费者 | `0x7A20A0` | **0** |
| P5 driver | `0x7838A0` | **0** |
| 连接无关泵 | `0x0F8FB0` | **0** |
| 出队(修正后) | `0x221E50` | **0** |
| P5 recv 包装 | `0x873A00` | **0** |
| 泵 driver | `0x1BF300` | **0** |

**结论:** 这些入口**没有**被静态函数指针表/vtable 以立即数登记。
P5 循环由 `0x7838A0` **直接 `call`**;泵由 `0x1BF3BC` **直接 `call`**。
**静态交叉引用**已确认;任何"运行期注册"都属于**动态目标猜测**,本任务不做。

### A2. 间接调用目标及参数来源

| 函数 | 间接调用站点 | 目标 | 参数来源 |
|---|---|---|---|
| P5 循环 `0x7A41D0` | `0x7A4202` | `jmp [ebx*4+0xBA4400]`(内部状态跳转表) | `ebx=[esi+0x9C]`,0..3 |
| P5 循环 | `0x7A4246` / `0x7A4276` | `call edx`(对象 vtable[0]) | `[esi+0xB0]`/`[esi+0xB4]` 对象 |
| P5 循环 | `0x7A436E` | `jmp [eax*4+0xBA4410]` | 内部状态 |
| 连接无关泵 `0x0F8FB0` | `0x0F90BE`/`0x0F90F0` | `call esi`(`[0xCA84C8]`) | 时间源函数指针 |
| 连接无关泵 | `0x0F90CC` | `call edi`(`[0xCA812C]`) | 时间/计数原语 |
| 泵 driver `0x1BF300` | `0x1BF36C`/`0x1BF3B2` | `call edi`(`[0xCA8164]`) | 时间原语 |
| 泵 driver | `0x1BF3B0` | `call esi`(`[0xCA818C]`) | 延时原语 |

- `[0xCA84C8]`、`[0xCA812C]`、`[0xCA8164]`、`[0xCA818C]` 等是**运行期导入槽**
  (VA → RVA `0x8Axxxx`),其内容在磁盘映像是**运行期地址**,不能静态解析为具体 API。
  **它们不是 ws2_32 槽**(ws2_32 槽已单独解析为 RVA `0x8A8380..0x8A855C`)。
- 出队 `0x221E50` 内部对队列对象做 `vtable+0x20`(状态)与 `vtable+0x2C`(出队)虚调用,
  由 `[0xCA819C]`/`[0xCA8190]` 临界区保护。

### A3. 队列初始化/注册/销毁/生命周期

- 出队 `0x221E50` 使用 `[0xCA819C]`(加锁)/`[0xCA8190]`(解锁)包裹,
  并 `call 0x643300` → `call 0xBAC600` 取得队列接口对象;
- 队列对象的**构造/注册点**未在本轮定位(其初始化很可能在不可读区或经动态注册);
- P5 循环的 `[esi+0xB0]`/`[esi+0xB4]` 在循环内检查+释放+重建(`0x7A421E`..`0x7A427E`),
  属**每会话对象生命周期**,由 `esi` 指向的会话对象管理。

### A4. 静态交叉引用 vs 动态目标猜测(严格区分)

| 关系 | 类型 | 依据 |
|---|---|---|
| `0x7A41D0` ← `0x7A4491` | **静态确认** | `E8` 直接调用 |
| `0x7A4430` ← thunk `0x7A47E0` ← `0x7838A0` | **静态确认** | `E8`/`E9` 直接 |
| `0x0F8FB0` ← `0x1BF3BC` | **静态确认** | `E8` 直接 |
| `0x221E50` ← `0xF8F25`/`0xF9075` | **静态确认** | `E8` 直接 |
| 时间源/队列接口的具体目标 | **动态,未证** | 运行期导入槽 |
| "某 vtable 在运行期注册了 P5 循环" | **未证,不主张** | 无立即数引用,也无动态证据 |

**最小闭环(本轮达成度):**

```
socket recv → 队列/缓冲 → 消费循环 → 消息解析/opcode 读取
   部分证实    部分证实      已证实        已证实(读字节+分支)
```
- `socket recv`(P5 `0x873A00`)✅;**recv 缓冲 → 消费循环输入** ❌(断点);
- `队列/缓冲`(连接无关队列 + P5 `[esi+0xB0/0xB4]`)部分证实;
- `消费循环`(`0x7A41D0`,driver `0x7838A0`)✅;
- `消息解析/opcode 读取`(`0x7765A0` 读字节 → `cmp 0x81/0x83/0x84/0x85`)✅(值语义未证)。

---

## Part B — 九模块协议实现准备度矩阵(049 更新)

证据等级沿用 046 口径。`OFFICIAL_CLIENT_COMPATIBLE` **本轮无任何模块达到**。

| # | 模块 | 原始证据 | 已实现代码 | 测试覆盖 | 官方客户端兼容性 | 未解决问题 | 下一步最小证据 |
|---|---|---|---|---|---|---|---|
| 1 | **Connectionless handshake** | 14 token + 方向(RVA 0x9BFCE8..0x9BFFA0);请求格式串 0x9BFD04/0x9BFE28 | `ConnectionlessHandshake`(解析/词表/请求模型/响应接口) | 13 项 handshake 测试 | **明文层:客户端证据支持**;响应载荷:未证 | challenge 算法/nonce/鉴权/OOB 前缀/响应封装 | 服务端样本 或 未连接 socket 前缀写入点 |
| 2 | **Session establishment** | 同上 + 状态机 | `HandshakeStateMachine`(7 态) | 13 项 session 测试 | **内部模型**;未与官方服务端交互 | challenge 校验规则;connect↔challenge 字段关联 | 服务端握手样本 |
| 3 | **Opcode dispatch** | P5 读字节 `0x7765A0` + `cmp 0x81/0x83/0x84/0x85`(`0x7A44F6` 等) | `FinalCodolOpcodeDispatcher`(**空表 + 显式拒绝**) | 3 项(表空/未知拒绝/需证据) | **否** | 字节值→opcode 名映射;缓冲来源 | `recv` 缓冲 == `0x7765A0` arg1 |
| 4 | **Reliable commands / ACK** | `EXE_LOSTRELIABLECOMMANDS`(错误上报);出队 RVA 修正为 0x221E50 | `ReliableCommandChannel`(内部窗口/重传) | 4 项 | **否** | 线格式序号/ACK 位图 | 可靠命令读取+入队点 |
| 5 | **Gamestate** | `CA_GAMESTATE`/`gamestateupdate %d`(诊断串) | `GameStateModel`(内部) | 3 项 | **否** | 收包缓冲→状态转换数据流 | 同上(缓冲来源) |
| 6 | **Configstrings** | `EXE_CONFIGSTRINGMISMATCH`/`ExpectedNetConfigStringMismatch`(错误处理) | `ConfigStringTable`(边界检查) | 1 项 | **否** | 索引→存储的指令级读写点 | 同上 |
| 7 | **Snapshot framing** | `process snapshots`(日志) | 帧容器抽象 | — | **否** | 帧边界/分片/结束标记 | 同上 |
| 8 | **Netfield / delta decoding** | **无** | 无 | 无 | **否** | netfield 表 + EOF | opcode 表 + netfield 表 |
| 9 | **Usercmd / movement sync** | 项目侧宽度表(`CONTRADICTED`) | `MovementModel`(内部) | 5 项 | **否** | 官方线格式 | 官方 usercmd 样本 |

### 关键纪律(逐条遵守)

- **不**因"接口已存在"升级为兼容;`FinalCodolOpcodeDispatcher` 表仍为**空**。
- **不**因"测试通过"升级为兼容;测试是内部一致性,不是官方兼容。
- **不**因"状态机完整"升级为兼容;`Connected` 仍需证据 id。
- 只有模块 1 的**明文识别/边界层**达到"客户端证据支持";其响应层与模块 2 的端到端仍未证。

### 代码层固化

`Analysis\ProtocolModuleReadiness` 已更新 3 条 verdict 的 `MinimumMissingFact`:
- Handshake → 列明 8 项未证实面;
- OpcodeDispatch → 指向 049 的 P5 读字节证据与"缓冲未追溯";
- ReliableCommandsAndAck → 记录出队 RVA 修正。
测试 `analysis/module-readiness-single-ready` 仍断言**恰好一个**模块 Ready,且
`SnapshotNetfieldDelta` 仍为 `Blocked`。
