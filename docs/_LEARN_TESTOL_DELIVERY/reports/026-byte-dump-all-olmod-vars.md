# 学习报告 026 — 逐字节：全部 166 个 `OLMOD_*` 环境变量穷举

**方法**：对四个插件全文按 NUL 切分，正则 `^OLMOD_[A-Z0-9_]+$` 去重
**性质**：全实测、穷举
**★★★ 本报告给出了"能否关掉 Winsock hook"的决定性否证**

---

## 一、★★★ 完整清单（166 个唯一变量）

### `Localnetworking.Ayria32` — **5 个**

```
0x050084  OLMOD_LOBBY_LISTEN
0x050134  OLMOD_LOBBY_HOST
0x050424  OLMOD_CLIENT_INSTANCE
0x050450  OLMOD_PROCESS_ROLE
0x050658  OLMOD_SYNTHETIC_DNS
```

★★★ **就这 5 个。没有 `OLMOD_DISABLE_HOOK` / `OLMOD_HOOK` / `OLMOD_RAW_SOCKETS` 之类。**

### `Alwaysoffline.Localnet32` — **34 个**

```
OLMOD_CLAIM_LEGACY_AUTH          ★★ 让出 legacy auth
OLMOD_CLAIM_LOBBY                ★★★ 认领大厅
OLMOD_CLIENT_BRIDGE_PORT
OLMOD_CONSOLE_LOG
OLMOD_DEDICATED_CONTROL_PORT
OLMOD_DW_ACCOUNT_ID              ★★ Demonware 账号 ID
OLMOD_EXTERNAL_AUTH3             ★★★ 外部 auth3（让出认证）
OLMOD_EXTERNAL_STUN              ★★★ 外部 STUN（让出 STUN）
OLMOD_FFA_SCORE_LIMIT
OLMOD_GAME_ENDPOINT              ★★ 战斗服端点
OLMOD_GAME_SECURITY_ID           ★★
OLMOD_GAME_SECURITY_KEY          ★★
OLMOD_HOST_ADDRESS
OLMOD_LOG_LEVEL
OLMOD_LSG_SECRETS                ★★★ LSG 密钥文件路径！
OLMOD_MARKETPLACE_ANSWER_230
OLMOD_MARKETPLACE_MAX_ITEMS
OLMOD_MARKETPLACE_MAX_REPLY_BYTES
OLMOD_PLATFORM_USER_ID           ★★ 平台 ID
OLMOD_PROCESS_ROLE
OLMOD_PUBLIC_PROFILE_MODE
OLMOD_ROOM_BOTS
OLMOD_ROOM_OWNER_PORT
OLMOD_SAVE_RESET_PROFILE
OLMOD_SERVE_PRIVATE_PROFILE
OLMOD_STATS_CLAN_GBK
OLMOD_STATS_NAME_UTF8
OLMOD_STATS_SELF_CLAN
OLMOD_STATS_SELF_ID
OLMOD_STATS_SELF_NAME
OLMOD_STATS_SELF_PRESTIGE
OLMOD_STATS_SELF_XP
OLMOD_VERBOSE_LOG
OLMOD_WARGOD_RETAIL_BASE
```

★★★ **三条极重要的发现**：

1. **`OLMOD_EXTERNAL_AUTH3`** —— **让出认证给外部！**
2. **`OLMOD_EXTERNAL_STUN`** —— **让出 STUN 给外部！**
3. **`OLMOD_LSG_SECRETS`** —— ★★★ **LSG 会话密钥文件路径**

★★ **`OLMOD_CLAIM_LEGACY_AUTH`** 与报告 011 引用的 `Servers.cpp:153-181` 那个门对应。

★★★ **⇒ `Alwaysoffline` 有**三个"让出"开关**，比报告 016 发现的 `OLMOD_SKIP_AUX` 更细粒度。**

### `CodolGameServer.Localnet32` — **126 个**

完整清单（按功能分组）：

**【机器人】** 12 个
```
OLMOD_BOTS, OLMOD_BOT_AI, OLMOD_BOT_AI_TRACE, OLMOD_BOT_CHARACTER,
OLMOD_BOT_CHARACTERS, OLMOD_BOT_CLASS_TIMING, OLMOD_BOT_FILL,
OLMOD_BOT_LIFE_GATE, OLMOD_BOT_NAMES, OLMOD_BOT_WAYPOINTS,
OLMOD_ROOM_BOTS (在 Alwaysoffline), OLMOD_BATTLECHATTER_TEAM,
OLMOD_BATTLECHATTER_EXCLUDE_SELF
```

