# 268 · T2 落地：`PVE_PLAYLIST_IDS` 补齐到权威 37 条（更正 160 卷/任务书的 22 条清单）

> 卷次：268（LOBBYFIX 修复线 · T2）
> run：`run_codol_001\runs\LOBBYFIX_20261103_124345`
> 承接：`160`（PVE 硬缺陷）/`156`（113 条 playlist 明文）/`157`（playlist 中文名/category）
> **后续：`270` §6**（本卷 §6 的地图残余 `COOP_PLAYLIST_MAP` —— 270 已查：硬编码无外部源，数据齐但规则未证，故不填）
> 性质：本地明文直读 + 服务端源码改动 + 离线端到端验证

> ★★ **更正主对话给的清单**：主对话（承 160 卷转手）给的 22 条 PvE 清单**有误** —— 含 4 个**不存在**的 id（`7`/`9` = 明文里被注释的 evac "reserved"，`17`/`91` 整份表里根本没有），且**漏 18 条**（整个 cat22 + cat28 的 185 + cat29 + cat30）。本卷以客户端实际解析的 `.info` 明文为准，得 **37 条**。主对话已接受此更正。

---

## §0 结论

**★★★★★ `lobby_server.PVE_PLAYLIST_IDS` 从 `{10}` 补齐到权威 **37 条**。**

| # | 证据 | 强度 |
|---|---|---|
| ① | 客户端实际解析的 playlist 表 = `publisher_files/mp_playlists_shipRetail_1.0.0.info`（zlib → `.arena` 明文） | ★★★★★ |
| ② | 该文件 `catinfo <id> <group>`：Group 0 = PvE；PvE 类别 = {20,21,22,23,24,25,26,28,29,30} | ★★★★★ |
| ③ | 逐个 `playlist <id>` 块的 `category` 落 PvE 类别者 = **37 条**（6+8+10+2+2+8+1） | ★★★★★ |
| ④ | 两份 publisher 文件（1.0.0 / release）解析结果**逐条一致** | ★★★★ |

---

## §1 根因（160 卷）

`21/5 findSessions` 处理里：

```python
is_pve = _pl in PVE_PLAYLIST_IDS
objs = [cc.build_mission_session_object(not is_pve, playlist=_pl, ...)]
# is_pve  → coop mission session (GameType=0x1000003, MaxPlayers=4)
# else    → 靶场 session        (GameType=0x1000007, MaxPlayers=1, map=mp_firingrange)
```

原值 `{10}` 只覆盖 1 条 ⇒ 其余 PvE playlist（生存 112、丧尸 69、…）全落 else 分支，客户端拿到**靶场**会话 ⇒ **「选剧情/生存进不去」的真根因**。

---

## §2 权威推导（本地第一权威）

来源 = 客户端**实际解析**的那份表：`kit/publisher_files/mp_playlists_shipRetail_1.0.0.info`。
（文件名后缀 `.info`，内容是 **zlib 流**（头 `78 9C`）→ 解压得 `.arena` 明文；与镜像内嵌明文 `VA 0x33A4E2D..` 同源，156 卷已录 113 条。）

`.arena` 里两类关键行：

```
catinfo 23    0     0         ""   "生存"      "Survival"        ; ← 第 2 列 = Group: 1=PvP, 0=PvE
playlist 10
displayorder 10
category 23                                                     ; ← 该 playlist 的类别
```

**判据**：`Group==0` 的类别 = PvE 类别；playlist 的 `category` 属之 ⇒ PvE。

### 2.1 权威 PvE 集合（37 条）

| 类别 | 名（英文） | playlist ids |
|---|---|---|
| 23 | Survival | 10, 12, 86, 90, 109, 112, 113, 116, 117, 155 |
| 22 | Cyborgs | 19, 21, 94, 95, 98, 99, 191, 193 |
| 20 | Zombie Arena | 69, 130, 135, 140, 143, 157 |
| 26 | Zombie Survival | 147, 151 |
| 28 | ZS Champions | 175, 185 |
| 29 | Zombie Hunter | 205, 229, 230, 231, 232, 233, 245, 246 |
| 30 | Tower Defence | 251 |

**= 37 条。**（PvE 类别里的 21/24/25 无活动 playlist。）

---

## §3 更正 160 卷 / 任务书给的 22 条清单

任务书 / 160 卷给的那份清单：`cat23: 10/112/86/113/12/116/90/117/109/155`；`Evac: 7/9/17`；`91`；`cat20: 69/130/157/135/140/143`；`cat26: 151/147`；`175`（22 条）。它与权威集合的差异：

