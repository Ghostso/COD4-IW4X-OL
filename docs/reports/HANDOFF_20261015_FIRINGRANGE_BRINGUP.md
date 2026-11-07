# CODOL 3.19 靶场实机 Bring-up —— 交接手册

> 交接时间：2026-10-15 21:57 (Asia/Shanghai)
> 本手册只写**本轮实际验证过**的内容；凡推论标注 `[推断]`，凡未完成标注 `[未完成]`。
> 工作根目录：`D:\BaiduNetdiskDownload\使命召唤OL`
> 用户裁定：**只有此目录内是本项目自有资料；目录外一律仅作参考。**

---

## 0. 一句话现状

客户端能被我们的 C# 战斗服完整握手、下发 gamestate、推进到 stage 6，但**随后卡在 `cls.state = 9 (CA_PRIMED)`**，屏幕显示“等待玩家数据”，约 60 秒后断开。
本轮用**对局态运行时内存转储**从运行时侧确认：**客户端从未解析过我们下发的任何快照**（快照字节仅出现在缓冲区，未进入解析态）。

---

## 1. 环境与启动链（已验证可用）

### 1.1 关键路径

| 角色 | 路径 |
| --- | --- |
| 游戏根 GAME_ROOT | `D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929` |
| 客户端 | `<GAME_ROOT>\codoMP_client_shipRetail.exe` |
| 大厅套件 | `D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\` |
| 提权代理 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py` |
| C# 战斗服 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe` |
| 战斗服配置 | `...\CODOL-Combat-Server-v0.1\config\firingrange_live.cfg` |
| 战斗服日志 | `...\CODOL-Combat-Server-v0.1\logs\firingrange_live.log` |

### 1.2 启动顺序（**必须按此，否则 IIPS 初始化失败**）

```powershell
# ① 提权代理必须真的提权（UAC 弹窗点“是”）。判据：debug_privilege=true
Start-Process -FilePath (Get-Command python).Source -Verb RunAs -WindowStyle Hidden `
  -ArgumentList '-X','utf8','D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py'
python -X utf8 CODOLServer\_mainline\agent_client.py ping    # 期望 debug_privilege: true

# ② 经代理运行一键链
python -X utf8 CODOLServer\_mainline\agent_client.py run python -X utf8 `
  D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py --secs 900 --out n10_test.txt
```

