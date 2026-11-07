# 268 · **actor 700..707 打不中的真相**、`isLinked` 我们写零、512 不是 256

## 一、范围

本报告学习 `EngineBindings.cpp` 18250–18450 行。

## 二、候选取的**五层过滤**（与 DObj 姿态共用的集合）

```php
std::vector<SvCollisionEntity> locationalCandidates;
locationalCandidates.reserve(std::min<std::size_t>(entities.size(), 16));
for (const auto &entity : entities)
{
    if (entity.shape != Capsule && entity.shape != ScriptModelDObj) continue;
    if (!SV_ShouldClipToEntity(entity, request.filter, request.contentMask) ||
        !SV_ShouldBroadphaseClipToEntity(request.start, request.end, PointTraceBounds, entity))
        continue;
    locationalCandidates.push_back(entity);
}
```

### 2.1 **`reserve(min(size, 16))`**

**⇒ 预留 16 个 —— 一个乐观的估计。**

**⇒ 而 §268 的注释说"trace 自己的宽相随后拒绝了几乎全部" ⇒ 所以实际上候选很少。**

### 2.2 **与 §266 的 `traceServerLocationalEntities` 内部过滤完全相同**

**⇒ 所以过滤被做了**两遍**：**

```text
① 建候选集时    （为 prepareNativeServerDObjPoses）
② 函数内部再过滤（traceServerLocationalEntities 自己也查 ShouldClip / Broadphase）
```

**⇒ 冗余但安全** —— 因为 `traceServerLocationalEntities` 是可复用的。

## 三、**`posesPrepared && traceServerLocationalEntities`**

```php
const auto posesPrepared = prepareNativeServerDObjPoses(candidateView, request.contentMask, exceptionDetails);
auto aggregate = *worldTrace;
auto invoked = posesPrepared &&
    traceServerLocationalEntities(request, priorityMap, candidateView, aggregate, exceptionDetails);
const auto animConditionBaseRestored = restoreServerAnimConditionStorage(previousAnimConditionBase);
```

### 3.1 **`&&` 短路**

**⇒ 如果姿态准备失败，`traceServerLocationalEntities` 不跑。**

**⇒ 而 `aggregate` 保持 `*worldTrace`。**

### 3.2 而 `restore` 在**两者之后**

**⇒ 所以无论 `invoked` 真假，`restore` 都会执行** ✓

### 3.3 而 `aggregate = *worldTrace` 是**拷贝**

**⇒ 所以 `worldTrace` 本身不被修改。**

## 四、**actor 700..707 打不中的真相**（本组最重要的一段）

### 4.1 那段实测

```php
// Actor DObjs are valid presentation objects, but CODOL's retained
// locational walker does not reliably return their entity id on a
// dedicated server.  The live Factory trace proves the failure:
// actors 700..707 are linked and pass broadphase within a few units
// of the shot axis, while the result remains a farther world hit
// with no entity id.  That makes the otherwise complete generic
// entity-damage path unreachable.
```

### 4.2 六层

```text
1. Actor 的 DObj 是合法的表现对象
2. 但 CODOL 保留的定位遍历器在专用服上【不可靠地返回它们的实体 id】
3. 实测：actor 700..707 已链接、在射线几单位内通过宽相
4. 而结果【仍是一个更远的世界命中，没有实体 id】
5. ⇒ 这让否则完整的通用实体伤害路径【不可达】
6. ⇒ 所以 §268 加了覆盖层
```

### 4.3 而"700..707"是**八个 actor**

**⇒ `zm_factory` 的敌人编号从 700 开始。**

### 4.4 那句"通用实体伤害路径不可达"

**⇒ 所以**即使**所有其他部分都对，actor 也打不到。**

**⇒ 这与记忆里"战斗服 world 从未绑定"是**不同的**层**：

```text
记忆    服务端自己的世界绑定缺失
§268    【原生】定位遍历器对 actor 不返回 entity id
```

**⇒ 两个独立的缺陷，都会有"打不到"的症状。**

