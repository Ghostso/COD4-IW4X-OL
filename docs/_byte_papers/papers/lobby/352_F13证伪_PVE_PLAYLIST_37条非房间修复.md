# 352 · F13 证伪：`PVE_PLAYLIST_IDS` 从 {10} 改成 37 条是不是「正确的修复」

> 卷次：352（room64 · F13 证伪路）
> 脚本：`_rev_analysis\_f64_13\`
> 待证命题：**「`PVE_PLAYLIST_IDS` 从 `{10}` 改成 37 条是正确的修复」**
> 性质：独立解析（不复用 268 卷结果）+ 当前链源码/日志复核

---

## §0 判定（一句话）

**主判定：这个改法与房间问题无关。** 而且它连「一个有效的修复」都算不上 —— 在当前实跑的
统一链（`CHAIN_UNIFIED_20261103`）里 `PVE_PLAYLIST_IDS` 是**死代码**（只被赋值、从不被读）。
37 条作为「PvE **类别**集合」是**正确**的（与 `.info` 明文 `Group==0` 逐条一致，missing=0/extra=0），
但把它当成「修复」是三重错位：

| 命题分解 | 结论 | 依据 |
|---|---|---|
| 37 这个集合 = 真实 PvE 类别集？ | **是（正确）** | 独立解析 `.arena`：Group0 类别 {20,21,22,23,24,25,26,28,29,30}，37 块命中；missing=[] extra=[] |
| 改它有修复效果？ | **否（死代码）** | 当前 `lobby_server.py` 全文 `is_pve` 出现 **0** 次；AST 里 `PVE_PLAYLIST_IDS` 只有 `Store@L320`，无任何 `Load` |
| 与房间故障有关？ | **否** | 实跑日志无 `21/5`；房间失败点在 `21/12`/购买/黑名单线（T1–T4/267），playlist 集不参与 |

⇒ 对三条候选的落点：**「这个改法与房间问题无关」**（主）。附：「37 条作为 PvE 分类不错，但作为 coop 路由集过宽，只有 10 条是 coop gametype；作为当前链修复是死代码」。

---

## §1 独立解析：真实 PvE 集合 = 37 条

**来源（本地第一权威）**：`CODOL_VERIFIED_GOLDEN_20261019\publisher_files\mp_playlists_shipRetail_1.0.0.info`
- 磁盘 21,412 B，头 `78 9C`=zlib；解压得 **112,664 B / 3975 行** `.arena` 明文（存 `_f64_13\playlists_decompressed.arena`）。

**判据链**（全部机读，脚本 `parse_playlists.py` / `compare_and_resolver.py`）：

1. `catinfo <id> <group>` 共 **25** 行（L123–152）。文件注释 L119 原文：
   `// Group will be used by the UI mostly to seperate PvP vs PvE` —— **Group 列就是官方 PvP/PvE 口径**。
2. `Group==0` 的类别 = `{20,21,22,23,24,25,26,28,29,30}`（PvE）；`Group==1` 的 = `{1,2,3,4,5,7,8,9,10,11,12,13,14,15,16}`（PvP）。
3. 逐个 `playlist <id>` 块取 `category <c>`；`c ∈ PvE 类别` ⇒ 计入。全表 **123** 个 playlist 块。

**结果（37 条，按 category）**：

| cat | 英文名 | ids |
|---|---|---|
| 23 | Survival | 10,12,86,90,109,112,113,116,117,155 |
| 22 | Cyborgs | 19,21,94,95,98,99,191,193 |
| 20 | Zombie Arena（Super Zombie Battle） | 69,130,135,140,143,157 |
| 26 | Zombie Survival | 147,151 |
| 28 | ZS Champions | 175,185 |
| 29 | Zombie Hunter | 205,229,230,231,232,233,245,246 |
| 30 | Tower Defence | 251 |

= **6+8+10+2+2+8+1 = 37**。

---

## §2 与服务端 37 条逐项对比

服务端 `REF_LOBBY_KIT\lobby_server.py:320–328`（与 golden 同哈希 `5652EC58…`）。机读比对：

```
REAL  = [10,12,19,21,69,86,90,94,95,98,99,109,112,113,116,117,130,135,140,143,
         147,151,155,157,175,185,191,193,205,229,230,231,232,233,245,246,251]
SERVER= 同上（逐元素）
missing_in_server = []      extra_in_server = []      EQUAL = True
```

