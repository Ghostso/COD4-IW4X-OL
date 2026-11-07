# T2_3_ENVIRONMENT_GUARDS_REPORT — 运行准备阻塞（G-C1/C2/C3/C4）

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd…`）
**本轮性质**：离线修复与离线验收。**未启动游戏、未附加 Frida、未读内存、未部署、未终止任何真实游戏进程。**

---

## 0. 结论

| 阻塞 | 状态 | 一句话 |
| --- | --- | --- |
| **G-C4** 版本约束分裂 | ✅ 已解决 | 收敛为 `frida>=16.5,<19`；工具运行前校验安装版本，范围外 `unavailable` 且不附加 |
| **G-C1** 游戏目录前置条件 | ✅ 已解决 | 新增 `verify-target` 动作与已批准基线 `config/codol-target-build.json`；显式 `--game-dir`；缺目录/缺文件/哈希或版本不符**一律失败关闭** |
| **G-C2** 终止前 PID 复核 | ✅ 已解决 | `terminate_pids` 在每次 `taskkill` 前重新核对映像名（并在可提供时核对全路径）；身份无法确认则**拒绝终止** |
| **G-C3** 构建级身份确认 | ✅ 已解决 | 协议 §10 增补：可重复的 `verify-target` 命令 + 逐 PID 运行时确认四步 |

## 1. G-C4：统一版本约束

### 1.1 三项核对

| 项 | 值 | 来源 |
| --- | --- | --- |
| 当前安装 | **frida 16.5.9**（Python dist 与 `frida --version` 一致），frida-tools 13.0.1 | `importlib.metadata` / CLI |
| 修复前声明 | `frida>=17,<18` | `tools/runtime/requirements-codol.txt:1` |
| 修复后 JS API 实际兼容范围 | 所选 `Module.findExportByName(null, name)` 存在于 **12.6.0 – 18.8.0**，**19.0.0 起被移除** | `types/frida-gum` 全版本扫描（`frida_api_audit.txt`） |

### 1.2 选择的策略

`frida>=16.5,<19`

- 下界取**唯一完成离线验证的版本线** 16.5（安装 16.5.9 在其内）；
- 上界取**所选 API 被移除的版本** 19.0.0（开区间），使声明与代码不会再次分裂；
- `requirements-codol.txt` 与工具常量 `SUPPORTED_FRIDA_RANGE` 同值，并有一致性单测；
- **未**升级任何依赖（任务要求不得未经说明直接升级全套依赖）。

### 1.3 运行期守卫（失败关闭）

`run()` 在 `frida.get_local_device()` **之前**校验 `frida.__version__`：

``
    installed_frida = getattr(frida, "__version__", None)
    if not frida_version_supported(installed_frida):
        return report(RESULT_UNAVAILABLE, { ... "refusing to run" })
``

分类为 **`unavailable`**（而非 `refused`）：插件**从未被请求**，因此不存在“插件拒绝”这一事实。范围外运行**不会**附加任何进程。

## 2. G-C1：游戏目录与目标构建前置条件

### 2.1 现状核对

| 项 | 值 | 判定 |
| --- | --- | --- |
| `config/codol-game-dir.txt` 内容 | `D:\codo_3.19.26.13_fresh\CoD Online` | 该路径**不存在** |
| 是否已修改该配置 | **否**（项目约定该文件是机器本地默认值，未擅自改动） | ✅ 优先用显式参数消除歧义 |
| 实验沙箱 | `E:\CODOL_SANDBOX\RUN001` | 存在 |

### 2.2 新增：已批准基线（数据，不是代码常量）

`config/codol-target-build.json`（schemaVersion 1）。基线值在批准时**直接读自确认的目标文件**，未从任何报告转录、未从截断哈希推导：

| 字段 | 值 |
| --- | --- |
| image | codoMP_client_shipRetail.exe |
| size | 7841344 |
| sha256 | 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537 |
| fileVersion / productVersion | 1649370 / 1649370 |
| plugin.path | Ayria/Plugins/CodolGameServer.Localnet32 |
| plugin.sha256 | 6D493B820E84A21B096C9914616B75DCEC488920D7AC76867049B20C5C6B2021 |

### 2.3 新增：可重复的校验命令

``
python tools/runtime/CodolGame.py verify-target --game-dir E:\CODOL_SANDBOX\RUN001
``

该动作**只读文件**：不启动游戏、不附加 Frida、不读内存。退出码 0 = 一致，1 = 不符或不可读，2 = 未给出可解析的 `--game-dir`。

实测（证据：`_t2_3_evidence/target_build_verification.txt`）：

| 场景 | 结果 |
| --- | --- |
| `E:\CODOL_SANDBOX\RUN001` | `ok: true`，`size/sha256/file_version` 与基线逐项一致，**exit 0** |
| `E:\CODOL_SANDBOX\NO_SUCH_RUN`（目录不存在） | `ok: false`，`the game directory does not exist`，**exit 1** |
| 未提供可解析的 `--game-dir` | 提示并要求参数，**exit 2** |

### 2.4 失败关闭的完整清单

| 情形 | 结果 |
| --- | --- |
| 基线文件缺失或格式非法 | 失败（**没有**“无基线即通过”的回退） |
| 游戏目录不存在 | 失败 |
| 目标映像缺失 | 失败 |
| 目标映像不可读（`OSError`） | 失败 |
| `size` 不符 | 失败 |
| `sha256` 不符 | 失败 |
| `FileVersion` 无法读取或为空 | 失败 |
| `FileVersion` 不符 | 失败 |
| 基线列出的插件缺失或哈希不符 | 失败 |

## 3. G-C2：终止前 PID 复核

### 3.1 审查结论

原 `terminate_pids` 对**早先枚举到的 PID** 直接执行 `taskkill /PID <pid> /T /F`。G1 只保护 Frida 附加路径；若客户端在枚举与 `taskkill` 之间退出、PID 被复用，就可能结束一个**无关进程树**（`/T`）。

### 3.2 新的安全行为

每个 PID 在 `taskkill` 之前重新确认：

| 情形 | 安全行为 |
| --- | --- |
| 映像查询抛异常（查询失败） | **拒绝终止**，计入失败，打印原因 |
| 映像名与期望不符 | **拒绝终止**，计入失败，警告“PID 可能已被复用” |
| 提供了期望路径但**路径读不到** | **拒绝终止**，计入失败（身份无法确认） |
| 提供了期望路径且**路径不符** | **拒绝终止**，计入失败 |
| 进程已不存在（`process_image_name` 返回 None） | **跳过**：请求的终态已达成，不计失败 |
| 映像与路径均一致 | 执行 `taskkill /PID <pid> /T /F` |
| `taskkill` 返回非零 | 计入失败 |

期望映像按调用点显式给出：客户端 PID → `codoMP_client_shipRetail.exe`；room owner PID → `ol_room_owner.exe`（全部 12 处调用点已逐一核对，见 §3.4）。

### 3.3 残余竞态（明确披露）

路径校验**缩小但不能消除** PID 复用窗口：路径读取与 `taskkill` 是两次独立操作，二者之间仍存在极短窗口。因此：

- 本机制**不是**进程身份的密码学保证；
- 协议 §5.4 仍要求人工/脚本在终止前复核，并优先使用单 PID 手工 `taskkill`。

### 3.4 调用点核对

| 调用点 | 期望映像 |
| --- | --- |
| `launch_room_owner` 超时回滚 | `ol_room_owner.exe` |
| `launch_process` 三处回滚（歧义 / 模块链 / 控制端口） | 默认 `codoMP_client_shipRetail.exe` |
| `launch` 状态写入失败 | 默认 |
| `launch_dedicated_pair` 三处回滚 | 混合：客户端默认 + room owner 显式 |
| `launch_client_for_dedicated` 回滚 | 默认 |
| `stop()` | 显式映像表 + （已知 game 目录时）显式路径表 |

### 3.5 测试

9 项新单测覆盖：复核通过才终止、映像不符拒绝、进程已退出跳过、查询失败拒绝、路径读不到拒绝、路径不符拒绝、路径一致放行、非目标期望映像（room owner）、`stop()` 传递正确的映像/路径表。全部使用 mock，**不对任何真实游戏进程做终止测试**。

## 4. G-C3：目标构建确认进入实验协议

在 [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) **追加** §10「T-2.3 增补：目标构建确认（G-C3）」，内容为：

1. **已批准基线**（§10.1，同 §2.2 的表）及其来源声明；
2. **可重复命令**（§10.2）：启动前后各执行一次 `verify-target`；
3. **逐 PID 运行时确认**（§10.3，修订原步骤 3）：
   - `tasklist /FI "IMAGENAME eq codoMP_client_shipRetail.exe"` ⇒ 恰好一个 PID；
   - `(Get-Process -Id <pid>).Path` ⇒ 映像全路径；
   - 对该路径重算 SHA-256 与 FileVersion，与基线逐项比较；
   - 任一项不符/为空/不可读 ⇒ **中止**。
4. **与 G-C2/G-C4 的关系**（§10.4）。

> **改动性质**：只在既有协议**末尾追加**一节，未删除、未改写任何既有条款；协议文件哈希变化已记入 [T2_3_SHA256_MANIFEST.txt](T2_3_SHA256_MANIFEST.txt)（`4512A5A1…` → `F1E3F82F…`）。

**能证明**：附加前该 PID 的映像文件就是已批准构建。
**不能证明**：进程启动后是否被内存补丁改写；步骤 2→3 之间的文件替换竞态；因此**不是**进程身份的密码学保证。

## 5. 未证明 / 未执行（明确披露）

- 未启动客户端，未附加 Frida，未读内存，未部署；**未对任何真实游戏进程执行终止**。
- `verify-target` 校验的是**磁盘文件**，不是**运行中的进程**；运行中身份由协议 §10.3 的逐 PID 步骤负责。
- PID 复用竞态被缩小但**未被消除**。
- 构建身份基于 路径 + SHA-256 + FileVersion，**不是**密码学签名验证。

## 6. 关联交付

- [T2_3_FRIDA_API_FIX_REPORT.md](T2_3_FRIDA_API_FIX_REPORT.md) · [T2_3_REGRESSION_REPORT.md](T2_3_REGRESSION_REPORT.md) · [T2_3_SHA256_MANIFEST.txt](T2_3_SHA256_MANIFEST.txt)
- [T2_2_EXPERIMENT_PROTOCOL.md](T2_2_EXPERIMENT_PROTOCOL.md) §10（G-C3 增补）
- 证据：`_t2_3_evidence/`（`target_build_verification.txt`、`target_build_verification_failure.txt`、`frida_api_audit.txt`）
