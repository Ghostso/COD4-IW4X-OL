# 00 — CODOL 复活项目 049:连接无关握手实现 + in-match 收包链定向突破

**任务号:** `CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049`
**承接:** 040–048
**性质:** 实做(代码 + 可复现构建 + 测试)+ 并行只读取证
**日期:** 2026-10-14

---

## 0. 六问直答

**A. 握手模块新增了哪些实际代码?**
在 047 工程独立分支 `049/connectionless-handshake` 新增 4 个文件、26 项测试:

| 文件 | 内容 |
|---|---|
| `src\Codol.BattleServer\Protocol\Handshake\HandshakeEvidence.cs` | 证据分级、`[TestOnly]`、`UnprovenHandshakeSurface`(8 项未证实面) |
| `src\Codol.BattleServer\Protocol\Handshake\ConnectionlessHandshake.cs` | 报文解析/边界检查、词表注册、`getchallenge`/`connect` 数据模型、`challengeResponse`/`connectResponse`/`connectReject` 处理接口、重复请求检测 |
| `src\Codol.BattleServer\Sessions\HandshakeStateMachine.cs` | 7 态状态机 + 完整合法转移表 + 超时/拒绝/重置 |
| `tests\Codol.BattleServer.Tests\HandshakeTestFixtures.cs` | `SIMULATED_HANDSHAKE_TEST_ONLY` 测试夹具(全部 `TEST_ONLY_` 前缀) |

**B. 哪些格式直接得到证据支持,哪些仍是模拟?**
- **证据支持:** 14 个连接无关命令词及其方向(RVA 0x9BFCE8..0x9BFFA0;比较点 0x1C1685..0x1C1DF0);客户端自身构造的 `getchallenge 0 "%s"`(0x9BFD04)、`connect %s "%s"`(0x9BFE28)。→ 本工程据此实现的**词法/边界/方向**是客户端证据支持的。
- **模拟(`SIMULATED_HANDSHAKE_TEST_ONLY`):** 所有 `challengeResponse`/`connectResponse`/`connectReject` 的**载荷内容**。`UnprovenHandshakeSurface` 显式列出 8 项未证实面(challenge 算法、nonce 长度、鉴权、连接序号、OOB 前缀、响应封装等)。

**C. 测试和构建是否真实通过?**
是。Release 构建 **0 warning / 0 error**;测试 **65 passed / 0 failed**(39 基线 + 26 新增);`dotnet build --no-incremental` 两次产物 SHA-256 **逐字节一致**;040–046 历史 **547 文件 0 失败**。命令与哈希见 `05`。

**D. P5 消费循环或连接无关队列是否找到了新的生产者/注册关系?**
是,取得 3 条新关系(见 `06`/`07`):
1. **P5 消费循环启动链闭合了一段:** `0x7A41D0` ← `0x7A4430` ← thunk `0x7A47E0` ← **`0x7838A0`**(P5 per-tick driver)。循环无 dword 指针引用 → 由 driver 直接 `call`,不是 vtable 注册。
2. **连接无关泵 `0x0F8FB0` 的唯一直接调用者是 `0x1BF3BC`**(在 `0x1BF300` 内),`0x1BF300` 的调用者为 `0x1BF52D / 0x37976B / 0x37C2F5`。
3. **修正 048 的一处地址口径错误:** 泵的出队被调用者实为 **RVA `0x221E50`**(VA `0x621E50`);048 把它记为 `0x621E50` 并 dump 了错误区域。

**E. 当前最小未闭环边在哪里?**
**P5 `recv` 缓冲 → 消息解析器输入** 这条边。已证实 P5 `recv(buf,len)`(`0x873A00` → `0x876ED0`),也已证实循环内**读 1 字节并按 0x81/0x83/0x84/0x85 分支**,但该字节的来源缓冲(`0x7765A0` 的 `arg1`)尚未与 `recv` 缓冲建立指令级连接。

**F. 050 应该立即实现哪个模块或解决哪个单一阻塞项?**
**唯一优先目标:** 证明 `0x7A41D0` 内 `0x7765A0` 读取的缓冲 == P5 `recv` 的 `buf`(或给出带地址的否定证据)。这是 `OpcodeDispatch` / `Gamestate` / `ConfigStrings` / `Snapshot` 四模块共同的唯一缺口。详见 `10`。

---

## 1. 交付物导航

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文 |
| `01_INPUT_IDENTITY_AND_HASHES.md` | 输入身份、SHA-256、PE 结构、恢复覆盖、工作区所有候选映像 |
| `02_HANDSHAKE_PROTOCOL_EVIDENCE.md` | 握手协议证据:词表、方向、格式串、未证实面 |
| `03_HANDSHAKE_IMPLEMENTATION.md` | `ConnectionlessHandshake` 实际代码与边界 |
| `04_SESSION_STATE_MACHINE.md` | 7 态状态机、转移表、失败路径 |
| `05_TESTS_AND_BUILD.md` | 构建 / 测试 / 哈希 / 确定性 / 历史不可变性 |
| `06_P5_CONSUMER_CHAIN.md` | D1:P5 消费循环启动者与缓冲追踪 |
| `07_CONNECTIONLESS_QUEUE_PRODUCER.md` | D2:连接无关泵队列与生产者链(含 D0 地址口径修正) |
| `08_SECTION3_GAP_ANALYSIS.md` | D3:第 3 节区缺口身份与覆盖 |
| `09_PROTOCOL_READINESS_MATRIX.md` | D4 + E:9 模块实现准备度矩阵 |
| `10_NEXT_ACTION_DECISION.md` | 050 唯一优先目标 |
| `scripts\049_harness.py` | 共享只读分析骨架 |
| `scripts\analyze_049.py` | 一键重生成全部证据 JSON + dump |
| `scripts\verify_049.py` | 44 项断言自检 |
| `evidence\` | 反汇编 dump / JSON / token 表 |
| `SHA256SUMS.txt` | 完整性清单 |

## 2. 完成标准对照

| # | 标准 | 结果 |
|---|---|---|
| 1 | 握手模块有真实代码 | ✅ `03`(3 个源文件,提交 `64f5095`) |
| 2 | 状态机确定转移 + 失败路径 | ✅ `04`(7 态 + 完整转移表) |
| 3 | 新增测试实际执行通过且区分模拟 | ✅ `05`(65/65;`SIMULATED_HANDSHAKE_TEST_ONLY`) |
| 4 | 工程可重复构建 | ✅ `05`(确定性哈希一致) |
| 5 | in-match 候选获得新可复核追踪 | ✅ `06`/`07`(3 条新关系 + 1 处 048 修正) |
| 6 | 第 3 节区缺口身份与覆盖分析 | ✅ `08` |
| 7 | 不能闭环处有明确断点,不推断 | ✅ `06`§6 / `07`§6 / `10` |
| 8 | 历史产物与客户端基线不变 | ✅ `05`(547 文件 0 失败) |
| 9 | 给出下一任务唯一优先目标 | ✅ `10` |

## 3. 复现命令

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049
python scripts\analyze_049.py
python scripts\verify_049.py          # 44/44 PASS

cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047
powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1 -Configuration Release
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-history-immutability.ps1
```

