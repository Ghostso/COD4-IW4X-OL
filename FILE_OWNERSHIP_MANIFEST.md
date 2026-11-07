# FILE_OWNERSHIP_MANIFEST — 文件归属、哈希、构建时间、产物与日志清单

**日期**：2026-10-10
**用途**：让每一个源码文件、每一个构建产物、每一条日志都能追溯到**具体工作树**与**具体构建**。
**采集方式**：只读（`Get-FileHash` / `git rev-parse` / `git status` / `git diff --check`）。
**哈希算法**：SHA-256（大写十六进制）。**所有哈希均为本轮实测，未转录自报告。**

---

## 1. 工作树归属

| 标识 | 路径 | 角色 | 允许操作 |
| --- | --- | --- | --- |
| **F** | `F:\桌面\ol\ol-mod-olfinal` | **唯一活动工作基准** | 读、构建、运行隔离测试目标 |
| **D** | `D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal` | **冻结历史回归副本** | **只读**：检视、哈希、比对 |
| **WS** | `D:\BaiduNetdiskDownload\使命召唤OL` | 会话工作目录 / 证据与日志根 | 写交付文档与证据归档 |
| **SBX** | `E:\CODOL_SANDBOX\RUN001` | 隔离运行时沙箱（制品来源） | **本轮只读** |

### 1.1 Git 身份

| 项 | F | D |
| --- | --- | --- |
| `git rev-parse HEAD` | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 同 F |
| `git rev-parse --abbrev-ref HEAD` | `OLfinal-live` | 同 F |
| upstream / ahead-behind | `origin/OLfinal-live`，`+8 -0` | 同 F |
| `origin` URL | `https://github.com/CODOL-EMU/ol-mod-olfinal.git` | 同 F |
| `--absolute-git-dir` | `F:/桌面/ol/ol-mod-olfinal/.git` | `D:/BaiduNetdiskDownload/使命召唤OL/_e1_regression/ol-mod-olfinal/.git` |
| `git diff --check` | exit **0** | exit **0** |
| `.git\index` mtime | 2026-10-09 12:26:40 | 2026-10-09 12:26:40 |

### 1.2 `git status --porcelain=v1`（轮次结束时，与轮次开始时逐行相同）

**F（8 修改 + 1 未跟踪）**
```
 M src/game_server/Appmain.cpp
 M src/game_server/FrameHook.cpp
 M src/game_server/FrameHook.hpp
 M src/game_server/server_mp/sv_network_mp.cpp
 M src/game_server/server_mp/sv_network_mp.hpp
 M src/game_server/win32/win_net.cpp
 M src/game_server/win32/win_net.hpp
 M xmake.lua
?? tests/game_server/TransportLifecycleTests.cpp
```

**D（5 修改 + 1 未跟踪）**
```
 M src/game_server/server_mp/sv_network_mp.cpp
 M src/game_server/server_mp/sv_network_mp.hpp
 M src/game_server/win32/win_net.cpp
 M src/game_server/win32/win_net.hpp
 M xmake.lua
?? tests/game_server/TransportLifecycleTests.cpp
```

---

## 2. 源码文件哈希（工作区实测）

### 2.1 两树都修改的文件

