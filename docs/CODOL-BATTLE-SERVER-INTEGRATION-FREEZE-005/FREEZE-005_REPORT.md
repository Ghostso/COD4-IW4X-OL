# CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005 冻结候选报告

**报告状态：PASS（仅限“服务端集成冻结候选基线”）**  
**验证日期：2026-10-13（Asia/Shanghai）**  
**正式代码主线：** `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1`  
**源码指纹：** `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`  
**源码文件数：** 25（`src/**/*.cs`）  
**Release 产物 SHA-256：** `0c0a4bc13325f6c9dc6d9abd9d2197efc41612029c0bf8627f3b752c299943ee`

> 结论边界：本轮只验证服务端自身的构建、自测、指纹、有限时启动、UDP 绑定和停机清理。
> **没有执行真实 CODOL 客户端端到端验证**，因此不得宣称“已实现客户端互通”或“可进入游戏”。
> 本基线最多只能称为“服务端集成冻结候选基线”。

---

## 1. 验收结论

| 验收项 | 结果 | 证据 |
|---|---|---|
| Release 构建成功 | PASS | `evidence/build.console.utf8.log`、`evidence/build.exitcode.txt` |
| 完整 `--selftest` 全部通过 | PASS，251/251，失败 0 | `evidence/selftest.stdout.log`、`evidence/selftest.exitcode.txt` |
| `--fingerprint` 与源码一致 | PASS | `evidence/fingerprint_evidence.json` |
| `--run --max-seconds 3` 成功 | PASS，退出码 0 | `evidence/run_maxseconds.stdout.log`、`evidence/run_observation.json` |
| UDP 绑定 | PASS，真实观察到 PID 绑定 `127.0.0.1:28960` | `evidence/run_observation.json` |
| 自动停机 | PASS，约 3.019 秒后触发 | `evidence/run_maxseconds.stdout.log` |
| 会话/实体清理 | PASS，`sessions=0 entities=0` | `evidence/run_maxseconds.stdout.log` |
| 源码前后未变化 | PASS，25/25 文件、清单差异 0、监视事件 0 | `evidence/inventory_comparison.txt`、`evidence/source_watcher.log` |

## 2. 受控冻结窗口

- 窗口开始：`2026-10-13T12:43:39.8896755+08:00`
- 窗口结束：`2026-10-13T12:44:33.2673168+08:00`
- `src/**/*.cs` 现有源文件全部以 `FileAccess.Read + FileShare.Read` 打开，外部写入/删除被 Windows 共享模式拒绝。
- `src` 上启用了持续 `FileSystemWatcher`，监视 `Created`、`Changed`、`Deleted`、`Renamed`。
- 30 秒静止等待期间及整个构建/自测/运行期间：**0 个源文件事件**。
- 验证前后清单逐项比较：**25 -> 25，差异 0**。
- 锁释放后再次独立采样：25 个文件，指纹仍为 `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`，差异 0。
- 正式主线不是 Git 仓库；本轮未依赖 Git 提交号，改以文件锁、文件监视器和 SHA-256 清单证明冻结窗口。

## 3. 源码指纹定义

计算范围固定为：

- 纳入：`CODOL-Combat-Server-v0.1\src\**\*.cs`
- 纳入数量：25
- 忽略：`build/**`、`logs/**`、`docs/**`、`config/**`、`tests/**`、生成二进制、历史证据目录、交付目录
- 排序：相对于 `src` 的路径使用 `/` 归一化，按 `.NET StringComparer.Ordinal` 排序
- 哈希输入：对每个文件依次写入 `UTF-8(relative_path)`、`0x00`、原始文件字节
- 摘要：SHA-256，64 位小写十六进制

```
SOURCE_SHA256=5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf
```

该算法与程序内 `BuildFingerprint.Compute`、`--fingerprint` 输出和 Release `BUILD_MANIFEST.txt` 记录值完全一致。

## 4. Release 构建

命令（工作目录为正式主线）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
```

结果：

- 配置：`release`
- 编译器：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`
- 源文件：25
- 退出码：0
- 结果行：`BUILD OK`
- 告警：1 条 `CS0675`（`src\Codol\ClientCommandReader.cs:213`）；为编译告警，不影响本轮构建成功判定。
- 产物：`build\bin\CODOLCombatServer.exe`，188416 字节
- 产物 SHA-256：`0c0a4bc13325f6c9dc6d9abd9d2197efc41612029c0bf8627f3b752c299943ee`
- 原始重定向日志为 CP936 字节；保留原始日志并另存 UTF-8 解码副本 `evidence/build.console.utf8.log`。

## 5. 完整自测

命令：

```powershell
build\bin\CODOLCombatServer.exe --selftest
```

