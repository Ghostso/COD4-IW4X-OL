# 大厅功能全量修复 —— 诊断与计划（2026-10-05）

> 承接 `HANDOFF_20261005_LOBBY_REACHED.md`（进大厅）与 `HANDOFF_20261005_REFKIT_WORKS.md`。
> 本轮目标：**专修大厅全部 BUG**。

---

## 0. 一句话

大厅已经能进，但**几乎所有交互功能都是空的**。根因不是我们改坏了，
而是**三方"能进靶场"的成功参照从来没有实现过这些功能**：
它的 `lsg.log` 里 `80/70/107/119/173/174/232` 全部回 66 字节空应答，
库存只有 8~9 件，`mp_playlists` 是自述 *"not the recovered production playlist"* 的占位文件。

**所以这批 BUG 没有"标准答案"可抄，必须逐项逆向。**

---

## 1. ★★ 客户端自己上报了失败原因（`71/7` = UIException）

`service=71 task=7` 是客户端的**日志上报通道**，里面装的就是"哪个 UI 操作炸了、为什么"。
从 `lobby_tasks.bin` 解出的原文（base64 解码后）：

| 次数 | 错误 | 调用链（尾部） | 对应功能 |
|---|---|---|---|
| 5x | `TypeError #1010` (未定义属性) | `OnboardingChallengesChecklistListItem.as:127` → `HomeView` | **大厅首页挑战清单** |
| 4x | `TypeError #1009` (访问空对象) | `MarketScrollGrid.as:145` → `MarketplaceFeaturedTab` → `MarketplaceView` | **商城（点商城标签）** |
| 1x | `TypeError #1009` | `MarketScrollGrid.as:145` → … → `PageNavigationController` | **商城（从主菜单进）** |
| 1x | `TypeError #1009` | `MarketScrollGrid.as:145` → … → **`SupplyDropView.as:202`** | **军火基地 / 军火箱** |
| 1x | `RangeError #1125` | `FilterCategoryButton.as:215` → `MOTDNotificationsPopup` | **筛选/公告弹层** |

### 关键结论

**`MarketScrollGrid.as:145` 抛 `#1009` = 它的数据源是 null。**
数据源来自 `80/70` 等 SKU 页；我们回空页 → 网格拿不到列表 → 视图构造中断 →

- 商城**空白**；
- `SupplyDropView`（军火箱）**构造到一半失败**，它的页面栈没有正常收尾 →
  返回时**旧页面没被关掉** → 你看到的"退出页面与大厅重叠"。

也就是说：**"军火箱页面重叠" 和 "商城空白" 是同一个根因**（SKU 页为空）。
修好 SKU 页，这两个会一起好。

---

## 2. 请求清单（你点完那一轮，83 条任务）

出现过的业务 service/task：

```
3/46 3/48 3/53            结算/生涯
6/5  6/14                 即时消息(mmbook)
8/1  8/2                  档案 public/secure
9/5  9/14                 好友
10/12 10/20 10/21         用户文件 / 发行方文件
12/6                      ?
28/4                      任务参数
29/10                     ?
68/3                      遥测
71/*                      日志上报(ClientLogin/ClientSettings/UIException…)
80/70 80/107 80/119 80/130 80/173 80/174 80/203 80/230 80/232   商城
93/1  93/131              余额 / 购买
102/1 102/7               ?
```

---

## 3. 已在本地修好的

### 3.1 ★ 购买解析（"背包/副武器/近战买不了"的直接原因）—— 已修

三方 C# 用**单一 58 字节硬模板**逐字节比对，只认"普通直购"这一种帧形。
实测 4/5 号背包、副武器、近战武器等走的是**别的帧形**（长度/可选字段不同）→
模板校验必然失败 → `Unsupported purchase parameters` → 玩家侧就是"点购买没反应"。

现改为**按类型标签 TLV 解析**（`0x08`=u32 / `0x03`=u8 / `0x01`=bool /
`0x10`=string / `0x13`=blob），只取需要的两个字段：

```python
vals = _scan_purchase_fields(payload)   # 顺序读出所有 u32
sku, quantity = vals[1], vals[3]        # 与 C# 取 payload[8]/[18] 等价
```

回测（三方实测帧）：`sku=22858, qty=1` ✅ 正确解出。
**实机验证：`购买成功 sku=32223 qty=1`，GP 883599 → 819999（真实扣款）。**

### 3.2 未映射请求现在显式记录 —— 已加

`reply_objects` 末尾不再静默返回空：
```
-> UNMAPPED service=%d task=%d payload=%dB -> 空 ACK (功能未实现)
```

### 3.3 AES 加速 + 按字节限流 —— 已修（上一轮）

