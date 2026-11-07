# 学习报告 011（重开）— `README.md` 逐字节（5,473 B / 94 行）

**学习范围**：包根 `README.md`
**方法**：全文读入 + 与实测清单逐条对照
**性质**：全实测
**★★★ 本报告把 README 的**每一条断言**与实测核对，发现 6 处不符**

---

## 一、★★★ README 的定位（第 1–4 行）

```
# TESTOL 完整交付版（源码 + 可直接运行件）

**更新**：2026-10-24　**性质**：**完整交付**——包含**上游源码树**（可自行构建）
+ **现成运行件**（双击即跑）+ 构建/部署/校验全套文档。
不是"只有编译产物"的成品包；`TESTOL GO v2` 是本包去掉 `source\` 的轻量版。
```

★★ **日期 `2026-10-24`** —— 与 `MANIFEST.sha256` 的打包时间一致。**

★★★ **⇒ 明确的三个层级关系：**
```
TESTOL 完整交付版  =  source\ + payload\ + bundle\ + 根脚本
TESTOL GO v2      =  本包 − source\
TESTOL-游戏根目录版 =  更早，且"依赖 D:\repo"
```

---

## 二、★★★ 目录结构声明（第 10–24 行，逐条核对）

| README 声明 | 实测 | 一致？ |
|---|---|---|
| `README.md` | 5,473 B | ✓ |
| `BUILD.md` | 3,738 B | ✓ |
| `1-构建.cmd` | 1,388 B | ✓ |
| `2-启动.cmd` | 35 B | ✓ |
| `3-停止.cmd` | 36 B | ✓ |
| `deploy.ps1` | 2,032 B | ✓ |
| `preflight.ps1` | 4,062 B | ✓ |
| `run.cmd` / `stop.cmd` | 4,243 / 860 | ✓ |
| `MANIFEST.sha256` | 93,853 B | ✓ |
| `source\` | **695 文件 / 44.5 MB** | ★★ **不符**（见 §六） |
| `bundle\` | python 链路 + 证书 | ✓ |
| `payload\Ayria\` | Ayria 运行时 + 4 插件 + lua/资产/配置 | ✓ |

★★★ **⇒ 根目录 9 个文件全部存在且字节一致。**

### ★★ 但 README **没提** `MANIFEST_SUMMARY.txt`

★★ **实测包根有 `MANIFEST_SUMMARY.txt`（247 B），README 的结构图里没有它。**

★ **⇒ 它是**打包脚本的副产物**，未写入 README。**

---

## 三、★★★ `source\` 的组成声明（第 26–29 行，逐条核对）

> `src\backend`（后端）、`src\game_server`（战斗服，**196 文件 / 14.2 MB**）、
> `src\localnetworking`、`src\platformwrapper`、`src\shared`、
> `tests\`、`tools\`（含 `build.ps1` / 部署脚本 / 逆向工具）、
> `assets\`（game_scripts lua 与 backend 资产）、`distribution\`、
> `.agents\`（开发管线与状态文档）、`docs\`（devlog 与参考资料）、
> `xmake.lua` + `vcpkg.json` + `LICENSE`

### 实测核对（上一轮的数据）

| 目录 | 实测 |
|---|---|
| `src\backend` | **65 文件 / 0.6 MB** |
| `src\game_server` | **196 文件 / 14.2 MB** ✓ ★ 完全吻合 |
| `src\localnetworking` | 6 文件 / 0.1 MB |
| `src\platformwrapper` | 7 文件 / 0.0 MB |
| `src\shared` | 10 文件 / 0.1 MB |
| `src\client_bridge` | ★ **7 目录里 README 未提的第 6 个 src 子目录**（2 文件） |

★★★ **⇒ `src\game_server` 的「196 文件 / 14.2 MB」精确正确 —— 说明 README 是实测写的。**

★ **但 README 漏了 `src\client_bridge\`。**

---

## 四、★★★ 三条用法（第 33–37 行）

| 场景 | 动作 |
|---|---|
| **直接跑** | 双击 `2-启动.cmd`（首次自动 `preflight` + `deploy`） |
| **改代码后重建** | `1-构建.cmd` → 把 `source\build\bin\release\` 覆盖进 `payload\Ayria\Plugins\` → `2-启动.cmd` |
| **只要源码** | 取 `source\`，`BUILD.md` 有全部前置 |

★★★ **⇒ 第二条揭示了**唯一的构建→部署路径**：**
```
1-构建.cmd  →  source\build\bin\release\  →  手工覆盖到 payload\Ayria\Plugins\  →  2-启动.cmd
```

★★ **⇒ 注意：**手工覆盖**，不是自动的。**
**这与 `deploy.ps1`（把 payload 部署到游戏根）是两个不同方向的复制。**

---

## 五、★★★★ 运行链（第 46–56 行）—— README 的核心

```
2-启动.cmd → run.cmd
  ├─ preflight.ps1   检查 hosts 五条 / dwauth.ini(3074) / stun.ini(3 个 stunN)
  │                  / cacert.pem(319,581 B) / IIPS\cacert 不存在
  ├─ deploy.ps1      payload\Ayria → <游戏根>\Ayria（大小相同跳过，不同则 .bak-<时间戳> 备份后覆盖）
  └─ python bundle\launch_chain.py --no-dedicated
        ├─ ol_room_owner.exe（28970）
        ├─ fake_auth_tls.py（127.0.0.1:3074）
        ├─ stun_local.py（UDP 3074/3478/19302）
        └─ client ← Ayria\Injector32.exe，由 nt10.py 拉起（读内存出 secrets.txt）
  战斗服 ＝ <游戏根>\Ayria\Plugins\CodolGameServer.Localnet32（进程内）
  后端  ＝ <游戏根>\Ayria\Plugins\Alwaysoffline.Localnet32（进程内）
