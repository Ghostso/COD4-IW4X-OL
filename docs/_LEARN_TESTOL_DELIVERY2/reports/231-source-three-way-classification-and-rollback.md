# 231 · 三路分类、回滚的四趟、`incrementalCollision` 的两种语义

## 一、范围

本报告学习 `EngineBindings.cpp` 7303–7502 行。

## 二、`createScriptModelDObj` 的转储格式

```cpp
static constexpr char Hex[] = "0123456789abcdef";
dump.reserve(DumpBytes * 2);          // 216 * 2 = 432 字符
for (index = 0; index < DumpBytes; ++index)
{
    const auto value = (uint8)bytes[index];
    dump += Hex[value >> 4];
    dump += Hex[value & 0xF];
}
```

**`216 × 2 = 432` 十六进制字符** —— 完整转储 `0xD8` 字节。

**日志行**：

```text
"script model dobj readback entity=N model=<名> dobj=<指针>
 wantModelPtr=<指针> wantScale=<浮点> header=<432 字符>"
```

**两个已知值都以**十进制**打印**（`std::to_string((uintptr_t)ptr)`）—— 而不是十六进制。

**而 `header` 是十六进制** —— **所以离线搜索时要先把十进制转成十六进制**。

**这是一处不便** —— 如果 `wantModelPtr` 也用十六进制，搜索会更直接。

## 三、`touched` 的三路分类

```cpp
for (const auto& [entityNum, mirror] : nativeServerEntityMirror_)
{
    const auto* target = findDesired(entityNum);
    if (incrementalCollision && !target) continue;      // ← 增量模式跳过"消失的"

    auto* slot = nativeSlot(entityNum);
    if (!writableBytes(slot, Size)) return failed("owned_slot_memory", entityNum);
    const auto actual = readSlot(entityNum);

    if (!target || target->source != mirror.source ||
        actual != mirror.linkedImage ||
        !scriptModelDObjMatches(mirror.source))
    {
        touched.push_back({ entityNum, actual, target, true });      // ── A. 需要重建
    }
    else if (target->projection != mirror.sourceProjection)
    {
        entityStateUpdates.push_back({ target, actual });            // ── B. 只需更新 entityState
    }
}
for (const auto& target : desired)
{
    if (nativeServerEntityMirror_.contains(target.source.entityNum)) continue;

    auto* slot = nativeSlot(target.source.entityNum);
    if (!writableBytes(slot, Size)) return failed("new_slot_memory", target.source.entityNum);
    const auto baseline = readSlot(target.source.entityNum);
    if (!SV_IsNativeServerEntityAvailableBaseline(baseline))
        return failed("baseline_owned", target.source.entityNum);
    touched.push_back({ target.source.entityNum, baseline, &target, false });   // ── C. 新占用
}
```

### 3.1 三条路径

```text
A. 已镜像 + （源变了 或 槽字节变了 或 DObj 不匹配）  ⇒ touched, previouslyOwned=true
B. 已镜像 + 只是 projection 变了（源与槽字节都没变）⇒ entityStateUpdates（轻量）
C. 未镜像（新实体）⇒ touched, previouslyOwned=false
```

### 3.2 三个"变了"的判据

```text
target->source != mirror.source              ← 源数据变了
actual != mirror.linkedImage                 ← 【槽字节被外人改了】
!scriptModelDObjMatches(mirror.source)       ← DObj 不在了或不对
```

**第二个尤其重要**：**引擎自己可能改了槽字节**（比如 `SV_LinkEntity` 重算 `absBox`）—— 所以每次都要比对。

### 3.3 `incrementalCollision` 跳过的含义

```cpp
// A native ClientThink links the one player whose command just
// moved; it does not reinterpret every other linked gentity as
// absent.  IncrementalCollision carries that same update-set
// meaning, while Collision and Presentation remain full desired
// images and therefore retain removal detection.
```

**"原生 `ClientThink` 链接那个刚移动的玩家；它不把其它每一个已链接的 gentity 重新解释为缺失。"**

**三种阶段的语义**：

```text
IncrementalCollision  → 【更新集】：只处理出现在 desired 里的
Collision/Presentation → 【完整镜像】：desired 里没有的 ⇒ 移除
```

**"因此保留移除检测"** —— 全量模式下才能发现"实体消失了"。