- 纯 Python AES 对大包要 ~19s → 改用 PyCryptodome（逐字节一致，自动回退）。
- 单次 0x85 应答实测上限：384KB 过 / 528KB 断 → 库存按 **480KB 字节预算**截断。

---

## 4. 待修清单（按根因归组，不是按现象）

### ★★ 4.0 决定性发现：可购买的 SKU id 是有限子集

实机连点 6 次购买，请求是 `93/131`，TLV 解出的 `sku` 分别是：

```
242, 241, 241, 31816, 31774, 32223
```

对照目录 `marketplace-catalog.json`：

| sku | 在 catalog 里？ |
|---|---|
| 241 | ❌ 不存在 |
| 242 | ❌ 不存在 |
| 31774 | ❌ 不存在 |
| 31816 | ❌ 不存在 |
| **32223** | ✅ 存在（Item=18481, Category=3, CP 8080） |

**结论：客户端发的 sku 大多不在 exe 内嵌目录里**，所以 `purchase()` 报
`Unsupported SKU/currency/quantity` → 购买失败。
而 `32223` 命中 → **成功扣款**（GP 883599 → 819999）。

**这直接改变 A 的定位**：

- 之前以为"购买解析模板太窄"是主因（已修，解析现在没问题）；
- **真正的阻塞是目录覆盖不全** —— 客户端用的是一批**服务端 SKU id**，
  和 exe 内嵌的 37,615 条**不是同一编号体系**。
- 佐证：客户端问商店时发的是 `u32(0x6CA0F2CC) = 1822730568`
  （目录版本/分页 token），而 catalog 的 `Id` 只到 6 万级。

**这解释了为什么"背包/副武器/近战买不了"**：
这些条目的 sku（241/242/31774/31816…）都在服务端目录里，而 exe 里那份没有。

**要修，需要拿到服务端那份 SKU 目录**（或至少 `241/242/31774/31816` 等
客户端实际会用的 id → item/price 映射）。候选来源：
1. `common_marketplace_lite.ff`（29 MB，未解出的层二）；
2. 客户端 `80/70` 请求里的 `1625160` 版本串对应的目录数据；
3. 运行时从客户端内存里取它反序列化后的 SKU 列表。

### ★★ 4.0.1 层二攻坚结果（2026-10-05，`_mkt_layer2_probe.py` / `_mkt_period_probe.py`）

`common_marketplace_lite.ff` 的**层一已解出**：

```
文件      29,594,085 B
magic     IWff0100  version=461  lang=1
AES key   da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5   (全库唯一, 同 main\*.ff)
IV        d499de7d14802404db93a5b886340000
层一      29,593,808 B -> 'IWffs100' 00 00 00 00 | 288B 高熵 | zone@0x12C
          zone = 'common_marketplace_lite'
```

**层二仍在, 且已确认是强加密(不是压缩、不是简单密钥流)**：

| 检验 | 结果 | 判定 |
|---|---|---|
| zlib/deflate/gzip 全偏移扫描 | 0 命中 | 非压缩 |
| 整段熵 | 8.000 | 高熵 |
| 周期扫描 P=256..8192 (64KB 样本) | 最小 delta −0.009 | **无周期** |
| 0x1000 周期 1MB 复核 | 熵 7.9998 = 随机期望 | **否证周期性** |
| zone 名派生密钥(sha256/md5) + AES-CTR | 0 命中 | 否证 |
| 相隔 0x40000 窗口 XOR | 7.957 ≈ 随机 | 无重复密钥流 |
| 分块熵 | min 7.204 / avg 7.910 | 存在少量低熵块(局部结构) |

> ⚠️ 记录一个**踩过的坑**：初测 `dist=0x1000` 用 4KB 样本得出 XOR 熵 7.41,
> 看起来像周期; 但 64KB 样本是 7.999、1MB 复核是 7.9998 —— **7.41 是小样本偏差**
> (4KB 时随机期望本身就只有 ~7.7)。教训: 判"周期性/密钥流"必须用 ≥64KB 样本,
> 否则会把小样本统计噪声当成突破。

**结论**：`common_marketplace_lite.ff` 与 `main\*.ff` 一样, 层一是 AES-CTR,
层二是 **COD OL 引擎自有的加密容器(`IWffs100` 主体)**, 密码学上无弱点可利用。
仓库既有结论(`FF_LAYER1_DECRYPT_20260930.md`)已明确: 层二的实现在
`codoMP_client_shipRetailBase.dll` 的 `.tls`(15.5MB) / `.tvm0`(32MB) 未解析区,
且已否证 zlib/lzma/bz2/ECB/CBC/CTR 变体/滚动变换链。

