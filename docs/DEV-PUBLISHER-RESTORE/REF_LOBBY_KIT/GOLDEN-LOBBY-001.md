# GOLDEN-LOBBY-001 —— 冻结清单（2026-10-07）

> **本文件是"稳定进大厅"的唯一权威复现依据。**
> 冻结含义：以下文件与配置**只读**，后续实验一律在开发副本上进行。
> 不得依赖记忆恢复成功环境。

```
STATUS            = FROZEN
FROZEN_AT         = 2026-10-07
FROZEN_BY_TASK    = CODOL 复活项目 · 下一阶段主任务（P0-1）
SCOPE             = 正式进入 Lobby + KeepAlive 稳定运行
```

---

## 0. 冻结范围说明（重要）

`REF_LOBBY_KIT` 全目录 **26.7 GB**，其中绝大部分是**内存转储**
（`mem_linear\`、`mem_marketplace\`、`mem_sku\` 等），与本阶段复现无关，
且用户明确要求**不要删**。

因此本 Golden **只冻结"运行所需"的那一部分**（下表 1.1），
转储/实验日志**不纳入版本管理**，仅记录路径。

---

## 1. 冻结内容

### 1.1 服务端核心（REF_LOBBY_KIT）

| 文件 | SHA-256（前 16 位） | 字节 |
|---|---|---|
| `lobby_server.py` | `d7eeb4564af05f4c…` | 76,410 |
| `codol_crypto.py` | `e836c63af75dd82e…` | 42,853 |
| `battle_server.py` | `71bb7beb85e51408…` | 69,019 |
| `marketplace_store.py` | `28b4a1be67de06f4…` | 46,226 |
| `fake_auth_tls.py` | `e638e96fe420d66d…` | 10,347 |
| `nt10.py`（注入/补丁/KDF hook） | `05863ebafc7d7bb3…` | 169,491 |
| `run_all.py`（一键启动） | `2aaa8847f112d926…` | 31,507 |
| `battle_selftest.py`（离线自测） | `06b8b5a8b32586cf…` | 20,145 |
| `make_local_ca.ps1`（本地 CA） | `f89e314e717a38a3…` | 6,607 |

> 完整哈希见 `_golden_hashes.json`（同目录，机器可读）。

### 1.2 业务数据（LOCAL SERVER BUSINESS DATA）

| 文件 | 内容 |
|---|---|
| `player-account.json` | UID `16701785630074219790` / `LAtt` / Lv70 / Prestige4 / CP 972,299 / GP 523,619 |
| `marketplace-inventory.json` | 库存 7,620 件 / Priority 37 |
| `marketplace-catalog-merged.json` | 目录 37,834 条 |
| `player_profiles\public.result` | 33,428 B |
| `player_profiles\secure.result` | 32,983 B |
| `publisher_files\mp_playlists_shipRetail_1.0.0.info` | version 796（7 条 playlist） |
| `battle_security_key.txt` | 全 0（代码内兜底 `01×16`） |

### 1.3 开关终态（冻结值）

| 开关 | 冻结值 | 说明 |
|---|---|---|
| `firingrange-session.enabled` | **ON** | 21/5 回靶场 session |
| `firingrange-battle.enabled` | **ON** | 起战斗服 |
| `firingrange-booking-push.enabled` | **OFF**（文件名为 `.OFF_CONFIRMED_CRASH`） | ★ 实测 9/9 断连，必须保持关闭 |
| `playlists-include-pve.on` | ON | 清单含 playlist 10 |
| `ready_push.on` | ON | 11/4 ready 推送 |
| `mirror_predicted.on` | ON | 快照镜像客户端预测态 |
| `marketplace-catalog-merged.on` | ON | 合并目录 |
| `marketplace-catalog-client.on` | ON | 客户端目录 |
| `marketplace-currency-lenient.on` | ON | 货币宽松 |
| `catalog-include-sku-table.on` | ON | 并入 SKU 表 |
| `sku-live.on` / `memlinear.on` / `callsign-scan.on` | ON | 采集线程 |
| `tas_spec.txt` | 空（**不注入 TAS**） | 实测会卡住 |
| `lobby_spec.txt` | `127.0.0.1:3074:CODOL-LOCAL` | — |
| `late_spec.txt` | 关（不改 TenProxy 代码） | — |
| `push_seq_offset.txt` | `1000` | 推送 seq 偏移（当前推送已关） |

### 1.4 内存补丁清单（nt10.py 实装，4 处 + 1 hook）

```
补丁1 AuthGate       @0x00B9A78E  74 -> 75   (JE -> JNE)
补丁2 ClientTicket   @0x00B9A7C5  75 -> EB   (JNE -> JMP)
补丁3 ParseFallback  @0x00B9A7C7  E8 -> E9   (call -> jmp 0x00B9A7F1)
补丁4 LsgNonceCheck  @0x00BA3C1C  85 C0 75 44 -> 85 C0 90 90  (NOP)
KDF hook             @0x00BA0D20  trampoline（派生会话密钥 -> secrets_kdf.txt）
```

### 1.5 客户端环境

| 项 | 值 |
|---|---|
| 沙箱（GAME_ROOT） | `run_codol_001\sandbox_datafix_20260929` |
| 客户端 | `codoMP_client_shipRetail.exe` 7,841,344 B |
| 主 DLL | `codoMP_client_shipRetailBase.dll` 60,327,992 B |
| `dwauth.ini` | `formal-zone-lsg.codol.qq.com 3074` / `formal-zone-auth.codol.qq.com 3074` / `0x03EA` |
| `iips.ini` | `enable_iips=1` / `iips_url="http://10.231.2.181/"` |
| 证书 | 本地 CA 追加进 `cacert.pem`（每次启动重建，SAN = localhost + formal-zone-auth/lsg.codol.qq.com） |

### 1.6 hosts

```
127.0.0.1 formal-zone-auth.codol.qq.com
127.0.0.2 formal-zone-lsg.codol.qq.com
```
（`run_all.py` 用 `# CODOL-LOCAL-BEGIN/END` 包围块管理；
**不劫持** `down.qq.com` / `intldlgs.qq.com` —— 让 ACE/TP3 走真实网络）

