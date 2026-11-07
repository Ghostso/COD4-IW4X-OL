# T2_3_FRIDA_API_FIX_REPORT — G-B1 非法 API 修复与版本约束统一

**日期**：2026-10-10
**工作树**：**F = `F:\桌面\ol\ol-mod-olfinal`**（HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，分支 `OLfinal-live`）
**修复文件**：`tools/runtime/CodolGameServerControl.py`、`tools/runtime/requirements-codol.txt`
**本轮性质**：离线修复 + 离线验收。**未启动游戏、未附加 Frida、未读内存、未部署。**

---

## 0. 结论

> **G-B1 已修复，G-C4 已收敛。** 注入脚本不再调用 Frida 19 才存在的 API，改为在 **16.5 – 18.x 全范围**都存在、且在 **19.0.0 被移除**的 `Module.findExportByName(null, name)`；支持范围据此收敛为 `frida>=16.5,<19`，工具在触碰目标前校验安装版本，范围外一律 `unavailable` 且不附加。
>
> 验收不依赖“字符串是否消失”：见 §4 的五项独立验证（官方类型定义全版本扫描、安装二进制扫描、`node --check` 真语法检查、API 面白名单单测、失败分类单测）。

## 1. 缺陷（T-2.2 G-B1）

修复前 `CodolGameServerControl.py` 的注入脚本（HEAD:174）：

``
    for (const exportName of [
        'ExitProcess', 'TerminateProcess', 'RaiseFailFastException',
        'RtlExitUserProcess'
    ]) {
        const address = Module.findGlobalExportByName(exportName);   // <-- 不存在
        if (address === null) continue;
        Interceptor.attach(address, { ... });
    }
``

该循环位于脚本顶层 `try` 内、任何插件导出调用之前，且无逐项 `try/catch`。在 Frida 16.5.9 上 `Module.findGlobalExportByName` 是 `undefined`，调用即抛 `TypeError`，被顶层 catch 捕获后脚本只发出 `result: 'tool-error'`——**`CODOL_GameServerSetEnabled(false)` 永远不会被调用**。

## 2. 修复选择与依据

### 2.1 两个候选 API 的存在区间（离线实测）

对 `types/frida-gum` 全版本逐项扫描（证据：`_t2_3_evidence/frida_api_audit.txt`）：

| 版本 | `static findExportByName(moduleName, exportName)` | `findGlobalExportByName` |
| --- | --- | --- |
| 12.6.0 – 18.8.0（含 16.5.1 / 17.0.0 / 17.3.1 / 18.0.0） | **存在** | **不存在** |
| 19.0.0 / 19.12.0 | **已移除** | **存在** |

安装的 `_frida.pyd`（16.5.9）字符串扫描：`GlobalExport` = 0 次、`findGlobalExportByName` = 0 次，而 `findExportByName` = 29、`getExportByName` = 43（对照组有效）。

⇒ 两个 API 的存在区间**互斥**，不存在同时可用的单一写法；必须二选一。

### 2.2 选择：兼容现有版本的最小修复

任务要求“优先采用兼容现有版本的最小修复，不升级整个 Frida 运行时来绕过单行错误”。因此采用：

``
        const address = Module.findExportByName(null, exportName);
``

参数约定：静态形式的第一个参数是**模块名**，`null` 表示“在全部模块中查找”。这与本机 16.5.9 配套的 frida-tools 13.0.1 自身 agent 的用法一致（`frida_tools/itracer_agent.js` 使用 `Module.getExportByName(null, name)`）。

同时**没有**升级 Frida、没有改动任何插件代码或 ABI。

### 2.3 修复后代码与声明版本的一致性

支持范围收敛为 `frida>=16.5,<19`：

- **下界 16.5**：本机安装 16.5.9 所在版本线，也是本次唯一完成离线验证的版本线；
- **上界 <19**：因为所选 API 在 **19.0.0 被移除**，把范围封闭在 19 之前，声明就不会因为运行时长高而再次变成假的；
- `requirements-codol.txt` 由 `frida>=17,<18` 更新为 `frida>=16.5,<19`；
- 工具新增常量 `SUPPORTED_FRIDA_RANGE` 与 `frida_version_supported()`，在 `run()` 中**先于** `frida.get_local_device()` 校验 `frida.__version__`。

三方（安装 / 声明 / 代码）现在**同区间**：安装 16.5.9 ∈ [16.5, 19) ✅

## 3. 顺带修复：必需导出在构造 NativeFunction 前校验（任务 §二.5）

