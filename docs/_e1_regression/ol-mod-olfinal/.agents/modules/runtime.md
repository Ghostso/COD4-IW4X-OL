# 运行时与自动化

## 分发与启动

分发内容、哈希来源、seed 和安装策略只在 `distribution/README.md` 与 `distribution/runtime-components.json` 维护。

标准启动使用原版 `Injector32.exe`，工作目录为游戏根目录，只传 `codoMP_client_shipRetail.exe` 路径，不添加参数。`CODOLBackend.Ayria32` 和旧的运行时 hotload 不是当前链路；`CodolGame.py launch-inventory` 只是 `launch` 的兼容别名。

`Localnetworking.Ayria32` 已由 xmake target `ol_localnetworking` 源码化，构建物为
`LocalnetworkingRe.Ayria32`，stage 时覆盖到兼容文件名。实现保持归档二进制的
`onStartup/onInitialized/onMessage`、六个 Winsock hook、`.Localnet32/Createserver`
发现链和无 virtual destructor 的 2019 `IServer::Endpoints` ABI；`IServer` 的唯一共享
定义在 `src/shared/LocalnetServer.hpp`。运行根、Plugins、Logs 和 Assets 均从当前 DLL
路径推导，不再写死 `./Ayria`。自动化 fixture 已验证构建物为 PE32、三个 export、
Localnet32 枚举、hostname claim、240/8 synthetic DNS、六个真实 Mhook hook、同-server
fan-out，以及 TCP 和非阻塞 UDP 的 `ping/pong` 往返与来源 endpoint 回填；尚未用该重建 DLL 完成 CODOL 自然链路
实跑，因此不能把归档组件的运行证据直接转移给重建物。归档 DLL 仍保留在
`distribution/legacy` 作为哈希固定的对照证据，但不再进入 stage。

`Platformwrapper.Ayria32` 的 CODOL-only 源码化第一阶段也已落入 xmake target
`ol_platformwrapper`，构建物为 `PlatformwrapperRe.Ayria32`，stage 时覆盖兼容文件名。实现以
`Ayria_cpp_20191208/Platformwrapper` 为结构基底，但只保留 CODOL EXE 已确认动态消费的
`Invoke/CreateObj/InitCrossContextByOpenID`、`onStartup/onInitialized/onMessage` 和对应三处
Mhook；52 个通用 Steam exports 没有进入实现。归档 DLL i64 进一步确认 Tencent 对象只有
15-slot vtable、byte/wide string 均先按 caller capacity 截断复制再回写完整长度，TerSafe
`CreateObj(0)` 分配 `0x858` bytes，`setInitInfo` 分别写 `uin +0x0C`、`gameVersion +0x10` 和
64-bit sink `+0x18`。这些差异已经覆盖 2019 源码未表达的对象头字段，并由静态断言锁定。

新 `Ayria/Assets/Platformwrapper/Platform.json` 集中持有 title、game/zone/server tags、认证
endpoint 和稳定 platform user ID；旧 `UserID.txt` 只作为迁移输入，`Username.txt` 不再进入
CODOL-only 插件。platform ID 是客户端 room/OpenID 兼容身份，backend profile 继续唯一持有
显示名。离线测试已经覆盖 PE32、六个 exports、配置优先级、`DEADC0DE` 低 ID 扩展、Tencent
tags 和 TCLS mapping 初始化/清理；归档 DLL 仍保留为回退。clean 自然运行
`.runtime/natural-match/20260809_rebuilt_platformwrapper_v1/` 中 client/dedicated 均加载重建 DLL，
Auth/frontend、QuickMatch、ready、client-native allocation、`mmbook/mmstart`、`SessionStart`、
`mp_crash_tropical/sd` world 和 snapshot 全部成功。随后对同一 client 的只读内存核验确认 room
member identity `+0x10/+0x14` 与内嵌 `MatchMakingInfo +0x208/+0x20C` 均为
`0x00000000DEADC0DE`，修复了旧失败样本中的零 internal ID。该证据只覆盖 CODOL-only 表面，
不提高 52 个未迁移 Steam exports 的完成度。

2019 ABI 的 `onStreamread/onPacketread` 不返回目标连接；原版 Localnetworking 因而按
`IServer*` 读取一次并 fan-out 到该 server 的全部同类 socket。源码化实现保持该语义，
并用每 socket 发送队列处理短写与 `WSAEWOULDBLOCK`。UDP 仍继承归档实现的
UDP-over-TCP 无 framing 边界；在取得 CODOL burst 运行证据前不擅自修改内部 wire。

## 双进程启动

`CodolGame.py launch-dedicated` 是当前 shared room owner + client + dedicated 生命周期入口。
launcher 先启动独立 `ol_room_owner.exe` 并确认 loopback IPC 端口就绪，再启动 client，最后以
`OLMOD_PROCESS_ROLE=dedicated` 启动游戏服务进程。CODOL 的 CRT initializer
`CODOL_SingleInstance_Init 0x00B49820` 原本让所有进程创建同一个全局 mutex；dedicated 的
`ol_game_server` 只在该角色下校验 CODOL PE timestamp、image size、mutex 名称和
`WinMain 0x641E2A` guard bytes，然后把 dedicated 的 mutex 名称末位改为独立固定值，同时
保持原生 `75 2D` 条件分支。client 与 `combined` 仍使用原名称和原生单实例保护。旧版
`EB 2D` bypass 会被原子升级为独立 mutex 并恢复为 `75 2D`。真实回归已验证结束 client 后
dedicated 保持存活，`CodolGame.py launch-client` 可只恢复 client 和 process state，不重启
authoritative world。第二进程还使用 CODOL `WinMain` 原生支持的 `-qa` 参数越过 TCLS-only
启动门槛，不另行 patch `WIN_NO_TCLS` 分支。

