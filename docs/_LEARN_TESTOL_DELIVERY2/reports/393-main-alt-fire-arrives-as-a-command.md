# 393 · **"交替开火作为【一条命令】到达，不是一个按钮"** —— 五个诊断 map 的"前四次"上限、`ConfigureSession` 不能摧毁已建立的 peer

## 一、范围

本报告学习 `sv_main_mp.cpp` 1350–1700 行。

## 二、**`n 89` 的服务端消费点**（本组最重要的一段）

### 2.1 那段

```php
// ALT-FIRE ARRIVES HERE, AS A COMMAND, NOT AS A BUTTON.
//
// The player's controls call it "Weapon Attachments" and bind
// it to 3, beside the killstreaks on 4-7 -- none of which are
// `+` binds, so none of them reach a usercmd at all. Two
// button hunts failed on that: sect.190's 0x100000 is aim down
// sights, and 0x08000000 fires 63 times in three minutes on an
// IDLE client. A control settled it -- two left-clicks gave
// exactly two 0x00000001 edges while five presses of 3 gave
// NONE.
//
// `n 89` is the command, and the evidence is a count rather
// than a plausible-looking bit: ten presses, ten commands, in
// two bursts of five. Queued on the world and consumed by the
// next clientThink as a single rising edge, so the toggle that
// sect.190 already built is driven unchanged.
for (const auto &command : clientPacket.reliableCommands) {
    if (command.command == "n 89" && clientPacket.clientSlot != (size_t)-1) {
        world_.requestAltWeaponToggle((uint32)clientPacket.clientSlot);
    }
}
```

### 2.2 十六层

```text
1. **交替开火【在这里】到达，作为一条【命令】，不是一个【按钮】**
2. ⇒ **玩家的控制把那个动作叫 "Weapon Attachments"**
3. ⇒ **并把它绑到 `3`，在 `4-7` 的连杀奖励旁边**
4. ⇒ **而它们【没有一个】是 `+` 绑定**
5. ⇒ **所以它们【根本】到达不了一个 usercmd**
6. ⇒ **两次按钮搜寻在那上面失败了**：
      · **sect.190 的 `0x100000` 是【瞄准镜】**
      · **`0x08000000` 在【一个空闲客户端】上三分钟触发 `63` 次**
7. ⇒ **一个对照 settle 了它**：
      · **两次左键给出恰好两个 `0x00000001` 边沿**
      · **而按 `3` 五次给出【零个】**
8. ⇒ **`n 89` 是那条命令**
9. ⇒ **而证据是一个【计数】而不是一个看似合理的位**
10. ⇒ **十次按键，十条命令，在两个五个的爆发里**
11. ⇒ **在世界里排队而由【下一个 `clientThink`】作为【一个单一的上升沿】消费**
12. ⇒ **所以 `sect.190` 已经建好的那个 switch 【原样驱动】**
```

### 2.3 ⭐⭐ **"证据是一个【计数】而不是一个看似合理的位"**

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第六次"从行为测量而不是从代码推理"）。**

**⇒ 三层**：

```text
错的方法：从反编译读一个位 ⇒ **两次都错**
对的方法：**数"按键 N 次 → 命令 N 条"**
⇒ **⇒ 一个可数的证据**
```

**✅ 与 §370 的"十次按键十条命令，一个精确的数量匹配"**完全一致 ✓

**⇒ **第三次确认那个测量。**

**⚠ 而"在两个五个的爆发里"⇒ **一个额外的细节**（不是均匀的十次）。**

**✅ **一个更精确的记录。**

### 2.4 而**"`sect.190` 已经建好的那个 switch 原样驱动"**

**✅ 与 §370 的 `altPair` / `altHeldWeapon` / `pendingAltToggle_`**完全闭合 ✓

**⇒ 三层**：

```text
§349  `requestAltWeaponToggle` 设 `pendingAltToggle_[n] = true`
§370  `clientThink` 消费它（一次性）
§393  **`n 89` 的来源**
```

**✅ ⭐ **一个完整的三段链**（命令 → 标志 → 消费）。**

**⚠ 而"`clientSlot != (size_t)-1`"⇒ **一个哨兵检查**。**

**✅ 与 §379 的"`~0u`"**同族（**第三次"全一是哨兵"）。**

## 三、**五个诊断 map 的"前四次"上限**（本组第二重要）

