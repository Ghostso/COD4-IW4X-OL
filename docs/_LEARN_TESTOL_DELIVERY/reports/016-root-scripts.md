# 学习报告 016 — 包根目录：README / run.cmd / preflight.ps1 / deploy.ps1

**学习范围**：包根 4 个脚本 + README
**核心发现**：★★★ **`run.cmd` 已经处理了报告 015 的缺口 4**；但 `run.cmd` 的 12 项检查**漏掉了 3 个真缺口**

---

## 一、README 定死的边界（★★ 很多"合规"信息）

### 包的定位（行 3-4）

> **完整交付** —— 包含**上游源码树**（可自行构建）+ **现成运行件**（双击即跑）+ 构建/部署/校验全套文档。
> 不是"只有编译产物"的成品包；`TESTOL GO v2` 是本包去掉 `source\` 的轻量版。

### 三条用法（行 33-37）

| 你想做什么 | 做什么 |
|---|---|
| **直接跑**（不构建） | 双击 **`2-启动.cmd`**（首次自动 `preflight` + `deploy`） |
| **改代码后重建** | 双击 **`1-构建.cmd`** → 产物覆盖进 `payload\Ayria\Plugins\` → `2-启动.cmd` |
| **只要源码** | 直接取 `source\` |

### ★★★ 运行链的官方描述（行 46-56）

```
2-启动.cmd → run.cmd
  ├─ preflight.ps1   检查 hosts 五条 / dwauth.ini(3074) / stun.ini(3 个 stunN) /
  │                  cacert.pem(319,581 B) / IIPS\cacert 不存在
  ├─ deploy.ps1      payload\Ayria → <游戏根>\Ayria
  │                  （大小相同跳过，不同则 .bak-<时间戳> 备份后覆盖）
  └─ python bundle\launch_chain.py --no-dedicated
        ├─ ol_room_owner.exe（28970）
        ├─ fake_auth_tls.py（127.0.0.1:3074）
        ├─ stun_local.py（UDP 3074/3478/19302）
        └─ client ← Ayria\Injector32.exe，由 nt10.py 拉起（读内存出 secrets.txt）
  战斗服 ＝ <游戏根>\Ayria\Plugins\CodolGameServer.Localnet32（进程内）
  后端   ＝ <游戏根>\Ayria\Plugins\Alwaysoffline.Localnet32（进程内）
