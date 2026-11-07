# 学习报告 035（重开）— `nt10.py` `main()` 的启动分支与失败判定

**学习范围**：第 1642–1751 行（80/230 最终定案 + 平台 ID + ShellExecuteW + 存活校验 + 句柄）
**性质**：全实测
**★★★ 本报告收录**80/230 的最终否证**（"不是回得太大，是回非空就卡"）

---

## 一、★★★★★ `80/230` 的**最终定案**（第 1642–1673 行）

### 1.1 ★★★ 老外的原始依据（第 1643–1649 行，逐字）

```python
# `research\source_reconstruction_progress.md:52-57` 逐字：
#   "CODOL then performs a distinct late Marketplace initialization through service `80`,
#    task `230`. **Its completion callback clears the same 20,000-entry cache and replaces
#    it with the returned objects. The reconstructed service now maps task `230`'s
#    empty-context request to the same persistent inventory backing store as task `203`.**
#    Runtime sequence `26` returned **the same 28 objects**, the post-initialization native
#    count remained `28`, and the warehouse displayed owned supplies without a purchase."
```

★★★ **⇒ 老外的实测：**
```
runtime sequence 26 返回**同样的 28 个对象**
        ↓
初始化后原生计数保持 **28**
        ↓
仓库显示了已拥有的补给（无需购买）
```

### 1.2 ★★★ 作者的推论（第 1651–1653 行）

```python
# ⇒ 230 要回**和 203 同一批**对象。老外那次是 28 个（他们测试库存小）。
# ⇒ 我们用已证可用的 400 件（≈24 KB），**远离 512 KB 天花板** ——
#   19:0x 那次卡连接中是 `=1` + `MAX_ITEMS=8460`（524 KB 顶到缓冲上限），不是 230 本身。
```

★★ **⇒ 假设："400 件（≈24 KB）是安全中间地带"。**

### 1.3 ★★★★★ **19:31 实测：假设被否掉**（第 1659–1669 行，逐字）

```python
# ★★★★ 2026-10-05 19:31 实测结果：**= "1" + MAX_ITEMS=400 依然卡连接中。已回滚为 "0"。**
#
# 现场（`D:\repo\03-live\client\TESTOL\Ayria\Logs\AlwaysofflineRe.Localnet32.log`，客户端 pid=20456 起于 19:29:44）：
#   19:30:07 seq=27 `80/230` 请求 3 B ⇒ 应答 **24,826 B**
#   19:30:10 seq=30 `10/10` / 19:30:12 seq=31..33 `71/7` / 19:30:18 seq=34 `68/3` / 19:30:23 seq=35 `71/3`
#   ⇒ **之后 40 秒零请求**（19:31:04 复核：socket 仍 Established 于 127.0.0.2:3074，进程 Responding=True，1488 MB）
#
# ⇒ **"400 件 ≈24 KB 是安全中间地带"这个假设被否掉了（rejected）。**
#   24,826 B 与 17:17「卡连接中 #1」的字节数**逐字节相同**，停点也相同（seq 34-35）。
#   ⇒ 触发条件**不是"回得太大"**（524 KB 卡、24 KB 也卡），而是
#     **`80/230` 只要回非空对象就卡**。230 的正确应答形态仍是**空**。
#
# ⇒ 真解方向改判：不再走"230 发库存"，改走 `:1597-1600` 那条 ——
#   在 `8/1` **之前**让 203 的库存就位，230 继续回空。
```

### ★★★★★ 完整的实测现场

| 项 | 值 |
|---|---|
| 客户端 pid | **20456** |
| 启动时刻 | **19:29:44** |
| `80/230` 请求 | **19:30:07 seq=27，请求 3 B** |
| 应答 | **24,826 B** |
| 后续任务 | `10/10` / `71/7` ×3 / `68/3` / `71/3`（seq 30–35） |
| ★★★ 结果 | **之后 40 秒零请求** |
| 复核（19:31:04） | socket 仍 **Established** 于 `127.0.0.2:3074`，进程 **Responding=True**，**1488 MB** |