### 3.1 五处

```cpp
dtlsNatDiagnostics_[peerKey]++ < 4
plaintextDiagnostics_[peerKey]++ < 4
dtlsRejectDiagnostics_ 的"只在变化时"
netchanRejectDiagnostics_[peerKey]++ < 4
connectionlessDiagnostics_ 的计数器（无上限）
```

**⇒ 四处有"前四次"，一处无上限。**

### 3.2 而**`dtlsPeerDiagnostics_` 的"只在变化时"**

```php
const auto previous = dtlsPeerDiagnostics_.find(peerKey);
const auto emitNat = packetType == 0x0D && dtlsNatDiagnostics_[peerKey]++ < 4;
if (emitNat || previous == dtlsPeerDiagnostics_.end() || previous->second != state)
{
    dtlsPeerDiagnostics_[peerKey] = state;
    ...
}
```

**⇒ 四层**：

```text
1. **`packetType == 0x0D`（NAT？）⇒ 前四次**
2. ⇒ **或状态【变化】⇒ 记录**
3. ⇒ **所以是一个"边沿 + 上限"的双重条件**
4. ⇒ **`state` 三值**：`empty` / `cookie-issued` / `established`
```

**✅ ⭐ **`packetType 0x0D` = NAT/STUN**。**

**⇒ 与记忆里的"DW 私有 STUN 15 字节应答"**配合。**

**⚠ 而"三个状态"⇒ **一个 DTLS 握手的三阶段**。**

**✅ 一个**清晰的握手模型**。

### 3.3 而**"★ DEBUG (2026-10-07)：Reply 上挂的握手现场数据"**

```cpp
// ★ DEBUG (2026-10-07): Reply 上挂的握手现场数据（net_dtls_cod.cpp 写入）带到日志。
if (result.kind == DtlsPacketResultKind::Reply && !result.reason.empty())
    std::clog << " detail=" << result.reason;
```

**⇒ 三层**：

```text
1. **一个中文注释**（罕见）
2. ⇒ **`net_dtls_cod.cpp` 把握手现场数据挂在 `Reply` 的 `reason` 上**
3. ⇒ **所以一个"reason"字段被复用作【诊断载荷】**
```

**✅ 与 §368 的"一个标签不能塌缩两个答案"**同族（**一个字段两个用途）。**

**⚠ 而"`reason` 被复用作 detail"⇒ **一个实用的变通**。**

## 四、**`ConfigureSession` 不能摧毁已建立的 peer**（本组第三重要）

### 4.1 那段

```php
// ConfigureSession can arrive once per native client while one match is
// being assembled. Do not destroy an established peer when the repeated
// descriptor is re-parsed; the session key is shared by the match.
const auto keyChanged = previousKey != dtlsConfig_.securityKey();
if (updated && (!wasConfigured || (keyChanged && dtlsPeers_.sessionCount() == 0)))
{
    dtlsPeers_.reset();
    dtlsPeerDiagnostics_.clear();
    dtlsRejectDiagnostics_.clear();
    dtlsNatDiagnostics_.clear();
    plaintextDiagnostics_.clear();
    netchanRejectDiagnostics_.clear();
}
```

### 4.2 十二层

```text
1. **`ConfigureSession` 在一个比赛被组装时可以【每个原生客户端到达一次】**
2. ⇒ **当一个重复的描述符被重新解析时【不要摧毁一个已建立的 peer】**
3. ⇒ **那个会话密钥是【由比赛共享的】**
4. ⇒ **`keyChanged = previousKey != securityKey()`**
5. ⇒ **只在一个三条件满足时重置**：
      · **`updated`**
      · **且（`!wasConfigured` 或（`keyChanged` 且 `sessionCount() == 0`））**
6. ⇒ **所以：首次配置 ⇒ 重置**
7. ⇒ **密钥变了而【没有会话】⇒ 重置**
8. ⇒ **密钥变了而【有会话】⇒ 不重置**
9. ⇒ **密钥没变而【已配置】⇒ 不重置**
10. ⇒ **五个诊断 map 一起清**
```

### 4.3 ⭐ **"会话密钥是【由比赛共享的】"**

**✅ 与 §347 的"基线是消息级的"**不同**（这是**比赛级的）**。**

**⇒ 三层**：

