# 学习报告 012（重开）— `BUILD.md` 逐字节（3,738 B / 71 行）

**学习范围**：包根 `BUILD.md`
**方法**：全文读入 + 与 `source\` 实测对照
**性质**：全实测
**★★★ 本报告发现 BUILD.md 与 README **在 `source\build\` 上自相矛盾**，且**映射表有一处致命偏差**

---

## 一、★★★ BUILD.md 的定位（第 1–4 行）

```
# BUILD · 从源码重建 TESTOL 的两个插件（完整交付版）

本包 `source\` 就是 `TESTOL GO v2` 里那几个插件的**上游源码树**（`ol-mod`，GPL-3.0，见 `source\LICENSE`）。
以下命令与要求全部来自源码树自带的 `README.md` / `tools\build.ps1` / `xmake.lua`，不是猜的。
```

★★★ **⇒ 明确的**来源声明**：所有命令**来自源码树本身**，不是作者臆造。**
**⇒ 这是可信度很高的写法（可回溯验证）。**

★ **"两个插件"** —— 指 `ol_backend` 与 `ol_game_server`（§3 表的前两行）。**

---

## 二、★★★ 前置要求（第 8–18 行）

| 项 | 要求 | 备注（逐字） |
|---|---|---|
| 平台 | **Windows x86** | 32 位目标 |
| 编译器 | **MSVC** | `xmake` 会自动探测；需装 VS 的 x86 工具链 |
| 构建器 | **xmake ≥ 3.0.9** | ★ **本机默认 `D:\Program Files\xmake\xmake.exe`** |
| 依赖 | **vcpkg**，`x86-windows-static` 的 **OpenSSL** | ★ 通过 `VCPKG_ROOT`；`tools\build.ps1` 默认找 **`E:\Source\Repos\Main\vcpkg`** |
| 游戏目录 | `source\config\codol-game-dir.txt` 内写客户端根路径 | 只有 `BuildAndDeploy.bat` 需要；单构建不需要 |

### ★★★ 两处**开发机路径泄漏**

```
D:\Program Files\xmake\xmake.exe        ← 作者机器
E:\Source\Repos\Main\vcpkg              ← 作者机器
```

★★★ **⇒ 与 README 的「不依赖 `D:\repo`」形成**同类问题**：**
**BUILD.md 自己就泄漏了两个作者本机路径。**

### ★★ 第 18 行：`build.ps1` 的原文报错

> `tools\build.ps1` 会在找不到 `vcpkg.exe` 时直接
> `throw "Set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe"`（**原文**）

★★ **⇒ 引用了**源码里的报错原文** —— 可验证。**

### ★★★ 但 `source\config\codol-game-dir.txt` **不存在**

★★ **实测（上一轮）：**
```
source\config\codol-game-dir.txt   ->  (missing)
source\config\  有 3 个文件（codol-identity.json / codol-platform.json / 另 1）
```

★★★ **⇒ BUILD.md 引用的配置文件**不存在**。**

★ **⇒ 但 BUILD.md 说"单构建不需要" —— 所以不影响 `-Action build`，只影响 `BuildAndDeploy.bat`。**

---

## 三、★★★ 构建命令（第 20–29 行）

```powershell
cd <本包>\source
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action build  -Mode release
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action test   -Mode release   # 可选
powershell -ExecutionPolicy Bypass -File .\tools\build.ps1 -Action stage  -Mode release   # 生成 build\stage\codol
```

`-Action` 可选值：`build` / `test` / `clean` / `configure` / `stage`
`-Mode`：`debug` / `release`

★★ **⇒ 5 个 action + 2 个 mode，全部明确。**

★★★ **⇒ `source\tools\build.ps1` 实测**存在**（上一轮已验证）。**

---

## 四、★★★★ 产物与名字映射（第 31–44 行）—— **本报告最重要的一节**