```

### ★★★ 五条关键信息

| # | 信息 | 与实测对照 |
|---|---|---|
| 1 | `cacert.pem` **319,581 B** | ★ 精确到字节（`preflight.ps1:81` 用 `> 100000` 宽松阈值） |
| 2 | **hosts 五条** | ✓ 与 `preflight.ps1:18-24` 一致 |
| 3 | `dwauth.ini(3074)` | ✓ |
| 4 | `stun.ini(3 个 stunN)` | ✓ |
| 5 | `IIPS\cacert 不存在` | ✓ |

### ★★★★ 第 52 行是最关键的一条

```
└─ client ← Ayria\Injector32.exe，由 nt10.py 拉起（读内存出 secrets.txt）
```

★★★ **⇒ README **明确声称**：客户端通过 `Injector32.exe` 拉起。**

★★★ **但这与 `nt10.py:1373` 的实际逻辑**矛盾**（上一轮报告 009 的发现）：**

```python
_inject = (os.environ.get("NT10_INJECT") == "1") or os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "inject_ayria.on"))
```

★★ **而包里**既没有** `inject_ayria.on`，`run.cmd` / `launch_chain.py` 也**都不设** `NT10_INJECT`。**

★★★ **⇒ 按字面执行，`_inject = False` ⇒ 走 `subprocess.Popen([client.exe])` ⇒ **不经 Injector32**。**

★ **⇒ README 的这一条与代码不一致。**（上一轮已列为报告 009 的核心矛盾）

### ★★ 第 56 行：固定 `--no-dedicated`

> **不含也不启动独立专服**（`codol_dedrun` / `third_party/sh1x`）——本包固定 `--no-dedicated`。

★★ **⇒ 与 `run.cmd:106` 的硬编码 `--no-dedicated` 一致 ✓**

★ **但这与 README 第 53–54 行"战斗服进程内"形成**需要澄清的关系**：**
```
--no-dedicated  ⇒  role = client
role = client   ⇒  ★ 按 game_server.md:197「不运行 gameplay server」
```
★★★ **⇒ 上一轮报告 016 已指出这个矛盾。**

---

## 六、★★★★ `README §5 合规边界`（第 58–70 行）—— 逐条核对

| # | 声明不含 | 实测 | 一致？ |
|---|---|---|---|
| 1 | 客户端本体、`.ff/.ifs/.iwd/.d3dbsp` | `source\` 内 **0 个** | ✓ |
| 1b | `.exe/.dll` **仅 2 个** | ★ **不符**（见下） | ★★ |
| 2 | `ACE-DRV32.dll`（真身/桩） | 未在包内 | ✓ |
| 3 | 独立专服（sh1x / `codol_dedrun`） | ✓ | ✓ |
| 4 | 玩家存档 / `Keystreams` / `Cloud\iotd-*` / `Launch_OLMod.bat` | `payload\` 内 **0 个** | ✓（报告 005 已验） |
| 5 | 腾讯/游戏密钥 | 包内 3 个证书文件 | ★ **实为 5 个**（见下） |
| 6 | `source\build\` / `.runtime\` / `.xmake\` / `*.log` | ★ **`build\` 和 `.xmake\` 实际在** | ★★★ |

### ★★ 不符 1：`.exe/.dll` 数量

> 已实测：`source\` 内 **0 个**（`.exe/.dll` **仅 2 个**，且是
> `distribution\legacy\Ayria\{Injector32.exe, Bootstrapper32.dll}` 这把 Ayria 加载器）

★★ **但 Glob 实测 `source\distribution\legacy\Ayria\` 有 **4 个**文件：**
```
Bootstrapper32.dll
Injector32.exe
Plugins\Localnetworking.Ayria32      ← ★ 无 .exe/.dll 后缀，所以不计
Plugins\Platformwrapper.Ayria32      ← ★ 同上
```

★★★ **⇒ README 说"仅 2 个"是**按扩展名**算的（`.Ayria32` 不算 `.dll`）。**
**字面正确，但 `Plugins\` 里那 2 个也是**加载器组件**。**

### ★★★ 不符 2：证书文件数量

> 包内 **3 个**证书文件全在 `bundle\`：`_ca.pem` / `_leaf2.key` / `_leaf2_chain.pem`

★★★ **但实测 `bundle\` 有 **5 个**证书相关文件：**
```
_ca.cer          791      ← ★ README 未提
_ca.pem        1,127      ← README 提到
_leaf2.cer       858      ← ★ README 未提
_leaf2.key     1,675      ← README 提到
_leaf2_chain.pem 2,343    ← README 提到
```

★★★ **⇒ README 漏了 `_ca.cer` 和 `_leaf2.cer`（两个 DER 二进制版）。**

★ **⇒ 实际是 **3 个 PEM + 2 个 DER = 5 个文件，描述同一套 2 张证书。**
**`fake_auth_tls.py:126` 用 `_leaf2.cer`（DER），所以它**是必需的**。**

### ★★★ 不符 3：`source\build\` 和 `source\.xmake\` **实际在包里**

> | `source\build\`、`source\.runtime\`、`source\.xmake\`、`*.log` | 构建/运行缓存，需自行生成 |

★★★ **实测（上一轮）：**
```
source\build    221 文件  140.7 MB   ← ★★★ 在包里
source\.xmake    11 文件     0.0 MB   ← ★ 在包里
source\.runtime              （确实不在）
```

★★★ **⇒ 三项里**两项在**，README 说"需自行生成"是**错的**。**

★ **⇒ 且这 232 个文件**不在 `MANIFEST.sha256` 里**（报告 001 的 241 个差异的大头）。**

---

## 七、★★★ `README §6 自检`（第 72–84 行）

```cmd
:: 前置检查（不写任何东西）
powershell -NoProfile -ExecutionPolicy Bypass -File preflight.ps1 -Game <客户端根>

