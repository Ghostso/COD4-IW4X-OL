# 361 · **"`0xFF0003NN` —— 两个字节都重要而它们做不同的事"** —— 记录槽 vs 指针索引、`25 j_spine4` 与红色 FX 占位、十八个 spawn 字段

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 16000–16400 行。

## 二、**`+0x58` 的两个字节**（本组最重要的一段）

### 2.1 那段

```php
// 0xFF0000NN, and NN IS THE AGENT SLOT. Measured four ways in 12.8.1:
// sub_530BB0 indexes the client's record array by this low byte, and
// sub_530C90 stamps the record the AGENT element names. If the two
// disagree the entity points at a record nobody filled.
// 0xFF0003NN. BOTH BYTES MATTER AND THEY DO DIFFERENT JOBS -- read live
// out of a retail demo (20-zm-actor-lifecycle.md 12.11):
//
//   +0x58 (low byte)  -- the RECORD slot. sub_530BB0 indexes the
//                        684-byte record array by centity+332.
//   +0x59 (byte 1)    -- the POINTER index within that record.
//                        sub_52FBE0 reads record[0x18 + 4*centity+333]
//                        and hands it to the DObj builder.
//
// MEASURED on a live retail zombie: entity 671, eType 19, carries
// 0xFF000303 -- record slot 3, pointer index 3 -- and slot 3's owner
// field reads 671. Across thirteen populated slots the ONLY non-null
// pointers are indices 3 and 4; indices 0, 1, 2 and 5 are null on every
// working zombie.
//
// This server sent 0xFF0000NN, so byte 1 was ZERO and every actor
// selected the null ptrs[0]. The DObj was then built with a null
// resource, got no bone array, and the client threw `25 j_spine4 <ent>`
// with a red FX placeholder where the zombie should be.
entity.networkState.actorField0058 = 0xFF000300u | (uint32)agentSlot;
```

### 2.2 二十层

```text
1. **`0xFF0000NN` 而 NN 是 agent 槽**
2. ⇒ **12.8.1 里用【四种方式】测量**：
     · **`sub_530BB0` 用这个低字节索引客户端的记录数组**
     · **`sub_530C90` 标记 [agent 元素所命名的] 那个记录**
3. ⇒ **若两者不同意，实体指向一个【没人填过的记录】**
4. ⇒ **`0xFF0003NN`**
5. ⇒ **两个字节都重要而它们做【不同的事】**
6. ⇒ **从零售 demo 活动读出（`20-zm-actor-lifecycle.md` 12.11）**：
     · **`+0x58`（低字节）—— 【记录槽】**
       **`sub_530BB0` 用 `centity+332` 索引那个【684 字节的记录数组】**
     · **`+0x59`（字节 1）—— 那个记录里的【指针索引】**
       **`sub_52FBE0` 读 `record[0x18 + 4*centity+333]` 并交给 DObj 构建器**
7. ⇒ **在一个【活的零售僵尸】上测量：实体 671，eType 19，携带 `0xFF000303`**
8. ⇒ **记录槽 3、指针索引 3**
9. ⇒ **而槽 3 的【拥有者字段】读 671**
10. ⇒ **跨【十三个已填充的槽】，唯一非空的指针是索引 3 与 4**
11. ⇒ **索引 0、1、2、5 在每一个工作僵尸上都是【空】**
12. ⇒ **这个服务器发 `0xFF0000NN` ⇒ 所以字节 1 是【零】**
13. ⇒ **而每一个 actor 选了【空的 `ptrs[0]`】**
14. ⇒ **DObj 于是用一个【空资源】被构建**
15. ⇒ **得不到骨骼数组**
16. ⇒ **而客户端抛 `25 j_spine4 <ent>`**
17. ⇒ **并用一个【红色 FX 占位符】代替僵尸应该在的地方**
```

### 2.3 ⭐⭐ **"两个字节都重要而它们做不同的事"**

**✅ 这是本文件里**最精密的位域发现**。**

**⇒ 三层**：

```text
+0x58 记录槽     ⇒ 哪个 684 字节记录
+0x59 指针索引   ⇒ 那个记录里的哪个指针（ptrs[N]）
⇒ 两者都必须对
```

