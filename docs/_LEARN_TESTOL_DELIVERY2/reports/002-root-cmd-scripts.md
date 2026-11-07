# 学习报告 002（重开）— 包根 `.cmd` 三件逐字节

**学习范围**：`2-启动.cmd`(35 B) / `3-停止.cmd`(36 B) / `stop.cmd`(860 B)
**方法**：全文读入 + 字节数反推换行
**性质**：全实测

---

## 一、★★ `2-启动.cmd`（35 字节，逐字节精确）

```cmd
@echo off
call "%~dp0run.cmd" %*
```

### ★★★ 字节数反推（验证换行风格）

```
"@echo off"                 =  9 字符
CRLF                        =  2 字节
"call \"%~dp0run.cmd\" %*"  = 22 字符
CRLF                        =  2 字节
                          ─────────
                            35 字节  ✓ 与清单一致
```

★★★ **⇒ **确证是 CRLF**（若为 LF 则只有 33 字节）。**

### ★★ 逐字符拆解第二行

```
c a l l  ␣  "  %  ~  d p 0 r u n . c m d  "  ␣  %  *
1 2 3 4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22
```

| 片段 | 含义 |
|---|---|
| `call` | ★ **不是 `start`** —— 同步调用，等待 `run.cmd` 返回 |
| `"%~dp0"` | ★★ **脚本所在目录（带尾部反斜杠）** |
| `run.cmd` | 实际执行体 |
| `%*` | ★★ **透传所有参数** |

★★ **`%~dp0` = `%~d0`（盘符）+ `%~p0`（路径），**自带尾部 `\`** ——
所以 `"%~dp0run.cmd"` 拼出来是正确的绝对路径。**

★★★ **⇒ 这两个文件让包**可以放在任意目录**（不依赖 CWD）。**

---

## 二、★ `3-停止.cmd`（36 字节）

```cmd
@echo off
call "%~dp0stop.cmd" %*
```

```
"@echo off"                  =  9
CRLF                         =  2
"call \"%~dp0stop.cmd\" %*"  = 23   ← 比 run 版多 1（"stop" 4 字 vs "run" 3 字）
CRLF                         =  2
                           ─────────
                             36  ✓