```text
密钥：**比赛级**（一次会话一个）
描述符：**每个客户端一次**（重复到达）
⇒ **⇒ 所以不能因为重复到达就重置**
```

**✅ ⭐ **一个"幂等性"的设计**。**

**⚠ 而"`sessionCount() == 0`"⇒ **所以只有在没有活会话时才重置**。**

**✅ 一个**精确的保护**。

### 4.4 而**`keyFingerprint` 只打印前四字节**

```cpp
std::string keyFingerprint;
for (std::size_t index = 0; index < 4; ++index)
    keyFingerprint += std::to_string(dtlsConfig_.securityKey()[index]) + (index == 3 ? "" : ":");
```

**⇒ 三层**：

```text
1. **只打印【前四个字节】**
2. ⇒ **所以是一个【指纹】而不是完整密钥**
3. ⇒ **⇒ 一个安全考量**（不把完整密钥写进日志）
```

**✅ ⭐ **一个正确的安全实践**。**

**⚠ 而"`std::clog` 打印【完整】密钥"⇒ **矛盾**！**

**⇒ 三层**：

```cpp
for (const auto byte : dtlsConfig_.securityKey())
    std::clog << std::hex << static_cast<unsigned int>(byte);
```

**⚠ 所以**`std::clog` 有完整密钥而 `RuntimeLog` 只有指纹**。**

**⇒ 一处**不一致**（可能因为 `clog` 只到控制台）。**

**✅ 一个**需要标注的差异**。

## 五、**`configureGameState` 的三个条件**（本组第四重要）

### 5.1 那段

```php
if (matchStatus_.configured && gameState.gameType == matchGameType_ &&
    (gameState.gameType == "sd" || gameState.gameType == "cha" ||
        gameState.gameType == "dm"))
{
    gameState.uiGameRules = {
        // sd's scoreboard limit is rounds won; the scored modes show the
        // score limit itself.
        .scoreLimit = gameState.gameType == "sd"
            ? matchStatus_.rules.winLimit
            : matchStatus_.rules.scoreLimit,
        .timeLimitMinutes = matchStatus_.rules.timeLimitMinutes,
        .halfTime = false,
    };
```

### 5.2 九层

```text
1. **三个条件**：`matchStatus_.configured` / 类型匹配 / 类型在 `{sd, cha, dm}`
2. ⇒ **`sd` 的记分板限制是【回合胜场】**
3. ⇒ **而计分模式显示【得分限制】本身**
4. ⇒ **所以 `scoreLimit = sd ? winLimit : scoreLimit`**
5. ⇒ **`timeLimitMinutes` 直传**
6. ⇒ **`halfTime = false`**（恒假）
```

**✅ 与 §391 的"SD 每回合拥有一个新的计时器"**配合。**

**⚠ 而 `"cha"`⇒ **第三个游戏类型**。**

**⇒ 所以**四种类型**：**

```text
sd    回合制
cha   （?）
dm    自由混战
zm    僵尸（不在这个列表里 ⇒ 走 §391 的"没有比赛时钟"）
```

**⚠ 而 `zm` **不**在这个列表里 ⇒ 所以 `uiGameRules` **不被覆盖**。**

**✅ 与 §391 的"`gameType == "zm"` 的门"**完全闭合 ✓

### 5.3 而**"`matchStartServerTime = 0`"**

