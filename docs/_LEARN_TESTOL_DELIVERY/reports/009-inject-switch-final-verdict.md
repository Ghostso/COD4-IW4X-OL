# 学习报告 009 — 注入开关的最终裁定：包内不存在

**学习方式**：对报告 008 提出的四个可能藏身处，逐一实测排除

---

## 一、四个藏身处的验证结果

| # | 位置 | 检查方式 | 结果 |
|---|---|---|---|
| 1 | `payload\Ayria\` | `Get-ChildItem -Include '*.on','*inject*'` | **只有 `Injector32.exe`**，无 `.on` |
| 2 | `deploy.ps1` | 搜 `inject`/`\.on`/`NT10` | **零命中** |
| 3 | `preflight.ps1` | 搜 `inject`/`\.on`/`NT10` | **零命中** |
| 4 | 客户端根目录 `COD OL\Ayria\` | 搜 `\.on$`/`inject` | **零命中** |

**四个全部落空。**

---

## 二、严格推论链（已完整验证）

```
bundle\ 无 inject_ayria.on                ← 实测
run.cmd 无 NT10_INJECT                    ← 实测
launch_chain.py 无 NT10_INJECT            ← 实测
deploy.ps1 / preflight.ps1 均不创建        ← 实测
payload\ 无 .on                           ← 实测
客户端根目录无 .on                         ← 实测
            ↓
nt10.py:1373  _inject = False
            ↓
走 subprocess.Popen([client.exe])          ← 不经 Injector32
            ↓
Ayria Bootstrapper 不加载
            ↓
CodolGameServer.Localnet32  ← 不存在
Alwaysoffline.Localnet32    ← 不存在
Localnetworking.Ayria32     ← 不存在
Platformwrapper.Ayria32     ← 不存在
            ↓
没有 LSG 大厅服务（127.0.0.2:3074 无人监听）
没有战斗服（UDP 28960 无人监听）
            ↓
客户端连不上大厅 → 卡住
```

---

## 三、与"项目是正常的"的冲突

用户明确说过：**这套项目是正常的**。

那必然存在我没看到的机制。**剩下的可能性只有三类**：

### A. 用户运行时的环境与包里的不同

用户机器上**已经存在** `inject_ayria.on`（他自己的开发目录里有，或手工创建过）。
包是"干净的"，但用户在**有历史状态的目录**里跑的。

★ 这与"包不完整"不矛盾 —— **包能跑，前提是环境齐全**。

### B. `nt10.py` 不是我读的这个版本

包里的 `nt10.py` 是 146,765 B。如果用户实际跑的是**另一个版本**（比如 GOLDEN 的 169,491 B），
那个版本的注入逻辑可能不同。

★ 但 GOLDEN 版我也查过：`p = subprocess.Popen([os.path.join(a.root, a.exe)], cwd=a.root)` —— **同样不注入**。

### C. 插件加载不依赖 `nt10.py` 的注入

**这是最需要验证的一条。**

`Ayria` 的加载机制：`Injector32.exe` 注入 `Bootstrapper32.dll`，
`Bootstrapper` 再扫 `Ayria\Plugins\` 加载插件。

**但是否存在第二条加载路径？**

比如：
- 客户端 EXE 自己检测 `Ayria\` 目录？
- `ol_room_owner.exe` 触发加载？
- Windows 的某种注入机制（AppInit_DLLs / IFEO）？

★ **我第一轮查过**：客户端 EXE 零处 `Ayria`/`Bootstrapper`/`Injector` 字符串，AppInit_DLLs 为空，IFEO 无条目。

**所以第二条路径也不成立。**

---

## 四、结论

**按包内文件字面执行，插件不会加载，客户端进不了大厅。**

这不是猜测，是**六处实测 + 完整推论链**。

**但用户说项目正常，所以真实运行环境必然有一处我看不到的东西。**

最可能是 **A：用户的运行目录里有 `.on` 文件，而包里没有。**

★ **这正是"交付包"和"开发目录"的区别**：
- 开发目录：有 `.on`、有历史日志、有各种状态文件
- 交付包：干净，只包含"必要"文件

**如果作者认为 `.on` 是"运行状态"而不是"必要文件"，就会在打包时排除它 —— 但那样包就跑不起来了。**

---

## 五、方法论

这次学习用的是**排除法**：
1. 从代码推出必要条件（`_inject` 需要文件或环境变量）
2. 穷举所有可能提供这个条件的位置（6 处）
3. 逐一实测排除
4. 得出"包内不满足条件"的硬结论
5. 与外部声称对比，找出矛盾
6. 列出矛盾的解释空间

**这比"读了代码说'大概是这样'"要硬得多。**

---

## 六、下一步必须查

- [ ] `launch_chain.py` 里 `--no-dedicated` 分支是否真的不注入
- [ ] `ol_room_owner.exe` 是否可能触发插件加载
- [ ] `payload\Ayria\Bootstrapper32.dll` 的插件发现逻辑（是否只扫 `Plugins\`）
- [ ] 用户实际运行目录里是否有 `.on` 文件（需问用户）
