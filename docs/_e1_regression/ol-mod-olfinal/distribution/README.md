# CODOL 3.3.3.3 运行分发基线

本目录定义 `ol-mod` 的权威 CODOL-only、x86 运行 overlay。它不是完整游戏包，也不包含游戏主程序；`tools/distribution/StageCodolRuntime.ps1` 会把本目录中的闭源兼容组件、`assets/` 中的 title `1004` 资产和当前 xmake 构建产物合并到 `build/stage/codol`。

游戏 EXE 不纳入此基线。当前活动 EXE 和 `patched/` 候选的字节不同；它们只是不同测试对象，不能仅根据此前某轮连接稳定性把任一版本声明为权威。涉及客户端地址、patch 或时序的运行记录必须同时记录实际 EXE SHA-256。

## 组件选择

继续归档使用的 Project Nova 组件：

- `Injector32.exe`：目前最稳定且已验证的注入方式；启动时不给游戏添加参数。
- `Bootstrapper32.dll`：Injector 注入后的固定 bootstrap ABI。

始终使用本仓库构建产物：

- `ol_localnetworking` -> 运行时兼容名 `Localnetworking.Ayria32`。
- `ol_platformwrapper` -> 运行时兼容名 `Platformwrapper.Ayria32`。
- `ol_backend` -> 运行时兼容名 `Alwaysoffline.Localnet32`。
- `ol_game_server` -> `CodolGameServer.Localnet32`。

`ol_localnetworking` 保持归档组件的三个 lifecycle export、六个 Winsock hook、
`.Localnet32/Createserver` 加载合约和 2019 `IServer::Endpoints` vtable ABI。运行根目录
从当前 DLL 所在的 `Plugins` 目录推导，因此源码内不绑定 `./Ayria`；分发目录仍保留
`Ayria` 名称以兼容尚未源码化的 Injector 和 Bootstrapper。

`ol_platformwrapper` 以 2019 Platformwrapper 为结构基底，只恢复 CODOL 已静态确认使用的
Tencent `Invoke`、TerSafe `CreateObj`、CrossShell `InitCrossContextByOpenID` 和三个插件
lifecycle exports，不迁移没有 CODOL 消费证据的 52 个 Steam 通用 exports。当前归档 DLL 的
15-slot Tencent vtable、字符串缓冲区长度语义、TerSafe 6-slot vtable、字段写入和精确
`sizeof(Interface000)=0x858` 已通过 i64 核对；构建物的 PE32、exports、配置迁移、Tencent tag
和 TCLS shared-memory lifecycle 已有离线回归。clean 自然替换又闭合 Auth/frontend、QuickMatch、
ready、client-native allocation、`mmbook/mmstart`、`SessionStart`、world 和 snapshot；归档 DLL
仍保留在 `distribution/legacy` 作为固定哈希回退证据。

明确排除：

- 所有 x64 文件和 title `1004` 以外的资产。
- 归档 `Alwaysoffline.Localnet32`，因为已由 `ol_backend` 替代。
- `CODOLBackend.Ayria32`。它属于旧热加载实验，运行日志显示其对未知 dispatcher build 拒绝 hook；当前 backend 已直接实现 inventory/Marketplace 链路。
- 当前游戏目录中的 Logs、Backups、IDA 文件、缓存、身份覆盖和实验副本。

## 资产与玩家状态

`assets/backend/1004` 包含从 `ayriax3/1/Ayria` 逐哈希核对的 Cloud/Server 资产，以及项目维护的 `MarketplaceSkus.json`。这些文件按不可变 backend 输入管理。

`assets/profile_seed/1004` 单独保存原版 `Publicprofile` 和 `the.json`。它们在运行后会变化，因此安装策略是 `if-missing`：空白安装会得到可用初始状态，更新插件或资产时不会覆盖现有玩家配置。`Inventory.json` 是当前重建 backend 的持久化 backing store，不是归档游戏资产；它由运行时按需创建，不进入初始 seed。

`assets/game_scripts` 是 dedicated authoritative gameplay 的项目资产，按 `replace` 安装到 `Ayria/Assets/OlMod/GameScripts`。运行时只按固定顺序读取 `common.lua`、`gametypes/<gametype>.lua` 和 `maps/<map>.lua`，map/gametype 必须通过 booking 名称约束；Lua 不获得任意路径或文件系统访问能力。当前首个生产脚本是 SD map gameobject allow-list，其他模式在脚本缺失时保留带标签 brush inactive 的保守状态。

运行目录中的职责边界固定为：

- `Ayria/Assets/Alwaysoffline/1004/Server`、`Cloud` 和 `MarketplaceSkus.json`：backend 输入。
- `Ayria/Assets/Alwaysoffline/1004/<user-id>`：backend 持久化状态，安装器默认不覆盖；其中 `Identity.json` 持有该账号的权威 `displayName`。
- `Ayria/Assets/Alwaysoffline/Identity.json`：仅作为尚无玩家 identity profile 时的首次迁移种子；认证创建玩家档案后，修改该文件不会改动既有账号名字。
- `Ayria/Assets/Platformwrapper/Platform.json`：客户端 platform ID、CODOL title 和认证 endpoint 兼容配置；不是 backend 或 dedicated 状态。旧 `UserID.txt` 只在该文件缺失或未指定 platform ID 时作为迁移输入。显示名仍由 backend 的玩家档案持有，`Username.txt` 不参与权威身份。

旧 `Ayria/Assets/CODOLBackend`、手工 `.bak` 和 `Publicprofile-test` 不属于 live manifest。清理时先确认归档价值：废弃插件资产可移出运行目录；玩家快照不可删除，只能迁入明确的测试归档位置。dedicated 不得扫描这些目录猜测玩家状态。

## 生成与安装

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\distribution\StageCodolRuntime.ps1

powershell -ExecutionPolicy Bypass -File .\tools\distribution\InstallCodolRuntime.ps1 `
  -GameDirectory "E:\path\to\CODOL_Experience_V3.3.3.3_FULL"
```

Stage 每次从干净来源重建 `build/stage/codol`，验证归档文件哈希、PE32 架构、title 范围和禁用组件，并生成 `ol-mod-runtime-manifest.json`。Install 只复制 manifest 管理的文件；仅显式传入 `-ReplacePlayerState` 才会覆盖 profile seed。