launcher 显式隔离 `OLMOD_PROCESS_ROLE`、`OLMOD_DEDICATED_CONTROL_PORT`、
`OLMOD_CLIENT_BRIDGE_PORT` 和 `OLMOD_ROOM_OWNER_PORT`，并给标准启动的两个游戏进程设置
`OLMOD_CONSOLE_LOG=1`。client 窗口标题为 `CODOL Client / Backend`，dedicated 为
`CODOL Dedicated Server`；未通过 launcher 启动时控制台默认关闭，可显式设置同一变量开启。
控制台在第一次正常 runtime 日志调用时延迟创建，不在 `DllMain` loader lock 内初始化；Injector
若让游戏继承不可见 console，runtime 会先脱离再分配可见窗口。同一内容继续分别落到 backend 与
game-server 文件日志。launcher 以 schema 2 原子维护 `Ayria/Logs/ol-mod-processes.json`，记录
owner PID/映像名/端口和两个游戏进程；schema 1 只读兼容。成功不再只看 Injector 返回和模块加载：
owner、client bridge 和 dedicated control 三个端口都必须进入预期状态；任一阶段失败会按反序回滚
已启动进程。`launch-client` 只在 tracked dedicated 与映像名匹配的 owner 均存活且端口状态一致时
恢复 client；`stop` 不会仅凭陈旧 PID 结束名称不匹配的进程。2026-08-08 clean run 已验证两个原始 EXE 进程同时保持
响应、两边完整加载五个模块，并闭合 `28962 -> client`、`28961 -> dedicated`。后续自然
`mmstart` 已闭合跨进程 `SessionStart`、局内连接、native world 和持续 snapshot。dedicated
第一阶段又只裁掉 `Com_Frame` 内四个已确认的 client-only per-frame callsite，仍保留 common
frame、资产更新与 ol-mod scheduler；`.runtime/natural-match/20260808_dedicated_frame_trim_v24/`
在 clean deployment 后保持 session/gamestate accepted、CCS/world/transport 有效，并发送
`4 full + 401 delta` snapshot。随后 dedicated 又只移除 WinMain 对
`CODOL_EmbeddedBrowser_Init` 的完整已核验 callsite，保留 `Com_Init` 和
`Com_Init_Try_Block_Function`；`.runtime/natural-match/20260808_dedicated_browser_trim_v25/`
以 `138/0` accepted/rejected client packets、`3 full + 103 delta` snapshot 和 parser
snapshot/playerstate `28/28` 通过 clean deployment。

真实第二客户端的基础隔离已具备独立 primitive，但尚未形成同局入口：
`OLMOD_CLIENT_INSTANCE=2..9` 可在 CODOL 原生 mutex 创建前把名称末位改为对应实例值，仍保留
原生 `75 2D` guard；`OLMOD_PLATFORM_USER_ID` 可按进程覆盖共享 `Platform.json` 的 platform
ID；`CodolClientAccount.py` 只在目标 user-ID 目录不存在时复制首账号的
`Publicprofile/Privateprofile/Inventory/the.json` 并创建独立 `Identity.json`，不会覆盖现有玩家
状态。独立 shared room/session owner 与 IPC host 现已由 launcher 管理，但每个 client 仍加载一套
进程内 backend，真实 room handler 尚未向 owner 登记；dispatcher 也仍只向单一 client bridge port
捕获 loadout。因此这些 primitive 只证明进程、身份、持久状态和 owner 生命周期可隔离，不能宣称
第二客户端已进入同一 backend room 或 authoritative session。正式下一步是按 authenticated user ID
从已确认的 room handler 登记各 client bridge，并由 booking 遍历冻结 roster 做多 endpoint capture。

多客户端 launcher 的正式职责仅限进程生命周期和 endpoint 注册：为每个 client 分配唯一
`OLMOD_CLIENT_INSTANCE`、platform user ID 和 client bridge port，并把该 endpoint 连同认证会话
登记给共享 backend owner。它不得决定房间成员、复制运行时 loadout、合并 `SessionStart`，也不得按
“client 1/client 2”硬编码队伍或权限。`ol-mod-processes.json` 后续需要把单值
`clientBridgePort` 提升为每 client 的 role/instance/user/bridgePort 记录，同时保留 dedicated
control port；状态恢复必须拒绝重复 instance、user ID 或 port。shared owner 与 booking dispatcher
现已支持一般化成员及逐 bridge capture；process state schema 3 也把每个 client 的 PID、instance、XUID
和 bridge port 独立记录，仍只读兼容 schema 1/2。`launch-dedicated` 保持启动主 client；随后可用
`CodolGame.py launch-client --client-instance 2 --platform-user-id <XUID> --client-bridge-port <PORT>`
附加第二客户端。协议和 launcher 使用固定 16 位大写十六进制 XUID，例如
`01100001DEADC0DF`；Alwaysoffline backend 的磁盘目录沿用无前导零形式，例如
`1004/1100001DEADC0DF`。两者是同一数值的不同表示，不得把目录名直接作为 platform ID。
secondary 启动前要求其账号目录内 `Identity.json` 已由 `CodolClientAccount.py` seed，
并拒绝与活动 client 重复 instance、XUID 或 bridge；日志按 client instance 分开。当前剩余实施边界是
两个真实 client 的 UI room/ready 和最终同局自然验证，而不是进程生命周期或 descriptor 聚合。
CODOL 当前自然认证使用 task 32，该 payload 只携带 session key、不携带 XUID；backend 的
`AuthSession` 因此必须以同一 `OLMOD_PLATFORM_USER_ID` 初始化身份，再由对应玩家目录解析名字。
task 28 的原生 payload 会携带 XUID，仍保持 payload authoritative，不被进程默认值覆盖。
真实 quick-match 的 `0x0B/13` 无参数请求在线上编码为单字节 `00`；handler 只接受该精确
wire 表示或测试用空 payload，其他字节继续 fail closed。旧合成测试只使用空 payload 曾导致
自然 room entry 持续返回错误 `1000`，且 owner IPC 根本未被调用。
真实顺序中两端 `mmstart` booking 会先于 task 4 ready 广播。dispatcher 因此按同一 request
generation 有界等待 owner 返回全员 ready 的冻结 roster；拿到 roster 后仅由 XUID 排序第一名
对应的 backend 聚合并提交一次 `SessionStart`，其他成员的重复 booking 不产生 dedicated side effect。
由于各 client 的本地 room 只含自身、但 task 4 channel push 会跨进程广播，一端 ready 会令另一端
本地 ready 标志变成 `1`，后者可能不再发送自己的 16-byte ready fixture。每个认证 client 发出
`mmstart` 本身已证明其本地 ready/match 状态机完成；booking sink 因此先用该 client 的 XUID/token
向 owner 提交自身 ready，成功后才进入 dispatcher。该提交不能替其他成员授权，owner/IPC 失败时
booking fail closed。

