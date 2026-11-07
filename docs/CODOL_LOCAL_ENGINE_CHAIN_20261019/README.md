# CODOL 本地引擎对局链

本目录是独立的本地链。它复用固化链已验证的 Auth/Lobby/nt10 拉起资产，但战斗部分只走游戏进程内的原生 CodolGameServer.Localnet32。

这里的“C 端”如果在历史记录中出现，指 C/C# 手写的外部战斗服，例如 CODOLCombatServer.exe 或旧 battle_server.py。本地链不启动这些外部战斗服；固化链与本地链的大厅层可以相同，但战斗层必须保持独立。

## 分层

本地链结构：大厅服务器 -> nt10 拉起游戏客户端 -> Bootstrapper32.dll -> CodolGameServer.Localnet32 -> FrameHook -> DedicatedControl 127.0.0.1:28961 -> 引擎本地对局 / UDP 28960。

本目录不启动 CODOLCombatServer.exe，不启动 battle_server.py，不调用旧的 start_native_dedicated_319.py。

## 运行

使用已经独立重建好的沙箱：

    python -X utf8 .\CODOL_LOCAL_ENGINE_CHAIN_20261019\scripts\start_local_engine.py --game-root D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_repro_test_20261019 --seconds 180

流程：复制的 kit\run_all.py 启动 Auth、Lobby 和 nt10.py；--no-battle 阻止大厅层启动任何独立战斗服；随后 native_engine_attach.py 等待同一个游戏客户端进程，动态取得 32 位 LoadLibraryW，加载 Bootstrapper32.dll 和 CodolGameServer.Localnet32，等待 CodolGameServer.log 出现 frame hook installed，连接 28961 并发送 ConfigureSession。

## 成功证据

本地链成功日志应出现：Bootstrapper32.dll 注入成功、CodolGameServer.Localnet32 loaded、frame hook installed、DedicatedControl 28961 connected、ConfigureSession status=0，以及 UDP 28960 属于同一个 codoMP_client_shipRetail PID。

日志输出：CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\native_engine_attach.jsonl、CODOL_LOCAL_ENGINE_CHAIN_20261019\kit\local_engine_nt10.txt、游戏沙箱\Ayria\Logs\CodolGameServer.log。

本机已有成功证据在 run_codol_001\LOCAL_LOBBY_KIT\local_native_server.log：Bootstrapper32 injected、CodolGameServer.Localnet32 already present、frame hook installed、Connected to DedicatedControl port 28961、ConfigureSession status=0、UDP 0.0.0.0:28960 属于游戏 PID。

## 说明

CODOLCombatServer.exe 是独立 C# 协议服务器，只能用于离线协议/自测，不是本地引擎链。CODOL_NATIVE_BATTLE_CHAIN_20261019 是早先错误的公共战斗服模型，已废弃，不要使用。