## 五、**覆盖层只处理非客户端 Capsule**（本组第二重要）

```php
for (const auto &entity : candidateView)
{
    if (entity.entityNum < MaximumGameClients ||
        entity.shape != SvCollisionShape::Capsule)
    {
        continue;
    }
    // OLMOD(actor_skeletal_precedence): an admitted posed actor
    // already received a native bone trace, including its misses.
    // A nearer broad capsule must not erase partGroup/partName or
    // turn an actual gap between posed limbs into a body hit.
    if (entity.actorHitPose && entity.entityNum < actorHitPoseOwners_.size() &&
        actorHitPoseOwners_[entity.entityNum].dobj &&
        !actorHitPoseOwners_[entity.entityNum].failed &&
        serverDObjGetAdapter((int)entity.entityNum) == actorHitPoseOwners_[entity.entityNum].dobj)
        continue;
    const auto capsuleTrace = traceTransformedCapsule(aggregate, request.start, request.end, PointTraceBounds, entity);
    if (!capsuleTrace) { invoked = false; break; }
    static_cast<void>(SV_ApplyEntityTraceHit(aggregate, *capsuleTrace, entity));
    if (aggregate.fraction == 0.0f) break;
}
```

### 5.1 两个 `continue` 条件

```text
① entityNum < MaximumGameClients     ⇒ 跳过（这是玩家）
② shape != Capsule                   ⇒ 跳过
```

### 5.2 **`entityNum < MaximumGameClients` ⇒ 玩家被跳过**

**⇒ 所以覆盖层**只处理 actor**。**

**⇒ 而注释解释**：

```php
// Players retain native DObj locational hit groups, and actors remain
// absent from the ordinary Pmove collision view.
```

```text
玩家    保留原生 DObj 定位命中组   （所以不用覆盖）
actor   在普通 Pmove 碰撞视图里【缺席】（所以需要覆盖）
```

### 5.3 **第二个 `continue` 是"姿态优先"**

```php
// OLMOD(actor_skeletal_precedence): an admitted posed actor
// already received a native bone trace, including its misses.
// A nearer broad capsule must not erase partGroup/partName or
// turn an actual gap between posed limbs into a body hit.
```

### 5.4 四层

```text
1. 一个【已被接纳的】摆好姿态的 actor 已经收到原生骨骼 trace（包括它的失误）
2. ⇒ 一个更近的【粗略胶囊】不能抹掉 partGroup/partName
3. ⇒ 也不能把【摆好姿态的肢体之间真实的空隙】变成身体命中
4. ⇒ 所以跳过
```

**⇒ 这是一个"精确优先于粗略"的规则** —— 即使粗略的给出更近的值。

**⇒ 与 §266 的"`result.fraction` 必须更好"**相反**：那里"更近就采纳"，这里"精确的即使更远也保留"。**

**⚠ 这是一处重要的语义差别** —— 而它由 `actorHitPose` 标志控制。

### 5.5 而那个五项 AND 是"姿态仍然有效"的验证

```text
entity.actorHitPose                              标志
entity.entityNum < actorHitPoseOwners_.size()    界
actorHitPoseOwners_[n].dobj                      非空
!actorHitPoseOwners_[n].failed                   没失败
serverDObjGetAdapter(n) == ...dobj                【引擎当前返回的 DObj 就是那个】
```

**⇒ 第五项是**代际检查**（与 §265 的 `gEntities_` 指针检查同族）。**

### 5.6 而 `invoked = false; break;` 在 trace 失败时

**⇒ 一个胶囊 trace 失败 ⇒ 整个 `invoked` 变 false ⇒ 后面返回 nullopt。**

**⇒ 这比"跳过这个实体"严格。**

## 六、**`isLinked` 的真相**（本组第三重要）

