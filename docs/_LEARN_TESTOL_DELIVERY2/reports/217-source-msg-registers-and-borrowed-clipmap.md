# 217 · MSG 三函数的三个寄存器、campaign 借用 mp 地图的 clipmap

## 一、范围

本报告学习 `EngineBindings.cpp` 4510–4709 行。

## 二、三个 `MSG_*` 的寄存器对照

### 2.1 `MSG_Init`（§216 已读）

```asm
push esi
mov esi, messagePointer
push bufferLength
push bufferData
call function
add esp, 8
pop esi
```

```text
ESI = msg_t*
栈  = bufferData, bufferLength（两个）
```

### 2.2 `MSG_WriteBits`

```asm
push edi
mov edi, messagePointer
mov edx, bits
push value
call function
add esp, 4
pop edi
```

```text
EDI = msg_t*
EDX = bits
栈  = value（一个）
```

### 2.3 `MSG_WriteString`

```asm
push esi
mov esi, messagePointer
mov ecx, value
call function
pop esi
```

```text
ESI = msg_t*
ECX = value（字符串指针）
栈  = 无
```

### 2.4 三者的对照

| 函数 | msg_t* | 第二参数 | 第三参数 | 栈 |
|---|---|---|---|---|
| `MSG_Init` | ESI | 栈 bufferData | 栈 bufferLength | 2 |
| `MSG_WriteBits` | **EDI** | **EDX = bits** | 栈 value | 1 |
| `MSG_WriteString` | **ESI** | **ECX = value** | — | 0 |

**三个函数用三个不同的寄存器装 `msg_t*`**：

```text
MSG_Init        ESI
MSG_WriteBits   EDI
MSG_WriteString ESI
```

**而 `MSG_WriteBits` 还把 `bits` 放 EDX、`value` 放栈** —— **参数顺序与声明顺序相反**（声明是 `(message, value, bits)`）。

**这是三个函数来自同一族的证据**（都是 MSG 写操作），但**寄存器分配各不相同** —— 所以必须逐个反汇编。

**注意 `MSG_WriteString` 没有 `add esp`** —— 因为没有栈参数 ✓

## 三、`CCS_Initialized()`：两个全局

```cpp
if (!module_ ||
    *(const uint32*)(module_ + ConstantConfigStringsInitializedRva) == 0)
{
    checksum_.store(0);
    return false;
}
const auto checksum = *(const uint32*)(module_ + ConstantConfigStringChecksumRva);
if (!checksum) { checksum_.store(0); return false; }
checksum_.store(checksum);
return true;
```

### 3.1 三级

```text
1. 未初始化标志 == 0       ⇒ false, checksum = 0
2. 校验和 == 0             ⇒ false, checksum = 0
3. 都非零                  ⇒ true, 缓存校验和
```

**校验和为零也当作"未初始化"** —— 因为零不是一个有效的校验和值。

### 3.2 三个地址

```text
ConstantConfigStringsInitializedRva = 0x73DB42C    （§186 里记过）
ConstantConfigStringChecksumRva     = 0x73D8240
ConfigStringTypesRva                = 0x73D8250    （在两者之间）
```

**注意 `0x73D8240`（校验和）与 `0x73D8250`（类型表）相差 0x10 = 16**，而**初始化标志在 `0x73DB42C`**（相隔 0x31EC）。

**这不是一组连续的全局** —— 所以不能靠相邻关系推断。

## 四、`beginLevelZoneLoad` vs `initializeLevelWorld`：两种校验

### 4.1 `beginLevelZoneLoad`

```cpp
if (!levelZoneLoad_ || mapName.empty() || gameType.empty() ||
    mapName.find('\0') != npos || gameType.find('\0') != npos ||
    gameThreadId_ != GetCurrentThreadId())
    return false;
```

**五项**：指针、两个非空、两个无 NUL、线程。

### 4.2 `initializeLevelWorld`

```cpp
if (!collisionMapLoad_ || !collisionWorldLink_ || !dbFindXAssetHeader_ ||
    !validBookingName(mapName) || !validBookingName(gameType) ||
    gameThreadId_ != GetCurrentThreadId())
    return false;
```

**五项**：三个指针、两个 `validBookingName`、线程。

### 4.3 两种名字校验的差别

```text
beginLevelZoneLoad:    非空 + 无 NUL          （宽松）
initializeLevelWorld:  validBookingName       （白名单 [A-Za-z0-9_-]{1,64}）
```

**后者更严** —— 因为它要把名字拼进路径（`"maps/mp/" + map + ".d3dbsp"`）。

**而 `beginLevelZoneLoad` 只是传给引擎当 zone 名**，所以宽松。