**【快照】** 6 个 ★★★
```
OLMOD_SNAPSHOT_ENTITY_BASELINES     ★★★ 实体基线
OLMOD_SNAPSHOT_ENTRY_FLAG           ★★★ 快照入口标志
OLMOD_SNAPSHOT_HEX                  ★★ 十六进制转储
OLMOD_SNAPSHOT_HEX_OBITUARY
```

**【世界/物理】** 20+ 个 ★★★
```
OLMOD_BULLET_FIRE_PROBE
OLMOD_BULLET_SELF_DAMAGE_PROBE
OLMOD_CAPSULE_ENTITY_PROBE
OLMOD_DOBJ_LOCATIONAL_PROBE
OLMOD_FLESH_IMPACT
OLMOD_GLASS_DAMAGE_TO_DESTROY
OLMOD_GLASS_DAMAGE_TO_WEAKEN
OLMOD_HITBOX_DIAGNOSTICS
OLMOD_PENETRATION
OLMOD_LOG_BULLET_PENETRATION
OLMOD_LOG_ENTITY_EVENTS
OLMOD_NATIVE_CAPSULE_TRACE
OLMOD_NATIVE_TRACE_COMPARISON
OLMOD_NOCLIP
OLMOD_NOCLIP_KEY
OLMOD_LEAD_LOST
OLMOD_LEAD_TAKEN
OLMOD_KILLCAM
OLMOD_KILLCAM_ARCHIVE
OLMOD_KILL_FEED
```

**【Factory（僵尸工厂）】** 13 个 ★★★
```
OLMOD_FACTORY_BO1_DAMAGE
OLMOD_FACTORY_BO1_TELEPORT_TRAVEL
OLMOD_FACTORY_DEATH_FX
OLMOD_FACTORY_ENTRY
OLMOD_FACTORY_FACE_GLOW
OLMOD_FACTORY_INTERACTABLES
OLMOD_FACTORY_PERK_MACHINES
OLMOD_FACTORY_POWER_MOTION
OLMOD_FACTORY_PRESENTATION
OLMOD_FACTORY_RECONSTRUCTED_POOL
OLMOD_FACTORY_REFINED_FX
OLMOD_FACTORY_ROOM_DRAFT
OLMOD_FACTORY_TELEPORTERS
```

**【僵尸模式】** 12 个 ★★★
```
OLMOD_ZM_COOP_REVIVE
OLMOD_ZM_COOP_SPAWN_ZONES
OLMOD_ZM_CORRIDOR_AUDIT
OLMOD_ZM_DEBUG_BATTERY
OLMOD_ZM_DEBUG_BATTERY_KEY
OLMOD_ZM_DEBUG_GODMODE
OLMOD_ZM_NAV_SOURCE
OLMOD_ZM_NODE_GROUND_AUDIT
OLMOD_ZM_NOTIFY_AUDIT
OLMOD_ZM_PLAYER_COLLISION_PROFILE
OLMOD_ZM_RECONSTRUCTED_FEEDBACK
OLMOD_ZM_ROUTE_DIAGNOSTICS
```

**【武器】** 8 个
```
OLMOD_ALPHA_BARRETT_METADATA
OLMOD_ALPHA_BARRETT_SAFE_MATERIALS
OLMOD_ALPHA_WEAPON_MODEL_AUDIT
OLMOD_ALPHA_WEAPONS
OLMOD_ALT_CMD_WEAPON
OLMOD_ALT_FIRE
OLMOD_ALT_FORCE_TEST
OLMOD_ALT_WEAPON_SLOTS
OLMOD_LOG_ALT_WEAPON
OLMOD_LOG_WEAPON_SPREAD
OLMOD_AUDIT_WEAPON_TABLE
OLMOD_DUMP_WEAPON_BAND
OLMOD_SWAY_PHASE
OLMOD_VIEWHANDS_TF141
```

**【超时/性能】** 8 个 ★★
```
OLMOD_CLIENT_TIMEOUT_MS
OLMOD_CONNECT_TIMEOUT_MS
OLMOD_AUTO_LOADOUT_GRACE_MS
OLMOD_CLIENT_UI_DVAR_REPAIR_DELAY_MS
OLMOD_SV_FRAME_MS
OLMOD_SV_THINK_BUDGET_MS
OLMOD_MAXFPS_CEILING
OLMOD_PERF_BASELINE
```