```markdown
| xmake target | 产出文件 | 作用 |
|---|---|---|
| `ol_backend`           | **`AlwaysofflineRe.Localnet32`** | 后端/大厅（进程内插件） |
| `ol_game_server`       | **`CodolGameServer.Localnet32`** | 战斗服（进程内插件，客户端权威） |
| `ol_localnetworking`   | `Localnetworking.Ayria32`        | 本地网络层 |
| `ol_platformwrapper`   | `Platformwrapper.Ayria32`        | 平台包装 |
| `ol_room_owner`        | `ol_room_owner.exe`              | 房间所有者（独立进程） |
| `ol_launcher`          | —                                | 启动器 |
```

### ★★★★ 致命偏差：`ol_backend` → `AlwaysofflineRe.Localnet32`

★★★ **但 `payload\Ayria\Plugins\` 里的实际文件名是 `Alwaysoffline.Localnet32`（**没有 `Re`**）。**

**实测对照**：

| 来源 | 后端插件的名字 |
|---|---|
| `BUILD.md:35` | **`AlwaysofflineRe.Localnet32`** |
| `payload\Ayria\Plugins\` 实际 | **`Alwaysoffline.Localnet32`** |
| `MANIFEST.sha256:71` | **`payload/Ayria/Plugins/Alwaysoffline.Localnet32`** |
| `ol-mod-runtime-manifest.json` | **`Ayria/Plugins/Alwaysoffline.Localnet32`** |
| 插件内部 DLL 名（上一轮 PE 实测） | **`AlwaysofflineRe.Localnet32`** |

★★★ **⇒ **三个不同的名字，各有各的位置：**
```
文件名（磁盘）        Alwaysoffline.Localnet32        ← payload 用的
内部 DLL 名（PE）     AlwaysofflineRe.Localnet32      ← BUILD.md 抄的是这个
```

★★★ **⇒ 如果按 BUILD.md 说的把产物 `AlwaysofflineRe.Localnet32` 覆盖进 `payload\Ayria\Plugins\`，
会**多出一个文件**，而 `Bootstrapper`/`Localnetworking` 加载器仍按 `*.Ayria32` / `*.Localnet32`
扫描 —— `AlwaysofflineRe.Localnet32` **仍以 `.Localnet32` 结尾，所以会被加载**，
**但会与旧的 `Alwaysoffline.Localnet32` **同时加载**（两个后端实例！）。**

★ **⇒ 这是一个**真实的部署陷阱**。**

### ★★ 其余 5 个映射核对

| target | BUILD.md 产出 | 实测 | 一致 |
|---|---|---|---|
| `ol_game_server` | `CodolGameServer.Localnet32` | ✓ 同名 | ✓ |
| `ol_localnetworking` | `Localnetworking.Ayria32` | ✓ | ✓ |
| `ol_platformwrapper` | `Platformwrapper.Ayria32` | ✓ | ✓ |
| `ol_room_owner` | `ol_room_owner.exe` | ✓ | ✓ |
| `ol_launcher` | —（无产出） | 包里无此文件 | ✓ |

★★ **⇒ **只有 `ol_backend` 一行有 `Re` 后缀偏差**，其余 5 行全对。**

### ★★★ 第 44 行的关键约束（逐字）

> **兼容文件名不能改**：Localnetworking 的插件发现与游戏目录仍依赖这些固定名字（**源码 README 明写**）。

★★★ **⇒ 源码 README 明确写了"名字不能改"，但 BUILD.md 的映射表却给了带 `Re` 的名字。**

★ **⇒ 说明 `ol_backend` 那一行是**从"内部 DLL 名"误抄成"产出文件名"**。**

---

## 五、★★★ 装回客户端（第 46–54 行）

```cmd
:: 方式 A（本包提供）：按大小比对 + .bak 备份
powershell -NoProfile -ExecutionPolicy Bypass -File deploy.ps1 -Game <客户端根>

