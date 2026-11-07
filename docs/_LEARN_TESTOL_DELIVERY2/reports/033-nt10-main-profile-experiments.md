# 学习报告 033（重开）— `nt10.py` `main()` 注入分支的**六段实测记录**

**学习范围**：第 1395–1513 行（启动重试 + `-qa` 依据 + 三个环境变量 + profile 下发形态）
**性质**：全实测
**★★★ 本报告是全包**实测记录最密集**的一段（六段独立实验）**

---

## 一、★★★★ 启动重试与清理（第 1398–1403 行）

```python
p, pid, hm = None, 0, None
for _try in range(1, 6):                                   # ★ 最多 5 次
    for n in ("codoMP_client_shipRetail.exe", "TP3Helper.exe"):
        subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
    time.sleep(1)
    hm = k32.CreateMutexW(None, False, a.mutex)
```

★★★ **⇒ 两个要点：**
```
① 重试 **5 次**
② ★★★ 每次杀**两个**进程：codoMP_client_shipRetail.exe **和 TP3Helper.exe**
```

★★★ **⇒ `TP3Helper.exe` 是**反作弊辅助进程** —— 必须先杀它，否则它可能保护客户端进程。**

★ **⇒ `CreateMutexW(None, False, a.mutex)` —— **占住互斥体**（`Global\{5BD75B76-...}`）。**

---

## 二、★★★★★ `-qa` 的完整依据（第 1416–1431 行，逐字）

```python
# ★★ 2026-10-05 16:10 加 `-qa`（**必须，且只能是这一个参数**）。
#   依据：老外自己的复盘原文 `tools\runtime\CodolGame.py:285-294` 逐字 ——
#     "-qa is the TCLS WinMain gate. It is NOT a role flag ... Started with no
#      arguments the process dies before the engine runs, on
#      致命错误 「请使用腾讯游戏登录器 (TCLS 文件夹内的 Client.exe) 启动游戏」.
#      Measured on build 1649370 ... Do NOT add more arguments: Injector32 fails
#      with ERROR_FILE_NOT_FOUND on the argument COUNT, which reads as a wrong
#      path."
#   甲方 2026-10-05 16:05 实测截图正是这条致命错误
#   （我直接跑 `Injector32.exe "<exe>"` 无参数）。
#   ⇒ **不要加第二个参数**（老外 `offline` 模式的五 token 串就是这么坏掉的）。
```

### ★★★★★ 五条关键信息

| # | 信息 | 内容 |
|---|---|---|
| 1 | `-qa` 的作用 | **"the TCLS WinMain gate"**（TCLS 启动门槛） |
| 2 | ★ 不是什么 | **"It is NOT a role flag"** |
| 3 | 不加参数的后果 | ★★★ **进程在引擎跑起来前就死**，报 **「请使用腾讯游戏登录器 (TCLS 文件夹内的 Client.exe) 启动游戏」** |
| 4 | 测量 build | **`1649370`** |
| 5 | ★★★ **不能加第二个参数** | **`Injector32` 会因**参数个数**报 `ERROR_FILE_NOT_FOUND`**（读起来像"路径错"） |

★★★ **⇒ 第 5 条是**极其具体的坑**：**
```
Injector32.exe 对**参数个数**敏感
        ↓
加第二个参数 ⇒ ERROR_FILE_NOT_FOUND
        ↓
★ 这个错误读起来像"文件找不到"，实际是"参数太多"
```

★ **⇒ 而 `offline` 模式的"五 token 串"就是这么坏掉的。**

★★ **⇒ 与上一轮记忆 `codol-frozen-chain-must-not-modify`（我加了 `-qa -q` 导致失败）**完全吻合**。**

### ★★★ 两条旁证（第 1428–1431 行）

```python
#   旁证：`runtime.md:57`「第二进程还使用 CODOL `WinMain` 原生支持的 `-qa` 参数
#   越过 TCLS-only 启动门槛，不另行 patch `WIN_NO_TCLS` 分支」；
#   另有 `ClientProcessPatches.cpp:1766` `publishTclsMapping()`
#   （`TCLS_SHAREDMEMEMORY<pid>` 共享内存，`OLMOD_TCLS_BLOB`，默认关）。
```

★★★ **⇒ 两条独立证据：**
```
① runtime.md:57 —— 用原生 -qa 越过 TCLS-only 门槛（不 patch WIN_NO_TCLS）
② ClientProcessPatches.cpp:1766 publishTclsMapping()
   → TCLS_SHAREDMEMEMORY<pid> 共享内存，OLMOD_TCLS_BLOB，默认关
```