结果：

- 退出码：0
- `[OK]`：251
- `[FAIL]`：0
- 摘要：`通过 251 项，失败 0 项。`
- 最后结果：`全绿。`

## 6. 指纹命令复核

命令：

```powershell
build\bin\CODOLCombatServer.exe --fingerprint
```

结果：

```text
SOURCE_FILES=25
SOURCE_SHA256=5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf
```

退出码：0。该值同时等于验证前清单指纹、验证后清单指纹和 `BUILD_MANIFEST.txt` 中的 `source_sha256`。

## 7. 有限时运行与停机清理

命令：

```powershell
build\bin\CODOLCombatServer.exe --run --max-seconds 3
```

运行观察：

- 退出码：0
- PID：10984
- 实际 UDP 监听被独立确认为：`127.0.0.1:28960`
- 监听 socket 的 `OwningProcess`：10984
- 主循环统计：`frames=101 ticks=100`，约 `3019ms`
- 自动停机行：`达到 max-seconds=3 -> 请求停止（自动退出）`
- 清理行：`停机清理自检通过: sessions=0 entities=0`
- 进程退出后再次查询 UDP 28960：端点数量 0
- 当前 `CODOLCombatServer.exe` 进程数量：0

## 8. 已验证 / 未执行 / 未解决

### 已验证

- 当前 25 个 C# 源文件在受控窗口内未被写入。
- Release 构建成功。
- 完整离线自测 251/251 通过。
- 源码清单、源码指纹、EXE 内报告指纹和构建清单一致。
- 服务端可启动并真实绑定 UDP 28960。
- 有限时运行可自动停止。
- 停机后会话和实体计数归零，UDP 端点释放。

### 未执行

- 真实 CODOL 客户端连接本服。
- 客户端端到端握手、进入地图、生成实体、收发快照或完成可玩战斗。
- 活体玩家输入、弹道、伤害、命中、BSP/Clip 碰撞和视线验证。

### 未解决 / 保留风险

- `CS0675` 编译告警仍存在；本轮未修改源码。
- 运行时报告未找到地图资产目录，服务端仅按配置启动；这不等价于客户端可加载地图。
- `codol2697` 的 snapshot 帧边界/delta 基准仍标记为 BLOCKED。
- 本机 .NET Framework 4.0 `csc.exe` 不支持 `/deterministic`；二进制 SHA-256 可能随编译变化，基线可重复性以源码指纹和 `BUILD_MANIFEST.txt` 为准，不宣称 EXE 逐位可复现。
- 交付目录是冻结候选证据包，不修改任何原始游戏文件、历史冻结基线或原始逆向证据。

## 9. 关键证据文件

- `attempt_01_20261013_124339/attempt_result.json`
- `attempt_01_20261013_124339/evidence/source_inventory_pre.tsv`
- `attempt_01_20261013_124339/evidence/source_inventory_post.tsv`
- `attempt_01_20261013_124339/evidence/source_fingerprint_pre.json`
- `attempt_01_20261013_124339/evidence/source_fingerprint_post.json`
- `attempt_01_20261013_124339/evidence/fingerprint_evidence.json`
- `attempt_01_20261013_124339/evidence/inventory_comparison.txt`
- `attempt_01_20261013_124339/evidence/source_watcher.log`
- `attempt_01_20261013_124339/evidence/build.exitcode.txt`
- `attempt_01_20261013_124339/evidence/build.console.utf8.log`
- `attempt_01_20261013_124339/evidence/selftest.exitcode.txt`
- `attempt_01_20261013_124339/evidence/selftest.stdout.log`
- `attempt_01_20261013_124339/evidence/fingerprint.exitcode.txt`
- `attempt_01_20261013_124339/evidence/fingerprint.stdout.log`
- `attempt_01_20261013_124339/evidence/run_maxseconds.exitcode.txt`
- `attempt_01_20261013_124339/evidence/run_maxseconds.stdout.log`
- `attempt_01_20261013_124339/evidence/run_observation.json`
- `attempt_01_20261013_124339/evidence/BUILD_MANIFEST.snapshot.txt`
- `attempt_01_20261013_124339/evidence/artifact.sha256`
- `attempt_01_20261013_124339/evidence/supporting_inputs.tsv`
- `attempt_01_20261013_124339/artifacts/CODOLCombatServer.exe`

## 10. 支持输入清单（不属于源码指纹，但已单独记录）

