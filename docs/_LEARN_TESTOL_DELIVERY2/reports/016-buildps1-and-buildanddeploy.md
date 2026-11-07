# 学习报告 016（重开）— `build.ps1` + `BuildAndDeploy.bat`（发现版本号冲突）

**学习范围**：`source\tools\build.ps1`（关键段）+ `source\BuildAndDeploy.bat`（815 B 全文）
**性质**：全实测
**★★★ 本报告发现交付包内**两个互相矛盾的客户端版本号**：`3.19.26.22` vs `3.3.3.3`**

---

# 第一部分：`source\BuildAndDeploy.bat`（815 B / 31 行，全文）

## 一、★★★★★ 版本号冲突（本报告最重要）

### `BuildAndDeploy.bat:21` 逐字

```cmd
echo [ERROR] Not a CODOL 3.3.3.3 game directory: %GAME_DIR%
```

### `run.cmd:9` 逐字

```cmd
rem  Needs: the 3.19.26.22 client itself + Python 3.14 (pefile, capstone).
```

★★★ **⇒ **两个不同的客户端版本号**：**
```
BuildAndDeploy.bat  →  CODOL 3.3.3.3
run.cmd             →  CODOL 3.19.26.22
```

★★★ **⇒ 这不是笔误 —— 两个数字**差了一个数量级**（3.3.3.3 vs 3.19.26.22）。**

### ★★★ 与记忆的对照

**记忆 `codol-reference-lineage-iw4x-not-olmod` 逐字**：
> 用户指正: **可靠性 IW4X(IW4) > CoD4X(IW3) > ol-mod**；
> 证据 = ol-mod 自己在 `net_chan_mp.hpp` 写"**3.3.3.3 用 6 收尾；OLfinal 用 5**"
> ⇒ 它服务的是 **3.3.3.3**、把我们的目标当**另一个 build**。

★★★ **⇒ **铁证吻合**：**
```
ol-mod 上游服务的是 3.3.3.3          ← BuildAndDeploy.bat 的版本号
我们的目标客户端是 3.19.26.22        ← run.cmd 的版本号
```

★★★ **⇒ `BuildAndDeploy.bat` 是**上游 ol-mod 的原始脚本**（未改版本号），
而 `run.cmd` 是本包作者**为 3.19 客户端写的**。**

★ **⇒ 这就是 `BUILD.md:53` 说的"方式 B（**源码自带**）" —— 它是**上游原物**，不是本包的。**

★★ **⇒ 用方式 B 会**拒绝**我们的 3.19 客户端目录（因为它检查 3.3.3.3）。**

---

## 二、★★★ `BuildAndDeploy.bat` 的完整流程（逐行）

```cmd
@echo off
setlocal

cd /d "%~dp0"                       ← 切到脚本目录

set "MODE=%~1"
if "%MODE%"=="" set "MODE=release"   ← 默认 release
if /i not "%MODE%"=="release" if /i not "%MODE%"=="debug" (
    echo Usage: %~nx0 [release^|debug]
    exit /b 2
)

set "GAME_DIR="
if exist "config\codol-game-dir.txt" set /p "GAME_DIR="<"config\codol-game-dir.txt"
if defined GAME_DIR goto game_dir_set
echo [ERROR] Add the CODOL game directory to config\codol-game-dir.txt.
exit /b 2

:game_dir_set
if exist "%GAME_DIR%\codoMP_client_shipRetail.exe" goto game_dir_valid
echo [ERROR] Not a CODOL 3.3.3.3 game directory: %GAME_DIR%   ← ★★★ 版本号
exit /b 2

:game_dir_valid
powershell.exe -NoProfile -ExecutionPolicy Bypass ^
    -File "%~dp0tools\distribution\InstallCodolRuntime.ps1" ^
    -GameDirectory "%GAME_DIR%" ^
    -Mode "%MODE%"
exit /b %errorlevel%
```

### ★★★ 五个检查点