**✅ 与 §347 的"`effect | (bone << 9)`"**同族（**第二次位域打包**）。

**⚠ 而这里是**两个独立的字节域**而不是位域。**

**✅ **三种打包：**

```text
§347  `effect | (bone << 9)`         位域
§361  `0xFF0003NN`                   两个字节域
§342  `packEntityWeapon`  = lo | hi<<16  两个 16 位
```

**⇒ 三次。**

### 2.4 而**"十三个已填充的槽里只有索引 3 与 4 非空"**

**✅ 一个**极不寻常的分布**。**

**⇒ 三层**：

```text
1. 十三个槽里只有两个指针非空（3 与 4）
2. ⇒ **索引 0/1/2/5 在所有工作僵尸上都是空**
3. ⇒ **所以 ptrs[0] 是【必然失败】的选择**
```

**✅ 而"这个服务器发 `0xFF0000NN`" ⇒ **正好选 0**。**

**⇒ **最坏的默认值。**

**⚠ 一个**极其微妙的错误**（发了一个"看起来合理"的值）。**

### 2.5 而 **`25 j_spine4 <ent>`**

**✅ 与 §338 的"`record+308` 是 tag 名字而它是空的 ⇒ 哈希空字符串"**同族（**第二次"空导致失败"**）。

**⇒ 三层**：

```text
1. 空资源 ⇒ 无骨骼数组
2. ⇒ **客户端找不到 `j_spine4` 骨骼**
3. ⇒ **所以报 `25 j_spine4 <ent>`**
```

**✅ 一个**具体的错误消息**（可搜索）。**

**⚠ 而 `25` 可能是一个**骨骼索引**或**错误码**。**

### 2.6 而**"红色 FX 占位符"**

**✅ 一个**极具体的视觉症状**（**第五次"具体视觉症状"**）。**

**⇒ 与 §350 的"控制台成了僵尸身体"、§360 的"倾斜的僵尸"**同族。**

**⇒ **第六次。**

**✅ 而"红色 FX 占位符"意味着**客户端知道有一个实体但无法渲染**。**

**⇒ 所以**不再是"不画"而是"画错"**。**

**✅ 一个**更晚的阶段**（比"不画"进了一步）。

## 三、**十八个 spawn 字段（全部来自零售第一帧）**（本组第二重要）

### 3.1 那段

```php
// THE REST OF THE EIGHTEEN. Every value here is the one the spec demo's own
// zombie carries on its first asserting frame -- zm_factory_sh entity 673
// life 4, re/demo-re/20-zm-actor-lifecycle.md section 12.1 -- and not one of
// them is a value this server chose.
//
// Several are all-ones "none" sentinels (2047, 2046, 0x00FFFFFF). A ZERO IN
// THEIR PLACE IS NOT A SMALLER VALUE, it is index 0 of whatever they select,
// which is the trap that already cost the scriptmover sentinels a session.
entity.networkState.eFlags = 2;
entity.networkState.actorField0054 = 1.0f;
entity.networkState.actorField005C = 0x00FFFFFFu;
entity.networkState.actorAttackerEntityNum = 2047;
entity.networkState.groundEntityNum = 2047;
entity.networkState.actorLoopSound = 2046;
entity.networkState.actorPartBits0 = 1;
```

### 3.2 十一层

```text
1. **十八个的其余部分**
2. ⇒ **这里每一个值都是 spec demo 自己的僵尸在它【第一个断言帧】上携带的**
3. ⇒ **`zm_factory_sh` 实体 673 生命 4，`re/demo-re/20-zm-actor-lifecycle.md` 第 12.1 节**
4. ⇒ **而没有一个是这个服务器选的**
5. ⇒ **几个是【全一】的"无"哨兵**（`2047`、`2046`、`0x00FFFFFF`）
6. ⇒ **用零代替它们【不是一个更小的值】**
7. ⇒ **它是它们所选东西的【索引 0】**
8. ⇒ **而那正是已经让 scriptmover 的哨兵们花掉一个会话的陷阱**
9. ⇒ `eFlags = 2`
10. ⇒ `actorField0054 = 1.0f`
11. ⇒ `actorField005C = 0x00FFFFFF`
12. ⇒ `actorAttackerEntityNum = 2047`
13. ⇒ `groundEntityNum = 2047`
14. ⇒ `actorLoopSound = 2046`
15. ⇒ `actorPartBits0 = 1`
```