**多/少 = 0/0，完全相等。** 所以若只看「集合对不对」，37 条是对的 —— 268 卷 §2 的推导**稳健**，本次独立复算一致。

---

## §3 判据一：37 条作为「修复」是死代码（当前链）

这是命题最致命的错位。**当前实跑的统一链根本不读这个集合。**

- 文本层：`REF_LOBBY_KIT\lobby_server.py` 全文搜 `is_pve` = **0 次**（AST `deadcode_check.py` 复验：`PVE_PLAYLIST_IDS` 只有 `Store` 节点 @L320，无 `Load`；`PVE_ADDRESS67_FLAG` 同样只被赋值 @L329）。
- 分支被换成**解析器**：当前 `21/5` 处理（L865–926）走 `_PlaylistResolver.resolve()`（L376–394）+ `cc.build_mission_session_object(True, ..., game_type_override=0x1000007, address67=True)`。它按每张地图的 gametype 字面（`coop`/`zm`/…）决定，并一律用 `0x1000007`；**不引用 `PVE_PLAYLIST_IDS`**。
- 因此 `{10}`→`37` 在当前链里**不改变任何一行实际执行路径**：改前改后行为字节级相同。

**谱系还原**（谁曾经读它）：37 条是在 `run_codol_001\runs\LOBBYFIX_20261103_124345\kit\lobby_server.py` 落地，那里 L636 确有 `is_pve = _pl in PVE_PLAYLIST_IDS`。当前统一链把该分支整体换成 resolver 后，`is_pve` 与集合一起沦为死代码。⇒ 「补齐 37 条」是一个**在自己已被删除的分支上做的修复**。

---

## §4 判据二：即使按 LOBBYFIX 谱系（is_pve 仍活），37 条也过宽、会引入新错位

在 `is_pve` 仍生效的谱系里，`is_pve→ coop mission session (GameType=0x1000003, MaxPlayers=4)`，`else→ 靶场 session (0x1000007, MaxPlayers=1)`。问题在于「PvE 类别」≠「coop gametype」。

**gametype 普查（`gametype_census.py`，按每个 playlist 的 `map,gametype,1` 行去重）**：

| gametype | playlist 数 | 覆盖面 |
|---|---|---|
| `coop` | **10** | cat23 全部（10,12,86,90,109,112,113,116,117,155） |
| `zm` | 8 | cat22 Cyborgs |
| `zhunt` | 8 | cat29 Zombie Hunter |
| `zarena` | 6 | cat20 Zombie Arena |
| `zsurv` | 2 | cat26 |
| `zchamp` | 2 | cat28 |
| `td` | 1 | cat30 |

⇒ **37 条里只有 10 条（全是 cat23）是 `coop` gametype；另外 27 条是 `zm/zarena/zsurv/zchamp/zhunt/td`。** 把它们一起推进「coop mission session（gametype 0x1000003）」等于给丧尸/机械/塔防模式回了一个它们本不使用的会话形状 —— 这是**新引入的类别/分支错位**（268 §6 已承认「只保证进对分支、不保证进得去」，但未点破「分类对≠gametype 对」）。

### §4.1 与 PvP 误判的关系（回答任务第 3 问）

- **不会把 PvP 误判成 PvE**：37 条精确 = Group0，PvP 类别（Group1）一个都不在集合里（普查：PvP 侧唯一 gametype=coop 的是 playlist 198「靶场」，且它不在 37 内）。所以「误把 PvP 当 PvE ⇒ 房间/匹配异常」这条路**不成立**。
- **会（在 is_pve 活着的谱系）把 27 条非 coop 的 PvE 误送 coop mission 分支**：这不是房间/匹配故障，是「会话地图/GameType 与所选模式不匹配」，会导致这些模式更进不去，而不是把房间搞坏。

---

## §5 判据三：37 条里有 11 条在 `*** CURRENTLY UNUSED PVE ***` 段

`.arena` 分节（`playlist 175` 起，L3289）：

```
// *** CURRENTLY UNUSED PVE ***        ← L3290
   playlist 150(Clash-TDM) 152 153      (PvP)
   playlist 175 185 205 230 231 232 229 233 245 246 251   ← 11 条在「未启用 PvE」段
L3699 // *** BattleCity Playlists ***
```

