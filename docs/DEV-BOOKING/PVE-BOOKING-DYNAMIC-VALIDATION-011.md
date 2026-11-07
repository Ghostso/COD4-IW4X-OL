# PVE-BOOKING-DYNAMIC-VALIDATION-011
# senderId=SessionId 假设的受控动态验证（本次未能执行）

> 2026-10-08 执行。性质：受控动态验证。结果：**被环境阻断（提权代理未就绪）**。

---

## 1. 本阶段性质与目标

验证唯一假设：
```
PvE mmbook response 的 senderId = findSessions 的 SessionId
= 客户端 reservation item +0x168/+0x16C = 0x632680 的 A/B 关联键
```

第一成功信号 = `battle_srv.log 出现 RX #1`（客户端 UDP → 127.0.0.1:28960）。

---

## 2. 已应用的修复（承 010，可回滚）

```
改前: cc.instant_push_body(1, "localhost", accepted)
改后: cc.instant_push_body(SESSION_ID, "localhost", accepted)
备份: lobby_server.py.bak_010_20261008_145002
SESSION_ID = 0x1122334455667788（同文件 line 458）
```

已语法校验通过。**本阶段未再修改任何其它协议字段。**

---

## 3. Test 0：环境基线（★ 阻断点）

| 项 | 状态 |
|---|---|
| DEV run_all.py / lobby_server.py / battle_server.py | 存在（DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT）|
| 游戏客户端 codoMP_client_shipRetail.exe | 存在（sandbox_datafix_20260929，7.8MB）|
| GAME_IP / GAME_PORT | 127.0.0.1 / 28960 |
| Battle UDP listener | 待启动（battle_server.py 绑 0.0.0.0:28960/UDP）|
| **提权代理 elevated_agent.py** | **未运行** |
| logs\elevated_agent.json | **不存在** |
| agent_client.py ping | **连接失败（代理未就绪）** |

**尝试启动提权代理**（`Start-Process -Verb RunAs -WindowStyle Hidden elevated_agent.py`）：
两次等待共 ~13s，`logs\elevated_agent.json` 仍未生成 → **UAC 未被批准 / 代理未起来**。

```
ENVIRONMENT_BLOCKER = CONFIRMED（提权代理需 UAC 批准，未获批，无法注入 ACE 客户端）
```

游戏客户端受 ACE/TenProtect 保护，必须经提权代理注入（Golden 纪律禁止绕过 ACE），
代理不起来就无法启动客户端做受控验证。

---

## 4. Test 1：SessionId 基线

本轮未启动 findSessions，无法记录**本轮实际** SessionId。

静态已知值：
```
SESSION_ID（服务器源码）= 0x1122334455667788
```

```
SESSION_ID = 0x1122334455667788（源码值；本轮运行值未观测）
reservation item +0x168/+0x16C = 未观测
```

---

## 5. Test 2：Server response

未运行，未记录 wire senderId。

```
WIRE_SENDER_ID = 未观测（修复后应为 SESSION_ID）
SENDERID_SESSIONID_MATCH = NOT_OBSERVED
```

---

## 6. Test 3：客户端 accepted correlation

未运行。无 runtime trace（不做 patch/hook 观测）。

```
AB_CORRELATION = NOT_OBSERVED
ACCEPTED_BRANCH_EXECUTED = UNKNOWN
```

---

## 7. Test 4：Battle UDP 首包

未运行。battle_srv.log 未产生新的 RX。

```
CLIENT_UDP_28960_SEEN = NOT_TESTED
```

---

## 8. 结果分支判定

当前不落入 A/B/C 任一分支，而是「**测试未执行**」——被提权代理（UAC）阻断。

一旦代理就绪，按下述顺序执行，并严格按 A/B/C 分支判定：
- A：出现 RX #1 → 停止 booking 修改，转 DTLS（PVE-BATTLE-DTLS-012）。
- B：仍 0 收包 → 先核对 senderId endian / A/B 拆半序，不改多变量。
- C：accepted 执行但仍 0 收包 → 停止 response 实验，转客户端 trigger（CLIENT-BOOKING-BATTLE-TRIGGER-012）。

---

## 9. 复现 / 执行步骤（供 UAC 获批后使用）

```powershell
# 1) 启动提权代理（需 UAC 批准）
cmd /c run_codol_001\run_elevated_agent_admin.cmd
#   等待 logs\elevated_agent.json 出现

# 2) 清场
Stop-Process -Name codoMP_client_shipRetail -Force -EA SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }

# 3) 归档旧 battle 日志，确保 RX=0 基线
# 4) 跑一轮（agent_client 提权）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\run_all.py" --secs 600 --out pve_booking_011.txt

# 5) 观察 battle_srv.log 是否出现 RX #1
Select-String 'DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\battle_srv.log' -Pattern 'RX|收包|NAT|DTLS'
```

关键观察点（按 Test 1~4）：
- 本轮真实 SessionId（findSessions 下发）
- wire senderId 是否 = SessionId（≠1）
- battle_srv.log `RX #1` 首包（源端口/长度/时间戳/首字节分类）

---

## 10. 证据记录

```
SessionId                 = 0x1122334455667788（源码；运行值未观测）
reservation item +0x168   = 未观测
reservation item +0x16C   = 未观测
wire senderId             = 未观测
wire receiverId           = 未观测
service / type / seq      = 未观测
message                   = "mmbook accepted\0"（源码）
client accepted result    = 未观测
Battle UDP RX count       = 0（未运行）
Battle UDP first packet   = 无
```

---

## 11. 最终状态

```ini
SESSION_ID               = 0x1122334455667788
WIRE_SENDER_ID           = 未观测
SENDERID_SESSIONID_MATCH = NOT_OBSERVED
AB_CORRELATION           = NOT_OBSERVED
ACCEPTED_BRANCH_EXECUTED = UNKNOWN
CLIENT_UDP_28960_SEEN    = NOT_TESTED
BATTLE_DTLS_HANDSHAKE    = NOT_TESTED
PVE_SESSION_CREATED      = NOT_TESTED
MAP_ENTRY                = NOT_TESTED
```

---

## 12. 结论与下一步

本阶段**未能执行**动态验证，原因是提权代理（elevated_agent.py）需 UAC 批准、
当前未就绪；游戏客户端受 ACE 保护，必须经该代理注入（Golden 纪律禁止绕过 ACE），
故无法在无代理的情况下做受控验证。

**未因失败而叠加任何修改**（senderId 修复保持唯一变量，可随时回滚）。

下一步二选一：
1. 用户批准 UAC 使提权代理就绪 → 我继续执行 §9 的 Test 1~4，观察 RX #1；
2. 若代理仍无法就绪，则静态升级 SENDERID_AB_MAPPING（dispatcher 的
   `[ebp+8]/[ebp+0xc] ← envelope.senderId low/high` 帧层映射）以在动态前提高置信度。
```