| 文件（相对工作树根） | F SHA-256 | F 字节 | D SHA-256 | D 字节 | HEAD 索引 blob | 相同? |
| --- | --- | --- | --- | --- | --- | --- |
| `src/game_server/server_mp/sv_network_mp.cpp` | `AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6` | 6,941 | `CA34DAF579A7CD92D29B903C2BB24B504FA80786A0034E16468062EE22E15324` | 5,705 | `60505309651af0a23d710070085333cec925b088` | ❌ |
| `src/game_server/server_mp/sv_network_mp.hpp` | `A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915` | 4,357 | `3AF3104EA0FEF31ECC86204DA029DAB7BF268B7F92AC1FE67E928628C9F9B1B6` | 3,291 | `6a7e4628da27a16d43808e01f4d05f46cc0a5fae` | ❌ |
| `src/game_server/win32/win_net.cpp` | `3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14` | 9,054 | `B4850F93FC07939E26F6FCE5D68C7264479413154073337D6EF1D18F0F8413EB` | 6,811 | `8a1e576282813c143bc6c1675e4cf437b442e072` | ❌ |
| `src/game_server/win32/win_net.hpp` | `8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1` | 2,642 | `9F4A50582D66706A7D8BEF308426E36949769098D02C691BBA07DF8358AB8851` | 2,177 | `7318a33ee6fb0e54a5aa63cf84fb28491b4bb6db` | ❌ |
| `xmake.lua` | `5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8` | 14,179 | `5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8` | 14,179 | `86f4211f5b079501515ab1729aa734e0460d7e7b` | ✅ |
| `tests/game_server/TransportLifecycleTests.cpp`（未跟踪） | `FA6A2760B73BBE52B377178C10BAA64390ADC43522A97D455070DE79DBE7DE94` | 27,504 | `00EBDB2C48065A3CEEC96C1A442774DCCC7BDD62634B57445D813230458D96CA` | 10,662 | —（未跟踪） | ❌ |

### 2.2 仅 F 修改的文件

| 文件 | F SHA-256 | F 字节 / 行 | D SHA-256（= HEAD 版本） | D 字节 |
| --- | --- | --- | --- | --- |
| `src/game_server/Appmain.cpp` | `407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1` | 481,281 / 9,546 | `69FDC488D0594A5DC65270ADBD3B7B8DA8A20AC753A19CB09173F8CED11C43CC` | 479,827 |
| `src/game_server/FrameHook.cpp` | `1CA962D707F23DA40F60878DB5A8542601BA68398FE4EA226D0F957BE8008D8A` | 3,683 / 117 | `D7E398184935632D9B8CCF4B6CFB9694BBF9A826645DCB9F3ED1E6184B2DCF26` | 2,053 |
| `src/game_server/FrameHook.hpp` | `6EDF4F9A21511468E99B779FE64BE5EA6B637F1E6AE24F91362013AA1EF5ACF5` | 1,213 / 27 | `EAD8A036BA73E7BB27316173F1993D8904BA5C6F2C41FE2312BF6607EBEA6B4F` | 246 |

### 2.3 两树相同的文件（抽样，用于确认 HEAD 一致）

| 文件 | 两树共同 SHA-256 |
| --- | --- |
| `src/game_server/EngineBindings.cpp` | 未修改，18,028 行（两树相同） |
| `config/codol-game-dir.txt`（gitignore） | `9AEEFD107F677EDD4F2A85DA7E38FF796718C7BF64F60E1B7D1CD6F1092019AA` |

### 2.4 受保护的常量（只读核对，**未修改**）

| 常量 | 值 | 位置 |
| --- | --- | --- |
| `EngineBindings::ExpectedTimestamp` | `0x6096930A` | `F:...\src\game_server\EngineBindings.hpp:438` |
| `EngineBindings::ExpectedImageSize` | `0x0E5D6000` | 同上 :439 |
| `EngineBindings::ComFrameRva` | `0x0FEA20` | 同上 :440 |
| `ClientProcessPatches::UnsignedFastfileVerificationRva` | `0x8371A` | `F:...\src\game_server\ClientProcessPatches.cpp:207` |
| `ComFramePrefix` | `55 8B EC 56 57` | `F:...\src\game_server\EngineBindings.cpp:755-757` |
| `UnsignedFastfileVerification` | `83 7C 24 08 01 0F 94 C0` | `F:...\src\game_server\ClientProcessPatches.cpp:208-211` |
| `AnyIpv4Address` | `0` | `F:...\src\game_server\win32\win_net.hpp:19` |
| `SocketAlreadyBoundError` | `10037`（`static_assert == WSAEALREADY`） | 同上 :24-27 |

