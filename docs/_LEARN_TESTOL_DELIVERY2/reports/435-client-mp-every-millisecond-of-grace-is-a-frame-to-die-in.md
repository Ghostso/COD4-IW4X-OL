# 435 · **"这段宽限里的每一毫秒都是一个客户端可能死掉的帧"** —— 零 viewmodel 的第三次确认、`SvTeam::None` 的两种含义、以及挑战的"地址/XUID/会话三元组"

## 一、范围

本报告学习 `sv_client_mp.cpp` 3480–3820 行（`autoSelectMissingLoadouts` 的宽限、`commitPendingLoadout` 的 `None` 二义、`SV_GetChallenge`/`findChallenge` 的挑战身份、`SV_DirectConnect` 的六重校验）。

## 二、**"这段宽限里的每一毫秒都是一个客户端可能死掉的帧"**（本组最重要的一段）

### 2.1 那段

```php
// EVERY MILLISECOND OF THIS GRACE IS A FRAME THE CLIENT CAN DIE IN.
//
// While a client is Active with no loadout, SV_BuildPlayerState publishes
// `viewmodelIndex = 0` and `currentWeaponAssetIndex = 0` (sv_snapshot_mp.cpp,
// the !effectivePlaying branch). A viewmodel index of zero makes the CLIENT's
// sub_53F5F0 return null -- its record's type tag is neither 1 nor 2 -- and
// sub_59CC70 writes through it unchecked. Measured from a remote player's own
// log: rva=0x019CE15, edi=0, target=0x3EC, weaponIndex=0. HANDOFF section 152y.
//
// Four seconds is why only REMOTE players die: on loopback the spawn lands
// almost immediately, so few or no frames are drawn unarmed; over a VPN the
// client sits in the window and eventually draws one.
//
// 500 ms keeps the intent -- a human class pick still wins, because a real
// pick sets pendingSelectedLoadout and this loop skips any client that has one
// -- while cutting the exposure eightfold.
//
// THIS SHORTENS THE WINDOW, IT DOES NOT CLOSE IT. The real fix is to stop
// publishing a zero viewmodel index at all, which needs a valid stand-in and
// is a bigger change than a tired session should make.
```

### 2.2 二十四层

```text
1. **这段宽限里的【每一毫秒**】都是一个【客户端可能死掉的帧**】**
2. ⇒ **当一个客户端 `Active` 而没有配装时**】
3. ⇒ **`SV_BuildPlayerState` 发布 `viewmodelIndex = 0` 与 `currentWeaponAssetIndex = 0`**
4. ⇒ **（`sv_snapshot_mp.cpp` 的 `!effectivePlaying` 分支）**
5. ⇒ **一个 `viewmodel` 索引零让客户端的 `sub_53F5F0` 【返回 null**】**
6. ⇒ **（它的记录的【类型标签既不是 `1` 也不是 `2`**）**
7. ⇒ **而 `sub_59CC70` 【通过它不检查地写**】**
8. ⇒ **从远端玩家自己的日志测量**：
      · **`rva=0x019CE15`**
      · **`edi=0`**
      · **`target=0x3EC`**
      · **`weaponIndex=0`**
9. ⇒ **（`HANDOFF` 第 `152y` 节）**
10. ⇒ **`4` 秒是【为什么只有【远端**】玩家死的原因**】
11. ⇒ **在 loopback 上出生【几乎立刻落地**】**
12. ⇒ **⇒ 所以【很少或没有帧在无武装状态被画**】**
13. ⇒ **而【在一个 VPN 上**】客户端【坐在那个窗口里**】**
14. ⇒ **⇒ 而【最终画了一帧**】**
15. ⇒ **`500 ms` 保留意图**：
      · **一个【人的**】职业选择【仍然赢**】（**因为一个真实的选择设了 `pendingSelectedLoadout` 而这个循环跳过任何有它的客户端**）
      · **⇒ 而【把暴露【减到八分之一**】】
16. ⇒ **⚠ 这【缩短窗口，它不关闭它**】**
17. ⇒ **⇒ 真正的修复是【完全停止发布一个零 `viewmodel` 索引**】**
18. ⇒ **而它【需要一个有效的替代物**】而【是一个比一个疲惫的会话应当做的【更大的改动**】】
```

