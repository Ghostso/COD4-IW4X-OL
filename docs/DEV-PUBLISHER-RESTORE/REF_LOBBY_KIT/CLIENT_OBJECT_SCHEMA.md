# 客户端对象字段表（从客户端自身 accessor 提取）

来源：`mem_linear/r_259D0000_06400000.bin` 里的
`codo.objects::<Class>/<field>` 访问器名（Scaleform/AS 侧真实读取的字段名）。
这是**客户端自己**声明它要读的字段，不是猜的 —— 用它来对齐服务端下发的
挑战 / 公告 / 游玩清单 / 快速匹配数据结构。

提取工具（可复现）：

```python
import re
data = open("mem_linear/r_259D0000_06400000.bin","rb").read()
seen = {}
for m in re.finditer(rb"codo\.objects::([A-Za-z0-9_]+)/([A-Za-z0-9_]+)", data):
    seen.setdefault(m.group(1).decode(), set()).add(m.group(2).decode())
```

## 挑战 / 首页挑战清单

| 类 | 字段 | 对应 bug |
|---|---|---|
| `OnboardingChecklistObj` | canReRoll, challenges, claimed, complete, featuredIdx, gpValue, isVeteran, name, refreshTime, rewardCosts, rewardIndex, rewards, timeLeft | 首页挑战 #1010 |
| `OnboardingChecklistChallengeObj` | uiChallenge | 同上 |
| `ChallengeBaseObj` | cppInitData, description, getFinished, getRewardText, icon, id, isPinned, name, profileID, progress, rewardGP, rewardXP, target | 生涯挑战面板 |
| `ChallengeObj` | actionIDs, awardSkuID, category, complete, currentProgress, description, enablePageJump, endValue, finished, gpGained, id, imageURL, items, name, playList, progress, rewardGP, target, targetProgress, weaponItemID, xp, xpGained | 生涯挑战面板 / 每日挑战 |
| `DailyChallengeObj` | chainBonus, difficulty, isPvp, rerollCount, score | 每日挑战条目 |
| `DailyChallengeChecklistObj` | scoreEarned | 每日挑战清单 |
| `DailyChallengeRewardObj` | score | 每日挑战奖励 |
| `ChallengeRewardObj` | claimed, entityDuration, entityId, entityInfo, gp, type, xp | 挑战奖励 |
| `WeeklyChallengeObj` | active, finished, revealed, step | 周挑战 |
| `VetChallengeObj` | awardSkuID, currentLevel, deactivated, finished, maxLevel, unlock_prestige, unlock_rank, unlocked | 老兵挑战 |

## 公告 / MOTD

| 类 | 字段 | 对应 bug |
|---|---|---|
| `MOTDMessageObj` | beViewed, caption, category, format, formattedTime, id, imagePath, imageURL, isFeaturedHomeAd, message, msgSender, otherSender, sender, timestamp, webData | 公告 #1125 |
| `MOTDCheckinRewardObj` | duration, featured, getDurationText, gp, isEarned, itemID, quantity, requirement | 签到奖励 |
| `ServerMessageObj` | duration, message, priority, timer, type | 系统消息 |

## 游玩清单 / 快速匹配

| 类 | 字段 | 对应 bug |
|---|---|---|
| `PlaylistCategoryObj` | cycleTodayIndex, entries, isFeatured, isNew, isNewUnlock, locked, name, unlockItem, unlockLevelStart | 游玩清单 MP 条目空 / `MatchMakingStripView` #1009 |
| `MatchSelectModeObj` | cycleTodayIndex, getPlaylist, heroOpsMaps, isNewUnlock, playlists, pveDifficulties, unlockItem | 模式选择 |
| `MatchSelectDifficultyObj` | getPlaylist, name, playlists | PvE 难度 |
| `QuickMatchFilterObj` | league, leagueName, map, maxPlayer, minPlayer, mode, playListID, playListName, skipLobby, type | 快速匹配 |
| `MatchStatusObj` | gametype, gametypeID, map, round, roundLimit, timeLeft, timeplayed | 对局状态 |

## 其它（本轮顺带提取）

| 类 | 字段 |
|---|---|
| `AARChallengeObj` | description, progressGain, progressStart, title |
| `MatchResultsChallengeObj` | currentProgress, gainedValue, startValue, targetProgress |
| `ActivityData` | gp, item, type, xp |
| `MessageRewardData` | currencyAmount, currencyType, item |

## 重要更正（2026-10-07）

* 旧 HANDOFF 把 `[%s]` / `%s=%s` / `update` / `userid` / `Whitelist` 当成
  `.info` 的解析键 —— 实测这两个格式串属于 **OpenSSL 的 config 解析器**
  （`codoMP_client_shipRetailBase.dll` 里紧邻 `crypto\conf\conf_def.c` /
  `crypto\conf\conf_api.c`），**与 `.info` 文件格式无关**。
