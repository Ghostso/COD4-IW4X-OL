# 学习报告 028 — 逐字节：名字常量的最终定案（三个不同用途的"名字"）

**方法**：`launch_chain.py` 全文正则计数 + `Alwaysoffline` 名字区逐串切分
**性质**：全实测
**★★★ 本报告把"名字"问题彻底拆清：有三个**完全不同**的名字**

---

## 一、★★★ `launch_chain.py` 的名字常量计数（实测）

```
SGamingSH0X        0 次   ← ★★★ 完全没有
Easily_            3 次   （L369 注释、L372 注释、L377 代码）
Lifetime丷          3 次   （L369、L372、L84? 注释）
Lifetime           3 次   （同上，子串）
Client青            0 次
AdministraClient   1 次   （L158 是 force_display_name.py 的默认，不在本文件）
Sunl1ght           0 次
```

### ★★★ 决定性结论

```
二进制 (Alwaysoffline @0x3B2F50)  "SGamingSH0X"   ← 编译期常量（认证用）
launch_chain.py:377               "Easily_"       ← ★★★ 失配
```

★★★ **`launch_chain.py` 里 `SGamingSH0X` 出现 **0 次** ——
确认它是**过期版本**（停在 2026-10-11 的 `Easily_`），
而二进制是 **2026-10-13+** 的 `SGamingSH0X`。**

### ★ 三个时间戳的对照

```
2026-10-11   launch_chain.py 写成 "Easily_"        （L372 注释）
2026-10-13   IdentityConfig.hpp 改成 "SGamingSH0X"  （:77-85）
2026-10-21   Alwaysoffline.Localnet32 编译          （PE 时间戳 0x6AD90EEC）
             ⇒ 二进制内含 "SGamingSH0X"              （@0x3B2F50 实测）
```

★★★ **⇒ `launch_chain.py` 落后源码 **2 天**、落后二进制 **10 天**。**

---

## 二、★★★ 三个"名字"必须分清（这是报告 011/014/015 混乱的根源）

### 名字 1：**认证名**（`DefaultUsername`）—— 决定能否进服

```
位置：Alwaysoffline.Localnet32 @0x3B2F50 = "SGamingSH0X"
用途：connect 名字校验（SV_DirectConnect 的 roster username vs userinfo name）
要求：★ 必须与客户端上报的 16 字节字段**逐字节相同**
同步：源码常量 = 二进制常量 = force_display_name 写入值
```

★★★ **`launch_chain.py` 的 `"Easily_"` 破坏了这个同步 ⇒ 进不去服。**

### 名字 2：**统计名**（`OLMOD_STATS_SELF_NAME`）—— 榜单显示

```
位置：Alwaysoffline @0x3B5C28 = "OLMOD_STATS_SELF_NAME"
默认值：'Lifetime' 在 0x3B5C40（紧邻，是默认值的一部分）
用途：Stats/Friends2 的生涯榜名字
要求：★ 与认证名**无关**
```

### ★★★ 逐字节证据（`0x3B5BF8..0x3B5C60`）

```
0x3B5BF8  26  "OLMOD_STATS_SELF_PRESTIGE"
0x3B5C14  18  "OLMOD_STATS_SELF_ID"
0x3B5C28  20  "OLMOD_STATS_SELF_NAME"
0x3B5C3C  (4 字节重叠)  ← "Lifetime" 从这里开始（0x3B5C40 的 'L' 在 0x3B5C3C+4）
0x3B5C4C  15  "OLMOD_STATS_SELF_XP"
0x3B5C60  22  "Stats::readStatsByRank"
0x3B5C78  24  "Stats::readStatsForEntity"
0x3B5C94  4   "clan"
0x3B5C9C  46  "Stats 4/4: args unparsable; answering empty (unchanged)."
```

★★★ **`Lifetime` 就在 `OLMOD_STATS_SELF_NAME` 之后 4 字节处** ——
**它是 `OLMOD_STATS_SELF_NAME` 的**默认值**！

★★ **⇒ `Lifetime` 是**统计榜的默认显示名**，与认证名无关。**

★★★ **⇒ 报告 027 第八节"`Lifetime` 是地图名还是名字"的疑问：它是**统计名**。**

### 名字 3：**界面名**（客户端自造）—— 由 `force_display_name.py` 改

```
位置：客户端进程内存的 16 字节定长字段（10 处）
来源：Windows 账户名[:10] + "Client"（如 Administrator → AdministraClient）
用途：右上角/角色名/榜单/列表
要求：★ 必须与名字 1 逐字节相同（connect 校验）
```

---

## 三、★★★ 三个名字的关系图（字节级还原）

```
┌──────────────────────────────────────────────────────────────┐
│ 名字 1：认证名  "SGamingSH0X"                                 │
│   来源：Alwaysoffline @0x3B2F50（编译期常量）                 │
│   消费：connect 校验（SV_DirectConnect）                      │
│         ★ 比对客户端上报的 16 字节字段                        │
└──────────────────────────────────────────────────────────────┘
                          ↕ 必须逐字节相同
┌──────────────────────────────────────────────────────────────┐
│ 名字 3：界面名（客户端内存 16 字节字段 ×10 处）                │
│   来源：客户端自造（Windows 账户名 + "Client"）               │
│   改写：force_display_name.py --apply <名字> --encoding utf-8 │
│         launch_chain.py:377 传 "Easily_"  ← ★★★ 错误！        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 名字 2：统计名  "Lifetime"（默认）                            │
│   来源：OLMOD_STATS_SELF_NAME 的默认值（@0x3B5C40）           │
│   消费：Stats/Friends2 生涯榜                                 │
│   ★ 与名字 1/3 无关，可独立设置                               │
└──────────────────────────────────────────────────────────────┘
```