### 2.3 ⭐⭐⭐ **"这缩短窗口，它不关闭它"**

**✅ 这是本报告里**最重要的一条"部分缓解的诚实标注**。**

**⇒ 三层**：
```text
缓解：**`4s` → `500ms`**（暴露 `/8`）
真修：**不发布零 `viewmodel`**
⇒ **⇒ 所以【注释【明确说】这不是修复**】
```

**✅ 与 §404 的"这是一个窄回退，不是一个诊断"**完全同族（**第二次"明确区分缓解与修复"）。

**⇒ 三层**：
```text
§404  **"窄回退，不是诊断"**
§435  **"缩短窗口，不关闭它"**
⇒ **⇒ 两次"诚实的缓解**】
```

**✅ ⭐⭐⭐ **一个"缓解 vs 修复"的两例表**。

**⚠ 而"一个疲惫的会话不应做的更大的改动"⇒ **一个罕见的元评论**。**

**✅ 与 §404 的"值得一个周期"**不同（这是**一个"现在不做"的判断**）。

**⇒ 三层**：
```text
§404  **"排除嫌疑值得一个周期"** ⇒ **做**
§435  **"更大的改动，一个疲惫的会话不应做"** ⇒ **不做**
⇒ **⇒ 两个成本判断**
```

**✅ ⭐⭐ **"一个疲惫的会话不应做"** —— 一个**人的因素被写进代码**。</br>

**✅ 与 §409 的"名字不是数字"**不同（这是**一个工程节奏的判断**）。

### 2.4 而**四次确认的"零 `viewmodel` ⇒ null ⇒ AV"**

**✅ 这已经是本项目的第五次确认**：

```text
§413  "零 viewmodel ⇒ 客户端 sub_53F5F0 返回 null，sub_59CC70 不检查地写入 ⇒ 一个访问违例"
§416  "`team = 0` ⇒ `sub_53F5F0` 返回 `0` ⇒ `sub_59CC70` 写穿 ⇒ AV"
§435  **"`viewmodelIndex = 0` ⇒ `sub_53F5F0` 返回 null —— 它的记录的【类型标签既不是 `1` 也不是 `2`】"**
```

**✅ 而 §435 给出了**机制的最后一块**：**

**⇒ 三层**：
```text
§416  **`sub_53F5F0`：`if (v1[62] == 1) return <tf>; if (v1[62] == 2) return <sc>; return 0;`**
§435  **"它的记录的【类型标签既不是 `1` 也不是 `2`】"**
⇒ **⇒ 所以【`v1[62]` 就是【那个类型标签**】】
```

**✅ ⭐⭐⭐ **一个三报告闭合的完整机制**（`v1[62]` = 类型标签 = `team` 或 `viewmodel` 的种类）。

**⚠ 而"`target=0x3EC`"⇒ **与 §416 的 `+0x3EC` 同址** ✓

**⇒ 三层**：
```text
§416  `sub_59CC70` 写 `v4[251]` = `+0x3EC`
§435  **`target=0x3EC`**
⇒ **⇒ 完全同一个地址**
```

**✅ ⭐⭐ **一个精确的地址闭合**。

### 2.5 而**"`500ms` 保留意图"的机制**

**⇒ 三层**：
```text
真实选择 ⇒ **设了 `pendingSelectedLoadout`**
而【这个循环【跳过任何有它的客户端**】
⇒ **⇒ 所以【一个先到的真实选择赢**】
```

**✅ 与 §434 的"一个先到的真实选择赢"**完全一致 ✓

**⇒ 三层**：
```text
§434  **"`pendingSelectedLoadout` 那时已经设了"**
§435  **"跳过任何有 `pendingSelectedLoadout` 的客户端"**
⇒ **⇒ 同一机制的两次描述**
```