```php
// The HUD clock is an absolute end time, so it needs the match
// start. It is NOT matchStatus_.startServerTime: that is reset to 0
// further down this same function and only filled later, when a
// client first reaches Playing, so at this point it holds nothing.
//
// configureGameState calls world_.reset(), which does `snapshot_ =
// {}`, so the world this gamestate describes begins at serverTime 0.
// That is also what CODOL does natively - the level start time is
// fixed at map load, not at first spawn - so 0 is the correct base
// and the clock simply runs from the moment the world starts.
gameState.matchStartServerTime = 0;
```

**⇒ 十层**：

```text
1. **HUD 时钟是一个【绝对的结束时间】**
2. ⇒ **所以它需要比赛开始**
3. ⇒ **而它【不是】 `matchStatus_.startServerTime`**
4. ⇒ **因为那在同一个函数下面被重置为 0**
5. ⇒ **而只在【一个客户端第一次到达 Playing】时被填**
6. ⇒ **所以在这里它【什么都没有】**
7. ⇒ **`configureGameState` 调用 `world_.reset()`，它做 `snapshot_ = {}`**
8. ⇒ **所以这个 gamestate 所描述的世界【从 `serverTime 0` 开始】**
9. ⇒ **那也是 CODOL 原生做的**：**关卡开始时间在【地图加载时】固定，不是在第一次出生**
10. ⇒ **所以 0 是正确的基数而时钟从【世界开始的那一刻】跑**
```

**✅ ⭐ **"关卡开始时间在地图加载时固定，不是在第一次出生"** —— 一个**精确的原生行为**。**

**⚠ 而"这里它什么都没有"⇒ **一个**顺序敏感的**注释**。**

**✅ 与 §368 的"源/投影/投影的投影"**不同（这是**一个时间基**）。

**⇒ 三层**：

```text
世界时间（`snapshot_.serverTime`）：**从 0 开始**
比赛开始时间：**也是 0**（因为 `world_.reset()`）
⇒ **⇒ 所以两者同步**
```

**✅ ⭐ **一个"世界重置 ⇒ 时间重置"的闭合**。**

## 六、`stageSessionRoster` / `commitSessionRoster` / `rollbackSessionRoster` 的三段

```cpp
bool stageSessionRoster(generation, members)   ⇒ clients_.stageSessionRoster(...)
bool commitSessionRoster(generation)            ⇒ clients_.commitSessionRoster(...)
bool rollbackSessionRoster(generation)          ⇒ clients_.rollbackSessionRoster(...)
```

**⇒ 三层**：

```text
1. **三段式**（stage / commit / rollback）
2. ⇒ **而都有 `generation` 参数**
3. ⇒ **所以是一个带代际的事务**
```

**✅ 与 §349 的"staged-then-commit"**第十二次。**

**⚠ 而"`generation`"⇒ **一个单调的令牌**。**

**✅ 与 §344 的"`spawnGeneration`"**同族（**第三次"代际令牌"）。**

## 七、`registerDynamicWeaponConfigString` 的五个参数

```cpp
std::optional<uint16> registerDynamicWeaponConfigString(
    SvModularWeaponConfigString configString,
    const uint16 firstDynamicWeaponAssetIndex,
    const SvClientSystem::WeaponConfigStringCommandBuilder &buildCommand)
```

**⇒ 三层**：

```text
1. **`configString`**（配置串）
2. ⇒ **`firstDynamicWeaponAssetIndex`**（§388 的"`firstDynamicWeapon`"）
3. ⇒ **`buildCommand`**（一个命令构建器）
```

**✅ 与 §388 的"`1147..1154` 从 `firstDynamicWeapon` 连续注册"**完全闭合 ✓

**⇒ **第二次确认那个起点。**

**⚠ 而"`buildCommand`"⇒ **所以客户端被告知一个新武器串**。**

**✅ 与 §391 的"`publishActorModelConfigString` 的时机错"**同族（**第二次"动态 configstring 的时机"）。**

## 八、`onComFrame` / `SV_ConnectionlessPacket` / `NET_DtlsPacket` 的三条入口

```text
onComFrame              ⇒ 每帧（timeouts / autoLoadout / scheduler / sendMessages）
SV_ConnectionlessPacket ⇒ 无连接包（先 DTLS 解密）
NET_DtlsPacket          ⇒ DTLS 包（握手 / 认证数据 / 连接less 转发）
```

**⇒ 三层入口。**

### 8.1 而**`NET_DtlsPacket` 的完整流程**

```text
① `dtlsPeers_.NET_DtlsPacket(...)`
② 诊断：`peerKey` = `(ipv4 << 16) | port`
③ 三个状态：`empty` / `cookie-issued` / `established`
④ 若 `Rejected` ⇒ 诊断（去重）
⑤ 若 `AuthenticatedData`
     · `NET_IsConnectionlessPacket(plaintext)`
     · 若 connectionless ⇒ `clients_.SV_ConnectionlessPacket(...)` ⇒ 回包
     · 否则 ⇒ `clients_.SV_PacketEvent(...)` ⇒ 处理 netchan