Audio startup 的三方结构参考与 CODOL 运行行为存在重要差异。BO1 将
`SND_InitDriver/SND_Init` 都放在 `!com_dedicated` 内，Ghosts dedicated 也没有 sound startup；
CODOL 对应序列则是 `CL_InitRenderer -> SND_InitDriver -> SND_Init -> cls_soundStarted=1`。
v26 只移除两次 sound call 但保留 started 提交，v28 连同提交一起移除，两者都在 process patch
成功后、dedicated control port 就绪前退出，因此完整 guard 不能直接移植。当前只 NOP
`Com_Init` RVA `0x19CBEA` 对 `SND_InitDriver 0x00712C10` 的完整 call，保留
`SND_Init 0x00710C80` 与 `cls_soundStarted 0x078B0A48`。新进程首先通过双端 control readiness，
随后 `.runtime/natural-match/20260808_dedicated_audio_driver_trim_v29/` 自然闭合 QuickMatch/ready、
session/gamestate accepted、world/transport，并发送 `3 full + 403 delta` snapshot、ack `408`；
client ingress 为 `538 accepted / 1 rejected`，唯一 reject 是连接前的非 CODOL netchan packet，
parser snapshot/playerstate `14/14` 且零 overflow，两个 PID 在捕获后仍响应。window、renderer、
剩余 sound 软件状态和 input 初始化仍在执行，不能把当前状态描述为完整 headless。

Renderer 不能沿 BO1/Ghosts 的 dedicated guard 只裁一个 CODOL callsite。`CL_InitRenderer 0x00467E20`
的注册、viewport、white/console material、font、StatMon 和 console asset 流程虽与 BO1 同构，且
Ghosts dedicated 不调用对应函数，但自然实验 v30 只 NOP `Com_Init` RVA `0x19CBE5` 的完整
`E8 36 B2 EC FF` 后，patch 成功且 dedicated 进程保持存活，却始终不能到达 ol-mod control
listener；这表明 CODOL 后续初始化仍消费 renderer 状态。撤销该 patch 后，
`.runtime/natural-match/20260808_dedicated_renderer_retained_v32/` 重新自然闭合
`mp_crash_tropical/sd`：session/gamestate accepted、class `31/31`、character `2`、dynamic weapon
`352`、world/transport 有效，稳定窗口为 `4 full + 412 delta`、ack `417`、client packet
`553 accepted / 1 rejected`，parser snapshot/playerstate `16/16` 且零 overflow。renderer 必须保留，
直到 CODOL post-init consumer 和 dedicated 分支能作为一个整体被证明并裁剪。

Window startup 当前只裁掉一个独立且副作用明确的边界。CODOL WinMain 在
`0x0064272A` 无条件执行 `push HWND; call ds:SetFocus`；dedicated 会在严格确认 `52 FF 15`
opcode 前缀后 NOP 完整 7 bytes，避免只删 6-byte stdcall call 而把参数留在栈上。IAT absolute
operand 的四字节由 PE loader relocation 所有，不参与固定值比较。自然 run
`.runtime/natural-match/20260808_dedicated_focus_trim_v34/` 闭合 `mp_crash_tropical/sd`、
session/gamestate accepted、class `31/31`、character `2`、dynamic weapon `352`、world/transport，
并达到 `3 full + 409 delta`、ack `414`、`549 accepted / 2 rejected`、parser
snapshot/playerstate `13/13` 和零 overflow；两个 reject 都是连接建立前的非 CODOL netchan
packet，随后 accepted ingress 与 delta snapshot 持续推进。该证据只允许移除无条件 focus
副作用；window class/handle、renderer 和 input startup 仍保留，当前仍不是完整 headless。

同一 WinMain 还会先用 `SystemParametersInfoA` 读取 Sticky/Toggle/Filter Keys，再在功能未启用时
临时清除热键标志。Dedicated 保留三次 GET 和退出路径使用的原状态，只把 RVA
`0x242662/0x24267B/0x242692` 的 `75 12/75 10/75 11` 分别改为
`EB 12/EB 10/EB 11`，从而始终跳过三次 SET。三个 opcode 与位移会作为一个原子单元完整校验；
原始、部分已 patch 和全部已 patch 均支持，未知 bytes 在任何写入前拒绝。参考实现并不一致：
BO1 dedicated WinMain 没有这组逻辑；Ghosts dedicated 则显式调用
`Sys_RecordAccessibilityShortcutSettings` 和 `Sys_AllowAccessibilityShortcutKeys(0)`。因此该裁剪是
CODOL dedicated 的宿主副作用隔离，不冒充三方原生一致。clean 自然 run
`.runtime/natural-match/20260808_dedicated_accessibility_trim_v35/` 闭合 `mp_crash_tropical/sd`、
session/gamestate accepted、class `31/31`、character `2`、dynamic weapon `352` 和 world/transport；
5 秒稳定窗口达到 `3 full + 100 delta`、ack `104`、client ingress `133 accepted / 0 rejected`，
parser snapshot/playerstate `24/24` 且零 overflow。

Dedicated 的 window message pump 继续完整保留，只移除它开头的系统光标可见性同步。CODOL
`IN_UpdateSystemCursorVisibility 0x0063DF20` 只按 desired/cached 状态循环调用 `ShowCursor`；BO1
`IN_ShowSystemCursor 0x007D8A00` 具有相同计数同步算法，Ghosts dedicated 则使用 server console
message loop。runtime 在严格确认 RVA `0x6980F4` 的 `E8 27 5E BA FF` 后 NOP 完整 call，仍执行
`PeekMessageA/GetMessageA/TranslateMessage/DispatchMessageA`、WndProc、window handle、renderer 和
其余 input 状态。clean 自然 run
`.runtime/natural-match/20260808_dedicated_cursor_visibility_trim_v36/` 闭合
`mp_crash_tropical/sd`、session/gamestate accepted、class `31/31`、character `2`、dynamic weapon
`352` 和 world/transport；稳定窗口达到 `3 full + 80 delta`、ack `84`、client ingress
`107 accepted / 0 rejected`，parser snapshot/playerstate `10/10` 且零 overflow。

Dedicated startup 现在还只移除一次不再有后续 consumer 的 input frame 调用。CODOL
`IN_Frame 0x0063E030` 与 BO1 同名函数的控制流吻合，负责 click-to-continue、mouse initialized/app
active 判断、mouse activate/deactivate 和 movement；正常每帧 caller 已由第一阶段 frame trim 移除。
runtime 在严格确认 `Com_Init` 尾部 RVA `0x19D0D0` 的 `E8 5B 0F 0A 00` 后 NOP 完整 call，
不删除 `IN_Init`、input globals、设备初始化或 window message pump。clean 自然 run
`.runtime/natural-match/20260808_dedicated_input_frame_trim_v37/` 闭合 `mp_crash_tropical/sd`、
session/gamestate accepted、class `31/31`、character `2`、dynamic weapon `352` 和 world/transport；
稳定窗口达到 `3 full + 86 delta`、ack `91`、client ingress `116 accepted / 0 rejected`，parser
snapshot/playerstate `12/12` 且零 overflow。