### 3.3 ⭐ **"用零代替它们不是一个更小的值，它是索引 0"**

**✅ 与 §350 的"用零 ⇒ 客户端解析一个被归零的基线"**同族**而更强**。**

**⇒ 三层**：

```text
1. 哨兵值 `2047` 意思是"无"
2. ⇒ **用 0 代替 ⇒ 不是"更小的无"**
3. ⇒ **而是"索引 0 的那个东西"**
4. ⇒ **所以是【一个具体的实体/资源】，不是"无"**
```

**✅ **第六次"零不是缺席而是索引 0"。**

**⚠ 而"已经让 scriptmover 的哨兵们花掉一个会话"⇒ **一次真实的事故**。**

### 3.4 而**三个哨兵的具体值**

```text
2047  = 0x7FF   （11 位全一）⇒ EntityNumNone
2046  = 0x7FE   （11 位次大）⇒ EntityNumWorld
0x00FFFFFF     （24 位全一）⇒ 一个 32 位字段的"无"
```

**✅ 与 §345 的"`EntityNumWorld == 2046`"、§346 的"`EntityNumNone` 推为 2047"**完全一致 ✓**

**⇒ **第三次确认那两个哨兵。**

### 3.5 而 `eFlags = 2` 与 `actorPartBits0 = 1`

**⇒ 两个**非哨兵的小值**。**

**✅ 而 `actorPartBits0 = 1` ⇒ **一个位掩码**（bit 0）。**

**⚠ 与 §345 的"`ActorPartBits0Field` 是 32 位"配合。**

## 四、**三个未测量的字，在一个门下**（本组第三重要）

### 4.1 那段

```php
// THE THREE UNMEASURED WORDS, behind the gate. +0x058's low byte spans
// 0..25 at spawn and its layout changes over the life; +0x0AC is 24 bits
// with nine distinct values; the event slot carries an id whose meaning is
// unread. They are the capture's own spawn-frame values, copied, and they
// are the three most likely to be wrong -- so they turn off together.
if constexpr (SvActorSendUnmeasuredSpawnWords)
{
    entity.networkState.actorField0058 = 0xFF000300u | (uint32)agentSlot;
    entity.networkState.actorField00AC = 6816015;
    entity.networkState.events[0] = SvEntityEvent{ .event = 3, .parameter = 13 };
}
```

### 4.2 九层

```text
1. **三个未测量的字，在【门】后面**
2. ⇒ **`+0x058` 的低字节在生成时跨 `0..25` 而它的布局在生命期里【变化】**
3. ⇒ **`+0x0AC` 是 24 位，有【九个不同的值】**
4. ⇒ **事件槽携带一个 id 而它的意义【未被读出】**
5. ⇒ **它们是捕获自己的生成帧值，被复制**
6. ⇒ **而它们是最可能错的那三个**
7. ⇒ **所以它们【一起关闭】**
8. ⇒ `actorField0058 = 0xFF000300 | agentSlot`
9. ⇒ `actorField00AC = 6816015`（= `0x6801FF`？）
10. ⇒ `events[0] = { event = 3, parameter = 13 }`
```

### 4.3 而**"最可能错的那三个一起关闭"**

**✅ 与 §349 的"未测量 ⇒ 默认不发"**完全同族（**第二次）。**

**⇒ 三层**：

```text
1. 一个开关控制三个
2. ⇒ **因为它们都是"复制自捕获而未验证"**
3. ⇒ **所以一起关**
```

**✅ 一个**正确的分组**（按"不确定性来源"而非"字段位置"）。

### 4.4 而 **`6816015`**

**⇒ 算一下：**

```text
6816015 = 0x6801FF
```

**⚠ 而 `0x6801FF` 是一个**奇怪的值**。**

**⇒ 而注释说"24 位，九个不同的值"。**

