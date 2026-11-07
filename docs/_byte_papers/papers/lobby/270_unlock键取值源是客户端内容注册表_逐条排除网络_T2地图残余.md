# 270 · T1 补完：unlock 键（`loadout4enable`/`badge_unlock_*`）取值源 = **客户端内容注册表**，逐条排除网络；+ T2 残余 `COOP_PLAYLIST_MAP`

> 卷次：270（LOBBYFIX 修复线 · T1 补完 + T2 残余）
> run：`run_codol_001\runs\LOBBYFIX_20261103_124345`
> 承接：`267`（T1 定案）/`268`（T2）/`249`/`250`/`252`/`253`
> 性质：独立反汇编（`client_image_20261027.bin`，**已验证是运行时 dump**）+ 服务端源码核对

---

## §0 结论

1. **★★★★★ 镜像确证为「运行时 dump」**：`[0x84ABB38]=60027`、`[0x84ABB3C]=60028`、`[0x84ABB40]=60216`、owned count=32、徽章表 `0x8269B18` 已填好 —— 这些**只有跑起来才会有的值**都在镜像里。
2. **★★★★★ 那 4 个值的写入链只有一条**：
   `[0x84ABB38]` ← `0x80A4C0` = `decode(0x660B00("loadout4enable"))`（唯一写点，全镜像穷举）。
   `0x660B00` = **客户端内存里的「内容/unlock 名→item id」注册表**（`[0x779583C]`，堆，步进 0x28，名@+8，≈26.7k 槽）。
3. **★★★★ 逐条排除**（见 §3）：CSV 资产 / dvar 注册表 / configstring / playlist / 80-203 库存 / 155 卷 25KB 配置块 / **lobby 服务的全部 publisher 文件** / **lobby_server.py 自身** —— **没有一条能把 `loadout4enable` 写成 60027**。
4. **★★★ 残留（诚实）**：`[0x779583C]` 这张注册表**自身的填充者没找到**（无 imm32 写其基址；bucket 常量 `0x1387` 只出现在查找函数里）。⇒ 不能 100% 断言「配置子系统与网络完全无关」；但**对 lobby 而言没有任何已证的可达通路**。
5. **★★★ T2 残余**：`COOP_PLAYLIST_MAP` 是 `codol_crypto.py` 里的**硬编码 dict，无外部注册源**；可补齐的**数据**已抽出（§6），但**规则未被证实**（唯一实测锚点与 playlist 自身的图不符）⇒ **不猜、不自动填**，给数据与判据。

---

## §1 镜像 = 运行时 dump（先钉死这个前提）

| 全局 | 镜像值 | 含义 |
|---|---|---|
| `[0x84ABB38]` | `0xEA7B` = **60027** | 4 号背包解锁 item（`0x80A4C0` 从 `loadout4enable` 解码） |
| `[0x84ABB3C]` | `0xEA7C` = **60028** | 5 号背包解锁 item |
| `[0x84ABB40]` | `0xEB38` = 60216 | supply_drop_list[0] |
| `[0x84ABB4C]` | 32 | 已拥有表计数 |
| `0x8269B18` idx1/2 | 解码 = **60220 / 60221** | 徽章槽 item |
| `0x8269FC8` | 已填 32 条 | 已拥有表 |

★ 解码式 `rol32(A^B^[0xE4DD90],8)` 用 `[0xE4DD90]=0x74BDDE03` **校验通过**（idx1: `0x38015688^0x70BC8860^0x74BDDE03` → rol8 → 60220），⇒ 镜像的 VA 映射与种子都正确，值是真的。

---

## §2 唯一写入链

```
0x80A4C0  push "loadout4enable" ; call 0x660B00
          test eax,eax / je → eax=0 (查不到就是 0)
          非空 → cx=[eax] ; xor cx,[0xE5737C] ; xor cx,ax ; rol cx,4 ; eax=movzx cx
0x80A4EE  mov [0x84ABB38], eax          ; ★ 全镜像唯一写点
0x80A4F3  push "loadout5enable" ; call 0x660B00 ; [0x84ABB3C]=eax
```

穷举：`[0x84ABB38]` 的 5 处引用里 **只有 1 处是写**（`0x80A4EE`，前缀 `a3`）；`[0x84ABB3C]` 同理（`0x80A513`/`0x80A51B`）。其余 4 处是读（`0x7D7470`/`0x7DBB60`/`0x80A530`/`0x5E57A5`）。

⇒ **要改 4/5 号背包的解锁 item，唯一入口就是 `0x660B00` 的那张注册表。**

---

## §3 `0x660B00` 是什么 + 逐条排除

### 3.1 `0x660B00` = 客户端内存注册表（非 dvar、非 configstring）

