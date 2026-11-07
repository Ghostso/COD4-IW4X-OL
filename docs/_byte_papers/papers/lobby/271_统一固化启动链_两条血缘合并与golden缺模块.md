# 271 · 统一固化启动链：两条血缘合并 + 发现 golden 长期缺模块（商城空页真根因）

> 卷次：271（2026-11-03，四条 agent 线收口后的整合卷）
> 触发：用户指示「复制整条固化启动链进行统一修复」
> 产出：`CHAIN_UNIFIED_20261103\`（47.4 MB，自洽可运行链）

---

## §0 结论

1. **★★★★★ 本轮两个修复 agent 干在了不同血缘上**：房间修复在**血统 B**（golden 派生），大厅修复在**血统 A**（`REF_LOBBY_KIT`，10-07 旧快照）。**两者的改动无法直接拼接** —— 这正是"统一修复"要解决的核心问题。
2. **★★★★★ 受保护基线与实跑 kit 已完全脱钩**：完整性校验查 `REF_LOBBY_KIT`，而运行链取 `CODOL_VERIFIED_GOLDEN_20261019`。**校验一直在校验一套没在跑的代码。**
3. **★★★★★ golden 长期缺 `market_skus.py`，导致商城 SKU 页必然回空页** —— 这是 231/253 定的「回空页 ⇒ `state=2` ⇒ 商城/仓库永空」根因，**修复做了却从未进到运行链**。
4. **★★★★ 已构建并验证统一链** `CHAIN_UNIFIED_20261103\`：只新增 3 个文件、改动 2 个文件，其余与 golden 逐字节一致。
5. **★★★ 磁盘告警**：D 盘一度 **0 字节可用**（备份 `REF_LOBBY_KIT` 时它含 128 GB 内存 dump）。

---

## §1 ★★★★★ 两条血缘

按 `lobby_server.py` 的 mtime + sha 排序：

| 时间 | 位置 | sha / 大小 | 血统 |
|---|---|---|---|
| 10-07 18:08 | `REF_LOBBY_KIT` | `d7eeb456` 76410 | **A 根** |
| 10-27 21:04 | `CODOL_VERIFIED_GOLDEN` | `ff473204` 88162 | **B 根** |
| 11-02 02:51 | `_p172/backup_before_r2` | `164f69a6` 91794 | B |
| 11-02 15:09 | `_p171/fixed_kit_ver` | `b93ea69a` 94971 | B |
| 11-02 23:18 | **MRKFIX** | `26a5a194` 95035 | B |
| 11-03 **13:02** | **ROOMFIX** | `7d17b7bd` 96934 | **B 顶** |
| 11-03 **12:56** | **LOBBYFIX** | `1ce3990f` **78066** | ❌ **A**（76410 + PVE 块） |

**判据**：LOBBYFIX 相对 `REF_LOBBY_KIT` 的 `difflib` 统一差异**只有 1 个 hunk、共 29 行**，全部在 `PVE_PLAYLIST_IDS`。78066 − 76410 = 1656 B ≈ 该 hunk。**⇒ LOBBYFIX 的底座是 A。**

★ 这不是 agent 的错 —— 是**我给它的提示里把「受保护资产 `REF_LOBBY_KIT` 只读」和「复制 kit」写得太近**，它就把 REF 当成了复制源。**但由此暴露的真问题更有价值：链上没有唯一可信的 kit 来源。**

### 1.1 两条血缘的 PVE 列表

| 来源 | 元素数 | 备注 |
|---|---|---|
| GOLDEN / REF | **1**（`{10}`） | 未修 |
| `_p171` / MRKFIX / ROOMFIX | 23 | **含 4 个不存在的 id `{7,9,17,91}`** |
| **LOBBYFIX** | **37** | 权威版（依客户端真正解析的 `.info` → `.arena`） |

集合差（LOBBYFIX vs MRKFIX/ROOMFIX）= 仅 LOBBYFIX 有 18 个、仅该套有 `{7,9,17,91}`。

---

## §2 ★★★★★ 受保护基线与实跑 kit 脱钩

```python
# run_codol_001\run_frozen_chain_once.py
DEFAULT_KIT     = ROOT / "CODOL_VERIFIED_GOLDEN_20261019"   # ← 实际跑这套
PROTECTED_ROOT  = ROOT / "REF_LOBBY_KIT"                     # ← 校验查这套
```

`verify_protected_baseline()` 只比对 `REF_LOBBY_KIT` 的 6 个 launch_core 文件与 `_golden_hashes.json`。
我实测：**该检查全绿**（8/9 条目与 REF 实际一致，唯一不符的是 `marketplace_store.py`：清单记 `28b4a1be`/46226 B，实际 `e44358f0`/50022 B）。

而实跑的 golden 里：`lobby_server.py` = `ff473204`（≠ 清单的 `d7eeb456`）、`nt10.py` = `6f1196e6`（≠ `05863ebafc`）、`battle_server.py` = `98437fbb`（≠ `71bb7beb`）。

**⇒ 基线完整性检查通过，但它证明的是「一套没在跑的代码没被改」。**

---

## §3 ★★★★★ golden 缺 `market_skus.py` = 商城空页真根因

golden 的 `lobby_server.py:253`：

```python
try:    import market_skus
except ... :
    market_skus = None
    print("-- [market] market_skus 不可用(%r) -> 商城目录对话回空页" % (_e,))