**教训（本轮踩过）**：若代理**未提权**（`debug_privilege:false, debug_err:1300`），`IIPSHostApp.exe` 不会启动，IIPS 完全不初始化，表现为“iips初始化错误/未按固化启动链启动游戏”。判定看 `<GAME_ROOT>\IIPS\TenioLog\` 是否产生新日志。

### 1.3 成功判据（REF_LOBBY_KIT 侧）

- `lobby_srv.log` 出现 `大厅连接建立` + `试解命中`，`hmac=OK` 远超 `hmac=BAD`（本轮 55:0）
- `<GAME_ROOT>\IIPS\TenioLog\` 生成新日志
- `firingrange_live.log` 出现 `GAMESTATE TX seq=1` 与后续 `SNAPSHOT TX`

### 1.4 战斗服由谁拉起（重要陷阱）

`lobby_server.py:1378` **优先启动 C# 战斗服**（若 `CODOLCombatServer.exe` 存在），只有它不存在时才回退 Python 版 `battle_server.py`。
本轮实测：**最近所有实机测试，客户端连的都是 C# 战斗服**，Python 版的“当年进图”能力**在本机从未复现**。

---

## 2. 本轮达成的结论（按证据强度分级）

### 2.1 【运行时实测·硬证据】客户端卡在 CA_PRIMED

从**对局态活内存转储**直读：

```
VA 0x076446B0 = 0x00000009      # cls.state = 9 = CA_PRIMED
```

- 该地址仅以 **VA = RVA** 形式可读（`0x76446B0`）；加 `0x400000` 读到的是无关值。
- 客户端进程存活、持续 20Hz 发 usercmd，战斗服侧 `ack` **恒为 5**（= 最后一个 gamestate 的 seq）。
- 与屏幕“等待玩家数据”一致。

### 2.2 【运行时实测·硬证据】客户端**从未解析**我们的快照

在完整转储（2160 区 / 1.44 GB）中穷举搜索：

| 搜索目标 | 结果 |
| --- | --- |
| 快照明文头（未掩码前 8 字节 + 明文段） | **0 命中** |
| 已发送的 gamestate 掩码包（seq=1/2/5 全包比对） | **0 命中** |
| 快照体特征尾串 `…ff0f05` | **1 命中**，落点紧邻 `scr_game_allowkillcam` 等 **configstring 文本**，周边**无任何 `06 02` DTLS 数据帧头** |

→ [推断，置信高] 该命中位于**消息/配置串缓冲**，非快照解析态；客户端**在解析之前就丢弃/未消费**我们下发的快照。

### 2.3 【日志实测】三轮实机 ack 行为完全一致

| 轮次 | 改动 | ack 结果 |
| --- | --- | --- |
| 基线（未改） | — | 冻结在最后一个 gamestate seq |
| 18:03 轮 | `0x0A → 0x08` | 仍冻结（4→5） |
| 21:16 轮 | `0x0A→0x08` + `220→85` | 仍冻结（5） |

→ **两处单字节改动均已生效（离线验证过线上字节），但都不解决问题。**

---

## 3. 本轮对源码的改动（**未回滚，需你决定去留**）

### 3.1 `src\Engine\ClientLogic.cs`（1 行生效 + 4 行注释）

- 第 852 行：`currentOpts.SnapshotEntryFlag = false;`（原为 `= !s.ClientEntered;`）
- 效果：快照入场帧 flags 由 `0x0A` 改为 `0x08`（已在线上字节 A/B 验证）
- 离线自测：**通过 254 / 失败 0**
- 回滚点：`ClientLogic.cs.bak_before_entryflag_test`（46404 B）

### 3.2 `src\Codol\MotionSnapshot.cs`（1 行生效 + 注释）

- 第 281 行：`w.Bits(85, 8);`（原为 `w.Bits(220, 8);`）
- 理由：本帧实际最高字段索引为 84，`lastChangedField` 应为 85；220 隐含“存在字段 219”，而 219 默认关闭
- 回滚点：`MotionSnapshot.cs.bak_before_lastchanged_test`（18154 B）

### 3.3 `src\SelfTest.cs`

- golden 首帧断言由“逐字节一致”改为“**仅第 11、12 字节不同**（即那 8 bit）”，其余逐字节一致

### 3.4 当前产物指纹

```
CODOLCombatServer.exe  Size=193536  mtime=2026-10-15 18:28:34
SHA256 = 0AD76F2052F09D544D0A778E99C32D78A48405E44D3CF4B02BBB8E133D1958CC
```

### 3.5 REF_LOBBY_KIT 开关改动（为动态抓取）

```
memlinear_after.txt   150 -> 420     # 延迟到“进对局之后”
memlinear_outdir.txt  mem_linear_20261007_134406 -> mem_linear_live_20261015
memlinear.on          保持存在（启用）
```

- **原值备份**：`REF_LOBBY_KIT\_memlinear_switches.bak_20261015\`
- **重要**：`mem_linear_20261007_134406` 是用户要求保留的**基准转储**，本次未覆盖。

---

## 4. 素材适用性（用户明确裁定）

| 素材 | 位置 | 可否作为 3.19 依据 |
| --- | --- | --- |
| O-3 `codoMP_client_shipRetail.exe` | `COD OL\` | ✅ **实际运行目标**，但磁盘上是 .tp3 加壳，不可直接反汇编 |
| 解壳运行时映像 `image_best.bin` | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\` | ✅ SHA256 `17cef6e0…2fd045`，与 048 报告 S-IMG 一致，**代码段完整可反汇编** |
| 官方录像 demo（31 份） | 见 §6 备份 | ✅ 关服前官方下行字节，**唯一客观物证**（但走回放路径，不经过网络入场门） |
| ol-mod / CODOL-AlphaBuild（含 C 源码） | `_e1_regression\`、`EARLY_SERVER_ANALYSIS\` | ⚠️ **仅学原理** |
| 2697 服务端 `codol_dedrun.exe` | `CODOL_2697_Launcher\` | ⚠️ **仅学原理**（版本跨度过大，多次重构级变革） |
| COD4x / IW4x | `DEV-BOOKING\_lineage021\` | ⚠️ 仅参照（血缘更近旧版，非 3.19） |

---

## 5. 动态抓取能力（**本轮才真正打通，务必沿用**）

### 5.1 为什么外部读取一定失败

项目自述（`REF_LOBBY_KIT\nt10.py:1584`、`:2141`）：

> **必须用早期句柄**：客户端被 ACE/TP3 保护，**后开的句柄 `VirtualQueryEx`/`ReadProcessMemory` 会被拒(err=5)**；早期句柄实测到 t≈6s 仍可读写。

本轮实测吻合：游戏完整运行后，外部 `OpenProcess` 能成功、`VirtualQueryEx` 也成功，但 **`ReadProcessMemory` err=5**（连 `0x400000` 的 MZ 都读不到）；连 `0x1F0FFF` 全权限句柄也被拒。

### 5.2 正确做法（已跑通）

```
1) 写 REF_LOBBY_KIT\memlinear.on            (空文件，启用)
2) 写 memlinear_after.txt = <延迟秒>        (# 建议 400~600，覆盖“进对局”时刻)
3) 写 memlinear_outdir.txt = <新目录名>     (# 绝不要指向既有 mem_linear 基准)
4) 正常走 §1.2 启动链
   -> nt10 在延迟到点时用【早期句柄】做全片线性转储