```php
// OLMOD(locational-candidacy-diagnostics): report the words the
// NATIVE trace reads, not the source mirror it was built from. The
// capsule log in Appmain prints SvCollisionEntity::linked, which is
// this project's own flag; CM_PointTraceToEntities instead reads
// gentity +0x110 isLinked, +0x112 svFlags and +0x12C contents, and
// SV_ToNativeServerEntity deliberately writes isLinked as ZERO and
// leaves SV_LinkEntity to set it. A respawned player that the
// source believes is linked but the native never linked looks
// exactly like the measured symptom: capsule present, linked=1,
// maxsZ=70, ray 2.5 units off its axis, and no hit for a whole
// magazine while the same setup hit at 103 units before the death.
```

### 6.1 四个事实

```text
1. `SvCollisionEntity::linked` 是【我们自己的】标志
2. 原生 `CM_PointTraceToEntities` 读的是 `gentity +0x110` 的 `isLinked`
3. `SV_ToNativeServerEntity` 故意把 `isLinked` 写成【零】，留给 `SV_LinkEntity` 设置
4. ⇒ 一个「源认为已链接但原生从未链接」的玩家，看起来【完全像】实测症状
```

### 6.2 而实测症状的五个数

```text
胶囊存在
linked=1            （源标志）
maxsZ=70
射线偏离轴 2.5 单位
整弹匣无命中
```

**⇒ 而"同样的设置在死亡前 103 单位处能打中"。**

### 6.3 **这是"两个 linked"的混淆**

```text
SvCollisionEntity::linked   我们的
gentity +0x110 isLinked     引擎的
```

**⇒ 名字相同、语义相同、但**两个不同的存储**。**

**⇒ 而我们的写零、引擎的由 `SV_LinkEntity` 设置。**

**⇒ 如果 `SV_LinkEntity` 没被调用（例如重生后），引擎的 `isLinked` 保持零 ⇒ **原生遍历器跳过这个实体**。**

**⇒ 这就是"重生后打不到"的完整解释。**

### 6.4 而 `+0x110`/`+0x112`/`+0x12C` 是三个 gentity 字段

```text
+0x110   isLinked
+0x112   svFlags        ← 与 §265 的 svFlags 一致
+0x12C   contents
```

**⇒ 而 §265 里说 `svFlags bit 2 = 0x04` 在 `+0x112`** ✓ 一致。

**⇒ 而 `+0x11A` 是**另一个**偏移**（§265 说"本 build 没有 `test byte [reg+0x11A], 4`"）。

**⇒ 所以 `+0x112`（3.3.3.3）与 `+0x11A`（本 build 不存在）是两个不同的搜索目标。**

### 6.5 那个 `TODO(CODOL): remove once a post-respawn player is hittable`

**⇒ 明确标注"重生后玩家能打中之后移除"。**

**⇒ 所以这个问题**未解决**。**

## 七、异常详情的**十四项**

```php
"native locational point trace unavailable code=0x%08lX "
"address=%p access=%llu fault=%p "
"eax=%p ebx=%p ecx=%p edx=%p esi=%p edi=%p "
"ebp=%p esp=%p eip=%p"
```

### 7.1 十四项

```text
code, address, accessType, faultAddress
eax, ebx, ecx, edx, esi, edi
ebp, esp, eip
```

**⇒ 四个异常信息 + **十个**寄存器。**

**⚠ 缺 `eflags`（而对某些 fault 有用）。**

### 7.2 而 `accessType` 是 `%llu`

**⇒ 所以它是一个枚举或位掩码。**

## 八、`validateMessageBindings`：**512 不是 256**（本组第四重要）

### 8.1 第一段：`MSG_Init` 的七项

```php
std::array<std::uint8_t, 64> buffer{};
msg_t message{};
MSG_Init(message, buffer.data(), 64);
if (message.overflowed || message.readOnly || message.data != buffer.data() ||
    message.maxsize != 64 || message.cursize || message.bit)
    return false;
```

**⇒ 六项条件**：

```text
overflowed == 0
readOnly == 0
data == buffer
maxsize == 64
cursize == 0
bit == 0
```

