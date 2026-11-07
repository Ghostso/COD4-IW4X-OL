# 314 · **`+0x154` 是 3.3.3.3 的而 `+0x15C` 是本 build 的**、`test byte [reg+112h],4` 零次命中、`damageEvent` 八位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 200–400 行。

## 二、**`+0x154` vs `+0x15C`**（本组最重要的一段）

### 2.1 那段

```php
// OLMOD(section-84): EVERY ADDRESS ABOVE IS 3.3.3.3's OR ANOTHER GAME'S,
// and this is the last block on section 81's list that is neither
// blocked nor translated. What is settled:
//   the OFFSET  +0x154 is 3.3.3.3's gentity currentAngles. out.exe's is
//               +0x15C, which sv_native_server_entity_mp.cpp already
//               carries -- SV_LinkEntity read line for line on both
//               builds settles it, and the +8 is the entityState growth
```

### 2.2 三层

```text
1. **`+0x154` 是 3.3.3.3 的 `gentity::currentAngles`**
2. ⇒ **本 build 的是 `+0x15C`**，而 `sv_native_server_entity_mp.cpp` 已经带上
3. ⇒ **`SV_LinkEntity` 逐行在两 build 读出来定案**，而 **`+8` 就是 `entityState` 的增长**
```

### 2.3 **`+8` 是 `entityState` 增长**

**⇒ 所以 `entityState` 在 `gentity` 里挪了 8 字节。**

**⚠ 而 §264 说三个 trace 函数的参数"循环右移" 也发生在 build 之间。**

**⇒ 所以 `+8` 的位移与"参数互换"是**两个不同的变化**。**

**✅ 与记忆里"`ownerNum=0x160` 读 `currentAngles` yaw"**相关**——**

**⇒ 而 §239（报告 239）说 "`0x118..0x168` nine offsets (four were 3.3.3.3's, `ownerNum=0x160` read `currentAngles` yaw)"。**

**⚠ 而这里是 `+0x154`（3.3.3.3）与 `+0x15C`（本 build）。**

**⇒ 而 §239 说 `0x160`。**

**⇒ 三个值：`0x154` / `0x15C` / `0x160`。**

**⇒ 可能：**

```text
0x154   3.3.3.3 的 currentAngles
0x15C   本 build 的 currentAngles
0x160   本 build 的 currentAngles 的【第二分量】？
```

**⚠ 而 §239 说 "`ownerNum=0x160` read `currentAngles` yaw" ⇒ 所以 0x160 是 `ownerNum` 而**读出来的值是 currentAngles 的 yaw**。**

**⇒ 一个**偏移错位的读数**（用 ownerNum 的地址读到了 currentAngles）。**

**⚠ 这是 §239 记录的"三个反转"之一。**

## 三、**"一个冻结面向世界 +X 的身体"**

```php
// Leaving this at zero does not merely lose a cosmetic angle: every
// locational trace is then evaluated against a body frozen facing
// world +X, so hit locations are attributed to whichever part happens
// to be under the ray in that frame.
```

### 3.1 三层

```text
1. **把它留零不只是丢一个装饰性的角度**
2. ⇒ **每一个定位 trace 然后对着一个【冻结面向世界 +X】的身体被评估**
3. ⇒ 所以**命中位置被归因到那一帧恰好在射线下的任何部位**
```

**✅ 与 §266 的"三个零向量 ⇒ 所有 trace 在模型空间原点"**完全同族** ✓**

## 四、**三个"settled"的判定**（本组第二重要）

### 4.1 第一个：`+0x154` 的修正（已在 §2）

### 4.2 第二个：`yaw-only` **没有被反驳**

```php
//   the CLAIM    yaw-only is not refuted here: section 55's locational
//               hit reproduced byte for byte across two cycles with this
//               code live, which a body frozen facing world +X would not
//               do. That is evidence, not a reading of the host
```

**⇒ 三层**：

```text
1. **`yaw-only` 在这里【没有】被反驳**
2. ⇒ §55 的定位命中**在两个周期里逐字节重现**，而**这段代码是活的**
3. ⇒ **那是一个冻结面向世界 +X 的身体【做不到】的**
4. ⇒ **那是证据，不是对宿主的阅读**
```

