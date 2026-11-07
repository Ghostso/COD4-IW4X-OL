# EARLY_SERVER_00 — 样本冻结与完整性基线

> 阶段 0 交付物。本报告只描述**静态文件证据**；未启动任何样本程序。

## 1. 样本标识

| 项 | 值 |
|---|---|
| 样本名称 | CODOL-AlphaBuild By Antia（2026-10-06） |
| 样本根目录 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server` |
| 上级整包目录 | `...\CODOL-AlphaBuild By Antia\`（含 `CODOL_Server` 与 `CODOL_Client`） |
| 样本形式 | **已解压目录**（非压缩包、非安装镜像） |
| 访问模式 | **只读**。本阶段及后续阶段均未写入、覆盖、重命名样本内任何文件 |
| 分析输出目录 | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\`（独立于样本，也独立于现有 CODOL 工程） |

**样本形式判定依据**：根目录直接可见 `dedicated\`、`lobby\`、`build\`、`patcher\`、`tools\`、`resource\` 以及 `START-*.cmd`/`STOP-ALL.cmd` 等文件；`dedicated\.git\` 与 `dedicated\obj\`、`dedicated\dis\` 等构建产物目录同时存在（`dedicated` 目录顶层清单）。无 `.zip/.7z/.rar/.iso/.tar` 分卷存在于服务端根；根目录内仅 4 个 archive 类别文件且均为子目录内的资源/工具压缩件（见 §5）。

## 2. 分析时间与工具版本

| 项 | 值 |
|---|---|
| 清单生成时间（UTC） | 2026-10-11T03:41:53Z（`00_BASELINE\_summary.json` 的 `generated_utc`） |
| 报告生成时间（本地） | 2026-10-11（Asia/Shanghai） |
| Python | 3.11.9（`C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe`） |
| pefile | 2024.8.26 |
| 清单工具 | `_tools\manifest.py`（多线程 SHA-256） |
| 校验工具 | `00_BASELINE\EARLY_SERVER_00_HASH_VERIFY.py`（`--root` 参数，只读） |
| PE 目录工具 | `_tools\pe_catalog.py` |
| 客户端清单工具 | `_tools\client_manifest.py` |

## 3. 总体统计（CONFIRMED）

| 指标 | 值 |
|---|---|
| 文件总数 | **15,754** |
| 总字节 | **635,442,074 B** |
| 总大小 | **606.005 MiB**（≈ 0.635 GB 十进制；即 606.005 MiB） |
| 不可读文件 | **0** |
| 清单耗时 | 3.53 s |

来源：`00_BASELINE\_summary.json`。

整包对照（`CODOL_Server` + `CODOL_Client`）：约 **16,530 文件 / ≈ 7.66 GB**（见 §6 客户端清单）。

## 4. 顶层目录体积（CONFIRMED）

| 目录 | 文件数 | 体积 |
|---|---:|---:|
| `build\` | 7,675 | 332.62 MiB |
| `dedicated\` | 7,687 | 212.06 MiB |
| `patcher\` | 13 | 29.31 MiB |
| `lobby\` | 310 | 20.40 MiB |
| `tools\` | 20 | 0.45 MiB |
| `_purge_backup_20261005_200601\` | 23 | 0.41 MiB |
| `_clone_backup_20261005_203207\` | 6 | 0.32 MiB |
| `_clone_backup_20261005_203212\` | 6 | 0.32 MiB |
| `resource\` | 2 | 0.29 MiB |
| `local-stack-logs\` | 2 | ≈0.00 MiB |

> `build\` 体积主要来自 Python 隔离环境（`build\pyenv\` 7,633 文件 / 197.63 MiB）与 PyInstaller（`build\pyinstaller\` 30 文件 / 113.14 MiB），属打包/运行环境，不是游戏逻辑。三个 `_*_backup_*` 目录为作者的历史备份快照，与复用价值无关（见阶段 4 排除项）。

### 4.1 关键子树（CONFIRMED）

`dedicated\`：

| 子目录 | 文件数 | 体积 | 说明 |
|---|---:|---:|---|
| `tools\` | 1,213 | 93.67 MiB | 含 MSYS2/构建工具与第三方库 |
| `bin\` | 1,390 | 48.28 MiB | 可执行服务端、插件、运行态 home |
| `docs\` | 398 | 26.80 MiB | 逆向/移植文档（核心知识资产） |
| `src\` | 1,770 | 24.42 MiB | **C/C++ 服务端源码（核心代码资产）** |
| `obj\` | 1,082 | 7.38 MiB | 中间目标文件 |
| `.git\` | 1,366 | 4.87 MiB | 仓库元数据（无有效提交，见阶段 1） |
| `plugins\` | 103 | 2.27 MiB | 8 个插件 DLL 及其源码 |
| `tests\` | 153 | 1.21 MiB | 单元/集成测试 |
| `scripts\` | 68 | 1.07 MiB | 运行脚本 |
| `lib\` | 5 | 1.14 MiB | 静态库 |

`lobby\`：

| 子目录 | 文件数 | 体积 |
|---|---:|---:|
| `resources\` | 74 | 7.12 MiB |
| `captures\` | 4 | 5.49 MiB |
| `docs\` | 40 | 2.05 MiB |
| `demonware\` | 39 | 1.07 MiB |
| `career\` | 24 | 0.72 MiB |
| `store\` | 20 | 0.72 MiB |
| `catalogue\` | 24 | 0.58 MiB |
| `handoff\` | 16 | 0.49 MiB |

## 5. 文件类别分布（CONFIRMED，按扩展名/签名归类）

| 类别 | 文件数 | 字节 |
|---|---:|---:|
| other | 5,457 | 191,851,465 |
| source | 2,739 | 72,376,823 |
| script | 2,587 | 17,577,783 |
| no-extension | 1,647 | 8,782,836 |
| game-script | 1,281 | 19,091,863 |
| object | 867 | 18,679,600 |
| doc | 345 | 6,417,970 |
| text | 235 | 9,689,474 |
| image | 232 | 14,139,358 |
| PE-library | 171 | 134,122,138 |
| config | 112 | 12,373,538 |
| PE-executable | 36 | 58,745,113 |
| log | 19 | 31,227,011 |
| binary-data | 11 | 29,949,047 |
| static-lib | 5 | 1,340,418 |
| archive | 4 | 3,714,286 |
| database | 2 | 561,152 |
| resource | 2 | 252,102 |
| cert-material | 1 | 272,441 |
| game-archive | 1 | 4,277,656 |

> 类别计数按文件扩展名/签名启发式归类，含 `build\pyenv` 与 `build\pyinstaller` 中大量与游戏无关的 Python 运行库文件（`other`/`source`/`no-extension` 的主要来源）。**真正的服务端二进制只有 12 个 PE**，见阶段 1。

## 6. 附带客户端样本清单（CONFIRMED）

任务书要求"确认早期版本的客户端—服务端配套关系"，因此对同批次客户端一并做了只读清单：

- `00_BASELINE\EARLY_SERVER_00_CLIENT_FILE_MANIFEST.csv` — `CODOL_Client` 共 **755 文件 / 6,983.58 MiB**。
- 客户端关键指纹见阶段 5。

## 7. 完整性校验结果（CONFIRMED）

校验脚本：`00_BASELINE\EARLY_SERVER_00_HASH_VERIFY.py`（读取 `EARLY_SERVER_00_FILE_MANIFEST.csv` 的 `relpath/size/sha256`，重新计算并比对，同时报告新增文件）。

执行结果（`_raw\hash_verify_result.txt`）：

```
manifest entries : 15754
  ok             : 15754
  changed        : 0
  missing        : 0
  read errors    : 0
  new/extra files: 0