★★★ **⇒ 三条关键结论：**
```
① "400 件 ≈24 KB 是安全中间地带" 假设 **被否掉**
② 24,826 B 与 17:17「卡连接中 #1」**逐字节相同**，停点也相同（seq 34-35）
③ ⇒ 触发条件**不是"回得太大"**，而是
   ★★★ **`80/230` 只要回非空对象就卡**
```

★★★ **⇒ 真解方向改判：**
```
不再走"230 发库存"
        ↓
改走：在 `8/1` **之前**让 203 的库存就位，230 继续回空
```

### 1.4 ★★ 最终设置（第 1673 行）

```python
os.environ["OLMOD_MARKETPLACE_ANSWER_230"] = "0"
```

---

## 二、★★★★ `OLMOD_PLATFORM_USER_ID`（第 1674–1681 行）

```python
# ★ 2026-10-05 19:5x：把 platform user id 也交给**客户端进程**。
#
# `runtime.md:108-110` 逐字："CODOL 当前自然认证使用 task 32，该 payload **只携带
# session key、不携带 XUID**；backend 的 `AuthSession` 因此**必须以同一
# `OLMOD_PLATFORM_USER_ID` 初始化身份**，再由对应玩家目录解析名字。"
# 值取 `Platform.json` 的 `platformUserId`（= 01100001DEADC0DE），
# 与客户端自己上报的 OpenID 同一个数。
os.environ["OLMOD_PLATFORM_USER_ID"] = "01100001DEADC0DE"
```

### ★★★★★ 关键信息

| # | 信息 | 内容 |
|---|---|---|
| 1 | 认证 task | **32** |
| 2 | ★★★ payload 内容 | **只携带 session key，不携带 XUID** |
| 3 | ⇒ 后果 | backend 的 `AuthSession` 必须**以同一 `OLMOD_PLATFORM_USER_ID` 初始化身份** |
| 4 | ★ 值 | **`01100001DEADC0DE`**（= `Platform.json` 的 `platformUserId`） |
| 5 | ★★ 一致性 | **与客户端自己上报的 OpenID 同一个数** |

★★★ **⇒ 完整的身份链：**
```
客户端 task 32 上报：session key（★ 不含 XUID）
        ↓
backend 拿不到身份
        ↓
★ 必须用 OLDMOD_PLATFORM_USER_ID 显式初始化 AuthSession
        ↓
再由对应玩家目录解析名字
```

★★ **⇒ 而 `01100001DEADC0DE` 与上一轮报告 017 的 `Platform.json` **完全一致**。**

---

## 三、★★★ 六条启动日志（第 1682–1688 行）

```python
log("[A] OLMOD_UNLOCK_ALL=1（★ 19:4x 从 0 改回：8/1 校验那一刻 203 还没来，谓词是唯一拥有权来源）")
log("[A] OLMOD_MARKETPLACE_ANSWER_230=0（230 必须空应答；非空=卡连接中，24,826 B / 524,298 B 两次实证）")
log("[A] OLMOD_MARKETPLACE_MAX_ITEMS=5361 + MAX_REPLY_BYTES=524288（只钳 203；5361 件/332,450 B 是已实测成功点）")
log("[A] OLMOD_PLATFORM_USER_ID=01100001DEADC0DE（与客户端同值，runtime.md:108-110）")
log("[A] OLMOD_LSG_SECRETS=%s（清 OLMOD_EXTERNAL_AUTH3 / 不设 OLMOD_CLAIM_LEGACY_AUTH）" % _secrets)
log("[A] OLMOD_SERVE_PRIVATE_PROFILE=1（下发 secure 档案 → 满级）")
```

★★★ **⇒ 六行日志，每行都带**理由**：**
```
① UNLOCK_ALL=1    ← 8/1 校验时 203 还没来，谓词是唯一拥有权来源
② ANSWER_230=0    ← 非空=卡连接中，24,826 B / 524,298 B 两次实证
③ MAX_ITEMS=5361  ← 只钳 203；5361 件/332,450 B 是已实测成功点
④ PLATFORM_USER_ID ← 与客户端同值，runtime.md:108-110
⑤ LSG_SECRETS     ← 清 EXTERNAL_AUTH3 / 不设 CLAIM_LEGACY_AUTH
⑥ SERVE_PRIVATE_PROFILE ← 下发 secure 档案 → 满级
```

