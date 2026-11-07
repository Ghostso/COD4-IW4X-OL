# `playlist` 段 · 探讨：从"模式表"到"完整对局配置"

> 对应：`lobby/20_playlist段字段表.md`

---

## 一、我以为 `catinfo` 已经够了

上一卷我发现 `catinfo` 是"模式按钮表"，觉得"加删模式"的问题解决了。

**但那只是"有哪些分类"。**

`catinfo` 的一条是：

```
catinfo 3  1  0  ""  "团队竞技"  "Team Deathmatch"
```

它只说"有一个叫团队竞技的按钮"，**没说这个按钮点下去会发生什么**。

---

## 二、`playlist` 段才是"点下去会发生什么"

`playlist 1` 的完整内容里有：

```
mp_nuked,cha,1
mp_mideast,cha,1
mp_shipment_long,cha,1
mp_cha_quad,cha,1
mp_mountain,cha,1
```

**这是"这个对局在哪些地图上、用什么 gametype 跑"。**

还有：

```
maxparty 4
maxhumanplayersperteam 3
rule scr_cha_scorelimit 50
rule scr_cha_timelimit 10
```

**这是"这个对局允许多人、打多久、多少分赢"。**

---

## 三、三层结构现在完整了

```
catinfo  (25)   →  UI 上显示哪些"大类按钮"
gametype (43)   →  每个模式的脚本和基础规则
playlist (123)  →  每个"可玩对局"的地图 + 规则组合
```

**关系**：

```
catinfo 3 (团队竞技)
   └─ playlist N (category 3)  ← 多个对局挂在同一个分类下
        ├─ mp_nuked,tdm,1
        └─ mp_village,tdm,1
```

---

## 四、这意味着"自定义对局"是完全可行的

用户想要"什么创建房间开始游戏都不是问题"。

**创建房间 = 客户端选一个 `playlist` + 一张地图，然后打包成 `mmstart`。**

如果我在 `.info` 里加一个 `playlist 256`：

```
playlist 256
displayorder 99
category 3
name chinese "我的自定义"
name english "Custom"
maxparty 4
rule scr_tdm_scorelimit 100
mp_crash_tropical,tdm,1
mp_village,tdm,1
```

**这个对局就会出现在 UI 里（如果服务端下发优先）。**

---

## 五、一个重要的编码细节

中文名是 **GBK**：

```
"ÊµÕ½¶Ô¿¹"  →  按 GBK 解释  →  "实战对抗"
```

**如果按 UTF-8 写回去，客户端会显示乱码。**

这是一个很容易踩的坑 —— 文件本身没有 BOM，也没有编码声明，
纯靠约定。

`version 796` 这一行也是 ASCII，说明整个文件是"混合编码"：
- 结构关键字：ASCII
- 中文值：GBK

**写回时必须严格保持。**

---

## 六、还差什么才能"完全自定义页面"

| 层级 | 在哪 | 状态 |
|---|---|---|
| 模式分类按钮 | `catinfo` | **明文可改** |
| 对局配置 | `playlist` | **明文可改** |
| 模式逻辑 | `.ff` 里的 GSC | 加密 |
| **页面布局/控件位置** | `ui_mp.ff` | **加密** |

**前两层打开了，后两层还没有。**

所以：
- ✅ 加/删模式
- ✅ 加/删对局
- ✅ 改名字、改规则、改地图池
- ❌ 改页面布局、加完全新的 UI 控件

---

## 七、方法论收获

> **"模式列表"和"模式定义"和"模式玩法"是三件事，分别在三个地方。**

- 列表 → `catinfo`（明文）
- 定义 → `gametype`（明文）
- 玩法 → GSC 脚本（加密）

**把这三者分开，就不会因为"玩法加密"而误以为"列表也加密"。**

---

## 八、下一步

1. **验证服务端 `.info` 是否覆盖磁盘 `.ff`** —— 决定这条路线是否成立
2. 统计 123 个 playlist 的分布（哪些是 PvP 哪些是 PvE）
3. 找 `flag` 字段的含义
