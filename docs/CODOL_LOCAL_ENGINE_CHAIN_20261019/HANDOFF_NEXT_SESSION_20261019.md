# CODOL 本地原生对局链交接日志

交接时间：2026-10-19

目标：让新的对话可以从当前证据继续推进，不重复已经做过的启动、转存和错误路线。

## 0. 任务边界

当前要做的是独立的本地原生战斗启动链。分层必须保持如下含义：

    Auth / Lobby 大厅服务
            |
            +-- nt10.py 拉起并准备游戏客户端
            |
            +-- 游戏进程内 Bootstrapper32.dll
            |
            +-- CodolGameServer.Localnet32
            |
            +-- 游戏引擎自己的本地 Dedicated 对局

这里的“C 端”指 C/C# 手写的外部战斗服，例如 CODOLCombatServer.exe 或旧 battle_server.py。本地链不能启动它。本地链可以复用固化链的 Auth、Lobby、nt10.py 和客户端拉起资产，但必须使用 --no-battle，由游戏进程内的 CodolGameServer.Localnet32 创建本地对局。

固化链和本地链是两条独立链：

- 固化链：Auth/Lobby/nt10 加上原有固化流程，必要时拉起 C 端手写战斗服。
- 本地链：复用大厅层，但不拉起 C 端手写战斗服，改由本地原生引擎对局。

不要把大厅服务器、C 端手写战斗服、CodolGameServer.Localnet32 混称为同一个服务。

## 1. 工作区和重要文件

本地链目录：

    D:\BaiduNetdiskDownload\使命召唤OL\CODOL_LOCAL_ENGINE_CHAIN_20261019

主要文件：

- scripts/start_local_engine.py：本地链总入口，默认走可见客户端模式；--dedicated-bootstrap 是专用取证路径。
- scripts/native_engine_attach.py：等待稳定客户端，取得 32 位 LoadLibraryW，加载 Bootstrapper 和 Localnet32，并在 Dedicated 模式下处理 28961/28960。
- scripts/round2_dump_and_reverse.py：运行期模块、可执行页、磁盘文件和页面镜像转存工具。
- kit/run_all.py：本地链大厅层启动器，已加入 --no-battle、客户端稳定等待和 --nt10-delay。
- kit/lobby_server.py：本地大厅服务副本。
- kit/nt10.py：与固化链相同的大厅注入器副本，当前 SHA256 与固化链相同。
- README.md：本地链简要说明。

当前测试沙箱：

    D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_repro_test_20261019

原版游戏和固化链目录不能直接改。固化链基准文件哈希：

    REF_LOBBY_KIT\run_all.py       2AAA8847F112D926B996E5FD38DD26B697ADC0697C45781F520940A8256ECDA6
    REF_LOBBY_KIT\lobby_server.py  D7EEB4564AF05F4C71FB3391112A8BF592B74F0AA12DEC8F286B927AE046C2CF
    REF_LOBBY_KIT\nt10.py          05863EBAFC7D7BB3820CCE057BC9E4E0EA07816945CA03E38A9BBFECACAB22F8

本地副本的 nt10.py 哈希相同；run_all.py 和 lobby_server.py 有本地链改造，不能直接当成固化链的等价文件。

## 2. 已完成且可信的证据

### 2.1 第一轮启动竞态

曾捕获到真实客户端启动过程：

- 首个客户端 PID 11204，主程序基址 0x00400000。
- codoMP_client_shipRetailBase.dll 基址 0x5E500000。
- WOW64 kernel32.dll 基址约 0x761C0000，动态 LoadLibraryW 约 0x761E1960。
- Bootstrapper 线程曾返回 0xC0000005，客户端约 4 秒后退出 0xC0000005。
- nt10.py 随后重试并创建 PID 3608。
- 旧逻辑曾继续附加已经退出的 PID 11204；现在已改为等待候选 PID 连续存活约 4.5 秒，并记录早退 PID。

后续每一轮都必须记录客户端 PID、启动器 PID、附加器 PID、退出码、模块基址和进程树，不能只看最后一个 PID。

### 2.2 IIPS 故障已单独隔离

历史 iips.ini 的 enable_iips=1 会产生：

    初始化IIPS错误：8189fec
    ExitCode = 0xFFFFFFFF

本地测试沙箱目前是：

    enable_iips=0
    iips_url="http://10.231.2.181/"

备份在：

    run_codol_001\sandbox_repro_test_20261019\iips.ini.bak_before_local_chain_disable_20261019

这只改了独立测试沙箱，未改固化链或原版。后续不要把当前 unknown executable image 直接归因到 IIPS；目前没有证据证明两者是同一个故障。

### 2.3 原生模块曾有完整成功样本

历史成功日志：

    run_codol_001\LOCAL_LOBBY_KIT\local_native_server.log