- 表基址 `[0x779583C]` 指向**堆**（dump 里 = `0x60941584`，超出镜像 VA 范围 ⇒ 堆未进镜像）。
- 条目：步进 0x28，`[+8]`=名字指针，`[+0]`=值；查找 = `hash(名,[0x660CE0])`→bucket→逐条 strcmp。
- **命名空间**（51 个直接 `push` 名字的调用点）：`loadout4enable/5enable`、`badge_unlock_*`、`supply_basic/advanced/limited`、`cha_*`(角色)、`heg_/fja_/fpa_/han_/ves_/elp_/eye_`(外观)、`pcb_/pci_/pct_/pcn_default`(名片默认)、`uav`/`predator_missile`/`helicopter`(连杀)、`emp`/`armor_locker`/`umbrella_system`(装备)、`defaultknife_mp`/`m4t2_mp`(武器)、`token`、`specialty_siderollingexpert`。
  ⇒ 这是一张 **「游戏内容/unlock 名 → item id」表**。
- **它 ≠ dvar 注册表**：dvar 查表是 `0x76F190`（表 `[0x80F8E30]`，名@+0，case-insensitive），dvar 注册是 `0x770940`。两张表布局不同。
- **它 ≠ ScriptClientData(NCS)**：NCS 读 `mp/scriptClientData.csv`（`0x6624E0`）→ 建 `ncs_<domain>_<name>` dvar（`0x661A30` 的 `ncs_%s_%s`），写 `[0x77e1768]`，不是 `[0x779583C]`。

### 3.2 逐条排除（协调者列出的通道）

| # | 通道 | 能否写 `loadout4enable`→60027 | 证据 |
|---|---|---|---|
| 1 | CSV 资产 `coStartingLoadoutSetting.csv`/`scriptClientData.csv` | ❌ | 经 `0x76B7A0→0x49CF30` 资产装载；**不是 publisher 文件**（`manifest.json` 只列 `.info`；kit 里也没有这两个 CSV）；它们提供**名字**，值仍来自 `0x660B00` |
| 2 | dvar 注册表 | ❌ | 是 `0x76F190`/`[0x80F8E30]`，与 `loadout4enable` 读的 `[0x779583C]` **不是同一张** |
| 3 | configstring | ❌（未找到） | 全镜像无 `ConfigString` setter 写该表；`ConfigString` 命中是遥测名 `dNetConfigStringMismatch` |
| 4 | playlist 明文 | ❌ | playlist 只含 map/gametype/rule，无 item-id |
| 5 | 服务端 80/203 库存 | ❌ | 267 卷已证：库存不喂已拥有表（反例 item 121） |
| 6 | 155 卷 25KB 配置块（80 section） | ❌ | 该块内 `loadout`=0、`badge`=0、`unlock`=0 |
| 7 | **lobby 服务的 publisher 文件** | ❌ | 逐文件（raw+zlib）扫：无一含 `loadout4enable`/`badge_unlock`（`tlogconfig.info` 的 "loadout" 是遥测字段名） |
| 8 | **`lobby_server.py` 自身** | ❌ | 源码内无 `dvar`/`configstring`/`post_options` 任何字样 ⇒ 大厅不发送任何配置 |

### 3.3 残留（诚实边界）

`[0x779583C]` 这张表**本身**的填充者**没找到**：全镜像无 `mov [0x779583C],reg`；bucket 常量 `0x1387` 只出现在查找函数；无 `Dvar_Set*`/`Dvar_Register*` 字符串绑定（只有 `Dvar_Get*`）。

**⇒ 两条并存的判断：**
- **对 lobby**：没有任何已证的可达通路（§3.2 全排除 + 大厅不发配置）。
- **一般性地**：客户端**确有**网络配置机制的痕迹（`ncs_network_dvar`、`dNetConfigStringMismatch`、`sv_post_options` 服务器命令），所以我**不能**断言「配置子系统与网络绝对无关」。这是与 267 卷「装配不读库存」并列的第二条边界。

---

## §4 触发顺序

`0x80A630` 的第一入口 `0x80A360`（←`0x4FE120`←`0x4FE220`）带**单次初始化标志** `[0x84abb2f]`，且门控在 **`code_post_gfx_mp` 核心 UI 资产已加载**（`0x49f180`）之后。⇒ 它建表发生在**启动/UI 资源装载**阶段。

第二入口 `0x80A400`（←`0x5BFCE0`←`0x5C0310`）无单次标志，在 `clientState [0x76446B0]` 达 5/8 时触发（可能在大厅）。

★ 但**两个入口读的都是同一批输入**（内容注册表 + CSV + 硬编码名），**都不读库存**。所以即使第二入口在连上大厅后重跑，也不会因为「大厅发了什么」而改变（除非注册表被改 —— §3.3 的残留）。

---

## §5 对 T1 定案的净影响