```

结论：**清单与样本当前状态完全一致，样本在本轮分析期间未发生变化**。后续任何时候可用同一脚本重放校验（只读，不写入样本）。

## 8. 交付物索引（阶段 0）

| 文件 | 内容 |
|---|---|
| `00_BASELINE\EARLY_SERVER_00_SAMPLE_BASELINE.md` | 本报告 |
| `00_BASELINE\EARLY_SERVER_00_FILE_MANIFEST.csv` | 15,754 行全量清单（relpath, size, sha256, mtime_utc, ext, category, read_error） |
| `00_BASELINE\EARLY_SERVER_00_HASH_VERIFY.py` | 只读重校验脚本 |
| `00_BASELINE\EARLY_SERVER_00_UNREADABLE_FILES.md` | 不可读/可疑文件报告 |
| `00_BASELINE\EARLY_SERVER_00_CLIENT_FILE_MANIFEST.csv` | 附带客户端清单 |
| `00_BASELINE\_summary.json` | 机器可读汇总 |
| `_raw\hash_verify_result.txt` | 校验原始输出 |

## 9. 证据等级说明

本报告全部条目为 **CONFIRMED**（可由磁盘字节直接复算）。未使用推测。样本内未观察到、但任务书关注的模块（如专用数据库服务、独立登录服务进程）在阶段 1 以 `NOT_OBSERVED` 标注，不等同于"不存在"。

