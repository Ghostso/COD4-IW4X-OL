# 268 探讨 · PVE playlist 补齐

## 一句话

把「哪些 playlist 是 PvE」从**别处抄来**改成**从客户端真正解析的表里推**，结果从 22 条（含 4 个空号）变成 37 条。

## 那个「22 条」是怎么来的

任务书给的 22 条，和 `_p171/fixed_kit_ver` 里的 23 条，本质是同一份 —— 大概率是最早照某个「分类印象」手列的：生存、丧尸、Evac。它的问题：

- **Evac 是"预留"**：明文里 `// playlist 7, 8, 82, 83, 84, 85 evac reserved` 和 `// playlist 9, 88, 89 reserved evac` **两行都被注释**。也就是说客户端根本不会请求 7/9。把它们当 PvE 是无害的（多判无害），但**不精确**。
- **17 / 91 干脆不存在**：整份表里搜不到 `playlist 17` / `playlist 91`。这是最该警惕的 —— 一个不存在的 id 进了集合，永远不会被命中，等于没写，却让人以为「覆盖了 Evac/Ambush」。
- **cat22/29/30 整族漏掉**：机械、丧尸、塔防 —— 名字一眼就是 PvE，却因为不在「生存/丧尸」的字面印象里被漏。

## 为什么用 `catinfo` 的 Group 而不是名字

文件里 `catinfo` 行自带 `Group` 列，注释原话：「Group will be used by the UI mostly to seperate PvP vs PvE」。这是**客户端自己的口径**，比「看英文名猜」硬。用它一filter，结果唯一、可复现。

## 与 156/157 的关系

- 156 卷：把镜像里 113 条 playlist 明文的 **id 全表** 列了出来（去重 113 个 id）。
- 157 卷：解中文名 + `category` 值域（1/2/3/8/9/13/14/15/16/23）+ 把 cat 名反推出来。
- 本卷：补上「**从 category → Group → PvP/PvE**」这一步，并吐槽：156 列了 id 但没分类，157 给了 category 但没给 group 映射的完整表 —— 两步之间正是「PvE 到底是哪几条」的答案所在。

## 没做的那件事

**地图没配。** `COOP_PLAYLIST_MAP` 只有 playlist 10。给 36 条配地图需要「每条 PvE playlist 客户端实际想加载哪张 coop 图」的证据，而现有的唯一实测（playlist 10 → `coop_take_mp_fav_tropical`）甚至不在 10 号的 map 列表里 —— 说明「会话地图 ≠ playlist 的第一张图」，**不能机械推**。

所以本卷停在「分支修对了」，把「地图一致」列为独立待办。若贸然照第一条 coop 图填，很可能又是「看起来修了、其实不连」。

## 一个副作用

改完后，playlist 112（Survival Normal Crash Tropical）这类从「靶场分支」变成「coop 分支」。靶场分支原本也是进不去的（160 卷），所以**不会有回退**；只是「进错了分支」变「进了对分支但图可能不对」。
