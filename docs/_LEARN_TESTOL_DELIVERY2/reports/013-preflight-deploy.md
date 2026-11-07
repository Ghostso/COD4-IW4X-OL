# 学习报告 013（重开）— `preflight.ps1` + `deploy.ps1` 逐字节

**学习范围**：`preflight.ps1`（4,062 B / 89 行）+ `deploy.ps1`（2,032 B / 55 行）
**性质**：全实测
**★★★ 本报告发现 `preflight.ps1` 有一处**误报逻辑**、`deploy.ps1` 有一处**静默跳过**

---

# 第一部分：`preflight.ps1`（4,062 B / 89 行）

## 一、★★★ 头部与参数（第 1–15 行）

```powershell
# TESTOL GO v2 preflight: hosts / dwauth.ini / stun.ini / cacert.pem
# Default: check only. -Apply writes what it can (hosts needs admin).
# Exit 0 = ready, 2 = missing pieces (see [BLOCK]).
param(
  [string]$Game = "",
  [switch]$Apply
)
$ErrorActionPreference = 'Continue'
$block = 0
function Ok($m)   { Write-Host ("  [OK]    " + $m) -ForegroundColor Green }
function Warn($m) { Write-Host ("  [WARN]  " + $m) -ForegroundColor Yellow }
function Bad($m)  { Write-Host ("  [BLOCK] " + $m) -ForegroundColor Red; $script:block++ }

if (-not $Game) { Write-Host "[BLOCK] -Game not given"; exit 2 }
$hosts = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
```

### ★★★ 设计要点

| 项 | 值 | 评价 |
|---|---|---|
| 两个参数 | `$Game` / `$Apply` | 简洁 |
| `$ErrorActionPreference = 'Continue'` | 遇错继续 | ★ 检查脚本该如此 |
| 三个输出级别 | `Ok` / `Warn` / `Bad` | ★★ **只有 `Bad` 计入 blocker** |
| 退出码 | **0 = 就绪 / 2 = 有 blocker** | 与 `run.cmd` 的 `if errorlevel 2` 对接 |
| **全 ASCII** | ★ `deploy.ps1:2` 明说 "ASCII only on purpose (cmd/PS5.1 encoding)" | ★★★ 但**实际有中文**（见 §六） |

★★★ **⇒ 这是**纯检查脚本**：`-Apply` 才写，默认只读。**

---

## 二、★★★★ hosts 检查（第 17–47 行）

### 2.1 期望的五条（第 18–24 行，逐字节）

```powershell
$want = @{
  'formal-zone-auth.codol.qq.com' = '127.0.0.1'     ← ★★★ auth → 127.0.0.1
  'formal-zone-lsg.codol.qq.com'  = '127.0.0.2'     ← ★★★ lsg  → 127.0.0.2
  'stun1-tub.codol.qq.com'        = '127.0.0.1'
  'stun2-tub.codol.qq.com'        = '127.0.0.1'
  'stun3-tub.codol.qq.com'        = '127.0.0.1'
}
```

★★★ **⇒ 核心拓扑：**auth 与 lsg **同端口 3074，不同回环 IP**。**

```
127.0.0.1:3074  →  formal-zone-auth.codol.qq.com   （TLS 认证）
127.0.0.2:3074  →  formal-zone-lsg.codol.qq.com    （明文大厅）
127.0.0.1:3074  →  stun1/2/3-tub.codol.qq.com      （UDP STUN，同 IP 不同协议）
```

★ **注意：`stun1/2/3` 全指 `127.0.0.1`，与 auth 同 IP。**
**⇒ auth 用 TCP，stun 用 UDP ⇒ **不冲突**（`fake_auth_tls.py` 是 TCP，`stun_local.py` 是 UDP）。**

### 2.2 ★★★ 三态判定逻辑（第 28–36 行）