**✅ 与 §277 的"用一条已经测量过能打中的线"同族（第十次"用实测作证据"）。**

### 4.3 第三个：**宿主**没有**那个函数**

```php
//   the HOST    HAS NO SUCH FUNCTION, which section 73 established and
//               this is a re-measurement of. 3.3.3.3's DObjTraceline has
//               THREE callers and out.exe's 0x007825F0 has TWO --
//               sub_46E0A0 at 0x0046E280 and sub_619470 at 0x0061963F --
//               and the missing one is the server leaf.
```

**⇒ 四层**：

```text
1. **宿主没有那个函数**
2. 3.3.3.3 的 `DObjTraceline` 有**三个**调用者
3. ⇒ 本 build 的 `0x007825F0` 有**两个** —— `sub_46E0A0` @ `0x0046E280` 与 `sub_619470` @ `0x0061963F`
4. ⇒ **而缺失的那个是【服务端叶子】**
```

**✅ 与 §265 的"四个 vs 两个调用者"**完全同族** ✓**

**⇒ 第二次用**调用者计数**证明服务端路径被删除。**

### 4.4 而 `test byte [reg+112h],4` 的**零次命中**

```php
// The bit test that picks the locational pair, `test byte [reg+112h],4`,
// occurs EXACTLY TWICE on 3.3.3.3 and both are inside
// SV_PointTraceToEntity itself (0x005FB605, 0x005FB717);
// at the ported displacement +0x11A it occurs ZERO times
// in out.exe AND zero times in OL.exe.
```

### 4.5 四层

```text
1. 挑选定位对的位测试是 **`test byte [reg+112h],4`**
2. ⇒ 在 3.3.3.3 上**恰好出现两次**，都在 `SV_PointTraceToEntity` 自己里面（`0x005FB605`、`0x005FB717`）
3. ⇒ **在移植位移 `+0x11A` 处它在 `out.exe` 里出现零次**
4. ⇒ **而且在 `OL.exe` 里也出现零次**
```

### 4.6 而 `+0x11A` 与 §265 的**两个值**

**§265**："`tests svFlags bit 2 at gentity +0x112`" 而 "The image has no `test byte [reg + 0x11A], 4` anywhere"

**⇒ 所以：**

```text
+0x112   3.3.3.3 的 svFlags
+0x11A   移植位移（+8）⇒ 本 build 应该在的地方
```

**⇒ 而 §314 说"在 `+0x11A` 处零次命中"。**

**✅ 与 §265 **完全一致** —— 而这里是**第二次确认**。**

**⚠ 而 §239 的记忆说 "`svFlags` offset conflict (still open: `0x112` vs `0x11A` in three places)"**

**⇒ 现在有**两次独立确认**"`+0x11A` 处零次命中" ⇒ 所以**不是冲突而是"本 build 没有那条指令"。**

### 4.7 而"**所以 `yaw-only` 规则根本无法从这个 build 读出来**"

```php
// So the yaw-only rule cannot be read off this build at all -- it is a
// contract for EngineBindings::traceServerLocationalEntities,
// which reimplements the function, and 3.3.3.3 plus BO1
// plus Ghosts are the only places it can come from.
// ONE-SIDED BY NECESSITY, not by omission
```

### 4.8 四层

```text
1. ⇒ **所以 `yaw-only` 规则根本不能从这个 build 读出来**
2. ⇒ 它是**给 `EngineBindings::traceServerLocationalEntities` 的契约**，那个函数**重新实现了它**
3. ⇒ 而 **3.3.3.3 + BO1 + Ghosts 是它唯一能来自的地方**
4. ⇒ **单侧是必然的，不是遗漏**
```

**✅ "单侧是必然的，不是遗漏"** —— 一个精确的自我辩护。**

**⇒ 与 §313 的"一是证据不是对宿主的阅读"同族。**

## 五、`playerEntityAngles` 的**一行**

```cpp
[[nodiscard]] constexpr std::array<float, 3> playerEntityAngles(
    const std::array<float, 3> &viewAngles)
{
    return { 0.0f, viewAngles[1], 0.0f };
}
```