```

★★★ **README 明确写了 `client ← Ayria\Injector32.exe`** —— **与报告 009 的实测矛盾扩大**。

### ★★ 但也明确写了"进程内"（行 53-54）

> 战斗服 ＝ `<游戏根>\Ayria\Plugins\CodolGameServer.Localnet32`（**进程内**）
> 后端 ＝ `<游戏根>\Ayria\Plugins\Alwaysoffline.Localnet32`（**进程内**）

★★ **"进程内"意味着必须注入** —— 而 `--no-dedicated`（`role=client`）
按报告 015 引用的 `game_server.md:197` **"不运行 gameplay server"**。

★★★ **这是一个内部矛盾**：
```
README 说：战斗服在客户端进程内运行，用 --no-dedicated 启动
game_server.md 说：role=client 不运行 gameplay server
```
**两者不能同时成立。**

★ **但注意**：插件可以被加载（`combined`/`client` 都能被**加载**），
**只是 `client` role 下它不安装 gameplay hook**。
**所以"进程内"（加载）和"不运行战斗服"（不装 hook）都对。**

### 不含什么（行 60-68）★ 合规边界

| 不含 | 说明 |
|---|---|
| 客户端本体、`.ff/.ifs/.iwd/.d3dbsp` | `source\` 内 **0 个** |
| `ACE-DRV32.dll`（真身/桩） | 属客户端保护组件 |
| **独立专服（sh1x / `codol_dedrun`）** | **走客户端权威** |
| 玩家存档 `Assets\Alwaysoffline\1004\<UID>\*`、`Keystreams`、`Cloud\iotd-*`、`Launch_OLMod.bat` | **打包时已排除**（`payload\` 内 0 个） |
| 腾讯/游戏密钥 | 无 |

★★ **"玩家存档 `1004\<UID>\*` 打包时已排除"** ——
**这正好解释了报告 015 的发现**：`1004\` 下没有 `<UID>` 目录，
所以 `display_name()` 的候选 1、2 必然落空。

★★★ **⇒ `lstrip("0")` 不是根因，根因是"存档被有意排除"。**
`lstrip` 的 bug 是**第二层**（即使有存档也找不到）。

★★ **README 行 67 还给了一条线索**：
> `source\tests\backend\Fixtures\1004\1100001DEADC0DE\Inventory.json` 是**源码自带的测试夹具**

## ★ 注意这里是 **`1100001DEADC0DE`**（15 位！），
**证明 `lstrip("0")` 的产出确实是 `1100001DEADC0DE`** ——
**测试夹具用的就是 lstrip 后的值。所以 `lstrip` 是**故意的**，不是 bug。**

★★★ **报告 015 的"隐藏 bug"结论需要修正**：
`lstrip("0")` 是**刻意的**（与测试夹具一致），
**真正的问题是 `1004\1100001DEADC0DE\` 存档被排除，且包内没有这个目录。**

---

## 二、`run.cmd` —— 12 项必需文件检查（行 49-59）

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

### ★★★ 检查了 11 项，**漏了 3 项**

| 漏检的 | 后果 |
|---|---|
| `bundle\_rsa.txt` | `fake_auth_tls.py` **第一行崩溃** |
| `bundle\_leaf2.key` | 同样（`make_context` 的 keyfile） |
| `bundle\_leaf2_chain.pem` | 同上 |

★★ **`run.cmd` 检查了 `_ca.pem`，却没检查 `_leaf2_chain.pem`/`_leaf2.key`** ——
而 `fake_auth_tls.py` **真正用的是后两个**（`build_pem_files()` 用 `_rsa.txt` + `_leaf2.cer` + `_ca.pem` 生成）。

★★★ **这是检查清单与实际依赖不匹配** ——
**`_ca.pem` 是生成输入，`_leaf2_chain.pem`/`_leaf2.key` 是使用对象。**

---

## 三、`run.cmd` 的游戏根定位（行 25-39）★★ 报告 015 缺口 4 已解决

```cmd
if defined OLMOD_GAME_ROOT (
  set "GAME=%OLMOD_GAME_ROOT%"
  goto :game_ready
)
if exist "%HERE%\codoMP_client_shipRetail.exe" (
  set "GAME=%HERE%"                  ← ★ 包放在客户端根目录
  goto :game_ready
)
if exist "%HERE%\..\codoMP_client_shipRetail.exe" (
  for %%I in ("%HERE%\..") do set "GAME=%%~fI"    ← ★ 包在客户端根的子目录
  goto :game_ready
)
echo [BLOCK] cannot find codoMP_client_shipRetail.exe near "%HERE%".
exit /b 2
```

### ★★★ 关键：`run.cmd:99-102` **显式设置环境变量**

```cmd
set "OLMOD_GAME_ROOT=%GAME%"
set "OLMOD_BASE=%BUNDLE%"
set "OLMOD_BASE_TOOLS=%BUNDLE%"
set "OLMOD_STUN=%BUNDLE%\stun_local.py"
```

★★ **所以 `launch_chain.py:69` 的默认值 `D:\repo\03-live\client\TESTOL` 永远不会被用到**（双击路径）。

★ **报告 015 的缺口 4 在双击路径上被绕过。** 修正。

### ★ 但 `launch_chain.py` 单独跑仍会 `SystemExit`

```python
GAME = os.environ.get("OLMOD_GAME_ROOT") or r"D:\repo\03-live\client\TESTOL"
if not os.path.isdir(GAME):
    raise SystemExit("set OLMOD_GAME_ROOT to the client root (got %r)" % GAME)
