# 大厅动态内容：publisher_files 全清单

> 对象：服务端 `10/21` 下发的全部 `.info` 文件
> 证据：`tools/publisher_inspect.py` 逐个解压

---

## 1. 总览

| 文件 | 大小 | 格式 | 作用 |
|---|---|---|---|
| `mp_playlists_shipRetail_1.0.0.info` | 21,412 | **zlib → 文本** | **模式/对局配置**（第 19/20/21 卷） |
| `configs_s.info` | 25,126 | **二进制（魔数 `34 FE`）** | 服务器配置（未解） |
| `market_ui.info` | 2,010 | **zlib → 文本** | 市场 UI 标签 |
| `sku_tags.info` | 3,520 | 文本 INI | 商品标签 |
| `activities_v1.info` | 417 | 文本 INI | **活动列表** |
| `daily_challenge_config.info` | 363 | 文本 INI | **每日挑战** |
| `MOTD.info` | 147 | 文本 INI | **大厅公告** |
| `tlogconfig.info` | 154 | 文本 INI | 日志上报配置 |
| `market-down.info` | 44 | 文本 INI | 市场开关 |
| `broadcast.info` | 24 | XML | 广播消息 |
| `whitelist_tester.info` | 93 | 文本 | 白名单 |

---

## 2. `MOTD.info` —— 大厅公告

```ini
[1]
title=使命召唤Online 战场集结
content=大厅商城、军火基地、个人仓库与靶场战斗服务已全部…
```

**这是大厅显示的"公告"文字。**

**格式**：INI 段，UTF-8 中文。

---

## 3. `activities_v1.info` —— 活动列表

```ini
[activities]
num=2

[activity_1]
id=1
title=战神排位 赛季冲刺
content=排位赛模式已修复并顺延，点击…
```

**这是活动横幅的内容。**

---

## 4. `daily_challenge_config.info` —— 每日挑战

```ini
[daily_challenge]
num=3

[1]
id=1
title=精准射击
content=在对局中完成10次爆头击杀
target=10
reward_type=1
```

**这是每日/每周挑战。**

---

## 5. `market_ui.info` —— 市场标签

```ini
[tags]
45137=HOT:1
41526=HOT:2
45542=HOT:3
...
44130=NEW:1
```

**格式**：`<SKU 号>=<标签>:<顺序>`

**这是商城"热销/新品"排序表。**

---

## 6. `broadcast.info` —— 广播

```xml
<MSG T=2050000000,P=0/>
```

**XML 格式的广播消息。**

---

## 7. `tlogconfig.info` —— 日志上报

```ini
[TLog]
uiclickcount=0
uiclick=0
uipage=1
uilastpages=0
dwdsmm_number=30
```

**控制客户端上报哪些 UI 行为。**

---

## 8. `configs_s.info` —— 唯一的二进制

```
head: 34 FE 6F 2C 4C D2 EC 77 64 AC 84 A1 CC 8D 18 9C ...
```

- 不是 zlib（`78 xx`）
- 不是 INI 文本
- 25,126 字节

**未解。**

---

## 9. ★ 对所有文件的意义

**大厅上几乎所有"看得见的内容"都来自这些 `.info`：**

```
模式列表      ← mp_playlists_*.info
公告          ← MOTD.info
活动          ← activities_v1.info
每日挑战      ← daily_challenge_config.info
商城排序      ← market_ui.info / sku_tags.info
广播          ← broadcast.info
```

**全部是 INI/text，全部可编辑。**

---

## 10. 这构成"完全自定义大厅"的第二层

```
第 1 层：模式/对局（playlists）
第 2 层：公告/活动/挑战/商城（MOTD/activities/daily/market）
第 3 层：页面布局（ui_mp.ff，加密）
```

**第 1、2 层全部打开。第 3 层未开。**

---

## 11. 📌 GBK/UTF-8 编码陷阱

实测：

```python
open(...).read()  →  'gbk' codec can't encode ... \xe4\xbd\xbf
```

`\xe4\xbd\xbf` 是 **UTF-8 编码的"使"**。

**所以 `MOTD.info` / `activities_v1.info` 是 UTF-8。**

但 `playlist` 里的中文是 **GBK**（第 20 卷已验证）。

**两种编码混在不同文件里。**

| 文件 | 编码 |
|---|---|
| `MOTD.info` | **UTF-8** |
| `activities_v1.info` | **UTF-8** |
| `daily_challenge_config.info` | **UTF-8** |
| `mp_playlists_*.info` | **GBK** |

**写回时必须按文件区分，不能统一。**

---

## 12. 未解

1. `configs_s.info`（`34 FE` 魔数）是什么格式
2. `sku_tags.info` 里 SKU 号（45137 等）对应哪些商品
3. `market_ui.info` 的 zlib 版本与 `sku_tags.info` 的明文版本谁生效
4. `broadcast.info` 的 `T=2050000000` 是什么（时间戳？）