完整跳过 `Com_StartHunkUsers 0x0059CFE0` 的方案已被自然运行证伪。CODOL 函数与 BO1 同名
边界逐调用吻合，但当前 dedicated 仍通过本进程的 client-loaded XAsset registry 解析武器，尚未拥有
BO1 server 的独立资产注册入口。v38 同时跳过 RVA `0x19D16B` 的启动 call 和 RVA `0x19E0F4`
的 Com_Error recovery call 后，frontend、ready、自然 allocation、transport、configstrings 和
`154 accepted / 0 rejected` ingress 均继续工作，但 session 固定停在
`weapon_registry_unavailable`，resolved class mask `0/31`，没有 gamestate、world 或 snapshot。
该 patch 已撤销。回退后的 clean run
`.runtime/natural-match/20260808_dedicated_hunk_users_retained_v39/` 恢复 session/gamestate
accepted、class `31/31`、character `2`、dynamic weapon `352`、world/transport、
`4 full + 88 delta`、ack `93`、`116 accepted / 1 rejected`；唯一 reject 是连接前非 CODOL
netchan packet，parser snapshot/playerstate `17/17` 且零 overflow。process patch 安装器的
`VirtualProtect`、cache flush 和 protection restore 已改为同一表驱动区域循环，并由该 clean run
验证无行为回归。`Com_StartHunkUsers` 必须保留到 dedicated 拥有等价的 native asset-registry
bootstrap；不能因 BO1/Ghosts dedicated 省略 frontend startup 就直接搬用完整 guard。

v40-v44 对“用四个 common zone descriptor 直接替代该 owner”做了更窄的自然验证。CODOL
`0x0049FD00` 的确构造 `patch_common_mp/common_mp/patch_localized_common_mp/localized_common_mp`，
`0x0059D730` 也确实在 frame 中轮询 loaded 后执行 weapon registry 序列；但 dedicated 在原生
post-init gate 未成立、registry 仅 `1 weapon / 2 attachment models` 时强行执行该序列，会在
`CODOL_Weapon_InitRegistry 0x0042CC50` 触发 `0xC0000005`，并在 watcher attach 前退出。
撤销首帧强制初始化并保留完整 Hunk 路径后，v44
`.runtime/natural-match/20260808_dedicated_hunk_users_native_owner_v44/` 中原生链自行把 registry
推进到 `357 weapons / 151 attachment models`，并闭合 session/gamestate、class `31/31`、
dynamic weapon `352`、world/transport、`4 full + 78 delta`、ack `84`、`105 accepted / 0 rejected`。
因此 runtime 不再安装完整 Hunk caller patch，也不主动调用该局部 registry 序列；下一轮必须先
闭合 `0x0059DD20/0x0059C180` 内 fastfile 与 post-init 状态的真实所有权。

后续静态追踪已闭合 `0x0B584C53` 的真实 writer。`0x0B584C50` 是 CODOL 的全局
`UIViewer` 对象，`UIViewer_Show 0x00566940` 在完成 `mp_ui_viewer` 的客户端 world、表现和
frontend setup 后用一次 word 写入提交 `{show=1,deferredShow=0}`；`UIViewer_Hide 0x00566B70`
对称清零。BO1 PDB 的 `UIViewer::Init/LoadMap/Show/Hide` 与这些字段和控制流逐项吻合。因此
`Com_PollCommonXAssetInitialization` 检查的不是通用 asset-ready byte，而是
`uiViewer.show`，它只是在当前客户端路径中间接保证更宽的 frontend/post-init 已完成。

`0x0059DD20` 也已按 BO1 同层职责闭合为 `Com_AssetLoadUI`：`0x0046AF40/0x0046AA00`
负责重置和分配本地 client memory，`0x00484C60("ui_mp", "menu")` 统计 UI zone，
`0x0059C180` 请求 UI 与 common MP fastfile，`0x006098D0("", "")` 清空 UI map/gametype，
`0x00471B00` 初始化 frontend/menu users。这里大部分仍是客户端职责；但在找到
`sub_584D30` 所消费 weapon-group list 的真实 producer 前，不能只复制其中一两个调用作为
dedicated bootstrap。下一调查边界收窄为该 list 从空到完整的 owner，而不是继续追
`uiViewer.show` 本身。

该调查已在只读 v51 `.runtime/natural-match/20260808_dedicated_weapon_group_root_poll_v51/`
达到足够的架构决策边界。managed asset probe 在 dedicated 上每 100 ms 只读
`0x02DF7D50`、weapon registry count、`uiViewer.show` 与 common-zone observation；root 从
`0` 变为 `0x33B99E0` 时，registry 已为 `353`、`common_mp=true`、`uiViewer.show=0`。
同轮 session/loadout/gamestate accepted、class `31/31`、dynamic weapon `352`、snapshot
`95`，客户端 parser snapshot/playerstate `134/134` 且零 overflow/`Com_Error`。因此该 list
不是 registry 主体或 frontend viewer 的前置条件。v45-v50 试用的 hardware watchpoint 会
终止客户端或让 dedicated 长期停在 `configstring_generation_reset`，已删除；不得把这些
失败运行当成游戏因果证据。当前保留完整 `Com_StartHunkUsers` 并暂缓继续细拆 assets，
只读 probe 留作未来部署/资源优化重新开启调查时的状态工具。

## Frida 临时目录

`tools/runtime/CodolFridaRuntime.py` 必须在 import `frida` 前执行，将解包目录放到仓库的 `.runtime/frida`。默认清理超过 24 小时的目录；批量清理使用 `CleanupRuntimeTemp.py`，不要再污染用户全局 TEMP 或工作区公共根目录。

`CodolMemoryStrings.py` 用于对运行客户端做有上限的只读 ASCII 证据扫描。它不调用游戏函数、不写目标内存，按 16 MiB chunk 扫描 readable ranges，定期输出进度，并把命中地址、range/module 归属和邻近字符串保存到 `.runtime/memory-strings/`。不要再为同类任务拼装无进度的单次全内存 `Memory.scanSync`；同步 RPC 被外部强制终止时可能继续占用目标进程，必要时应结束该次测试客户端，而不是继续叠 attach。

## 匹配自动化

`CodolMatchFlow.py --action full` 依次执行原生 QuickMatch、等待房间、调用 room `SetReady(1)`，然后只观察 allocation。默认不直接调用 `0x006E4A20`。