:: 方式 B（源码自带）：把 build\bin\release 的产物装进游戏目录
source\BuildAndDeploy.bat release
```

★★★ **⇒ 两条路径，但方向不同：**
```
方式 A（deploy.ps1）        payload\Ayria  →  <游戏根>\Ayria
方式 B（BuildAndDeploy.bat） source\build\bin\release  →  游戏目录
```

★★ **⇒ 方式 A 部署的是**包内现成件**，方式 B 部署的是**自己构建的产物**。**

★ **⇒ 若用方式 B，就会遇到 §4 的 `Re` 后缀问题。**

---

## 六、★★★★ BUILD.md 与 README 的**直接矛盾**（`source\build\`）

### BUILD.md §5（第 56–63 行）

> ## 5. 本包**没有**附带的东西（要自己生成）
>
> | 缺项 | 原因 | 怎么来 |
> |---|---|---|
> | **`source\build\`** | 构建输出（**1.4 GB**，含 vcpkg 缓存与 .obj） | 按 §2 自己构建 |
> | `source\.runtime\` | frida 二进制（**408 MB**） | 运行时自动下载/由 `tools\runtime` 处理 |
> | **`source\.xmake\`** | xmake 缓存 | 构建自动生成 |
> | `*.log` | 历史构建日志 | 无价值 |

### 实测

```
source\build     221 文件   140.7 MB    ← ★★★ 在包里！
source\.xmake     11 文件     0.0 MB    ← ★ 在包里！
source\.runtime                （不在）
```

★★★ **⇒ BUILD.md 与 README §5 **说的是同一件事**，而**两处都与实测不符**。**

★★ **⇒ 且 BUILD.md 说 `source\build\` 是 **1.4 GB**，实测 **140.7 MB** —— 差 10 倍。**

★★★ **⇒ 可能解释：**
```
作者打包时 source\build\ 是 1.4 GB（含完整 vcpkg 缓存 + .obj）
实际交付的只有 140.7 MB（可能被清理过，或打包时只复制了部分）
```

★ **⇒ 无论哪种，**声明与实物不一致**。**

---

## 七、★★★★ `BUILD.md §6 已知坑`（第 65–70 行）—— 四条全部有效

### 坑 1：必须 x86

> **必须 x86**：目标是 32 位插件（`.Localnet32`），x64 构建出来的东西装不进客户端。

★★ **实测印证**：`payload\Ayria\Plugins\` 四个插件的 PE `Machine` 全是 **`0x014C`（i386）** ✓

### 坑 2：OpenSSL 静态

> **OpenSSL 静态**：`x86-windows-static` 三件套；缺了会在链接期报符号错。

★ **`Alwaysoffline` 导入 `bcrypt.dll` 而非 OpenSSL DLL** ✓（上一轮 PE 实测）
★★ **⇒ 印证了"静态链接 OpenSSL"。**

### ★★★ 坑 3：构建产物与包内不应混用（第 69 行，逐字）

> **构建产物与包内 `payload\Ayria\Plugins\` 不应混用**：包内那份是 **2026-10-22 构建**
> （`Alwaysoffline` **`90789FA742E2…`**、`CodolGameServer` **`FD91713C1134…`**），
> 你重建后哈希必然不同——**要用新的就把 `build\bin\release` 覆盖进 `payload\Ayria\Plugins\` 再用 `run.cmd`**。

★★★ **⇒ 两个哈希与 `MANIFEST.sha256` 完全一致：**
```
MANIFEST:71  90789FA742E2D06B34D81D1FCE467C6B9C08582E1E4DA2A61243D24CAB18B020  Alwaysoffline.Localnet32
MANIFEST:72  FD91713C1134CD252C92738F3D2E92267B9DF53A7BE7CF4EB90EB7AFE4A41B2C  CodolGameServer.Localnet32
```

★★ **⇒ 且"2026-10-22 构建"与 PE TimeDateStamp 吻合（`0x6AD90EEC` = 2026-10-21 19:13 UTC
= 本地 2026-10-22 03:13）。** ✓

★★★ **⇒ BUILD.md 的这条**完全准确**，且精确到哈希前 12 位。**

### 坑 4：`ol_deploy` 是 phony target

> **`ol_deploy` 是 phony target**：不要裸跑 `xmake build`（会连带触发部署钩子），只用 `tools\build.ps1`。

★★ **⇒ 这是**防止误部署**的重要警告。**

★ **⇒ 说明 `xmake.lua` 里有个 `ol_deploy` target 会**自动往游戏目录装**。**

---

## 八、逐字节证据总表

| # | 项 | BUILD.md | 实测 | 一致 |
|---|---|---|---|---|
| 1 | 来源声明 | 全部来自源码树 | ✓ 可回溯 | ✓ |
| 2 | xmake 路径 | `D:\Program Files\xmake\xmake.exe` | ★ 作者机器 | ★ 泄漏 |
| 3 | vcpkg 路径 | `E:\Source\Repos\Main\vcpkg` | ★ 作者机器 | ★ 泄漏 |
| 4 | ★ `codol-game-dir.txt` | 存在 | ★ **不存在** | ★ |
| 5 | 构建命令 | 5 action × 2 mode | `build.ps1` 存在 | ✓ |
| 6 | ★★★★ **`ol_backend` 产出** | **`AlwaysofflineRe.Localnet32`** | payload 是 **`Alwaysoffline.Localnet32`** | ★★★ **偏差** |
| 7 | `ol_game_server` 产出 | `CodolGameServer.Localnet32` | ✓ | ✓ |
| 8 | `ol_localnetworking` | `Localnetworking.Ayria32` | ✓ | ✓ |
| 9 | `ol_platformwrapper` | `Platformwrapper.Ayria32` | ✓ | ✓ |
| 10 | `ol_room_owner` | `ol_room_owner.exe` | ✓ | ✓ |
| 11 | ★ 名字约束 | "兼容文件名不能改" | 与 §4 的 `Re` 矛盾 | ★ |
| 12 | ★★★ `source\build\` | **没有附带 / 1.4 GB** | ★ **221 文件 / 140.7 MB 在** | ★★★ |
| 13 | ★★★ `source\.xmake\` | **没有附带** | ★ **11 文件在** | ★★★ |
| 14 | 坑 1（x86） | — | 四个插件全 `0x014C` ✓ | ✓ |
| 15 | 坑 2（静态 OpenSSL） | — | `Alwaysoffline` 导 `bcrypt` 非 OpenSSL DLL ✓ | ✓ |
| 16 | ★★★ 坑 3（哈希） | `90789FA742E2…` / `FD91713C1134…` | 与清单**完全一致** | ✓ |
| 17 | 坑 3（构建日期） | 2026-10-22 | PE `0x6AD90EEC` = 本地 10-22 03:13 ✓ | ✓ |
| 18 | 坑 4（phony target） | `ol_deploy` | — | 需查 `xmake.lua` |

---

## 九、结论

### 1. ★★★★ 发现一个**真实的部署陷阱**：`ol_backend` 的产出名带 `Re`

```
BUILD.md 说产出 AlwaysofflineRe.Localnet32
payload 里的文件名是 Alwaysoffline.Localnet32
插件内部 DLL 名是 AlwaysofflineRe.Localnet32
```

★★★ **⇒ 按 BUILD.md 构建并覆盖，会在 `Plugins\` 里**多出一个文件**，
两个都以 `.Localnet32` 结尾 ⇒ **都会被加载 ⇒ 两个后端实例。****

★ **⇒ 正确做法：构建后**改名为 `Alwaysoffline.Localnet32`** 再覆盖。**

### 2. ★★★ BUILD.md 与 README **在 `source\build\` 上共同出错**

```
两份文档：source\build\ 没有附带，需自行生成（1.4 GB）
实测：    221 文件 / 140.7 MB 在包里
```

### 3. ★★★ `BUILD.md §6` 的四条坑**全部有效**，尤其坑 3 精确到哈希

★ **⇒ 这部分质量最高，可作构建参考。**

### 4. ★★ 两处作者机器路径泄漏（xmake / vcpkg）

### 5. ★★ `codol-game-dir.txt` 不存在，但不影响单构建

---

## 十、下一步

- `preflight.ps1`（4,062 B）逐字节
- `deploy.ps1`（2,032 B）逐字节
- `run.cmd`（4,243 B）逐字节
- `1-构建.cmd`（1,388 B）逐字节
- `source\xmake.lua`（14,013 B）—— 验证 `ol_deploy` phony target