其中曾完整出现：

    PID=19576
    Unpack gate unlocked at t=6.36s
    WOW64 kernel32.dll base = 0x77A80000
    Dynamic LoadLibraryW @ 0x77AA1960
    Bootstrapper32 injected
    CodolGameServer.Localnet32 already present: 0x51450000
    frame hook installed
    Connected to DedicatedControl port 28961
    ConfigureSession status=0
    UDP 0.0.0.0:28960 属于游戏 PID

这证明模块加载、FrameHook、28961 控制端口和 28960 激活路径曾经可以连通，但没有证明当前独立本地链的路径、沙箱和客户端映像完全相同。该日志只能作为成功时序样本，不能直接当作当前链已经成功。

### 2.4 第二轮运行期转存

转存目录：

    CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\ROUND2_STATIC_DUMP_20261019_203103

本轮 PID 11172，重要基址：

    客户端       0x00400000
    Base DLL     0x5E500000
    Bootstrapper 0x62A40000
    Localnet32   0x563B0000

已保存 client_runtime.bin、base_dll_runtime.bin、bootstrapper_runtime.bin、localnet_runtime.bin、7 个可执行页镜像、dump_manifest.json 和 reverse_report.json。

本轮没有成功对局：127.0.0.1:4200 已监听，28961 只有 SYN_SENT，28960 未建立，客户端最终退出 0xFFFFFFFF。

注意：当时入口反汇编使用了模块基址，不是 PE AddressOfEntryPoint，因此 reverse_report.json 里的入口反汇编不能直接作为结论。下一次逆向必须按 PE 入口 RVA 和 section 文件偏移修正后再读。

## 3. 最近一次本地链结果和真正阻塞点

最近日志：

    CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\start_local_engine.jsonl
    CODOL_LOCAL_ENGINE_CHAIN_20261019\logs\native_engine_attach.jsonl
    run_codol_001\sandbox_repro_test_20261019\Ayria\Logs\AlwaysofflineRe.Localnet32.log
    run_codol_001\sandbox_repro_test_20261019\Ayria\Logs\CodolGameServer.log

启动器记录：

    launcher PID       18456
    稳定客户端 PID     19316
    附加器 PID         12652
    客户端基址         0x00400000
    Base DLL           0x5E500000
    LoadLibraryW       0x761E1960
    Bootstrapper       0x62A10000
    Localnet32         0x56030000
    frame_hook         false
    returncode         6
    lobby_ready        false

沙箱日志的决定性内容：

    [combined/backend] Refused to apply CODOL startup patches to an unknown executable image.
    [combined/game-server] game server frame hook failed

同时可以确认：

- Bootstrapper 已加载 Localnetworking.Ayria32 和 Platformwrapper.Ayria32。
- Localnetworking 已在 127.0.0.1:4200 监听。
- Localnet32 已进入模块表。
- 但 AlwaysofflineRe.Localnet32 拒绝给当前客户端应用 CODOL 启动补丁，导致 CodolGameServer.Localnet32 的 FrameHook 失败。
- 当前轮没有 lobby_ready.flag，也没有可靠的可见游戏窗口验收。

当前阻塞点应写成：

Native 模块加载成功，但 AlwaysofflineRe 不认可当前运行期客户端映像，导致启动补丁未应用，继而 FrameHook 失败。

目前不能把它写成“28961 协议坏了”“IIPS 8189fec”或“远程线程一定失败”。这些都没有被当前日志证明。

## 4. 新对话必须按这个顺序推进

### 第一步：先做固化链运行基线

不要直接继续改本地注入器。先把 REF_LOBBY_KIT 做只读副本，在副本上跑一轮完整固化链并记录：

1. Auth 服务启动、监听地址和日志。
2. Lobby 服务启动、监听地址和握手完成时间。
3. nt10.py 的实际命令行、重试次数、每个客户端 PID 和退出码。
4. TP/ACE/IIPS 进程是否出现，IIPS 配置原值。
5. 客户端窗口、lobby_ready.flag、进程树和所有模块基址。
6. 固化链是否启动 C 端手写战斗服，以及 28960 的占用 PID。

副本必须独立保存日志，不能修改 REF_LOBBY_KIT。这一轮的目的不是修复，而是回答“固化链启动时到底多做了什么”，因为当前本地链失败可能来自启动参数、环境变量、游戏根目录、TP/IIPS 时序或映像文件差异。

### 第二步：做静态和运行期差异表

把固化基线与最近本地轮逐项对照，至少包括：

- run_all.py、lobby_server.py、nt10.py 的哈希和实际参数。
- 游戏根目录：固化链的 sandbox_datafix_20260929 与本地链的 sandbox_repro_test_20261019。
- iips.ini、dwauth.ini、hosts、证书和启动标志文件。
- 客户端完整命令行、当前工作目录和环境变量，尤其是 OLMOD_PROCESS_ROLE。
- 客户端 PE 的 SHA256、SizeOfImage、入口 RVA、节表和磁盘路径。
- Bootstrapper32.dll、AlwaysofflineRe.Localnet32、CodolGameServer.Localnet32 的版本、大小和 SHA256。
- Localnetworking 的 4200、DedicatedControl 的 28961、对局 UDP 28960 的监听/连接时序。
- 进程内模块加载顺序和每个模块的运行期基址。

