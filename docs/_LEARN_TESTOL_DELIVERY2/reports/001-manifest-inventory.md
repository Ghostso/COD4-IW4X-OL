# 学习报告 001（重开）— `MANIFEST` 全量清单：交付包的权威字节账

**学习目标**：`F:\桌面\ol\TESTOL 完整交付版`（**整个交付包**，不是 ol-mod、不是客户端）
**方法**：读包自带的 `MANIFEST.sha256` + `MANIFEST_SUMMARY.txt`（这是包对自己的字节级声明）
**性质**：全实测
**★ 本报告纠正了上一次学习的范围漂移**

---

## 一、★★★ 先说范围纠正（为什么重开）

上一次学习我从 `bundle\`/`payload\` 起步（对），但**从中途滑进了客户端 EXE 反汇编和运行时内存转储**
（报告 033–054 全部是 `mem_000.bin` 与 `codoMP_client_shipRetail.exe`）。

**那不是交付包** —— 那是**你机器上的游戏客户端**。

本次重开，**只学交付包内的 769 个文件**。

---

## 二、`MANIFEST_SUMMARY.txt` 逐字节（247 字节）

```
TESTOL full delivery — manifest summary
files: 769
total: 59.9 MB

source                   files=695   44.5 MB
payload                  files=55    15.2 MB
bundle                   files=10    0.2 MB
(root)                   files=9     0.0 MB
```

### ★★ 逐项核对

| 区域 | 声明文件数 | 声明体积 | 实测 | 一致？ |
|---|---|---|---|---|
| `source\` | 695 | 44.5 MB | 见 §4 | ★ 不符 |
| `payload\` | 55 | 15.2 MB | 55 | ✓ |
| `bundle\` | 10 | 0.2 MB | **11** | ★ 多 1 个 |
| `(root)` | 9 | 0.0 MB | **15** | ★ 多 6 个 |
| **合计** | **769** | **59.9 MB** | **1010** | ★★ **多 241** |

★★★ **⇒ 包里有 **241 个文件不在清单里**（占 24%）。**

---

## 三、`MANIFEST.sha256` 的**格式规范**（逐字节）

```
<64 位十六进制 SHA256><两个空格><相对路径，正斜杠分隔><两个空格><字节数><LF>
```

**实测样例（第 1 行，逐字节）**：
```
FBCB12AD967C41B7A74ADEE095719526EEB9CE44FA97FAF360F2524796B127BF  1-构建.cmd  1388
└──────────── 64 字符大写十六进制 ────────────┘  └─ 2 空格 ─┘ └路径┘ └ 2 空格 ┘ └大小┘
```

### ★ 要点

1. **哈希用大写十六进制**（不是 `sha256sum` 的小写）
2. **路径用正斜杠 `/`**，即使包在 Windows 上（`payload/Ayria/...`）
3. **路径是相对包根**，不含 `F:\桌面\ol\TESTOL 完整交付版\` 前缀
4. **末尾是字节数**（不是 `sha256sum` 的标准格式 —— 这是定制格式）
5. **中文文件名直接以 UTF-8 出现**（`1-构建.cmd`）

★★★ **⇒ `certutil -hashfile` 的校验必须注意大小写**（README §6 给的自检命令
`certutil -hashfile payload\... SHA256` 输出**大写**，与清单一致 ✓）。

---

## 四、★★★ 全量非 source 清单（**74 个文件**，逐条实测）

### 4.1 包根（9 个，清单行 1–9）

| # | 文件 | 字节 | SHA256 前 16 |
|---|---|---|---|
| 1 | `1-构建.cmd` | 1388 | `FBCB12AD967C41B7` |
| 2 | `2-启动.cmd` | 35 | `CE0EAB59805A99F7` |
| 3 | `3-停止.cmd` | 36 | `91EFD80FE5225BFA` |
| 4 | `BUILD.md` | 3738 | `EDDB90F4A7695226` |
| 5 | `deploy.ps1` | 2032 | `677DB016997E2AB1` |
| 6 | `preflight.ps1` | 4062 | `F1FE15243D65587B` |
| 7 | `README.md` | 5473 | `64CC74E9EC880AC2` |
| 8 | `run.cmd` | 4243 | `4E2437F6A736D6F2` |
| 9 | `stop.cmd` | 860 | `79DCE72879165C29` |

### 4.2 `bundle\`（10 个，清单行 10–19）

| # | 文件 | 字节 | SHA256 前 16 |
|---|---|---|---|
| 10 | `_ca.cer` | 791 | `900D518AF5C7C03B` |
| 11 | `_ca.pem` | 1127 | `3DF4949EF0923B2F` |
| 12 | `_leaf2_chain.pem` | 2343 | `CE4B1B971BC65A1B` |
| 13 | `_leaf2.cer` | 858 | `8A949AB3DD381F39` |
| 14 | `_leaf2.key` | 1675 | `3EB7075C8A2B71A0` |
| 15 | `fake_auth_tls.py` | 17600 | `D209CB35CCC841DA` |
| 16 | `force_display_name.py` | 19288 | `26394BD5CB8C61C7` |
| 17 | `launch_chain.py` | 25009 | `0EBB846A13802190` |
| 18 | `nt10.py` | 146765 | `2FE89C877E276CC7` |
| 19 | `stun_local.py` | 7618 | `1A61A2A7BD842E1D` |

★ **清单里**没有** `_rsa.txt`** —— 与报告 011（上一轮）的发现一致，**该文件确实未交付**。

### 4.3 `payload\Ayria\`（55 个，清单行 20–74）

**顶层（5 个）**：

| # | 文件 | 字节 | SHA256 前 16 |
|---|---|---|---|
| 20 | `Bootstrapper32.dll` | 159744 | `C52F6BEB84857179` |
| 21 | `Bootstrapper64.dll` | 204288 | `74043429FF05C5BC` |
| 22 | `Injector32.exe` | 126464 | `30CC97C0C2A67ED4` |
| 23 | `ol_room_owner.exe` | 283648 | `627EF1748BDFAE44` |
| 24 | **`ol-mod-runtime-manifest.json`** | 28209 | `1BD353E87110858F` |

★★ **`ol-mod-runtime-manifest.json` 是 payload 的一部分** ——
**它记录 ol-mod 的上游来源（`"project": "ol-mod"`），是**来源标注**，不是要学的内容。**

**`Assets\Alwaysoffline\`（14 个）**：

| 文件 | 字节 |
|---|---|
| `Identity.json` | **34** |
| `1004\MarketplaceSkus.json` | **2,578,582** |
| `1004\Server\activities_v1.info` | **2** |
| `1004\Server\broadcast.info` | 23 |
| `1004\Server\configs_s.info` | 26,249 |
| `1004\Server\daily_challenge_config.info` | **0** |
| `1004\Server\market_ui.info` | 2,010 |
| `1004\Server\market-down.info` | 90 |
| `1004\Server\MOTD.info` | **0** |
| `1004\Server\mp_playlists_shipRetail_release.info` | 112,274 |
| `1004\Server\selected_playlist.txt` | **17** |
| `1004\Server\sku_tags.info` | 3,520 |
| `1004\Server\tlogconfig.info` | 154 |
| `1004\Server\whitelist_tester.info` | 93 |

**`Assets\OlMod\GameScripts\`（31 个 Lua）**：

| 目录 | 数量 | 关键 |
|---|---|---|
| `GameScripts\` | 1 | `common.lua` 2,866 |
| `GameScripts\gametypes\` | 11 | `cha/dm/coop/conf/dmz/sd/td/war/zarena/zhunt/zm` |
| `GameScripts\maps\` | 19 | ★ **`coop_training_mp_cargoship.lua` 201,269**（最大）+ 18 个 sh 后缀小文件 |

**`Assets\Platformwrapper\`（1 个）**：`Platform.json` 256

**`Plugins\`（4 个）** ★★★：

| 文件 | 字节 | SHA256 前 16 |
|---|---|---|
| `Alwaysoffline.Localnet32` | **4,189,184** | `90789FA742E2D06B` |
| `CodolGameServer.Localnet32` | **6,834,176** | `FD91713C1134CD25` |
| `Localnetworking.Ayria32` | 519,168 | `AF0E22FD2F4A77D1` |
| `Platformwrapper.Ayria32` | 543,232 | `840B22DA2A2AA7C5` |

★ **`BUILD.md:69` 给的哈希是**缩写前 12 位**：
```
Alwaysoffline  90789FA742E2…  ← 与清单一致 ✓
CodolGameServer FD91713C1134… ← 与清单一致 ✓
```

---

## 五、★★★ 三处**清单与实际的差异**（本次核心发现）

### 差异 1：`bundle\` 有 11 个文件，清单只有 10

```
实际 bundle\：11 个
清单 bundle\：10 个
多出的：re-auth.out.log  （0 字节）
```

★★ **`re-auth.out.log` 是 `launch_chain.py:289` 的**运行时输出重定向目标**：
```python
stdout=open(os.path.join(BASE, "re-auth.out.log"), "w")
```

★★★ **⇒ 这是一个**运行产物**，被打包进来了（且是 0 字节）。
**它不该在交付包里。**

★ **注意：`launch_chain.py:321` 还有 `stun_local.out.log`（`"a"` 模式）** ——
**那个**不在**包里**（运行后才会生成）。

### 差异 2：包根有 15 个文件，清单只有 9

★★★ **多出的 6 个是 `.bak` 文件**：

```
1-构建.cmd.bak-lf          1339
2-启动.cmd.bak-lf            33
3-停止.cmd.bak-lf            34
run.cmd.bak-lf             4121
stop.cmd.bak-lf             843
preflight.ps1.bak-nobom    4059
```

★★★ **⇒ 这 6 个是**我上一次学习时**创建的备份**
（LF→CRLF 转换和加 BOM 时的备份，见上一轮会话的错误 2）。

★ **它们不属于交付包，是我留下的污染。**

### 差异 3：★★★ `source\build\` 被交付了，但 README 说"没有附带"

**README.md:60-63 逐字**：
> | `source\build\` | 构建输出（1.4 GB，含 vcpkg 缓存与 .obj） | 按 §2 自己构建 |
> | `source\.runtime\` | frida 二进制（408 MB） | 运行时自动下载/由 `tools\runtime` 处理 |
> | `source\.xmake\` | xmake 缓存 | 构建自动生成 |
> | `*.log` | 历史构建日志 | 无价值 |

★ **README 说这四项**都没有附带**。**

**但实测**（上一轮的数据）：
```
source\build   221 files  140.7 MB   ← ★★★ 存在！
source\.xmake   11 files    0.0 MB   ← ★ 存在
source\.runtime            （未测到）
```

★★★ **⇒ `source\build\`（140.7 MB）实际在包里，且**不在 `MANIFEST.sha256` 里**。**

★ **`source\.runtime\`（README 说 408 MB）未在 Glob 中出现 —— 确实没带。**

---

## 六、★★★ 241 个差异文件的完整分解

```
清单 769
实际 1010
差异 241
  其中：
    source\build\        221   ★★★ README 说没有
    source\.xmake\        11   ★ README 说没有
    .bak 文件（我留的）     6
    MANIFEST.sha256        1   （自指，无法列自己）
    MANIFEST_SUMMARY.txt   1
    re-auth.out.log        1
                        ───
                        241  ✓ 完全吻合
