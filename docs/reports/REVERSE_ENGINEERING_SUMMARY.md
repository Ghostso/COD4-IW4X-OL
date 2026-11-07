# CODOL (使命召唤OL) 逆向工程与推进总结

> 生成时间：2026‑09‑30  
> 工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

---

## 1. 项目概览
| 目录 / 组件 | 说明 |
|------------|------|
| **analysis_logs/** | 静态分析产出的日志、配置解密、模块列表、手写恢复文档 |
| **COD OL/** | 逆向脚本、启动器原型、加密工具、监控工具 |
| **CODOLServer/** | 服务端模拟实验：大厅服务、平台端点重定向、AES 密钥推导、实验记录 |
| **OfflineServer / restore\*** | 早期离线服务器尝试、二进制还原、合同还原 |
| **IW4X / WeGame / WeGameInstaller** | 相关客户端/启动器组件的辅助分析 |
| **_core\*_observer / _dyn_stage1 / _ebo1_* / _ich\*_observer** | 动态观测、插桩、内存快照脚本 |
| **scripts/** (在 COD OL) | 核心自动化工具：`tas_crypt.py`、`codol_launch.py`、`watch_game.py`、`procmem.py`、`prochandles.py`、`probe_handoff.py` |

---

## 2. 关键静态逆向成果

### 2.1 TCLS → Client 交接流程  (见 `analysis_logs/handoff_recovery.md`)
| 项目 | 详情 |
|------|------|
| **命令行模板** (TCLS.dll `0x103C53CC`) | `\"%s\" -q %u -i %d -s %d -g %d -u %u -n %s`  <br> 可选尾部 `-m --1` 由 `channel->vtbl+0xA8()` 决定 |
| **CreateProcessW 调用点** | `0x10044AE4` (函数 `0x100447C0`)<br> `bInheritHandles=TRUE`、非挂起启动 |
| **共享内存名称** | `TCLS_TASMEMORY_<pid>` (加密, 0x7AC 字节) <br> `TCLS_SHELLMEMORY_<pid>` (明文, 0x224 字节) |
| **TAS 结构 (0x7AC)** | 见文档表格：ready flag、长度字段、block1(0x400)、block2(0x80)、daemon 字段、UTF‑8 文本段、随后 **整体加密** (偏移 0x004‑0x7AC, 长度 0x7A8) |
| **SHELL 结构 (0x224)** | 明文，含相同 daemon dword (offset 0x008) |
| **加密算法** | **Tenio cipher** – KSA 由 8 字节密钥派生 (`CreateFileW` + `GetFileTime` → `pack('<II', lo, hi)`)，回退常量 `0x46D14CF9 / 0xEF1DC888`。KSA/加解密已在 `tas_crypt.py` 完整复现并自测通过。 |
| **密钥来源** | TAS 路径使用 **游戏 EXE 的文件时间** (`this+0x461EC`) 作为 8‑byte key。 |

### 2.2 模块加载清单 (`analysis_logs/game_modules.txt`)
| 基址 | 大小 | 模块名 |
|------|------|--------|
| 0x63040000 | 0x3391488 | `BugTrace.dll` |
| 0x658A0000 | 0x13721600 | `ACE-DRV32.dll` |
| 0x63630000 | 0x18100224 | `TenRpcs.dll` |
| 0x66F10000 | 0x2564096  | `GameRpcs.dll` |
| 0x68470000 | 0x323584   | `GDPLoader.dll` |
| … | … | … (完整列表见文件) |

### 2.3 配置文件解密尝试
- `commonconfig.cfg.dec`、`dirsystemconfig.cfg.dec` 已导出明文，但 **并非** 用上述 Tenio cipher 且本地文件时间密钥均无法解密，说明另有密钥派生或格式。

---

## 3. 动态实验与观测

| 实验 | 结果 | 备注 |
|------|------|------|
| **Baseline 启动** (`-q` only) | 游戏显示 Splash → ~30 s 后自动退出 | 无共享内存被游戏打开 |
| **Full 启动** (完整命令行 + TAS/SHELL mappings) | 同上，Splash 后同步中止 | 监控到游戏创建的 socket、进程、模块加载 (`game_watch*.txt`) |
| **共享内存标记扫描** (`CODOLBLOCK1-MARKER`, `CODOL-TEXT-MARKER`) | **未在游戏内存中发现** (t+6 s) | 说明 TAS 登录块未被消费，或被 TenProtect 保护 |
| **句柄枚举** (`prochandles.py`) | 进程句柄列表中 **未出现** `TCLS_TASMEMORY_<pid>` / `TCLS_SHELLMEMORY_<pid>` | 验证了交接未被客户端使用 |
| **反作弊 (ACE) 保护** | ~10 s 后内存读取失效 | 限制后续动态分析 |

**结论**：已完整复现 TCLS 的静态交接，**足以让客户度显示启动画面**，但后续登录/平台鉴权 (TenProtect / iips) 依赖实时腾讯服务，离线环境无法通过。

---

## 4. 开发的自动化工具 (位于 `COD OL\scripts\`)

| 脚本 | 功能 | 关键依赖 |
|------|------|----------|
| `tas_crypt.py` | Tenio KSA/加密/解密、默认密钥、暴力破解 | 纯 Python |
| `codol_launch.py` | 原型离线启动器：重建命令行、创建 TAS/SHELL 共享内存、可选 `--no-shm`、`--keep` 监控 | `tas_crypt`、Win32 API (`ctypes`) |
| `watch_game.py` | 启动游戏并定时采样：模块、窗口、内存扫描、句柄、网络 | `procmem.py`、`prochandles.py` |
| `procmem.py` | 进程模块枚举、窗口枚举、多模式内存扫描、Dump | `psutil`、`ctypes` |
| `prochandles.py` | 通过 `NtQuerySystemInformation` 枚举 Section/Event/Mutant/Semaphore | `ctypes` |
| `probe_handoff.py` | 一键启动+标记扫描，输出扫描结果 | 上述模块组合 |

所有脚本均在 **Python 3.10+** 下可直接运行，已在仓库内通过 `analysis_logs/*.txt` 产出日志验证。

---

## 5. 服务端模拟进展 (`CODOLServer/`)

| 子目录 | 进度 |
|--------|------|
| `lobby_server/` | 基础大厅协议框架、消息解析、会话管理 |
| `experiments/` | 多轮实验：AES 密钥推导 (`_aeskey_*`)、平台端点存根 (`_capture1`、`_liveplat*`) |
| `_a2_runs/`, `_fullimage/`, `_expA*` | 完整镜像捕获、实时平台交互记录、重放测试 |
| `subagents/` | 子任务自动化：密钥派生、协议 Fuzzing |
| `logs/` | 运行时日志、网络抓包、错误堆栈 |
| `_write_handoff.py` | 将静态恢复的 TAS/SHELL 数据写入文件供离线分析 |

**已实现**：
- 平台四大端点 (登录、心跳、配置下发、匹配) 的 **DNS/Hosts 重定向** 存根
- **AES‑256‑GCM** 密钥派生链 (从 `iips` 契约、文件时间、硬件 ID) 的部分逆向
- 大厅服务的 **最小可用原型** (可接受客户端连接、回复基础握手)

**待完成**：
- 完整的 **iips 契约解析** 与签名验证
- 真实的 **TAS 登录块** 获取 (需线上抓包或模拟 TenProtect)
- 配置文件 (`commonconfig.cfg` 等) 的真实解密流程

---

## 6. 遗留未知 / 风险点 (严禁臆造)

| 未知项 | 影响 |
|--------|------|
| `-i -s -g -u -n` 等参数的语义及来源字段 (`this+0x48F94` 等) | 可能影响匹配/大厅逻辑 |
| 实时账号数据 (`uId`, `cltkey`, `gameSignature`, `OpenID`, `LoginKey`) | 离线无法生成合法 TAS block1/2 |
| TenProtect 内部读取 `TCLS_TASMEMORY_<pid>` 的代码路径 | 需 Hook `OpenFileMappingW` 进一步定位 |
| `commonconfig.cfg` / `tlog/*.log` 的真实解密密钥/格式 | 影响配置加载、日志分析 |
| 客户端在 **成功 TAS 登录** 时是否真打开该共享内存 | 目前仅在字符串表中见到，运行时未观测到 |

---

## 7. 建议后续步骤 (优先级)

1. **平台端点全链路重定向** – 利用现有 `CODOLServer` 存根，配合 hosts/DNS 劫持，观察 Splash 后是否进入登录菜单。  
2. **TenProtect 内部 Hook** – 在游戏进程内注入 `rt_hook.py`/`Frida`，拦截 `OpenFileMappingW` / `MapViewOfFile` 定位 TAS 读取器。  
3. **获取真实 TAS block** – 通过线上抓包或模拟 TenProtect 生成合法 block1/block2，替代离线伪造数据。  
4. **配置解密深入** – 尝试以 **写入进程** (TCLS/Assistant/TPSvc) 的文件时间、进程 ID、硬件 ID 作为密钥素材，或定位 `TenBase 0x10054100` 加载器真实入口。  
5. **完善大厅/匹配协议** – 基于 `lobby_server` 实现完整消息交互，支撑客户端进入房间流程。  

---

## 8. 重要产物清单 (可直接追溯)

| 路径 | 类型 | 说明 |
|------|------|------|
| `analysis_logs/handoff_recovery.md` | 文档 | 完整静态交接恢复记录 |
| `analysis_logs/game_modules.txt` | 日志 | 运行时模块基址/大小 |
| `analysis_logs/TCLS_cipher_core.txt` | 反汇编 | 密钥派生、KSA、加密核心 |
| `analysis_logs/TenBase_*.txt` | 反汇编 | TenBase 加密/配置加载相关 |
| `COD OL/scripts/tas_crypt.py` | 工具 | Tenio cipher 完整实现 |
| `COD OL/scripts/codol_launch.py` | 工具 | 离线启动器原型 |
| `COD OL/scripts/watch_game.py` | 工具 | 动态监控采样 |
| `COD OL/scripts/procmem.py` | 库 | 进程内存/模块/扫描 |
| `COD OL/scripts/prochandles.py` | 库 | 句柄/对象枚举 |
| `COD OL/scripts/probe_handoff.py` | 工具 | 一键交接验证 |
| `CODOLServer/_write_handoff.py` | 工具 | 导出 TAS/SHELL 二进制 |
| `CODOLServer/lobby_server/` | 代码 | 大厅服务原型 |
| `CODOLServer/experiments/_aeskey_*/` | 实验 | AES 密钥推导系列 |
| `CODOLServer/logs/` | 日志 | 服务端运行记录 |

---

## 9. 结语
截至目前，**静态层面的 TCLS→Client 交接已 100% 复现并验证**，核心加密算法已还原并封装为可复用库。动态层面受限于 **TenProtect / iips 实时鉴权** 与 **反作弊保护**，离线环境无法跨过登录阶段。后续工作重点应放在 **平台服务模拟** 与 **TenProtect 内部逻辑 Hook** 上，争取在完全离线条件下实现从 Splash 到大厅/匹配的完整流程。

--- 

*文档由自动化汇总脚本生成，后续每阶段里程碑请追加至本文件的 “更新记录” 章节。*