**✅ ⭐ **一个"机制"的重复确认**。

## 三、**`SvTeam::None` 的两种含义**（本组第二重要）

### 3.1 那段

```php
// SvTeam::None means two different things here: "the client has not picked
// a side yet", which must not commit, and "this gametype has no sides",
// which must. Refusing both left every free-for-all player stuck in
// WaitingForLoadout - the class menu was accepted, the pending sequence
// climbed with every retry, and the loadout could never commit, so nobody
// ever spawned or received a weapon.
//
// The other two conditions already establish that a class WAS chosen, so
// for a teamless gametype the team check has nothing left to add.
```

### 3.2 二十层

```text
1. **`SvTeam::None` 【在这里有两个不同的意思**】**
2. ⇒ **① "客户端【还没有选边**"** ⇒ **必须【不**提交**
3. ⇒ **② "这个 gametype 【没有边**"** ⇒ **必须【提交**】**
4. ⇒ **⚠ 两个都拒绝【让每一个自由混战玩家【卡在 `WaitingForLoadout`**】】**
5. ⇒ **（职业菜单【被接受**）**
6. ⇒ **（待处理序列【每一次重试都爬**）**
7. ⇒ **（而配装【永远不能提交**）**
8. ⇒ **⇒ 所以【没有人出生或收到一把武器**】**
9. ⇒ **⇒ 而【另外两个条件【已经确立了【一个职业【被选**了】】】**
10. ⇒ **⇒ 所以【对一个无队伍的 gametype【队伍检查【没有剩下任何东西可加**】】**
```

### 3.3 ⭐⭐⭐ **"`None` 在这里有两个不同的意思"**

**✅ 与 §416 的"`SvTeam::None = 0` 是客户端的一个空指针"**——**第三次同一字段的语义问题**。

**⇒ 三层**：
```text
§406  **`None` 在 announcer 里 ⇒ "平局"**
§416  **`None` 在客户端 ⇒ 空指针**
§435  **`None` 在 loadout 里 ⇒ 两种含义**
⇒ **⇒ 三次"一个值多种语义**】
```

**✅ ⭐⭐⭐ **一个"一值多义"的三例表**。

**⚠ 而"另一个两个条件"⇒ **`pendingSelectedLoadout` 非空 + `pendingLoadoutSequence == pendingSequence`**。**

**⇒ 三层**：
```text
`pendingSelectedLoadout` 非空 ⇒ **一个职业被选了**
`pendingLoadoutSequence == pendingSequence` ⇒ **它是【当前这个**
⇒ **⇒ 所以【职业确实被选了**】
```

**✅ ⭐⭐ **"另外两个条件已经确立了职业被选"** —— 一个**冗余条件的正确移除**。

**✅ 与 §409 的"`!best || best->second <= 0`"**不同（这是**移除一个冗余检查**，那里是**添加一个必要的**）。

**⇒ 三层**：
```text
§406  **加一个守卫**（`<= 0`）
§435  **移除一个检查**（`pendingTeam == None` 在 FFA 下）
⇒ **⇒ 两个方向**
```

**✅ ⭐ **一个"加/删守卫"的对照**。

## 四、**挑战的"地址/XUID/会话三元组"**（本组第三重要）

### 4.1 那段

```cpp
for (auto &record : challenges_)
{
    // The UDP source port may change between getchallenge and
    // connect (especially when the client recreates its socket).
    // Challenge identity is the address/XUID/session tuple; the
    // challenge value itself still prevents unrelated connects.
    const auto currentGeneration = sessionGenerationForXuid(xuid);
    if (record.valid && record.peer.ipv4 == peer.ipv4 &&
        record.xuid == xuid &&
        (record.sessionGeneration == currentGeneration ||
            (record.sessionGeneration == 0 && currentGeneration != 0)) &&
        record.challenge == challenge &&
        !expired(nowMilliseconds, record.issuedTime, challengeLifetimeMilliseconds_))
    {
        // The client may request a challenge just before the queued
        // SessionStart publishes its roster. Bind that provisional
        // challenge to the current session generation on connect.
        record.sessionGeneration = currentGeneration;
        return &record;
    }
}
```