### 3.4 `baseline_owned` 的检查

```cpp
if (!SV_IsNativeServerEntityAvailableBaseline(baseline))
    return failed("baseline_owned", target.source.entityNum);
```

**新占用一个槽之前，必须确认该槽是"可用的基线"**（不是别人正在用的）。

**与 §218 里 `publishNativeServerEntityData` 的"已经有人占了这个槽就拒绝"同一纪律。**

### 3.5 `reserve` 的两种规模

```cpp
touched.reserve(incrementalCollision
    ? desired.size()                                        // 增量：最多 desired 大小
    : nativeServerEntityMirror_.size() + desired.size());   // 全量：两边之和
```

**增量模式下 `touched` 最多是 `desired.size()`**（因为跳过了不在 desired 里的）。

## 四、快速路径

```cpp
if (touched.empty() && entityStateUpdates.empty())
{
    if (phase == Presentation && !ensurePlayerDObjs())
        return playerDObjFailed();
    if (phase == Presentation)
        synchronizeActorHitPoses(entities, serverTime);
    return synchronized();
}
```

### 4.1 三件事

```text
1. Presentation 阶段仍要更新玩家 DObj
2. Presentation 阶段仍要同步演员姿势
3. 返回 synchronized()
```

**"没有要改的实体，但 Presentation 阶段的其他工作仍要做"** —— 这是一个容易漏掉的分支。

## 五、`entityStateUpdates` 的前置检查

```cpp
for (const auto& entry : entityStateUpdates)
{
    if (!entry.desired->entityState)
        return failed("entity_state_source", entry.desired->source.entityNum);
}
```

**只更新 entityState 的路径，必须真的有 entityState 源** —— 否则拒绝。

## 六、`rollback` 的四趟

### 6.1 第一趟：全部 unlink

```cpp
for (const auto& entry : touched)
{
    auto* slot = nativeSlot(entry.entityNum);
    const auto current = readSlot(entry.entityNum);
    if (SV_IsNativeServerEntityLinked(current) &&
        !invokeSVUnlinkEntity(svUnlinkEntity_, slot))
    {
        restored = false;
    }
}
```

**"先全部 unlink"** —— 因为**后面的两步都会替换 DObj 与字节**，而 CM 树里的链接必须先在干净状态。

**注释（在正向流程里）**：

```cpp
// CODREF(sv_unlink_entity): every owned touched slot must leave the CM
// tree before its gentity bytes or DObj ownership are replaced.
```

### 6.2 第二趟：释放 DObj

```cpp
for (const auto& entry : touched)
{
    const auto old = nativeServerEntityMirror_.find(entry.entityNum);
    if (entry.desired && entry.desired->source.shape == ScriptModelDObj)
        freeScriptModelDObj(entry.desired->source);       // 释放【新的】
    else if (old != end)
        freeScriptModelDObj(old->second.source);          // 释放【旧的】
}
```

**两个分支**：

```text
有 desired 且是 ScriptModelDObj  ⇒ 释放 desired 的（新创建的）
否则（没有 desired，或不是 ScriptModel）⇒ 释放旧的
```

**注意：如果 `desired` 存在但不是 ScriptModelDObj，走 `else if`** —— 释放旧的。

**而如果两者都不是 ScriptModelDObj，`freeScriptModelDObj` 内部还会判 shape 早退** —— 所以是安全的。

### 6.3 第三趟 + 第四趟：恢复字节与重链

```cpp
for (const auto& entry : touched)
{
    auto* slot = nativeSlot(entry.entityNum);
    auto backup = entry.backup;
    const auto relink = entry.previouslyOwned && SV_IsNativeServerEntityLinked(backup);
    if (relink)
        SV_ClearNativeServerEntityLinkedFlag(backup);      // 清掉链接位再写回
    std::memcpy(slot, backup.bytes.data(), Size);          // 写回字节

    const auto old = nativeServerEntityMirror_.find(entry.entityNum);
    if (old != end && !createScriptModelDObj(old->second.source))
        restored = false;                                  // 重建旧的 DObj

    if (relink)
    {
        const auto link = invokeNativeLink(slot);          // 重新链接
        if (!link.contextInstalled || !link.invoked || !link.contextRestored)
            restored = false;
    }
}
```

**一个循环里做了四件事**：