**⇒ 纯静态解层二不是一条能在合理时间内走通的路。**
要拿到 SKU 目录, 更现实的是**运行时**: 在客户端已加载 `common_marketplace_lite`
之后, 直接从内存里取它解密后的 zone 数据(此时是明文)。

### ★★ 4.0.2 最后一轮静态尝试(均已否证)

对层二主体做了穷尽式验证, 全部否证:

| 假设 | 方法 | 结果 |
|---|---|---|
| 同 key + 同 IV 另起 CTR | AES-CTR(key192, iv) 解 64KB | 熵 7.997, 仅头 12B 明文 → body 未变 |
| 同 key + zero IV | AES-CTR(key192, 0) | 熵 7.997 → 否证 |
| CTR 计数器含偏移(iv+Δ, Δ=0x10/0x160/…) | 试多个 Δ | 否证 |
| 周期密钥流 | P=256..8192 扫描 + 1MB 复核 | 否证(见 4.0.1) |
| zone 名派生密钥 | sha256/md5 + 多种 IV | 否证 |
| 压缩(zlib/deflate/gzip/lzma/bz2) | 全偏移扫描 | 否证 |
| 分组模式(ECB/CBC/CFB/OFB) | 仓库既有结论 | 否证 |

**唯一读到的明文**: `IWffs100\0\0\0\0` + 288B 加密头 + zone 名(`@0x12C`)。
主体 29.6MB 全部高熵(7.997~8.000)。

### ★ 4.0.3 下一步（运行时路线）

静态路线到此为止。要拿 SKU 目录, 走**运行时内存取明文**:

客户端启动时**必然**解密 `common_marketplace_lite` 并把它放进内存
(否则商城不会尝试渲染), 因此内存里存在**解密后的 zone 数据**。

做法:
1. 用现成的注入链路(`CODOLServer\_mainline\agent_client.py` + `nt10.py`)挂上客户端;
2. 在进程里扫 `/proc` 等价物 —— Windows 下用 `VirtualQueryEx` 遍历可读区,
   找 `IWffs100` 或 zone 名 `common_marketplace_lite` 附近的**已解密**副本;
3. 命中后再分析其内容, 提取 SKU 记录(字段名 `productId`/`price`/`currency` 等
   已在 exe `0x6AF8D4` 附近出现过)。

工具基础已具备: `nt10.py` 里有 `ReadProcessMemory`/`VirtualQueryEx` 封装
(`nt10.py:825`、`:1549`), 可直接复用。

### A. 商城 SKU 页为空 → 商城空白 + 军火箱重叠 + 大部分买不了

`80/70 / 107 / 119 / 173 / 174 / 232` 全是空页。这是**当前最大的根因**。

客户端请求参数（三方日志原文）：

| task | 参数 | 解读（推测） |
|---|---|---|
| `80/70` | `1, 2000, "1625160"` | 页号=1 / 每页=2000 / 数据版本 |
| `80/107` | `1, 2000, "1625160"` | 同上（另一视图） |
| `80/119` | `1, 1000, 0x6CA0F2CC` | 页号 / 每页 / 筛选 id |
| `80/173` | `700` | 单条查询？ |
| `80/174` | `700, 1` | |
| `80/232` | 无参 | |

我们手上**有完整目录**：`marketplace-catalog.json` = 37,615 条 SKU
（字段 `Id/Item/Currency/Price/Category/Stackable/Grant/SelectedDays`），
去重后 17,371 个 item。**缺的只是"怎么按线上格式序列化"**。

> ⚠️ 风险提示（来自三方注释）：SKU 记录格式写错会让**整个 marketplace 服务死掉**
> （商店/仓库一起变灰且本次会话不恢复）。所以要做成**开关 + 逐字段对齐**，
> 一旦客户端再抛 `#1009` 就立刻回退空页。

### B. 游玩清单为空

`publisher_files\mp_playlists_shipRetail_release.info` 解开后是：
```
// Build 1649370 parser probe. Map and gametype assets exist locally.
// This is not the recovered production playlist and has not passed client QA.
gametype coop / playlist 1 / "Local Story Probe"
```
只有 1 个 coop 探测项。**需要真实 playlist 数据**。
本地有 `main\mp_playlists.ff`(49KB, 加密) 和 `common_gametype_*.ifs`（游戏模式资源），
但没有可直接读取的明文 playlist。

### C. 大厅首页挑战清单（`OnboardingChallengesChecklistListItem #1010`）

5 次异常，来自 `HomeView` 的挑战清单条目。需要给它下发挑战数据（或让它安全跳过）。

### D. 筛选/公告弹层（`FilterCategoryButton #1125` → `MOTDNotificationsPopup`）

`MOTD.info` 现在是 `; No local message entries.`，`broadcast.info` 是 `{}`。
空数据导致筛选按钮索引越界。