**⚠ 所以它是**从九个值里选的一个**。**

**✅ 一个**具体的实测值**。**

## 五、**"字段 29 不是外观"**（本组第四重要）

### 5.1 那段

```php
// FIELD 29 IS NOT THE APPEARANCE. That was tested in game -- all eighteen
// fields sent with a resolved band index here, client ACTIVE, frames clean,
// nothing drawn -- and refuted in the binary (12.4, 12.5). What the field
// does carry is still unknown, so this server sends nothing for it rather
// than inventing a value.
entity.networkState.actorField009C = 0;
```

### 5.2 七层

```text
1. **字段 29【不是】外观**
2. ⇒ **那在游戏里被测过**：
     · **十八个字段全发，这里用一个解析出的带索引**
     · **客户端 ACTIVE**
     · **帧干净**
     · **【什么也没画】**
3. ⇒ **并在二进制里被【反驳】**（12.4、12.5）
4. ⇒ **那个字段实际携带什么【仍未知】**
5. ⇒ **所以这个服务器为它【什么都不发】而不是发明一个值**
```

### 5.3 ⭐ **"游戏里被测过 ⇒ 什么也没画 ⇒ 而二进制反驳"**

**✅ 一个**双重的证伪**（实测 + 反汇编）。**

**⇒ 与 §360 的"崩溃说 `demoq` 是对的"**同族（**第二次"实测胜过先验"**）。**

**⚠ 而这里是**两个独立证据一致**。**

**✅ **最强的证据等级。**

### 5.4 而 **"为它什么都不发而不是发明一个值"**

**✅ 与 §350 的"`SvActorSendUnmeasuredSpawnWords` 默认关闭"**同族（**第十六次"不要猜"**）。

## 六、**"trType 1，两个都是"**

```php
// trType 1 IN BOTH, which is what every one of the 64 measured lives opens
// with. 13 is the terminal state and is not this server's to send yet.
entity.networkState.positionTrajectoryType = 1;
entity.networkState.angleTrajectoryType = 1;
```

### 6.1 五层

```text
1. **两个都是 trType 1**
2. ⇒ **那是 64 条测量的生命里【每一个】开启时的值**
3. ⇒ **13 是终止状态**
4. ⇒ **而它还【不是】这个服务器该发的**
5. ⇒ `positionTrajectoryType = angleTrajectoryType = 1`
```

**✅ 与 §344 的"`positionTrajectoryType == 3`"**不同**（那是**修复的**，这是**生成**）。**

**⚠ 所以**三个轨迹类型**：**

```text
1    生成（64/64 生命）
3    修复动画（§354）
13   终止（尚未发）
7    领奖台相机（§361 九）
```

**✅ **四个值。**

## 七、**"连上并且可被射击"（12.161）**（本组第五重要）

### 7.1 那段

```php
// LINKED AND SHOOTABLE (12.161).
//
// The old note here said a zombie that blocks movement before it can move
// itself would wall the map off, and left `collisionBounds` empty with
// `collisionLinked` false. They move now, and the cost of that caution was
// that a zombie did not exist in the trace world at all: `rebuildCollisionView`
// emits an entity only when `collisionLinked` is set, and `sv_bullet` resolves
// a hit from `trace.hitId`, so no bullet could ever reach one.
entity.collisionShape = SvCollisionShape::Capsule;
entity.collisionBounds = StandingPlayerTraceBounds;
entity.collisionContents = PlayerCollisionContents;
entity.collisionLinked = SvActorLinkCollision;
```

### 7.2 九层

```text
1. **连上并且可被射击（12.161）**
2. ⇒ **旧注释说一个在自己能移动之前阻塞移动的僵尸会把地图【围死】**
3. ⇒ **并让 `collisionBounds` 空、`collisionLinked` 假**
4. ⇒ **它们现在会移动了**
5. ⇒ **而那个谨慎的代价是：一个僵尸在 trace 世界里【根本不存在】**
6. ⇒ **`rebuildCollisionView` 只在 `collisionLinked` 被设时发出一个实体**
7. ⇒ **而 `sv_bullet` 从 `trace.hitId` 解析一次命中**
8. ⇒ **所以【没有子弹能到达一个僵尸】**
```

