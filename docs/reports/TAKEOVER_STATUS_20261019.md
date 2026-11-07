# CODOL 项目接管状态

接管时间：2026-10-19（Asia/Shanghai）
工作根目录：`D:\BaiduNetdiskDownload\使命召唤OL`

## 当前结论

- 大厅链路已是可复用基线：`127.0.0.1:3074` TLS Auth、`127.0.0.2:3074` 明文 Lobby、4 处客户端放行补丁、KDF/HMAC/keepalive 证据齐全。固化入口是 `REF_LOBBY_KIT`，不得修改。
- 当前主线是本地原生对局：大厅 -> `nt10.py` -> `Bootstrapper32.dll` -> `CodolGameServer.Localnet32` -> 进程内 Dedicated。`CODOLCombatServer.exe` 和旧 `battle_server.py` 不属于这条链。
- 最新本地链运行失败在 FrameHook 之前：`CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\native_engine_attach.jsonl` 记录客户端 PID `19316`、Bootstrapper `0x62A10000`、Localnet32 `0x56030000`，`frame_hook=false`、返回码 `6`。
- 同一轮沙箱日志为：`[combined/backend] Refused to apply CODOL startup patches to an unknown executable image.` 和 `[combined/game-server] game server frame hook failed`；没有证据表明是 28961 协议、IIPS 8189fec 或 SessionStart 导致。

## 关键证据

1. `CODOL_LOCAL_ENGINE_CHAIN_20261019\HANDOFF_NEXT_SESSION_20261019.md` 是当前原生链交接入口；它要求先做固化链基线，再做运行期差异对照。
2. `_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp` 的宿主门禁要求 `TimeDateStamp=0x6096930A`、`SizeOfImage=0x0E5D6000`，随后还有多组函数前缀守卫。
3. 当前零售客户端 `COD OL\codoMP_client_shipRetail.exe` 的 SHA256 是 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`，实际 `SizeOfImage=0x0E659000`。工作区文档已确认它不是 `ol-mod` 参考 `out.exe` 的同一映像。
4. 当前 `COD OL\Ayria\Plugins\CodolGameServer.Localnet32` SHA256 为 `FC3A9174FA5E49138D6DF6FF22A20151551996ADE72A29D8EA5CD56D5A055EAB`。其二进制在多个位置含 `0x0E659000` 相关字节；`*.bak` 版本含 `0x0E5D6000` 相关字节。因此“只改宿主 SizeOfImage”不能直接视为已解决，仍需验证其余前缀守卫和入口时序。
5. 历史 `run_codol_001\LOCAL_LOBBY_KIT\local_native_server.log` 曾记录 `-q -qa` Dedicated 路径成功安装 FrameHook、监听 TCP `28961`、返回 ConfigureSession `status=0` 并占用 UDP `28960`。这只是历史时序样本，不能替代当前链验收。
6. 当前已清理客户端、Auth/Lobby、28960、28961、4200 残留；没有活动对局进程。

## 不变量

- 不修改 `REF_LOBBY_KIT`、`COD OL` 原版目录或现有黄金备份。
- 原生链测试时只允许一个 UDP `28960` owner；不要启用 `firingrange-booking-push.enabled`。
- 在 `CodolGameServer.log` 出现 `game server frame hook installed` 之前，不发送 SessionStart，也不把 UDP 28960 监听误判为进图。
- `AlwaysofflineRe.Localnet32.log` 的 `unknown executable image` 是独立的 3.3.3.3 客户端补丁门禁；历史运行中它可以先出现、随后继续应用 Auth3 补丁，不能单独作为 FrameHook 根因。

## 下一步

用相同的本地沙箱、当前插件和不启动外部战斗服的条件，先验证 Dedicated 注入路径：

```powershell
python -X utf8 .\CODOL_LOCAL_ENGINE_CHAIN_20261019\scripts\start_local_engine.py `
  --dedicated-bootstrap `
  --game-root D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_repro_test_20261019 `
  --seconds 60
```