开启 `OLMOD_CONSOLE_LOG=1` 时，同一客户端进程同时拥有 `ConsoleWindowClass` 控制台窗口和类名为 `CODO` 的游戏窗口；`EnumWindows` 顺序受 Z-order 影响，不能取首个可见窗口。`CodolMatchFlow` 现只选择 `CODO` 的 HWND/thread，缺失时等待并 fail closed。修复前两客户端会随机有一端只报告 `armed`，因为 native 调用被约束到了控制台线程；修复后的 clean `mp_crash_tropical/sd` 双客户端运行让两端进入 `Playing`，分别完成 14 秒 `gameplay_smoke`，随后 `.runtime/two-client-stability/20260816-190102.jsonl` 又持续推进 30 秒。最终双方 `clientThink failure=none:0`、reliable 全确认、player/clientInfo mask 均为 `3`，进程保持在线。综合输入只证明所列动作没有破坏 transport/usercmd/snapshot，仍不替代逐动作表现与模式完整性验证。

仓库根目录的 `Match_CODOL_Two_Clients.bat` 固化上述共享房间顺序。默认只停止 process-state 中受跟踪的测试进程，再启动 dedicated 和两个独立 client；`reuse` 模式保留已经启动且仍在 frontend 的三个进程。两种模式都由 `CodolTwoClientMatch` 等待 owner 先观察客户端 1 发布房间、客户端 2 加入同一 roster、双方并行 Ready、roster freeze 和单次 booking，最终要求双方 `Playing` 及短 transport 稳定窗口。手动依次让两个客户端各自匹配可能建立两个单人 native room，不能等价替代该流程。

只有显式 `--force-client-allocation` 或 `--action allocate` 才会强制调用该客户端入口。每次记录必须保留 `source=client-native` 或 `source=frida-forced`。

`CodolNaturalMatchTrace.py` 是自然匹配验证的统一生命周期入口。它可以选择 build/install 和 clean launch；对于本轮启动的客户端，无副作用的 frontend probe 必须同时看到本轮自然 `ClientLoadTime` telemetry，以及 `QuickMatch` 实际访问的 native objects、vtable slots 与方法地址全部就绪且连续稳定，才允许继续。client connection state 只记录为诊断信息，不参与 readiness 判定。随后要求 `CodolNetchanTrace.py` 的主 packet log 出现脚本 `ready`，并要求同一 Frida session 的低流量 Cbuf log 同时出现 `ready/attached`，再以 `CodolGameServerControl.py --watch-log` 的单次持久 Frida session 确认 server watcher armed。不要错误要求忙碌的主 packet log 也保留 Python-side `attached` append；2026-08-04 实跑中该 marker 因并发落盘缺失，但同一文件已有数千个完整 parser event。不要为每个 sample 反复 attach/detach；该旧方式曾在 allocation 后触发 `frida-agent.dll` `0xC0000409` 崩溃。

`CodolMatchFlow.py --character-index` 不直接写 current-character cache，也不再误用 onboarding selector `0x68C580`。它通过 `CODOL_CharacterSlot_GetItem 0x593370` 取得真实 item，再以保留 EDI 的 x86 thunk 调用普通 `CODOL_CurrentCharacter_SelectItem 0x689FF0`；观察到 `dwProfile +0x9085` dirty flags 后，在窗口线程限频调用 `CODOL_PublicProfile_UploadPoll 0x592350`，并等待 operation 回到零、dirty flags 清空后才允许 QuickMatch。`+0x9084` 只作为 raw `state_9084` 输出，不冒充 upload completion。forced `StartGame` 若从同一 window-thread Interceptor 回调内调用，Frida 可能抑制嵌套的 `startGameAddress` callback；工具只在 NativeFunction 无异常返回后补发同等标级的 `allocation_observed/source=frida-forced/observation=native_call_returned`，避免真实调用已完成却无界等待。

`CodolClientInput.py` 用 CODOL action table 与 `CL_ExecuteBindingAction` 触发真实 binding input，而不是把没有 console handler 的 `+forward` 交给 `Cbuf_AddText`。当前直接由 CODOL `s_bindingActionNames` 闭合的动作包括 ADS `+speed_throw/-speed_throw`、冲刺 `+breath_sprint/-breath_sprint`、专用换弹 `+reload/-reload`、开火、四向移动、跳跃、蹲伏、匍匐和切枪；`+usereload` 在实测缺弹状态下没有进入 reload weapon state，不能代替专用换弹 action。飞扑不伪造独立 binding，而由 scenario 在前进和冲刺期间组合 prone，继续交给 native `Pmove` 判定。工具在一个 Frida session 内完成 main-thread input timeline、超时 release、parser counters，以及 server `192`-byte sample、client snapshot/prediction 的 opaque byte capture；Python/JS 不解码这些状态或实现 movement/weapon/stance heuristics。`CODOL_GameServerGetWorldPlayerSampleV1` 仍在同一把 C++ 锁内一次复制 frame、last usercmd、world player 与 weapon scalars，避免多个 getter 拼接跨帧状态。超时 release 必须调用 lowercase RPC `requestrelease`；scenario 在 `Com_Frame` 完成最后一次 release/sample 后直接发送 terminal，不再经过独立 capture-finalize RPC。`--input-action` 保留单动作兼容入口，`--input-scenario` 加载 versioned JSON；两者在 world/可选 loadout 边界后停止旧 watcher，再运行 single-session exercise，证据固定为 `client-native-forced`。

`tools/runtime/scenarios/gameplay_smoke.json` 是 14 秒综合输入刺激，覆盖 ADS、短点射、换弹、切枪、前进冲刺和蹲伏/匍匐切换。它只用于在已有 Playing world 中快速发现 parser、usercmd、snapshot 或原生状态机回归；多种动作共享同一窗口，不能替代用于归因的单动作 scenario，也不能把通过结果解释为 gameplay 已完整还原。

`CodolHudElemState.py` 是只读 HudElem 差分工具。它从活动 snapshot 读取 CODOL 的 `31 current + 31 archival` active prefix，并按本体 `42` 项 descriptor 返回少量原始字段；不写客户端内存、不推断文字语义。定位“受击后错误出现战地指令完成”时，应在同一局内分别捕获受击前后结果，先确定新增/变化的数组槽、type 和字段，再沿对应 server HudElem owner 与客户端 consumer 核对；不得根据屏幕文字直接清零某个未知字段。

