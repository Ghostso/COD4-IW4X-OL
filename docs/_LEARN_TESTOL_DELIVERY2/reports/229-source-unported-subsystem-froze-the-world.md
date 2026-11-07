# 229 · 一个"设计上的降级"如何冻结整个世界

## 一、范围

本报告学习 `EngineBindings.cpp` 6905–7104 行。

## 二、`DesiredEntity` 的构造：两个严格对齐

```cpp
if (entity.shape == SvCollisionShape::Capsule)
{
    if (entityStateIndex >= entityStates.size() ||
        entityStates[entityStateIndex].entityNum != entity.entityNum)
        return failed("entity_state_missing", entity.entityNum);
    entityState = entityStates[entityStateIndex++].state;
    customization = entityStates[entityStateIndex - 1].customization;
    spawnGeneration = entityStates[entityStateIndex - 1].spawnGeneration;
    if (!entityState) return failed("entity_state_null", entity.entityNum);
}
if (entityStateIndex != entityStates.size())
    return failed("entity_state_orphan");
```

### 2.1 三条对齐规则

```text
1. capsule 必须有一个 entityState，且【实体号相同】
2. 游标严格顺序推进
3. 结束时【必须用完】—— 否则 "orphan"
```

**`entityStateIndex++` 之后立刻 `entityStateIndex - 1`** —— 因为要先取 `state` 再取另两项。

**这是同一个数组的两次索引** —— 可以合并成一个引用：

```cpp
const auto& source = entityStates[entityStateIndex++];
entityState = source.state;
customization = source.customization;
spawnGeneration = source.spawnGeneration;
```

**当前写法是对的但重复了三次索引。**

### 2.2 只有 capsule 需要 entityState

**`ScriptModelDObj` 与 `BrushModel` 不需要** —— 所以它们不消耗 `entityStates`。

## 三、`ensurePlayerDObjs`：备份两个半

### 3.1 为什么必须备份两半

```cpp
// The characterInfo BYTES now live in the shared anim-condition
// region rather than inside the slot, so copying the slot alone no
// longer rolls this transaction back. Save both halves.
struct CharacterInfoBackup
{
    std::uint32_t entityNum{};
    NativeServerCharacterInfoSlot slot;                                    // 记账
    std::array<std::byte, SvNativeCharacterInfoSize> bytes{};              // 实际字节
};
```

**"字符信息的字节现在住在共享的 anim-condition 区域而不是槽内，所以只复制槽不再回滚这个事务。保存两半。"**

**这正是 §216 里"一份缓冲两个消费者"的后果** —— 槽只持有 ol-mod 的记账，字节在共享区。

### 3.2 `std::array<byte, 0x450>` 逐个拷贝

```cpp
std::ranges::copy(serverCharacterInfo(entry.source.entityNum), backup.bytes.begin());
```

**每玩家 0x450 = 1104 字节** —— 18 个玩家 = 19,872 字节的备份。

**每帧都做**（因为 `ensurePlayerDObjs` 在 Presentation 阶段跑）。

## 四、`CustomizationAbsent` 的报与撤

### 4.1 两个分支

```cpp
if (entry.source.bodyRole != Player ||
    entry.source.entityNum >= nativeServerCharacterInfo_.size() ||
    !entry.customization)
{
    if (entry.source.bodyRole == Player && !entry.customization)
        reportPlayerDObjState(entityNum, PlayerDObjState::CustomizationAbsent);
    continue;
}
releasePlayerDObjReportedState(entityNum, PlayerDObjState::CustomizationAbsent);
```

### 4.2 那段"到达是正常情形"

```cpp
// The customization has arrived, so the report above is now
// stale. Drop it silently -- the arrival is the NORMAL case and
// an instrument must be quiet when nothing is wrong - but drop
// it, because leaving it latched is what kept the three later
// states from ever reporting.
```

**"到达是正常情形，而仪器在没有问题时必须安静 —— 但必须撤掉它，因为留着它闩住正是让后面三个状态从来无法报告的原因。"**

**这是 §225 里那个"31 次全中"的修复**。

## 五、那个"3981 行 / 110 秒"的日志洪水

```cpp
if (!dobjUpdated)
{
    // Deduped on (entity, stage). This is a KNOWN degraded path --
    // model_resolution_unported_olfinal, sec 16a -- and it fired twice
    // per frame, 3981 lines in a 110-second run. A permanent condition
    // is worth saying once per distinct condition, not 36 times a
    // second; the count is not the information, the stage is.
    static std::string reported;
    auto details = to_string(entityNum) + " stage=" + failureStage;
    if (reported != details) { reported = details; log(...); }
}
```

### 5.1 数字

```text
每帧两次
110 秒 3981 行
≈ 36 次/秒
```

### 5.2 那句"数量不是信息，阶段才是"

**"A permanent condition is worth saying once per distinct condition, not 36 times a second; the count is not the information, the stage is."**

## 六、**一个"设计上的降级"如何冻结整个世界**（本组最重要的一段）

### 6.1 六步因果链

```cpp
// AN UNPORTED SUBSYSTEM MUST NOT STOP THE WORLD. OLfinal has no
// counterpart for 3.3.3.3's selector/slot-base/name-table model
// resolution (section 16a), so resolveCharacterModelNames always
// fails here and the surrounding comments already call that a
// by-design degradation. It was not degrading. It failed the entity
// mirror, which made SvServerWorld::endFrame roll back and return
// false, which made the frame return before publishing -- so
// worldFrame_->serverTime froze, every following snapshot was
// rejected as duplicate_server_time, and the player who had just
// spawned correctly saw the world stop dead. Cosmetic absence, total
// desync.
```