**✅ 与 §355 的"战斗服 world 从未绑定"**不同**（那是**服务端**的 world，这是**客户端侧碰撞视图**）。**

**⚠ 但**同一个教训**：**

```text
"代码写好了但没接线" ⇒ grep 那个 setter 的调用点
```

**✅ 与记忆里的"battle server world 从未绑定"**完全同族。**

**⇒ **第二次"未接线"。**

### 7.3 而 `StandingPlayerTraceBounds`

**✅ 与 §359 的"完整盒的水平尺寸匹配 `StandingPlayerTraceBounds`"**完全一致 ✓**

**⇒ **第二次确认那个常量名。**

**⚠ 而这里**直接用它做碰撞盒**（不是导航盒）。**

**⇒ 所以**同一个盒子两个用途**。**

## 八、**"没有这些它就永不被发送"**

```php
// WITHOUT THESE IT IS NEVER SENT. The publication gate is `gameplayActive`,
// and the staging pass that sets it for map entities runs on mode changes,
// not every frame -- see the same note on spawnPodiumFigure.
entity.gameplayActive = true;
entity.mapModeEligible = true;
entity.collisionLinked = SvActorLinkCollision;
```

### 8.1 六层

```text
1. **没有这些它就永不被发送**
2. ⇒ **发布门控是 `gameplayActive`**
3. ⇒ **而给地图实体设它的 staging pass 在【模式变化】时运行，不是每帧**
4. ⇒ **所以一个在 `+17000` 创建的实体永不被 staging 而永不被发布**
5. ⇒ `gameplayActive = true` / `mapModeEligible = true`
6. ⇒ **`collisionLinked = SvActorLinkCollision`**（一个开关）
```

**✅ 与 §350 的"`spawnScriptModel` 的两行可见性判据"**完全一致 ✓**

**⇒ **第三次"`gameplayActive` + `mapModeEligible` 两行决定可见性"。**

### 8.2 而 `spawnPodiumFigure` 的同一注释

**✅ 一次**极完整的诊断**：**

```php
// This is what "the figures spawn, the frames validate, and nothing
// draws" actually was: frameReject=none:0 says the entities that WERE
// published validated, and says nothing about an entity that was
// filtered out before it got there.
```

**⇒ 六层**：

```text
1. **"人像生成了、帧验证了、而什么也没画"实际上是什么**
2. ⇒ **`frameReject=none:0` 说【被发布】的实体验证了**
3. ⇒ **而对一个【在到达那里之前就被过滤掉】的实体什么也没说**
4. ⇒ **所以准入统计的"零拒绝"不等于"全部发布"**
```

**✅ 与 §346 的"七十五项合取"**同族（**"沉默"的第三层**）。**

**⇒ **第四次"沉默读起来像健康"。**

## 九、**`spawnPodiumCamera` 的轨迹（七）**

```cpp
if (trajectoryStartTime) {
    constexpr float Pi = 3.14159265358979323846f;
    constexpr float CameraMotionSeconds = 17.0f;
    const auto yaw = place.angles[1] * Pi / 180.0f;
    entity.networkState.positionTrajectoryType = 7;
    entity.networkState.positionTrajectoryTime = trajectoryStartTime;
    entity.networkState.positionTrajectoryDuration = 500;
    entity.networkState.positionTrajectoryDelta = {
        std::cos(yaw) * (50.0f / CameraMotionSeconds),
        std::sin(yaw) * (50.0f / CameraMotionSeconds),
        -15.0f / CameraMotionSeconds,
    };
    entity.networkState.angleTrajectoryType = 7;
    entity.networkState.angleTrajectoryTime = trajectoryStartTime;
    entity.networkState.angleTrajectoryDuration = 500;
    entity.networkState.angleTrajectoryDelta = { 3.0f / CameraMotionSeconds, 0.0f, 0.0f };
}
```

### 9.1 九层