综合 scenario 在父进程只读取和规范化一次，随后以独占创建方式冻结为本轮 run 的 `input_scenario.snapshot.json` 并记录 SHA-256；子进程只读取该不可变副本并验证 digest。指定 `--output` 时，JSON framing 增量写入 `client_input.samples.jsonl`，Frida binary `_data` 原样写入相邻 `.samples.bin`；每批 flush/fsync，sequence、segment offset/size/hash 连续校验，崩溃尾部和 orphan bytes 可诊断恢复。纯数据的原子写入、framing 和离线校验集中在 `CodolCaptureEvidence.py`，父编排器在子进程退出后会重新读取 JSONL/blob、验证每段 hash 并与 scenario 和 child summary 对照，不接受只保持相同文件大小的替换。既有采样可用下列命令重算 capture integrity，无需重新进图：

```powershell
python tools/runtime/CodolClientInput.py --summarize-raw <run>\client_input.samples.jsonl --output <run>\client_input.recomputed.json
```

离线 summary 只声明 journal/blob/framing/hash 是否完整，不解释 gameplay。它可以在进程崩溃、Frida detach 或父进程 timeout 后恢复已经写完整的 sample，但不能把原始字节完整等同于 Pmove、snapshot 或 prediction 语义一致。

`--forced-reliable-command` 中的 menu response 必须使用原生四段格式 `mr <serverId> <menuIndex> <response>`；`mr custom3` 只会形成畸形 reliable payload，现由入口直接拒绝。发送 `customN/classN` 前，编排器还会读取当前 prepared character 的 `registered_class_mask`；明确未注册的 class 立即以 `ProtocolFailure` 退出，不自动替换用户选择，也不把“menu 已解析但 loadout provider 无法提交”误报为 gameplay 成功。2026-08-04 的旧 runner build 中 character `0` mask 为 `0x19`，`custom1` 曾进入 `Playing`。production 已绑定 scoped native `PmoveSingle/PM_SetPitchValues` runner、native playerstate-to-entity conversion 和受限 event dispatcher；v6 已验证 character `0/custom2` 能提交到 `Playing` 并持续执行 command，但该 menu response 仍为 `client-native-forced`，不能外推自然 UI 选择。

input probe 现在每 250 ms 原子保存 checkpoint；即使 Frida detach、RPC 或宿主等待卡住，`CodolNaturalMatchTrace.py` 也会在子进程 timeout 后读取最后 checkpoint，保留 parser/usercmd/world 证据。parser 失败以 outer `CL_ParseServerMessage` leave 的 accepted/rejected 为权威，inner playerstate overflow 只作定位观察；报告同时记录 outer enter/leave、packet acceptance 和 `Com_Error`。`CodolNetchanTrace.py` 在观察到 `CL_ExecuteBindingAction` 后临时开启 128 次 playerstate field trace，用于把输入后的首个拒包定位到确切 sparse field 顺序，而不是把 inner reader 的中间 overflow 直接当作整包失败。

运行时工具不承担 Pmove 实现或 conformance 判定。JSON 只描述输入刺激，Frida 只调用 native binding 并保存 opaque evidence；production 的手写 `SV_Pmove`、collision fixture、`.pmt` recorder、自回放和专用 `pmove_core.json` 均已删除。当前只保留 fixed runner 的服务器编排测试，真实 gameplay 必须来自后续 CODOL native shared-Pmove adapter。

父编排器只 gate input dispatch、parser 与独立重算后的 raw journal/blob framing/hash，并明确写 `gameplay_conformance_evaluated=false`。只有 native runner 接入且已有 `Playing` world 后才按单动作或临时 versioned scenario 做定向观察；出现差异再沿 CODOL xref/wire/consumer 增加最小采样，不恢复散落的 Python offset decoder，也不预建通用 offline analyzer。

`.runtime/natural-match/20260803_playerstate_ascending_fix_v2/` 是输入、parser 与 snapshot wire 的历史自动化基线：86 个 packet 全部 accepted 且零 overflow/Com_Error，足以取代旧的“`W` 让客户端主线程停滞”判断；其中 origin/speed 变化来自已删除的手写 movement，不代表当前 production 可移动。

`.runtime/natural-match/20260806_native_pmove_prod_v6/` 是当前 production shared-Pmove 基线。自然 QuickMatch/ready 后使用明确标级的 forced allocation、`custom2` 与四向 binding scenario；input capture 为 44 个连续 sample、44/44 outer packet accepted、零 overflow/`Com_Error`，且没有 native exception 事件。server `commandTime` 持续推进，四段输入都改变 server-owned origin，释放后 server、snapshot 和 prediction 收敛到同一位置；后续同 PID 状态仍保持 received/executed 同步和 20 Hz snapshot。该基线只验证基础四向移动与停止，不覆盖 attack、weapon switch、offhand、stance、mantle 或复杂障碍物。

`.runtime/natural-match/20260802_200239/` 保留为 attack binding、weapon timer fields 和 parser 的历史证据；clip/state 变化来自已删除的手写 `PM_Weapon` 子集，不表示当前 production firing 可用。

`.runtime/natural-match/20260803_weapon_slot_remap_v3/` 是 weapon identity 与最终动态槽基线。frontend 只缓存 staged modular 描述，allocation 后由完整 CCS type table 选定首个动态 weapon slot `352` 并连续注册；forced `custom4` 的 server、snapshot、selected weapon、HUD 与客户端 definition 一致为 primary `354`，不再被原生槽 `289..294` 的 AC130/空投武器覆盖。该运行证明主体和显式附件进入 modular assembly，但当时的 key 没有 `coWeapItemsWEA.csv` 默认组件，不能用来声明原版基底模型完整。

`.runtime/natural-match/20260803_default_weapon_components_v3/` 是当前完整默认组件基线。forced `custom4` 的 M4 key 包含六个 WEA 默认件和红点、握把，客户端原生 definition 读回 `attachment_count=8/model_count=10`；viewmodel trace 列出主体、默认枪口/枪托/握把/导轨/弹匣/机械瞄具、红点、前握把和 reticle，截图显示完整 M4、HUD 与 `30/180` ammo。运行共记录 2117 个 netchan events，reject、overflow 与 `Com_Error` 均为零，且未再出现 AC130 weapon name。QuickMatch/ready/allocation/gamestate/world 仍为自然链路，loadout 为 `client-native-forced`；该结果只覆盖所测 M4/M9 配装，不外推所有武器和效果。