---

## 四、★★★★★ `ShellExecuteW` 与 pid 重找（第 1689–1719 行）

### 4.1 ★★★ 启动调用（第 1689–1696 行）

```python
try:
    _rc = ctypes.windll.shell32.ShellExecuteW(
        None, "open", _inj, '"%s" -qa' % _tgt, a.root, 1)
except Exception as _ie:
    log("  !! ShellExecuteW 异常 %r" % (_ie,))
    _rc = 0
if int(_rc) <= 32:
    log("  !! ShellExecuteW 返回 %s (<=32 即失败)" % (_rc,))
```

★★★ **⇒ `ShellExecuteW` 的六个参数：**
```
None               ← hwnd
"open"             ← lpOperation
_inj               ← lpFile（注入器路径）
'"%s" -qa' % _tgt  ← lpParameters（★ 客户端路径 + -qa）
a.root             ← lpDirectory
1                  ← nShowCmd（SW_SHOWNORMAL）
```

★★★ **⇒ `<= 32` 即失败（`ShellExecuteW` 的标准约定）。**

★ **⇒ 注释（第 1412–1414 行）说明了为什么必须用 `ShellExecuteW`：**
> 实测 `subprocess.Popen` 会让注入器报 `"Could not create process. Error: 2"`
> （`ERROR_FILE_NOT_FOUND`），而 `UseShellExecute=true` 就成功
> （**老外 `Launch_OLMod.bat` 正是这么写的**）。

### 4.2 ★★★ pid 重找（第 1697–1705 行）

```python
pid = 0
for _ in range(60):                 # 有界等待: 最多 ~15s 找出真游戏进程
    time.sleep(0.25)
    pid = _find_game_pid(a.exe)
    if pid:
        break
if not pid:
    log("  !! 第 %d 次: 注入后 15s 内没找到 %s 进程, 重试" % (_try, a.exe))
    continue
p = None                            # ★ 注入模式下没有 Popen 对象
```

★★★ **⇒ **60 次 × 0.25 秒 = 15 秒** 有界等待。**

★★ **⇒ `p = None` —— 注入模式下没有 `Popen` 对象（这是关键差异）。**

★ **⇒ 与注释"注入后 pid 必须重新按进程名找"完全对应。**

### 4.3 ★★★ 4 秒存活校验（第 1710–1719 行）

```python
alive = True
for _ in range(16):                 # 观察 4s
    time.sleep(0.25)
    if not _game_pids(a.exe):
        alive = False
        break
if alive:
    break
log("  !! 第 %d 次注入式启动在 4s 内退出, 重新拉起" % _try)
continue
```

★★★ **⇒ 16 次 × 0.25 秒 = **4 秒** 观察窗口（与注释的"4s 内退出就重试"一致）。**

---

## 五、★★★ 非注入分支（第 1721–1736 行）

```python
p = subprocess.Popen([os.path.join(a.root, a.exe)], cwd=a.root)
pid = p.pid
t_launch = time.time()
log("game pid=%d mutex=%s apis=%s  (第 %d 次启动)"
    % (pid, bool(hm), apis, _try))
alive = True
for _ in range(16):                 # 观察 4s
    time.sleep(0.25)
    if p.poll() is not None:
        alive = False
        break
if alive:
    break
rc = p.poll()
log("  !! 第 %d 次启动在 %.1fs 内退出 rc=%s(0x%X), 重新拉起"
    % (_try, 4.0, rc, (rc or 0) & 0xFFFFFFFF))
```

★★★ **⇒ 与注入分支的三处差异：**

| 项 | 注入分支 | 非注入分支 |
|---|---|---|
| 启动方式 | `ShellExecuteW` | **`subprocess.Popen`** |
| `pid` 来源 | ★ **`_find_game_pid`** | **`p.pid`** |
| 存活判定 | `_game_pids(a.exe)` | **`p.poll() is not None`** |
| `p` | **`None`** | **Popen 对象** |