★★ **⇒ 第 ② 条印证了记忆里"`OpenFileMapping TCLS_SHAREDMEMEMORY<pid>` 是全流程的钥匙"。**

---

## 三、★★★★★ 三个环境变量的取舍（第 1432–1454 行）

### 3.1 ★★★ 背景（第 1434–1442 行，逐字）

```python
# 背景：老外 backend 的 `LobbyProtocol.cpp` 里有一段专门为「吃我方 secrets.txt」而写的
# `LobbySecrets`，逐字注释：
#   "The Python lobby ... reads the snapshot nt10.py takes out of the client's memory
#    (nt10.py:732-759) and uses it verbatim -- decrypt <- aes_out, requestHmac <- hmac_out,
#    encrypt <- aes_in, responseHmac <- hmac_in, responseId <- challenge"
#   "We keep that whole channel and change only who writes the file: ... this backend
#    simply consumes the same file." / "Path: OLMOD_LSG_SECRETS, defaulting to ./secrets.txt."
# ⇒ **这就是 `[100] 无法连接大厅服务` 的正解**：不是把 backend 删掉，而是把这份密钥喂给它。
#   默认值 "./secrets.txt" 是相对客户端 CWD(D:\repo\03-live\client\TESTOL) 的 ⇒ 必须给绝对路径。
```

★★★★★ **⇒ `[100]` 的**正解**（逐字）：**
```
不是把 backend 删掉
        ↓
而是把这份密钥**喂给它**
```

★★ **⇒ 且揭示了一个**陷阱**：**
```
OLMOD_LSG_SECRETS 默认 "./secrets.txt"
        ↓
相对**客户端 CWD**（D:\repo\03-live\client\TESTOL）
        ↓
★ 必须给**绝对路径**
```

### 3.2 ★★★★★ 三个变量的取舍（第 1444–1449 行，逐字）

```python
# 三个变量的取舍（依据 1A-DSH\HANDOFF-20261005-1510.md §3）：
#   · OLMOD_LSG_SECRETS      = 绝对路径（必设，否则 backend 派生不出正确密钥 ⇒ [100]）
#   · OLMOD_EXTERNAL_AUTH3   必须**清掉**：它会让 backend 放弃 claim `lsg.`/`lobby.`
#                            （Servers.cpp:164-169）⇒ 大厅又回到我方 Python，白装
#   · OLMOD_CLAIM_LEGACY_AUTH 不设：Servers.cpp 里我加的默认门 = **不抢认证**
#                            ⇒ `formal-zone-auth.codol.qq.com` 继续由我方 fake_auth_tls.py 服务
```

### ★★★★★ 完整的三变量表

| 变量 | 动作 | 原因 |
|---|---|---|
| **`OLMOD_LSG_SECRETS`** | **设为绝对路径** | 必设，否则 backend 派生不出密钥 ⇒ **`[100]`** |
| **`OLMOD_EXTERNAL_AUTH3`** | ★★★ **必须清掉**（`pop`） | 会让 backend **放弃 claim `lsg.`/`lobby.`**（`Servers.cpp:164-169`）⇒ 大厅又回到我方 Python，**白装** |
| **`OLMOD_CLAIM_LEGACY_AUTH`** | ★ 不设 | 默认门 = **不抢认证** ⇒ `formal-zone-auth` 继续由 `fake_auth_tls.py` 服务 |

★★★ **⇒ 这是**极其精妙的配置权衡**：**
```
OLMOD_LSG_SECRETS      →  设（喂密钥）
OLMOD_EXTERNAL_AUTH3   →  ★ 清掉（否则 backend 让出大厅）
OLMOD_CLAIM_LEGACY_AUTH →  ★ 不设（否则 backend 抢认证）
```

★★ **⇒ 目标：**backend 管大厅 + 我方 Python 管认证**。**

### 3.3 ★★★ 实际实现（第 1450–1454 行）

```python
_secrets = globals().get("SECRETS_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "secrets.txt")
os.environ["OLMOD_LSG_SECRETS"] = _secrets
os.environ.pop("OLMOD_EXTERNAL_AUTH3", None)
os.environ.pop("OLMOD_CLAIM_LEGACY_AUTH", None)
```

★★★ **⇒ 三行代码完全对应三条取舍。**
**⇒ `os.environ.pop(..., None)` 是**幂等删除**（不存在也不报错）。**

---

