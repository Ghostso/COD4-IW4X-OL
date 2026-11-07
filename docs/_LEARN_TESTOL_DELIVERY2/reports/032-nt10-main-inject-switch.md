# 学习报告 032（重开）— `nt10.py` `main()` 参数与注入开关

**学习范围**：第 1326–1395 行（参数 + 日志 + 补丁规格 + 注入开关 + pid 查找）
**性质**：全实测
**★★★ 本报告收录**注入开关的完整定义**与**"必须重新找 pid"的原因**

---

## 一、★★★ 完整的参数表（第 1319–1334 行）

```python
ap.add_argument("--root", default=r"D:\repo\03-live\client\TESTOL")
ap.add_argument("--exe", default="codoMP_client_shipRetail.exe")
ap.add_argument("--mutex", default=r"Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}")
ap.add_argument("--apis", default="connect,sendto,gethostbyname")
ap.add_argument("--direct", default="")
ap.add_argument("--delay", type=float, default=2.5)
ap.add_argument("--secs", type=int, default=60)
ap.add_argument("--show", type=int, default=6)
ap.add_argument("--only-exe", action="store_true")
ap.add_argument("--out", default="n9.txt")
ap.add_argument("--ps-probe", action="store_true",
                help="出生点/位置探针: 周期性扫客户端内存里的本地 playerstate, "
                     "命中预测态后定点轮询写 predicted.bin")
```

### ★★★ 11 个参数

| # | 参数 | 默认 | 类型 |
|---|---|---|---|
| 1 | `--root` | `D:\repo\03-live\client\TESTOL` | str |
| 2 | `--exe` | `codoMP_client_shipRetail.exe` | str |
| 3 | `--mutex` | `Global\{5BD75B76-...}` | str |
| 4 | `--apis` | `connect,sendto,gethostbyname` | str |
| 5 | `--direct` | `""` | str |
| 6 | `--delay` | **`2.5`** | float |
| 7 | `--secs` | **`60`** | int |
| 8 | `--show` | **`6`** | int |
| 9 | `--only-exe` | False | flag |
| 10 | `--out` | **`n9.txt`** | str |
| 11 | `--ps-probe` | False | flag |

★★★ **⇒ `--ps-probe` 的移植说明（第 1331–1332 行，逐字）：**
```python
# ★ 2026-10-05 13:30 移植自 KK 2026-10-04 归档：出生点/位置探针。
#   B 路线（镜像客户端预测态）必须先有它写出 predicted.bin。
```

★★★ **⇒ "B 路线（**镜像客户端预测态**）必须先有它写出 `predicted.bin`"。**
**⇒ 说明"B 路线"是**回发预测态**的方案（与我们项目方向一致）。**

★ **⇒ 来源："移植自 **KK** 2026-10-04 归档" —— 第三方贡献。**

---

## 二、★★★ 日志双写（第 1336–1345 行）

```python
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
snap = os.path.splitext(os.path.abspath(a.out))[0]
fh = open(a.out, "w", encoding="utf-8", buffering=1)

def log(s):
    print(s, flush=True)
    fh.write(s + "\n")
```

★★★ **⇒ 四个要点：**
```
① stdout 强制 UTF-8（errors="replace"）
② snap = 输出文件去掉扩展名的路径（★ 用于派生的快照文件名）
③ fh 用 buffering=1（★ 行缓冲 ⇒ 崩溃也不丢最后一行）
④ log() 同时写 stdout 和文件
```

★ **⇒ `buffering=1` 是**关键**（默认是块缓冲，崩溃会丢数据）。**

---

## 三、★★★★ 补丁规格来自文件（第 1347–1355 行）

```python
# 补丁规格来自文件(避免命令行开关被环境回滚)
PS = ""
pf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_spec.txt")
if os.path.exists(pf):
    try:
        PS = open(pf, encoding="utf-8").read().strip()
    except Exception:
        PS = ""
log("补丁规格 = %r (来自 patch_spec.txt)" % PS)
```

★★★ **⇒ 注释理由（逐字）：**避免命令行开关被环境回滚**。**
**⇒ 与 docstring 第 20 行的"命令行开关会被环境回滚, 文件不会"一致。**

★ **⇒ `patch_spec.txt` **不在交付包里**（需验证），所以 `PS = ""`。**

★★ **⇒ `PS` 为空 ⇒ `parse_patches("")` 返回空列表 ⇒ **没有额外补丁**。**

