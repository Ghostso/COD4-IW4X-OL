# CODOL 客户端

面向《使命召唤 Online》（CODOL）1649370 版本的离线客户端运行与本地档案适配。

客户端通过 Python 宿主、固定版本原生适配、离线守卫和资源库组织运行环境。当前支持本地离线适配，尚未实现多人联机及完整对局闭环。

## 当前能力与边界

| 方向 | 当前状态 |
| --- | --- |
| 离线启动 | 已有固定版本镜像、启动预检、会话目录装配和临时断网守卫 |
| 本地账号 | 已有 SQLite 档案持久化、昵称、配装及游戏设置保存逻辑 |
| 本地商城 | 已有 GP/CP 购买、单品及礼包、库存与余额事务保存逻辑 |
| 原生 UI | 已有角色预览、大厅导航、本地房间及改名等适配，具体验收状态见变更记录 |
| 分析工具 | 提供输入版本校验、独立副本、PE 恢复及 Fastfile、资源分析入口 |

已有实现和历史测试通过不等于当前版本已完成实机验收。尤其是重构后的页面、角色展示、退出重启和完整游戏流程，应以[问题解决与变更记录](docs/client-issue-resolution-log.md)及对应验证报告为准。

新建账号使用当前初始化策略：保留满级及进度条件，按商城及排位赛荣誉渠道筛选初始授权；GP 初始值为 20 亿，CP 为 10 万。已有的历史全解锁账号保留原行为。具体授权、数量及购买规则见[客户端架构设计](docs/client-code-architecture.md)；启动脚本中的 “Full-Unlock” 字样不代表所有新账号无条件全解锁。

## 目录结构

```text
client/
├── start_client.cmd        Windows 离线启动入口
├── run.py                  版本预检与离线分析入口
├── requirements.txt        Python 依赖
├── src/codol_rebuild/      客户端生产源码
├── native/                 原生守卫源码
├── tools/                  启动及资源准备工具
├── tests/                  正式自动化测试与固定夹具
├── bin/                    固定运行程序和组件
├── resources/              固定版本运行资源
├── data/accounts/          本地账号、档案与设置
├── workspaces/             运行会话、缓存和构建中间材料
├── manifests/              输入版本清单
├── licenses/               组件许可材料
└── docs/                   架构与变更记录
```

客户端源码按 `application`、`adapters`、`resources`、`platform`、`runtime`、`bootstrap`、`analysis` 和 `core` 分层。依赖方向与模块职责以[客户端架构设计](docs/client-code-architecture.md)为准。

## 环境准备

- **系统**：Windows。实际运行依赖 Win32 API、低权限令牌、目录联接及原生组件。
- **Python**：现有启动脚本固定使用 `C:\Python314\python.exe`。以下命令沿用此路径；使用其他安装路径时，可直接调用 Python 启动入口。
- **输入与资源**：需要匹配 1649370 的输入文件、固定离线镜像、守卫、补丁记录及已准备好的资源库。仅有 Python 源码和依赖不能完成启动。

在 `client/` 目录打开 PowerShell，安装依赖：

```powershell
& C:\Python314\python.exe -m pip install -r .\requirements.txt
```

运行前确认至少存在以下内容：

```text
bin/v1649370/codol1649370-offline.exe
bin/offline_guard.exe
resources/v1649370/offline-menu-patches.json
resources/v1649370/offline-resources/
resources/v1649370/offline-image-library/
resources/v1649370/offline-loose-library/
```

镜像和补丁会进行固定指纹检查，不可用其他版本文件直接替换。资源来源、准备流程及清单约定见[固定版本运行资源](resources/v1649370/README.md)，镜像说明见[离线运行基底](bin/v1649370/README.md)。

## 启动客户端

以下命令均在 `client/` 目录执行。

### 1. 校验输入版本

```powershell
& C:\Python314\python.exe -B -X utf8 .\run.py check
```

此命令按 `manifests/build1649370.json` 校验关键输入，不启动游戏。