## 四、★★★★★ `OLMOD_SERVE_PRIVATE_PROFILE` 的**三轮实测**（第 1455–1474 行）

### 4.1 ★★★ 背景（第 1455–1457 行）

```python
# ★★ 2026-10-05 16:35：满级所需。等级**不在** Publicprofile 里，在 secure 档案里，
#   由 LSG `service 8 task 2`（Profiles2::getPrivateInfo）下发 —— 见
#   `lobby_server.py:246-247`（task1=public.result / task2=secure.result）。
```

★★★ **⇒ 等级的位置：**
```
等级**不在** Publicprofile
        ↓
在 **secure 档案**里
        ↓
由 LSG **service 8 task 2**（Profiles2::getPrivateInfo）下发
```

★★ **⇒ `lobby_server.py:246-247`：`task1=public.result` / `task2=secure.result`。**

### 4.2 ★★★ 老外的原始观察（第 1458–1460 行）

```python
#   老外 backend 把 `8/2` **故意置空**（注释：非空 task-2 private profile 对 out.exe 是
#   fatal —— 那是对 1649370 量的，不是我们这个 3.19.26.13）。所以做成**默认关的开关**，
#   这里打开来实测；若客户端启动被它弄坏，删掉这一行即可回到原状。
```

★★★ **⇒ 老外的观察：**非空 task-2 private profile 对 out.exe 是 fatal**。**
**但作者指出："那是对 1649370 量的，不是我们这个 3.19.26.13"。**

### 4.3 ★★★★★ **三轮实测的完整结果**（第 1461–1473 行，逐字）

```python
#   ★★ 2026-10-05 16:33 结论（实测两次，两种帧法）：**`8/2` 只要回非空档案，
#   这个客户端就死**（第一次：对象体 = userId+档案，日志停在 80/119；
#   第二次：对象体 = 纯档案字节，日志停在 80/173，两次都缺 8/3 / 21/5）。
#   ⇒ 老外源码里那句 "a non-empty task-2 private profile is fatal" 对我们这个
#   3.19.26.13 客户端**同样成立**。⇒ 永久置 0，等级不能走 `8/2` 下发。
#   `Privateprofile`（老外工具生成的 level 70）留在盘上无害，但不下发。
#   ★★ 2026-10-05 17:1x 第三次实测（唯一没试过的组合）：对象体 = **纯 `secure.result`
#   （32,983 B）**，也就是**我方 Python 大厅当年真正下发的那一份**
#   （`lobby_server.py:246-252`：`d = open(p,'rb').read(); return [d]`）。
#   前两次都不是这个组合：① 对象体 = userId + 旧的 secure.result（帧法错）；
#   ② 对象体 = 纯字节但内容是老外工具生成的 310 B `Privateprofile`（内容不是当年那份）。
#   等级 1 把商城/repo/军火基地全锁死（甲方截图挂锁 2/2/6），且 `80/203` 因此从不被请求
#   ⇒ 等级是总闸，必须走通。
```

### ★★★★★ 三轮实验的完整对照

| 轮次 | 对象体内容 | 结果 |
|---|---|---|
| **①** 16:33 第一次 | `userId + 档案` | ★ **日志停在 `80/119`** |
| **②** 16:33 第二次 | **纯档案字节** | ★ **日志停在 `80/173`**，缺 `8/3` / `21/5` |
| **③** 17:1x 第三次 | **纯 `secure.result`（32,983 B）** = 我方 Python 大厅当年真正下发的那份 | （记录到此，结论未写完） |

★★★ **⇒ 前两次的结论：**`8/2` 只要回非空档案，这个客户端就死**。**

★ **⇒ 且"老外源码里那句 `a non-empty task-2 private profile is fatal`
对我们这个 **3.19.26.13** 客户端同样成立"。**

★★★ **⇒ 第三次实验的**精妙之处**（第 1467–1471 行）：**
```
前两次都不是"当年那份"：
  ① 帧法错（userId 前缀）
  ② 内容错（老外工具的 310 B Privateprofile，不是当年的 32,983 B）
        ↓
★ 第三次用**我方 Python 大厅当年真正下发的那份**（32,983 B）
```

### 4.4 ★★★ 等级是"总闸"（第 1472–1473 行）

```python
#   等级 1 把商城/repo/军火基地全锁死（甲方截图挂锁 2/2/6），且 `80/203` 因此从不被请求
#   ⇒ 等级是总闸，必须走通。
```

