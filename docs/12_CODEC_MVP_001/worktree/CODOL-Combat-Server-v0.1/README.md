# CODOL Combat Server v0.1

用现有 CODOL 客户端与资源实现的**独立战斗服务器第一版**。
协议不来自"假设 COD4X/IW4x 与 CODOL 相同"，而来自**真实客户端抓包的字节**。

> 交付报告: [../V0_1_IMPLEMENTATION_REPORT.md](../V0_1_IMPLEMENTATION_REPORT.md)
> 验收对照: [../V0_1_ACCEPTANCE_MATRIX.md](../V0_1_ACCEPTANCE_MATRIX.md)

---

## 快速开始

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"

# 可重复构建（需要 Windows 自带的 csc.exe，不联网、无第三方依赖）
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1

# 全部自动化测试（退出码 0 = 全绿）
.\build\bin\CODOLCombatServer.exe --selftest

# 启动战斗服主循环
.\build\bin\CODOLCombatServer.exe --run
```

> ⚠️ `--run` 会绑定 UDP 28960 并运行战斗服主循环。**本版从未获得真实客户端连接**
> （见验收矩阵 AC-4），因此它验证的是"服务端自身能跑"，**不是**"能进可玩战斗"。

## 命令

| 命令 | 作用 |
|---|---|
| `--run` | 启动战斗服主循环（默认） |
| `--selftest` | 离线自测：复放真实抓包字节，**不需要游戏与网络** |
| `--print-protocol` | 打印实机核实过的协议常量 |
| `--print-session` | 打印本服将下发的权威会话描述符字节 |
| `--export-session` | 把描述符落盘到 `session_descriptor/` |
| `--config <path>` | 指定配置文件（默认 `config/combat_server.cfg`） |
| `+set <key> <value>` | 覆盖任意配置项 |
| `--help` / `--version` | 帮助 / 版本 |

## 目录结构

```
src/Program.cs                入口与命令行
src/ServerHost.cs             初始化阶段机 / 生命周期 / 主循环
src/Engine/GameWorld.cs       地图与游戏模式初始化、权威帧推进
src/Engine/ClientLogic.cs     会话协议：解码 -> 权威更新 -> 快照编码
src/Engine/ServerConfig.cs    配置（含行内注释支持）
src/Engine/SessionExporter.cs 权威会话描述符导出
src/Codol/CodolProtocol.cs    协议常量与各阶段编解码
src/Codol/MotionSnapshot.cs   位级快照编码（index-skip）
src/Codol/SessionDescriptor.cs 会话描述符（地址下发通道）
src/Codol/SessionGolden.cs    黄金向量（自动生成，勿手改）
src/SelfTest.cs               离线自测（8 个分节，122 项断言）
tests/gen_session_golden.py   黄金向量生成器
config/combat_server.cfg      最小战斗启动配置
docs/                         许可证政策、工具链探测、证据日志
```

## 权威会话描述符（本版新增，重要）

客户端"去哪台战斗服"的地址**不由** `mmbook accepted` 下发，而由
**21/5 findSessions 的 session 对象**下发（证据见
[`DEV-BOOKING/MVP-PVE-MATCH-ENTRY-009.md`](../DEV-BOOKING/MVP-PVE-MATCH-ENTRY-009.md) §8）。
那个对象里还夹带 **16B securityKey**，是 ECDH 派生的一半输入 ——
**两侧不一致 = 传输密钥不同 = 连上也会静默丢包**。

因此本服把描述符作为**自己的、可校验的产物**导出：

```
build/bin/session_descriptor/
  session_record_258.bin      258B matchmaking session 记录
  mission_normal.bin          21/5 普通 mission session 对象
  mission_firingrange.bin     21/5 靶场 mission session 对象
  battle_security_key.txt     16B securityKey（hex）—— 大厅必须用这一份
  endpoint.txt                ip:port —— 客户端将连到这里
  session_descriptor.json     元数据 + SHA-256
```

**大厅应直接消费该目录**，而不是各自硬编码 IP / 端口 / 密钥。

相关配置（见 `config/combat_server.cfg`）：
`session_endpoint` · `session_addr_layout` · `session_map` · `session_gametype` ·
`session_maxplayers` · `session_currentplayers` · `session_playlist` · `session_export_dir`

启动时会校验"会话端点 == 实际监听端点"，不一致直接报 `ERROR`（不静默）。

## 重建黄金向量

描述符字节固化在 `src/Codol/SessionGolden.cs`，由生成器从**已冻结的参考实现**
`REF_LOBBY_KIT/codol_crypto.py` 产出（禁止手工编辑）：

```powershell
python -X utf8 tests\gen_session_golden.py
```

长度不符时生成器**拒绝写出**（防止悄悄漂移）。

## 当前能力边界（务必阅读）

**已实现且自证**：协议握手全链、会话生命周期、玩家命令解析、权威运动学帧循环、
game state 下发、位级快照编码、权威会话描述符、可重复构建（以源码指纹形式可断言）、
122 项自动化测试。

**未实现 / 未验证**：
- ❌ **CODOL 客户端从未连上本服**（`收包=0`）—— 这是唯一真正的阻塞点
- ❌ 活体玩家命令（目前只离线复放真实抓包字节）
- ❌ 地图 BSP / Clip 真实碰撞与视线
- ❌ 弹道 / 伤害 / 命中判定
- ❌ PvE booking 应答格式（靶场信封已否证）
- ❌ 进入可玩战斗

## 许可证

本版为**零第三方依赖**的独立实现。
CoD4x_Server（AGPL-3.0）与 iw4x-client（GPL-3.0）**均未复制源码**，
仅作架构分层与否定性结论的阅读参考。详见
[LICENSE_POLICY_REUSE.md](docs/LICENSE_POLICY_REUSE.md)。