---

## 3. 构建产物归属

### 3.1 本轮构建（唯一由本会话产生的产物）

| 项 | 值 |
| --- | --- |
| **工作树** | **F** |
| 目标 | `ol_transport_lifecycle_tests`（`set_default(false)`） |
| 命令 | `xmake f` → `xmake build -r ol_transport_lifecycle_tests`（workdir = F） |
| 构建时间 | **2026-10-10 11:58:29** |
| 构建耗时 | 30.171 s（强制全量重建） |
| 产物路径 | `F:\桌面\ol\ol-mod-olfinal\build\bin\release\ol_transport_lifecycle_tests.exe` |
| 产物大小 | 3,826,176 B |
| 产物 SHA-256 | `4BE2180D1856DB6A8CF1BBD831001BE8C059E2A519582A5DAED99BE7E5A18468` |
| 运行结果 | `checks=106 failures=0`，exit 0 |
| 构建日志 | [_batch10_evidence\T1_rerun.log](_batch10_evidence/T1_rerun.log)（增量，0.156 s）· [_batch10_evidence\T1_rerun_forced.log](_batch10_evidence/T1_rerun_forced.log)（强制重建 + 运行） |
| 副产物 | `F:\...\build\bin\release\Ayria\Logs\CodolGameServer.log`（186,532 B，测试 P1 用例写入） |
| 是否触发 `ol_deploy` | **否**（`build\stage` mtime 仍为 2026-10-09 17:01:07） |

### 3.2 F 工作树的既有产物（本轮**未重建**，仅登记哈希）

| 产物 | 大小 (B) | 构建时间 | SHA-256 | 归属 |
| --- | --- | --- | --- | --- |
| `CodolGameServer.Localnet32` | 6,559,232 | 2026-10-09 20:05:25 | `21D1481735828B48F3C36C09B84581756A1BC6051F57DE198E75B1556A54B9CA` | F（插件，含当前 Appmain/FrameHook/sv_network 修改） |
| `CodolGameServer.map` | 9,429,723 | 2026-10-09 20:05:25 | `EF2A640934E40B8EB760B987C3CB81AE995854086DAC30FD384710592A33C2C3` | F |
| `CodolGameServer.exp` | 10,708 | 2026-10-09 20:05:09 | `EC81A2CFA18A8B9888D539FF67A3E77C85D844698AE0055BEAC13C8624B5D580` | F |
| `LocalnetworkingRe.Ayria32` | 492,032 | 2026-10-09 16:59:35 | `8F1BC5D424EADEC61650E3F67402D52D95E558492E94B8DE6484BA4F3F99100A` | F |
| `PlatformwrapperRe.Ayria32` | 543,232 | 2026-10-09 16:59:36 | `A7420E17E383174403EA844BC9236ACAFE9B029F58FA6A8DEA0D1ADBCD7F8D2F` | F |
| `AlwaysofflineRe.Localnet32` | 3,996,160 | 2026-10-09 16:59:39 | `D2B9CA407CCB99B888DADCCFD1977380C40E2421E577DD0354E79F01898EEF54` | F |
| `ol_room_owner.exe` | 283,648 | 2026-10-09 17:01:07 | `354D5B29834D1FFD2CB51E36B2C5385E5B55E09825E9BA5EB7206A1E676EBCB3` | F |
| `ol_game_server_tests.exe` | 7,481,856 | 2026-10-09 13:52:25 | `21AD81277D8E4BD6544319D6BCD51B35C9FD1CB3553555FF7E7CDD2F218CCBFC` | F |
| `ol_dedicated_control_tests.exe` | 286,720 | 2026-10-09 13:52:29 | `0B7ED7010D218258AF691D216209D25870279B8A877593F08C6466E48524232B` | F |
| `ol_playerdata_def_tests.exe` | 216,576 | 2026-10-09 13:52:32 | `4757FDB2314B13E126A209A62128F84616892E24BAEC7394933E447B7737F2DB` | F |