```text
1. 清链接位（如果要 relink）
2. 写回备份字节
3. 重建旧 DObj
4. 重新链接
```

### 6.4 为什么"先清链接位再写回"

```cpp
if (relink) SV_ClearNativeServerEntityLinkedFlag(backup);
std::memcpy(slot, backup.bytes.data(), Size);
```

**因为备份字节里 `isLinked` 是 1** —— 如果直接写回去，那一字节就是"已链接"，而实际上 CM 树里没有它。

**所以先清位、写回、再调 `SV_LinkEntity` 让它真正链接。**

**这是一个很精细的顺序** —— 而 `relink` 条件 `entry.previouslyOwned && SV_IsNativeServerEntityLinked(backup)` 保证"只有本来链接着的才重链"。

### 6.5 `restored` 的语义

**任何一步失败都 `restored = false`，但循环继续** —— 所以尽可能多地恢复。

**"尽力而为的回滚"** —— 而返回值让调用方知道是否完整。

## 七、正向流程的前两趟

```cpp
// 第一趟：全部 unlink
for (const auto& entry : touched)
{
    if (entry.previouslyOwned &&
        !invokeSVUnlinkEntity(svUnlinkEntity_, nativeSlot(entry.entityNum)))
    {
        if (!rollback()) return failed("rollback_after_unlink", entry.entityNum);
        return failed("native_unlink", entry.entityNum);
    }
}

// 第二趟：释放旧 DObj
for (const auto& entry : touched)
{
    const auto old = nativeServerEntityMirror_.find(entry.entityNum);
    if (old != end) freeScriptModelDObj(old->second.source);
}
```

### 7.1 与 rollback 的对称

```text
正向：unlink → free 旧 DObj → 写新字节 → create 新 DObj → link
回滚：unlink → free（新或旧）DObj → 写回备份 → create 旧 DObj → link
```

**两个方向的步骤数相同，但回滚的"释放"要判"释放哪个"。**

### 7.2 两重失败路径

```cpp
if (!rollback()) return failed("rollback_after_unlink", entityNum);
return failed("native_unlink", entityNum);
```

**两个阶段名**：

```text
"rollback_after_unlink"  ← unlink 失败【且】回滚也失败
"native_unlink"          ← 只有 unlink 失败（回滚成功）
```

**所以看日志能区分"只是 unlink 失败"与"unlink 失败且回滚也失败"** —— 后者严重得多。

## 八、那次"2.7 ms per command"的橡皮筋

```cpp
// Copying every retained native owner for each usercmd was the measured
// Factory rubber-band: ~2.7 ms per command, roughly 140 commands/s.
// An incremental command changes one player, so stage only that entry;
// full frame phases still stage the complete ownership map.
auto stagedMirror = incrementalCollision
    ? decltype(nativeServerEntityMirror_){}
    : nativeServerEntityMirror_;
if (incrementalCollision) stagedMirror.reserve(desired.size());
```

### 8.1 数字

```text
2.7 ms / 命令
140 命令 / 秒
⇒ 378 ms / 秒 = 38% 的 CPU 时间
```

**"Factory 橡皮筋"** —— 因为延迟导致的回拉。

### 8.2 优化

```text
增量：从空 map 开始，只 stage desired 的
全量：复制整个 mirror
```

## 九、关键结论

1. **三路分类**：需要重建 / 只需更新 entityState / 新占用。
2. **槽字节每次都要比对** —— 因为引擎自己会改（`absBox` 等）。
3. **`incrementalCollision` 是"更新集"，另两种是"完整镜像"** —— 只有后者能检测移除。
4. **新占用槽前必须确认是"可用基线"**，与 `publishNativeServerEntityData` 同一纪律。
5. **回滚四趟**：unlink → free → 写回字节 → 重建+重链。
6. **"先清链接位再写回字节"** —— 否则字节里的 `isLinked=1` 与 CM 树不一致。
7. **两个失败阶段名区分"回滚成功"与"回滚也失败"**。
8. **每命令 2.7 ms × 140/s = 38% CPU** —— 增量优化消除了它。

## 十、未闭合点

- `createScriptModelDObj` 的转储里两个已知值用十进制而 `header` 用十六进制，离线搜索需转换。
- `EngineBindings.cpp` 7502 行之后未读取。
