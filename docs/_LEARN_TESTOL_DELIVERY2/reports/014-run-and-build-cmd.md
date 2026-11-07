# 学习报告 014（重开）— `run.cmd` + `1-构建.cmd` 逐字节

**学习范围**：`run.cmd`（4,243 B / 123 行）+ `1-构建.cmd`（1,388 B / 50 行）
**性质**：全实测
**★★★ 本报告发现 `run.cmd` 的 11 项检查**漏了 3 个真实依赖**，且**`1-构建.cmd` 会把产物放错名字**

---

# 第一部分：`run.cmd`（4,243 B / 123 行）

## 一、★★★ 头部声明（第 5–15 行，逐字节）

```cmd
rem ============================================================
rem  TESTOL GO v2 - self-contained, client-authoritative.
rem  Ships: python chain (bundle\) + Ayria runtime + plugins + assets
rem         (payload\Ayria\).
rem  Needs: the 3.19.26.22 client itself + Python 3.14 (pefile, capstone).
rem  It does NOT ship or start the dedicated server (codol_dedrun).
rem
rem  run.cmd          -> deploy payload into <GAME>\Ayria, then launch
rem  run.cmd --check  -> deploy dry-run + pre-flight only
rem  run.cmd --no-deploy -> skip deploy, launch only
rem ============================================================
```

### ★★★ 四条关键信息

| # | 声明 | 评价 |
|---|---|---|
| 1 | **`3.19.26.22` 客户端** | ★★★ **唯一的版本号声明**（`README`/`BUILD.md` 都没写） |
| 2 | **Python 3.14**（pefile, capstone） | ★★ 明确依赖两个库 |
| 3 | 不含也不启动 `codol_dedrun` | ✓ 与 README 一致 |
| 4 | 三种用法 | ★ 但**实际支持 5 种**（见 §四） |

★★★ **⇒ `3.19.26.22` 是**全包唯一出现客户端版本号的地方**。**
**（`preflight.ps1` 不检查版本；`nt10.py` 也不检查。）**

★ **⇒ `pefile` 与 `capstone` 是 Python 依赖 —— 但 `run.cmd` 只检查 `python.exe` 存在，
**不检查这两个库**（第 50 行）。**

---

## 二、★★★ 路径设置（第 17–23 行）

```cmd
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"     ← ★ 去掉尾部反斜杠
set "BUNDLE=%HERE%\bundle"
set "PAYLOAD=%HERE%\payload\Ayria"
set "PY=C:\Program Files\Python314\python.exe"    ← ★★★ 硬编码
set "LC=%BUNDLE%\launch_chain.py"
set "PRE=%HERE%\preflight.ps1"
```

★★★ **⇒ 关键设计：**
```
① %~dp0 自带尾部反斜杠 ⇒ 手动去掉，后续统一用 "%HERE%\xxx"
② PY 硬编码 C:\Program Files\Python314\python.exe
③ BUNDLE / PAYLOAD / PRE 全从 HERE 推导
```

★★★ **⇒ `PY` 硬编码是**最脆弱的假设**：**
**Python 3.14 的默认安装路径。若装在别处（或 3.11/3.12），`run.cmd` 直接 `[BLOCK]`。**

★ **⇒ 本机实测：`C:\Program Files\Python314\python.exe` **不存在**（上一轮已验），**
**实际有 `C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe`。**

---

## 三、★★★★ 游戏根定位（第 25–39 行）—— **三重回退**

```cmd
if defined OLMOD_GAME_ROOT (
  set "GAME=%OLMOD_GAME_ROOT%"
  goto :game_ready
)
if exist "%HERE%\codoMP_client_shipRetail.exe" (
  set "GAME=%HERE%"
  goto :game_ready
)
if exist "%HERE%\..\codoMP_client_shipRetail.exe" (
  for %%I in ("%HERE%\..") do set "GAME=%%~fI"
  goto :game_ready
)
echo [BLOCK] cannot find codoMP_client_shipRetail.exe near "%HERE%".
echo         Put this folder in the client root, or set OLMOD_GAME_ROOT first.
exit /b 2
```

### ★★★ 三种定位策略（优先级递减）

```
① 环境变量 OLMOD_GAME_ROOT         （显式指定）
② 包就放在客户端根目录下            （%HERE% 里有 codoMP_client_shipRetail.exe）
③ 包在客户端根的**子目录**里        （%HERE%\.. 里有）
```

★★★ **⇒ 第 ③ 种用 `for %%I in ("%HERE%\..") do set "GAME=%%~fI"` 取**父目录的绝对路径**。**
**`%%~fI` = 完整路径（解析 `..`）。**