**⇒ 三项：pitch = 0、yaw = viewAngles[1]、roll = 0。**

**✅ 与 §313 的"`currentAngles` 只有 YAW"完全一致。**

## 六、**`CODDIFF` 的"两个跳过条件"**

```php
// CODDIFF(client_think_real): BO1 skips the write while the player is
// linked (ps.eFlags & 0x300) and Ghosts while (ps+292 & 0x3800), both
// leaving the link owner's angles in place. This server never links a
// player - BG_GetPlayerEyePosition is admitted only for
// linkEntityNum == 2047 - so the guarded branch has no producer here.
```

### 6.1 四层

```text
1. **BO1 在玩家被链接时跳过写入**（`ps.eFlags & 0x300`）
2. ⇒ **Ghosts 在 `ps+292 & 0x3800` 时跳过**
3. ⇒ 两者都**让链接所有者的角度留在原地**
4. ⇒ **本服务器从不链接一个玩家** —— `BG_GetPlayerEyePosition` 只在 `linkEntityNum == 2047` 时被接纳
5. ⇒ **所以那个被守护的分支在这里没有生产者**
```

### 6.2 而 `linkEntityNum == 2047`

**⇒ 与 §264 的 `baseEntity = 2047`（`ENTITYNUM_NONE`）**完全一致** ✓**

**⇒ 所以"未链接"= 2047。**

### 6.3 而 `TODO` 的精确退出条件

```php
// TODO(CODOL): restore the linked/mounted branch together with the
// turret owner. Exit when a CODOL link producer exists and a mounted
// player's currentAngles can be read from its owner entity.
```

**⇒ 三层**：

```text
1. 恢复 linked/mounted 分支与**炮塔所有者**一起
2. ⇒ **退出条件**：一个 CODOL 链接生产者存在
3. ⇒ 而**一个骑乘玩家的 `currentAngles` 能从它的所有者实体读到**
```

**✅ 一个**可判定的退出条件**。**

## 七、**`0x00C55B68` 的 76 项表 vs `0x00DA8078`**（本组第三重要）

```php
// CODREF(g_update_client_info): the CODOL 76-entry clientInfo table at
// 0x00C55B68 maps fields 46..49 to +0x30..+0x3C (10-bit model CCS
// indexes) and fields 50..53 to +0x58..+0x64 (6-bit tag CCS indexes).
// out.exe's clientState table is 0x00DA8078 and section 82e already
// showed it CONTRADICTS that layout -- the fields at +0x30..+0x3C are
// SIX bits here, +0x58..+0x64 are not in the table at all, and there is
// a separate 10/11-bit group at +0x80..+0x90. This paragraph describes
// 3.3.3.3 and is kept as the shape the packer was built against, not as
// a claim about the host.
```

### 7.1 三组表

```text
3.3.3.3 的 76 项表   0x00C55B68
本 build 的 clientState 表  0x00DA8078
（3.3.3.3 的字段布局）
  fields 46..49 ⇒ +0x30..+0x3C   【10 位】model CCS
  fields 50..53 ⇒ +0x58..+0x64   【6 位】tag CCS
```

### 7.2 而**三处矛盾**

```text
① 本 build 的 +0x30..+0x3C 是【六位】而不是十位
② +0x58..+0x64 【根本不在表里】
③ 而有一个【独立的 10/11 位组】在 +0x80..+0x90
```

**⇒ 所以"那段描述的是 3.3.3.3"。**

### 7.3 而"**保留为打包器被构建所依据的形状，而不是关于宿主的断言**"

**✅ 与 §314 的"单侧是必然的"同族**（第十三次"明确不是断言"）。

## 八、**`memcpy_s(a1 + 260, 0x30, (a2 + 76), 0x30)`** 的**四十八字节**

```php
// THE TWELVE-ENTRY CHARACTER RECORD, netfields 21..32 at +0x4C..+0x78.
//
// CG_SetupClientCharacterInfo 0x541800 copies FORTY-EIGHT BYTES from
// clientState +0x4C straight into the model resolver's request
// (`memcpy_s(a1 + 260, 0x30, (a2 + 76), 0x30)`), and this server's own
// probe reads that same request at clientInfo+1024 as word(0..3) then
// word(4..15) -- the OVERRIDES whose absence every one of our model
// requests reports as `no-overrides`. Twelve dwords is exactly the
// twelve-entry character record. Handoff section 181m.
```