**这是"按用途分级校验"的正确做法**。

## 五、`zoneLoaded`：最简单的那个

```cpp
if (!zoneLoaded_ || name.empty() || name.find('\0') != npos)
    return false;
const std::string terminated(name);   // 确保 NUL 结尾
return zoneLoaded_(terminated.c_str());
```

**`std::string terminated(name)`** —— 因为 `string_view` 不保证 NUL 结尾，而原生函数要 C 串。

**同样的模式在 `beginLevelZoneLoad` 与 `initializeLevelWorld` 里也出现**：

```cpp
const std::string map(mapName);
const std::string game(gameType);
```

**这是 `string_view` → `const char*` 的标准桥接**。

## 六、campaign 借用 mp 地图的 clipmap（本组最重要的一段）

### 6.1 症状

```text
This built exactly one candidate -- ClipMapMp at "maps/mp/<map>.d3dbsp" --
and returned false when it missed, which is what
`world initialization failed map=coop_training_mp_cargoship` was:
the ZONE loaded fine (zoneLoaded passed, `map asset load requested` logged),
only the clipmap lookup missed.
```

**"zone 加载正常，只有 clipmap 查找没中"** —— 失败点极其具体。

### 6.2 为什么不能替换成 `mp_cargoship`

```text
Serving the multiplayer `mp_cargoship` instead is NOT a substitute:
the client loads `coop_training_mp_cargoship` (its own gamestate says so,
and so does the retail coop capture), so the two sides hold different
levels and the level checksum rejects the join.
```

**"两侧持有不同的关卡，而关卡校验和会拒绝加入"**

**这是"用近似替代"被校验和挡住的具体例子。**

### 6.3 解密 fastfile 得到的实测

```text
mp_nuked 的 zone 携带 `maps/mp/mp_nuked.d3dbsp`
而 coop_training_mp_cargoship 的【三个】fastfile（.ff / _const / _load）
与其 235 文件的 lf_ 归档【一个 .d3dbsp 都没有】。
```

**"三个 fastfile + 235 文件归档里一个 .d3dbsp 都没有"** —— 这是"它根本不带 clipmap"的直接证据。

### 6.4 推导

```text
campaign 关卡建在 mp_cargoship 上 —— 它自己的名字就这么说 ——
所以最后一个 `mp_` 前缀的分量是它复用的 clipmap 所属的地图。
```

### 6.5 那段借用名的代码

```cpp
std::string borrowed;
if (const auto at = map.rfind("mp_"); at != std::string::npos && at != 0)
    borrowed = map.substr(at);
```

**`rfind("mp_")`** —— 找**最后**一个 `mp_`。

**`at != 0` 的检查** —— 如果 `mp_` 在开头（即 `mp_cargoship` 本身），**不借用**（那是它自己）。

**所以**：

```text
"coop_training_mp_cargoship"  → rfind = 14  → borrowed = "mp_cargoship"  ✓
"mp_cargoship"                → rfind = 0   → borrowed = ""              ✓
"coop_training"               → npos        → borrowed = ""              ✓
```

**这个逻辑很干净**。

## 七、六个候选的完整表

```cpp
{ ClipMapMp, "maps/mp/" + map + ".d3dbsp" }
{ ClipMapSp, "maps/mp/" + map + ".d3dbsp" }
{ ClipMapMp, "maps/" + map + ".d3dbsp" }
{ ClipMapSp, "maps/" + map + ".d3dbsp" }
// 若有 borrowed：
{ ClipMapMp, "maps/mp/" + borrowed + ".d3dbsp" }
{ ClipMapSp, "maps/mp/" + borrowed + ".d3dbsp" }
```

### 7.1 两个维度

```text
资产类型：ClipMapMp(15) / ClipMapSp(14)
路径前缀：maps/mp/ / maps/
```

**四种组合 + 两种借用 = 最多六个**。

### 7.2 注释里的两个事实

```text
14 是库存 SP ClipMap，紧邻 ClipMapMp 的 15；
campaign 路径约定【去掉】"mp/"。
```

**"campaign 路径约定去掉 mp/"** —— 所以 `maps/<map>.d3dbsp` 是 campaign 形式。

### 7.3 失败时**列出全部尝试**

```cpp
std::string tried;
for (const auto &candidate : candidates)
    tried += (tried.empty() ? "" : ", ") +
        std::to_string(candidate.assetType) + ":" + candidate.name;
log("no clipmap for " + map + " -- tried " + tried);
```

**"一个未命中应当自己点名，而不是塌缩成 'failed'"**

**这是本项目反复出现的原则的又一次应用**。

### 7.4 成功时也记录

```cpp
log("clipmap resolved type=" + std::to_string(chosen->assetType) +
    " name=" + chosen->name);
```