**完整链条**：

```text
1. resolveCharacterModelNames 总是失败（设计上的降级）
2. 它让实体镜像失败
3. ⇒ SvServerWorld::endFrame 回滚并返回 false
4. ⇒ 该帧在发布之前返回
5. ⇒ worldFrame_->serverTime 冻结
6. ⇒ 每一个后续快照被拒为 duplicate_server_time
7. ⇒ 刚正确出生的玩家看到世界完全静止
```

**"Cosmetic absence, total desync."**

**"外观缺失，整体失步"** —— 一句极精确的总结。

### 6.2 为什么"继续"是安全的，且**只在这里**

```cpp
// Continuing is safe HERE and only here: the resolution fails at the
// top of the update, before any native or hunk mutation, so the
// rollback above is complete and irreversibleMutationStarted is
// false. Any other stage, and anything that has already touched
// native state, keeps the fail-stop -- that guard exists because a
// half-mutated DObj pool cannot be recovered short of level restart.
```

**三个条件同时成立才继续**：

```cpp
if (failureStage == "model_resolution_unported_olfinal" &&
    !priorIrreversibleMutation && !irreversibleMutationStarted)
```

```text
1. 阶段必须是 model_resolution_unported_olfinal
2. 本批次【之前】没有不可逆变更
3. 本实体也没有
```

**理由**：

> **"解析在更新【顶部】失败，在任何原生或 hunk 变更之前，所以上面的回滚是完整的，而 `irreversibleMutationStarted` 是 false。任何其它阶段，以及任何已经触碰原生状态的东西，保持 fail-stop —— 那个守卫存在是因为一个半变异的 DObj 池除了关卡重启之外无法恢复。"**

### 6.3 那个 fail-stop 的语义

```cpp
nativeServerPlayerDObjPoisoned_ = priorIrreversibleMutation || irreversibleMutationStarted;
```

**一旦毒化，`ensurePlayerDObjs` 的开头就返回 false**：

```cpp
if (nativeServerPlayerDObjPoisoned_)
{
    failedPlayerDObjStage = "poisoned";
    return false;
}
```

**所以"毒化"是终态** —— 直到 `initializeLevelWorld` 清理。

**而 §217 里 `resetNativeServerEntityMirrorAfterWorldInitialization` 有 `nativeServerPlayerDObjPoisoned_ = false`** ✓

### 6.4 `priorIrreversibleMutation` 的累加

```cpp
priorIrreversibleMutation = priorIrreversibleMutation || irreversibleMutationStarted;
```

**在**成功路径**上累加**：

```cpp
if (dobjUpdated) { priorIrreversibleMutation = ...; ...; continue; }
```

**所以"前面某个玩家成功了且它有不可逆变更" ⇒ 后面某个玩家失败时不能继续。**

**这是一个"批次级"的传染判断** —— 因为 DObj 池是共享的。

## 七、`nativeServerPlayerDObjObservedSuccess_` 的三条件

```cpp
if (!nativeServerPlayerDObjObservedSuccess_ ||
    !nativeServerPlayerDObjFailure_.empty())
{
    log("native server player DObj active entity=" + to_string(entityNum));
}
nativeServerPlayerDObjObservedSuccess_ = true;
nativeServerPlayerDObjFailure_.clear();
```

**与 §228 里 `synchronized` lambda 完全同构**：

```text
首次成功 或 曾失败过 ⇒ 记录
然后置真、清失败
```

## 八、`CharacterInfoBackup` 的回滚

```cpp
for (const auto& backup : backups)
{
    nativeServerCharacterInfo_[backup.entityNum] = backup.slot;
    std::ranges::copy(backup.bytes, serverCharacterInfo(backup.entityNum).begin());
}
```

### 8.1 **恢复所有**，不是只恢复失败的

**`for (const auto& backup : backups)`** —— 遍历**全部**备份。

**因为前面的玩家可能已经成功改了状态，而这次失败要整体回滚。**

**这是一个"批次事务"的语义** —— 任一失败则全批回滚。

### 8.2 但"成功"的玩家已经改了 DObj

**注意：`characterInfo` 回滚了，但 DObj 没有回滚**（DObj 的创建是不可逆的）。

**所以这个回滚是【不完整的】** —— 而注释承认了这一点：

> **"`SvNativeCharacterInfoSlot` 与字节都恢复了，但 DObj 池不行。"**

**实际上注释只说"保存两半"，没说"DObj 不能回滚"** —— 但 §229 开头那段 `CODDIFF` 说了：

> **"与槽/链接替换不同，原生玩家 DObj/XAnim 调用不暴露回滚结果。"**

## 九、关键结论

1. **`entityStates` 必须与 capsule 严格一一对齐**，多余的报 `orphan`。
2. **`characterInfo` 的字节住在共享区**，所以回滚必须保存两半。
3. **`CustomizationAbsent` 必须在到达时【主动撤销】**，否则闩住会遮蔽后续三个状态。
4. **3981 行 / 110 秒 = 36 次/秒** —— "数量不是信息，阶段才是"。
5. **"外观缺失"可以升级为"整体失步"** —— 六步链条。
6. **只在 `model_resolution_unported_olfinal` + 无任何不可逆变更时才继续**。
7. **`priorIrreversibleMutation` 是批次级传染** —— 因为 DObj 池共享。
8. **回滚是"批次事务"**：任一失败则恢复全部 characterInfo（但 DObj 不回滚）。

## 十、未闭合点

- `EntityStateUpdate` 结构在本段未使用（属另一条路径）。
- `EngineBindings.cpp` 7104 行之后未读取。