```text
1. **轨迹类型 7**（§361 六 的第四个值）
2. ⇒ **时长 500ms**
3. ⇒ **位移速度 = `(cos(yaw)*50, sin(yaw)*50, -15) / 17s`**
4. ⇒ **所以 17 秒走 50 单位水平 + 15 单位下降**
5. ⇒ **角度速度 = `3.0 / 17s` 每秒**（只有 pitch）
6. ⇒ **17 秒 ⇒ 3 度俯仰**
7. ⇒ **所以相机缓慢平移并下俯**
```

### 9.2 而 **"位移的单位是单位/秒"**

**✅ 与 §354 的"`delta = Δ * (1000/duration)`"**完全一致 ✓**

**⇒ **第三次确认 `delta` 是速度。**

**⚠ 而这里是 `Δ / 秒`（不是 `Δ × 1000/ms`）。**

**✅ **一个更直接的写法**（因为 17 是秒不是毫秒）。

### 9.3 而 `500ms` 的时长与 `17 秒` 的运动

**⇒ 三层**：

```text
1. `duration = 500`（ms）
2. ⇒ **而速度按 17 秒算**
3. ⇒ **所以 500ms 内只走 50/34 ≈ 1.47 单位**
```

**⚠ 所以**`duration` 与速度的"总时长"不同**。**

**⇒ 一个**需要区分的语义**（阶段时长 vs 总运动）。

**✅ 与 §342 的"轨迹类型 3 与 duration 50"**不同。

### 9.4 而**"没有动画索引，因为本 build 不暴露那个命名空间"**

```php
// THE FIGURE'S SECOND FRAME, MINUS THE ANIMATION. Retail spawns a
// podium figure with an int origin and a model and then, 400 ms later,
// asserts a float origin, both trajectory types, field 21 and an
// animation index with its animTime. Three of those five are the same
// on all three of its figures and are set here; the animation index is
// 319/334/349 -- one per place, per map -- and needs an animation-index
// namespace this build does not expose, so it is left alone rather than
// guessed (HANDOFF 139 section 5).
```

**⇒ 十层**：

```text
1. **人像的第二帧，减去动画**
2. ⇒ **零售生成一个人像，用【整数 origin】与一个模型**
3. ⇒ **然后 400ms 后，断言一个【浮点 origin】、两个轨迹类型、字段 21 与一个动画索引及其 animTime**
4. ⇒ **那五个里的三个在三座人像上都相同，而在这里被设**
5. ⇒ **动画索引是 319/334/349 —— 每个位置一个，每张地图**
6. ⇒ **而它需要一个【本 build 不暴露的】动画索引命名空间**
7. ⇒ **所以它被【独处】而不是猜测**（`HANDOFF 139` 第 5 节）
```

**✅ 与 §360 的"字段 29 不是外观 ⇒ 什么都不发"**同族（**第四次"不猜"**）。

**⇒ **四个具体的不猜决策**：**

```text
§360  字段 29 不发明值
§360  三个未测量的字一起关闭
§361  动画索引 319/334/349 独处
§361  字段 29 = 0
```

## 十、`setPodiumFigureAnimation` 的**三条命令序列**

```cpp
if (fadeOutAnimationIndex) append({ SetGoalWeight, ..., animationKey = fadeOutAnimationIndex, weight = 0.0f, rate = 1.0f, blendTime = 0.2f, flags = 0 });
if (clearTree) append({ ClearTree, ..., animationKey = 0, blendTime = 0.2f });
append({ SetGoalWeight, ..., animationKey = animationIndex, weight = 1.0f, rate = 1.0f, blendTime = 0.2f, flags = flags });
```

### 10.1 四层

```text
① fade-out（weight 0）
② clear-tree（若要求）
③ 新的 goal（weight 1）
```

**✅ 而注释说：**

```php
// One transition replaces any still-redundant operation for this
// figure. Commands inside the transition remain ordered: retail's
// exit is weight-zero, clear-tree, then the emote-out goal.
```

**⇒ 五层**：

```text
1. **一次转换替换这个【人像】的任何仍冗余的操作**
2. ⇒ `erase_if(pendingAnimationCommands_, entityNum == ...)`
3. ⇒ **转换内的命令保持有序**
4. ⇒ **零售的退出是：weight-zero → clear-tree → emote-out goal**
5. ⇒ 所以这个顺序是**从零售测得**
```