⑥ 回包前再 `NET_DtlsBuildData`
```

**✅ ⭐ **`peerKey = (ipv4 << 16) | port`** —— 一个**精确的键**。**

**⚠ 而 `port` 是 16 位 ⇒ 所以 `(ipv4 << 16) | port` 无冲突** ✓**

**✅ 一个**正确的打包**。

### 8.2 而**`FragmentPending` 不算拒绝**

```cpp
else if (clientPacket.kind == NetchanProcessKind::FragmentPending)
{
    // Fragment buffering is normal netchan traffic.  It is not a
    // rejected packet and must not inflate drop diagnostics.
}
```

**⇒ 四层**：

```text
1. **分片缓冲是【正常的】netchan 流量**
2. ⇒ **它【不是】一个被拒的包**
3. ⇒ **而【绝不能】膨胀丢弃诊断**
4. ⇒ **所以一个空的 `else if`**
```

**✅ 与 §350 的"FAT 分片帧真实布局"**配合。**

**⚠ 而"一个空的 `else if`"⇒ **一个显式的"什么都不做"**。**

**✅ 与 §369 的"中性化而不是跳过"**不同（这是**真的什么都不做**）。

**✅ 一个**正确的分类**。

## 九、关键结论

1. **⭐⭐ "交替开火【在这里】到达，作为一条【命令】，不是一个【按钮】"`** —— 而 **"`n 89` 是那条命令，而证据是一个【计数】而不是一个看似合理的位：十次按键，十条命令，在两个五个的爆发里"`**。
2. **"sect.190 的 `0x100000` 是瞄准镜，而 `0x08000000` 在空闲客户端上三分钟 63 次"`** —— 第三次确认那两个错的位。
3. **"在世界里排队而由下一个 `clientThink` 作为【一个单一的上升沿】消费，所以 `sect.190` 已经建好的那个 switch 原样驱动"`** —— **一个完整的三段链**（命令 → 标志 → 消费）。
4. **⭐ 五个诊断 map 的"前四次"上限**（`dtlsNat` / `plaintext` / `netchanReject`）+ **`dtlsPeer` 的"边沿 + 上限"双重条件**。
5. **`packetType == 0x0D` = NAT/STUN**，而 DTLS 的三个状态（`empty` / `cookie-issued` / `established`）。
6. **"★ DEBUG (2026-10-07)：Reply 上挂的握手现场数据"** —— `reason` 字段被复用作诊断载荷（**一个字段两个用途**）。
7. **⭐⭐ "`ConfigureSession` 在一个比赛被组装时可以每个原生客户端到达一次 ⇒ 不要摧毁一个已建立的 peer，因为会话密钥是【由比赛共享的】"`** —— 一个**幂等性设计**。
8. **四条件重置**（`updated` 且（`!wasConfigured` 或（`keyChanged` 且 `sessionCount() == 0`）））。
9. **⚠ `keyFingerprint` 只打印前四字节（正确）而 `std::clog` 打印【完整】密钥** —— 一处不一致。
10. **⭐ `configureGameState` 的三条件**（`configured` / 类型匹配 / 类型在 `{sd, cha, dm}`）—— 而 **`zm` 不在这个列表里**，与 §391 的门**完全闭合**。
11. **"`sd` 的记分板限制是【回合胜场】而计分模式显示【得分限制】本身"`**。
12. **⭐⭐ "关卡开始时间在【地图加载时】固定，不是在第一次出生 —— 所以 0 是正确的基数而时钟从世界开始的那一刻跑"`** —— 而 **`world_.reset()` 的 `snapshot_ = {}` 让"世界重置 ⇒ 时间重置"闭合**。
13. **`stageSessionRoster` / `commitSessionRoster` / `rollbackSessionRoster` 的三段式**，而**都有 `generation`** —— 第十二次事务性、第三次"代际令牌"。
14. **`registerDynamicWeaponConfigString` 的 `firstDynamicWeaponAssetIndex`** —— 第二次确认 §388 的起点。
15. **⭐ `NET_DtlsPacket` 的 `peerKey = (ipv4 << 16) | port`** —— 一个精确且无冲突的键。
16. **"分片缓冲是正常的 netchan 流量，它不是一个被拒的包，而绝不能膨胀丢弃诊断"`** —— 一个显式的空 `else if`。

## 十、未闭合点

- `"n 89"` 之外的可靠命令号。
- `DtlsPeerState` 的完整三值确认。
- `configureFromDemonwareDescriptor` 的完整解析。
- `"cha"` 游戏类型的语义。
- `SvGameState::uiGameRules` 的完整字段。
- `sv_main_mp.cpp` 1700 行之后未读取。
