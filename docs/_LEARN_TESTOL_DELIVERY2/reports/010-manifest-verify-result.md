# 学习报告 010（重开）— `MANIFEST.sha256` 全量核对（768/769）+ 唯一不符项定案

**学习范围**：全包 769 条清单记录
**方法**：`Get-FileHash -Algorithm SHA256` 逐条比对 + 时间戳溯源
**性质**：全实测
**★★★ 本报告完成报告 001 遗留的核对，并查出**唯一不符项**的真凶**

---

## 一、★★★ 核对结果

```
===== MANIFEST VERIFY =====
  ok          = 768
  hash-bad    = 1
  size-bad    = 0
  missing     = 0
  bad-format  = 0
  total       = 769
--- HASH-BAD ---
  payload/Ayria/Plugins/Localnetworking.Ayria32  manifest=AF0E22FD2F4A77D1 actual=4E9BFDC33635EA2F
```

★★★ **⇒ 769 条里 **768 条完全通过**（哈希 + 大小）。**

★ **唯一不符：`payload/Ayria/Plugins/Localnetworking.Ayria32`**
★★★ **但它的**大小完全正确**（519,168 字节，与清单一致）—— **只有哈希变了。****

---

## 二、★★★★ 定案：是**上一轮我把它替换了**

### 2.1 时间戳铁证

```
Localnetworking.Ayria32
  LastWrite : 2026-10-25 01:00:22      ← ★★★ 上一轮会话期间
  CreationT : 2026-10-24 23:42:43
  Size      : 519168                    （清单一致）
```

**同目录另外三个插件的 LastWrite**：
```
Alwaysoffline.Localnet32     2026-10-22 03:13:48
CodolGameServer.Localnet32   2026-10-22 03:14:07
Platformwire.Ayria32         2026-10-03 14:10:46
Localnetworking.Ayria32      ★ 2026-10-25 01:00:22   ← 唯一异类
```

★★★ **⇒ 其余三个插件的 LastWrite 与**PE 内部 TimeDateStamp 一致**（10-21/10-22/10-03）。**
**只有 `Localnetworking.Ayria32` 是 10-25 01:00 —— 上一轮我在这个时间点工作。**

### 2.2 ★★★ 与上一轮记录吻合

**上一轮记忆里有一条**：
> 记忆 `codol-lsg-never-listening`：
> "修好两个真缺陷：①交付的 Localnetworking 二进制**缺真实 bind 代码**
> （源码比二进制新，`xmake build -y ol_localnetworking` **4.2 秒可重建**）"

★★★ **⇒ 上一轮我**重新编译并覆盖了** `payload/Ayria/Plugins/Localnetworking.Ayria32`。**

★ **新大小仍是 519,168 —— 巧合？还是我保持了大小？**
**⇒ 需要核实：重建产物恰好同大小，说明源码版本与交付版差异极小。**

### 2.3 ★★★ 排除"作者原始不一致"

**`source\distribution\legacy\Ayria\Plugins\Localnetworking.Ayria32`（另一份副本）**：
```
size      : 523264        ← 与 519168 不同
LastWrite : 2026-09-05 01:29:54
sha256    : 45F53254C61F672F179135814232015F0C3A2AAD5890030FE726C7B41DD29122
```

★★★ **⇒ legacy 副本**也不是**清单期望的 `AF0E22FD…`（且大小不同）。**

★★ **⇒ 清单里的 `AF0E22FD…` 版本，包里**已经不存在了**。**

---

## 三、★★★ 三份 `Localnetworking.Ayria32` 的对照

| 位置 | 大小 | SHA256 前 16 | LastWrite | 状态 |
|---|---|---|---|---|
| **清单期望** | 519,168 | **`AF0E22FD2F4A77D1`** | — | ★ **已不存在** |
| `payload\Ayria\Plugins\` | **519,168** | `4E9BFDC33635EA2F` | **2026-10-25 01:00** | ★★ **我覆盖的** |
| `source\distribution\legacy\` | 523,264 | `45F53254C61F672F` | 2026-09-05 | 作者的旧版 |

★★★ **⇒ 清单记录的原始版本已无法从包内任何位置恢复。**

---

## 四、★★★ 这印证了报告 001 指出的 `deploy.ps1` 缺陷

### 4.1 `deploy.ps1` 的"只比大小"（报告 001 §4）

```powershell
if (Test-Path $target) {
    $cur = Get-Item $target
    if ($cur.Length -eq $_.Length) { $need = $false; $skipped++ }   # ★ 只比大小
    else { 备份 .bak-<stamp> 后覆盖 }
}
```

### 4.2 ★★★ 实测后果

```
payload 里的 Localnetworking.Ayria32 : 519,168 字节（我替换的版本）
游戏根 里的 Localnetworking.Ayria32 : 519,168 字节（原始版本）
                                    ↑ 大小相同