:: 部署 dry-run
powershell -NoProfile -ExecutionPolicy Bypass -File deploy.ps1 -Game <客户端根> -DryRun

:: 文件完整性
findstr /I "CodolGameServer.Localnet32" MANIFEST.sha256
certutil -hashfile payload\Ayria\Plugins\CodolGameServer.Localnet32 SHA256
```

### ★★ 逐条评估

| 命令 | 评价 |
|---|---|
| `preflight.ps1 -Game <客户端根>` | ★ **需要 BOM 才能在 PS 5.1 下跑**（上一轮已修） |
| `deploy.ps1 -Game <客户端根> -DryRun` | ✓ 正确（`deploy.ps1:4` 有 `[switch]$DryRun`） |
| `findstr /I "...Localnet32" MANIFEST.sha256` | ✓ |
| `certutil -hashfile ... SHA256` | ★ **输出大写，与清单格式一致** ✓ |

★★★ **⇒ 自检命令**全部有效**（但 `preflight.ps1` 依赖 BOM）。**

---

## 八、★★★ `README §7 与两个轻量版的区别`（第 86–93 行）

| | 本包 | `TESTOL GO v2` | `TESTOL-游戏根目录版` |
|---|---|---|---|
| 源码 | **有**（44.5 MB） | 无 | 无 |
| 可自建 | **能** | 不能 | 不能 |
| 依赖 `D:\repo` | 不依赖 | 不依赖 | ★ **依赖** |
| 体积 | 约 **60 MB**（zip 约 20 MB） | 6 MB zip | 小 |

★★★ **⇒ 三条重要信息：**
1. **本包约 60 MB** —— 但**实测（含 `source\build\`）是 185.2 MB**
2. **不依赖 `D:\repo`** —— 但 `launch_chain.py:69` 的默认值**就是** `D:\repo\03-live\client\TESTOL`
3. **早期版"依赖 `D:\repo`"** —— 说明作者曾把开发机路径写死

★★★ **⇒ 第 2 条是**严重的**：README 说"不依赖 D:\repo"，
但 `launch_chain.py:69` 的默认 `GAME` 就是它。**
**只有 `run.cmd:99` 设了 `OLMOD_GAME_ROOT` 才绕开。**

★ **⇒ 这与上一轮报告 016 的发现一致（缺口 4 在双击路径被绕过，单独跑会崩）。**

---

## 九、逐字节证据总表

| # | 项 | README 声明 | 实测 | 一致 |
|---|---|---|---|---|
| 1 | 更新日期 | 2026-10-24 | 清单时间一致 | ✓ |
| 2 | 根 9 文件 | 全列 | 全部存在且字节一致 | ✓ |
| 3 | `MANIFEST_SUMMARY.txt` | ★ **未提** | 247 B 存在 | ★ |
| 4 | `src\game_server` | **196 文件 / 14.2 MB** | 完全吻合 | ✓ |
| 5 | `src\client_bridge` | ★ **未提** | 2 文件存在 | ★ |
| 6 | `cacert.pem` | **319,581 B** | 精确 | ✓ |
| 7 | hosts | **五条** | 5 条 | ✓ |
| 8 | ★★★ 客户端启动方式 | **经 `Injector32.exe`** | ★ **`nt10.py` 默认不经** | ★★★ |
| 9 | `.exe/.dll` | 仅 **2 个** | 2 个（按扩展名） | ✓（字面） |
| 10 | ★★★ 证书文件 | **3 个** | ★ **5 个**（漏 `_ca.cer`/`_leaf2.cer`） | ★★★ |
| 11 | ★★★ `source\build\` | **需自行生成** | ★ **221 文件 / 140.7 MB 在包里** | ★★★ |
| 12 | ★★★ `source\.xmake\` | **需自行生成** | ★ **11 文件在包里** | ★★★ |
| 13 | 体积 | **约 60 MB** | **185.2 MB**（含 build） | ★★ |
| 14 | ★★★ 依赖 `D:\repo` | **不依赖** | ★ **`launch_chain.py:69` 默认就是它** | ★★★ |
| 15 | 固定 `--no-dedicated` | ✓ | `run.cmd:106` 硬编码 | ✓ |

---

## 十、结论

### 1. ★★★ README 的**主干是准确的**（路径、字节数、命令、依赖链都对）

★★ **尤其 `src\game_server` 的「196 文件 / 14.2 MB」和 `cacert.pem` 的「319,581 B」精确到字节，
说明它是**对着实测写的**，不是凭记忆。**

### 2. ★★★ 但有 **6 处不符**，分三类

**A 类（漏写，无害）**
```
① MANIFEST_SUMMARY.txt 未提
② src\client_bridge 未提
③ 证书 3 个 → 实为 5 个（漏 _ca.cer / _leaf2.cer）
```

**B 类（过时，有影响）**
```
④ source\build\ / .xmake\ 说"需自行生成"，实际在包里（140.7 MB）
⑤ 体积说 60 MB，实际 185.2 MB
```

**C 类（★★★ 与代码矛盾，最重要）**
```
⑥ 说"client ← Injector32.exe，由 nt10.py 拉起"
   而 nt10.py:1373 默认 _inject=False ⇒ 直起 exe
⑦ 说"不依赖 D:\repo"
   而 launch_chain.py:69 的默认 GAME 就是 D:\repo\03-live\client\TESTOL
```

### 3. ★★★ 第 ⑦ 条与第 ⑥ 条是**同一类问题的两面**

★★★ **⇒ README 描述的是**作者开发环境**下的运行方式，
而**交付包在别人机器上按字面跑不通**。**

★ **⇒ 这正是"完整交付"与"能在别处跑"的差距。**

### 4. ★★ `README §5` 的合规声明**基本可信**（游戏本体/存档/密钥确实排除了）

★ **唯一不准的是 `source\build\`（把构建缓存当成了交付物）。**

---

## 十一、下一步

- `BUILD.md`（3,738 B）逐字节
- `preflight.ps1`（4,062 B）逐字节
- `deploy.ps1`（2,032 B）逐字节
- `run.cmd`（4,243 B）逐字节
- `1-构建.cmd`（1,388 B）逐字节