**成功也记** —— 因为"哪一个候选中了"是有价值的信息（能说明地图的真实布局）。

## 八、世界初始化的三连调用

```cpp
if (!invokeCollisionMapLoad(collisionMapLoad_, bspName.c_str(), game.c_str(), map.c_str()) ||
    !invokeNoArgument(collisionWorldLink_) ||
    !resetNativeServerEntityMirrorAfterWorldInitialization())
{
    return false;
}

return findXAsset(AssetTypeComWorld, bspName.c_str(), true).data != nullptr;
```

### 8.1 顺序

```text
1. collisionMapLoad(bsp, gameType, mapName)   ← ECX=mapName, 栈=bsp, gameType
2. collisionWorldLink()                        ← 无参数
3. resetNativeServerEntityMirrorAfterWorldInitialization()
4. findXAsset(ComWorld, bsp, allowDefault=true)
```

**`invokeCollisionMapLoad` 的参数顺序**（§202）：

```text
ECX = mapName（第三个参数）
栈  = bspName, gameType
```

**注意 bspName 与 mapName 不同** —— 如果用了 borrowed，`bspName` 是 `maps/mp/mp_cargoship.d3dbsp` 而 `mapName` 是 `coop_training_mp_cargoship`。

### 8.2 最后一步用 `allowDefault = true`

```cpp
findXAsset(AssetTypeComWorld, bspName.c_str(), true)
```

**`true`** —— 与前面查找 clipmap 时的 `false` 相反。

**因为这里只是"确认 ComWorld 存在"**，宽松即可。

## 九、`resetNativeServerEntityMirrorAfterWorldInitialization`

```cpp
releaseActorHitPoses();
actorHitPosesEnabled_ = false;

for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
{
    auto* slot = (std::byte*)gEntities_ + entityNum * SvNativeServerEntity::Size;
    if (!writableBytes(slot, SvNativeServerEntity::Size))
        return false;
    static_cast<void>(mirror);      // 【只是校验，不用值】
}

for (entityNum = 0; entityNum < nativeServerCharacterInfo_.size(); ++entityNum)
    serverDObjFreeAdapter((int32)entityNum, 0);

nativeServerCharacterInfo_ = {};

for (entityNum = 0; entityNum < ServerCharacterInfoSlotCount; ++entityNum)
    std::ranges::fill(serverCharacterInfo(entityNum), std::byte{});

nativeServerPlayerDObjPoisoned_ = false;
```

### 9.1 三步清理

```text
1. 释放演员击打姿势
2. 逐实体检查 gEntities_ 槽可写（并释放对应的 DObj）
3. 清 characterInfo 数组（两份：ol-mod 的与原生块里的）
```

**第 2 步的 `static_cast<void>(mirror)`** —— 结构化绑定里 `mirror` 没用，显式忽略。

**但那整个循环只做"可写性检查"** —— 如果某个槽不可写就返回 false。

**这是一个"只校验不修改"的循环**，而 `mirror` 的值完全没用 —— **这是一个可以指出的小冗余**（可以用 `for (const auto& entry : map)` 只取键）。

### 9.2 那段注释

```cpp
// OLMOD(native-player-dobj-lifetime): level world initialization is
// the only proven recovery boundary after a caught native DObj or
// animation exception. COD's original void APIs do not expose a
// recoverable failure protocol for partially mutated DObj/XAnim state.
```

**"COD 原来的 void API 不为部分变异的 DObj/XAnim 状态暴露可恢复的失败协议"**

**所以"关卡世界初始化"是唯一被证实的恢复边界** —— 因为那是引擎自己会重建这些状态的地方。

## 十、关键结论

1. **三个 MSG 函数用三个不同的寄存器装 `msg_t*`**（ESI/EDI/ESI），且 `MSG_WriteBits` 的参数顺序与声明相反。
2. **`CCS_Initialized` 把零校验和也当未初始化**。
3. **两种名字校验按用途分级**：宽松（zone 名）vs 白名单（拼路径）。
4. **campaign 关卡的三个 fastfile + 235 文件归档里一个 `.d3dbsp` 都没有** —— 所以必须借用 mp 地图的 clipmap。
5. **`rfind("mp_")` + `at != 0`** 精确区分了"借用"与"自己"。
6. **六个候选、失败时列出全部尝试、成功时也记录**。
7. **`string_view` → `std::string` → `c_str()`** 是标准桥接（保证 NUL 结尾）。

## 十一、未闭合点

- `releaseActorHitPoses` 与 `serverDObjFreeAdapter` 的完整实现在本组之外。
- `EngineBindings.cpp` 4709 行之后未读取。