### 1.7 依赖 DLL（客户端自带，**未新增**）

```
ace-ats32.dll 1,758,784   ACE-DRV32.dll 6,835,192   VSDDrvDll.dll 11,168,832
PolicyProbe.dll 6,855,224  TCJ.dll 3,158,584        tvsd.dll 11,932,240
TerSafe.dll 8,280,328      TenSLX.dll 2,675,768     TenSp.dll 164,920
BugTrace.dll 1,029,624     TenProxy.dll 167,592     TenRpcs.dll 17,408,000
```
> ⚠️ 这些都是**原版** ACE/TP 文件（见 §4），不是 stub。

---

## 2. 从零复现步骤（唯一权威）

```powershell
# ① 起提权代理（会弹 UAC，必须点"是"）
$py=(Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping     # 期望 ok=true

# ② 清残留（必须，否则单实例互斥导致坏启动）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue"

# ③ 一键跑（起 auth + lobby + battle，改 hosts/dwauth/证书，拉起游戏并注入）
cd "D:\BaiduNetdiskDownload\使命召唤OL"
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 600 --out n10_golden.txt
```

| 项 | 值 |
|---|---|
| **CWD** | `D:\BaiduNetdiskDownload\使命召唤OL` |
| **启动参数** | `--secs 600 --out <name>.txt`（不要加 `--tas`） |
| 服务布局 | auth TLS `127.0.0.1:3074` / lobby `127.0.0.2:3074` / battle UDP `0.0.0.0:28960` |

### 复现成功的判据

```
① lobby_srv.log 出现：=== 大厅连接建立 ===  且 [keys] ★ 试解命中
② 首帧：hmac=OK marker=0x86
③ 出现 <- keepalive
④ 收到 8/1 8/2（档案）、10/21（发行方配置）等
⑤ 全程 hmac=BAD 计数 = 0
```

---

## 3. 成功日志位置（冻结时的基线）

| 日志 | 规模 | 关键指标 |
|---|---|---|
| `REF_LOBBY_KIT\lobby_srv.log` | 134,649 B | 建立 23 / 结束 23 / 异常 0 / keepalive 15 / **hmac=OK 235 / BAD 0** |
| `REF_LOBBY_KIT\auth3074.log` | 9,580 B | TLS 认证 |
| `REF_LOBBY_KIT\battle_srv.log` | 322,463 B | 已监听 28960，`收包=0`（未进对局） |
| `_golden_hashes.json` | — | 核心文件 SHA-256 |

---

## 4. ACE 状态（诚实记录，不粉饰）

```
ACE_REMOVAL = NOT_COMPLETE
```

| 项 | 状态 | 证据 |
|---|---|---|
| ACE 文件 | **仍存在** | 沙箱内 `ace-ats32.dll` / `ACE-DRV32.dll` / `ACE-BASE.sys` / `ACE-GAME.sys` 均在，且是**原版**（尺寸/时间戳与备份一致） |
| ACE 驱动 | **仍安装** | `C:\Windows\System32\drivers\` 有 `ACE-ADVT.sys` `ACE-BASE.sys` `ACE-GAME.sys` |
| ACE 进程 | 当前无 | `Get-Process` 匹配 0 个 |
| `BugTrace.dll` | **仍加载**（实机在跑） | 抓包日志里它的 sendto 调用者 |
| ACE ABI/stub/mock | 有备份但**未使用** | `ace_facade\`、`_ace_backup_20261002\` |
| 客户端 ACE 强依赖 | **仍是**（靠 4 个内存补丁绕过） | 见 §1.4 |
| 本 Golden 是否"完全无 ACE" | ❌ **不是** | 属"**绕过/共存**" |

> 项目纪律：**禁止**关闭/停止/配置/规避 ACE、TenProtect
> （历史实测蓝屏 `0x01010002`）。ACE 彻底移除在**独立分支**进行，
> 不得为当前 Battle 主线破坏本 Golden。

---

## 5. 已知缺口（本 Golden **不包含**）

```
P0  6/14 PvE booking 应答格式 = UNKNOWN      ← 本阶段唯一主线
P1  商城目录页(80/70 等)回空 → 商城空白
P1  首页挑战 #1010 / 公告 #1125
P1  MP 游玩清单条目为空
P2  名片/徽章/称号 拥有与装备（缺 ref↔itemID 映射表）
P2  未映射服务 3/46,48,53 · 9/5,14 · 10/20 · 12/6 · 28/1,4 · 29/10 · 102/1,2,7
```

---

## 6. 纪律（冻结后）

1. **Golden 只读**；所有实验在开发副本（如 `REF_LOBBY_KIT_dev\`）进行。
2. 改任何 §1.1 的文件前，先复制 Golden 到副本。
3. 不得依赖记忆恢复环境 —— 一切以本文件 + `_golden_hashes.json` 为准。
4. 商城协议实验**冻结**，除非 Battle 主线已完成。
5. 已在 Golden 里标为 OFF 的开关（尤其
   `firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH`）**不要打开** ——
   实测 9/9 断连。