```

★ **`python launch_chain.py --help` 在这个位置就崩了** —— 因为它 `raise SystemExit` 在 `argparse` 之前。
**这是个不友好的设计**（用户想看帮助反而看到错误）。

---

## 四、`run.cmd` 的最终启动（行 106）

```cmd
start "TESTOL chain" cmd /k ""%PY%" -u "%LC%" --no-dedicated --tag m%RANDOM%"
```

★ **`start ... cmd /k`** = 新开一个常驻窗口（`/k` 不退出）——
**这样日志可见，且进程不随 `run.cmd` 退出而终止。**

★★ **`--tag m%RANDOM%`** —— 每轮日志文件名不同（`n10run-m<随机>.txt`）。

★ **`--no-dedicated` 是硬编码的**（README 行 56 也确认："本包固定 `--no-dedicated`"）。

---

## 五、`preflight.ps1` —— 检查 5 项

### ① hosts 五条（行 18-24）★★ 精确对应

```powershell
'formal-zone-auth.codol.qq.com' = '127.0.0.1'    ← auth (TLS)
'formal-zone-lsg.codol.qq.com'  = '127.0.0.2'    ← ★ lsg (明文)
'stun1-tub.codol.qq.com'        = '127.0.0.1'
'stun2-tub.codol.qq.com'        = '127.0.0.1'
'stun3-tub.codol.qq.com'        = '127.0.0.1'
```

★★★ **`auth` → `127.0.0.1`，`lsg` → `127.0.0.2`** ——
**同端口 3074，不同回环 IP**（与报告 011 的拓扑假设完全一致）。

### 写入方式（行 43-44）★ 可逆

```powershell
$blockLines = @('# CODOL-LOCAL-BEGIN') + (缺失项) + @('# CODOL-LOCAL-END')
Add-Content -Path $hosts -Value $blockLines -Encoding ASCII
```

★★ **块标记 `# CODOL-LOCAL-BEGIN` / `# CODOL-LOCAL-END`** ——
**可以整块删除，不污染 hosts 其他内容。这是好的实践。**

★ **注意报告 013 提到的 `# CODOL-STUN-LOCAL-BEGIN`**（`launch_chain.py:83` 注释）
—— **与这里的 `# CODOL-LOCAL-BEGIN` 名字不同**！

★★ **两个不同的块标记** ⇒ hosts 里可能有**两个块**，且删除时容易只删一个。

### ② `dwauth.ini`（行 53-63）

**检查**：内容含 `formal-zone-lsg.codol.qq.com` **且** 含 `3074`。

**`-Apply` 生成**（行 60）：
```
formal-zone-lsg.codol.qq.com 3074
formal-zone-auth.codol.qq.com 3074
0x03EA
```

★★ **`0x03EA` = 1002（十进制）** —— titleId 相关？
而 `Platform.json` 里 `titleId = 1004`。

★★ **`0x03EA = 1002 ≠ 1004` —— 值得注意。**
可能是"zoneId 的另一种表示"或**旧值**。

### ③ `stun.ini`（行 64-74）

**检查**：含 **≥3 个** `stun\d-tub.codol.qq.com`。

**`-Apply` 生成**：三行域名（无端口）。

★ **注意 `Warn` 而不是 `Bad`** —— stun.ini 缺失只警告不阻塞。

### ④ `cacert.pem`（行 78-82）★★ 精确大小

```powershell
if ($sz -gt 100000) { Ok } else { Warn ("cacert.pem 只有 " + $sz + " B（真身约 319 KB）") }
```

★ **阈值 100 KB，真身约 319,581 B**（README 行 48 也写了这个数）。

★★ **这是 Mojang/curl 的 cacert.pem**（约 319 KB 的根证书包）。
**客户端用它验证 TLS，必须替换成本地 CA 或者保留（因为我们的 CA 也要在里面）。**

### ⑤ ★★ `IIPS\cacert.pem` 必须**不存在**（行 83-84）