```powershell
foreach ($k in $want.Keys) {
  # ① 精确匹配期望行
  $line = $hs | Where-Object { $_ -match ('^\s*' + [regex]::Escape($want[$k]) + '\s+' + [regex]::Escape($k) + '\s*$') }
  if ($line) { Ok ("$k -> " + $want[$k]) }
  else {
    # ② 存在该域名但指向别处
    $any = $hs | Where-Object { $_ -match ('^\s*\S+\s+' + [regex]::Escape($k) + '\s*$') }
    if ($any) { Warn ("$k 指向 " + ($any -join ';') + "（期望 " + $want[$k] + "）") }
    # ③ 完全没有
    else { Bad ("hosts 缺 $k -> " + $want[$k]); $missingHosts += $k }
  }
}
```

★★★ **⇒ 三态设计精确：**
```
OK    精确匹配（IP 正确）
WARN  域名在但 IP 错（★ 不算 blocker！）
BLOCK 域名完全没有（★ 计入 blocker）
```

★★ **⇒ **`WARN` 不计入 blocker** —— 这是一个**重要的宽松选择**：**
**hosts 指向错误 IP 时，`preflight` 仍然返回 0（就绪）。**

★ **⇒ 但如果 IP 错了（如指向真实的 `codol.qq.com` 服务器），客户端会连到真服务器而失败。**

★★★ **⇒ 这是**一个可能掩盖问题的设计**。**

### 2.3 ★★★ hosts 写入（第 37–47 行）

```powershell
if ($missingHosts.Count -gt 0 -and $Apply) {
  $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    Warn "写 hosts 需要管理员。请以管理员运行，或手工加以下行："
    foreach ($k in $missingHosts) { Write-Host ("        " + $want[$k] + " " + $k) }
  } else {
    $blockLines = @('# CODOL-LOCAL-BEGIN') + ($missingHosts | ForEach-Object { $want[$_] + ' ' + $_ }) + @('# CODOL-LOCAL-END')
    Add-Content -Path $hosts -Value $blockLines -Encoding ASCII
    Ok ("已写入 hosts: " + ($missingHosts -join ', '))
  }
}
```

★★★ **⇒ 三个好设计：**
```
① 管理员检测（不硬要求）
② 非管理员时**打印要手工加的行**（可复制）
③ ★★★ 用 **块标记** `# CODOL-LOCAL-BEGIN` / `# CODOL-LOCAL-END` 包裹
```

★★★ **⇒ 块标记是**可逆设计** —— 删除整块即可完全撤销。**

★ **但注意：`launch_chain.py:83` 的注释提到的是 `# CODOL-STUN-LOCAL-BEGIN`，**
**与此处的 `# CODOL-LOCAL-BEGIN` **不同名**（上一轮报告 013 已记录）。**

★★ **⇒ 两个不同的块名 ⇒ hosts 里可能有**两个块**，删除时容易只删一个。**

---

## 三、★★★ `dwauth.ini` 检查（第 49–63 行）

```powershell
$dwauth = Join-Path $Game 'dwauth.ini'
$stun   = Join-Path $Game 'stun.ini'
if (Test-Path $dwauth) {
  $d = Get-Content $dwauth -ErrorAction SilentlyContinue
  if (($d -join "`n") -match 'formal-zone-lsg\.codol\.qq\.com' -and ($d -join "`n") -match '3074') { Ok "dwauth.ini 含 lsg/auth + 3074" }
  else { Bad "dwauth.ini 内容不含 formal-zone-lsg/3074（当前: $($d -join ' | ')）" }
} else {
  Bad "缺 dwauth.ini"
  if ($Apply) {
    Set-Content $dwauth "formal-zone-lsg.codol.qq.com 3074`r`nformal-zone-auth.codol.qq.com 3074`r`n0x03EA" -Encoding ASCII
    Ok "已生成 dwauth.ini"
  }
}
```

### ★★★ `-Apply` 生成的 `dwauth.ini`（逐字节）

