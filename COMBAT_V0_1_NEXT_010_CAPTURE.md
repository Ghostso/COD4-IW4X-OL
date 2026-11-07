# COMBAT_V0_1_NEXT_010_CAPTURE.md

> 任务：COMBAT-V0.1-NEXT-010 步骤 1–3 —— 授权后最小插桩（**已实施**）＋ 采集准备
> **当前状态：插桩完成、静态自检全通过；等待用户确认后由用户手动采集。**
> 本次**未修改** `GOLDEN-LOBBY-001`、原 `REF_LOBBY_KIT`、战斗服务器源码；
> **未部署、未提交、未推送**；**未启动/注入/附加/读取客户端进程**。

---

## 1. 修改前检查（步骤 1，全部通过）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 独立副本路径 | `D:\\BaiduNetdiskDownload\\使命召唤OL\\REF_LOBBY_KIT_CAP009` |
| | 不属于 `GOLDEN-LOBBY-001` | ✅ `False` |
| | 不等于原 `REF_LOBBY_KIT` | ✅ `False` |
| | 不属于战斗服源码 `src` | ✅ `False` |
| 2 | 修改前 SHA-256 清单 | ✅ 见 [SHA256 清单](COMBAT_V0_1_NEXT_010_SHA256.txt) |
| 3 | 日志函数默认关闭 | ✅ 开关文件不存在 ⇒ `_cap_on()` 返回 False ⇒ 全部函数立即 return |
| 4 | 采集目标文件不存在 | ✅ `capture-21-5.meta` / `.hex` 均不存在（未覆盖任何历史证据） |

### 1.1 修改前源文件哈希

| 文件 | 字节数 | SHA-256 |
|---|---|---|
| `REF_LOBBY_KIT/lobby_server.py` | 76,410 | `D7EEB4564AF05F4C71FB3391112A8BF592B74F0AA12DEC8F286B927AE046C2CF` |
| `REF_LOBBY_KIT/codol_crypto.py` | 42,853 | `E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607` |
| `REF_LOBBY_KIT/lobby_srv.log` | 134,649 | `B3E105CF9B735EAAEAF8C939009389013B6B89A9DCD351E0A117E72EAAD29FF2` |

> **修改后原文件的哈希仍为上面同值** —— 证明**只改了副本**。

---

## 2. 最小插桩（步骤 2，已实施）

### 2.1 改动规模

| 项 | 值 |
|---|---|
| 改动文件 | **仅 1 个**：副本的 `lobby_server.py` |
| 原始 | 76,410 B（`D7EEB456…`） |
| 插桩后 | `2F300B33436A2CED2004D6C2821A68AFE0A9D9D1215B37C34CF587A69E035235` |
| 字符增量 | **+3,080** |
| 行增量 | **+84** |
| **删除的行** | **0**（`Compare-Object` 实测 `pristine-only = 0`） | 
| **⇒ 纯插入，无任何现有行被改写** | |

### 2.2 插桩位置（5 处锚定插入）

| # | 锚点（唯一） | 插入内容 | 用途 |
|---|---|---|---|
| P1 | `OUTDIR = os.path.dirname(...)` 之后 | `BLOCK_CAPS`（85 行只读采集块） | 定义开关与落盘函数 |
| P2 | `    conn.settimeout(1.0)` 之后 | `_cap_cid = _cap_init(addr)` | **会话标识** |
| P3 | `                    ntasks += 1` 之前 | `_cap_frame(..., "C2S-PLAIN", ...)` | **入站 0x85 明文帧** |
| P4 | `                        conn.sendall(rep)` 之后 | `_cap_frame(..., "S2C-PLAIN", ...)` | ★ **`conn.sendall(rep)` 实际发送的完整 `rep`** |
| P5 | `                            conn.sendall(pf)` 之后 | `_cap_frame(..., "S2C-PUSH", ...)` | 推送信封（**仅当正常流程真的产生**） |

**所有锚点均校验"恰好匹配 1 次"，否则脚本中止且不写文件**（见 §2.5）。

### 2.3 记录的是哪一层（任务要求的明确回答）

| 层级 | 是否记录 | 说明 |
|---|---|---|
| `conn.sendall(rep)` 的**完整 `rep`** | ✅ **记录**（P4，`S2C-PLAIN`） | 任务优先项；就是实际发出的 306 B 帧 |
| 入站 0x85 的**解密后明文帧** | ✅ 记录（P3，`C2S-PLAIN`） | 服务器解密后可得；**不标注为"客户端实收"**，标注为 `C2S-PLAIN` |
| 入站**加密原始字节** | ⚠️ 不单独记录 | 副本已有既存 `lobby_rx.bin`（append 原始 TCP 字节，非本次新增） |
| **解析后对象** | ❌ 不记录 | 对象 ≠ 原始帧；避免与原始字节混淆 |

> ★ **命名纪律**：方向标签用 `S2C-PLAIN` / `C2S-PLAIN` / `S2C-PUSH`，
> 并在 `_cap_frame` 的 docstring 中写明"入站为服务端解密所得"，
> **不把服务端构造的数据冒充为客户端实际收到的原始响应**。

### 2.4 记录内容与安全

每条 `FRAME` 记录（`capture-21-5.meta`，TSV）：

```
时间戳.毫秒  kind  cid  direction  service=  task=  seq=  len=  parsed_ok=  sha256=  note
```

- ✅ 记录：时间戳、方向、会话标识 `cid`、service/task/seq、长度、sha256、**完整 hex**；
- ❌ **不记录**：`SEC_KEY`、`aes_in/aes_out`、`hmac_in/hmac_out`、会话密钥、任何凭据；
- 帧内本身含公开 IV 与密文（协议自有），**不属于敏感凭据**。

