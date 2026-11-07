# 学习报告 008 — 注入开关的实证核查（验证报告 007 的疑问）

**学习方式**：不是读代码，是**用工具验证**报告 007 提出的疑问

---

## 一、验证目标

报告 007 发现 `nt10.py` 的注入开关：
```python
_inject = (os.environ.get("NT10_INJECT") == "1") or os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "inject_ayria.on"))
```

**疑问**：`launch_chain.py` 或 `run.cmd` 是否创建这个文件/设置这个变量？

---

## 二、验证结果（实测）

### ① `bundle\` 目录里有没有 `.on` / `.flag` 文件

```
=== bundle 里所有 .on / .flag 文件 ===
(空 = 无)
```

**没有任何 `.on` 或 `.flag` 文件。**

### ② `launch_chain.py` 有没有提到 `inject`

```
Line 5:   `Ayria\Injector32.exe` on line 26 raised
Line 15:  straight through `Injector32.exe` with NO `nt10.py`. That breaks LSG for us
Line 34:  3. run nt10.py  -> launches the client through Ayria\Injector32.exe -qa,
Line 74:  INJ = os.path.join(GAME, r"Ayria\Injector32.exe")
Line 262: for p, what in ((INJ, "Injector32"), (TGT, "client exe"), (ROOM, "ol_room_owner")):
Line 409: #   Injector32.exe "<client>" -qa
Line 415: #     -> injector reaped before it creates the game
Line 420: # injector -- CodolGame.py:291-292 warns ERROR_FILE_NOT_FOUND follows the
```

**全部是注释和路径引用，没有任何一处创建 `inject_ayria.on` 或设置 `NT10_INJECT`。**

### ③ `run.cmd` 有没有提到

```
Line 52: call :need "%BUNDLE%\nt10.py"                      "bundle nt10.py"
Line 56: call :need "%PAYLOAD%\Injector32.exe"              "payload Injector32.exe"
```

**只是检查文件存在，没有设环境变量。**

---

## 三、这就产生了一个严格的推论

### 事实链

1. `nt10.py:1373` 判定 `_inject = False`（既无环境变量，又无 flag 文件）
2. `_inject = False` ⇒ 走 `subprocess.Popen([os.path.join(a.root, a.exe)], cwd=a.root)`
3. 直起客户端**不经过 Injector32.exe**
4. **⇒ Ayria 插件不会加载**
5. 插件不加载 ⇒ `CodolGameServer.Localnet32` / `Alwaysoffline.Localnet32` **都不在**
6. 没有 `Alwaysoffline` ⇒ **没有 LSG 大厅服务**
7. 没有 `CodolGameServer` ⇒ **没有战斗服**

### 但 `launch_chain.py` 的注释说

行 34：
> 3. run nt10.py → launches the client through **Ayria\Injector32.exe -qa**

**注释说要通过 injector 启动，但代码实际不会。**

---

## 四、这是 bug 还是设计

### 可能性 A：打包遗漏

作者开发时 `bundle\` 里有 `inject_ayria.on`，打包时忘了带上。

**证据支持**：
- `nt10.py` 的注释明确说"为什么需要注入"
- `launch_chain.py` 的文档说"through Injector32.exe"

**证据反对**：
- 如果遗漏，作者自己测试时会发现插件不加载
- 除非作者测试时用的是**开发目录**（有 `.on` 文件）而不是**打包目录**

### 可能性 B：`--no-dedicated` 路径不需要注入

`run.cmd` 固定传 `--no-dedicated`。

但 `--no-dedicated` 只是跳过**第二进程**（dedicated），不影响**第一进程**（client）的注入。

**不成立。**

### 可能性 C：靠 `launch_chain.py` 的某个环境变量传下去

检查 `chain_env()`：

```python
env["OLMOD_PROCESS_ROLE"] = role
env["OLMOD_DEDICATED_CONTROL_PORT"] = str(DEDICATED_PORT)
env["OLMOD_CLIENT_BRIDGE_PORT"] = str(BRIDGE_PORT)
env["OLMOD_ROOM_OWNER_PORT"] = str(ROOM_PORT)
env["OLMOD_CLIENT_INSTANCE"] = "1"
env["OLMOD_CLAIM_LOBBY"] = "1"
env["OLMOD_CONSOLE_LOG"] = ...
env["CODOL_FORCE_RECORD_VALIDATOR"] = "1"
env["OLMOD_STATS_NAME_UTF8"] = "1"
```

**没有 `NT10_INJECT`。**

**不成立。**

---

## 五、结论

**这个包按字面执行，插件不会加载。**

但这与"项目是正常的"（用户明确说过）矛盾。

**所以必然存在我还没看到的东西**。可能的藏身处：

1. **`payload\Ayria\` 目录里是否有 `.on` 文件**（deploy 后会复制到客户端根目录）
2. **客户端根目录里是否已经有这个文件**（之前的手工操作留下的）
3. **`deploy.ps1` 是否创建它**
4. **`preflight.ps1` 是否创建它**

★ **下一步必须查这四处。**

---

## 六、方法论记录

这次学习的价值在于：**不是读代码，而是把代码的判定条件代入实际环境，推出必然结果，再去找矛盾。**

- 读代码：`_inject` 的条件是"环境变量或文件"
- 代入环境：两者都没有
- 推出结果：`_inject = False`
- 追后果：插件不加载 → 大厅/战斗服都没有
- 发现矛盾：这与"项目正常"冲突
- 下一步：查还有哪些地方可能创建这个文件

**这比"读一遍然后总结"深一层。**