* `catinfo` / `displayorder` / `unlockflag` / `levelrestricted` /
  `maxhumanplayersperteam` 这些键在 `mem_linear` 与 60MB 客户端 DLL 里
  **一处都搜不到** —— 说明 `mp_playlists` 解析器**不按这些名字读**。
  重建 `_build_playlists.py` 时沿用的字段名需要重新验证（见下）。

## 下一步（游玩清单 MP 条目）

`PlaylistCategoryObj` 真实读的是 `name / entries / unlockLevelStart / locked /
isNewUnlock / isFeatured / cycleTodayIndex`；`MatchSelectModeObj` 读 `playlists /
pveDifficulties / heroOpsMaps`。所以要真正让 MP 列表出条目，应该：

1. 找到 `mp_playlists_shipRetail_*.info` 的**原生解析器**（`MatchService` 侧），
   拿到它逐字段读的键名；
2. 或者 hook 客户端的 `PlaylistCategoryObj` setter，记录它拿到的字段序列
   （与 SKU 页同款做法：只读 dump + 开关 + 单条验证）。

在拿到真实键名之前，**不要**再凭猜改 `mp_playlists` 的字段名 —— 风险与
SKU 页那次相同（猜错会让整个 MatchMakingStripView 崩）。

---

# 附：从 EXE 直接提取的**商品/活动域名与对象 schema**（2026-10-07）

来源：`COD OL\codoMP_client_shipRetail.exe` 里的字符串表（不是猜 —— 这是客户端
自己用的域名与对象字段名）。用 `find`/`re` 定位，偏移已标注，可复现。

## 1. 商城域名（script command 名）

```
marketplace.init / getbalance / deposit / getproducts / getskus /
getinventory / clearinventory / getinventories / putentitlement /
getentitlements / showentitlements / getplayerinventory /
downloadconfig / livemarketupdate / purchasesku / putinventory
```

客户端本地命令：`cmd pr purchase`（0x6afd30）。

## 2. 客户端要的**配置文件**（`10/21` publisher 请求的源头）

| 文件 | 偏移 |
|---|---|
| `mp/marketplace.json` | 0x6a2cc4 |
| `mp/coMarketplaceItems.csv` | 0x6d2cb3 |
| `mp/coMarketplaceProducts.csv` | (同族) |
| `mp/coMarketplaceProductItems.csv` | (同族) |
| `mp/coMarketplaceSKUs.csv` | (同族) |
| `mp/coMarketplaceDiscounts.csv` | (同族) |
| `mp/unlockFlags.csv` | 0x6a2bc8 |
| `mp/saleTimesFlags.csv` | 0x6a2bb0 |
| `mp/coLoadoutBundlesTable.csv` | 0x6af9d4 |
| `mp/playersecuredata.def` / `mp/playerdata.def` | 0x6a4b7c / 0x6a4c64 |

★ **`mkt_assets/marketplace.client.json`** 就是客户端的 `marketplace.json` 清单，
里面写着这 6 张 CSV 的 **MD5 + version=1625160**：
```
coMarketplaceItems.csv        29ECAC6583404C3DA026B2BC0852F7B4
coMarketplaceProducts.csv     8E28FE82D782B957ACC303DB653DD701
coMarketplaceProductItems.csv 4546218F39C6DA111EE55939B7C68D1C
coMarketplaceSKUs.csv         34D383EAA01D6CF357D13D138E83789C
coMarketplaceDiscounts.csv    00FEB0FC06B17347A68A64D475F9DD43
unlockFlags.csv               14FE5D77C1E35DC35BF0744754F3DB19
```
2026-10-07 复核：1226 个 IIPS 包**按原始 MD5 全部不命中**；marketplace 包内只有
`.iwi` 图片，**没有 CSV**；这些 CSV 文件名**只出现在 exe**（不做成磁盘文件）。
→ 这三张表是**服务端下发的数据**，客户端只用清单校验 MD5。**拿不到原始字节，
  就永远对不上客户端编号**（见 HANDOFF §13.3）。

## 3. `codo.objects.SKUObj` —— 80/70 应答里每个 SKU 的字段（0x6af8c0 起）

