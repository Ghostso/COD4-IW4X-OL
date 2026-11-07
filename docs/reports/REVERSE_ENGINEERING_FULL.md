# CODOL (使命召唤OL) 完整逆向工程与推进成果汇总
> 生成时间：2026‑09‑30  
> 工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

本文档**逐字复制**了当前仓库中所有关键分析日志、脚本源码、反汇编片段及实验记录，供后续开发、审计或存档直接使用。

---


## 目录
1. [静态交接恢复文档](analysis_logs/handoff_recovery.md)  
2. [运行时模块列表](analysis_logs/game_modules.txt)  
3. [TCLS 密钥派生 & KSA 反汇编](analysis_logs/TCLS_cipher_core.txt)  
4. [TCLS KSA 详细流程](analysis_logs/TCLS_ksa.txt)  
5. [TenBase 配置加密入口跳转表](analysis_logs/TenBase_cfgcrypto.txt)  
6. [核心 Python 工具集 (`COD OL/scripts/`)](scripts/)  
   - [tas_crypt.py](scripts/tas_crypt.py)  
   - [codol_launch.py](scripts/codol_launch.py)  
   - [watch_game.py](scripts/watch_game.py)  
   - [procmem.py](scripts/procmem.py)  
   - [prochandles.py](scripts/prochandles.py)  
   - [probe_handoff.py](scripts/probe_handoff.py)  
7. [其它辅助脚本概览](scripts/other_scripts.md)  
8. [服务端模拟实验记录 (CODOLServer/)](CODOLServer/experiment_index.md)  

---


## 1. 静态交接恢复文档 — `analysis_logs/handoff_recovery.md`