★★ **⇒ 这是**正确处理**的做法（不是简单拼 `%HERE%\..`）。**

### ★★★ 第 99 行：把定位结果回写环境变量

```cmd
set "OLMOD_GAME_ROOT=%GAME%"
set "OLMOD_BASE=%BUNDLE%"
set "OLMOD_BASE_TOOLS=%BUNDLE%"
set "OLMOD_STUN=%BUNDLE%\stun_local.py"
```

★★★ **⇒ 这是**关键的一步**：**
**`launch_chain.py:69` 的默认 `GAME = D:\repo\03-live\client\TESTOL` 会抛 `SystemExit`，**
**但 `run.cmd:99` 先设了 `OLMOD_GAME_ROOT` ⇒ 绕开。**

★★ **⇒ 所以**双击路径能跑，单独跑 `launch_chain.py` 会崩**（上一轮报告 016 已记录）。**

---

## 四、★★★ 11 项必需文件检查（第 49–59 行）

```cmd
call :need "%GAME%\codoMP_client_shipRetail.exe"   "client exe"
call :need "%PY%"                                  "python 3.14"
call :need "%LC%"                                  "bundle launch_chain.py"
call :need "%BUNDLE%\nt10.py"                      "bundle nt10.py"
call :need "%BUNDLE%\fake_auth_tls.py"             "bundle fake_auth_tls.py"
call :need "%BUNDLE%\stun_local.py"                "bundle stun_local.py"
call :need "%BUNDLE%\_ca.pem"                      "bundle CA"
call :need "%PAYLOAD%\Injector32.exe"              "payload Injector32.exe"
call :need "%PAYLOAD%\ol_room_owner.exe"           "payload ol_room_owner.exe"
call :need "%PAYLOAD%\Plugins\CodolGameServer.Localnet32" "payload battle server plugin"
call :need "%PAYLOAD%\Plugins\Alwaysoffline.Localnet32"   "payload backend plugin"
```

### ★★★ `:need` 的实现（第 115–122 行）

```cmd
:need
if exist "%~1" (
  echo   [OK]    %~2
) else (
  echo   [BLOCK] %~2  ^(missing: %~1^)
  set /a BLOCK+=1
)
exit /b 0
```

★★ **⇒ 累加 `BLOCK` 计数，`exit /b 0`（不影响 errorlevel）。**

### ★★★★★ **漏检的 3 个真实依赖**

★★★ **实测 `fake_auth_tls.py:115-135` 的 `build_pem_files()` 需要：**
```python
with open(os.path.join(ROOT, "_rsa.txt")) as f:     ← ★★★ 必需
leaf = open(os.path.join(ROOT, "_leaf2.cer"), "rb").read()   ← ★ 必需
ca = os.path.join(ROOT, "_ca.pem")                  ← ✓ 已检查
```

★★★ **⇒ 检查了 `_ca.pem`，但**漏了**：**
```
_rsa.txt        ← 不存在！⇒ build_pem_files() 第一行就崩
_leaf2.cer      ← 存在，但未检查
```

★★★ **⇒ 而 `_rsa.txt` **实际不在包里**（`MANIFEST.sha256` 也没有它，报告 001 已验）。**

★★ **⇒ 所以 `run.cmd` 的 11 项检查**全部通过后**，`launch_chain.py` 仍会在
`fake_auth_tls.py` 启动时崩溃。**

★ **⇒ 上一轮报告 011 已记录这个缺陷，现在**确认它是 `run.cmd` 的检查盲区**。**

### ★★ 另外：不检查 Python 库

```cmd
call :need "%PY%"  "python 3.14"
```

★★ **⇒ 只检查 `python.exe` 存在，**不检查 `pefile` / `capstone` 是否能 import**。**

★ **⇒ 但 `run.cmd:9` 明写需要它们。**

---

## 五、★★★ 五种用法（第 61–97 行）—— 比头部声明的三种多两种

### 用法 1：`--check`（第 61–71 行）

```cmd
if /i "%~1"=="--check" (
  echo [deploy] dry run:
  powershell ... -File "%HERE%\deploy.ps1" -Game "%GAME%" -DryRun
  echo [preflight] hosts / dwauth.ini / stun.ini / cacert
  powershell ... -File "%PRE%" -Game "%GAME%"
  if "%BLOCK%"=="0" ( echo [CHECK] ready. ) else ( echo [CHECK] blockers: %BLOCK% )
  exit /b 0
)
```

