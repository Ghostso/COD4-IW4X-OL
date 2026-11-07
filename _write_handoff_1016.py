# -*- coding: utf-8 -*-
DOC = r"D:\BaiduNetdiskDownload\使命召唤OL\HANDOFF_20261016_CONSUMER_CHAIN.md"
TXT = """# CODOL 3.19 靶场 Bring-up —— 消费链交接日志

> 交接时间：2026-10-16 01:54 (Asia/Shanghai)
> 工作根目录：`D:\\BaiduNetdiskDownload\\使命召唤OL`
> 用户裁定：**只有此目录内是本项目自有资料；目录外一律仅作参考。**
> 方法纪律：只读转储 + 定点采样 + 静态反汇编。未注入客户端、未断点、
> 未改客户端 `.text`、未触碰/绕过 ACE、TenProtect。

---

## 0. 一句话现状

客户端**能收到**我方快照、**能读出** seq、**能通过**收包链前置各门、**能进入**快照解析器 `0x471E90`，
但**在解析器内部失败**，随后还原 `seedB`，`cls.state` 停在 **9（CA_PRIMED）**，屏幕"等待玩家数据"。

**卡点已从"传输/掩码/长度层"收窄到"解析器内部字段语义"。**

---

## 1. 本轮（10-15 夜 ~ 10-16 凌晨）新增的确证结论

### 1.1 客户端确实读到了我方快照的 seq —— **硬证据**

`seedB`（`codec+0x80148`）会短暂等于**我方刚发出的 seq**，随后被还原：

| 轮次 | 采样 | 命中 |
| --- | --- | --- |
| `chain_timeline`（5ms） | 12 次瞬态 | **12/12** 命中服务端 seq，Δ 在 ±30 内 |
| `lenscan`（5ms） | 28+ 次瞬态 | 与 `m0C` 完全同步 |

代码依据（`image_best.bin` 实测）：
- `0x5C23D8`：`seedB := payload[0..3]`（报文前 4 字节 = 我方 seq）
- `0x5C2447`：**仅在"受理失败"时**把 `seedB` 还原成旧值

→ 瞬态出现 == "读到了但没受理"。**这推翻了早期"客户端没收到快照"的结论。**

### 1.2 我方头部四字段完全正确 —— 离线复算

按判官解码器 `0x470A60` 解码我方**本机实际发送**的字节：

| 字段 | 值 | 判定 |
| --- | --- | --- |
| opcode | `0x00` | ✅ snapshot |
| serverTime | `1000` | ✅ |
| deltaNum | `0x00` | ✅ |
| snapFlags | `0x08` | ✅ |

对照（**旧**掩码含 `ClientReliableCommand` 演化项）：opcode = `0x73` → 必被丢弃。
→ **掩码修复必要且正确**（已合入，`--selftest` 263 项全绿）。

### 1.3 已通过的前置门

`0x5C2260` 收包链：
```
门1 0x5C22B5 size>=4
门2 0x5C22BD OOB 判定
门3 0x5C22FC cls.state>=7
门4 0x5C2380 call 0x674EB0   (24B 指纹块比对)
门5 0x5C23A0 call 0x674740   (读4B+校验)
门6 0x5C2405 块索引窗口
解码 0x5C242B call 0x470A60
分派 0x5C2434 call 0x473A50
结算 0x5C243C cmp [msg],0 -> 失败则 0x5C2447 还原 seedB
```
因失败走 `0x5C2447`（还原）而**不是**门6失败的 `0x5C2413`（不还原）
→ **门4/门5/门6 全部通过**。

### 1.4 判官 msg_t 的完整布局（代码级确证，来自 `0x473A50` 初始化序列）

| 偏移 | 语义 | 写入点 |
| --- | --- | --- |
| `+0x00` | 读错误标志 | memset |
| `+0x08` | 缓冲指针 | `0x473AAB` → `ebp-0x2000C` |
| `+0x10` | **容量** | `0x473AB1` = `0x20000` |
| `+0x14` | **有效长度** | `0x473B4F` = `payload[8:]` 长度 |
| `+0x18` | 段偏移 | `0x473AC7` = 0 |
| `+0x1C` | **读游标** | 分派循环 `0x473BA3`，起 1 |
| `+0x20` | 位位置 | memset |

判官实际看到：`payload[8:]` = **137 字节**（我方 payload = seq(4)+state(141)）。

### 1.5 parser 的读取序列（`0x471E90`）

```
0x47210A  eax = [esi+0x1C]              ; cursor
0x472110  edx = [esi+0x18] + [esi+0x14] ; 段上限
0x472116  edi = eax + 4
0x47211F  cmp edi, edx ; 0x472121 jg -> 0x47214B (越界, 置错误位)
0x47212C  MSG_ReadData(dst,4)           ; ① serverTime
0x4721AA  test ecx,ecx ; 0x4721AC jne    ; ② deltaNum
0x4721B7  [读1B失败点]
0x4721E1  [读1B]                        ; ③ snapFlags (仅当 deltaNum==0)
0x472209  [读1B失败点]
0x472215  and ecx,8
0x472221  mov [0xC89E04C], 0            ; ★清零
```
**注意：②③不是循环**（无跳回），各只执行一次。

6 处 `[esi]=1`（置错误位）：
| 位置 | 类别 | 判据 |
| --- | --- | --- |
| `0x47214B` | 读4B越界 | `cursor+4 > [+0x18]+[+0x14]` |
| `0x4721B7` | 读1B越界 | 游标越过段边界 |
| `0x472209` | 读1B越界 | 同上（第二段） |
| `0x47224B` | 基线拒绝 | `[0xC89E010]&8==0` 且 flag bit3!=0 |
| `0x4722CB` | 记录拒绝 | `[edi+0x3B7C]==0` 或 `[edi+0x3B88]!=eax` |
| `0x47232E` | 时间窗拒绝 | `(client+0x3C2C - rec+0x3BA8) > (client+0xA8E0-800)` |

---

## 2. 已排除的方向（不要再走）

| 方向 | 排除依据 |
| --- | --- |
| ❌ 掩码算法 | 已修；复算证明旧掩码 opcode=0x73 |
| ❌ "客户端没收到快照" | `seedB` 瞬态 = 我方 seq（12/12） |
| ❌ 收包链门1-门6 | 失败走 `0x5C2447`（非门6路径） |
| ❌ 单纯加长报文体 | ②实验：141B→541B 无任何变化（**注意口径见 §4**） |
| ❌ 时间窗拒绝（`0x47232E`） | 5 份转储实算：判据 0 vs 24800，**不触发** |
| ❌ 记录拒绝（`0x4722CB`） | `deltaNum==0` → 不走该分支 |
| ❌ 基线拒绝（`0x47224B`） | `[0xC89E010]&8` 实测=0，且我方 flag=0x08 |

---

## 3. 本轮源码改动（保留状态）

| 文件 | 改动 | 回滚点 | 建议 |
| --- | --- | --- | --- |
| `src\\Engine\\ClientLogic.cs` | 快照掩码与 gamestate 对齐（删 cmd 演化项） | `.bak_before_maskfix_20261016` | **保留**（已证必要） |
| `src\\SelfTest.cs` | 新增 5b 节"判官解码一致性"（6 断言） | `.bak_before_maskfix_20261016` | 保留 |
| `src\\Engine\\ServerConfig.cs` | 新增 `snap_pad*` 长度扫描开关（默认关） | — | 可保留（默认关） |
| `config\\firingrange_live.cfg` | **当前含 `snap_pad_step=32`（实验残留）** | `.bak_before_lenscan` | ⚠️ **需还原** |

构建产物：
```
CODOLCombatServer.exe  size=196608
sha256 = 0BB62767958A8D2E80339BA2EC1B1DA96C1AAE2CAFFF226A0FD59F813B6D851E
source_sha256 = f1560348b43d6f0976775c038dc4494d07ed699dc1b4fc02d5025fbc42685198
--selftest: 263 项通过 / 0 失败
```

---

## 4. 我（本轮 agent）犯过的错误 —— 务必不要重复

1. **对象字段混用**：两次把 `codec+0x109250`（**端点描述符**，含 `127.0.0.1`/`28960`）
   当作 msg_t 来推算。真正的 msg_t 布局见 §1.4（由 `0x473A50` 初始化序列确证），
   **且收包链的 msg_t 在栈上**（调用者 `0x4F8D70` 内 `ebp-0x200e8`），转储抓不到。

2. **②实验结论夸大**：`LENSCAN` 只往**尾部追加零字节**。
   若错在头部/第二段语义，追加零字节本就不可能奏效。
   → 该实验**只能**证明"单纯加长无用"，**不能**证明"长度没问题"。**已降级为弱结论。**

3. **把工作流做成"卡一步猜一步"**（用户明确批评）：
   多次"读汇编→下结论→被实测推翻"。**正确顺序应是：先设计可证伪判据，再动手。**

---

## 5. 当前未解矛盾（下一轮的首要问题）

`0x472221` 会在 `snapFlags&8` 成立时清零 `[0xC89E04C]`。
我方 `snapFlags=0x08` → 应触发清零。

**但实测 5 份转储（跨 7 分钟）`[0xC89E04C]` 恒为 `0x12`（18）。**

两者不能同时成立。候选解释（**均未证实**）：
| # | 可能 | 证伪方法 |
| --- | --- | --- |
| A | parser 未执行到 `0x472215` | 读实时游标 |
| B | `0x470F39` 每帧加回，18 是净差 | 查 `0x470DC0` 调用频率 |
| C | 解码后 snapFlags ≠ 0x08 | 已排除（复算=0x08） |
| D | `[0xC89E04C]` 语义与我的理解不同 | 读 `0x470DC0` 上下文 |

**建议的判定实验（下一次上机，只读）**：
把采样器加两个字段 `[0xC89E04C]`、`[0xC89E010]`（都是全局，随时可读），5ms 采样 60s：
- 若 `[0xC89E04C]` **周期性归零** → parser 确实到达（A 否，B/D 待查）
- 若**单调不动** → parser 从未到达，卡点在头部三处读越界

**判据是二值的，不依赖任何解读。**

---

## 6. 素材与地址口径（沿用）

| 项 | 值 |
| --- | --- |
| O-3 权威原件 | `COD OL\\codoMP_client_shipRetail.exe`，SHA256 `36997674…2B537`（**本轮复核未变**） |
| O-4 解壳映像 | `CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin` |
| 地址约定 | `file_offset == RVA`，`VA = RVA + 0x400000` |
| 关键 VA | `cls.state = 0x76446B0`；`client = [0x76638F4]^0x6891D1C7`；`codec = [0x331C0C8]^0xD362501F` |
| 已知差异 | 活内存 vs image 在 `0x4723D9` 有 **2 字节**差异（`54 56`→`65 51`），该区段反汇编须谨慎 |

---

## 7. 本轮新增产物（全部只读）

| 产物 | 位置 |
| --- | --- |
| 消费链确证清单 | `CONSUMER_CHAIN_FINDINGS_20261016.md` |
| 入场转储结论 | `ENTRY_DUMP_20261016_FINDINGS.md`（前一轮） |
| **5ms 全字段采样** | `REF_LOBBY_KIT\\chain_timeline.jsonl`（32 MB） |
| 采样离线分析 | `REF_LOBBY_KIT\\chain_analysis_20261016.txt` |
| 定点转储 ×15 | `mem_linear_{readonly,chain,lenscan}_20261016_p0{0..4}_*` |
| 分析脚本 | `_rev_analysis\\p0a_clsstate\\*.py`（全部只读） |

---

## 8. 动态抓取链（务必沿用）

```powershell
# ① 提权代理（UAC 点"是"，判据 debug_privilege:true）
Start-Process -FilePath (Get-Command python).Source -Verb RunAs -WindowStyle Hidden `
  -ArgumentList '-X','utf8','D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\elevated_agent.py'
python -X utf8 CODOLServer\\_mainline\\agent_client.py ping

# ② 一键链
python -X utf8 CODOLServer\\_mainline\\agent_client.py run python -X utf8 `
  D:\\BaiduNetdiskDownload\\使命召唤OL\\REF_LOBBY_KIT\\run_all.py --secs 500 --out n10_xxx.txt
```

`REF_LOBBY_KIT` 开关现状：
```
memlinear.on                  = 启用
memlinear_trigger.on          = 启用（触发式转储，优先级高于延迟式）
memlinear_trigger_offsets.txt = 0,5,10,20,40
memlinear_after.txt           = 420（已不生效，触发式优先）
memlinear_outdir.txt          = mem_linear_lenscan_20261016   ← 下轮请改成新目录
clsstate-sample.on            = 启用
clsstate-sample_secs.txt      = 600
```

**坑**：`run_all` 失败会自动重试（`_a2`/`_a3`…），每轮重写约 9 GB。
**D 盘当前仅剩 28 GB**，跑前务必确认。

---

## 9. 环境状态（交接时 01:54）

```
18296 python (elevated_agent, debug_privilege=true)
20492 python (run_all 链)
3968  python (run_all 链)
19316 CODOLCombatServer (UDP 28960，无客户端连接)
客户端 codoMP_client_shipRetail 已自行退出
```

磁盘：C 88.1 GB / **D 28.0 GB** / E 311.2 GB

---

## 10. 下一步优先级

1. **还原 `firingrange_live.cfg`**（去掉 `snap_pad_step`，否则下轮快照会被无意义加长）
2. **做 §5 的二值判定实验**（加采 `[0xC89E04C]`/`[0xC89E010]`）
3. 依据结果二选一：
   - 若 parser 从未到达 → 解头部三处读越界的**实际边界来源**（msg_t 在栈上，需设计可抓取方案）
   - 若 parser 到达过 → 转向"解析器读取的字段序列 vs 我方字节"的逐字段比对
4. **禁止**再用"最近的 `55 8B EC`"当函数起点（MSVC `/Oy`，该启发式会造出假函数）
"""
open(DOC,"w",encoding="utf-8").write(TXT)
print("wrote",DOC,len(TXT.encode("utf-8")),"bytes")