**✅ 与 §344 的"布告三字段无条件"**同族（**顺序来自实测**）。

### 10.2 而 **`framesRemaining = 4`**

```cpp
pendingAnimationCommands_.push_back({
    .command = std::move(command),
    // MEASURED retail redundancy: a fresh podium operation is
    // present in four consecutive snapshot frames; when an
    // equal delta baseline is selected the wire reuses it.
    .framesRemaining = 4,
});
```

**⇒ 五层**：

```text
1. **测量的零售冗余：一个新的人像操作【出现在四个连续快照帧里】**
2. ⇒ **当选择一个相等的 delta 基线时，线上【复用它】**
3. ⇒ **所以 `framesRemaining = 4`**
```

**✅ 与 §341 的"11,048 次提到 vs 零售零次"**不同** —— 这里是**零售确实重复**。**

**⇒ **一个极重要的区分**：**

```text
clientInfo   零售【零次】重复 ⇒ 我们也零次
动画命令     零售【四次】重复 ⇒ 我们也四次
```

**✅ **两条相反的规则、都来自实测。**

## 十一、`revealPodiumFigures` 的**两个分支**

```cpp
for (auto &[number, entity] : entities_) {
    if (entity.mapClassName == "podium_weapon" && entity.networkState.eType == EntityTypeScriptMover) {
        entity.networkState.eFlags &= ~SvEFlagsNoDraw;
        continue;
    }
    if (entity.mapClassName != "podium_figure" || entity.networkState.eType != EntityTypeScriptMover)
        continue;
    entity.networkState.eFlags &= ~SvEFlagsNoDraw;
    entity.networkState.positionTrajectoryType = 1;
    entity.networkState.angleTrajectoryType = 1;
    entity.networkState.scriptMoverField0070 = 1;
}
```

### 11.1 三层

```text
① `podium_weapon`  ⇒ 只清 `NoDraw`
② `podium_figure`  ⇒ 清 `NoDraw` + 两个轨迹类型 = 1 + `field0070 = 1`
③ 其它 ⇒ 跳过
```

**✅ 而注释解释：**

```php
// CODREF(retail DM 648800, absolute decode): all three figures clear
// eFlags 16 -> 0, set pos/apos type 1 and +0x70 = 1 together. Restrict
// this to our podium figures and weapons: the camera and intermission
// players must remain hidden. Reapplying after the boundary is safe.
```

**⇒ 六层**：

```text
1. **全部三座人像把 eFlags 16 → 0**
2. ⇒ **设 pos/apos 类型 1 与 `+0x70 = 1`【一起】**
3. ⇒ **限制到我们的人像与武器**
4. ⇒ **相机与中场玩家必须【保持隐藏】**
5. ⇒ **在边界之后重新施加是安全的**
6. ⇒ **`eFlags 16` = bit 4**
```

**✅ 与 §361 六的"`positionTrajectoryType = 1` 是生成态"**配合。**

**⇒ 而这里是**从隐藏到显示**（用类型 1 作为"显示"）。**

**⚠ 所以**类型 1 有两个用途**（生成 + 显示）。**

**✅ 合理。**

### 11.2 而 `SvEFlagsNoDraw` = 16

**⇒ 三层**：

```text
1. `eFlags` bit 4 = 不画
2. ⇒ **清它 ⇒ 画**
3. ⇒ **而 §361 六 的 `eFlags = 2`（bit 1）**是另一个标志
```

**✅ 与 §361 三的"`eFlags = 2`"配合。**

**⚠ 所以**两个 `eFlags` 位**：**

```text
bit 1 (2)   生成时（可能"活动"？）
bit 4 (16)  不画
```

**✅ 一个**位掩码**。**

## 十二、关键结论