- **操作结论不变**：服务端改 SKU→Item（发 60027/60028）**不能**解锁 4/5 号背包（267 卷已证）。**T4 仍不改。**
- **协调者的假设检验**：若「unlock 键可由网络设」成立 ⇒ 存在大厅侧修法。**本轮结论：对 lobby 未找到任何通路**（§3.2）；大厅侧修法**无证据支撑**，不应尝试。
- **唯一仍开**：`[0x779583C]` 的填充者（建议另立一卷，专门找它的 loader / 是否读某配置文件）。

---

## §6 T2 残余：`COOP_PLAYLIST_MAP`

1. **注册来源 = 硬编码 dict**（`codol_crypto.COOP_PLAYLIST_MAP`），**没有任何外部文件/表**注册它。当前只有 `10: "coop_take_mp_fav_tropical"`。另有 `coop_map.txt`（单值全局覆盖）。
2. **可补齐的数据**（从 served `.info` 抽每个 PvE playlist 自己的图）：

| playlist | 图（首） | playlist | 图（首） |
|---|---|---|---|
| 10 | coop_survival_mp_cross_fire | 116 | coop_survival_mp_crash_tropical |
| 12 | coop_survival_mp_cross_fire | 117 | coop_survival_mp_fav_tropical |
| 19 | zm_asylum_sh | 130 | za_coliseum |
| 21 | zm_asylum_sh | 135/140/143 | za_island |
| 69 | za_coliseum | 147/151 | mp_crash_tropical |
| 86/90 | coop_survival_mp_cross_fire | 155 | coop_survival_mp_cross_fire |
| 94/98 | zm_asylum_sh | 157 | za_coliseum |
| 95/99 | zm_sumpf_sh | 175/185 | mp_village |
| 109 | coop_survival_mp_cross_fire | 191/193 | zm_factory_sh |
| 112 | coop_survival_mp_crash_tropical | 205 | mp_deathmarch_chap1 |
| 113 | coop_survival_mp_fav_tropical | 229 | mp_deathmarch_chap3_a |
| 230 | mp_deathmarch_chap1_b | 231 | mp_deathmarch_chap1_c |
| 232 | mp_deathmarch_chap1_d | 233 | mp_deathmarch_chap3_b |
| 245 | mp_deathmarch_chap4_a | 246 | mp_deathmarch_chap4_b |
| 251 | mp_battlecity_mountains_td | | |

3. **为什么仍不自动填**：唯一实测锚点是 `playlist 10 → coop_take_mp_fav_tropical`，而 **`coop_take_*` 在整份 playlist 明文里 0 命中**，且 playlist 10 自己的图全是 `coop_survival_*`。⇒ **「会话地图 = 该 playlist 的图」这条规则未被证实**（甚至被唯一锚点反证）。照 §6.2 硬填 = **猜**。
4. **结论**：给出数据 + 规则未证；**不填**。下一步应抓一条**生存 playlist** 的 mmstart（真机），看它到底要哪张 `coop_survival_*`，才能把规则钉死。**在钉死前填 36 条，比不填更容易误导**（本次协调者原则）。

---

## §7 复现命令

```powershell
cd run_codol_001\runs\LOBBYFIX_20261103_124345
python -I t1k_globals.py    # 镜像=运行时 dump：60027/60220 等
python -I t1l_a4c0.py       # 0x80A4C0 唯一写入链
python -I t1m_refs.py       # 0xDE6CCC 引用 + 注册表指针
python -I t1o_config.py     # 25KB 配置块 80 section + loadout/badge/unlock=0
python -I t1x_76f190.py     # dvar 注册表 0x76F190（≠0x660B00 那张）
python -I t1y_names.py      # 0x660B00 的 51 个名字（内容/unlock 命名空间）
python -I t1z_pubscan.py    # 逐 publisher 文件扫 unlock 键（全无）
python -I t2c_coopmap.py    # COOP_PLAYLIST_MAP 硬编码 + 各 PvE playlist 的图
```

---

## §8 方法论

1. **★★★★★ 「运行时值」要先证镜像是不是 dump。** `[0xBSS 全局]=非零` 一条即证（这些是 .bss，静态 PE 里为 0）。这决定了「谁写的」是一个真问题。
2. **★★★★ 「唯一写点」是排除法的地基。** `[0x84ABB38]` 只有 1 个写点 ⇒ 只要追它，就穷尽了所有可能的改法。
3. **★★★★ 排除要「逐通道 × 逐证据」，不能给结论。** 8 条通道各配一条可复现的证据（文件扫描 / 函数布局 / 反例）。
4. **★★★ 名字的命名空间能定性系统。** 51 个名字全是「内容/unlock 键」⇒ 那是内容表，不是 dvar、不是 configstring。
5. **★★★ 找不到填充者要说「找不到」，并给下一步。** 残留 `[0x779583C]` 的 loader 是唯一未闭合项，已写成可独立核验的任务。
6. **★★ 「修一半更误导」的应用**：T2 的地图**数据齐了但规则未证** ⇒ 宁可不填 + 给判据，也不猜 36 条。