**构建→日志追溯**：`CodolGameServer.Localnet32` 的哈希 `21D14817…` 与 [_batch2_build.log](_batch2_build.log)（2026-10-09 20:05）记录一致 ⇒ 该产物由 batch2 构建产生。`ol_room_owner.exe` 的哈希 `354D5B29…` 与 [_stage_final.log](_stage_final.log)（17:01）一致。

**D 工作树产物**：`ol_transport_lifecycle_tests.exe` **不存在**（7 次构建全部失败，见 [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) §4）。D 的 `build\` 体积 1,145 MB（F 为 1,195.9 MB），但其中不含 T-1 测试二进制。

### 3.3 插件产物与报告的差异（登记）

| 来源 | `CodolGameServer.Localnet32` 哈希 | 时间 |
| --- | --- | --- |
| F 当前产物（实测） | `21D1481735828B48F3C36C09B84581756A1BC6051F57DE198E75B1556A54B9CA` | 2026-10-09 20:05 |
| [_t1_compat.log](_t1_compat.log) | `0EABD5F54763976CA4A92CC4C0DBB34A5CC8E60DE6EBFE4A3C6FA28A6A157971` | 2026-10-09 17:32 |
| [_compat_olgs.log](_compat_olgs.log) | `C1494BD5F986624832494490B7039283C93371137B577A6DD2061AA19AB1DB9A` | 2026-10-09 19:02 |
| [_batch1_build.log](_batch1_build.log) | `F771003F9CC50FDAA001215E6F02C1EF12869A8718648492766FD766C8E445F5` | 2026-10-09 19:44 |
| [_batch2_build.log](_batch2_build.log) | `21D1481735828B48F3C36C09B84581756A1BC6051F57DE198E75B1556A54B9CA` | 2026-10-09 20:05 |
| `E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32` | `6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021`（沙箱副本，来自 [_build_olgs.log](_build_olgs.log) 13:49） | 2026-10-09 13:49 |
| 报告 [CODOL_SERVER_PROGRESS_20261009.md](CODOL_SERVER_PROGRESS_20261009.md) §6.3 | 记沙箱为 `6D493B82…6B2021`，与"两个当前构建"（`0EABD5F5…`、`21D14817…`）均不同 | — |

⇒ **F 的当前插件产物是 `21D14817…`（20:05），且它包含当前全部未提交修改**（Appmain.cpp mtime 20:04:10 < 构建时间 20:05:25）。

### 3.4 F 的 stage 快照（既有，本轮未触碰）

`F:\桌面\ol\ol-mod-olfinal\build\stage\codol\Ayria\`（mtime 2026-10-09 17:01:07）：

| 文件 | 大小 (B) | SHA-256 |
| --- | --- | --- |
| `Ayria\Injector32.exe` | 126,464 | `30CC97C0C2A67ED498BB85EBB60A08E27C769C6785E351A01D2F246B50E3F0E1` |
| `Ayria\Bootstrapper32.dll` | 159,744 | `C52F6BEB848571797F696D0616597A1E505A73EF48D80BB55E30D059E9A97D28` |
| `Ayria\ol_room_owner.exe` | 283,648 | `354D5B29834D1FFD2CB51E36B2C5385E5B55E09825E9BA5EB7206A1E676EBCB3` |
| `Ayria\Assets\*` | — | 44 条目录清单，逐项哈希见 `build\stage\codol\ol-mod-runtime-manifest.json` |

> **本轮未部署、未复制该 stage 到任何位置。** `E:\CODOL_SANDBOX\RUN001\Ayria\` 的 44 文件来自 2026-10-09 17:07 的前轮操作，本轮只读。

---

## 4. 客户端制品归属（只读，未获取/未修改）

| 项 | 值 |
| --- | --- |
| 路径 1 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 路径 2 | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe` |
| 大小 | 7,841,344 B |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| mtime | 2026-09-10 00:06:54 |
| PE | PE32 / x86 / `TimeDateStamp=0x6096930A` / `SizeOfImage=0x0E659000` / 7 段 `.tp3×6,.tvm0` / `FileVersion=1649370` |
| 角色 | **加壳零售客户端候选 A**（非目标制品；见 [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md)） |
| `out.exe` | **本机在授权根内 0 命中** |