### 8.1 五层

```text
1. **十二项角色记录，netfields 21..32 在 `+0x4C..+0x78`**
2. ⇒ `CG_SetupClientCharacterInfo 0x541800` **把四十八字节**从 `clientState +0x4C` 拷进模型解析器的请求
3. ⇒ `memcpy_s(a1 + 260, 0x30, (a2 + 76), 0x30)` —— **`0x30 = 48`、`76 = 0x4C`**
4. ⇒ 而这个服务器自己的探针在 `clientInfo + 1024` 读同一个请求为 `word(0..3)` 然后 `word(4..15)`
5. ⇒ **那些 OVERRIDES 的缺失就是每一个模型请求报的 `no-overrides`**
6. ⇒ **十二个 dword 恰好就是十二项角色记录**
```

### 8.2 而 `a2 + 336` = `+0x150` 的**证明**

```php
// The netfield table calls these name[0..31], perks[0..1] and
// clanAbbrev[0..4]. Those are MW3 PORT NAMES and they are wrong for how
// this build uses the memory: `a2 + 336` in the same function is +0x150,
// the character model index this project already confirmed, which is
// what proves a2 carries WIRE offsets. Trust the consumer.
```

### 8.3 五层

```text
1. netfield 表把这些叫做 `name[0..31]`、`perks[0..1]`、`clanAbbrev[0..4]`
2. ⇒ **那些是 MW3 的移植名字**，而对**这个 build 如何使用那块内存**是**错的**
3. ⇒ 因为**同一个函数里的 `a2 + 336` 是 `+0x150`**
4. ⇒ 而那是**这个项目已经确认的角色模型索引**
5. ⇒ **这就证明 `a2` 携带【线偏移】**
6. ⇒ **相信消费者**
```

### 8.4 **"信任消费者"**

**✅ 与 §314 的"`yaw-only` 是给重新实现的函数的契约"同族**（第十一次"以消费者为准"）。

**⇒ 而 `a2 + 336 = 0x150`** ⇒ 一个**具体的算术验证。**

## 九、`ClientInfoCharacterRecordFields` 的**十二个**

```cpp
constexpr std::array ClientInfoCharacterRecordFields{
    21u, 22u, 23u, 24u, 25u, 26u, 27u, 28u, 29u, 30u, 31u, 32u };
constexpr std::uint32_t ClientInfoCharacterRecordBitCount = 32;
constexpr std::uint32_t ClientInfoExplicitModelFieldFirst = 46;
constexpr std::uint32_t ClientInfoExplicitTagFieldFirst = 50;
constexpr std::uint32_t ClientInfoExplicitModelBitCount = 10;
constexpr std::uint32_t ClientInfoExplicitTagBitCount = 6;
```

### 9.1 两组字段

```text
21..32    十二项角色记录    每项 32 位？
46..49    显式模型          每个 10 位
50..53    显式标签          每个 6 位
```

### 9.2 而 `ClientInfoCharacterRecordBitCount = 32`

**⚠ 而 §313 的 `ClientInfoCustomizationStorageFields` 里 fields 21/22/27/31/32 是**10 位**。**

**⇒ 所以 `21..32` 在**那个上下文**里是 10 位而这里说 `BitCount = 32`。**

**⚠ 两处矛盾。**

**⇒ 可能 `ClientInfoCharacterRecordBitCount = 32` 是**"每一项 32 位"**而 §313 的是**"每一项 10 位"**。**

**⇒ 而 §314 说 `memcpy_s` 拷 48 字节 = 12 dword = 12 × 32 位。**

**✅ 所以 `32` 是**每项 32 位** —— 而 §313 的 10 位是**另一条路**（显式模型字段 46..49）。**

**⇒ 两条路：**

```text
21..32    12 × 32 位 = 384 位 = 48 字节    ← 【memcpy 的】
46..49    4 × 10 位                        ← 【显式模型】
50..53    4 × 6 位                         ← 【显式标签】
```