### 2. 检查启动计划

```powershell
.\start_client.cmd --dry-run
```

`--dry-run` 检查必要文件、镜像指纹、补丁和宿主参数，显示启动计划；不创建运行会话、不启动客户端，也不请求 UAC。它不等同于完整资源校验或实机验收。

### 3. 正式启动

```powershell
.\start_client.cmd
```

也可双击 `start_client.cmd`。脚本默认启用本地档案，并使用固定图片库与松散资源库，运行到关闭客户端或发生致命错误。

启动过程中临时断网守卫可能请求 UAC，Python 宿主保持当前用户权限，客户端使用低权限令牌。守卫未就绪时不会恢复客户端执行。

需要使用其他 Python 路径时，可按以下参数直接调用启动工具：

```powershell
& C:\Python314\python.exe -B -X utf8 .\tools\launch_offline.py `
  --resource-library .\resources\v1649370\offline-image-library `
  --loose-library .\resources\v1649370\offline-loose-library `
  --local-profile
```

常用参数可追加到启动脚本后：

| 参数 | 用途 |
| --- | --- |
| `--dry-run` | 仅检查并显示启动计划 |
| `--prepare-only` | 准备运行目录但不运行游戏；会产生准备产物 |
| `--verify-resources` | 强制对资源进行 SHA-256 全量复核 |
| `--seconds 60` | 执行有时限的诊断运行，允许范围为 1～600 秒 |

完整参数说明：

```powershell
& C:\Python314\python.exe -B -X utf8 .\tools\launch_offline.py --help
```

## 档案、资源与日志

- **持久数据**：`data/accounts/` 保存账号、档案和游戏设置。备份本地进度时应保留此目录。
- **会话产物**：每次实际运行在 `workspaces/offline-runs/<会话名>/` 中保存独立程序副本、配置及诊断产物；启动输出会给出对应目录。
- **固定资源**：`resources/v1649370/` 提供基础覆盖层、图片库和模型音频等松散资源库。
- **共享缓存**：`workspaces/offline-resource-cache/` 由已验证资源库生成，清理前须考虑已有会话引用。

不要直接修改固定离线镜像。宿主会先将其复制到会话目录，再应用运行补丁。`workspaces/` 还包含资源输入副本和提取中间材料，不能整体当作可丢弃缓存；清理会话时也不能递归穿过资源目录联接。详见[工作目录说明](workspaces/README.md)。

## 自动化测试

正式测试及固定夹具位于 `tests/`，覆盖账号、档案、资源、原生适配及架构边界等内容。

**当前测试入口存在文档与文件不一致**：测试文档约定使用 `test.py`，但编写本 README 时该文件不存在，因此这里暂不提供该入口的运行命令。测试组织与环境依赖见[客户端自动化测试](tests/README.md)。

部分测试依赖 Windows API、原生镜像、资源和捕获数据，不能视为任意环境下均可运行的纯单元测试。历史测试通过不代表当前版本已重新通过验证，也不代表实机功能验收完成。

## 离线分析

`run.py` 是分析入口，游戏启动使用前述启动脚本。可通过以下命令查看各专题工具：

```powershell
& C:\Python314\python.exe -B -X utf8 .\run.py --help
& C:\Python314\python.exe -B -X utf8 .\run.py fastfile --help
& C:\Python314\python.exe -B -X utf8 .\run.py bootstrap --help
& C:\Python314\python.exe -B -X utf8 .\run.py assets --help
```

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [客户端架构设计](docs/client-code-architecture.md) | 模块边界、账号策略、运行装配与依赖方向 |
| [问题解决与变更记录](docs/client-issue-resolution-log.md) | 历史问题、实施记录、证据与验收限制 |
| [固定版本运行资源](resources/v1649370/README.md) | 资源内容、准备流程与清单约定 |
| [离线运行基底](bin/v1649370/README.md) | 固定镜像来源、指纹与使用方式 |
| [客户端自动化测试](tests/README.md) | 测试范围、夹具与环境依赖 |