```

★★★ **⇒ 差异**完全解释清楚**，无未解项。**

★ **⇒ `source\build\` 的 221 个文件（140.7 MB）是**唯一的大宗**，
**这与 `MANIFEST_SUMMARY.txt` 说的 `source files=695` 不符（实际 927 = 695 + 221 + 11）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `MANIFEST_SUMMARY.txt` 大小 | 247 字节 |
| 2 | 声明总文件数 | **769** |
| 3 | 实测总文件数 | **1010** |
| 4 | 声明总体积 | 59.9 MB |
| 5 | 清单格式 | `HASH(64大写)  路径  大小` |
| 6 | 清单行分隔 | **2 空格**（非制表符） |
| 7 | 路径分隔 | **正斜杠** |
| 8 | 根目录清单条目 | 9 |
| 9 | 根目录实际文件 | **15**（+6 个 .bak） |
| 10 | bundle 清单条目 | 10 |
| 11 | bundle 实际文件 | **11**（+`re-auth.out.log`） |
| 12 | payload 清单条目 | 55 |
| 13 | payload 实际文件 | 55 ✓ |
| 14 | `source\build\` | ★★★ **221 文件 / 140.7 MB，不在清单** |
| 15 | `_rsa.txt` | ★ 不在清单也**不在包** |
| 16 | `Alwaysoffline` 哈希 | `90789FA742E2D06B`（与 BUILD.md 一致） |
| 17 | `CodolGameServer` 哈希 | `FD91713C1134CD25`（与 BUILD.md 一致） |

---

## 八、结论

### 1. ★★★ 范围已锁定：交付包 = 769 个清单文件 + 241 个差异文件

★★ **要学的核心是**清单内的 769 个**（尤其根 9 + bundle 10 + payload 55 = **74 个非 source 文件**）。**

★ **`source\` 的 695 个是**上游参考**（ol-mod，GPL-3.0），只需按需查阅。**

### 2. ★★★ 三处差异已完全定案

```
① re-auth.out.log        运行产物被打包（0 字节）
② 6 个 .bak 文件          我上一次学习的污染
③ source\build\ 140.7 MB  README 说没带，实际带了
```

★★★ **⇒ ② 需要清理（是我的责任）。① ③ 是交付包自身的瑕疵。**

### 3. ★★ 清单本身是**可信的**（格式规范、哈希与 BUILD.md 自洽）

★ **`certutil -hashfile` 的校验命令（README §6）与清单格式匹配（大写）。**

### 4. ★★ `ol-mod-runtime-manifest.json` 是**来源标注**，不是学习对象

★★ **它记录 payload 各文件的上游路径（`assets/game_scripts/...`），
是为 GPL 合规与可追溯性而附的。**
**⇒ 报告 001 之后**不再单独学它**（除非要核对来源）。**

---

## 九、下一步（按清单顺序）

1. ★★★ **包根 9 个文件逐字节**（`README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1` / `run.cmd` / `stop.cmd` / 三个 `.cmd`）
2. ★★★ **`bundle\` 10 个文件逐字节**（5 个脚本 + 5 个证书）
3. ★★ **`payload\Ayria\` 55 个文件逐字节**（先小文件，后 2.5 MB 的 `MarketplaceSkus.json`）
4. ★★ **`Plugins\` 4 个插件的 PE**
5. ★ **清理我的 6 个 `.bak` 遗留**