**⇒ 注意 `bit == 0`** —— 所以 `msg_t` 有 `bit` 字段（位级写入的当前位偏移）。

**⇒ 与记忆里"`msg_t` 0x30 with 32-bit-only asserts"一致。**

### 8.2 第二段：`MSG_WriteBits(0x78, 8)`

```php
MSG_WriteBits(message, 0x78, 8);
if (message.overflowed || message.cursize != 1 || message.bit != 8 || buffer[0] != 0x78)
    return false;
```

**⇒ 四项**：

```text
cursize == 1    （写了一个字节）
bit == 8        （位偏移 8）
buffer[0] == 0x78
```

**⇒ 验证"位写入推进到字节边界"。**

### 8.3 第三段：`MSG_WriteString("codol")`

```php
MSG_Init(message, buffer.data(), 64);
MSG_WriteString(message, "codol");
if (message.overflowed || message.cursize != 6 || memcmp(buffer.data(), "codol\0", 6) != 0)
    return false;
```

**⇒ 三项**：

```text
cursize == 6    （5 个字符 + NUL）
内容逐字节相同
```

**⇒ 验证"字符串写入带 NUL 终止"。**

### 8.4 第四段：**512 字节的 gamestate**

```php
// 512, NOT 256. The serverinfo now carries retail's ten measured keys
// (see formatServerInfo) and the gamestate is ~277 bytes; at 256 this
// writer overflowed and the stage failed for lack of room rather than
// for a real mismatch.
std::array<std::uint8_t, 512> gameStateBuffer{};
EngineMsgWriter writer(*this, gameStateBuffer);
SvGameState gameState{ .mapName = "mp_crash", .gameType = "tdm" };
SV_PopulateRequiredConfigStrings(gameState);
gameState.configStrings.emplace(TimescaleConfigStringIndex, "0 0 1 1");
```

### 8.5 四个数

```text
512     缓冲区
~277    gamestate 实际大小
256     旧缓冲区（溢出）
10      serverinfo 的键数
```

**⇒ "在 256 时这个写入器溢出了，而这个阶段因为在**空间不足**上失败而不是在**真正的不匹配**上失败。"**

**⇒ 这是一个"假的失败" —— 测试自己坏了。**

**⇒ 第 N 次"仪器坏了读起来像被测对象坏了"。**

### 8.6 而 `SV_PerfBaseline` 的**特殊处理**

```php
// OLMOD_PERF_BASELINE deliberately suppresses the vision configstrings, so
// SvGameStateFixtureBytes stops describing what the writer produces and this
// stage would fail on the mode rather than on a defect -- which took the
// dedicated down once already. The write is still exercised; only the byte
// comparison is skipped, and only in the diagnostic mode.
if (SV_PerfBaseline())
    return SV_WriteGameState(writer, gameState, 0, 0);
return SV_WriteGameState(writer, gameState, 0, 0) &&
    std::ranges::equal(writer.data(), SvGameStateFixtureBytes);
```

### 8.7 三层

```text
1. `OLMOD_PERF_BASELINE` 故意抑制 vision 配置串
2. ⇒ `SvGameStateFixtureBytes` 不再描述写入器的输出
3. ⇒ 这个阶段会在【模式】上失败而不是在【缺陷】上
4. ⇒ 而它【已经让专用服挂过一次】
```

**⇒ 所以 perf baseline 模式下**跳过字节比较**，但仍**执行写入**。**

**"只跳过字节比较，且只在诊断模式下。"**

**⇒ 这是一个正确的"诊断模式不应触发自检"处理。**

### 8.8 而 `TimescaleConfigStringIndex` 被显式加

```php
gameState.configStrings.emplace(TimescaleConfigStringIndex, "0 0 1 1");
```

**⇒ 记忆里"`11861` timescale"** ✓

**⇒ 而值 `"0 0 1 1"` 是一个四元组。**

## 九、`EngineMsgWriter` 的**溢出检查**