```
formal-zone-lsg.codol.qq.com 3074\r\n
formal-zone-auth.codol.qq.com 3074\r\n
0x03EA
```

★★ **⇒ 三行，**CRLF 换行，无 BOM，ASCII 编码**。**

★★★ **⇒ `0x03EA` = 1002 —— 而 `Platform.json` 的 `titleId` 是 1004。**
**上一轮报告 017 已确认**两者无关**（不同字段）。**

### ★★★ 检查逻辑的**宽松性**

```powershell
if (($d -join "`n") -match 'formal-zone-lsg\.codol\.qq\.com' -and ($d -join "`n") -match '3074')
```

★★★ **⇒ 只检查**两个子串**：`formal-zone-lsg.codol.qq.com` 和 `3074`。**

★ **⇒ 不检查：**
```
① formal-zone-auth 是否存在
② 端口是否正确（只要出现 "3074" 就算过，哪怕在别的行）
③ 0x03EA 是否存在
④ 顺序
```

★★★ **⇒ 这是一个**非常宽松**的检查 —— 几乎任何包含这两个子串的文件都能过。**

---

## 四、★★★ `stun.ini` 检查（第 64–74 行）

```powershell
if (Test-Path $stun) {
  $s = Get-Content $stun -ErrorAction SilentlyContinue
  $n = ($s | Where-Object { $_ -match 'stun\d-tub\.codol\.qq\.com' }).Count
  if ($n -ge 3) { Ok "stun.ini 含 $n 个 stunN-tub 名" } else { Warn "stun.ini 只含 $n 个 stunN-tub 名" }
} else {
  Warn "缺 stun.ini（客户端 getPublicAddr 可能 Address Fail）"
  if ($Apply) {
    Set-Content $stun "stun1-tub.codol.qq.com`r`nstun2-tub.codol.qq.com`r`nstun3-tub.codol.qq.com" -Encoding ASCII
    Ok "已生成 stun.ini"
  }
}
```

★★★ **⇒ `stun.ini` 缺失只 `Warn`，**不阻塞**（与 `dwauth.ini` 的 `Bad` 不同）。**

★ **⇒ 理由在括号里写明：`（客户端 getPublicAddr 可能 Address Fail）`** ——
**是"可能"，不是"必然"。**

★★ **⇒ 但上一轮 `stun_local.py` 的分析证明：缺 STUN 会导致 `t≈54s 致命错误`。**
**⇒ 这个 `Warn` 级别**可能过低**。**

---

## 五、★★★ 证书检查（第 76–84 行）

```powershell
$ca = Join-Path $Game 'cacert.pem'
if (Test-Path $ca) {
  $sz = (Get-Item $ca).Length
  if ($sz -gt 100000) { Ok ("cacert.pem " + $sz + " B") } else { Warn ("cacert.pem 只有 " + $sz + " B（真身约 319 KB）") }
} else { Bad "缺 cacert.pem" }
$iips = Join-Path $Game 'IIPS\cacert.pem'
if (Test-Path $iips) { Warn "IIPS\cacert.pem 存在（基线里没有这个文件，可能干扰）" } else { Ok "IIPS\cacert.pem 不存在（符合基线）" }
```

### ★★★ 两个判断

| 检查 | 阈值 | 级别 |
|---|---|---|
| `cacert.pem` 存在且 **> 100,000 B** | 100 KB | 缺失 = `Bad`，过小 = `Warn` |
| **`IIPS\cacert.pem` 必须不存在** | — | 存在 = `Warn` |

★★★ **⇒ `cacert.pem` 的"真身约 319 KB"与 `README:48` 的"319,581 B"一致。**

★★ **⇒ `IIPS\cacert.pem` 存在时只 `Warn`，但注释说"可能干扰"。**

★ **⇒ `IIPS` 是腾讯启动基础设施（记忆里 `iips.ini` 指向不可达的 `10.231.2.181`）。**
**它的 `cacert.pem` 会让客户端走腾讯证书链，与本地 CA 冲突。**