**采集范围（`CAPTURE_TARGETS`）**：`(21,5)` 与 `(6,14)` —— 与任务要求一致；
**非目标帧（如 `10/21`）实测被忽略**（见 §2.6）。

### 2.5 幂等与安全保证

| 机制 | 实现 |
|---|---|
| **幂等** | 检测标记 `CAPTURE_TARGETS = frozenset`；已插桩则跳过 |
| **锚点安全** | 每个锚点在写入前 `count()` 校验，`!= 1` 即 **中止且不写文件** |
| **块唯一性** | 写前校验标记出现 1 次 |
| **零行为变更** | 开关关闭时 `_cap_on()` 立即 False ⇒ 不建文件、不改状态 |
| **异常隔离** | `_cap_*` 内部全 `try/except`；异常不得外溢影响消息处理 |

### 2.6 静态自检结果（全通过）

```
=== 1) syntax check (py_compile) ===            exit = 0
=== 2) AST parse ===                             AST OK, top-level nodes = 85
=== 3) switch OFF: capture must NOT be enabled ===
   capture-21-5.enabled exists = False
   capture-21-5.meta exists    = False
   capture-21-5.hex exists     = False
=== 4) diff vs pristine ===
   pristine-only lines = 0 ; copy-only lines = 84
=== 5) OUTDIR/CAPTURE_FLAG 顺序校验 ===
   OUTDIR at 9111  CAPTURE_FLAG at 9578  order OK = True
```

**采集钩子单元测试（`test_capture_hooks.py`，不联网、不启客户端）：**

```
=== A) switch OFF ===   _cap_init -> None ; 未创建任何文件        OK
=== B) switch ON ===
   2026-10-10T21:35:03.912  SESSION-BEGIN  c0001  NA  peer=('127.0.0.1', 50001)
   2026-10-10T21:35:03.912  FRAME  c0001  S2C-PLAIN  service=21  task=5   seq=47  len=306  parsed_ok=True  sha256=ebd41b44…
   2026-10-10T21:35:03.912  FRAME  c0001  C2S-PLAIN  service=6   task=14  seq=48  len=9    parsed_ok=True  sha256=78d88565…
   (service=10/task=21 非目标帧 **未** 被记录)                  OK
ALL CAPTURE-HOOK ASSERTIONS PASSED
```

**⇒ `306` 字节长度、`sha256`、方向标签、会话标识、非目标过滤 全部按预期工作。**

---

## 3. 等待用户确认：采集操作说明（步骤 3）

> ### ⏸ **暂停点：等待用户确认"可以开始"后再由用户手动采集。**
> **Agent 不启动、不注入、不附加、不读取客户端进程。**

### 3.1 独立副本路径

```
D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT_CAP009
```

### 3.2 开关方式

| 动作 | 操作 |
|---|---|
| **启用采集** | 在副本目录创建空文件 `capture-21-5.enabled` |
| **停止采集** | 删除该文件 |

**默认：不存在 ⇒ 采集关闭。**

### 3.3 预期输出文件名（均在副本目录内）

| 文件 | 内容 |
|---|---|
| `capture-21-5.meta` | TSV：时间戳 / kind / cid / 方向 / service / task / seq / len / parsed_ok / sha256 |
| `capture-21-5.hex` | 每帧：`> <cid> <dir> len=<n>` 换行 + 完整 hex |

**两文件均为 append-only；采集前不存在（已确认）。**

### 3.4 建议操作序列（由用户执行）

```powershell
# 1) 进入副本
cd "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT_CAP009"

# 2) 打开采集开关（创建空文件）
New-Item -ItemType File -Path capture-21-5.enabled -Force

# 3) 按既有已授权流程启动大厅（与原套件同法，例如 run_all.py）
#    —— 具体命令由你决定；Agent 不代跑

# 4) 【你手动】在客户端进入一次对局（PvE/剧情均可）

# 5) 关闭采集开关
Remove-Item -Path capture-21-5.enabled

# 6) 确认产出
Get-ChildItem capture-21-5.*
Get-Content capture-21-5.meta | Select-Object -First 20
```

### 3.5 回滚方式（两个选项，任选）

| 方式 | 操作 |
|---|---|
| **最小回滚（保留副本）** | 把副本的 `lobby_server.py` 用原文件覆盖回去：`Copy-Item ..\REF_LOBBY_KIT\lobby_server.py . -Force`（哈希可核对 `D7EEB456…`） |
| **完全回滚** | 直接删除整个 `REF_LOBBY_KIT_CAP009` 目录 |

**⇒ 原 `REF_LOBBY_KIT` 从未被改动，回滚不影响任何历史证据。**

### 3.6 采集后请把下列内容交回给 Agent

1. `capture-21-5.meta` 全文；
2. `capture-21-5.hex` 全文（或至少 `service=21 task=5` 与 `service=6 task=14` 的行）；
3. 副本 `lobby_server.py` 的 SHA-256（`2F300B33…`）；
4. **同一会话的确认信息**（`cid` 相同的若干帧即可）。

---

## 4. 本次的可复核脚本

| 脚本 | 作用 |
|---|---|
| `_combat_next001/apply_capture_patch.py` | **锚定插桩器**（幂等；锚点计数校验；不符即中止不写） |
| `_combat_next001/test_capture_hooks.py` | **采集钩子单元测试**（开关 OFF/ON、目标过滤、长度与 sha256） |

**复现命令：**

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001"

# 复现插桩（对副本；幂等）
python -X utf8 apply_capture_patch.py "..\REF_LOBBY_KIT_CAP009"

# 复现钩子自检（不联网、不启客户端）
python -X utf8 test_capture_hooks.py "..\REF_LOBBY_KIT_CAP009"
```