```php
EngineMsgWriter::EngineMsgWriter(const EngineBindings &bindings, const std::span<std::uint8_t> buffer)
    : bindings_(bindings)
{
    if (buffer.size() > (size_t)numeric_limits<int32_t>::max())
    {
        message_.overflowed = 1;
        return;
    }
    bindings_.MSG_Init(message_, buffer.data(), (int32_t)buffer.size());
}

void EngineMsgWriter::MSG_WriteData(const std::span<const std::uint8_t> value)
{
    if (message_.overflowed || message_.cursize < 0 ||
        message_.maxsize < message_.cursize ||
        value.size() > (size_t)(message_.maxsize - message_.cursize))
    {
        message_.overflowed = 1;
        return;
    }
    if (value.empty()) return;
    memcpy(message_.data + message_.cursize, value.data(), value.size());
    message_.cursize += (int32_t)value.size();
}
```

### 9.1 构造函数的两项

```text
buffer 大小 <= INT32_MAX
否则标记 overflowed 且【不调 MSG_Init】
```

**⚠ 如果 `MSG_Init` 没被调用，`message_` 保持值初始化（全零）⇒ `data == nullptr`。**

**⇒ 而后续 `MSG_WriteData` 会因 `overflowed` 而早退** ✓

**⇒ 安全。**

### 9.2 `MSG_WriteData` 的四项

```text
!overflowed
cursize >= 0                    ← 【防负】
maxsize >= cursize              ← 【防 maxsize 被破坏】
value.size() <= maxsize - cursize  ← 【防溢出，且无符号减法】
```

**⇒ 第三项是关键：`maxsize - cursize` 在两个都非负时安全。**

**⇒ 而第二项保证 `maxsize - cursize >= 0`** ✓

**⇒ 四项的顺序正确。**

### 9.3 而 `value.empty()` 在检查**之后**

**⇒ 空写入不改变 `cursize` 也不标记溢出。**

**✓ 正确。**

## 十、关键结论

1. **候选集过滤做两遍**（建集时 + 函数内部），因为 `traceServerLocationalEntities` 可复用。
2. **`reserve(min(size, 16))`** 是一个乐观估计。
3. **actor 700..707 在专用服上打不中** —— 定位遍历器不返回它们的 entity id，而结果是一个更远的世界命中。
4. **覆盖层只处理 `entityNum >= MaximumGameClients` 的 Capsule**（即 actor 而非玩家）。
5. **"姿态优先"规则**：已摆好姿态的 actor 收到过原生骨骼 trace ⇒ 更近的粗略胶囊不能覆盖它。
6. **五项 AND 验证姿态仍有效**，第五项是代际检查（引擎当前 DObj == 我们记录的）。
7. **`isLinked` 有两个**：`SvCollisionEntity::linked`（我们的）与 `gentity+0x110`（引擎的）；我们**故意写零**。
8. **"重生后打不到"的完整解释** —— 引擎的 `isLinked` 从未被 `SV_LinkEntity` 设置。
9. **实测症状五个数**：胶囊存在、`linked=1`、`maxsZ=70`、射线偏 2.5 单位、整弹匣无命中。
10. **`TODO` 明确标注未解决**。
11. **异常详情十四项但缺 `eflags`**。
12. **`validateMessageBindings` 的四段**（`MSG_Init` 六项、位写四项、串写三项、gamestate 字节比较）。
13. **512 不是 256** —— gamestate 约 277 字节，256 会让测试因空间不足而非真不匹配而失败。
14. **`OLMOD_PERF_BASELINE` 跳过字节比较但仍执行写入** —— 因为该模式故意抑制 vision 配置串。
15. **`EngineMsgWriter` 的四项溢出检查顺序正确**。

## 十一、未闭合点

- `SV_LinkEntity` 在重生路径里是否被调用（若否，这是"重生后打不到"的修法）。
- `MaximumGameClients` 的值。
- `actorHitPoseOwners_` 的维护逻辑。
- `exceptionDetails` 缺 `eflags` 是否影响诊断。
- `EngineBindings.cpp` 18450 行之后未读取。