```

★ **两个都是**两行纯转发器**，无其他逻辑。**

---

## 三、★★★ `stop.cmd`（860 字节）逐行

```cmd
:1   @echo off
:2   title TESTOL GO v2 stop
:3   echo Stopping client / injector / room owner / aux ...
:4   （空行）
:5   taskkill /F /IM codoMP_client_shipRetail.exe /T >nul 2>&1
:6   taskkill /F /IM nt10.exe /T >nul 2>&1
:7   taskkill /F /IM ol_room_owner.exe /T >nul 2>&1
:8   （空行）
:9   powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'nt10|fake_auth|stun_local|launch_chain' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
:10  （空行）
:11  echo.
:12  echo Leftovers:
:13  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process codoMP_client_shipRetail,ol_room_owner -ErrorAction SilentlyContinue | Select-Object Id,ProcessName | Format-Table -AutoSize"
:14  （空行）
:15  echo.
:16  echo Done. If the client is still listed, quit the game in-game first so progress is saved.
:17  pause
```

---

## 四、★★★ `stop.cmd` 的三处问题（逐字节发现）

### 问题 1：★★★ 杀 `nt10.exe`（第 6 行）—— **这个进程名不存在**

```cmd
taskkill /F /IM nt10.exe /T >nul 2>&1
```

★★★ **但 `nt10.py` 是 **Python 脚本**，由 `python.exe` 运行，
**进程名是 `python.exe`，不是 `nt10.exe`。****

★ **证据**：`launch_chain.py:352-357`：
```python
subprocess.Popen(
    [PY, "-u", "nt10.py", "--root", GAME, ...],   # PY = python.exe
```

★★★ **⇒ 第 6 行是**死代码**（永远找不到进程）。
**它可能来自 `nt10` 曾经被 `pyinstaller` 打包成 `.exe` 的旧设计。**

★★ **好在第 9 行的 PowerShell 用**命令行正则**兜住了**：
```powershell
Where-Object { $_.CommandLine -match 'nt10|fake_auth|stun_local|launch_chain' }
```
**这个能正确杀掉 `python.exe -u nt10.py`。**

### 问题 2：★★★ 第 3 行声称杀 "injector"，**实际没有**

```cmd
echo Stopping client / injector / room owner / aux ...
```

★★ **但下面三条 `taskkill` 只针对**：
```
codoMP_client_shipRetail.exe
nt10.exe            （无效）
ol_room_owner.exe
```

★★★ **⇒ **没有任何一条杀 `Injector32.exe`。****

★ **可能的辩解**：`taskkill /T`（树杀）会带走注入器 ——
**但注入器是**父进程**，客户端才是它的子进程；`/T` 是**从指定进程向下杀**，
杀客户端不会带走注入器。**

★★★ **⇒ 如果 `Injector32.exe` 还活着（注入了但没退出），`stop.cmd` **不会清掉它**。**

### 问题 3：★★★ 与 `launch_chain.py` 的 `stop_all()` **正则不一致**

| 来源 | 正则 |
|---|---|
| `stop.cmd:9` | `'nt10\|fake_auth\|stun_local\|launch_chain'` ★ **含 launch_chain** |
| `launch_chain.py:190-197`（报告 010） | `'nt10\|fake_auth\|stun_local'` ★ **不含** |

★★★ **⇒ `stop.cmd` 会杀掉 `launch_chain.py` 自己，`stop_all()` 不会。**

★ **这是**正确的**差异**：
- `stop.cmd` 是**外部**停止按钮 ⇒ 应该杀 `launch_chain`
- `stop_all()` 是 `launch_chain` **内部**调用 ⇒ 不能自杀

★★ **⇒ 无 bug，是设计。**（但值得记录）

---

## 五、★★ `stop.cmd` 的收尾（第 11–17 行）

```cmd
echo.
echo Leftovers:
powershell ... Get-Process codoMP_client_shipRetail,ol_room_owner ...
echo.
echo Done. If the client is still listed, quit the game in-game first so progress is saved.
pause
```

★★★ **⇒ 两个好设计**：

1. **残留检查**（`Get-Process` 列出来）—— 不只杀，还**报告结果**
2. **提示语**（`quit the game in-game first so progress is saved`）——
   ★★ **警告强制杀会丢存档** —— 责任转移给用户

★ **`pause`** → 双击时窗口不闪退。

---

## 六、★★★ 三个 `.cmd` 与 `run.cmd` 的调用关系

```
2-启动.cmd  ──call──>  run.cmd   ──start──> launch_chain.py
3-停止.cmd  ──call──>  stop.cmd
```

★★★ **⇒ 启动用 `start`（异步，不阻塞），停止用 `call`（同步，等完成）。**

★ **这与语义匹配**：
- 启动要**立刻返回**让用户看到提示（`run.cmd:106` 用 `start ... cmd /k`）
- 停止要**等杀完**再报告残留

---

## 七、逐字节证据总表

| # | 文件 | 字节 | 行数 | 行尾 | 关键 |
|---|---|---|---|---|---|
| 1 | `2-启动.cmd` | **35** | 2 | CRLF | `call "%~dp0run.cmd" %*` |
| 2 | `3-停止.cmd` | **36** | 2 | CRLF | `call "%~dp0stop.cmd" %*` |
| 3 | `stop.cmd` | 860 | 17 | CRLF | 3 条 taskkill + 1 条 PS 正则 |
| 4 | `taskkill nt10.exe` | — | 行 6 | — | ★★★ **无效进程名** |
| 5 | 声称杀 injector | — | 行 3 | — | ★★★ **实际没杀** |
| 6 | PS 正则 | — | 行 9 | — | `nt10\|fake_auth\|stun_local\|launch_chain` |
| 7 | `stop_all()` 正则 | — | — | — | `nt10\|fake_auth\|stun_local`（少一项） |

---

## 八、结论

### 1. ★★ 两个转发器是**字节精确**的 35/36 字节（CRLF 已确证）

### 2. ★★★ `stop.cmd` 有两处**实际缺陷**

```
① `nt10.exe` 进程名不存在 ⇒ 那条 taskkill 是死代码
② 声称杀 injector 但没杀 ⇒ Injector32.exe 可能残留
```

★ **两处都由第 9 行的 PowerShell 正则部分兜住**（①②它都能覆盖，因为
`Injector32.exe` 不在正则里 —— ★ **所以 ② 真的没兜住**）。

★★★ **⇒ 修正版结论：**
```
① nt10.exe       → PowerShell 正则兜住 ✓
② Injector32.exe → ★ 无任何机制覆盖 ✗
```

### 3. ★★ 与 `launch_chain.py:stop_all()` 的正则差异是**有意设计**

### 4. ★★ 残留检查 + 存档警告是**好设计**

---

## 九、下一步

按清单顺序，接下来是包根的两个 PowerShell 脚本（`preflight.ps1` 4062 B / `deploy.ps1` 2032 B）
与 `run.cmd`（4243 B）逐字节 —— 这三者是**交付包的运行主干**。