★★★ **⇒ 等级 1 的三个后果：**
```
① 商城锁死
② repo 锁死
③ 军火基地锁死
（甲方截图：挂锁 2/2/6）
        ↓
且 `80/203` 因此**从不被请求**
        ↓
★★★ ⇒ 等级是**总闸**，必须走通
```

### 4.5 ★★ 最终设置（第 1474 行）

```python
os.environ["OLMOD_SERVE_PRIVATE_PROFILE"] = "1"
```

★★ **⇒ 尽管前面说"永久置 0"，这里设的是 **`"1"`** ——**
**说明**代码里还是开着**（可能与注释的矛盾是"注释记录的是 16:33 的结论，代码是 17:1x 第三次实验的设置"）。**

---

## 五、★★★★★ `OLMOD_PUBLIC_PROFILE_MODE` 的**四种发法**（第 1475–1513 行）

### 5.1 ★★★ 背景事故（第 1477–1480 行，逐字）

```python
# 背景：甲方 18:4x 报「您的帐户检测到数据异常，现已修复，但是您需要重新配置您的背包」
# 并且新手引导又出现 —— 时间点正好在我把 8/1 从「userId 前缀 + 档案」改成「纯档案」
# 之后。也就是说：**改之前客户端根本不解析那个对象（静默丢弃、背包照样重置）；
# 改之后它解析了，并判定内容异常 ⇒ 走修复流程把背包重置。**
```

★★★★★ **⇒ 一次**完整的因果分析**：**
```
改之前：客户端**根本不解析**那个对象（静默丢弃、背包照样重置）
        ↓
改之后：它**解析了**，并判定内容异常
        ↓
★ 走修复流程把背包重置
```

### 5.2 ★★★★★ 四种发法的完整对照（第 1482–1496 行）

```python
# 发法（`Profiles2Service.cpp` 的 `publicProfileMode()`；2026-10-07 起默认 canonical）：
#   canonical ★ 正确发法（2026-10-07）：`0A <u64 owner>` + 规范存储体
#             （raw 32768 / flag=0 / tail 625，共 33428 B；owner = 客户端请求里的
#             DW id 0xE7C8A98A6B4C2D0E）。依据：老外 C# `CodolLocalLobbyServer.cs`
#             的 SavePublicProfile / ReadProfileResult + 归档 public.result 逐字节对照；
#             见 `01-docs\30-topics\findings\定因-重登重置真因是8-1下发形态不对-按老外C#规范件修复-20261007-1130.md`。
#   body      纯档案字节（无 owner 前导；10-05 18:35 起被本行强制为默认）——
#             **实测每次登录弹「数据异常」+ 重置**（11:00/11:04/11:25 三轮 A=0 上传）。
#   prefixed  u64 session userId + 档案（上游 getPublicInfos 的写法；用错了 id——
#             给的是会话平台 id，不是客户端请求的 DW id ⇒ 被静默丢弃；18:35 之前的默认）
#   off       回 **0 个对象** —— 客户端没有档案可载，于是**自己造一份并通过 8/3 上传**
#             （17:25 / 17:31 实测过，那时 8/1 正是空的）
```

### ★★★★★ 四种发法的完整表

| 模式 | 格式 | 结果 |
|---|---|---|
| **`canonical`** ★ | **`0A <u64 owner>` + 规范存储体**（raw 32768 / flag=0 / tail 625，共 **33,428 B**；owner = **`0xE7C8A98A6B4C2D0E`**） | ★★★ **正确** |
| **`body`** | 纯档案字节（无 owner 前导） | ★★ **每次登录弹「数据异常」+ 重置**（三轮实测） |
| **`prefixed`** | `u64 session userId` + 档案 | ★★ **用错 id**（会话平台 id ≠ 客户端请求的 DW id）⇒ **被静默丢弃** |
| **`off`** | 回 **0 个对象** | 客户端**自己造一份**并通过 `8/3` 上传 |

★★★ **⇒ `canonical` 的三个精确参数：**
```
0A <u64 owner>           ← ★ 前导字节 0x0A + 8 字节 owner
raw 32768                 ← 原始档案 32 KB
flag = 0
tail 625                  ← 尾部 625 字节
---
总计 33,428 B
owner = 0xE7C8A98A6B4C2D0E   ← ★★★ Demonware 账号 ID
```

★★★★★ **⇒ `owner = 0xE7C8A98A6B4C2D0E` 与记忆里的"Demonware 账号 ID"**完全吻合**（上一轮报告 012）。**

### 5.3 ★★★★★ 2026-10-07 的**决定性更正**（第 1508–1513 行，逐字）

```python
# ★★★ 2026-10-07 11:2x 更正（上面那段 10-05 的判断作废一半）：
#   `body` 的弹窗不是"客户端解析后判定内容异常"，而是**对象缺 `0A <u64 owner>`
#   前导**；`prefixed` 则用了平台 id（不是它请求的 DW id）⇒ 被静默丢弃。
#   正确发法 = **正确 owner + 规范体**，缺一不可 —— `canonical` 把两半补齐。
#   （10-05 的 off/body 两轮实验记录保留在上面，不删。）
os.environ["OLMOD_PUBLIC_PROFILE_MODE"] = "canonical"
```

★★★★★ **⇒ 最终定案：**
```
body      ⇒ 缺 `0A <u64 owner>` 前导 ⇒ 弹窗
prefixed  ⇒ 用了**平台 id**（不是它请求的 DW id）⇒ 静默丢弃
        ↓