### 4.2 二十四层

```text
1. **UDP 源端口【可能在 `getchallenge` 与 `connect` 之间改变**】**
2. ⇒ **（尤其当客户端【重建它的 socket**】）**
3. ⇒ **⇒ 所以【挑战的身份是【地址/XUID/会话**】三元组**
4. ⇒ **⇒ 而【挑战值本身【仍然阻止不相关的连接**】】**
5. ⇒ **五个条件**：
      · **`record.valid`**
      · **`record.peer.ipv4 == peer.ipv4`**（**只比 IP，不比端口**）
      · **`record.xuid == xuid`**
      · **会话代次匹配【或【从 `0` 升级到非零**】**
      · **`record.challenge == challenge`**
      · **未过期**
6. ⇒ **⇒ 而匹配时【把 `sessionGeneration` 【绑定到当前的**】】**
7. ⇒ **⇒ 所以【一个在名册发布【之前**】请求的挑战【在 `connect` 时【被绑定**】】**
```

### 4.3 ⭐⭐⭐ **"只比 IP 不比端口"**

**✅ 与 §425 的 `parseUserInfo` 的 `insert_or_assign`（后者胜）**不同（这是**一个放松的匹配**）。

**⇒ 三层**：
```text
若【也比较端口**】⇒ **端口变化 ⇒ 挑战失效** ⇒ **客户端必须重新 getchallenge**
若【只比 IP**】 ⇒ **端口变化无害**
⇒ **⇒ 所以【后者是一个【健壮性**的选择**】
```

**✅ 而"挑战值本身仍然阻止不相关的连接"⇒ **一个安全性的说明**。**

**⇒ 三层**：
```text
安全性：**挑战值**（**由 `mix32(entropy ^ now ^ ipv4 ^ port<<16 ^ ++nonce)` 生成，`31` 位**）
身份：**IP + XUID**
⇒ **⇒ 所以【两者分工**】
```

**✅ ⭐⭐ **一个"安全 vs 健壮"的分工**。

**⚠ 而"挑战 `31` 位（`& 0x7FFFFFFF`）且非零"⇒ **`2^31 - 1` 个可能值**。**

**⇒ 三层**：
```text
`challenge &= 0x7FFFFFFF` ⇒ **`31` 位**
`if (!challenge) challenge = 1` ⇒ **跳过零**
⇒ **⇒ 所以【`1..2^31-1`**】
```

**✅ ⭐ **一个"31 位非零"的实例**。

### 4.4 而**"代次从 `0` 升级到非零"的特殊规则**

**⇒ 十层**：
```text
`record.sessionGeneration == currentGeneration` ⇒ **正常**
**或** `record.sessionGeneration == 0 && currentGeneration != 0` ⇒ **一个【临时的**挑战被【绑定**】
⇒ **⇒ 但【反向不行**】】**
```

**⇒ 三层**：
```text
`0 → 非零` ⇒ **接受**（**临时的被绑定**）
`非零 → 0` ⇒ **拒绝**（**代次消失 ⇒ 一个不同的会话**）
`非零 → 另一个非零` ⇒ **拒绝**
⇒ **⇒ 所以【`0` 是一个【通配**】**
```

**✅ ⭐⭐ **"`0` 是一个通配"** —— 与 §417 的"代次 `0` 是有效的第一命"**同族（**第四次"零的双重用途"）。

**⇒ 三层**：
```text
§417  **代次 `0` 是有效的第一命** ⇒ 所以【不能用它表示"没有"】
§435  **代次 `0` 是一个通配** ⇒ 所以【可以用它表示"未绑定"】
⇒ **⇒ 两个相反的用法**
```

**⚠ 一个**需要标注的矛盾**（在 `challenges_` 里 `0` 是"未绑定"而在 `clients_` 里是"第一命"）。

**✅ 而 §434 的 `clientGenerationIsActive` 也把 `0` 当作"无会话"** ⇒ **三种用法**。