★★★ **⇒ 非注入分支的 `pid = p.pid` 是**正确的**（因为直接起的就是游戏）。**

---

## 六、★★★ 五次重试后的放弃判定（第 1738–1744 行）

```python
if _inject:
    if not pid or not _game_pids(a.exe):
        log("EXC: 注入式启动连续 5 次都没起来, 放弃本轮")
        return
elif p is None or p.poll() is not None:
    log("EXC: 连续 5 次都是坏启动(0xC0000005), 放弃本轮")
    return
```

★★★ **⇒ 两个分支的放弃条件不同：**
```
注入模式：not pid **或** not _game_pids(a.exe)
非注入：  p is None **或** p.poll() is not None
```

★ **⇒ 非注入分支的日志明确写了 **`0xC0000005`**（与 docstring 的"坏启动"一致）。**

---

## 七、★★★ 早期句柄（第 1746–1747 行）

```python
# 早期句柄(实测它到 t=6s 仍可读写; 后开的会被 ACE 拒绝)
h = k32.OpenProcess(PROC_ALL, False, pid)
```

★★★★ **⇒ 一条**关键的实测**：**
```
早期打开的句柄：到 t=6s 仍可读写
后开的句柄：    ★ 会被 ACE 拒绝
```

★★★ **⇒ 所以必须在**启动后立即** `OpenProcess`，拿到句柄后一直用。**

★ **⇒ `PROC_ALL = 0x0438`（`VM_OPERATION|VM_READ|VM_WRITE|QUERY_INFORMATION`）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 老外实测 | 230 返回 **28 个对象**，原生计数保持 28 |
| 2 | ★★★★★ **19:31 否证** | **`MAX_ITEMS=400` 依然卡连接中** |
| 3 | 实测现场 | pid **20456** / `80/230` 应答 **24,826 B** / 之后 **40 秒零请求** |
| 4 | ★★ 复核状态 | socket **Established** / **Responding=True** / **1488 MB** |
| 5 | ★★★★★ **最终结论** | **不是"回得太大"，而是"回非空对象就卡"** |
| 6 | 真解方向 | **在 `8/1` 之前让 203 库存就位，230 继续回空** |
| 7 | ★★★ 认证 task | **32**，payload **只携带 session key，不携带 XUID** |
| 8 | ★★ `OLMOD_PLATFORM_USER_ID` | **`01100001DEADC0DE`**（与 OpenID 同值） |
| 9 | ★★ `ShellExecuteW` | 6 参数，**`<= 32` 即失败** |
| 10 | ★★ 为什么不用 Popen | Popen 报 `Error: 2`；老外 `Launch_OLMod.bat` 用 ShellExecute |
| 11 | ★ 注入后 pid 等待 | **60 × 0.25s = 15 秒** |
| 12 | 存活观察 | **16 × 0.25s = 4 秒** |
| 13 | ★★★ 非注入分支 | `p.pid` / `p.poll()`（**与注入分支完全不同**） |
| 14 | 重试次数 | **5 次** |
| 15 | ★★★ **早期句柄** | **t=6s 仍可读写；后开的被 ACE 拒绝** |

---

## 九、结论

### 1. ★★★★★ **80/230 的最终定案**：不是"回得太大"，而是"回非空就卡"

```
524,298 B 卡
24,826 B  也卡（逐字节与 17:17 那次相同，停点也相同）
        ↓
★★★ ⇒ **80/230 只要回非空对象就卡**
```

### 2. ★★★★ 真解方向改判为"**在 `8/1` 之前让 203 库存就位**"

### 3. ★★★★★ `task 32` 的 payload **不含 XUID** ⇒ 必须显式给 `OLMOD_PLATFORM_USER_ID`

### 4. ★★★ **早期句柄到 t=6s 仍可读写，后开的被 ACE 拒绝**

★ **⇒ 必须在启动后立即 `OpenProcess`。**

### 5. ★★ 注入与非注入分支的 pid/存活判定**完全不同**

---

## 十、下一步

- `main()` 剩余（第 1751 行起）—— TAS 注入、hook 安装、线程启动
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