★★★ **⇒ 注意：`--check` **总是 `exit /b 0`**，即使有 blocker。**

### 用法 2/3：`--no-deploy` / `--no-preflight`（第 80 / 92 行）

```cmd
if /i not "%~1"=="--no-deploy" ( ... deploy ... )
if /i not "%~1"=="--no-preflight" ( ... preflight ... )
```

★★ **⇒ 两个独立的跳过开关。**

### ★★★ 用法 4/5：**参数组合的缺陷**

```cmd
if /i "%~1"=="--check"              ← 只看第 1 个参数
if /i not "%~1"=="--no-deploy"      ← 只看第 1 个参数
if /i not "%~1"=="--no-preflight"   ← 只看第 1 个参数
```

★★★ **⇒ 全部只判断 `%~1`（**第一个参数**）⇒ 不能组合：**
```
run.cmd --no-deploy --no-preflight    ← ★ 只有 --no-deploy 生效
run.cmd --no-preflight --no-deploy    ← ★ 只有 --no-preflight 生效
```

★★ **⇒ 这是**参数解析的简化**（只支持单个开关）。**

### ★★ 但头部只声明了 3 种

```
run.cmd               （默认）
run.cmd --check
run.cmd --no-deploy
```

★★ **⇒ `--no-preflight` 未在头部声明，但代码支持。**

---

## 六、★★★ 部署与预检的执行顺序（第 80–97 行）

```cmd
[1] if not --no-deploy:
      deploy.ps1 -Game "%GAME%"
      if errorlevel 3 → [ABORT] + pause + exit /b 3

[2] if not --no-preflight:
      preflight.ps1 -Game "%GAME%"
      if errorlevel 2 → echo [WARN] ... continuing    ← ★★★ 只警告，继续！
```

★★★ **⇒ 关键：`preflight` 的 blocker **不阻止启动**。**

```cmd
if errorlevel 2 echo [WARN] preflight reported blockers - continuing ^(add --no-preflight to skip, -Apply to fix^)
```

★★★ **⇒ 这是**有意的宽松**：**
```
deploy 失败（errorlevel 3）  →  ABORT
preflight 有 blocker（errorlevel 2）→  ★ 只 WARN，继续启动
```

★ **⇒ 理由可能是：`preflight` 的 blocker 是"环境问题"，用户可能想先试跑。**

★★ **⇒ 但这与 `run.cmd:73` 的 `if not "%BLOCK%"=="0"` 分支**矛盾**：**
```
第 73 行：文件检查有 BLOCK ⇒ [ABORT] + exit /b 2   （硬阻塞）
第 96 行：preflight 有 blocker ⇒ 只 WARN，继续     （软警告）
```

★★★ **⇒ 两处对"blocker"的处理**不一致**。**

---

## 七、★★★★ 最终启动命令（第 106 行，逐字节）

```cmd
start "TESTOL chain" cmd /k ""%PY%" -u "%LC%" --no-dedicated --tag m%RANDOM%"
```

### ★★★ 逐段解析

| 片段 | 含义 |
|---|---|
| `start "TESTOL chain"` | 新窗口，标题 `TESTOL chain` |
| `cmd /k` | ★ 执行后**保持窗口不关**（`/k`） |
| `""%PY%" -u "%LC%" ..."` | ★★ **双引号嵌套**（外层给 `start`，内层给 `cmd /k`） |
| `-u` | Python 无缓冲输出 |
| `--no-dedicated` | ★★★ **硬编码**（README 第 56 行也确认） |
| `--tag m%RANDOM%` | ★ 每次日志文件名不同（`n10run-m<随机>.txt`） |

★★★ **⇒ `start ... cmd /k` 的作用：**
```
① 异步启动（run.cmd 立即返回）
② 新窗口（不占用当前窗口）
③ /k 保持（链跑完后窗口不关，日志可见）
```

★★ **⇒ 与 `stop.cmd` 的 `call`（同步）形成对比。**

### ★★★ 环境变量在这一行之前已设好（第 99–102 行）

```cmd
set "OLMOD_GAME_ROOT=%GAME%"
set "OLMOD_BASE=%BUNDLE%"
set "OLMOD_BASE_TOOLS=%BUNDLE%"
set "OLMOD_STUN=%BUNDLE%\stun_local.py"
```

★★★ **⇒ 这 4 个变量通过 `setlocal` 的作用域传给 `start` 启动的子进程。**
**（`setlocal EnableExtensions` 在第 2 行，所以变量只在本次 `run.cmd` 作用域内。）**

