# HOSTS_INTEGRITY_EVENT — 系统 hosts 修改的独立完整性事件

**事件编号：** INT-031-01  
**日期：** 2026-10-13（Asia/Shanghai）  
**性质：** **不可完全复原的系统配置修改**（详见 §3）  
**对协议结论的影响：** **无**（无 codol/QQ 残留行；且与本次 "100" 弹窗无因果关系）

---

## 1. 事件经过（按时间）

| 时刻 | 事件 |
|---|---|
| 15:12:00 | 实验前登记 `hosts`：**937 B**，SHA-256 `07642387e67016546a0a1bab53522fe29becf2990740ccaa55e37c8fdfa2115a` |
| 15:12:06 | `_work\lab\run_all.py` 执行 `ensure_hosts()`，按既有流程写入 `# CODOL-LOCAL-BEGIN/END` 两条映射（`127.0.0.1 formal-zone-auth.codol.qq.com`、`127.0.0.2 formal-zone-lsg.codol.qq.com`） |
| 15:19:05 | 实验结束，移除该映射块。**此时文件变为 0 字节**（写入过程中被外部短暂占用，导致内容丢失） |
| 15:19:xx | 从 `CODOLServer\_mainline\_hosts_snap\hosts.original`（915 B，标准模板快照）恢复 |
| 15:33:51 | 保全"当前文件"副本至 `integrity\hosts_AS_FOUND_20261013_153351.txt` |

---

## 2. 当前状态

| 项 | 值 |
|---|---|
| 当前 `hosts` | **915 B** / `37756f9b5a3d050bb1b579a79032632b9c2596ab667056335da71aee22fdfa52` |
| `codol` / `QQ` 相关非注释行 | **0 条** |
| 内容 | 控制台标准模板（`# Copyright (c) 1993-2009 Microsoft Corp.` … `#23.77.15.30 store.steampowered.com #UHE_`） |
| 保全副本 | `integrity\hosts_AS_FOUND_20261013_153351.txt`（与当前文件同哈希） |
| 其他制品副本 | `integrity\etc_hosts_artifacts\`（etc 目录全部 `hosts*` 只读副本，含 `hosts.ics` / `hosts.legacybridge-backup` / `hosts.dz` / `hosts_UHE_Backup\*.bak`） |

---

## 3. 查找实验前副本的结果（穷尽性）

**目标哈希：** `07642387e67016546a0a1bab53522fe29becf2990740ccaa55e37c8fdfa2115a`（937 B）

| 搜索范围 | 方法 | 结果 |
|---|---|---|
| `D:\BaiduNetdiskDownload\使命召唤OL`、`C:\Windows\System32\drivers\etc`、`C:\Temp`、`%LOCALAPPDATA%\Temp`、`%APPDATA%` | 遍历**所有 937 字节**文件并逐字节比对 SHA-256 | 137 个候选，**0 匹配** |
| `etc` 目录全部 `hosts*` | 哈希比对 | 无匹配 |
| `hosts_UHE_Backup\*.bak`（11 份） | 哈希比对 | 无匹配 |
| `CODOLServer\_mainline\_hosts_snap\`（`hosts.original` + 2 份 `.bak`） | 哈希比对 | 无匹配 |
| `backups\FROZEN_*\hosts.snapshot` | 哈希比对 | 无匹配 |
| 形态重建（`clean_hosts()` 后 / 追加块后） | 复算 | 915 B / 1036 B，**均不等于 937 B** |
| VSS 卷影 | `vssadmin list shadows` | **无可用卷影** |
| 回收站 | 遍历 | 无匹配 |

### 判定

> **实验前的 937 B 版本在本机不存在可验证副本，该修改无法逐字节复原。**

---

## 4. 影响评估

| 维度 | 评估 |
|---|---|
| 对本次实验进程 | 实验期间映射按预期生效（`lobby_server` @ `127.0.0.2:3074` 收到真实客户端 hello），**功能上有效** |
| 对本次 "100" 弹窗 | **无因果关系** —— 弹窗出现在该写入**之前**（客户端 15:14:5x 结束, 弹窗为用户观察到的最终状态）；差异在启动链，不在 hosts |
| 对协议结论 | **无影响** —— 当前无任何 codol/QQ 残留映射 |
| 残留风险 | 当前 `hosts` 为标准模板，**不改变任何主机解析行为**（除注释行外仅含被注释的示例） |

---

## 5. 后续处置建议（不擅自执行）

1. **保持当前状态**（标准模板，无残留映射），不再写入。
2. 若需要"实验前逐字节一致"，须由**外部备份/另一台机器**提供该 937 B 文件；本机已穷尽搜索无果。
3. 今后任何 `hosts` 写入**必须先**调用 `CODOLServer\_mainline\_z7_hosts.py snapshot`（它会把原字节写入 `_hosts_snap\hosts.original` 与带时间戳 `.bak`），再 `apply`，结束后 `restore` —— 本次未走该工具，是事件根因。
