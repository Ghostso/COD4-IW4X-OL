# TEST_AND_BUILD_RESULTS — 实际执行的测试与构建

**日期：** 2026-10-13（Asia/Shanghai）  
**原则：** 只记录真实执行的命令、退出码和输出；不把既有证据冒充本轮实测。

---

## 1. 本轮只读复验：目标客户端哈希

命令（只读）：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'COD OL\codoMP_client_shipRetail.exe'
Get-FileHash -Algorithm SHA256 -LiteralPath 'COD OL\codoMP_client_shipRetailBase.dll'
```

结果：

| 文件 | SHA256 | 与固定基线 |
|---|---|---|
| `codoMP_client_shipRetail.exe` | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | 一致 |
| `codoMP_client_shipRetailBase.dll` | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | 一致 |

结论：目标版本匹配，034 镜像结论可沿用。

---

## 2. 既有 FREEZE-005 证据（必读基线，非本轮重跑）

```text
命令：powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
结果：BUILD OK
退出码：0
告警：1 条 CS0675 (ClientCommandReader.cs:213)
产物：CODOLCombatServer.exe (188416 B)
产物 SHA256：0c0a4bc13325f6c9dc6d9abd9d2197efc41612029c0bf8627f3b752c299943ee
源码指纹：5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf
源文件数：25
```

```text
命令：CODOLCombatServer.exe --selftest
退出码：0
通过：251
失败：0
结果：全绿
```

```text
命令：CODOLCombatServer.exe --run --max-seconds 3
退出码：0
UDP 绑定：127.0.0.1:28960
停止后：sessions=0 entities=0
说明：connected=0；无客户端连接
```

以上完整原始输出：

- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\build.exitcode.txt`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\build.console.utf8.log`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\selftest.exitcode.txt`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\selftest.stdout.log`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\run_maxseconds.stdout.log`
- `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005\attempt_01_20261013_124339\evidence\run_observation.json`

---

## 3. 037 本轮独立副本复验

### 3.1 只读复制与源码指纹

- 复制源：`CODOL-Combat-Server-v0.1`
- 副本：`CODOL-BATTLE-SERVER-PROTOCOL-GAP-037\_verification\server-copy`
- 复制文件：148 个（仅 `src/config/build/tests/README.md`，不含日志/缓存）
- 源码文件：25 个 `.cs`
- 计算所得源码指纹：`5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`
- 与 FREEZE-005 是否一致：**一致**

说明：副本内含复制过来的旧 `build/bin/CODOLCombatServer.exe`，其哈希与 FREEZE-005 相同；该旧 EXE 的自测不能作为本轮重新构建的证据。

### 3.2 通过 `build\build.ps1` 复构建：BLOCKED（宿主编码问题）

执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
```

结果：

| 项 | 值 |
|---|---|
| 脚本退出码 | 1 |
| `csc` 退出码 | 空 |
| 编译输出 | 空 |
| 耗时 | 约 38 ms |
| 现象 | PowerShell 脚本内参数路径中文被解释为 `D:\BaiduNetdiskDownload\}?OL\...` |

根因探测：

- 直接调用 `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /help`：退出码 0，正常输出。
- PowerShell 文件中 `& $csc @args` 打印实际参数：中文路径变成 `D:\BaiduNetdiskDownload\}?OL\...`。
- 因此这是当前宿主编码/参数传递问题，**不是源码编译错误**。

原始日志：

- `_verification\build.stdout.txt`
- `_verification\build.stderr.txt`
- `_verification\build.exitcode.txt`
- `_verification\server-copy\build\logs\build_release_20261013_170602.log`

### 3.3 直接 `csc` 复构建：成功

绕过 PowerShell 参数编码，在 ASCII 副本中使用直接进程参数编译同一批 25 个源文件：

```text
编译器：C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe (4.8.9037.0)
配置：/optimize+ /platform:x86 /warn:4
退出码：0
告警：1 条 CS0675 (src\Codol\ClientCommandReader.cs:213)
产物：C:\Windows\Temp\codol037_repo\build\bin\CODOLCombatServer.exe
产物 SHA256：c066455274bf6cf5cde0f3c94033f553ade88348ec630a3e503dfba925120abe
```

说明：产物哈希与 FREEZE-005 不同是预期现象；本机 `csc` 不支持 `/deterministic`，FREEZE-005 已说明可重复性以源码指纹为准，不宣称 EXE 逐位可复现。

原始输出：

- `_verification\rebuild.stdout.txt`
- `_verification\rebuild.stderr.txt`
- `_verification\rebuild.exitcode.txt`

### 3.4 本轮自测：249/251，2 项失败属验证包装缺失

执行：

```text
C:\Windows\Temp\codol037_repo\build\bin\CODOLCombatServer.exe --selftest
退出码：2
通过：249
失败：2
```

失败项：

1. `BUILD_MANIFEST.txt 含 source_sha256 :: (未找到 manifest 或字段)`
2. `构建产物大小 == BUILD_MANIFEST 记录值 :: actual=188416 recorded=-1`

原因：本轮直接调用 `csc` 绕过了 `build\build.ps1` 的 manifest 生成步骤，未生成 `BUILD_MANIFEST.txt`。这两项是验证包装缺失，不是协议或功能失败。

原始输出：

- `_verification\rebuild.selftest.txt`
- `_verification\rebuild.selftest.exitcode.txt`

**结论：**

- 正式基线 FREEZE-005：构建 PASS，251/251 PASS。
- 037 直接 `csc` 复构建：成功；功能自测 249/251，2 项为 manifest 缺失。
- 037 `build.ps1` 复构建：因宿主编码参数问题 BLOCKED；已给出原始日志。
- 未发现任何协议级测试失败。

---

## 4. 未执行的测试（明确声明）

- 未启动游戏。
- 未做真实客户端 E2E。
- 未产生新抓包。
- 未对目标客户端做动态调试、注入或 hook。
- 未验证 gamestate/configstring/snapshot 与目标客户端的兼容性。

---

## 5. 测试覆盖与协议正确性的边界

FREEZE-005 的 251 项通过证明：

- 服务端密码学原语与编解码器内部正确。
- 服务端生命周期、实体表、错误路径、清理逻辑自洽。
- 旧抓包链路的离线复放通过。

它**不**证明：

- 目标客户端会接受这些字节。
- legacy/2697 格式属于 3.19.26.22。
- gamestate 或 snapshot 可被目标客户端解析。

**测试数量不得替代协议正确性。**