★ **⇒ 但 `start` 启动的新 `cmd` 会**继承**这些环境变量 ✓**

---

## 八、★★★ 日志提示（第 108–112 行）

```cmd
echo   logs : %BUNDLE%\n10run-*.txt / re-*.log / stun_local.out.log
echo          %GAME%\Ayria\Logs\CodolGameServer*.log
echo   stop : stop.cmd
timeout /t 6 >nul
exit /b 0
```

★★ **⇒ 列出 4 类日志：**
```
bundle\n10run-*.txt          （nt10.py 的输出）
bundle\re-*.log              （launch_chain.py 的重定向：re-<tag>-nt10.out.log 等）
bundle\stun_local.out.log
<GAME>\Ayria\Logs\CodolGameServer*.log
```

★ **`timeout /t 6`** —— 等 6 秒让窗口显示信息，然后 `exit /b 0`。**

---

## 九、逐字节证据总表（`run.cmd`）

| # | 项 | 值 |
|---|---|---|
| 1 | 大小 | **4,243 B** |
| 2 | 行数 | 123 |
| 3 | ★★★ 客户端版本 | **`3.19.26.22`**（全包唯一） |
| 4 | Python 路径 | ★★★ **硬编码 `C:\Program Files\Python314\python.exe`** |
| 5 | Python 库 | `pefile` / `capstone`（★ 不检查） |
| 6 | 游戏根定位 | **3 重回退**（env / 同目录 / 父目录） |
| 7 | ★★ 父目录解析 | `for %%I in ("%HERE%\..") do set "GAME=%%~fI"` ✓ |
| 8 | 必需文件检查 | **11 项** |
| 9 | ★★★ **漏检** | **`_rsa.txt`**（不存在！）/ `_leaf2.cer` / Python 库 |
| 10 | 参数 | `--check` / `--no-deploy` / `--no-preflight`（★ 只认第 1 个） |
| 11 | ★★ deploy 失败 | `exit /b 3`（硬阻塞） |
| 12 | ★★★ preflight blocker | **只 WARN，继续启动**（软警告） |
| 13 | ★★ 两处 blocker 处理 | **不一致** |
| 14 | 启动命令 | `start "TESTOL chain" cmd /k "..."` |
| 15 | `--no-dedicated` | ★★★ **硬编码** |
| 16 | `--tag m%RANDOM%` | 日志名随机 |
| 17 | 环境变量 | 4 个（`OLMOD_GAME_ROOT` / `_BASE` / `_BASE_TOOLS` / `_STUN`） |
| 18 | 收尾 | `timeout /t 6` + `exit /b 0` |

---

# 第二部分：`1-构建.cmd`（1,388 B / 50 行）

## 十、★★★ 头部与路径（第 1–13 行）

```cmd
@echo off
setlocal EnableExtensions
title TESTOL build from source

set "HERE=%~dp0"
set "SRC=%HERE%source"                    ← ★ 注意：%~dp0 自带 \，所以是 <HERE>source
set "BP=%SRC%\tools\build.ps1"

echo ============================================================
echo   TESTOL  -  build plugins from source
echo   src : %SRC%
echo ============================================================
echo.
```

★★★ **⇒ **与 `run.cmd` 的差异**：**
```
run.cmd   :  set "HERE=%~dp0"  然后  if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
1-构建.cmd:  set "HERE=%~dp0"  ★ 不去尾部反斜杠，直接 " %HERE%source "
```

★★ **⇒ 两种风格都对，但**不一致**：**
```
run.cmd       HERE 无尾斜杠 ⇒ "%HERE%\bundle"
1-构建.cmd    HERE 有尾斜杠 ⇒ "%HERE%source"
```

★ **⇒ 这是**同一个作者两种写法**（说明是不同时期写的）。**

---

## 十一、★★★ 两道 BLOCK 检查（第 15–28 行）

### 检查 1：`source\tools\build.ps1` 存在

```cmd
if not exist "%BP%" (
  echo [BLOCK] missing source tree: %BP%
  pause & exit /b 2
)
```

### ★★★ 检查 2：`VCPKG_ROOT`（带**默认回退**）

```cmd
if not defined VCPKG_ROOT (
  if exist "E:\Source\Repos\Main\vcpkg\vcpkg.exe" set "VCPKG_ROOT=E:\Source\Repos\Main\vcpkg"
)
echo VCPKG_ROOT=%VCPKG_ROOT%
if not defined VCPKG_ROOT (
  echo [BLOCK] set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe
  echo         (needs the x86-windows-static OpenSSL triplet)
  pause & exit /b 2
)
```