**✅ 而 §313 的 `ClientInfoCustomizationStorageFields`（8 个，76 位）是**第三条路**。**

**⇒ 所以有三条路** —— 而 §313 与 §314 各记录一/两条。**

## 十、`PlayerDamagePayloadLimits` 的**四个**

```cpp
constexpr SvPlayerDamagePayloadLimits PlayerDamagePayloadLimits{
    .maximumClients = MaximumGameClients,
    .maximumEntities = MaximumGameEntities,
    .methodOfDeathCount = MethodOfDeathCount,
    .hitLocationCount = HitLocationCount,
};
```

**⇒ 四项，全部来自已有的常量。**

**✅ 与记忆里"`MethodOfDeathCount = 20`"、"`HitLocationCount = 21`"一致。**

## 十一、`normalizedDamageDirection` 的**五项**

```cpp
if (!direction) return nullopt;                                     // ①
const auto lengthSquared = d[0]² + d[1]² + d[2]²;
if (!isfinite(lengthSquared) || lengthSquared < 0.0f) return nullopt;  // ②
if (lengthSquared == 0.0f) return std::array<float,3>{};             // ③
const auto inverseLength = 1.0f / std::sqrt(lengthSquared);
return { d[0]*inv, d[1]*inv, d[2]*inv };                            // ④
```

### 11.1 四项

```text
无方向 ⇒ nullopt
非有限或负 ⇒ nullopt
零长度 ⇒ 【零向量】（不是 nullopt）
否则 ⇒ 归一化
```

### 11.2 而**"零长度 ⇒ 零向量而不是 nullopt"**

**⇒ 三层**：

```text
1. 零长度是一个**合法的"无方向"**
2. ⇒ 所以返回零向量
3. ⇒ 而不是 nullopt（那意味着"读不出"）
```

**✅ 与 §289 的"空串 ⇒ 0.0f 而不可读 ⇒ nullopt"**完全同族** ✓**

**⇒ 第五次"空/零 vs 读不出"的区分。**

## 十二、`damageDirectionBytes` 的**四项**（本组第四重要）

```php
if (!direction) return { 0xFF, 0xFF };                              // ① 哨兵
const auto horizontal = std::hypot(d[0], d[1]);
float pitch{}, yaw{};
if (horizontal == 0.0f)
    pitch = d[2] > 0.0f ? 270.0f : 90.0f;                          // ② 垂直
else
{
    pitch = BG_NormalizeAngle360(-std::atan2(d[2], horizontal) * RadiansToDegrees);
    yaw = BG_NormalizeAngle360(std::atan2(d[1], d[0]) * RadiansToDegrees);
}
return {
    (uint32)(pitch * (256.0f / 360.0f)) & 0xFF,                    // ③ 量化
    (uint32)(yaw * (256.0f / 360.0f)) & 0xFF,
};
```

### 12.1 四项

```text
无方向          ⇒ {0xFF, 0xFF}（哨兵）
水平为零        ⇒ pitch = 270（向上）或 90（向下），yaw = 0
否则            ⇒ atan2 两个角度，归一化到 0..360
量化            ⇒ × (256/360) ⇒ 0..255（八位）
```

### 12.2 而**`{0xFF, 0xFF}` 是哨兵**

**⇒ 与 §278 的 `optionalClient` 的 `0xFFFFFFFF` 同族（第十一次"哨兵"）。**

### 12.3 而**向上是 270 而向下是 90**

```text
d[2] > 0 ⇒ pitch = 270   （向上）
d[2] ≤ 0 ⇒ pitch = 90    （向下）
```

**⚠ 与直觉相反（向上通常是 90）。**

**⇒ 因为 COD 的 pitch 是**negated**（正 pitch 向下）。**

**✅ 与 `pitch = -atan2(d[2], horizontal)` 的负号一致。**

### 12.4 而 `& 0xFF` 的**双重保险**

**⇒ 因为 `pitch * (256/360)` 在 pitch = 360 时会得 256 ⇒ `& 0xFF` 得 0。**

**✓ 正确。**

### 12.5 而 `256.0f / 360.0f` 是**八位角度**的量化

**⇒ 与记忆里"`directionToByte` 的 162 个方向"**不同的量化**：**