---

## 四、★★★★ `zN` 占位符的过滤（第 1357–1361 行）

```python
# 允许用 "zN" 占位: 只为把代码洞/cnt 槽位预留出来, 不当 hook 装
apis = [x for x in a.apis.split(",") if x and not re.fullmatch(r"z\d+", x)]
for d in a.direct.split(","):
    if d.strip():
        apis.append("@" + d.strip())
```

★★★ **⇒ 两个步骤：**
```
① 过滤掉 zN（正则 `z\d+`）—— ★ 占位符，不装 hook
② --direct 的项加 "@" 前缀后追加
```

★★ **⇒ 为什么要占位：**把代码洞/cnt 槽位预留出来**（槽位按列表顺序分配）。**

★ **⇒ `@` 前缀走"直接地址"路径（`@tenproxy.dll:0x6BD0`）。**

---

## 五、★★★★★ **注入开关**（第 1363–1374 行）—— 全包最关键的一段

### 5.1 ★★★ 坏启动率（第 1363–1364 行，逐字）

```python
# ★ 启动 + 存活校验: 这台机器上"坏启动"(0xC0000005 @ t≈2s)概率约 20-40%,
#   只要在启动后 4s 内就退出, 就直接重新拉起, 不用让上层 run_all 从头再来。
```

★★★ **⇒ 两个精确数据：**
```
坏启动率：**20-40%**
崩溃时刻：**t ≈ 2s**
崩溃码：**0xC0000005**（访问冲突）
判定：启动后 **4s 内**退出
```

★★★ **⇒ `0xC0000005 @ t≈2s` 正是报告 020 说的"撞上 TP3 在 t≈2s 的 ws2_32 完整性检查"。**

### 5.2 ★★★★★ 注入开关的完整注释（第 1366–1372 行，逐字）

```python
# ─────────────────────────────────────────────────────────────────────
# 2026-10-05 02:10  A 路线实验：注入式启动（Ayria）
#   开关：同目录放 inject_ayria.on，或设 NT10_INJECT=1。默认走原「直接起 exe」。
#   为什么需要：游戏服务端是注入式插件 Ayria\Plugins\CodolGameServer.Localnet32，
#   不注入就不会加载 => 靶场卡「等待链接」。
#   注意：注入后 pid 必须重新按进程名找 —— 注入器的 pid 不是游戏 pid，
#         而后续 TAS 注入 / 内存读会话密钥都依赖真游戏 pid。
# ─────────────────────────────────────────────────────────────────────
```

### ★★★★★ 四条信息

| # | 信息 | 内容 |
|---|---|---|
| 1 | **路线名** | **"A 路线实验：注入式启动（Ayria）"** |
| 2 | **开关** | `inject_ayria.on` 文件 **或** `NT10_INJECT=1`；**默认直接起 exe** |
| 3 | ★★★ **为什么需要** | 服务端是**注入式插件** `Ayria\Plugins\CodolGameServer.Localnet32`，**不注入就不会加载 ⇒ 靶场卡「等待链接」** |
| 4 | ★★★ **关键陷阱** | **注入后 pid 必须重新按进程名找**（注入器的 pid ≠ 游戏 pid） |

★★★ **⇒ 第 3 条是**全包最重要的架构说明**：**
```
游戏服务端 = 注入式插件 CodolGameServer.Localnet32
        ↓
不注入 ⇒ 插件不加载
        ↓
★★★ 靶场卡「等待链接」
```

★★★ **⇒ 第 4 条是**实现陷阱**：**
```
subprocess.Popen([Injector32.exe, ...]).pid  = ★ 注入器的 pid
        ↓
真正的游戏进程是注入器**创建**的，pid 不同
        ↓
后续所有操作（TAS 注入 / 读密钥）都需要**真游戏 pid**
        ↓
★ 必须按进程名重新找
```

### 5.3 ★★★ 开关的实际实现（第 1373–1374 行）

```python
_inject = (os.environ.get("NT10_INJECT") == "1") or os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "inject_ayria.on"))
```

★★★ **⇒ 两个条件任一成立即注入：**
```python
NT10_INJECT == "1"                                    # 环境变量
os.path.exists("<bundle>\inject_ayria.on")            # 同目录文件
```