```powershell
if (Test-Path $iips) { Warn "IIPS\cacert.pem 存在（基线里没有这个文件，可能干扰）" }
else { Ok "IIPS\cacert.pem 不存在（符合基线）" }
```

★★ **注意：存在时是 `Warn` 不是 `Bad`** —— 但注释说"**可能干扰**"。

★★★ **`IIPS` 是腾讯的启动基础设施**（记忆：`iips.ini` 指向不可达的 `10.231.2.181`）。
**它的 `cacert.pem` 会让客户端走腾讯的证书链，与本地 CA 冲突。**

★ **这是"基线里没有这个文件"的判据** —— 说明**干净客户端的 IIPS 目录不该有 cacert**。

---

## 六、`deploy.ps1` —— 按大小比对部署（行 20-51）

```powershell
Get-ChildItem $PAY -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($PAY.Length + 1)
    $target = Join-Path $dstRoot $rel
    if (Test-Path $target) {
        $cur = Get-Item $target
        if ($cur.Length -eq $_.Length) { $need = $false; $skipped++ }   # ★ 只比大小
        else { 备份 .bak-<stamp> 后覆盖 }
    }
    if ($need) { Copy-Item ... }
}
```

### ★★ "只比大小"是个弱点

**大小相同但内容不同 ⇒ 跳过部署 ⇒ 用旧文件。**

★ **实际风险**：源码改一个字节的补丁（同大小），部署不会更新。
★★ **但换个角度看**：这是**为了"客户端正在运行时也能安全重跑"**的取舍
（重量级 hash 比对更慢，且大小相同基本可判定未变）。

### ★ `.bak-<时间戳>` 备份（行 31）

```powershell
Copy-Item $target ($target + '.bak-' + $stamp) -Force
```

★ **每次部署都生成新备份** ⇒ **多次部署后 .bak 文件堆积**。

### 退出码（行 54-55）

```powershell
if ($failed -gt 0) { exit 3 }
exit 0
```

★ `run.cmd:84` 检查 `if errorlevel 3` 并提示"客户端还在运行吗"。

---

## 七、`2-启动.cmd` / `3-停止.cmd`（35 B / 36 B）

```cmd
2-启动.cmd   → call run.cmd
3-停止.cmd   → call stop.cmd
```

★ **极简转发器**（我上次修过 CRLF）。

---

## 八、★★★ 交付包缺口的最终定账（修订报告 015）

### 双击 `2-启动.cmd` 的**真实**失败链

```
run.cmd 找 GAME
    ├─ OLMOD_GAME_ROOT 未设
    ├─ 包里没有 codoMP_client_shipRetail.exe
    └─ 父目录也没有
        ⇒ [BLOCK] cannot find codoMP_client_shipRetail.exe
        ⇒ exit /b 2   ← ★★★ 双击的第一步就停在这里
```

★★★ **交付包本身就是 `F:\桌面\ol\TESTOL 完整交付版`，
里面没有客户端 exe ⇒ 双击 `2-启动.cmd` 立刻失败，连检查清单都不会执行。**

★ **README 行 38 明说了**："Put this folder in the client root, or set OLMOD_GAME_ROOT first." ——
**但我上次读 README 时没注意这条**（它藏在 run.cmd 里）。

### 假设 `OLMOD_GAME_ROOT` 设对了

```
run.cmd 的 11 项检查
    ├─ client exe            ✓（用户提供）
    ├─ Python314             ✗ ← 本机不存在 ⇒ [BLOCK]
    ├─ launch_chain.py       ✓
    ├─ nt10.py               ✓
    ├─ fake_auth_tls.py      ✓
    ├─ stun_local.py         ✓
    ├─ _ca.pem               ✓
    ├─ Injector32.exe        ✓
    ├─ ol_room_owner.exe     ✓
    ├─ CodolGameServer...    ✓
    └─ Alwaysoffline...      ✓
        ⇒ 唯一 BLOCK = Python314
```

### 修好 Python 路径后

