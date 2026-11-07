# 学习报告 015（重开）— `source\xmake.lua` 的产物名铁证

**学习范围**：`source\xmake.lua`（14,013 B）的 target 定义段
**性质**：全实测（源码级）
**★★★ 本报告用构建脚本**铁证**了 `BUILD.md` 的映射表，并解开"两个后端实例"风险**

---

## 一、★★★★ 四个插件的 `set_filename`（逐行实测）

```lua
target("ol_localnetworking")
    set_kind("shared")
    set_group("plugins")
    set_filename("LocalnetworkingRe.Ayria32")        ← ★★★ Re

target("ol_platformwrapper")
    set_kind("shared")
    set_group("plugins")
    set_filename("PlatformwrapperRe.Ayria32")        ← ★★★ Re

target("ol_backend")
    set_kind("shared")
    set_group("plugins")
    set_filename("AlwaysofflineRe.Localnet32")       ← ★★★ Re

target("ol_game_server")
    set_kind("shared")
    set_group("plugins")
    set_filename("CodolGameServer.Localnet32")       ← ★ 无 Re
```

★★★ **⇒ **四个里三个带 `Re`，只有 `CodolGameServer` 不带。****

★★★ **⇒ 这与上一轮 PE 实测的"内部 DLL 名"**完全一致**：**
```
LocalnetworkingRe.Ayria32    ✓
PlatformwrapperRe.Ayria32    ✓
AlwaysofflineRe.Localnet32   ✓
CodolGameServer.Localnet32   ✓（无 Re）
```

★★★ **⇒ 结论：`set_filename` **就是**导出表里的 DLL Name —— 它们是同一个东西。**

---

## 二、★★★★★ 铁证：`payload\` 里的文件名**与构建产物不同**

### 完整对照表

| target | `set_filename`（构建产物） | `payload\Ayria\Plugins\` 实际文件名 | 差异 |
|---|---|---|---|
| `ol_localnetworking` | `LocalnetworkingRe.Ayria32` | **`Localnetworking.Ayria32`** | ★★ **去掉 `Re`** |
| `ol_platformwrapper` | `PlatformwrapperRe.Ayria32` | **`Platformwrapper.Ayria32`** | ★★ **去掉 `Re`** |
| `ol_backend` | `AlwaysofflineRe.Localnet32` | **`Alwaysoffline.Localnet32`** | ★★ **去掉 `Re`** |
| `ol_game_server` | `CodolGameServer.Localnet32` | `CodolGameServer.Localnet32` | ✓ **相同** |

★★★ **⇒ **三个带 `Re` 的产物，在 payload 里全被**手工改名去掉了 `Re`**。****

★★★ **⇒ 这是**交付时的手工步骤**，`BUILD.md` / `1-构建.cmd` **都没有记录**。**

---

## 三、★★★★ 这解开了报告 012/014 的"两个后端实例"风险

### 3.1 加载器的扫描规则（上一轮已证）

```
Bootstrapper32.dll    扫描  *.Ayria32
Localnetworking.Ayria32 扫描  *.Localnet32
```

★★★ **⇒ 两种后缀都会匹配 `Re` 版本：**
```
LocalnetworkingRe.Ayria32   → 匹配 *.Ayria32     ⇒ Bootstrapper 会加载
PlatformwrapperRe.Ayria32   → 匹配 *.Ayria32     ⇒ Bootstrapper 会加载
AlwaysofflineRe.Localnet32  → 匹配 *.Localnet32  ⇒ Localnetworking 会加载
```

★★★ **⇒ 若把 `set_filename` 的产物直接放进 `Plugins\`，会**同时存在两个同名模块**：**
```
Localnetworking.Ayria32      （原）
LocalnetworkingRe.Ayria32    （新建）  ⇒ ★ 两个都加载
```

★ **⇒ 两个 `Localnetworking` 都装 Winsock hook ⇒ **严重冲突**。**

★★★ **⇒ 这就是为什么 payload 里的文件名必须去掉 `Re`。**

### 3.2 `1-构建.cmd:48` 的通配提示**会踩这个坑**

```cmd
echo Next: copy the fresh *.Localnet32 into payload\Ayria\Plugins, then run 2-启动.cmd
```

★★★ **⇒ `*.Localnet32` 会匹配到 `AlwaysofflineRe.Localnet32` 与 `CodolGameServer.Localnet32`，
**两个都会被复制** ⇒ `AlwaysofflineRe.Localnet32` 与旧的 `Alwaysoffline.Localnet32` **并存**。**

### ★★★ 3.3 正确的做法（`BUILD.md` 未写）

```
构建产物                              应改名为
AlwaysofflineRe.Localnet32    →     Alwaysoffline.Localnet32
LocalnetworkingRe.Ayria32     →     Localnetworking.Ayria32
PlatformwrapperRe.Ayria32     →     Platformwrapper.Ayria32
CodolGameServer.Localnet32    →     （不改）
```

★★★ **⇒ 这三条改名规则是**交付包隐含的第五个知识**，`BUILD.md` 与 `1-构建.cmd` 都没提。**

---

## 四、★★★ `ol_deploy` 是 **phony** target（验证 `BUILD.md:70`）

```lua
target("ol_deploy")
    set_kind("phony")
    add_deps("ol_localnetworking", "ol_platformwrapper", "ol_backend",
             "ol_game_server", "ol_room_owner")
