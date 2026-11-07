# CODOL 固化启动链恢复记录（2026-10-20）

## 结果

标准固化链已完成单次实启并进入大厅。

验证运行：`run_codol_001\runs\ONCE_20261020_003753`

- 外层返回码：`0`
- 客户端启动次数：`1`
- 客户端退出：`rc=0 t=50.0`
- Auth：成功
- 大厅：连接成功
- HMAC：59 条通过，0 条失败
- Publisher：10 个文件成功下发
- `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`：0 次
- 固化核心：`verify_frozen_chain.py` 返回 `{"ok": true, "failures": []}`

## 已确认的故障链

### 1. IIPS

正确组合：

```text
run_codol_001\sandbox_ifs1_20260923\iips.ini
enable_iips=1
```

启动必须经过已提权代理：

```text
CODOLServer\_mainline\elevated_agent.py
```

判据是新生成 `IIPS\TenioLog\*.log`，并出现 `IIPSHostApp.exe`。

### 2. Publisher 文件

先在 `ONCE_20261020_002345` 实测得到错误：

```text
EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
```

原因是一次性运行 kit 只复制了核心脚本，没有复制：

```text
publisher_files\
player_profiles\
user_files\
```

补齐后，客户端请求的 10 个 `.info`、`the.json`、`public.result`、
`secure.result` 全部成功下发，错误消失。

### 3. 控制超时

提权代理中的 `run_all.py` 正常运行时间超过 10 秒，而外层曾只等待 10 秒，
因此错误显示为：

```text
elevated launch failed: timed out
```

控制连接超时现与 `--seconds` 绑定。

## 固化入口

入口：

```text
run_codol_001\run_frozen_chain_once.py
```

入口会：

1. 校验 `REF_LOBBY_KIT` 启动核心哈希。
2. 创建独立 `ONCE_*` 运行目录。
3. 复制 `publisher_files`、`player_profiles`、`user_files`、
   `mkt_assets`、`sku_arrays` 到运行 kit。
4. 写入 `source_manifest.json`、`data_manifest.json`、`preflight.json`。
5. 通过提权代理执行固化启动器。
6. 将 `nt10.py` 的一次性副本改为单次启动。
7. 写入 postflight 与运行后核心校验结果。

## 单次启动

已加入一次性令牌：

```text
run_codol_001\runs\.frozen_launch_used
```

令牌存在时，入口在创建运行目录和启动客户端之前拒绝执行。
恢复下一轮实验必须显式重置令牌，不能自动重试。

## 保护边界

`run_all.py` 与 `nt10.py` 当前 ACL：

```text
SYSTEM                 FullControl
BUILTIN\Administrators FullControl
BUILTIN\Users          ReadAndExecute
```

普通权限的写回测试已实测被拒绝，两个文件哈希保持不变。

这可阻止普通项目或普通权限 Agent 直接改写固化核心；管理员和 SYSTEM
仍可恢复文件或调整 ACL。它不是防恶意管理员的加密隔离。

ACL 备份：

```text
run_codol_001\runs\ACL_BACKUP_20261020
```

加固脚本：

```text
run_codol_001\harden_frozen_core_acl.ps1
```

## 禁止事项

- 不修改 Golden 或 REF_LOBBY_KIT 的 `run_all.py`、`nt10.py` 来实现单次启动。
- 不直接绕开一次性入口启动客户端。
- 不在固化目录生成证书、日志、标志、运行状态或密钥。
- 不以空 publisher/profile/user 数据目录启动。
- 启动失败不在同一进程内多轮重试。

## 恢复命令

完整性检查：

```powershell
python -X utf8 .\run_codol_001\verify_frozen_chain.py
```

保护检查：

```powershell
python -X utf8 .\run_codol_001\run_frozen_chain_once.py --verify-only
```

实启：先确认一次性令牌已按明确的新实验重置，再执行：

```powershell
python -X utf8 .\run_codol_001\run_frozen_chain_once.py --seconds 60
```