QuickMatch runtime readiness 由 `CodolMatchFlow.py --action frontend` 在单个持久 Frida session 中读取 `0x006F2C10 -> 0x006F0940` 同一批 globals；新建房间前除 config、room、room-service、callback/list 对象范围可读且所需虚函数可执行外，还必须看到 lobby 已 logon、public profile 的 27 个 required chunks 完整且 parse/operation 已结束、startup cinematic 已停止。已存在且至少有一名成员的 room 可以走 `resume`，只补尚未提交的 ready，不重入 QuickMatch。clean launch 从本轮 `ClientLoadTime` telemetry 之前就启动同一 probe，使其能在片头阶段经 `Cbuf_AddText("autocinematic none")` 跳过视频并持续观察真正的 frontend 门槛；client connection state 仍只作诊断。2026-08-01 17:38 已在主大厅 `connection_state=0` 下直接闭环原生 QuickMatch、ready 和 client-native allocation，因此 PVP UI 导航不是生命周期依赖，也不应成为服务器恢复任务。早前黑屏阶段的 `0x3AB8` access violation 只证明浅层 mapped/readable 检查不足，不能证明 state `0` 本身不安全。

`allocation_observed` 只表示客户端进入分配链路；编排器必须继续等待 active client、gamestate update、server-owned snapshot 和客户端 parser 完整返回，不能在房间倒计时或等待连接时提前结束。每轮输出 trace、server samples、截图、分阶段耗时和 `summary.json`；成功、失败与超时路径都必须停止两个 watcher 并保存最终状态。这里的 `success` 只表示当前自然 world/snapshot 捕获边界完整执行，不等同于 authoritative gameplay 已恢复。

`CodolMatchFlow --action full` 的 ready 不是无条件立即调用：先执行 QuickMatch，只有 room 变为 active 且本地成员加入后才调用 `SetReady(1)`；调用各自最多一次，随后必须读回 ready 状态才继续。运行 `20260802_030031` 只有 `match_invoked`，room 在 120 秒内始终未 active，因此没有 `ready_invoked` 并按 timeout 清理；这不表示 ready 自动化丢失，也不能通过回退 UI 导航修复。clean run `.runtime/natural-match/20260802_0651_clean_intro_command/` 在 104.5 秒内以一次 QuickMatch、一次 ready、ready readback 和 `client-native` allocation 完成，真实 parser snapshot/playerstate `13/13`、`overflow_events=0`，稳定窗口达到 `1 full + 91 delta`。排障时先按事件区分“尚未建房”“房间已建但成员未加入”“成员已加入但尚未 ready”。

`references/client_probe/CodolFrameTrace.py` 是相机与渲染节奏的唯一专用只读回归入口。它在 `CG_CalcViewValues` 完成点逐帧统计两帧往返、角度大跳、viewaxis 正交性、roll 持续比例和 predicted-to-refdef 眼高，并在 `view_state` 中保留 predicted `ground/view/link entity` 与 `playerSizeScale`。prediction 聚合还分别统计 predicted 到 `snap/nextSnap` 的距离、`snap -> nextSnap` 距离、snapshot 间隔，以及 snapshot 推进边界帧与普通帧的 refdef 位移、加速度和方向反转；大于 `128` units 的出生/传送 discontinuity 不参与抖动导数。`CodolNaturalMatchTrace.py --frame-trace` 会在输入前等待该 probe 同时报告 `ready/attached`，输入结束后将 summary 收进同一轮 `summary.json`，避免短输入窗口与人工启动 probe 错位。`CodolClientInput.py` 中旧的重复 camera detector 已删除，只保留 scenario 所需的 refdef sample/alignment summary；不要只凭单张截图声明相机稳定，也不要把 origin 的周期下落复位与角度抖动混为一类。2026-08-01 的 entity-reference 与 player-size-scale 修复后，专用 detector 已归零且眼高稳定为 `60`。

clean run `.runtime/natural-match/20260810_movement_jitter_trace_v5/match/` 使用 `release -> forward down 4 s -> up`，先清除出生后的 `pm_flags 0x400` release gate，再完整执行输入；parser `115/115`、accepted `115`、零 reject/overflow/`Com_Error`。566 个 Playing 帧内 snapshot 固定每 `50 ms` 推进，边界帧/普通帧平均位移分别为 `0.361/0.349`，平均加速度为 `0.036/0.026`，两类方向反转均为 `0`，`snapshot_correlated_jitter_detected=false`。因此当前没有证据把移动时第一人称模型的轻微抖动归因于 20 Hz snapshot 周期性回拉；该 probe 尚未测量 viewmodel 自身的 bob/weapon movement transform，也没有施加可重复鼠标转向输入，不能用此结果宣称第一人称模型或鼠标响应已经正常。后续先扩充对应原生表现状态或 look-input 证据，不修改 snapshot 平滑策略掩盖现象。

长流程不能只在结束时输出一行。编排器按 phase 和默认 5 秒 heartbeat 向 stdout flush JSON progress event，并从启动开始原子更新 `summary.json` 的 `outcome=running`、`current_phase`、`last_progress_at` 和当前 counters；checkpoint replace 会重试短暂的 Windows reader contention，stdout pipe 被宿主关闭时也会继续运行并最终写入非 running outcome 与 `current_phase=completed`。checkpoint 只能保留进度，不能主动唤醒 Codex App；Agent 启动后仍应短轮询真实 cell 输出或该文件，一旦 completed、进程退出或 watcher 报错就立即分析，不再用固定长 sleep 或无反馈的 `waiting for events`。

2026-08-01 的 server timeout 验证暴露了一个尚未自动化的边界：`CodolGameServerControl.py --watch-seconds` 从 watcher attach 而非 disconnect trigger 起算，预留 260 秒仍可能在 240 秒 active timeout 前结束。单次验证已用续接 watcher闭环；若需要重复验证，应把 `watcher armed -> native disconnect -> 从 trigger/lastPacketTime 计算 deadline -> active slot 清零后自动停止 -> 保存 summary` 合入 `CodolNaturalMatchTrace.py`，不要继续人工拼固定时长。当前不新增一次性脚本。

2026-07-31 多次 clean-process 运行显示 native allocation 可在约 11 秒到超过 60 秒间出现；一次 60 秒 timeout 截图中房间倒计时只剩 3 秒，因此默认 allocation timeout 已提高到 120 秒，不能为了缩短测试而默认改成 Frida forced allocation。固定 25 秒后置采集也曾在房间倒计时剩余 23 秒时提前停止，现已改为上述 server/client 状态驱动门槛。最终成功 run 用时约 108 秒：prepare 3.5 秒、frontend 23.5 秒、allocation 62.7 秒、到 gamestate 边界并稳定采集 14.3 秒。后续继续用 summary 区分各阶段，只优化有自然链路证据支撑的部分。