```

★★★ **⇒ `set_kind("phony")` 确认 —— `BUILD.md:70` 的"`ol_deploy` 是 phony target"**完全正确**。**

★★ **⇒ 它 `add_deps` 了 **5 个** target ⇒ 裸跑 `xmake build` 会**先构建这 5 个，再执行部署钩子**。**

★ **⇒ 这正是 `BUILD.md` 警告"不要裸跑 `xmake build`"的原因。**

---

## 五、★★★ 其余 target 的配置（逐项实测）

### 5.1 `ol_localnetworking`

```lua
add_packages("mhook")
add_links("ws2_32")
```

★★★ **⇒ `mhook` 包 —— 这正是**Winsock hook 库**！**
**印证了上一轮"`Localnetworking` 装 Winsock hook"的实测。**

### 5.2 `ol_platformwrapper`

```lua
add_packages("mhook", "nlohmann_json")
add_links("user32")
```

★ **也有 `mhook`（可能用于 hook 某些 API）。**
★ **只链 `user32` —— 与上一轮 PE 实测"只导入 USER32 + KERNEL32"一致** ✓

### 5.3 `ol_backend`

```lua
add_packages("openssl", "nlohmann_json", "zlib")
add_links("bcrypt", "ws2_32")
```

★★★ **⇒ 三个包：`openssl`（TLS）+ `nlohmann_json`（JSON）+ `zlib`（压缩）。**

★★ **⇒ `zlib` 印证了报告 003 的发现：`market_ui.info` 是 **zlib 压缩**！**
**⇒ 后端自己能解压那个文件。**

★ **⇒ `bcrypt` 与上一轮 PE 实测一致（`Alwaysoffline` 导入 `bcrypt.dll`）** ✓

### 5.4 `ol_game_server`

```lua
add_shflags("/MAP", {tools = "link", force = true})
```

★★★ **⇒ 链接时生成 **`.map` 文件**（符号表）。**
**注释写："Resolve sampled release-build stall addresses without changing optimization."**

★★ **⇒ 作者用 `.map` 文件**定位 release 构建的卡顿地址**，而不改优化级别。**
**这是一个**很好的调试实践**。**

### 5.5 `ol_room_owner` / `ol_launcher`

```lua
target("ol_room_owner")
    set_kind("binary")
    set_group("servers")
    set_default(false)              ← ★ 默认不构建
    ...
    add_links("ws2_32")

target("ol_launcher")
    set_kind("binary")
    add_files("../launcher/main.cpp")   ← ★ 在 source 之外
    add_syslinks("user32", "gdi32", "iphlpapi")