★★★ **⇒ 这个检查**只 Warn 不 Bad**，但后果可能严重。**

---

## 六、★★★★ `preflight.ps1` 的两处**实际缺陷**

### 缺陷 1：★★★ 注释说 "ASCII only"，**实际有中文**

★ **`deploy.ps1:2` 明写**：
```powershell
# ASCII only on purpose (cmd/PS5.1 encoding).
```

★★★ **但 `preflight.ps1` 里有 **8 处中文**：**
```
第 40 行  "写 hosts 需要管理员。请以管理员运行，或手工加以下行："
第 45 行  "已写入 hosts: "
第 56 行  "dwauth.ini 内容不含 formal-zone-lsg/3074（当前: "
第 58 行  "缺 dwauth.ini"
第 61 行  "已生成 dwauth.ini"
第 69 行  "缺 stun.ini（客户端 getPublicAddr 可能 Address Fail）"
第 72 行  "已生成 stun.ini"
第 81 行  "cacert.pem 只有 " + ... + " B（真身约 319 KB）"
第 84 行  "IIPS\cacert.pem 存在（基线里没有这个文件，可能干扰）"
```

★★★ **⇒ `preflight.ps1` **不是** ASCII —— 它有 UTF-8 中文。**

★★★ **⇒ 这正是上一轮"加 UTF-8 BOM"的原因：**
**无 BOM 的 UTF-8 中文在 PS 5.1 下按 ANSI 解析 ⇒ 引号/括号错乱 ⇒ ParserError。**

★ **⇒ 而 `deploy.ps1` **确实**是纯 ASCII（无中文）⇒ 无需 BOM。**

★★★ **⇒ 两份脚本的编码策略**不一致**，但都"能跑"（一份靠 BOM，一份靠无中文）。**

### 缺陷 2：★★ `-Apply` 写 `dwauth.ini` 用 `Set-Content -Encoding ASCII`

```powershell
Set-Content $dwauth "formal-zone-lsg.codol.qq.com 3074`r`n..." -Encoding ASCII
```

★★ **⇒ 内容是纯 ASCII（域名 + 数字 + `0x03EA`），所以 ASCII 编码**没问题**。** ✓

★ **⇒ 但 `Set-Content` 在 PS 5.1 下**会加 BOM？**
**→ `-Encoding ASCII` 不加 BOM。** ✓

---

## 七、★★★ 逐字节证据总表（`preflight.ps1`）

| # | 项 | 值 |
|---|---|---|
| 1 | 大小 | **4,062 B**（含 BOM 3 字节） |
| 2 | 行数 | 89 |
| 3 | 参数 | `$Game` / `$Apply` |
| 4 | 退出码 | 0 就绪 / 2 有 blocker |
| 5 | hosts 期望 | **5 条**（auth 127.0.0.1 / lsg 127.0.0.2 / stun1-3 127.0.0.1） |
| 6 | ★★ hosts 三态 | OK / **WARN（IP 错，不计 blocker）** / BLOCK |
| 7 | ★★ hosts 块标记 | `# CODOL-LOCAL-BEGIN` / `# CODOL-LOCAL-END` |
| 8 | ★ `dwauth.ini` 生成 | 3 行 CRLF，含 `0x03EA` |
| 9 | ★★ `dwauth.ini` 检查宽松 | 只查 2 个子串 |
| 10 | ★★ `stun.ini` 缺失只 Warn | 不阻塞 |
| 11 | `cacert.pem` 阈值 | **> 100,000 B** |
| 12 | ★★ `IIPS\cacert.pem` 存在只 Warn | 注释说"可能干扰" |
| 13 | ★★★ **中文 9 处** | 与 "ASCII only" 声明矛盾 |

---

# 第二部分：`deploy.ps1`（2,032 B / 55 行）