必须把“文件不同”“命令行不同”“角色环境变量不同”“时序不同”分别列为独立差异，不能只凭日志猜一个原因。

### 第三步：定位 unknown executable image 的识别条件

以插件日志和静态代码为入口，查清 AlwaysofflineRe 判断映像的依据：

- 是完整文件哈希、PE 头字段、入口字节、节大小，还是模块路径/进程角色。
- 期望的客户端文件是哪一个，是否必须来自固化链的同一沙箱。
- nt10.py 是否在插件识别前改写了客户端代码或加载顺序。
- 是否必须先完成大厅握手、TCLS/共享内存交接，再加载 Localnet32。
- 是否依赖历史 Injector32.exe、ol_room_owner.exe 或其他交接程序。

只有拿到证据后，才在本地独立沙箱做最小改动：优先对齐路径、映像文件和必要参数；不要先改插件内部补丁，也不要往固化链和原版目录写入。

### 第四步：重新跑可见模式并完整验收

本地链命令基线：

    python -X utf8 .\CODOL_LOCAL_ENGINE_CHAIN_20261019\scripts\start_local_engine.py --game-root D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_repro_test_20261019 --seconds 180

可见模式下，native_engine_attach.py 不应在 FrameHook 之前强行调用 CODOL_GameServerSetEnabled 或发送 ConfigureSession。先证明游戏映像被识别、FrameHook 安装，再进入 28961/28960 激活阶段。

本轮成功判据必须全部满足：

- Auth/Lobby 握手完成。
- 客户端窗口或可靠的大厅就绪标志存在。
- 客户端在观察窗口内没有早退。
- AlwaysofflineRe 不再报 unknown executable image。
- CodolGameServer.log 出现 frame hook installed。
- Localnet32 监听 28961，并返回 ConfigureSession status=0。
- UDP 28960 的拥有 PID 与当前客户端 PID 对应。
- 进程树中没有 CODOLCombatServer.exe 或旧 C 端战斗服。

任何一项缺失都不能宣布“进入本地原生对局”。

### 第五步：失败后再做第二轮转存和逆向

如果第四步仍失败，先保存准确的第一轮结果，再对同一 PID 或下一次稳定 PID 做转存。修正 round2_dump_and_reverse.py 的入口反汇编逻辑：

1. 从 PE 读取 AddressOfEntryPoint。
2. 用模块运行期基址加入口 RVA 得到真实 VA。
3. 用 section 的 PointerToRawData/VirtualAddress 做磁盘与运行期对应。
4. 对比客户端 .text、可写可执行页、Base DLL、Bootstrapper、Localnet32 的字节和页保护。
5. 把差异地址换算成 module + RVA，记录磁盘字节、运行期字节、保护属性和写入时序。

重点先查导致 unknown executable image 的识别输入，不要再次从错误的模块基址反汇编，也不要无证据地改重定位表或插入跳转。

## 5. 不要重复的路线和结论

- 不要启动 CODOLCombatServer.exe、battle_server.py 或 firingrange-battle.enabled 来冒充本地原生链。
- 不要把 C 端手写战斗服的“能进图”当作原生引擎物理验证。
- 不要把历史 local_native_server.log 直接当成当前链成功，只能拿它作为成功时序样本。
- 不要先改固化链、原版游戏、ACE/TenProtect 文件或现有备份。
- 不要继续把时间花在 CDB 参数传递上；当前首要阻塞已从“抓写入 D1”转移到 unknown executable image 和固化/本地启动差异。
- 不要把 SYN_SENT 的 28961 误判为 28961 协议本身损坏；当前日志显示 FrameHook 在其之前就失败了。
- 不要使用外部 IP、KEY 或外部模型调度；本任务只依赖工作区中的本地证据。

## 6. 新对话开始时先执行的动作

1. 阅读本文件和 CODOL_LOCAL_ENGINE_CHAIN_20261019\README.md。
2. 检查是否有残留 codoMP_client_shipRetail、Bootstrapper、Localnet32、28960/28961/4200 监听者，并只记录或清理本链残留。
3. 读取最近四个日志文件，确认没有新的用户改动覆盖当前结论。
4. 先建立固化链只读副本和运行基线，再决定是否改本地链。
5. 每次启动都保存一份带时间戳的 JSONL/日志目录，写出 PID、基址、退出码和成功判据。

正确推进方向：固化链运行基线 -> 运行期差异对照 -> 识别条件取证 -> 本地沙箱最小修复 -> 可见大厅验收 -> 原生对局激活 -> 第二轮转存复核。