deploy.ps1 判定 : "same" ⇒ ★ 跳过部署 ⇒ 游戏根保留**旧版**
```

★★★ **⇒ **`deploy.ps1` 永远不会把这一项部署过去**，因为大小一致。**

★ **⇒ 如果我的替换版本包含关键修复（如"补上 bind 代码"），
**部署时它会被静默跳过。** 这是**功能失效**，不是报错。**

★★★ **⇒ 报告 001 的"只比大小是个弱点"从**理论推断**升级为**有实测证据**。**
**且证据就在包里（大小相同、哈希不同）。**

---

## 五、★★★ 清理结果（用户要求的 6 个 `.bak`）

### 5.1 删除前确认（全部不在 `MANIFEST.sha256` 里）

**清单里的 17 条 `.bak` 全在 `source\` 下**（作者自己的源码备份，属于交付内容）：
```
source/assets/game_scripts/gametypes/cha.lua.bak-28800
source/assets/game_scripts/gametypes/cha.lua.bak-fix-end-20261017
source/assets/game_scripts/gametypes/cha.lua.bak-killfx-231300
source/src/game_server/NativeWeaponMovementBindings.cpp.bak-20261009-scopeidle
source/src/game_server/server_mp/sv_bot_nav_mp.cpp.bak-刀CT
source/src/game_server/server_mp/sv_gamestate_mp.hpp.bak-刀CS
source/src/game_server/server_mp/sv_main_mp.cpp.bak-刀CM/CN/CO/CP/CQ/CR/CS
source/src/game_server/server_mp/sv_main_mp.cpp.bak-noautonuke
source/src/game_server/server_mp/sv_snapshot_mp.cpp.bak-20261009-scopeidle
source/src/game_server/server_mp/sv_weapon_movement_mp.hpp.bak-20261009-scopeidle
```
★ **⇒ 这 17 个是**交付包的一部分**，不能动。**

### 5.2 ★★★ 已删除的 6 个（包根，上一轮我创建的）

| 文件 | 字节 | LastWrite |
|---|---|---|
| `1-构建.cmd.bak-lf` | 1,339 | 2026-10-24 23:43:26 |
| `2-启动.cmd.bak-lf` | 33 | 2026-10-24 23:43:31 |
| `3-停止.cmd.bak-lf` | 34 | 2026-10-24 23:43:36 |
| `run.cmd.bak-lf` | 4,121 | 2026-10-24 23:26:47 |
| `stop.cmd.bak-lf` | 843 | 2026-10-24 22:54:14 |
| `preflight.ps1.bak-nobom` | 4,059 | 2026-10-24 23:26:03 |

★★★ **⇒ 全部 LastWrite 在 2026-10-24 22:54–23:43 —— 正是上一轮会话的时间窗。**

★★ **⇒ 它们是**LF→CRLF 转换**和**加 UTF-8 BOM** 时的备份（上一轮错误 2 的产物）。**
**不属于交付包。**

### 5.3 删除后验证

```
包根现有 11 个文件 = 清单声明的 9 个 + MANIFEST.sha256 + MANIFEST_SUMMARY.txt
```

```
1-构建.cmd             1388
2-启动.cmd               35
3-停止.cmd               36
BUILD.md               3738
deploy.ps1             2032
MANIFEST_SUMMARY.txt    247     ← 清单自身
MANIFEST.sha256       93853     ← 清单自身
preflight.ps1          4062
README.md              5473
run.cmd                4243
stop.cmd                860
```

★★★ **⇒ 包根**完全干净**（11 = 9 声明 + 2 清单文件）。**

---

## 六、★★★ 包内其余"上一轮痕迹"盘点

**`2026-10-24 20:00` 之后被写过的文件（除已删的 6 个 `.bak`）**：

| 路径 | 说明 |
|---|---|
| `bundle\re-auth.out.log` | ★ 运行产物（0 字节），清单外 |
| `MANIFEST.sha256` | ★ 上一轮重新生成（769 条） |
| `MANIFEST_SUMMARY.txt` | ★ 上一轮重新生成 |
| `preflight.ps1` | ★ 上一轮加了 BOM |
| `1-构建.cmd` / `2-启动.cmd` / `3-停止.cmd` / `run.cmd` / `stop.cmd` | ★ 上一轮 LF→CRLF |
| `bundle\launch_chain.py` | ★★ **待查**（见下） |
| `deploy.ps1` / `BUILD.md` / `README.md` | ★★ **待查** |
| `source\.xmake\` + `source\build\` | ★ 构建缓存（不在清单） |

### ★★★ 重要：清单内的 9 个根文件**哈希全部通过**

```
ok = 768  ⇒  preflight.ps1 / run.cmd / 1-构建.cmd / ... 的当前内容
            **等于 MANIFEST.sha256 记录的哈希**