| # | 检查 | 失败行为 |
|---|---|---|
| 1 | 参数是 `release` 或 `debug` | 打印用法，`exit /b 2` |
| 2 | `config\codol-game-dir.txt` 存在 | `[ERROR] Add the CODOL game directory...`，`exit 2` |
| 3 | 该文件里有非空路径 | 同上（`if defined GAME_DIR`） |
| 4 | 路径下有 `codoMP_client_shipRetail.exe` | ★★★ **`[ERROR] Not a CODOL 3.3.3.3 game directory`** |
| 5 | 调用 `tools\distribution\InstallCodolRuntime.ps1` | 透传 errorlevel |

★★★ **⇒ 第 4 项**只检查 exe 存在**，**不检查版本**。**
**报错文字里的 "3.3.3.3" 是**硬编码的文案**，不是实际校验。**

★ **⇒ 所以对 3.19 客户端，**这项检查会通过**（exe 存在），只是错误文案里的版本号是旧的。**

★★ **⇒ 版本号冲突是**文案层面的**，不是**行为层面的**。**

★★★ **⇒ 但仍是一个**明确的信号**：这个脚本来自 3.3.3.3 时代，未随 3.19 更新。**

---

## 三、★★ `config\codol-game-dir.txt` **确实不存在**

★★ **实测（上一轮）：**
```
source\config\codol-game-dir.txt   ->  (missing)
```

★★★ **⇒ `BuildAndDeploy.bat` **必然失败**在第 2 步（`[ERROR] Add the CODOL game directory...`）。**

★ **⇒ 这与 `BUILD.md:16` 的"`source\config\codol-game-dir.txt` 内写客户端根路径"一致 ——**
**但该文件**没有随包交付**，需要用户自己创建。**

★★ **⇒ 所以 `BUILD.md` 的"方式 B"**需要额外手工步骤**（创建这个文件）。**

---

## 四、★★★ `InstallCodolRuntime.ps1` 是实际执行者

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass ^
    -File "%~dp0tools\distribution\InstallCodolRuntime.ps1" ^
    -GameDirectory "%GAME_DIR%" ^
    -Mode "%MODE%"
```

★★ **⇒ 真正的部署逻辑在 `source\tools\distribution\InstallCodolRuntime.ps1`。**

★ **⇒ 这是**第三个部署路径**（前两个：`deploy.ps1` 与 `BuildAndDeploy.bat`）。**

---

# 第二部分：`source\tools\build.ps1`（关键段）

## 五、★★★ 参数与 `ValidateSet`（第 2–4 行）

```powershell
param(
    [ValidateSet("build", "test", "clean", "configure", "stage")]
    [string]$Action = "build",
    ...
)
```

★★★ **⇒ `ValidateSet` 明确限定 5 个值 —— 与 `BUILD.md:29` 的"`-Action` 可选值：
`build` / `test` / `clean` / `configure` / `stage`"**完全一致** ✓**

---

## 六、★★★ xmake 与 vcpkg 的检查（第 16 / 23–35 行）

```powershell
throw "xmake was not found in PATH or at $BundledXmake"        # 第 16 行

$VcpkgRoot = $env:VCPKG_ROOT                                    # 第 23 行
...
throw "Set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe"   # 第 31 行