```

**而 golden 目录里没有 `market_skus.py`。** ⇒ 从 golden 跑，`import` 必然失败 ⇒ `market_skus = None` ⇒ **商城 SKU 目录回空页**。

对账 231 卷（`codol-marketplace-empty-page-is-root-cause`）：
> 三个响应回调同一判据 `cmp byte [reply+5],0` ⇒ `==0` 就 `mov [0x82C4A88],2`
> ⇒ **服务端"刻意回空页"正是商城/仓库全空的根因**。

**⇒ 231 卷描述的"服务端刻意回空页"在运行链上的**真实来源**不是"某个分支被写死"，而是**模块缺失导致的必然降级**。** 247/268 修好了 `market_skus.py` 的 19 字段，但那个文件**从未被放进 golden**。

`run_frozen_chain_once.py` 的 `CORE` 白名单**列了** `market_skus.py`（第 58 行），但复制循环是
`if (kit / n).is_file(): copy` —— **缺文件被静默跳过**，日志里不留一行。

---

## §4 统一链的构建与验证

### 4.1 组装规则

```
CHAIN_UNIFIED_20261103\
  CODOL_VERIFIED_GOLDEN_20261019\      <- golden 底座(591 文件, 含全部数据目录)
      lobby_server.py   <- ROOMFIX(血统B顶)  + PVE 37 条补丁
      codol_crypto.py   <- ROOMFIX (R20 41位 / R21 1位头)
      market_skus.py    <- LOBBYFIX (19 字段)
      _sku_schema_as.py <- MRKFIX
      market_sku_probe.py <- MRKFIX (含 .tested_ok)
  REF_LOBBY_KIT\                        <- 仅 launch_core + 两个 flag + 重建的清单
  run_codol_001\run_frozen_chain_once.py
  MIGRATION_MANIFEST.json