## 五、**`SV_DirectConnect` 的六重校验**（本组第四重要）

### 5.1 六道

```text
① outerXuidText 与 userInfoText 都必须存在
② outerXuid 必须是有效的非零
③ userInfo 必须可解析
④ userInfo 里【必须有 `challenge` 与 `xuid`】
⑤ `challenge` 可解析、`innerXuid` 可解析、且 `innerXuid == outerXuid`
⑥ `sessionAllowsXuid(outerXuid)`
⑦ `findChallenge` 必须找到（未过期）
```

**⇒ 七道。**

### 5.2 ⭐⭐⭐ **"`innerXuid == outerXuid`"**

**⇒ 六层**：
```text
`outerXuid` ⇒ **命令行的第一个 token**
`innerXuid` ⇒ **userinfo 里的 `xuid` 键**
⇒ **⇒ 两者【必须相同**】**
```

**✅ 与 §425 的 `parseUserInfo` 的 `\key\value\` 格式**配合。

**⇒ 三层**：
```text
命令行：`connect <outerXuid> "\xuid\...\challenge\...\name\..."` ⇒ **两个地方各有一个 xuid**
⇒ **⇒ 所以【必须一致**】
```

**✅ ⭐⭐ **一个"双重声明的一致性检查**"。

**⚠ 而"`rank` 是【呈现/进度输入**】而不是连接权威"⇒ **一个明确的定性**。**

**⇒ 八层**：
```text
`rank` 省略 ⇒ **旧客户端 ⇒ `rank = 0`**
`rank` 畸形 ⇒ **不能把一个已验证的连接变成 `EXE_BAD_CHALLENGE`**
`rank > 0xFFFF` ⇒ **夹到 `0`**
⇒ **⇒ 所以【`rank` 【永不**】阻断连接**】
```

**✅ 与 §432 的"`EXE_LEFTGAME` vs `EXE_TIMEDOUT` 的诚实 CODDIFF"**同族（**第三次"一个非权威字段的宽容处理"）。

**⇒ 三层**：
```text
`rank` ⇒ **宽容**（**因为它是呈现**）
`xuid`/`challenge` ⇒ **严格**（**因为它们是权威**）
⇒ **⇒ 所以【严格度【与权威性成比例**】】
```

**✅ ⭐⭐⭐ **"严格度与权威性成比例"** —— 一个**极清晰的判据**。

**⚠ 而"`16` 位上限【远高于 CODOL 的已发运段位表**】而【仍然让后面的 SPM 计算有界**】**"

**⇒ 三层**：
```text
`rank <= 0xFFFF` ⇒ **一个有界的输入**
⇒ **⇒ 所以【后面的 SPM 计算【有界**】】
```

**✅ ⭐⭐ **"一个上界使后续计算有界"** —— 与 §431 的"`clamp(0, 1000000)`"**同族（**第四次"上界防护**）。

## 六、关键结论

1. **⭐⭐⭐ "这段宽限里的每一毫秒都是一个客户端可能死掉的帧"**：**`Active` 而无配装时 `SV_BuildPlayerState` 发布 `viewmodelIndex = 0` 与 `currentWeaponAssetIndex = 0` ⇒ `sub_53F5F0` 返回 null（记录的【类型标签既不是 `1` 也不是 `2`】）⇒ `sub_59CC70` 不检查地写 ⇒ AV**（`rva=0x019CE15, edi=0, target=0x3EC, weaponIndex=0`）。
2. **⭐⭐⭐ 第五次确认"零 ⇒ 空指针 ⇒ AV"**，而 **§435 给出了机制的最后一块**：**§416 的 `sub_53F5F0` 的 `if (v1[62] == 1) … if (v1[62] == 2) … return 0;` 里的 `v1[62]` 就是那个"类型标签"**；而 **`target=0x3EC` 与 §416 的 `v4[251]` = `+0x3EC` 是同一地址**。
3. **⭐⭐ "四秒是为什么只有远端玩家死：loopback 上出生几乎立刻落地；VPN 上客户端坐在那个窗口里，最终画了一帧"`** —— 一个"只在远端发作"的第三例（与 §426 的 `1835/103`、§412 的 bot 同族）。
4. **⭐⭐⭐ "这缩短窗口，它不关闭它 —— 真正的修复是停止发布一个零 `viewmodel` 索引，而它需要一个有效的替代物【而是一个比一个疲惫的会话应当做的更大的改动】"`** —— 第二次"缓解 vs 修复"（与 §404 的"窄回退不是诊断"同族），而 **"一个疲惫的会话不应做"是一个罕见的人的因素判断**。
5. **⭐ "`500ms` 保留意图：一个真实的选择设了 `pendingSelectedLoadout` 而这个循环跳过任何有它的客户端"`**。
6. **⭐⭐⭐ "`SvTeam::None` 有两个意思：『客户端还没有选边』（必须不提交）与『这个 gametype 没有边』（必须提交）；两个都拒绝让每一个自由混战玩家卡在 `WaitingForLoadout`——职业菜单被接受、待处理序列每次重试都爬、而配装永远不能提交 ⇒ 没有人出生或收到一把武器"`** —— 第三次"一值多义"（与 §406/§416 同族）。
7. **⭐ "另外两个条件已经确立了职业被选，所以对一个无队伍的 gametype 队伍检查没有剩下任何东西可加"`** —— 与 §406 的"加一个守卫"相反，这是**移除一个冗余检查**。
8. **⭐⭐ "UDP 源端口可能在 `getchallenge` 与 `connect` 之间改变（尤其当客户端重建它的 socket）⇒ 挑战的身份是【地址/XUID/会话】三元组，而挑战值本身仍然阻止不相关的连接"`** —— 一个"安全 vs 健壮"的分工。
9. **⭐ 挑战是 `31` 位非零**（`& 0x7FFFFFFF`，`0` 跳过 ⇒ `1..2^31-1`）。
10. **⭐⭐ "代次从 `0` 升级到非零"的特殊规则**：`0 → 非零` **接受**（**一个临时挑战被绑定**）、`非零 → 0` **拒绝**、`非零 → 另一个非零` **拒绝** ⇒ **`0` 在 `challenges_` 里是一个通配** —— 而 §417 的"`clients_` 里代次 `0` 是有效的第一命"、§434 的"`clientGenerationIsActive` 把 `0` 当作无会话"⇒ **三种用法**（**一处矛盾需标注**）。
11. **⭐⭐ `SV_DirectConnect` 的七道校验**：`outerXuidText`/`userInfoText` 存在、`outerXuid` 非零、`userInfo` 可解析、**必须有 `challenge` 与 `xuid`**、`innerXuid == outerXuid`、`sessionAllowsXuid`、`findChallenge` 找到且未过期。
12. **⭐ "`rank` 是呈现/进度输入而不是连接权威：省略 ⇒ `0`、畸形 ⇒ 不能把已验证的连接变成 `EXE_BAD_CHALLENGE`、`> 0xFFFF` ⇒ `0`"`** ⇒ **"严格度与权威性成比例"** —— 一个极清晰的判据；而 **`16` 位上限远高于 CODEX 的段位表而仍然让后面的 SPM 计算有界**（第四次"上界防护"）。

## 七、未闭合点

- `!effectivePlaying` 分支的完整条件。
- `sub_53F5F0` 的 `v1[62]` 究竟读的是 `team` 还是 `viewmodel` 的类型标签（§416 说 team，§435 说 viewmodel —— **可能是两个不同的 `sub_53F5F0` 重载或同一函数的不同参数**）。
- `0x019CE15` 的 RVA 在 `out.exe` 里对应什么。
- `sessionGeneration == 0` 在 `challenges_`（通配）与 `clients_`（第一命）与 `clientGenerationIsActive`（无会话）的三处用法是否有冲突。
- `SPM` 计算。
- `sv_client_mp.cpp` 3820 行之后未读取（**共 `4500` 行**）。