```

★★★ **⇒ `ol_room_owner` 有 `set_default(false)` ⇒ **默认不构建**，需显式指定。**
**但 `ol_deploy` 的 `add_deps` 里有它 ⇒ 通过 `ol_deploy` 会构建。**

★ **⇒ `ol_launcher` 的源文件在 `../launcher/main.cpp`（`source\` 之外）⇒ **交付包里可能没有**。**

---

## 六、★★★ 测试 target（9 个）

```
ol_backend_tests
ol_game_server_tests
ol_playerdata_def_tests
ol_dedicated_control_tests
ol_lua_runtime_tests
ol_localnetworking_tests
ol_platformwrapper_tests
ol_localnetworking_fixture   （set_filename("Fixture.Localnet32")）
ol_archived_tls_probe
```

★★★ **⇒ 9 个测试 target，覆盖 6 个模块。**

★ **⇒ `ol_localnetworking_fixture` 产出 `Fixture.Localnet32` —— 又一个 `.Localnet32` 后缀！**
**若它被构建并放进 `Plugins\`，会被 `Localnetworking` 当作插件加载。**

★★ **⇒ 但 `set_default` 未设为 false，说明**默认会构建**？需查上下文。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `ol_localnetworking` | `set_filename("LocalnetworkingRe.Ayria32")` |
| 2 | `ol_platformwrapper` | `set_filename("PlatformwrapperRe.Ayria32")` |
| 3 | `ol_backend` | `set_filename("AlwaysofflineRe.Localnet32")` |
| 4 | `ol_game_server` | `set_filename("CodolGameServer.Localnet32")`（**无 Re**） |
| 5 | ★★★ payload 里的名字 | **三个去掉了 `Re`** |
| 6 | ★★★ 改名规则 | **`BUILD.md` / `1-构建.cmd` 均未记录** |
| 7 | `ol_deploy` | **`set_kind("phony")`** ✓ 确认 BUILD.md:70 |
| 8 | `ol_deploy` deps | **5 个** target |
| 9 | `Localnetworking` 包 | **`mhook`** + `ws2_32` |
| 10 | `Platformwrapper` 包 | `mhook` + `nlohmann_json` + `user32` |
| 11 | `Alwaysoffline` 包 | **`openssl` + `nlohmann_json` + `zlib`** + `bcrypt` + `ws2_32` |
| 12 | `CodolGameServer` | **`/MAP`** 链接符号表（不改优化） |
| 13 | `ol_room_owner` | `set_default(false)` |
| 14 | `ol_launcher` 源 | **`../launcher/main.cpp`**（source 外） |
| 15 | 测试 target | **9 个** |
| 16 | `ol_localnetworking_fixture` | `set_filename("Fixture.Localnet32")` |

---

## 八、结论

### 1. ★★★★★ 用 `xmake.lua` 铁证了 `BUILD.md` 的映射表，并发现**遗漏的改名步骤**

★★★ **⇒ 这是本次学习中**最有价值的一条工程知识**：**
```
构建产物 → payload 文件名，需要手工去掉 "Re"
```

★★ **⇒ 若不改名，会**同时加载两个同名模块** ⇒ Winsock hook 双装 ⇒ 严重冲突。**

### 2. ★★★ `BUILD.md:70` 的"`ol_deploy` 是 phony"**完全正确**

### 3. ★★★ `zlib` 依赖印证了 `market_ui.info` 是 zlib 压缩

### 4. ★★ `mhook` 包印证了 Winsock hook 实现方式

### 5. ★★ `/MAP` 是作者定位 release 卡顿的调试手段（不改优化）

### 6. ★★ `ol_launcher` 的源在 `source\` 之外，交付包可能不含

---

## 九、下一步

- `source\tools\build.ps1` —— 验证 `-Action` 实现与 `stage` 行为
- `source\BuildAndDeploy.bat` —— 验证"方式 B"的实际行为
- `bundle\` 五个脚本逐字节
- `bundle\` 五个证书文件逐字节
- `payload\` 四个插件 PE + 四个 loader 二进制