### E. 4/5 号背包 / 副武器 / 近战

购买解析已修（见 §3.1）。若仍不行，属于**背包槽位解锁**问题（可能走 `8/*` 档案
或别的 service），需要下一轮抓购买时的完整帧再定。

---

## 5. 下一步建议顺序

1. **A（商城 SKU 页）** —— 收益最大，一次修掉"商城空白 + 军火箱重叠 + 买不了"。
   做法：先用 **1 条 SKU** 试探格式（开关 `marketplace-skus.enabled`），
   确认客户端不抛 `#1009` 且能渲染，再逐页放大。
2. **C（首页挑战）** —— 异常次数最多，且是进大厅第一眼看到的。
3. **D（筛选/公告）** —— 数据补齐即可。
4. **B（游玩清单）** —— 需要真实 playlist 数据，工作量最大，放最后。

---

## 6. 复现与验证

```powershell
# 清场
Stop-Process -Name codoMP_client_shipRetail -Force -EA SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne 5160 } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }

# 跑一轮（agent_client 提权）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 600 --out n10lobby_audit.txt
```

诊断工具：

```powershell
# 看哪些请求没映射
Select-String 'REF_LOBBY_KIT\lobby_srv.log' -Pattern 'UNMAPPED'

# 客户端上报的 UI 异常
python -X utf8 "REF_LOBBY_KIT\_dump_uiexception.py" "REF_LOBBY_KIT\lobby_srv.log"
```

---

## 8. ★★ 失败记录：自编 SKU 页把整个 marketplace 打挂（2026-10-05 22:10）

**做了什么**：按内存里挖到的 `SKUObj` 字段表（`_sku_schema_as.py`）编了 3 条 SKU，
在 `80/70 / 107 / 119 / 173 / 174 / 232` 上作为目录页返回
（`market_skus.py` + `marketplace-skus.on` 开关）。

**结果**：**灾难性失败**。客户端表现：

- 仓库、商城等**全部变成红色叹号**；
- **角色被锁**；
- 界面上**所有按钮点不动**，整个大厅失去交互。

**这正是三方注释反复警告过的那个失败**：
> "客户端反序列化不了的应答会让**整个 marketplace 服务死掉**
>  （STORE/INVENTORY 变灰且本次会话不再恢复）"

**判断**：我们编的字段集/顺序**不对**。虽然字段名是从客户端内存里拿的，
但"在协议里怎么排、哪些必填、类型标签用哪个"仍然是猜的 —— 猜错就整服务死。

**已做的处置**：

1. 立即删除 `marketplace-skus.on` 开关（恢复空页行为）；
2. `lobby_server.py` 里加了**硬闸**：即使 `marketplace-skus.on` 存在, 也只在
   额外写了 `marketplace-skus-allow-unsafe.on` 时才真的发 SKU 页, 否则强制回空页；
3. 杀掉进程、重开一局（marketplace 服务只在**单次会话**内失效, 重开即恢复）。

**教训（写进纪律）**：

- **不要靠猜编协议对象。** 字段名能挖到, 不等于线格式能推出来。
- 三方只做过"靶场"这一条路, 商城/目录它压根没实现 —— **没有可抄的标准答案**。
  要动目录页, 必须先有**一份真实的服务端响应字节**（官方 pcap / 第三方存档）
  作为逐字节对照, 或者把客户端反序列化器逆到字段级。
- 任何"服务端主动发结构化对象"的新实验, 都必须**先只发 1 条**并准备随时回滚。

**结论**：商城目录这条线**暂停**。等拿到真实响应样本再动。
能安全推进的是那些**不依赖自编对象**的项（见下）。

---

## 7. 本轮改动文件

| 文件 | 改动 |
|---|---|
| `REF_LOBBY_KIT\marketplace_store.py` | `parse_purchase` 由硬模板改为 TLV 结构解析；库存按字节预算截断 |
| `REF_LOBBY_KIT\lobby_server.py` | 未映射请求显式记 `UNMAPPED` |
| `REF_LOBBY_KIT\codol_crypto.py` | AES 优先用 PyCryptodome（大包提速 ~9000x），保留纯 Python 兜底 |
| `REF_LOBBY_KIT\run_all.py` | 修掉与 lobby_server 重复拉起战斗服抢 28960 的问题 |
| `REF_LOBBY_KIT\_grant_all_items.py` | 新增：把 catalog 全部道具写进角色仓库 |
| `REF_LOBBY_KIT\_dump_uiexception.py` | 新增：解 `71/7` 里的 UIException |
| `REF_LOBBY_KIT\marketplace-catalog.json` | 新增：37,615 条 SKU（从归档 zip 取出） |