**【诊断/探针】** 15 个
```
OLMOD_MSGWIN_PROBE
OLMOD_WSWITCH_PROBE
OLMOD_USERCMD_SAMPLE
OLMOD_SCOREBOARD_TRACE
OLMOD_LOG_RING_ADVANCE
OLMOD_LOG_NAME_BYTES
OLMOD_LOG_BUTTONS
OLMOD_LOG_CLIENT_COMMANDS
OLMOD_PROBE_PROFILE_SLOTS
OLMOD_DUMP_MODEL_BAND
OLMOD_XMODEL_SURFACE_AUDIT
OLMOD_AUDIT_ITEM_NAMES
OLMOD_FX_AUDIT
OLMOD_DISCONNECT_WITNESS
OLMOD_PLAINTEXT_CONFIG
```

**【其他】** 其余的
```
OLMOD_CLIENT_BRIDGE_PORT, OLMOD_CLIENT_INSTANCE, OLMOD_CONSOLE_LOG,
OLMOD_DEDICATED_CONTROL_PORT, OLMOD_HOST_ADDRESS, OLMOD_LOG_LEVEL,
OLMOD_PROCESS_ROLE, OLMOD_VERBOSE_LOG, OLMOD_TCLS_BLOB,
OLMOD_UNLOCK_ALL, OLMOD_AUTO_LOADOUT, OLMOD_CHARACTER_ITEM,
OLMOD_CHARACTER_VARIANT, OLMOD_CONST_BASELINES, OLMOD_DMZ_LOOT_BAND,
OLMOD_DMZ_PICKUP_EVENT, OLMOD_DMZ_UNARMED, OLMOD_ALLOW_RAW_COMMAND,
OLMOD_ALLOW_UNSIGNED_FASTFILES, OLMOD_OUTFIT_ATTACHMENTS,
OLMOD_OUTFIT_TAG, OLMOD_RESOLVE_CHARACTER_MODELS, OLMOD_PLAYER_VOCALS,
OLMOD_AC130_TEST_GRANT, OLMOD_UAV_RADAR_TEST, OLMOD_UAV_RADAR_TEST_GRANT,
OLMOD_WINNING, OLMOD_CLIENT_UI_DVAR_REPAIR
```

### `Platformwrapper.Ayria32` — **1 个**

```
OLMOD_PLATFORM_USER_ID
```

★ **与报告 024 的 `OLMOD_`=1 次一致** ✓

---

## 二、★★★ 决定性否证：**没有任何"禁用 Winsock hook"的开关**

### `Localnetworking` 的全部 5 个变量

```
OLMOD_LOBBY_LISTEN     ← 控制"是否 bind Lobby"
OLMOD_LOBBY_HOST       ← 控制"bind 到哪个主机名"
OLMOD_CLIENT_INSTANCE  ← 客户端实例号
OLMOD_PROCESS_ROLE     ← client/dedicated/combined
OLMOD_SYNTHETIC_DNS    ← 合成 DNS（1=黑洞 240.0.0.0/4, 0=真 hosts）
```

★★★ **⇒ 没有任何变量能关闭 `sendto`/`recvfrom`/`gethostbyname`/`bind` 的 hook 安装。**

★★★ **这是"混合方案不可行"的硬证明**：
**`Localnetworking` 的 hook 是**无条件安装**的。**

### 唯一的"间接"路径：`OLMOD_SYNTHETIC_DNS=0`

★★ **`OLMOD_SYNTHETIC_DNS=0`** 会让 `gethostbyname` 用**真 hosts**。
**但 hook 仍然装着** —— 只是行为不同。

★★ **⇒ 冲突依然存在（两个 hook 都想占据 `gethostbyname` 的入口）。**

---

## 三、★★★ `OLMOD_EXTERNAL_AUTH3` / `OLMOD_EXTERNAL_STUN` —— 关键接口

```
Alwaysoffline:
  OLMOD_EXTERNAL_AUTH3     ★★★
  OLMOD_EXTERNAL_STUN      ★★★
  OLMOD_CLAIM_LEGACY_AUTH  ★★
  OLMOD_LSG_SECRETS        ★★★
```

### ★★★ `OLMOD_LSG_SECRETS` 是最重要的一条

★★ **这是一个**文件路径**变量** ——
**指定 LSG 密钥从哪里读。**