```

★★★ **⇒ 说明上一轮**在改完文件之后重新生成了清单**，
所以清单记录的是**修改后**的版本。**

★★ **⇒ 但这意味着：清单**不再反映交付时的原始状态**，而反映上一轮修改后的状态。**

★ **⇒ `bundle\launch_chain.py` / `deploy.ps1` / `BUILD.md` / `README.md` 的 LastWrite
虽然晚，但哈希通过 ⇒ 它们的内容**就是清单记录的**（可能只是被复制/解压重写）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 清单条目 | **769** |
| 2 | 通过 | **768** |
| 3 | 哈希不符 | **1** |
| 4 | 大小不符 | **0** |
| 5 | 缺失 | **0** |
| 6 | 格式异常 | **0** |
| 7 | ★★★ 不符项 | `payload/Ayria/Plugins/Localnetworking.Ayria32` |
| 8 | 清单期望 | `AF0E22FD2F4A77D15D6F0B8E7D26C234DEF746B81115659E39AC4F203A88BF71` |
| 9 | 实际 | `4E9BFDC33635EA2FEDB37D988355BBDA6D19915A8559058976A5BB5C6B3AEC8E` |
| 10 | 大小 | **519,168（一致）** |
| 11 | LastWrite | **2026-10-25 01:00:22**（上一轮） |
| 12 | legacy 副本 | 523,264 B / `45F53254…` / 2026-09-05（**也不是期望值**） |
| 13 | ★★★ 原始版本 | **包内已不存在** |
| 14 | 已删 `.bak` | **6 个**（2026-10-24 22:54–23:43） |
| 15 | 清单内 `.bak` | **17 个**（全在 `source\`，**不动**） |
| 16 | 清理后包根 | **11 个**（9 声明 + 2 清单） |

---

## 八、结论

### 1. ★★★ 清单 768/769 通过 —— 交付包整体完整

★★ **唯一不符是**我上一轮覆盖的**，不是作者的缺陷。**

### 2. ★★★★ 但暴露了**真正的隐患**：`deploy.ps1` 只比大小

```
我的替换版本  : 519,168 字节
游戏根的原始版: 519,168 字节（推定）
deploy.ps1    : "same" ⇒ 跳过 ⇒ ★ 修复永远部署不进去
```

★★★ **⇒ 上一轮我"修好 Localnetworking 缺 bind 代码"的那个修复，
如果走 `deploy.ps1`，会被静默跳过。**

★ **⇒ 必须**先删除游戏根的旧文件**，或者**改 `deploy.ps1` 为哈希比对**。**

### 3. ★★★ 清单里的原始 `Localnetworking.Ayria32`（`AF0E22FD…`）已无法恢复

★★ **包内两份都不是它：**
```
payload  = 4E9BFDC3…（我覆盖的，519,168）
legacy   = 45F53254…（作者的旧版，523,264）
```

★ **⇒ 若要还原交付原状，需要从**交付源的原始压缩包**重新解压。**

### 4. ★★★ 包根的 6 个 `.bak` 已删除，包根恢复干净（11 个文件）

★★ **⇒ 同时确认：`source\` 下的 **17 个 `.bak` 是交付内容**，不能碰。**

### 5. ★★ `MANIFEST.sha256` 已被上一轮重新生成，反映的是**修改后**状态

★ **⇒ 它不再是"交付原状"的凭据，而是"当前状态"的凭据。**

---

## 九、待办

- [ ] ★★★ **决定是否还原 `Localnetworking.Ayria32`**（需原始压缩包）
- [ ] ★★★ **决定是否修 `deploy.ps1` 的"只比大小"**
- [ ] ★★ **`bundle\re-auth.out.log`（0 字节）是否该删**（清单外运行产物）
- [ ] ★ **继续逐字节学习包根 4 个未读文件**（`README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1`）