| 问题 | 具体 |
|---|---|
| **多 4 个不存在的 id** | `7`/`9` 在明文里是**被注释掉的 "evac reserved"**（`// playlist 7, 8, 82, 83, 84, 85 evac reserved`）；`17`/`91` 在整份表里**根本没有** |
| **漏 18 条** | 整个 cat22(Cyborgs 8 条)、cat28 的 185、cat29(Zombie Hunter 8 条)、cat30(251 1 条) |

★ 任务书自己说「不要照抄我给的这个列表，去 157 卷/镜像确认」—— 照做后得到的正是这 37 条。

★ **在修谱系也踩了同一个坑**：`_rev_analysis/_p171/fixed_kit_ver/lobby_server.py`（PVE 已展开为多行）用的正是那 23 条（= 上面 22 条的变体，含 7/9/17/91、漏 cat22/28/29/30）。**建议一致化到本卷的 37 条。**

---

## §4 修复

`kit/lobby_server.py`：

```diff
-PVE_PLAYLIST_IDS = {10}
+PVE_PLAYLIST_IDS = {
+    10, 112, 86, 113, 12, 116, 90, 117, 109, 155,   # cat23 Survival
+    19, 21, 94, 95, 98, 99, 191, 193,               # cat22 Cyborgs
+    69, 130, 135, 140, 143, 157,                    # cat20 Zombie Arena
+    147, 151,                                       # cat26 Zombie Survival
+    175, 185,                                       # cat28 ZS Champions
+    205, 229, 230, 231, 232, 233, 245, 246,         # cat29 Zombie Hunter
+    251,                                            # cat30 Tower Defence
+}
```

（附推导依据注释；`PVE_ADDRESS67_FLAG` 等其余逻辑不变。）

---

## §5 验证（离线）

| 检查 | 方法 | 结果 |
|---|---|---|
| 集合一致 | 从 served `.info` 重算 PvE 集合 vs 源码 AST 里的 `PVE_PLAYLIST_IDS` | **missing=[] extra=[]** |
| 路由 | 117 条 playlist 逐条判 `is_pve` | **37 PvE(coop) / 80 firing-range**，且 37 == 权威 PvE 集 |
| 抽样 | playlist 1/10/112/155/69/251 | 1→firing-range；其余→PVE(coop) |

复现：`python -I verify_lobbyfix.py`（ALL PASS 10/10）+ `python -I e2e_lobbyfix.py`（E2E OK）。

---

## §6 边界（必须说清）

1. **未实机。** 不启动客户端。
2. **map 路由是相邻的第二个缺口。** `codol_crypto.COOP_PLAYLIST_MAP` **只登记了 playlist 10**（`10: "coop_take_mp_fav_tropical"`）；其余 36 条 PvE playlist 的会话地图会退回 `MISSION_MAP_NORMAL="coop_training_mp_cargoship"`。注释明说「session 里的 map 必须与客户端实际要加载的一致，否则客户端不会去连战斗服」。
   ⇒ **本修复只保证「进了正确的分支（coop），不再进靶场分支」；不保证「地图一定对、一定能进」。**
   ⇒ **不猜地图**：每张 PvE playlist 该回哪张 coop 图，缺权威依据（playlist 10 的实测地图 `coop_take_mp_fav_tropical` 甚至不在 10 号的 map 列表里 ⇒ 会话地图不是「playlist 的第一张图」，不能机械推）。需另立任务追（客户端 mmstart 实测 / coop 任务注册表）。
3. **未逐一实测** 37 条 playlist 的客户端请求真的带这些 id（本轮只证明「若带则路由正确」）。

---

## §7 复现命令

```powershell
cd run_codol_001\runs\LOBBYFIX_20261103_124345
python -I t2b_pub.py          # 解 zlib 得 .arena；catinfo group==0 推导 37 条
python -I verify_lobbyfix.py  # T2 集合一致性
python -I e2e_lobbyfix.py     # 117 条路由
```

---

## §8 方法论

1. **★★★★★ 「权威清单」要从客户端**实际解析**的文件里推，不要用别人列好的表。** 任务书给的 22 条有 4 个不存在的 id、漏 18 条 —— 依赖它会把修复做成「假修」。
2. **★★★★ 判据在数据自身里。** `catinfo` 的 `Group` 列**就是** PvP/PvE 的官方口径（文件注释原话「Group will be used by the UI mostly to seperate PvP vs PvE」），不必按名字猜。
3. **★★★ 集合要对**两份**同源文件**做交叉（1.0.0 与 release 逐条一致），排除单份损坏。
4. **★★ 缺 id / 多 id 都要报。** 「只加不查」会把 phantom id（7/9/17/91）带进去，看着像 PvE、其实是空号。
5. **★★ 修了 A 不等于修了 B。** 路由分支（A）与地图一致（B）是两个缺口；只修 A 要明确说「B 仍未闭合」。