```text
§258  directionToByte   162 个量化方向（三维）
§314  damageDirectionBytes  256 步（pitch/yaw 各八位）
```

**✅ 两个不同的量化方案。**

## 十三、`projectPlayerDamageFeedback` 的**五段**

```cpp
// ① 500 ms 后清 damageCount
if (feedback.damageTime && serverTime - *feedback.damageTime > 500)
    playerState.damageCount = 0;

// ② 抖动计时器从 damageTime 驱动
if (feedback.damageTime && playerState.damageDuration)
{
    const auto elapsed = serverTime >= *feedback.damageTime ? serverTime - *feedback.damageTime : 0u;
    playerState.damageTimer = elapsed < playerState.damageDuration ? playerState.damageDuration - elapsed : 0u;
}

// ③ 无血或无最大血量 ⇒ 返回
if (!feedback.damageBlood || !playerState.maxHealth) return;

// ④ damageCount = min(127, 100 * blood / maxHealth)
const auto damageCount = std::min<uint32>(127, 100 * feedback.damageBlood / playerState.maxHealth);
const auto direction = damageDirectionBytes(feedback.damageFrom);
playerState.aimSpreadScale = std::min(255.0f, aimSpreadScale + (float)damageCount);

// ⑤ damageEvent 三位置换
playerState.damageEvent = (playerState.damageEvent + 1) & 0x7;
playerState.damagePitch = direction[0];
playerState.damageYaw   = direction[1];
playerState.damageCount = damageCount;
playerState.damageDuration = SvFlinchDurationMilliseconds;
playerState.damageTimer    = SvFlinchDurationMilliseconds;
feedback.damageBlood = 0;
feedback.damageFrom.reset();
feedback.damageTime = serverTime >= 20 ? serverTime - 20 : 0;
```

### 13.1 而**抖动计时器从伤害时间驱动**

```php
// THE FLINCH TIMER RUNS DOWN IN REAL TIME, and the demo shows it
// reaching exactly 0 rather than stopping short: 675, 567, 464 ...
// 122, 17, 0. Driven from the damage time rather than by
// subtracting a frame length, so a dropped or long frame cannot
// leave it stuck part-way.
```

**⇒ 四层**：

```text
1. 抖动计时器**实时**倒数
2. demo 显示它**精确到 0** 而不是停在半路：**675, 567, 464 ... 122, 17, 0**
3. ⇒ **从伤害时间驱动**而不是**减去一个帧长**
4. ⇒ **所以一个丢弃的或长的帧不能让它卡在半路**
```

**✅ 一个**正确的"从绝对时间推导"而不是"增量"**的设计。**

**⇒ 与 §245 的"`stage` vs `faultStage`"、§263 的"`GetTickCount64`"同族。**

### 13.2 而**`damageEvent` 在 8 处回绕**（本组第三重要）

```php
// WRAPS AT EIGHT, NOT AT 0xFFFF. The field is eight bits wide and
// retail's 244 assertions of it span exactly 0..7 -- so it is a
// three-bit counter and the client only reads it for a CHANGE.
// 0xFFFF was harmless while the value went to a field nobody reads
// and is worth getting right now that it does not.
playerState.damageEvent = (playerState.damageEvent + 1) & 0x7;
```

### 13.3 五层

```text
1. **在 8 处回绕，不是 0xFFFF**
2. 字段是**八位**宽而**零售的 244 个断言**它的值**恰好跨 0..7**
3. ⇒ 所以它是一个**三位计数器**而**客户端只为一个【变化】读它**
4. ⇒ **`0xFFFF` 是无害的**当那个值去到一个**没人读的字段**
5. ⇒ 而现在那个字段**不**是没人读了 ⇒ **值得弄对**
```

### 13.4 **"244 个断言恰好跨 0..7"**

**⇒ 与 §313 的"`14,610 / 93,042`"、§288 的"75 个全试过"同族（第十二次"语料计数"）。**

**⇒ 而"三位计数器"与"客户端只读变化"配合。**

### 13.5 而 `damageTime = serverTime - 20`

```php
feedback.damageTime = serverTime >= 20 ? serverTime - 20 : 0;
```