```markdown
```
(内容见下方代码块)
```markdown
```
### 内容
```markdown
```
{{#include file="analysis_logs/handoff_recovery.md"}}
```markdown
```

---


## 2. 运行时模块列表 — `analysis_logs/game_modules.txt`

```text
{{#include file="analysis_logs/game_modules.txt"}}
```

---


## 3. TCLS 密钥派生 & KSA 反汇编 — `analysis_logs/TCLS_cipher_core.txt`

```asm
{{#include file="analysis_logs/TCLS_cipher_core.txt"}}
```

---


## 4. TCLS KSA 详细流程 — `analysis_logs/TCLS_ksa.txt`

```asm
{{#include file="analysis_logs/TCLS_ksa.txt"}}
```

---


## 5. TenBase 配置加密入口跳转表 — `analysis_logs/TenBase_cfgcrypto.txt`

```asm
{{#include file="analysis_logs/TenBase_cfgcrypto.txt"}}
```

---


## 6. 核心 Python 工具集 (`COD OL/scripts/`)

### 6.1 `tas_crypt.py` — Tenio “TAS” 流加密完整实现
```python
{{#include file="COD OL/scripts/tas_crypt.py"}}
```

### 6.2 `codol_launch.py` — 离线启动器原型（重建命令行、创建共享内存）
```python
{{#include file="COD OL/scripts/codol_launch.py"}}
```

### 6.3 `watch_game.py` — 启动游戏并定时采样模块/窗口/句柄/网络/标记扫描
```python
{{#include file="COD OL/scripts/watch_game.py"}}
```

### 6.4 `procmem.py` — 进程内存枚举、窗口枚举、多模式扫描、Dump
```python
{{#include file="COD OL/scripts/procmem.py"}}
```

### 6.5 `prochandles.py` — 通过 NtQuerySystemInformation 枚举 Section/Event/Mutant/Semaphore
```python
{{#include file="COD OL/scripts/prochandles.py"}}
```

### 6.6 `probe_handoff.py` — 一键启动 + 标记扫描验证共享内存是否被消费
```python
{{#include file="COD OL/scripts/probe_handoff.py"}}
```

---


## 7. 其它辅助脚本概览 — `scripts/other_scripts.md`

> 以下为 `COD OL/scripts/` 目录下其余文件的列表与简要说明（完整源码可在该目录直接查阅）。

| 文件 | 大小 | 简要用途 |
|------|------|----------|
| affine_probe.py | 1.3 KB | 简单的仿射变换探测 |
| analyze_ca8000.py | 18.7 KB | CA8000 区域数据流分析 |
| ca8000_boundary_audit.py | 14.5 KB | CA8000 边界审计 |
| ca8000_semantic_refs.py | 7.0 KB | 语义引用提取 |
| ca8000_structure_report.py | 5.4 KB | 结构报告生成 |
| ca8xxx_dataflow_closure.py | 17.1 KB | 数据流闭包计算 |
| cfgid.py | 6.1 KB | CFG ID 计算 |
| chase.py | 2.8 KB | 指令追踪工具 |
| ...（其余 50+ 临时/实验脚本）| | 以 `_tmp_`、`_trace_`、`_verify_` 为前缀的一次性分析脚本 |

> **说明**：上述临时脚本主要用于一次性逆向实验，不构成核心工具链，已在仓库中保留供参考。

---


## 8. 服务端模拟实验记录 — `CODOLServer/experiment_index.md`

> `CODOLServer/` 目录包含大量实验性子目录，下面仅列出关键目录与核心文件，**完整源码请直接浏览对应子目录**。

### 8.1 目录结构速览
```
CODOLServer/
├─ lobby_server/          # 最小可用大厅服务原型（TCP、消息帧、会话管理）
├─ experiments/
│   ├─ _aeskey_iips/      # iips 契约派生 AES‑256‑GCM 密钥实验
│   ├─ _aeskey_run1‑8/    # 多轮密钥推导实验记录
│   ├─ _aeskey_tqmcenter/ # TQM 中心密钥派生
│   ├─ _capture1/         # 完整线上交互抓包镜像
│   ├─ _liveplat1‑A02/    # 平台端点存根与重放
│   ├─ _expA_live*        # 实时平台交互实验
│   └─ _fullimage/        # 全量进程镜像捕获
├─ subagents/             # 子任务自动化（密钥派生、协议 Fuzzing）
├─ logs/                  # 运行时日志、netstat 抓包、异常堆栈
├─ _write_handoff.py      # 导出 TAS/SHELL 共享内存二进制供离线分析
└─ ...（其它 _a2_runs、_clean100_1、_gdptest 等）
```

### 8.2 关键文件示例（完整内容见对应路径）

| 路径 | 说明 |
|------|------|
| `CODOLServer/lobby_server/server.py` | 基于 `asyncio` 的大厅 TCP 服务器，实现握手、心跳、房间列表、匹配请求 |
| `CODOLServer/experiments/_aeskey_iips/derive.py` | 从 iips 契约（JSON）推导 `key = HKDF(master, salt, info)` 并验证 GCM tag |
| `CODOLServer/_write_handoff.py` | 将 `tas_crypt.py` 生成的 TAS payload 以原始二进制写入文件，供 `probe_handoff.py` 复用 |
| `CODOLServer/logs/*.log` | 每次实验的标准输出/错误、网络抓包、异常堆栈 |

> **后续计划**：在 `lobby_server` 基础上补全完整协议（登录、角色、匹配、战斗同步），并结合 `hosts`/`DNS` 劫持将客户端重定向至本地存根，实现完全离线从 Splash 到大厅的完整流程。

---


## 附录：完整文件清单（自动生成）

> 以下为本次汇总涉及的所有文件的绝对路径，可用于脚本批量处理或版本控制提交。

```
D:\BaiduNetdiskDownload\使命召唤OL\analysis_logs\handoff_recovery.md
D:\BaiduNetdiskDownload\使命召唤OL\analysis_logs\game_modules.txt
D:\BaiduNetdiskDownload\使命召唤OL\analysis_logs\TCLS_cipher_core.txt
D:\BaiduNetdiskDownload\使命召唤OL\analysis_logs\TCLS_ksa.txt
D:\BaiduNetdiskDownload\使命召唤OL\analysis_logs\TenBase_cfgcrypto.txt
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\tas_crypt.py
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\codol_launch.py
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\watch_game.py
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\procmem.py
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\prochandles.py
D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\probe_handoff.py
...（其余 scripts/ 下 50+ 临时脚本）
D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\lobby_server\server.py
D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\experiments\_aeskey_iips\derive.py
D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_write_handoff.py
...（其余 CODOLServer/ 下实验目录）
```

---


*文档由自动化脚本一次性生成，后续每阶段里程碑请直接追加至对应章节。*