- `build/build.ps1` — `fef2c68366e6bb5a2fefbd551e04b0a452d3f05eb66166f470cfebfb2a6c0bf6`
- `config/combat_server.cfg` — `72206a7007c6b01dadbcaf18f538f545fbb78514d83fa51f463cf4f38607a723`
- `config/firingrange-gamestate.bin` — `020f20c9464d3dadeea9dce8432270ab2e9041c60674cc441a9774b4a33edbc4`
- `README.md` — `fd884a21b114e52984f65cfd340d7924a5b23c2cbf0b92b8aaa112aa41ba43a1`
- `tests/gen_golden_snapshot.py` — `d85650cc4aaf1454fced94d92c5697623f791c4b9fc85eaec2bdc7c15d93fb3e`
- `tests/gen_session_golden.py` — `d386cc569a22108ff1d1960b3fe8258514ac0cf2dba9fec0126ea15a7ca73ad2`
- `tests/golden_first_snapshot.hex` — `d90ae1b4982420d265d117364ff0d4dc8a1a4524758474eb662ef2a4283066b6`

## 附录 A：源码文件清单与 SHA-256（25 项）

- `Codol/Aes128.cs` — `999277876d728e9f800dd388f814d2a87cf97471bf35ebcc176e88d9674f422d`
- `Codol/BigInt.cs` — `89c9431efa8fa4bac78b20a31cf953e6c417ac6ed543102662432c2fffbcdc11`
- `Codol/BitScanner.cs` — `930a94caf5f26a31ae6e7d306f0c0a17b11df4abc9816d45de1f53dec634f649`
- `Codol/ClientCommandReader.cs` — `5ecbb02f31f380c68b8192fbe026700b4b20f1131dd41dc047f55dd3a65f6905`
- `Codol/Codol2697Protocol.cs` — `bc4aaf1ee518072b0776efe29f491710002c8000ee6a131b4df9e6714e9065c6`
- `Codol/CodolClientReplay.cs` — `487e8c40585bcc2b966a64848a7172feb1fa7ce22536f9713e0ad87d8155ea88`
- `Codol/CodolProtocol.cs` — `fa06d0543b621216dc57c05a581ec1dcb8f00d18a9bf1368942213c75cf4a046`
- `Codol/MotionSnapshot.cs` — `272bb62147a81d108108da0439da6a080206c0f62c73f19c0b49395403af1d66`
- `Codol/P224.cs` — `634cd01959f37714311b456747452b7b7e59298d53f29998b0e644bd74ee3277`
- `Codol/SessionDescriptor.cs` — `0e1a31706b9467d997ce22a3622d3ce2caeb065ae4de5f50a03f82695ec2c732`
- `Codol/SessionGolden.cs` — `fe23c29567a1992be6eabe7f2e2e0857be24be158ae7af212b59449ff7eec154`
- `Codol/Sha1.cs` — `cb18b5c304408ef3eaea555536848193d100909d56f45d1a3c22033096d40875`
- `Engine/BuildFingerprint.cs` — `a218645f31f381e6426b17b84b672c037fc79c41dde90430cdf780d46647b3fe`
- `Engine/ClientLogic.cs` — `0aba015da760a1c6f7ceb717895f6240060ca6bbfcfa1f41b592c39e9c2468cc`
- `Engine/ClientSession.cs` — `17b813dbf4a6881fe19b636178c8cded8d2d609f5589ca2119c923971f3aa3fe`
- `Engine/GameWorld.cs` — `07fa1793671f5ff8dee84177cecdf162adc28e7956d2a216d0a8fd8b2a27cc7d`
- `Engine/PlayerIdentity.cs` — `29d8ba719c43913d80e8258f5c62c04a36fb2b22f13895566615eda74854d512`
- `Engine/ServerConfig.cs` — `3767c4721eeec345c7680c390dd41edc40418181221c6f4fd407ac77e19032e2`
- `Engine/ServerHost.cs` — `245725fbeeb65b8c9c5bfb1310204ca43b99f58e86875cdb909a074d09382c67`
- `Engine/SessionExporter.cs` — `92bcbb54f43e0cdaddb6ca5d505cc1d75abc552157694c04904579ad302de431`
- `Net/Logger.cs` — `3bb982efa91c11f35310b44121bff104796bf1123b3f18a0f2ef408fed5f37e9`
- `Net/UdpTransport.cs` — `66945bd0b473bfe64fe670492eda353b79fe9e988f95fec207d48da43addae01`
- `Program.cs` — `56ce57d3848ac29fab5bd77af87ff80a08ca90d107676cf64025865bdf76ae3a`
- `SelfTest.Codol2697.cs` — `98663ec8a3940f808558686ae2aa0507b7a238f325c5edf3ac7313ab5ac47f88`
- `SelfTest.cs` — `16660b753d0e3c585f7d8043d732865acf8c536bf1602cd13c5b46512ea8c6ba`