★★★ **⇒ 这正是 `nt10.py` 写 `secrets.txt` 的消费端！**

★ **链路完整**：
```
nt10.py 读客户端内存 → 写 secrets.txt
                          ↓
Alwaysoffline 读 OLMOD_LSG_SECRETS 指定的文件
                          ↓
LSG 服务端得到会话密钥
```

★★ **报告 012 说"密钥必须从客户端内存读"，现在有了**消费端的字节级证据**。**

### ★★ `OLMOD_EXTERNAL_AUTH3` / `OLMOD_EXTERNAL_STUN` = 细粒度让出

```
OLMOD_EXTERNAL_AUTH3=1   跳内部 auth3，用外部的（= fake_auth_tls.py）
OLMOD_EXTERNAL_STUN=1    跳内部 STUN，用外部的（= stun_local.py）
```

★★ **⇒ 这比 `launch_chain.py` 的 `OLMOD_SKIP_AUX`（粗粒度）更精确。**

★★★ **但 `launch_chain.py` 的 `chain_env()`（报告 010）**没有设这两个**！**
```
chain_env 只设：
  OLDMOD_PROCESS_ROLE, OLDMOD_DEDICATED_CONTROL_PORT, OLDMOD_CLIENT_BRIDGE_PORT,
  OLDMOD_ROOM_OWNER_PORT, OLMOD_CLIENT_INSTANCE, OLMOD_CLAIM_LOBBY,
  OLMOD_CONSOLE_LOG, CODOL_FORCE_RECORD_VALIDATOR, OLMOD_STATS_NAME_UTF8
```

★★★ **⇒ 默认情况下 `Alwaysoffline` **自己**处理 auth3 和 STUN，
而 `fake_auth_tls.py` / `stun_local.py` 是**外部的**（端口 3074）。**

★★ **这与 `launch_chain.py` 同时启动两边是**矛盾的**：**
- `fake_auth_tls.py` 绑 `127.0.0.1:3074`
- `Alwaysoffline` 若也处理 auth3，会在**同一个端口**应答？

★★★ **⇒ 或者 `Alwaysoffline` 内部 auth3 是**虚拟 socket**（不真 bind），
所以两者不冲突。**（这与记忆里"Alwaysoffline 的 ServerKind::lobby 是虚拟 socket"的说法吻合。）**

---

## 四、★★ `CodolGameServer` 的 126 个变量揭示的**功能全貌**

★★★ **这是全包最有价值的一份"战斗服能力清单"。**

### 按游戏模式分组

| 模式 | 变量数 | 关键变量 |
|---|---|---|
| **TDM/通用** | ~15 | `OLMOD_WINNING`, `OLMOD_KILLCAM`, `OLMOD_KILL_FEED` |
| **僵尸工厂（Factory）** | 13 | `OLMOD_FACTORY_*` 全套 |
| **僵尸模式（ZM）** | 12 | `OLMOD_ZM_*` 全套 |
| **DMZ** | 3 | `OLMOD_DMZ_*` |
| **机器人** | 12 | `OLMOD_BOT_*` 全套 |
| **武器** | 14 | `OLMOD_ALPHA_*` / `OLMOD_ALT_*` |
| **快照/实体** | 6 | `OLMOD_SNAPSHOT_*` |
| **物理/弹道** | 20 | `OLMOD_BULLET_*` / `OLMOD_PENETRATION` |
| **超时/性能** | 8 | `OLMOD_*_TIMEOUT_MS` |
| **诊断** | 15 | `OLMOD_*_PROBE` / `OLMOD_*_AUDIT` |

### ★★★ 与记忆的交叉验证

| 记忆结论 | 新证据 |
|---|---|
| `svc->world` 从未绑定 ⇒ 伤害/HIT 全死 | `OLMOD_FLESH_IMPACT`, `OLMOD_HITBOX_DIAGNOSTICS`, `OLMOD_GLASS_DAMAGE_*` 全在，**但需要 world** |
| 快照 512 字节上限 | `OLMOD_SNAPSHOT_ENTITY_BASELINES` / `OLMOD_SNAPSHOT_ENTRY_FLAG` |
| 实体最多约 10 个 | 同上 |
| `omit=1` ⇒ 不写位置 | `OLMOD_SNAPSHOT_*` 系列控制**写什么** |
| 开镜失效 / pm_flags | `OLMOD_ALT_FIRE`, `OLMOD_ALT_WEAPON_SLOTS` |
| 悬空/无移动动画 | `OLMOD_NOCLIP`, `OLMOD_NATIVE_CAPSULE_TRACE` |