只记录一次启动的 launcher/client/bootstrapper PID、模块基址、退出码、`CodolGameServer.log`、`AlwaysofflineRe.Localnet32.log`、端口状态和环境变量。

- 如果 Dedicated 成功而 Combined 失败，阻塞点是启动角色/时序/注入边界，应对齐入口，不再改 SessionStart。
- 如果两者都失败，读取第一条 binding 失败证据，继续做运行期模块与函数前缀差异表。
- 只有 FrameHook 成功后，才修正并发送 `SessionStart`；现有脚本的 classMask 与非 present class 的 perks/equipment 不一致，当前 payload 必然不合法。

本次接管没有修改生产代码或固化链。

## 暂停前最后一轮复测（21:26）

- 使用入口：`CODOL_LOCAL_ENGINE_CHAIN_20261019\scripts\start_local_engine.py --dedicated-bootstrap --seconds 60`。
- Auth/Lobby 服务成功监听：`127.0.0.1:3074`、`127.0.0.2:3074`；本轮使用 `--services-only --no-battle`，没有启动外部战斗服。
- 启动器 PID：`4812`；Dedicated bootstrap PID：`5204`。
- 沙箱日志在 `21:26:57` 出现：`[dedicated/game-server] game server frame hook installed`；Bootstrapper 加载 `Localnetworking.Ayria32` 和 `Platformwrapper.Ayria32`，Localnetworking 监听 `127.0.0.1:4200`。
- 但 `native_engine_bootstrap.txt` 未留下，最终没有可用的客户端进程、TCP `28961` 或 UDP `28960`；因此本轮只能判定为“FrameHook 日志曾出现，但游戏未保持运行”，不能判定 Dedicated 或进图成功。
- 暂停前已停止本轮启动器、Auth/Lobby 和 bootstrap 相关进程；当前没有保留客户端、IIPSHostApp、TP3Helper、CODOLCombatServer 或 `28960/28961/4200` 活动实例。

当前状态：**已暂停，等待后续指令**。

## 恢复后的 Dedicated 完整复测（21:46）

- 入口：`start_local_engine.py --dedicated-bootstrap --seconds 60`，同沙箱。
- Auth/Lobby 正常监听。客户端 PID 5560 以 `-q -qa` 挂起启动，解壳门在 3.91s 解锁，Bootstrapper32 注入成功（`0x69500000`）。
- **FrameHook 成功**：`CodolGameServer.log` 21:46:03 记录 `[dedicated/game-server] game server frame hook installed`；Localnet32 在模块表 `0x676B0000`。
- **但 DedicatedControl 未起来**：120 次连接尝试后 `127.0.0.1:28961` 仍不可达，UDP `28960` 未监听，脚本以 returncode=5 退出，客户端进程已结束。
- 结论：Dedicated 路径能过 `bindings.valid()` 和 FrameHook（与历史成功样本一致），当前卡在 FrameHook 之后、DedicatedControl 启动之前。下一步应查 `Com_Frame` 是否被调用、`onServerFrame` 是否运行、DedicatedControl listener 的启动条件与角色门，而不是回查 binding 门禁。

## 暂停后的 Dedicated 深入复测（22:06）

- 用 `datafix` 沙箱 + `--keep-iips` 测试：FrameHook 安装成功（22:06:19），但 `enable_iips=1` 触发 IIPS 错误弹窗，客户端无法继续。
- 用 `repro_test` 沙箱 + `enable_iips=0` 测试：FrameHook 安装成功，但客户端在 FrameHook 后退出（`0xFFFFFFFF`），28961 未监听。
- 探针验证：`CODOL_GameServerGetStatus` 返回 `enabled=0 frame=0 serverTime=0`，证明 `Com_Frame` 循环未运行。
- 结论：Dedicated 路径在当前环境下陷入两难——`enable_iips=1` 触发 IIPS 错误，`enable_iips=0` 导致客户端退出。需要找到历史成功样本中 IIPS 初始化的真实条件，或确认 Dedicated 模式是否需要完整的 `main` 目录 + 其他初始化步骤。
- 当前已停止所有残留进程，环境干净。