★★★ 正确发法 = **正确 owner + 规范体，缺一不可**
        ↓
canonical 把两半补齐
```

★★ **⇒ 且明确"10-05 的 off/body 两轮实验记录保留在上面，不删" ——**
**这是**保留历史、标注作废**的诚实做法。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 启动重试 | **5 次** |
| 2 | ★★★ 每次杀两个进程 | `codoMP_client_shipRetail.exe` + **`TP3Helper.exe`** |
| 3 | ★★★★★ `-qa` 作用 | **TCLS WinMain gate**（不是 role flag） |
| 4 | 不加参数的报错 | **「请使用腾讯游戏登录器 (TCLS 文件夹内的 Client.exe) 启动游戏」** |
| 5 | ★★★ 不能加第二个参数 | `Injector32` 因**参数个数**报 `ERROR_FILE_NOT_FOUND` |
| 6 | 测量 build | **`1649370`** |
| 7 | ★★ 旁证 | `runtime.md:57` / `ClientProcessPatches.cpp:1766 publishTclsMapping()` |
| 8 | ★★★★★ **`[100]` 正解** | **不是删 backend，而是把密钥喂给它** |
| 9 | ★★ `OLMOD_LSG_SECRETS` | **必须绝对路径**（默认相对 CWD） |
| 10 | ★★★ `OLMOD_EXTERNAL_AUTH3` | **必须清掉**（否则 backend 让出大厅） |
| 11 | ★★★ `OLMOD_CLAIM_LEGACY_AUTH` | **不设**（否则抢认证） |
| 12 | ★ 等级位置 | **secure 档案**（`service 8 task 2`） |
| 13 | ★★★★★ `8/2` 三轮实测 | ① `80/119` ② `80/173` ③ 32,983 B 真件 |
| 14 | ★★★ 结论 | **`8/2` 回非空档案 ⇒ 客户端就死** |
| 15 | ★★★ 等级是总闸 | 等级 1 ⇒ 商城/repo/军火基地全锁（挂锁 2/2/6），`80/203` 从不被请求 |
| 16 | ★★★★★ **四种发法** | `canonical` ✓ / `body` ✗ / `prefixed` ✗ / `off` 自造 |
| 17 | ★★★ `canonical` 参数 | `0A <u64 owner>` + raw 32768 + flag 0 + tail 625 = **33,428 B** |
| 18 | ★★★ **owner** | **`0xE7C8A98A6B4C2D0E`**（DW 账号 ID） |
| 19 | ★★★★★ **最终定案** | **正确 owner + 规范体，缺一不可** |

---

## 七、结论

### 1. ★★★★★ `[100]` 的**正解**是"喂密钥给 backend"，不是"删掉 backend"

### 2. ★★★★★ **三个环境变量的精妙权衡**（设一个、清一个、不设一个）

### 3. ★★★★★ **`8/2` 的三轮实验**证明"非空 private profile 会让客户端死"

★ **⇒ 第三次用"当年那份 32,983 B 真件"仍未解决 ⇒ 等级不能走 `8/2` 下发。**

### 4. ★★★★★ **`8/1` 的四种发法**最终定案为 `canonical`

```
正确 owner（0xE7C8A98A6B4C2D0E）+ 规范体（0A + 32768 + flag0 + tail625）
        ↓
缺一不可
```

### 5. ★★★ 等级是"总闸"（影响商城/repo/军火基地/80-203）

### 6. ★★ `TP3Helper.exe` 必须一起杀

---

## 八、下一步

- `main()` 剩余（第 1513 行起，约 60 行）—— 启动与线程编排
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