## 八、★★★ 头部（第 1–18 行）

```powershell
# Deploy payload\Ayria -> <GAME>\Ayria  (size compare + .bak-<stamp> backups)
# ASCII only on purpose (cmd/PS5.1 encoding).
param(
  [string]$Game = "",
  [switch]$DryRun
)
$ErrorActionPreference = 'Continue'

$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
$PAY = Join-Path $HERE 'payload\Ayria'
$stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')

if (-not $Game) { Write-Host '[BLOCK] -Game not given'; exit 2 }
if (-not (Test-Path $PAY)) { Write-Host ("[BLOCK] payload missing: " + $PAY); exit 2 }
if (-not (Test-Path $Game)) { Write-Host ("[BLOCK] game root missing: " + $Game); exit 2 }

$dstRoot = Join-Path $Game 'Ayria'
$copied = 0; $skipped = 0; $backed = 0; $failed = 0
```

★★★ **⇒ 与 `preflight.ps1` 的关键差异：**
```
$HERE  = 脚本所在目录（★ 不依赖 CWD）
$PAY   = <HERE>\payload\Ayria      （★ 固定，不可配）
$dst   = <Game>\Ayria
```

★ **⇒ `payload` 路径**不可配**，必须与 `deploy.ps1` 同级。**

### ★★★ 三个前置检查（全 `exit 2`）

```
① $Game 未给
② payload 不存在
③ 游戏根不存在
```

---

## 九、★★★★ 核心逻辑：**只比大小**（第 20–51 行）

```powershell
Get-ChildItem $PAY -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($PAY.Length + 1)
    $target = Join-Path $dstRoot $rel
    $tdir = Split-Path -Parent $target
    $need = $true
    if (Test-Path $target) {
        $cur = Get-Item $target
        if ($cur.Length -eq $_.Length) { $need = $false; $script:skipped++ }   # ★★★ 只比大小
        else {
            if ($DryRun) { $script:backed++ }
            else {
                try { Copy-Item $target ($target + '.bak-' + $stamp) -Force; $script:backed++ }
                catch { Write-Host ("  [WARN] cannot back up " + $rel + " (in use?)") }
            }
        }
    }
    if ($need) {
        if ($DryRun) {
            $script:copied++
            Write-Host ("  [DRY] would deploy " + $rel)
        } else {
            try {
                if (-not (Test-Path $tdir)) { New-Item -ItemType Directory -Force -Path $tdir | Out-Null }
                Copy-Item $_.FullName $target -Force
                $script:copied++
            } catch {
                Write-Host ("  [FAIL] " + $rel + " : " + $_.Exception.Message)
                $script:failed++
            }
        }
    }
}
```

### ★★★★★ 缺陷：`$cur.Length -eq $_.Length` 是**唯一的"相同"判据**

★★★ **⇒ 后果（报告 010 已实测）：**
```
payload\Ayria\Plugins\Localnetworking.Ayria32  519,168 B  （我替换的版本）
游戏根\Ayria\Plugins\Localnetworking.Ayria32   519,168 B  （原始版本）
                                                ↑ 大小相同
deploy.ps1 判定 "same" ⇒ 跳过 ⇒ ★ 修复永远部署不进去，且不报错
```

★★★ **⇒ 这是**静默失败**：`deploy: copied=N same=M` 里 `M` 会+1，
**用户看不出哪一项被跳过了。**

### ★★ 但换个角度看：这是**有意的取舍**

★ **理由**：客户端运行时文件被锁，**读哈希会失败或很慢**；
**大小比对是"客户端在跑也能安全重跑"的折中。**

★★ **⇒ 代价是"同大小不同内容"永远不更新。**

### ★★★ `.bak-<stamp>` 备份（第 31 行）

```powershell
Copy-Item $target ($target + '.bak-' + $stamp) -Force
```

★★ **⇒ `$stamp` = `yyyyMMdd-HHmmss`（第 11 行）。**