$env:VCPKG_ROOT = (Resolve-Path -LiteralPath $VcpkgRoot).Path   # 第 34 行
$env:PATH = "$env:VCPKG_ROOT;$env:PATH"                         # 第 35 行
```

★★★ **⇒ 第 31 行的报错**与 `BUILD.md:18` 引用的原文**逐字一致** ✓**
```
BUILD.md:18  throw "Set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe"（原文）
build.ps1:31 throw "Set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe"
```

★★ **⇒ `BUILD.md` 的引用是**准确的**。**

★ **⇒ `$BundledXmake` —— 说明有"随包 xmake"的回退（但包里没有）。**

---

## 七、★★★ `ol_deploy` 与 `stage`（第 54 / 60 行）

```powershell
# 第 54 行
# ol_deploy target cannot recursively invoke the installer.
...
# 第 60 行
if ($Action -eq "stage") {
```

★★★ **⇒ 第 54 行的注释确认了 `ol_deploy` 的存在与**递归调用风险**：**
```
# ol_deploy target cannot recursively invoke the installer.
```

★★ **⇒ 这与 `BUILD.md:70` 的警告"不要裸跑 `xmake build`（会连带触发部署钩子）"**完全对应** ✓**

★ **⇒ 且 `build.ps1` **专门处理**了这个情况（`ol_deploy` 不能递归调 installer）。**

★★★ **⇒ 这是**上游作者已经踩过这个坑**的证据。**

---

## 八、★★★ `stage` 的实际行为（第 60 行）

```powershell
if ($Action -eq "stage") {
```

★★ **⇒ `stage` 是一个**独立分支**，不是 `build` 的附加步骤。**

★★★ **⇒ 与 `BUILD.md:26` 的"`-Action stage` → 生成 `build\stage\codol`"一致。**

★ **⇒ 而 `1-构建.cmd:41-45` 是先 `build` 再 `stage`（两步）。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **版本号冲突** | **`3.19.26.22`（run.cmd）vs `3.3.3.3`（BuildAndDeploy.bat）** |
| 2 | 冲突性质 | ★ **文案层面**（实际只检查 exe 存在） |
| 3 | ★ 与记忆吻合 | ol-mod 上游服务 **3.3.3.3** ✓ |
| 4 | `config\codol-game-dir.txt` | ★★ **不存在** ⇒ 方式 B 必然失败 |
| 5 | `BuildAndDeploy.bat` 检查点 | **4 个** |
| 6 | 实际部署者 | `tools\distribution\InstallCodolRuntime.ps1` |
| 7 | `build.ps1` `ValidateSet` | **5 个 action** ✓ 与 BUILD.md 一致 |
| 8 | ★ `build.ps1:31` 报错 | **与 BUILD.md:18 引用逐字一致** ✓ |
| 9 | ★ `$BundledXmake` | 随包 xmake 回退（包里没有） |
| 10 | ★★ `build.ps1:54` | **`ol_deploy` 不能递归调 installer** |
| 11 | `stage` | 独立分支，非 build 附加 |

---

## 十、结论

### 1. ★★★★★ 交付包内**两个客户端版本号并存**，且都有出处

```
run.cmd:9             3.19.26.22   ← 本包作者写的（正确目标）
BuildAndDeploy.bat:21 3.3.3.3      ← 上游 ol-mod 原物（未改）
```

★★★ **⇒ 这与记忆里"ol-mod 服务 3.3.3.3、把我们的目标当另一个 build"**完全吻合**。**

★ **⇒ **这是第三次独立确认**这条血统关系：**
```
① 记忆（用户指正 + net_chan_mp.hpp 注释）
② 上一轮 PE 实测（TimeDateStamp 0x6096930A = 3.19）
③ 本报告（BuildAndDeploy.bat 的硬编码 3.3.3.3）
```

### 2. ★★★ 版本号冲突**只在文案层**，不影响行为

★ **⇒ `BuildAndDeploy.bat` 只检查 `codoMP_client_shipRetail.exe` 存在，不校验版本。**

### 3. ★★ `BUILD.md` 的"方式 B"需要**额外创建 `config\codol-game-dir.txt`**

★ **⇒ 该文件未随包交付。**

### 4. ★★★ `build.ps1` 的报错与 `BUILD.md` 引用**逐字一致**

★ **⇒ 说明 `BUILD.md` 是**对着源码写的**，可信度高。**

### 5. ★★ 上游已处理 `ol_deploy` 的递归调用风险

---

## 十一、下一步

- `bundle\` 五个脚本逐字节（`launch_chain.py` 已在上轮部分读过，需完整重读）
- `bundle\` 五个证书文件逐字节
- `payload\` 四个插件 PE + 四个 loader 二进制
- `source\tools\distribution\InstallCodolRuntime.ps1`