★★★ **⇒ 只有**名字 1 = 名字 3** 这一条约束。名字 2 完全独立。**

---

## 四、★★★ 修复方案（最小改动）

### 方案 A：改 `launch_chain.py` 的默认值（一行）

```python
# 现状
display_name = os.environ.get("OLMOD_DISPLAY_NAME", "Easily_")

# 改为
display_name = os.environ.get("OLMOD_DISPLAY_NAME", "SGamingSH0X")
```

★★ **优点**：一行改动，与二进制常量对齐。
★ **缺点**：改的是**交付包的原始文件**（虽是副本，但要记录）。

### 方案 B：设环境变量（零改动）

```cmd
set OLMOD_DISPLAY_NAME=SGamingSH0X
set OLMOD_DISPLAY_NAME_ENC=utf-8
```

★★ **优点**：**不改任何文件**。
★★★ **这是首选 —— 与我们"不改固化链"的铁律一致。**

### ★★★ 方案 C：改源码常量（改二进制常量）

★★ **不推荐** —— 要重新编译 `Alwaysoffline.Localnet32`（4 MB），
且**它当前与源码一致**，改了反而制造新的失配。

---

## 五、★★★ 复核：字节长度

```
"SGamingSH0X"  = 10 字节（纯 ASCII）
字段容量       = 16 字节
⇒ 余 6 字节补 NUL  ✓ 无截断争议

"Easily_"      = 7 字节
⇒ 余 9 字节补 NUL

"Lifetime丷"   = 8 + 3 = 11 字节（UTF-8）
"内裤再美终究装逼" = 16 字节（GBK，正好装满）
```

★★ **`SGamingSH0X` 是 10 字节，安全。** ✓

---

## 六、逐字节证据总表

| # | 位置 | 内容 | 结论 |
|---|---|---|---|
| 1 | `launch_chain.py:377` | `os.environ.get("OLMOD_DISPLAY_NAME", "Easily_")` | ★★★ 失配源 |
| 2 | `launch_chain.py` 全文 | `SGamingSH0X` **0 次** | ★★★ 完全缺失 |
| 3 | `Alwaysoffline @0x3B2F50` | `SGamingSH0X` | ★★★ 二进制权威值 |
| 4 | `Alwaysoffline @0x3B5C28` | `OLMOD_STATS_SELF_NAME` | 统计名变量 |
| 5 | `Alwaysoffline @0x3B5C40` | `Lifetime` | ★ 统计名默认值 |
| 6 | `Alwaysoffline @0x3B2F64` | `OLMOD_PLATFORM_USER_ID` | 平台 ID |
| 7 | `launch_chain.py:158`（force_display_name.py） | `AdministraClient` | 扫描串默认值 |

---

## 七、结论

### 1. ★★★ 名字失配已**完全定案**

```
源码      "SGamingSH0X"
二进制    "SGamingSH0X"
launcher  "Easily_"        ← 唯一失配
```

**修法：设 `OLMOD_DISPLAY_NAME=SGamingSH0X`（零文件改动）。**

### 2. ★★★ 三个名字必须分清

```
认证名  = SGamingSH0X   （决定能否进服）
界面名  = 被 force_display_name 改成 SGamingSH0X（客户端内存）
统计名  = Lifetime      （榜单，独立，可不管）
```

★★ **报告 011 说"名字有两条路"（`profile.name` + `extra_data.username`），
现在修正为**三条路**（认证 / 界面 / 统计）。**

### 3. ★ 本机账户名的影响

★★ **如果本机是 `Z7-CT5N1`（13 字符？不，7 字符），
客户端自造名会是 `Z7-CT5N1` + `Client`？**

★ **`force_display_name.py --needle` 默认 `AdministraClient`**
—— **本机扫不到。**

★★★ **⇒ 必须同时设 `--needle`。但 `launch_chain.py:388` **不传 `--needle`**！**

★★ **⇒ 即使名字值对了，**扫描串错了照样扫不到**。**

★ **这是第二个必须修的参数。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **`force_display_name.py` 的 `--needle` 在 `launch_chain.py` 里能否传**
      （当前 `L388` 只有 `--watch` / `--apply` / `--encoding`）
- [ ] ★★ **本机账户名对应的客户端自造名**（需要实际启动客户端确认）
- [ ] ★★ **`OLMOD_STATS_SELF_NAME` 的默认值完整字节**（`Lifetime` + 什么？）
- [ ] ★ **`Stats::readStatsByRank` / `readStatsForEntity` 的实现**
- [ ] ★ **`OLMOD_STATS_*` 共 8 个变量的完整清单**（报告 026 已列 34 个中的 8 个）