从 Agent 或 Python 启动仓库 `.ps1` 时，统一使用参数数组调用 Windows PowerShell：

```text
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File <script> ...
```

不要依赖当前 shell 的 execution policy，不要从外层 shell 直接执行 `.ps1`，也不要把命令拼成需要二次解析的字符串。PowerShell 中不使用 `&&`；多步操作优先拆成独立调用，由编排器检查每一步退出码。

当前 xmake CLI 一次只接受一个 target；分别执行 `xmake build ol_backend`、`xmake build ol_game_server`，不要把两个 target 追加在同一条 build 命令中。

复用当前进程并完成一轮自然捕获：

```text
python tools/runtime/CodolNaturalMatchTrace.py --keep-game-running
```

部署 release、clean launch 并在结束后保留游戏进程时使用 `--install --keep-game-running`。只有明确需要 clean process 或部署新 DLL 时才加 `--clean-launch`/`--install`。

未来 native runner 接入并已有 `Playing` world 后，可做一次定向原生输入取证：

```text
python tools/runtime/CodolNaturalMatchTrace.py --require-active-world --keep-game-running --input-action forward --input-hold-seconds 0.15
```

`--require-active-world` 无进程时直接失败且不启动游戏；三重门槛不能确认复用时也直接失败，不触发 QuickMatch/ready/allocation。该模式不能与 `--clean-launch`、`--install` 或 `--force-client-allocation` 组合。运行成功只表示输入、parser 与 raw evidence 边界完整，不是 server/snapshot/prediction 已一致的结论。

## Weapon movement 回归

`.runtime/natural-match/20260807_weapon_movement_prod_v3/` 是 production weapon-movement 接线后的无攻击回归。当前 profile 只注册 class mask `0x1c`，编排器在 v2 发送前拒绝旧基线的 `custom2`，v3 改用已注册 `custom3` 后完整通过；这是 profile-aware guard，不是 protocol/parser 回归。v3 保存 43 个连续 opaque sample，输入窗口 44/44 packet accepted，零 reject、overflow、`Com_Error` 与 native exception，最终 snapshot/prediction origin 精确一致。该结果只证明新增 gun-angle 阶段未破坏 movement/wire，不证明 FireWeapon 或逐 command gameplay conformance。

## 观察顺序

1. 读取 PID、插件和 server baseline。
2. 挂日志、状态、packet watcher。
3. 确认 watcher armed。
4. 触发自动流程。
5. 等待成功或超时。
6. 读取最终 server state 后再 detach。

游戏可以在多轮测试间保持运行。只有部署新 DLL、状态无法复位、崩溃或测试要求 clean process 时才重启。

## 2026-08-03 自动化边界更新

clean launch 偶发出现 lobby 已 logon、QuickMatch objects 已 ready，但 PublicProfile 长时间停在 `chunk_mask=0/operation=1/parsed=false`。backend 已有 `CODOL_RequestInventoryRefresh` export；实跑中请求后 refresh generation `1` 从 queued 进入 succeeded，客户端随即恢复到 `chunk_mask=0x7ffffff/operation=0/parsed=true`。`CodolMatchFlow` 现只对这一精确停滞签名等待 10 秒后请求一次，不对普通 lobby 登录、profile operation `0` 或其他失败状态盲目重试。

forced allocation 现会在 `ready_confirmed` 的同一次 UI-thread drive 中调用 `startGame`，避免依赖下一次 message dispatch。但 `.runtime/natural-match/20260803_character_viewhands_v4/` 仍在调用后约 55 秒才看到客户端真正 connect；这说明 room `SetReady(1)` 的本地 readback 尚不等于后端确认 ready，不能把 pipeline 标成完整 working。该运行最终仍成功完成 `frida-forced` allocation、gamestate、world、forced `custom3` 与 viewmodel trace；后续 ready 修复应回到 backend/room event ownership，不重新研究 PVP UI 导航。

health/damage 验证现由三层诊断共同读取：`CODOL_GameServerGetWorldPlayerHealthStatus` 暴露 server-owned current/max health 与 damage 四元组，`CodolNetchanTrace.py` 记录每次真实 parser commit，`CodolCgameState.py` 同时读取 snapshot/next snapshot/predicted state。clean run `.runtime/natural-match/20260804_health_spawn_v1/` 三层一致为 `100/100` 和四项零值，playerstate parser 零 overflow；截图仍有紫红边缘，故视觉 overlay 不进入 health wire 的成功判据。

`CODOL_GameServerGetWorldEventStatus` 现保留当前 world 的最后一个 authoritative transition，避免 250 ms/500 ms watcher 错过单帧 spawn notify。clean run `.runtime/natural-match/20260804_spawn_notify_v1/` 在 Playing 后读回唯一 `client_spawned sequence=1/spawnSequence=1/spawnGeneration=1`，后续 snapshot 持续推进但 sequence 不变；该 checkpoint 用于诊断与压缩恢复，脚本运行时仍应直接消费同帧 `SvServerWorld::frameEvents()`。

## 2026-08-08 modular weapon 回归

`CodolNaturalMatchTrace.py --force-client-allocation` 现在在启动 QuickMatch 前等待 server `loadout_preparation.prepared=true`、当前/已准备角色一致且至少一套 class 已注册；默认有界等待 45 秒，可用 `--loadout-prepare-timeout` 调整。该门槛只约束会跳过自然倒计时的 forced allocation，不改变自然 allocation 或 active-world 复用语义。clean run `.runtime/natural-match/20260808_weapon_dependency_cache_prepared_v12_retry/` 在角色 `3`、attempt `17`、mask `31` 后才进入匹配，随后以真实 client cgame resolver 证明动态 weapon `352..360` 连续，parser `42/42`、零 overflow/`Com_Error`，active client 和 snapshot world 均建立。

同 PID 的后续只读状态还确认用户自然选择的 `custom1` 已进入 `Playing`，primary/secondary 为 `353/354`，当前 weapon `353`、clip `6`，与客户端“自由 黑金”截图一致。约 150 秒后 ingress 的 accepted packet 停在 `4256`，后续拒绝开始累积，主要原因为 usercmd command time 非递增，之后又出现 invalid fragment，ack 不再推进并最终退出。该现象是下一项长时 netchan/usercmd 稳定性调查，不归因于 modular registry，也不能用重发 loadout 或 UI 操作掩盖。