★★★ **⇒ **每次部署都生成新备份** ⇒ 多次部署后 `.bak` 堆积。**

★ **⇒ 且备份文件**不清理**、**不在清单里**（若在游戏根则无所谓）。**

### ★★ 错误处理

```powershell
catch { Write-Host ("  [WARN] cannot back up " + $rel + " (in use?)") }
```
★★ **⇒ 备份失败只 `WARN`，**不增加 `$failed`** ⇒ 会继续覆盖（丢掉备份）。**

```powershell
catch { Write-Host ("  [FAIL] " + $rel + " : " + $_.Exception.Message); $script:failed++ }
```
★★ **⇒ 复制失败计入 `$failed` ⇒ `exit 3`。**

---

## 十、★★★ 汇总行与退出码（第 53–55 行）

```powershell
Write-Host ("deploy: copied=" + $copied + " same=" + $skipped + " backed_up=" + $backed + " failed=" + $failed + $(if ($DryRun) { " (dry run)" } else { "" }))
if ($failed -gt 0) { exit 3 }
exit 0
```

★★★ **⇒ 四个计数 + 退出码 0/3：**
```
copied    实际复制数
same      ★ 大小相同跳过数（含"同大小不同内容"）
backed_up 备份数
failed    失败数
exit 3    有失败
exit 0    全部成功（或全部跳过）
```

★ **⇒ `run.cmd:84` 用 `if errorlevel 3` 捕获，提示"客户端还在运行吗"。**

---

## 十一、★★★ `deploy.ps1` 是**纯 ASCII**（验证）

★ **通读全文（55 行），**没有任何中文字符**。**

★★★ **⇒ 与 `deploy.ps1:2` 的声明"ASCII only on purpose"**一致** ✓**

★★ **⇒ 所以 `deploy.ps1` **不需要 BOM**（上一轮也确实没给它加）。**

---

## 十二、★★★ 两份脚本的**对比总结**

| 项 | `preflight.ps1` | `deploy.ps1` |
|---|---|---|
| 大小 | 4,062 B | 2,032 B |
| 中文 | ★★★ **9 处** | ★ 无 |
| BOM | ★★★ **需要**（已加） | 不需要 |
| "ASCII only" 声明 | ✗ 无此声明 | ✓ 有 |
| 参数 | `$Game` / `$Apply` | `$Game` / `$DryRun` |
| 写操作 | hosts / dwauth.ini / stun.ini | 复制文件 + 备份 |
| 退出码 | 0 / 2 | 0 / 2 / 3 |
| 核心缺陷 | ★★ hosts IP 错只 Warn；dwauth 检查过宽 | ★★★ 只比大小 |

---

## 十三、结论

### 1. ★★★ `preflight.ps1` 是**宽松的检查器**

★★ **三处宽松：**
```
① hosts IP 错 → Warn（不阻塞）
② dwauth.ini 只查 2 个子串
③ stun.ini 缺失 → Warn（不阻塞）
```

★★★ **⇒ 它能通过的环境，**不一定真能跑**。**

### 2. ★★★ `deploy.ps1` 的"只比大小"是**已知的静默失败源**

★★ **实测证据已在包里（报告 010）。**

### 3. ★★★ `preflight.ps1` 有 9 处中文，与 `deploy.ps1` 的 "ASCII only" 策略不一致

★★ **⇒ 这就是上一轮必须给它加 BOM 的根本原因。**

### 4. ★★ hosts 用**块标记**包裹，可整块撤销 —— 好设计

### 5. ★★ `IIPS\cacert.pem` 只 Warn，但后果可能严重

---

## 十四、下一步

- `run.cmd`（4,243 B）逐字节
- `1-构建.cmd`（1,388 B）逐字节
- `source\xmake.lua`（14,013 B）—— 验证 `ol_deploy` phony target
- `bundle\` 五个脚本逐字节