原先 9 个**必需**导出直接写成 `new NativeFunction(plugin.getExportByName(...))`：导出缺失时 `getExportByName` 抛错，只会落进 `tool-error`。现在统一经过一个校验器：

``
    function nativeExport(module, exportName, returnType, argumentTypes) {
        const address = module.findExportByName(exportName);
        if (address === null)
            throw codolStop('unavailable', module.name + ' does not export ' + exportName);
        return new NativeFunction(address, returnType, argumentTypes);
    }
``

改造的 9 个必需导出：`setEnabled`、`getStatus`、`getNetworkStatus`、`getNetchanStatus`、`getSessionStatus`、`configureGameState`、`getGameStateStatus`、`getConstantConfigStringStatus`、`getTransportStatus`。

- **地址有效性**：`findExportByName` 返回 `null` 时在构造前抛出，绝不会用空地址构造 `NativeFunction`；
- **分类**：导出缺失是“无法请求到插件” ⇒ `unavailable`（**不是** `refused`，也**不是** `confirmed`）；
- 60+ 个**可选**导出保持原有 `try/catch` 不变，缺失时保持 `null`，行为未变。

## 4. 验证（不依赖字符串消失）

| # | 验证 | 方法 | 结果 |
| --- | --- | --- | --- |
| V1 | 修复后代码与声明版本一致 | `types/frida-gum` 12.6.0 → 19.12.0 全版本扫描两个候选 API 的存在区间 | 见 §2.1：所选 API 覆盖 16.5–18.8，19.0.0 起移除；范围 `<19` 与之严格吻合 ✅ |
| V2 | JS 脚本通过静态检查 | 把 `create_script()` 收到的**真实**脚本落盘，用 `node --check` 解析 | exit 0 ✅（单测 `test_the_generated_script_is_syntactically_valid_javascript`） |
| V3 | 脚本只用声明过的 Frida API | 从真实脚本中提取全部 `Object.member` 引用（先剥离 `//` 注释），与本报告 §2.1 依据的官方类型逐项比对 | 集合差为空 ✅（`test_the_script_uses_only_declared_frida_apis`） |
| V4 | 必需导出在校验后才构造 | 断言 `nativeExport` 体内 `address === null` 早于 `return new NativeFunction(`；并断言 4 个关键导出走 `nativeExport` | ✅ |
| V5 | 失败分类不被误判 | 单测覆盖：脚本载入抛异常 ⇒ `tool-error`(1)；必需导出缺失 ⇒ `unavailable`(3)；Frida 版本越界 ⇒ `unavailable`(3) 且 `attach` 未被调用；插件返回 true ⇒ `confirmed`(0)；插件返回 false ⇒ `refused`(2) | ✅ |

### 4.1 与验收标准的对应

| 用户强调的验收标准 | 证据 |
| --- | --- |
| 1. 修复后代码与声明支持的 Frida 版本一致 | V1 + 版本守卫单测（`test_range_boundaries`、`test_the_installed_frida_is_inside_the_declared_range`） |
| 2. JS 脚本能通过静态检查与离线测试 | V2（`node --check`）+ V3（API 白名单）+ 34 项工具单测全绿 |
| 3. API 不可用 / 导出不存在 / 调用异常都不会被误判为成功 | V5（三种失败各自映射到 `tool-error` / `unavailable`，且断言 `!= confirmed`、`!= refused`） |
| 4. 错误 PID 不会进入强制终止调用 | 见 [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md) §3 |
| 5. 目标构建指纹与目录前置条件明确、可重复 | 见同报告 §2 |

## 5. 仍未证明的内容（明确披露）

- 修复后的脚本**从未在任何真实 Frida 运行时中执行过**。V1/V3 基于官方类型定义与安装二进制，V2 只做**语法**解析；因此“脚本能成功载入并找到导出”仍属**待验证**。
- 本机没有 Frida 17.x / 18.x，声明范围内的这些版本同样**未经执行验证**。
- 因此本修复把“确定会失败”变为“静态层面一致、待运行时确认”，而不是“已证明可用”。

## 6. 关联交付

- [T2_3_ENVIRONMENT_GUARDS_REPORT.md](T2_3_ENVIRONMENT_GUARDS_REPORT.md) · [T2_3_REGRESSION_REPORT.md](T2_3_REGRESSION_REPORT.md) · [T2_3_SHA256_MANIFEST.txt](T2_3_SHA256_MANIFEST.txt)
- [T2_2_RUNTIME_READINESS_REVIEW.md](T2_2_RUNTIME_READINESS_REVIEW.md)（G-B1 的发现过程）
- 证据：`_t2_3_evidence/frida_api_audit.txt`、`tool_tests_t23.log`
