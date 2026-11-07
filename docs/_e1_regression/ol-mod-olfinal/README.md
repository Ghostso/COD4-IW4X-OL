# ol-mod

`ol-mod` 用于恢复《使命召唤 Online》QA 客户端离线运行所需的控制面与游戏服务器链路。仓库只保留继续开发需要的源码、测试、资产和工具；旧 Ayria/Project Nova 名称仅在插件 ABI、固定加载路径或历史证据需要时保留。

## 目录

```text
src/backend/              DW3 控制面插件
src/game_server/          游戏服务器与协议实现
tests/                    对应模块的自动化测试和 fixtures
assets/backend/1004/      CODOL 后端资产
assets/profile_seed/1004/ 原版初始玩家状态，仅缺失时安装
distribution/             CODOL-only x86 分发契约与闭源兼容组件
tools/runtime/            运行时观察和原生客户端流程自动化
tools/distribution/       干净 staging 与保留玩家状态的安装工具
tools/profile/            Profile、库存和商城工具
tools/reverse/            IDA/idalib 分析与注释工具
references/client_probe/  历史客户端伪链路和协议探针
docs/references/          带来源归属的外部文章、翻译和参考资料
docs/devlog/              面向人类读者的中文开发历程
.agents/                  Agent 约束、当前状态和研究文档
```

## 构建

要求：

- Windows x86
- MSVC
- Xmake 3.0.9 或更新版本
- vcpkg `x86-windows-static` OpenSSL

本机默认使用 `D:\Program Files\xmake\xmake.exe` 和 `E:\Source\Repos\Main\vcpkg`；也可以通过 `PATH` 与 `VCPKG_ROOT` 覆盖。

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action build -Mode release
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action test -Mode release
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action stage -Mode release
```

构建产物位于 `build/bin/<mode>`。逻辑目标使用新命名：

- `ol_backend` -> `AlwaysofflineRe.Localnet32`
- `ol_game_server` -> `CodolGameServer.Localnet32`

最终兼容文件名暂时不能更改，因为源码化 Localnetworking 的插件发现 ABI 和现有游戏目录仍依赖这些固定名称。

迁入代码中的 `AlwaysofflineRe`、`CodolGameServer` namespace 也暂时原样保留，以保证首个 xmake 基线可以逐文件验证。后续可在独立、行为不变的提交中逐模块改名，避免把命名重构与协议修复混在一起。

## 运行分发

`build/stage/codol` 是由 manifest 驱动生成的游戏目录 overlay，只包含 title `1004`、PE32 组件和必要资产。闭源 Injector/Bootstrapper/Platformwrapper 来自已核对的 `ayriax3/1` 原版；Localnetworking、backend 与 game server 使用当前构建产物。详见 [`distribution/README.md`](distribution/README.md)。

安装到游戏目录时，已有 `Publicprofile`、`the.json` 和后续运行时创建的 `Inventory.json` 默认不会被覆盖：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\distribution\InstallCodolRuntime.ps1 `
  -GameDirectory "E:\path\to\CODOL_Experience_V3.3.3.3_FULL"
```

## 协作与文档

Agent 的工作约定、证据等级、当前 handoff 和文档归属统一维护在 [`.agents/AGENTS.md`](.agents/AGENTS.md) 与 [`.agents/README.md`](.agents/README.md)。根 README 不复制这些规则。

外部参考文章与中文翻译从 [`docs/references/`](docs/references/) 进入；经过取舍的项目开发历程从 [`docs/devlog/`](docs/devlog/) 进入。它们面向阅读和复盘，不替代 `.agents/modules/` 中的当前实现边界。