```
launch_chain.py main()
    └─ 步骤 0: fake_auth_tls.py
        └─ build_pem_files()
            └─ open("_rsa.txt")   ← ★★★ FileNotFoundError，进程崩溃
                ⇒ wait_port(3074, 20s) 失败 ⇒ return 3
```

★ **`--no-dedicated` 路径不会执行到 `start_dedicated.ps1`** ⇒ **缺口 3 不影响双击路径**。

### ★★ 修好 `_rsa.txt` 之后

```
步骤 0  ✓ fake auth 起
步骤 0b ✓ stun_local 起
步骤 1  ✓ room owner 起
步骤 2  nt10.py 拉客户端
        └─ 无 inject_ayria.on ⇒ 直起 exe ⇒ 插件不加载
            ⇒ 但 wait_port(28962) 等的是 client bridge
                ★ 28962 是 nt10.py 自己开的（bridge），不依赖插件
            ⇒ 可能通过
步骤 2b force_display_name --apply Easily_
        ★ 但 --needle 默认 AdministraClient，本机账户 Z7-CT5N1 扫不到
        ⇒ 静默无操作
步骤 3  跳过（--no-dedicated）
        ⇒ status() ⇒ return 0  ★ "成功"
```

★★★ **所以最终的"成功"是**假成功**：
- 脚本 return 0
- 但**插件没加载** ⇒ 无大厅、无战斗服
- **名字没改**
- 客户端会卡在"连接中"

---

## 九、这一块的结论

### 修订报告 015 的三处判断

| # | 报告 015 的判断 | 修订 |
|---|---|---|
| 缺口 4（`OLMOD_GAME_ROOT`） | 会 `SystemExit` | ★ **双击路径已解决**（`run.cmd:99` 显式设置）；**单独跑仍会崩** |
| 缺口 3（`start_dedicated.ps1`） | 步骤 3 必然失败 | ★ **双击用 `--no-dedicated`，不会执行到** |
| `lstrip("0")` 是隐藏 bug | ★ **不是 bug**，是刻意的（测试夹具 `1100001DEADC0DE` 用的就是这个值） |

### 新的关键发现

1. ★★★ **交付包双击的第一步就失败** —— 包内没有客户端 exe，
   且 `run.cmd` 要求"包放在客户端根目录"或设 `OLMOD_GAME_ROOT`。
2. ★★ **`run.cmd` 检查 11 项，漏了 `_rsa.txt` / `_leaf2.key` / `_leaf2_chain.pem`** ——
   而这三项是 `fake_auth_tls.py` 的**真实**依赖。
3. ★★ **README 说"进程内战斗服"，`game_server.md` 说"`client` role 不装 gameplay hook"** ——
   两者都对（加载≠运行），但**合起来 = `--no-dedicated` 下没有战斗服**。
4. ★ **hosts 有两个不同的块标记**（`# CODOL-LOCAL-BEGIN` / `# CODOL-STUN-LOCAL-BEGIN`）。
5. ★ **`dwauth.ini` 的 `0x03EA` = 1002 ≠ `Platform.json` 的 `titleId` 1004**。
6. ★ **`IIPS\cacert.pem` 存在时只 Warn 不 Bad** —— 但注释说"可能干扰"。
7. ★★ **README 明确写了"玩家存档 `1004\<UID>\*` 打包时已排除"** ——
   **这就是名字落到 `Alwaysoffline` 的真正原因。**

---

## 十、待验证

- [ ] ★★★ **`--no-dedicated` + `role=client` 下，插件到底装不装 gameplay hook？**
      （README 与 `game_server.md` 的矛盾核心）
- [ ] ★★ **`0x03EA` (1002) vs `titleId` 1004 的关系**
- [ ] **两个 hosts 块标记是否都该有**（还是只有一个）
- [ ] `cacert.pem` 319 KB 是否就是 curl 的 cacert.pem（需要查）
- [ ] `deploy.ps1` "只比大小"是否导致过实际事故
- [ ] `1-构建.cmd` / `BUILD.md` 的内容（构建链）