---

## 5. 日志清单与归属

### 5.1 本轮新产生的日志

| 日志 | 大小 | 工作树 | 内容 |
| --- | --- | --- | --- |
| [_batch10_evidence\T1_rerun.log](_batch10_evidence/T1_rerun.log) | 见文件 | **F** | `xmake f` + 增量构建（0.156 s，无陈旧源）+ 运行 106/0 |
| [_batch10_evidence\T1_rerun_forced.log](_batch10_evidence/T1_rerun_forced.log) | 见文件 | **F** | 强制全量重建（30.171 s）+ 运行 106/0 + 前后 exe 哈希 |

### 5.2 既有 T-1 日志（工作区根，本轮只读引用）

| 日志 | 时间 | 归属工作树 | 断言 | 结果 | 是否代表当前源码 |
| --- | --- | --- | --- | --- | --- |
| [_t1_build.log](_t1_build.log) | 10-09 17:31 | F（日志内 `cwd=F:...`） | 43 | exit 0 | ❌ 过期 |
| [_t1_compat.log](_t1_compat.log) | 10-09 17:32 | F | — | 插件重链 exit 0 | ❌ 过期 |
| [_e1_build.log](_e1_build.log) | 10-09 18:27 | F | 49 | exit 0 | ❌ 过期 |
| [_e1_copy.log](_e1_copy.log) | 10-09 18:27 | F→D 复制 | — | `robocopy exit=1` | 复制记录 |
| [_e1_regression.log](_e1_regression.log) | 10-09 18:28 | D（意图） | 49 | **无效**（构建失败后跑旧二进制） | ❌ 无效 |
| [_e1_regression2.log](_e1_regression2.log) … [_e1_regression8.log](_e1_regression8.log) | 10-09 18:29–18:31 | D | — | 全部 `BUILD exit=-1` | 失败记录 |
| [_a1c3_build.log](_a1c3_build.log) | 10-09 18:48 | F（`cwd=F:...`） | 83 | exit 0 | ❌ 过期 |
| [_compat_olgs.log](_compat_olgs.log) | 10-09 19:02 | F | — | 插件重链 exit 0 | ❌ 过期 |
| [_batch1_build.log](_batch1_build.log) | 10-09 19:44 | F | 83 | exit 0 | ❌ 过期 |
| [_batch2_build.log](_batch2_build.log) | 10-09 20:05 | F | 92 | exit 0 | ❌ 过期（但插件产物 `21D14817…` 由此产生） |
| [_p1_build.log](_p1_build.log) | 10-09 20:41 | F | 105 / **7 FAIL** | exit 1 | ❌ 历史失败 |
| [_p1_diag.log](_p1_diag.log) | 10-09 20:42 | F | 105 / 7 FAIL | exit 1 | ❌ 历史失败 |
| [_p1_run2.log](_p1_run2.log) | 10-09 20:43 | F | 105 | exit 0 | ❌ 过期 |
| [_p1_final.log](_p1_final.log) | 10-09 20:44 | F | 105 | exit 0 | ❌ 过期 |
| [_a6_build.log](_a6_build.log) | 10-09 21:23 | F | **106** | exit 0 | ✅ 与当前 F 测试文件一致 |

### 5.3 其它相关日志

| 日志 | 时间 | 内容 |
| --- | --- | --- |
| [_build_olgs.log](_build_olgs.log) | 10-09 13:49 | 首次成功构建 `ol_game_server`，产物 `6D493B82…` |
| [_run_tests.log](_run_tests.log) | 10-09 13:52 | 3 套测试 exit 0 |
| [_build_plugins.log](_build_plugins.log) | 10-09 16:59 | 插件构建 exit 0 |
| [_stage_final.log](_stage_final.log) | 10-09 17:01 | stage exit 0 |