即 37 条中有 **11 条（175,185,205,229,230,231,232,233,245,246,251）位于官方标注的「未启用 PvE」区**。把它们标成「当前 PvE」在语义上不精确（虽不致房间故障，但「正确修复」一词过强）。

另：reserved id（`7,8,82,83,84,85,9,88,89,24,25,26,61,62,163..173,91,92,93,17`）**没有一个落进 37 集合** —— 268 卷避免 phantom id 的做法是对的。

---

## §6 与房间故障的真实关系（回答任务第 3/4 问）

实跑 `CHAIN_UNIFIED_20261103\run_codol_001\runs\ONCE_20261103_151503\kit\lobby_srv.log`：

- `service=21` 只出现 `task=1`（createSession）与 `task=12`（updateSession 空应答，payload=288）。**全程没有 `21/5 findSessions`** ⇒ 上文所述 21/5 分支（不管 resolver 还是 is_pve）**在本轮根本没执行**。
- 房间不可用的现场是 `21/12` 空应答、以及本线之外的购买/黑名单（267 T1–T4）/dwRoom 出网等。playlist 集合不在这条因果链上。

⇒ 无论 37 条对错，**它都不是房间修复**。更换 `PVE_PLAYLIST_IDS` 不改变房间可用性。

---

## §7 顺带更正 268 卷 §5 的一处证据失误

268 §5 ①称「两份 publisher 文件（1.0.0 / release）解析结果逐条一致」。**该结论不成立**：
`mp_playlists_shipRetail_release.info`（262 B→解压 424 B）内容是**自述探针桩**：
`// This is not the recovered production playlist and has not passed client QA.`，`version 1`，仅 1 个 `playlist 1 category 0`。
它**不是**同源生产表，不能用来交叉校验 37 条。（不影响 37 集合本身结论，因 1.0.0 单份即可自证。）

---

## §8 结论（对照任务给的三选一）

| 候选 | 是否成立 | 说明 |
|---|---|---|
| 「37 条正确」 | **否（作为修复）** | 集合作为 PvE 类别对；但当前链死代码、语义过宽（27 条非 coop）、11 条在 unused 段 |
| 「37 条有错，正确的是 X」 | **部分** | 若目标是「coop 会话路由集」，正确的是**仅 cat23 的 10 条**（10,12,86,90,109,112,113,116,117,155）；但目标本身在当前链已被 resolver 取代 |
| **「这个改法与房间问题无关」** | **是（主判定）** | 21/5 未执行；房间失败在 21/12/购买/黑名单线；改常数对其零影响 |

**最终：`PVE_PLAYLIST_IDS` {10}→37 不是房间的正确修复 —— 它与房间问题无关，且在实跑链里是死代码；37 条仅作为「PvE 类别集合」正确，作为 coop 路由集合应为 10 条（cat23），其余 27 条 gametype 非 coop。**

---

## §9 复现

```powershell
$env:PYTHONIOENCODING="ascii"
python -I _rev_analysis\_f64_13\parse_playlists.py        # zlib->arena, catinfo group==0, 37 blocks
python -I _rev_analysis\_f64_13\compare_and_resolver.py   # missing/extra + resolver 模拟
python -I _rev_analysis\_f64_13\gametype_census.py        # gametype 分布：coop=10, 非coop=27
python -I _rev_analysis\_f64_13\deadcode_check.py         # AST: PVE_PLAYLIST_IDS 只 Store 无 Load
python -I _rev_analysis\_f64_13\check_release.py          # release.info = 424B 探针桩
```

## §10 方法论

1. **「集合对」≠「修复对」。** 要从「代码是否真的读它 / 分支是否真的执行」两处验证，否则在死代码上做正确数学=零修复。
2. **类别（PvE）不是 gametype（coop）。** 一个分类正确的集合，喂进按 gametype 分派的会话构造，会造出类别内、gametype 外的错位。
3. **日志先看「分支有没有跑」。** 实跑无 21/5，则 21/5 上的一切修补都与现场无关。
4. **交叉证据要看对象是不是同一种东西。** 拿 `release.info` 这个自述「非生产探针」去交叉校验，等于用错基准放大自信。
