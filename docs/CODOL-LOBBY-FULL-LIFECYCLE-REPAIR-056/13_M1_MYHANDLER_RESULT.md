# 13 — M1 实验：MyEventHandler 与建房闸门（Q3）

> 2026-10-29。M1 用 GOLDEN 独立 Kit 单发 + 提权扫描器，覆盖建房后 76 秒，12 轮扫描。
> **结论：055 问题 4 已答；同时发现"memberCount 是建房闸门"的结论被混淆变量污染。**

---

## 一、方法

- Kit：`run_codol_001/kit_M1_MYHANDLER_20261029`（= GOLDEN 副本 + 成功轮 `coop_map.txt`）
- 扫描器：`RUNS/M1_MYHANDLER_20261029/m1_scan_vtables.py`（只读堆；搜 vtable 指针；
  经提权 Agent 抢早期句柄——普通进程 OpenProcess 被 ACE 拒 err=5）
- 全部 vtable 地址先用 E1 全内存转储验证为**真 vtable**（内容皆为镜像内代码指针）：

| 符号 | vtable VA | 转储首 dword | 有效？ |
|---|---|---|---|
| dwroomimp（对照） | 0x00DC7274 | 0x006391E0 … | ✅ |
| dwroommatchuber | 0x00DC795C | 0x0063E100 … | ✅ |
| my_event_handler | 0x00DC78F0 | 0x0063B500 … | ✅ |
| dwroommessage_text | 0x00DC7504 | 0x00625970 … | ✅ |

---

## 二、答案：MyEventHandler 在本 build 从未实例化

对 E1 全内存转储（2 GB）逐字节搜索各 vtable **地址值**的出现位置：

| vtable | 转储内出现次数 | 位置 |
|---|---|---|
| `dwroomimp` | 2 | .text 1 处 + **堆实例 1 处**（0x3EAEA240） |
| `dwroommatchuber` | 2 | **仅 .text**（0x63BCD1 / 0x63C014） |
| `dwroommessage_text` | 3 | 仅 .text |
| **`my_event_handler`** | **0** | **全镜像无处出现** |

**`my_event_handler` 的 vtable 地址在整个 2 GB 内存里出现 0 次**——连写 vptr 的构造代码都不存在。
⇒ **`MyEventHandler` 在本 build（3.19/1649370）从未被实例化**，不是"memberCount 不够"的问题。

**对原始因果链的修正：** 055 的因果图假设
`dwRoomMatch::Init → MyEventHandler → slot[1]=0x63B500 → dwRoomMatchUber`。
既然 MyEventHandler 根本不存在、而 `dwRoomMatchUber` 在 mc=1 时确实出现，
**`dwRoomMatchUber` 必然由另一条路径创建**（055 §4 的假设 2 成立）。
"MyEventHandler 缺失 ⇒ 建房链断"这一环在本 build 不成立。

---

## 三、★ 更重要的发现：memberCount 结论被混淆变量污染

M1 实机（GOLDEN，memberCount=1，建房完成于 14:13:43）12 轮扫描结果：

| 轮次 | my_event_handler | dwroommatchuber | dwroomimp（对照） |
|---|---|---|---|
| 全部 12 轮（含建房后 76 s） | 0 | **0** | 1 |

这与 10-27 A/B 的结论矛盾。核对两轮**实际使用的 lobby_server**：

| 轮次 | lobby_server.py | memberCount | **第三个 u32** | dwRoomMatchUber |
|---|---|---|---|---|
| 10-26 成功轮 / E1 | `8A1D2840…`(78 KB) | 0 | **18** | 无 |
| 10-27 A/B（EARLIEST2） | `322912F5…` | 1 | **18** | **有** 0x3ACA0CD8 |
| GOLDEN / M1（本轮） | `FF473204…` | 1 | **1** | **无** |

A/B 是从**原始 18** 改 memberCount 0→1（结论只在 third=18 的 kit 内成立）；
GOLDEN 后来把 third 也改成了 1 —— 于是 memberCount=1 **不再产生对象**。

⇒ **"memberCount=1 是建房闸门"不成立。** 真正的条件至少是
`memberCount=1` **且** `第三个 u32=18`（或另有第三个变量）。

A/B 结论本身也有旁证错误：memory 记"MyEventHandler 零实例"被当作 memberCount=0 的后果，
但 M1 证明 **mc=1 时它同样是 0**（且全镜像无引用）。

---

## 四、附带观测

- `dwRoomMatchUber_obj`（[0x82E1518]）12 轮恒为 0，与堆扫描一致。
- `start_requested`（0x849B61C）在**建房之前**就已是 1（t+107 s），与"A/B 中随对象出现由 0 变 1"不符 ⇒ 该地址的语义需重新确认。
- 阳性对照有效：`dwroomimp=1`（0x3AE005A8）、`conn_obj` 在大厅连接后出现 0x3AE89F20。

---

## 五、M1b（单变量）结果：第三个 u32 也不是闸门