### 5.4 证据归档（本轮新建）

| 文件 | 大小 | 内容 |
| --- | --- | --- |
| [_batch10_evidence\diff_F_git.patch](_batch10_evidence/diff_F_git.patch) | 25,009 B | F 的 `git diff`（8 文件，+311/−32） |
| [_batch10_evidence\diff_D_git.patch](_batch10_evidence/diff_D_git.patch) | 9,616 B | D 的 `git diff`（5 文件，+104/−12） |
| [_batch10_evidence\diff_F_vs_D_src.patch](_batch10_evidence/diff_F_vs_D_src.patch) | 22,495 B | F 与 D 的 `src/` 逐文件差异（+213/−33） |
| [_batch10_evidence\diff_T1tests_F_vs_D.patch](_batch10_evidence/diff_T1tests_F_vs_D.patch) | 18,721 B | 两份 T-1 测试差异（+349/−0） |
| [_batch10_evidence\T1_tests_F.cpp](_batch10_evidence/T1_tests_F.cpp) | 27,504 B | F 侧测试副本（只读快照） |
| [_batch10_evidence\T1_tests_D.cpp](_batch10_evidence/T1_tests_D.cpp) | 10,662 B | D 侧测试副本（只读快照） |

---

## 6. 交付文档归属（本轮新建）

| 文档 | 说明 |
| --- | --- |
| [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md) | 工程基准、冻结规则、双工作树关系 |
| [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md) | 两份 T-1 实现及测试的逐项差异与采用版本 |
| [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md) | 测试覆盖、实际执行结果、失败与未验证项 |
| [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md) | 目标客户端制品缺口与解除门禁所需证据 |
| **FILE_OWNERSHIP_MANIFEST.md**（本文件） | 工作树路径、HEAD、文件哈希、构建时间、产物哈希、日志路径 |

> **未新建重复文档**：本仓库此前**不存在** `BASELINE_ADJUDICATION` / `T1_DIFF_REVIEW` / `T1_ACCEPTANCE_REPORT` / `ARTIFACT_BLOCKERS` 的等价物（已在工作区与 F、D 内检索，0 命中）。最接近的既有文档 [CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md](CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md) 与 [CODOL_SERVER_PROGRESS_20261009.md](CODOL_SERVER_PROGRESS_20261009.md) 已在本轮被**引用**，**未被修改**。

---

## 7. 本轮写入副作用（完整清单）

| 位置 | 内容 | 可回滚方式 |
| --- | --- | --- |
| `WS\_batch10_evidence\`（新建目录） | 6 个归档文件 + 2 个日志 | 删除该目录 |
| `WS\`（工作区根） | 5 份交付文档 | 删除这 5 个文件 |
| `F:\...\build\bin\release\ol_transport_lifecycle_tests.exe` | 强制重建（gitignore `/build/`） | 删除或重跑 `xmake build` |
| `F:\...\build\bin\release\Ayria\Logs\CodolGameServer.log` | 测试运行追加日志 | 删除该日志 |
| `F:\...\.xmake\` | `xmake f` 刷新配置缓存（gitignore `/.xmake/`） | 删除或重配 |

**F 与 D 的受版本控制文件：0 字节改动。** 两树 `git status --porcelain` 在轮次前后逐行一致。

---

## 8. 关联交付

- [BASELINE_ADJUDICATION.md](BASELINE_ADJUDICATION.md)
- [T1_DIFF_REVIEW.md](T1_DIFF_REVIEW.md)
- [T1_ACCEPTANCE_REPORT.md](T1_ACCEPTANCE_REPORT.md)
- [ARTIFACT_BLOCKERS.md](ARTIFACT_BLOCKERS.md)
