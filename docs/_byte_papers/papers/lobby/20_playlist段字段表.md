# `playlist` 段 · 123 个对局配置的完整字段表

> 对象：`mp_playlists_shipRetail_1.0.0.info` 的 `playlist` 段
> 证据：`_byte_papers/playlist_plain.txt`（已解压，可复跑）

---

## 1. 段结构总览

```
version 796
  ├─ rule / set         全局规则（dvar 默认值）
  ├─ catinfo    × 25    ★ 模式分类（UI 分组按钮）
  ├─ gametype   × 43    ★ 模式定义（脚本 + 规则）
  └─ playlist   × 123   ★ 对局配置（地图列表 + 规则）
```

**123 个 `playlist` = 大厅里 123 个可选"玩法组合"。**

---

## 2. 一个完整的 `playlist` 块（实测，`playlist 1`）

```
playlist 1
displayorder 1
category 1
name chinese "实战对抗"
name english "Skirmish"
description chinese "冲锋(随机地图)-冲锋团队竞技模式，人数6V6，
    死亡后固定复活点复活，在10分钟内，率先达到50击杀的队伍获胜。"
description english "Charge TDM with bots."
buildversion default cb3 release
unlocklevelend 70
vsrule "6V6"
combattraining
onboardbonus
difficulty 0
minparty 0
maxparty 4
rule 1011 1
rule 3265 4
maxhumanplayersperteam 3
rule scr_cha_scorelimit 50
rule scr_cha_timelimit 10
rule scr_cha_roundlimit 2
rule scr_cha_roundswitch 2
rule scr_cha_winlimit 1
rule scr_cha_halftime 1
rule scr_cha_scorelimithalftime 1
mp_nuked,cha,1
mp_mideast,cha,1
mp_shipment_long,cha,1
mp_cha_quad,cha,1
mp_mountain,cha,1
wargodWarmRoundId 216
```

---

## 3. 字段逐条

| 字段 | 示例 | 含义 |
|---|---|---|
| `playlist <N>` | `1` | **对局 ID**（下一个可用 ID = 256） |
| `displayorder <N>` | `1` | UI 里的排序 |
| `category <N>` | `1` | 指向 `catinfo` 的 ID |
| `name chinese "<GBK>"` | `"实战对抗"` | **UI 显示名（中文）** |
| `name english "<str>"` | `"Skirmish"` | UI 显示名（英文） |
| `description chinese "<GBK>"` | 大段说明 | **UI 显示描述** |
| `description english` | | |
| `buildversion <a> <b> <c>` | `default cb3 release` | 构建标记 |
| `unlocklevelend <N>` | `70` | 解锁所需等级 |
| `vsrule "6V6"` | | 人数规则文本 |
| `combattraining` | （标志） | 是否为战斗训练 |
| `onboardbonus` | （标志） | 新手奖励 |
| `difficulty <N>` | `0` | 难度 |
| `minparty <N>` / `maxparty <N>` | `0` / `4` | 组队人数范围 |
| `maxhumanplayersperteam <N>` | `3` | 每队真人上限 |
| `rule <dvar> <val>` | `scr_cha_scorelimit 50` | **本对局的规则覆盖** |
| `<map>,<gametype>,<flag>` | `mp_nuked,cha,1` | **★ 地图条目** |
| `wargodWarmRoundId <N>` | `216` | 战神模式关联 |

---

## 4. ★ 地图条目格式

```
mp_nuked,cha,1
mp_mideast,cha,1
mp_shipment_long,cha,1
mp_cha_quad,cha,1
mp_mountain,cha,1
```

格式：`<地图资产名>,<gametype>,<标志>`

**这三元组就是"这个对局包含哪些地图、用什么模式跑"。**

### 对"创建房间"的意义

**自定义房间 = 自己写一个 `playlist` 块**：

```
playlist 256
displayorder 99
category 3
name chinese "我的模式"
name english "My Mode"
rule scr_tdm_scorelimit 100
mp_crash_tropical,tdm,1
mp_village,tdm,1
```

---

## 5. 全部 123 个 playlist 的覆盖范围

- **PvP**：`category 1..16`（团队竞技、搜索爆破、冲锋、抢劫、VIP、核弹足球…）
- **PvE**：`category 20..30`（英雄行动、塔防、丧尸猎人、生存、机械僵尸…）

---

## 6. `Name_chinese` 用的是 **GBK 编码**

实测字节（`playlist 1` 的中文名）：

```
"ÊµÕ½¶Ô¿¹"   ← 这是 GBK 的"实战对抗"被按 latin1 读出来的样子
```

**编码是 GBK（CP936），不是 UTF-8。**

改中文名时必须按 GBK 写回，否则乱码。

---

## 7. 可改清单（全部明文）

| 目标 | 操作 |
|---|---|
| 新增一个对局（房间配置） | 加一个 `playlist` 块，ID 用 256 |
| 删除一个对局 | 删掉该块 |
| 改对局出现位置 | 改 `displayorder` |
| 改对局归属分类 | 改 `category` |
| 改对局名字 | 改 `name chinese`（GBK） |
| 改对局描述 | 改 `description` |
| 改对局包含的地图 | 改 `<map>,<type>,<flag>` 行 |
| 改对局规则 | 改 `rule ...` |
| 改组队人数 | 改 `minparty` / `maxparty` |

**123 个对局，全部可读、可改、可增、可删。**

---

## 8. 与"创建房间/开始游戏"的关系

大厅里"创建房间"时，客户端选的是：
1. **`catinfo`** 里的一个分类（PvP/PvE 按钮）
2. **`playlist`** 里的一个对局
3. 一个地图

**然后把这些打包成 `6/14 mmstart` 命令**（第 6/14 卷已解）。

**所以：改 `playlist` → 改可选的房间配置。**

---

## 9. 未解

1. 磁盘 `mp_playlists.ff`（AES）与服务端 `.info` 的优先级
2. `flag` 第二字段（`mp_nuked,cha,1` 的 `1`）的取值含义
3. `rule` 里大量数字 dvar（`1011`、`3265`）的含义
4. `wargodWarmRoundId` 的用途
