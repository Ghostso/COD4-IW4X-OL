# 工具分类

- `runtime`：当前运行时控制、Frida 环境、匹配和状态观察。
- `profile`：玩家 profile、库存、商城和可视化编辑器。
- `reverse`：IDA/idalib 批处理、函数检查与 annotation。
- `distribution`：从受控源生成 CODOL-only x86 runtime，并安装且默认保留玩家状态。
- `build.ps1`：统一的 Xmake/MSVC/vcpkg 构建入口。

工具行为与运行约束统一见 [`.agents/modules/runtime.md`](../.agents/modules/runtime.md)，这里不维护迁移状态或兼容链路副本。