```

**本轮成果**：`REF_LOBBY_KIT\mem_linear_live_20261015\` = **2160 个区 / 1.44 GB**，切片命名 `r_<VA8>_<SIZE8>.bin`（**基址即 VA**）。

### 5.3 从转储定位值的正确口径

```
切片名 r_XXXXXXXX_YYYYYYYY.bin 中的 XXXXXXXX 就是该块的【绝对 VA】
cls.state 的 VA 就是 0x76446B0（不加任何基址）
exe 映像头在 0x400000（MZ 可见），代码段在 0x401000 起
```

---

## 6. 本轮新增产物清单（可复核）

| 产物 | 位置 | 说明 |
| --- | --- | --- |
| demo 黄金备份 | `D:\...\使命召唤OL\DEMO_GOLDEN_BACKUP_20261015\` | 31 文件 / 79,711,672 B + `DEMO_MANIFEST.txt` |
| demo 跨盘备份 | `E:\DEMO_GOLDEN_BACKUP_20261015\` | 同上（跨物理盘冗余） |
| demo 聚合指纹 | 见 manifest | `AA902F0C87C16F0DA92C14B357E1F6949D105B9535DF227727C76CFB338BAF43` |
| 对局态内存转储 | `REF_LOBBY_KIT\mem_linear_live_20261015\` | 2160 区 / 1.44 GB（本项目自有、对局态） |
| 逆向工作目录 | `D:\...\使命召唤OL\_rev_analysis\` | 本轮脚本与中间件（`fstarts.json`、`image_rebuilt.bin`、`live_state_sampler.py` 等） |
| 开关原值备份 | `REF_LOBBY_KIT\_memlinear_switches.bak_20261015\` | §3.5 的回滚点 |

---

## 7. 未完成 / 下一步（按优先级）

### P0-A　从转储反推 `cls.state` 的写入者

- 已有：`cls.state` 的 VA `0x76446B0`、其对局态值 = 9。
- 静态已穷举：**整个 .text 段对 `0x76446B0` 只有 5 处直接写，值 = 3/7/4/0/7，没有一处写 10**。
- 还发现一处**数组形式**写：`mov dword [eax + 0x76446B0], 0`（`eax = idx<<5`）—— 说明可能不是单一全局。
- [未完成] 在转储里找 `0x76446B0` 的**引用**，确定客户端期望什么条件才从 9 跃迁到 10。

### P0-B　定位顶层消息分派器（0/1/3/6）

- 046 注解记录：客户端 opcode 为 `0 snapshot / 1 reliable / 3 gamestate / 6 EOF`。
- **我们 C# 用的是 `Eof = 5`**（来自 `sv_gamestate_mp.hpp`）—— 存在**潜在冲突，尚未裁决**。
- 已找到：`0x214C00` 处的跳转表分派器，但管辖范围是 `0x64..0x78`（ASCII `d`..`x`），是**文本命令分派**，不是网络消息分派。
- [未完成] 静态扫 `E8` 只能覆盖直接调用；**间接调用（函数指针/vtable）扫不到**。转储里有 **92,307 个候选指针表**，可据此反推。

### P1　补全快照的五个缺失段

046 注解指出 `CL_ParseSnapshot` 的段序为：

```
playerstate -> packet sound commands(44B 记录环) -> packet clients
            -> packet entities -> client infos -> glass changes
```

- **我们的快照只有 playerstate + 常数尾巴**，上述五段**全部缺失**。
- 注解还点明：objectives 段必须用 `indexBits=1`（一元零终止），**复用主表 4-bit gap 会让整帧失效**。

---

## 8. 纪律红线（务必遵守）

- **不绕过 / 不停用 / 不配置 ACE、TenProtect**（历史实测蓝屏 `0x01010002`）。
- **允许**：`ReadProcessMemory` / 早期句柄只读转储 / 静态反汇编。
- **禁止**：Frida 注入、改客户端 `.text`、对游戏/平台进程下断点（项目文档内部对“调试器”一条存在**冲突记录**，见 `REPRODUCTION-BASELINE-LOBBY-001.md` §7.4；**动用前请与用户确认**）。
- 分析样本一律**只读**；不修改 `COD OL\` 原件。

---

## 9. 当前机器状态（交接时 21:57）

**仍在运行的进程**：

```
9476   CODOLCombatServer        21:16:50   (UDP 28960)
3204   python                  21:16:50   (run_all 链条)
17800  python                  21:16:49   (run_all 链条)
18296  python                  18:03:21   (提权代理 elevated_agent, debug_privilege=true)
```

**注意**：客户端 `codoMP_client_shipRetail.exe` 在本手册写作时**已不在进程表**（对局超时后退出或已关）。
若下一轮要抓动态，需按 §1.2 重新拉起并使用**早期句柄**（§5）。

**磁盘余量**：C 92.5 GB / D 63.9 GB / E 311.2 GB（每次全片转储约 1.4~42 GB，注意预算）