Kit `run_codol_001/kit_M1B_THIRD18_20261029`（**GOLDEN + 仅把 createRoom 第三个 u32 由 1 改回 18**；
运行时大厅服 SHA-256 = `EF1CCD8C3A8E147F81A759384DC83762C379878509B30D5688EBDE4860484FC3`），
Run `ONCE_20261029_142248`，建房 14:23:50，**扫描 14 轮（t+22 s → t+262 s，覆盖建房后约 208 秒）**，
读取覆盖率恒为 **100%**（末轮 #15 覆盖 0% = 客户端已退出）：

| 轮次（建房后） | my_event_handler | dwroommatchuber | dwroomimp（对照） |
|---|---|---|---|
| #5–#14（建房后 9–208 s） | 0 | **0** | 1 |

> 证据：`E:\codol_m1_run3\scan.txt` / `scan.jsonl`；`postflight.json` `protected_ok: true`、
> `returncode: 0`、`client_pids: [14712]`。

⇒ **第三个 u32=18 单独不能恢复对象创建。** M1 + M1b 合起来把 A/B 结论的两个候选变量
（memberCount、第三个 u32）都排除了：

| 试验 | memberCount | 第三个 u32 | 对象出现？ |
|---|---|---|---|
| 10-26 轮 / E1 | 0 | 18 | 否 |
| 10-27 A/B（**不同版大厅 322912F5**） | 1 | 18 | **是** |
| GOLDEN（M1） | 1 | 1 | 否 |
| GOLDEN+third18（M1b，**与 GOLDEN 仅差这一个 u32**） | 1 | 18 | 否 |

两轮服务端推送行为也已对比：A/B 轮与 M1b 轮在房间阶段**推送几乎相同**
（11/4 回显 242/194、114/70、242/190；M1b 多一条 194/153 的 StartGame）

⇒ 剩下的解释是**两版大厅服本身的行为差异**。

> ⚠ **2026-10-29 用户确认：M1/M1b 两轮一直都在建房**（与 A/B 那轮相同的 UI 动作）。
> 因此先前"M1/M1b 点的是剧情任务入口、UI 路径不同"的推测**已被排除**。
> 唯一剩下的变量是 **GOLDEN 与 10-27 版大厅服（322912F5）之间除 createRoom 字段外的差异**。

## 七、M1C / M1D：继续二分（两个变量均已排除）

用户确认：**M1/M1b/M1C 三轮一直都是建房**（与 A/B 相同 UI 动作）⇒ UI 路径假设作废。

### M1C —— 关掉 GOLDEN 独有的 `dwRoomMessageStartGame` 推送

Kit `kit_M1C_NOSTARTGAME_20261029`（= M1b + 两处 StartGame 推送用开关 gate 住，无 `startgame_push.on` ⇒ 不发）。
Run `ONCE_20261029_143139`：建房 14:32:40，日志确认
`★ M1C: 11/4 处 dwRoomMessageStartGame 推送已禁用 (payload 109 字节未发)`。

| 轮次（建房后） | my_event_handler | dwroommatchuber | 覆盖率 |
|---|---|---|---|
| #5–#8 | 0 | **0** | 100% |

⇒ **StartGame 推送不是抑制因素**（且本轮客户端只建房+11/4，未发 findSessions/mmstart）。

### M1D —— 关掉 nt10 补丁 5（GateB 放行）

动机：A/B 轮用的是 **4 补丁** nt10，GOLDEN 是 **5 补丁**（第 5 个把 `0x0062FE80` 写成 `B0 01 C3`，
即 GateB / 自动开局状态机入口闸门恒返回真）。Kit `kit_M1D_NOPATCH5_20261029`（= M1b + 补丁 5 默认关）。

Run `ONCE_20261029_143736`：补丁确认只应用 4/5（`进度 4/5, 本轮新增 [1, 2, 3, 4]`），
建房 14:38:35 —— 但**扫描无效**：句柄虽在 t+22.85 s 拿到，首次读取即 `err=5`，
5 轮覆盖率全为 **0.0%**（ACE 读取窗口问题）。

**M1D-b 重跑（有效）**：Run `ONCE_20261029_144410`，同样 4/5 补丁，
两次建房（14:45:09、14:46:15），扫描 10 轮、**覆盖率 100%**、覆盖建房后约 2.5 分钟：

| 轮次 | my_event_handler | dwroommatchuber | dwroomimp（对照） |
|---|---|---|---|
| #3–#10（含两次建房之后） | 0 | **0** | 1 |

⇒ **nt10 补丁 5（GateB 放行）也不是原因**。

### 当前排除矩阵

| 候选变量 | 试验 | 结果 |
|---|---|---|
| 客户端 UI 路径 | 用户确认三轮都在建房 | ❌ 排除 |
| memberCount | M1 vs A/B | ❌ 排除 |
| createRoom 第三个 u32（18 vs 1） | M1b | ❌ 排除 |
| `dwRoomMessageStartGame` 推送 | M1C | ❌ 排除 |
| nt10 补丁 5（GateB） | M1D-b（有效，覆盖率 100%） | ❌ 排除 |
| 其余大厅/套件差异（21/5 应答内容、102/7 回显、marketplace、playlist resolver、各开关文件） | — | 未测 |

**方法论警告**：五轮实机中已有两轮因 ACE 读取窗口失败而作废（M1D 第一次、更早的一次），
每次结论都必须附读取覆盖率，否则"0 实例"可能是"读不到"。