★★★ **⇒ 而 `launch_chain.py` **两者都不设**（报告 018 已确认 `chain_env` 无 `NT10_INJECT`），**
**包里也**没有 `inject_ayria.on`**（上一轮已验证）。**

★★★ **⇒ 所以默认 `_inject = False` ⇒ **走"直接起 exe"** ⇒ **插件不加载**。**

★★ **⇒ 这与 README 第 52 行的"client ← `Ayria\Injector32.exe`，由 `nt10.py` 拉起"**矛盾**。**

---

## 六、★★★ `_game_pids` 与 `_find_game_pid`（第 1376–1395 行）

### 6.1 `_game_pids`（第 1376–1392 行）

```python
def _game_pids(name):
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name,
                              "/FO", "CSV", "/NH"],
                             capture_output=True, text=True,
                             errors="replace").stdout
    except Exception:
        return []
    found = []
    for line in out.splitlines():
        parts = [x.strip().strip('"') for x in line.split(",")]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                found.append(int(parts[1]))
            except Exception:
                pass
    return found
```

★★★ **⇒ 用 `tasklist /FO CSV /NH` 拿进程列表，手工解析 CSV。**

★ **⇒ `/NH` = 无表头；`/FI IMAGENAME eq <name>` = 按镜像名过滤。**

★★ **⇒ 手工解析（`strip('"')` + `split(",")`）—— 因为 CSV 里字段可能带引号。**

★ **⇒ 校验 `parts[0].lower() == name.lower()` —— 防止 `/FI` 过滤失效时的误匹配。**

### 6.2 ★★★ 为什么用 `tasklist` 而不是 toolhelp

★★★ **⇒ 因为 `docstring` 说"模块枚举必须早（t≈0.2s）：晚了会被 **ACE 封掉**（toolhelp 返回空）"。**

★★ **⇒ `tasklist` 是**独立进程**，不受 ACE 对游戏进程内 toolhelp 的限制。**

★ **⇒ 这是**绕过 ACE 的正确方式**。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 参数总数 | **11 个** |
| 2 | ★★ `--ps-probe` 说明 | **B 路线（镜像预测态）必须先有它写 `predicted.bin`** |
| 3 | 移植来源 | **KK 2026-10-04 归档** |
| 4 | 日志 | 双写 + **`buffering=1`**（行缓冲） |
| 5 | ★★ 补丁规格来源 | `patch_spec.txt`（**避免命令行被环境回滚**） |
| 6 | ★ `zN` 过滤 | 正则 `z\d+`（占位符不装 hook） |
| 7 | `--direct` | 加 `@` 前缀 |
| 8 | ★★★★★ **坏启动率** | **20-40%**，`0xC0000005 @ t≈2s`，4s 内退出 |
| 9 | ★★★★★ **A 路线** | **注入式启动（Ayria）** |
| 10 | ★★★ 开关 | `inject_ayria.on` 或 `NT10_INJECT=1`，**默认直起** |
| 11 | ★★★★★ **为什么需要注入** | **不注入插件不加载 ⇒ 靶场卡「等待链接」** |
| 12 | ★★★ **关键陷阱** | **注入后 pid 必须重找**（注入器 pid ≠ 游戏 pid） |
| 13 | ★★ `_game_pids` | `tasklist /FO CSV /NH` 手工解析 |
| 14 | ★ 为什么用 tasklist | **toolhelp 被 ACE 封，tasklist 是独立进程** |

---

## 八、结论

### 1. ★★★★★ **"不注入 ⇒ 插件不加载 ⇒ 靶场卡「等待链接」"** 是核心架构说明

★★★ **⇒ 这是 README 第 52 行那句话的**源码级依据**。**

### 2. ★★★★★ **默认 `_inject = False`** 与 README 的描述**矛盾**

```
README:  client ← Ayria\Injector32.exe，由 nt10.py 拉起
代码:    默认 _inject = False ⇒ subprocess.Popen([client.exe]) 直起
```

### 3. ★★★ **注入后 pid 必须重找**（注入器 pid ≠ 游戏 pid）

### 4. ★★★ **坏启动率 20-40%，`0xC0000005 @ t≈2s`** 与 TP3 检查吻合

### 5. ★★ `tasklist` 是绕过 ACE 的正确方式（独立进程）

### 6. ★★ `buffering=1` 保证崩溃不丢日志

---

## 九、下一步

- `main()` 剩余（第 1395 行起，约 60 行）—— **启动、hook 安装、线程编排**
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
