# 独立本地原生战斗启动链

本目录是从固化链复制出来的独立新链。它不调用旧 REF_LOBBY_KIT、旧 run_all.py 或旧 start_native_dedicated_319.py。公共服务资产从固化链复制，原生战斗服二进制和 session descriptor 从 CODOL-Combat-Server-v0.1 复制。

两个入口只差是否拉起 C 端：

- `scripts/start_local.ps1`：启动原生 `CODOLCombatServer.exe`、本地 auth 和 Lobby，不拉起 `codoMP_client_shipRetail.exe`。
- `scripts/start_frozen.ps1`：启动完全相同的公共服务，然后调用新链自己的 `kit/nt10.py` 拉起 C 端。

公共端点：`127.0.0.1:3074`、`127.0.0.2:3074`、UDP `127.0.0.1:28960`。

密钥来源：`combat/session_descriptor_firingrange/battle_security_key.txt` 复制到 `kit/battle_security_key.txt`；新 Lobby 从该文件读取，避免全零密钥和原生战斗服不一致。

## 本地链

```powershell
.\scripts\start_local.ps1 -Seconds 600
```

成功条件：`stack_ready.json` 出现，`combat_server.log` 显示战斗服初始化，auth/Lobby 两个端口监听；进程列表中没有 C 端。

## 固化链

```powershell
.\scripts\start_frozen.ps1 -Seconds 600
```

成功条件：除本地链条件外，`NATIVE_CHAIN_READY client_started=true`、`kit` 下的 `frozen_nt10.txt` 产生，客户端和 IIPSHostApp 存活。

两条链共享 service_stack.py、战斗服二进制、session descriptor、auth、Lobby、端口和日志协议；只有客户端启动步骤不同。当前本地入口短时回归已确认：战斗服绑定 UDP 28960、导出 6 个 descriptor、使用 01010101010101010101010101010101，并在 8 秒后正常清理。

离线 selftest 当前通过 251 项；4 项失败来自复制后的运行环境（临时目录权限和缺少源码指纹目录），不是端口或协议启动失败。真实 C 端连接仍需通过固化入口单独验收。