1. **⭐⭐ "`0xFF0003NN` —— 两个字节都重要而它们做不同的事"`** —— `+0x58` 记录槽（`sub_530BB0` 用 `centity+332` 索引 684 字节记录数组）、`+0x59` 指针索引（`sub_52FBE0` 读 `record[0x18 + 4*centity+333]`）。
2. **零售僵尸 671 携带 `0xFF000303`** —— 记录槽 3、指针索引 3、而槽 3 的拥有者字段读 671。
3. **十三个槽里只有索引 3 与 4 非空，而 0/1/2/5 在所有工作僵尸上都是空`**。
4. **"这个服务器发 `0xFF0000NN` ⇒ 字节 1 是零 ⇒ 每个 actor 选了空的 `ptrs[0]`"`**。
5. **"DObj 用空资源构建 ⇒ 无骨骼数组 ⇒ 客户端抛 `25 j_spine4 <ent>` ⇒ 红色 FX 占位符"`** —— 一个极具体的视觉症状。
6. **⭐ 十八个 spawn 字段全部来自零售第一帧**（`zm_factory_sh` 实体 673 生命 4，12.1）。
7. **⭐ "几个是全一的『无』哨兵（2047、2046、0x00FFFFFF）—— 用零代替【不是一个更小的值】，它是它们所选东西的索引 0"`** —— **第六次"零不是缺席而是索引 0"**。
8. **三个哨兵的具体值确认**（`2047` EntityNumNone / `2046` EntityNumWorld / `0x00FFFFFF`）。
9. **⭐ 三个未测量的字在一个门下一起关闭**（`+0x058` 布局变化 / `+0x0AC` 九个值 / 事件 id 意义未读）。
10. **⭐ "字段 29 不是外观"** —— **游戏里测过（十八字段全发、ACTIVE、帧干净、什么也没画）而二进制反驳**，所以**什么都不发**。
11. **"trType 1 两个都是，那是 64 条测量的生命里每一个开启时的值；13 是终止态"`** —— **四个轨迹类型**（1 生成 / 3 修复 / 7 相机 / 13 终止）。
12. **⭐ "连上并且可被射击"（12.161）** —— 旧的谨慎（空 `collisionBounds` + `collisionLinked` false）让**僵尸在 trace 世界里根本不存在** ⇒ **没有子弹能到达它**。
13. **"`rebuildCollisionView` 只在 `collisionLinked` 被设时发出实体"`** —— 与记忆的"battle server world 从未绑定"**同族（第二次"未接线"）**。
14. **`StandingPlayerTraceBounds` 同时用作导航盒（§359）与碰撞盒（这里）`**。
15. **⭐ "没有这两行它就永不被发送"`** —— `gameplayActive` 由**模式变化时的 staging pass** 设置，而非每帧。
16. **⭐ "`frameReject=none:0` 说【被发布】的实体验证了，而对一个【在到达那里之前就被过滤掉】的实体什么也没说"`** —— **第四次"沉默读起来像健康"**。
17. **领奖台相机的轨迹类型 7**：17 秒内 50 单位水平 + 15 单位下降 + 3 度俯仰，而 `duration = 500ms`（阶段时长 ≠ 总运动）。
18. **第三次确认 `delta` 是速度**（这里是 `Δ / 秒` 而非 `Δ × 1000/ms`）。
19. **⭐ "动画索引 319/334/349 需要一个本 build 不暴露的命名空间，所以独处而不猜"`** —— **四个具体的不猜决策**。
20. **三条命令序列（weight-zero → clear-tree → 新 goal）来自零售实测**。
21. **⭐ `framesRemaining = 4`** —— **"一个新的人像操作出现在四个连续快照帧里"`** —— 与 §341 的"clientInfo 零售零次重复"**形成极重要的对照**。
22. **`revealPodiumFigures` 的两分支**：武器只清 `NoDraw`、人像还设两个轨迹类型与 `field0070`。
23. **`SvEFlagsNoDraw = 16`（bit 4）与 `eFlags = 2`（bit 1）** —— 两个不同的位。

## 十三、未闭合点

- `actorField00AC = 6816015` 的九个值。
- `actorField0054 = 1.0f` 的语义。
- `actorPartBits0 = 1` 的位含义。
- `eFlags = 2`（bit 1）的语义。
- 字段 29 究竟携带什么。
- `sv_snapshot_mp.cpp` 16400 行之后未读取（27,016 行，进度 61%）。