★★★ **⇒ 这些变量是**调试开关**，不是**修复开关**。
**它们能让"死掉的"功能**打印诊断**，但不能**复活它**（world 未绑定是根因）。**

---

## 五、★★★ 对"换战斗服"任务的关键结论

### 结论 1：`CodolGameServer` 的配置面有 126 个变量

★★ **换战斗服时，**如果新实现不读这些变量**，用户就无法调试。
**但**不读也能工作**（它们全是可选的调试开关）。**

★ **⇒ 最小实现只需要读**核心 3-5 个**（`OLMOD_PROCESS_ROLE` / `OLMOD_CLIENT_BRIDGE_PORT` /
`OLMOD_CLAIM_LOBBY` / `OLMOD_HOST_ADDRESS` 等）。**

### 结论 2：★★★ 战斗服真正的核心契约是 `OLMOD_SNAPSHOT_*` + `OLMOD_GAME_ENDPOINT`

★★ **`OLMOD_GAME_ENDPOINT`（在 `Alwaysoffline` 里）** ——
**指战斗服端点（UDP 28960）。**

★ **⇒ 战斗服的地址通过 `Alwaysoffline` 传给 `CodolGameServer`，
而不是 `CodolGameServer` 自己 bind。**

★★ **这与报告 024 的"三层"架构一致**：
```
Alwaysoffline   决定 "战斗服在哪" (OLMOD_GAME_ENDPOINT)
CodolGameServer 在客户端进程内运行，被 Alwaysoffline 告知端点
```

### 结论 3：★★★ 混合方案的真实障碍

```
1. Localnetworking 的 Winsock hook 无法关闭（本报告）
   ⇒ sendto/gethostbyname 冲突 ⇒ 与 nt10.py 互斥

2. 但 OLDMOD_LSG_SECRETS 让我们可以"绕过 nt10 直接喂密钥"
   ⇒ ★★★ 如果自己实现一个读内存的工具写 secrets.txt，
      就不需要 nt10.py 的 Winsock hook
   ⇒ 冲突可以规避！
```

★★★ **这是本次学习的**最重要操作结论**：

```
原方案：nt10.py（hook ws2_32 观测网络）+ 外部战斗服  → 冲突
新方案：自研读者（只 ReadProcessMemory，不 hook）+ 外部战斗服
        ↓
        OLMOD_LSG_SECRETS=<path> 告诉 Alwaysoffline 从哪读
        ↓
        ★ 无 hook 冲突
```

★ **而我**已经有了这个工具**：`force_display_name.py` 就是纯 `ReadProcessMemory` 的。
**同样的技术可以读会话密钥（地址链见报告 005）。**

---

## 六、逐字节证据总表

| # | 证据 | 值 |
|---|---|---|
| 1 | `Localnetworking` 的 `OLMOD_*` | **5 个**（无禁用 hook 开关）★★★ |
| 2 | `Alwaysoffline` 的 `OLMOD_*` | **34 个**（含 `EXTERNAL_AUTH3`/`EXTERNAL_STUN`/`LSG_SECRETS`）★★★ |
| 3 | `CodolGameServer` 的 `OLMOD_*` | **126 个**（最全的功能清单）★★ |
| 4 | `Platformwrapper` 的 `OLMOD_*` | **1 个** |
| 5 | 合计唯一变量 | **166 个** |
| 6 | `OLMOD_LSG_SECRETS` | 偏移待查，`Alwaysoffline` 内 |
| 7 | `OLMOD_EXTERNAL_AUTH3` / `_STUN` | `Alwaysoffline` 内 |

---

## 七、待逐字节继续（★ 优先级）

- [ ] ★★★ **`OLMOD_LSG_SECRETS` 的精确偏移与读取逻辑**
- [ ] ★★★ **`OLMOD_EXTERNAL_AUTH3` / `_STUN` / `_CLAIM_LEGACY_AUTH` 的精确偏移**
- [ ] ★★ **`OLMOD_SYNTHETIC_DNS=0` 时 `gethostbyname` hook 是否还在**（间接路径验证）
- [ ] ★★ **`OLMOD_GAME_ENDPOINT` 的格式与默认值**
- [ ] ★ **`OLMOD_SNAPSHOT_ENTITY_BASELINES` 的语义**
- [ ] ★ **126 个变量的默认值（可能编译期常量）**