**⇒ 三层**：

```text
1. 设成 `serverTime - 20`
2. ⇒ **往回 20 ms**
3. ⇒ 所以**第一帧的 `elapsed` 是 20 而不是 0**
```

**⚠ 一个**有意的偏移**（可能是为了让"已过去 20 ms"看起来像真的）。**

**⇒ 而从 `damageTimer = damageDuration` 看，那个偏移让**第一帧就减 20**。**

## 十四、`validCharacterCustomization` 的开头

```php
// A CUSTOMIZATION HAS TO CARRY A CHARACTER IDENTITY, AND THIS BUILD
// CARRIES IT IN A DIFFERENT FIELD FROM 3.3.3.3.
//
// This used to demand a non-zero selectionId, full stop. On OLfinal
// they are ALWAYS zero -- CharacterSelectionResolve is absent
// (section 16a) and the server says so on every spawn -- so the
```

**⇒ 三层**：

```text
1. **一个定制化必须携带一个角色身份**
2. ⇒ 而这个 build **在一个与 3.3.3.3 不同的字段里**携带它
3. ⇒ 过去它要求一个非零 `selectionId`
4. ⇒ **而在 OLfinal 上它们【总是】零** —— `CharacterSelectionResolve` 缺席（§16a）
```

**✅ 与 §282 的"`characterPresentationResolverAvailable()` 返回 false"**完全一致** ✓**

**⇒ 所以这是一个**已知的无解**并被处理。**

## 十五、关键结论

1. **`+0x154` 是 3.3.3.3 的 `currentAngles` 而 `+0x15C` 是本 build 的**，`+8` 是 `entityState` 增长。
2. **留零 ⇒ 一个冻结面向世界 +X 的身体 ⇒ 命中全错。**
3. **`yaw-only` **没有被反驳** —— §55 的定位命中逐字节重现，而那是一个冻结身体做不到的。
4. **"那是证据，不是对宿主的阅读"**。
5. **宿主没有那个函数**：`DObjTraceline` 3 个调用者 vs 2 个，缺的是服务端叶子。
6. **`test byte [reg+112h],4` 在 3.3.3.3 上恰好两次而 `+0x11A` 处零次** —— 两次独立确认。
7. **"`yaw-only` 规则根本不能从这个 build 读出来"** —— 它是给重新实现的函数的契约。
8. **"单侧是必然的，不是遗漏"**。
9. **`playerEntityAngles` 只有 yaw**。
10. **BO1 跳过 `ps.eFlags & 0x300`、Ghosts 跳过 `ps+292 & 0x3800`**，而本服务器**从不链接玩家**（`linkEntityNum == 2047`）。
11. **`0x00C55B68` 的 76 项表与 `0x00DA8078` 三处矛盾**。
12. **`memcpy_s(a1+260, 0x30, a2+76, 0x30)` = 48 字节 = 12 dword**。
13. **`a2 + 336 = 0x150`** 证明 `a2` 携带线偏移 ⇒ **"信任消费者"**。
14. **三条不同的字段路**（`21..32` 384 位 / `46..49` 10 位 / `50..53` 6 位 + §313 的 8 个 76 位）。
15. **`normalizedDamageDirection` 的"零长度 ⇒ 零向量而不是 nullopt"** —— 第五次空/零区分。
16. **`damageDirectionBytes` 的 `{0xFF, 0xFF}` 哨兵**，向上 270 向下 90（negated pitch）。
17. **八位角度量化 `× (256/360)`** 与 §258 的 162 方向不同。
18. **抖动计时器从绝对伤害时间驱动**（demo 显示 675/567/464/.../17/0）。
19. **`damageEvent` 三位计数器在 8 处回绕** —— 零售 244 个断言跨 0..7。
20. **`validCharacterCustomization` 的角色身份在**不同的字段**里**（因为 `selectionIds` 在 OLfinal 上总是零）。

## 十六、未闭合点

- `damageTime = serverTime - 20` 的 20 ms 偏移依据。
- `+0x15C` 与 §239 的 `0x160` 的关系。
- 三条字段路是否会在客户端冲突。
- `sv_snapshot_mp.cpp` 400 行之后未读取。