```
productId, requirementLevel, requirementPrestige, requirementUnlockFlag,
stackable, promoSkuId, price, currency, startDate, endDate,
ignoreEntitlement, couponEnable, originalPrice, discountRate,
equipLevel, isBanned, isBasePerk, inInventoryButLocked,
inInventoryButExpired, showBreadcrumb, exclusiveProductID,
legendDesc, itemDependencies, isEquippableBundle, onboardCharacterID,
tagOrder, bHideFromMarket, giftable, isAvailableForSale, currentSKUIndex, skuTypes
```
（currency 取值有 `@SF_UI_CP` / `@SF_UI_GP` / `@SF_UI_HP` / `@SF_UI_EHP` 四个域。）

## 4. `codo.objects.ProductObj`（0x6aecd8 起）

```
characterIndex, characterName, characterType, lethalQuantity,
tacticalQuantity, nameid, maxArmor, maxHealth
```

## 5. SupplyDrop / 开箱（0x6a32b0 起）

```
supply_drop_list, %i_SlotCount, supply_drop_info,
%i_DustSKU, %i_DustRequirement, %i_SupplyMultipleConsume, %i_%i,
supply_drop_samples, NEW/FEATURED/RECOMMENDED,
%i_FeaturedEnabled, supply_drop_featured, %i_EarnSlotCount,
%d_%d, supply_drop_showoff, %d_%d_%d, supply_drop_version
```
开箱结果对象：
```
Version, ConsumeSupplyDrop, Action, ClientTx, SupplyDropID,
ConsumedItems{item_id,item_quantity,expire_date_time},
GrantedItems{item_quantity_delta,duration_unit,alternative_granted,alternative},
GrantedCurrencies{currency_id,amount,balance_before,balance_delta},
GrantedProducts{product_id,product_quantity}, ReplacedItems{reason}
```
（对应 UI 崩溃点 `SupplyDropView` 构造中断 —— 军火箱页面重叠。）

## 6. 每日/周挑战与活动（0x6a49d0 起）

```
rule_date_start, rule_date_end, sku_id, gp_reward, xp_reward,
match, game_mode, coop, rounds, play_list, consecutive_win, yes,
daily_begin, daily_end, valid_from, valid_until, min_level, max_level,
daily_id, daily_once, party, xp_scale, gp_scale, maps, modes,
dailyId, activity, month, day, year,
deathray/war/ffa/training/survival/zarena/story,
firstWin, player_levels, killnum, killway, headshot, knife,
match_requirement, win, use_method, use, carry, play_time, accumulated,
weapon_scale, match_result, cooperation_type, teammates, friends
```
命令面：`GetChallenges{ChallengeTypes, EndTimestamp, Balances}`、
`RerollChallenge{ChallengeType, SequenceID, ChallengeID, RerollCount}`、
`GetChallengesResponse` / `RerollChallengeResponse`。

★ 这就是旧的 `daily_begin/daily_end/daily_id/daily_once` 键的**权威出处**
（之前那篇 HANDOFF 的键名是对的，只有 `[%s]`/`%s=%s` 那部分是 OpenSSL 误记）。

---

# 附 2：SKU → Item 映射的一次尝试与**否证**（2026-10-07，负结果）

## 假设

`mkt_assets/client_catalog.csv` 是运行时从内存扒出的 107 条
「客户端点过的 SKU → 它自己的 Item」。这 107 个 SKU 与 exe 目录的 37615 个 Id
**零交集**。观察到一种可能：客户端 SKU 是 **exe 目录按 Id 排序后的下标**。

## 表面证据（当时看着很像）

* `exe_ids[sku]` 随 sku **单调不减 98/98**；
* 一组 `17272..17282` 的 exe Item 恰好是 2172..2177 连号，
  与内存 item 10032..10037 连号**同步**；
* memItem 排序后 exeItem 单调 85/98，Pearson r ≈ 0.87。

## ★ 否证（拿 ground truth 一测就崩）

用手册里**已实测入库成功**的 SKU 反查（这些是硬证据）：

```
sku 37251  期望 Item 29892   index 假设给 29512   ✗
sku 31184  期望 Item 22384   index 假设给 25235   ✗
sku 37116  期望 Item 29767   index 假设给 29452   ✗
sku 16096  期望 Item  7110   index 假设给 10501   ✗
sku 31774  期望 Item   122   index 假设给 25838   ✗
```

5/5 全部不符。说明"单调不减小"只是**两条都在粗排序的序列之间的伪相关**
（任何单调函数都会给出高相关），不是真映射。

**结论：SKU→Item 映射仍未解，且不能用排序/下标硬凑。** 不要再试这条。
要真解，只有拿到那 6 张 coMarketplace CSV（见附 1 第 2 节）或 hook 客户端
`marketplace.getskus` 的解析器。

> 教训补充：**相关系数高 ≠ 映射对**。凡是能影响"发什么物品给玩家"的结论，
> 必须用已实测入库的 SKU 做 ground-truth 反查，通过才算数。