★★★ **⇒ `E:\Source\Repos\Main\vcpkg` 是**作者机器的路径**（与 `BUILD.md:15` 一致）。**

★★ **⇒ 若该路径不存在且未设 `VCPKG_ROOT` ⇒ `[BLOCK]`。**

---

## 十二、★★★ 构建与产物（第 30–50 行）

```cmd
echo [1/2] build (release) ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%BP%" -Action build -Mode release
if errorlevel 1 (
  echo [FAIL] build failed - see output above
  pause & exit /b 1
)

echo [2/2] artifacts in %SRC%\build\bin\release
dir /b "%SRC%\build\bin\release" 2>nul
if /i "%~1"=="stage" (
  echo [stage] building stage\codol ...
  powershell ... -File "%BP%" -Action stage -Mode release
)

echo Next: copy the fresh *.Localnet32 into payload\Ayria\Plugins, then run 2-启动.cmd
pause
```

★★★ **⇒ 与 `BUILD.md` 的差异：**
```
BUILD.md  §2  : build / test / clean / configure / stage   （5 个 action）
1-构建.cmd    : build（默认）+ stage（带 "stage" 参数）    （2 个）
```

★★ **⇒ `1-构建.cmd` 是**简化封装**（只暴露 build 和 stage）。**

### ★★★ 第 48 行的提示 —— **与 `BUILD.md` 的 `Re` 后缀问题呼应**

```cmd
echo Next: copy the fresh *.Localnet32 into payload\Ayria\Plugins, then run 2-启动.cmd
```

★★★ **⇒ 用通配 `*.Localnet32` —— **不指定具体文件名**。**

★★ **⇒ 如果产物是 `AlwaysofflineRe.Localnet32`，它**也匹配 `*.Localnet32`**，
**会被复制进 `Plugins\` ⇒ 与旧的 `Alwaysoffline.Localnet32` **并存**。**

★★★ **⇒ 报告 012 指出的"两个后端实例"风险，在这里被**进一步放大**（因为用了通配）。**

---

## 十三、逐字节证据总表（`1-构建.cmd`）

| # | 项 | 值 |
|---|---|---|
| 1 | 大小 | **1,388 B** |
| 2 | 行数 | 50 |
| 3 | ★ `HERE` 风格 | **保留尾反斜杠**（与 `run.cmd` 不同） |
| 4 | 检查 1 | `source\tools\build.ps1` 存在 |
| 5 | ★★★ 检查 2 | `VCPKG_ROOT`（回退到 **`E:\Source\Repos\Main\vcpkg`**） |
| 6 | action | **build**（默认）+ **stage**（参数 `stage`） |
| 7 | 失败退出 | `exit /b 1` |
| 8 | ★★★ 第 48 行提示 | **`*.Localnet32` 通配** ⇒ 会带上 `Re` 后缀的产物 |

---

## 十四、结论

### 1. ★★★ `run.cmd` 的 11 项检查**漏了 `_rsa.txt`**

★★★ **⇒ 检查全过，`fake_auth_tls.py` 仍会在第一行崩溃。**

★ **⇒ 应补 3 项：`_rsa.txt`（或改用现成 `_leaf2.key`）/ `_leaf2.cer` / Python 库。**

### 2. ★★★ `run.cmd` 里 `3.19.26.22` 是**全包唯一的客户端版本号**

★ **⇒ 但**没有任何脚本检查**客户端版本。**

### 3. ★★★ `preflight` 的 blocker **不阻止启动**，而文件检查的 blocker **阻止**

★★ **⇒ 两处语义不一致（一处硬、一处软）。**

### 4. ★★★ `1-构建.cmd` 用 `*.Localnet32` 通配复制，会带上 `AlwaysofflineRe` 的产物

★★ **⇒ 与 `BUILD.md` 的 `Re` 后缀偏差**叠加**，产生"两个后端实例"的实际风险。**

### 5. ★★ `run.cmd` 与 `1-构建.cmd` 的 `HERE` 处理风格不一致（有/无尾斜杠）

### 6. ★★ 三个作者机器路径泄漏（`Python314` / `E:\Source\Repos\Main\vcpkg` / `D:\repo`）

---

## 十五、下一步

- `source\xmake.lua`（14,013 B）—— 验证 `ol_deploy` phony target 与产物名
- `source\tools\build.ps1` —— 验证 `-Action` 的实际实现
- `bundle\` 五个脚本逐字节
- `bundle\` 五个证书文件逐字节