```

### 4.2 与 golden 的差异清单（全量对账）

| 类型 | 文件 |
|---|---|
| **新增 3** | `market_skus.py` / `_sku_schema_as.py` / `market_sku_probe.py` |
| **改动 2** | `codol_crypto.py`（`e836c63a` 42853 → `02f762ff` 46945）、`lobby_server.py`（`ff473204` 88162 → `ad6a3ada` 97687） |
| **删除 0** | — |

### 4.3 验证结果

| 项 | 结果 |
|---|---|
| `--verify-only`（受保护基线） | **OK, exit=0** |
| `py_compile` 全部 .py | **0 错误** |
| `PVE_PLAYLIST_IDS` | **37 元素，无 `{7,9,17,91}`** |
| `import market_skus` | **OK，6/6 API 齐备** |
| `_sku_schema_as.SKU_AS_FIELDS` | **19 字段** |
| 数据目录 | 5/5 齐备（`publisher_files` 34 / `mkt_assets` 83 / `sku_arrays` 209 / `player_profiles` 11 / `user_files` 1） |
| 总体积 | **47.4 MB** |

**运行方式**（本体游戏目录只读引用，**不建 junction** —— 避免日后 `rmtree` 顺着链接删到 24.7 GB 本体）：

```powershell
python -I CHAIN_UNIFIED_20261103\run_codol_001\run_frozen_chain_once.py `
    --verify-only `
    --game-root "D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
```

---

## §5 ★★★ 磁盘事件（必须记住）

首次"全量备份两个受保护目录"时 **D 盘被写爆（0 字节可用）**。

- 原因：`REF_LOBBY_KIT` = **178,162 文件 / 128 GB**，其中 `mem_linear_20261007_134406` 一个子目录就 **40 GB**，`mem_marketplace` 14 GB。它不是"链"，是**内存 dump 归档**。
- 处置：删除我自己的这个半成品备份（22.35 GB，创建于几分钟前），D 盘恢复 22.36 GB。
- ⚠ **未备份成功**。若要真正备份受保护资产，**必须只备份 launch_core 那十来个文件**，不能整目录 copytree。
- 各盘余量：C 17.3 / D 22.4 / **E 284.0** / F 16.8 / G 126.5 GB。

---

## §6 边界总账

| # | 项 | 状态 |
|---|---|---|
| 1 | 统一链可运行（静态） | ✅ 验证通过（**未启动客户端**） |
| 2 | 受保护资产 | ✅ **一字未动**（只在新建目录里组装） |
| 3 | `REF_LOBBY_KIT` 整目录备份 | ❌ **未完成**（磁盘不足）；改为"只镜像 launch_core" |
| 4 | `COOP_PLAYLIST_MAP` 硬编码 dict 残余 | ❌ 未修（T2 残余，需真实抓包） |
| 5 | R22 Manifold `type` 0 vs 1 | ❌ 静态不可达 |
| 6 | `battle_security_key` KDF 公式不一致（163 卷） | ❌ 未修 ⇒ **仍不足以进战斗服** |
| 7 | 实机 | 按用户指示**暂不实机** |

---

## §7 复现命令

```powershell
python -I _rev_analysis/_p253/d4_lineage.py         # 血缘排序
python -I _rev_analysis/_p253/d6_pve_compare.py     # PVE 列表比对
python -I _rev_analysis/_p253/d7_build_chain.py     # 构建统一链
python -I _rev_analysis/_p253/d8_verify_chain.py    # PVE/语法/导入验证
python -I _rev_analysis/_p253/d9_final_check.py     # 差异清单 + 迁移 manifest
```

---

## §8 方法论

1. **★★★★★ 「受保护」和「在跑」是两件事。** 一个措辞严谨的完整性检查，可以长期绿色地保护一套没人执行的代码。**校验对象必须等于执行对象。**
2. **★★★★★ 缺文件 + `if is_file()` 白名单 = 静默降级。** `CORE` 列了它、复制循环跳过它、日志无一字。程序**照样能跑**，只是行为悄悄退化成"安全兜底"。
3. **★★★★ 并行分线必须先钉死「唯一复制源」。** 我给 agent 的提示里"只读的 REF"和"复制 kit"挨得太近 ⇒ 两个 agent 选了不同的源 ⇒ 改动落在不同血缘。
4. **★★★ 备份前先量体积。** `copytree` 一个 128 GB 的目录把磁盘写爆，代价是我唯一的全量备份机会。
