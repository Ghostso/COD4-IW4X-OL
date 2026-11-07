# 397 · **更正 §396 与 §367：`isAllowed` 的参数是【实体自己的名字列表】，不是允许列表** —— `setMapGameObjects({})` 确实是一个清空

## 一、更正的原因

在 §396 §4.3 里我写道：

> ⚠ 而 `setMapGameObjects({})` 的语义可疑：§367 的 `active = mapModeEligible && isAllowed(...)` 而 `isAllowed("")` 返回 **true** ⇒ **空输入会让所有 `eligible` 的实体【激活】**，与"清空"的意图**矛盾**。

**这个判断是错的。** 我读错了 lambda 的参数与捕获。

## 二、真实的代码

### 2.1 §367 的原始代码（18525–18551 行）

```cpp
bool SvServerWorld::setMapGameObjects(
    const std::span<const std::string_view> allowedGameObjectNames)
{
    const auto isAllowed = [allowedGameObjectNames](
                               const std::string_view gameObjectNames) {
        if (gameObjectNames.empty())
            return true;
        std::size_t offset{};
        while (offset < gameObjectNames.size())
        {
            offset = gameObjectNames.find_first_not_of(" \t\r\n", offset);
            if (offset == std::string_view::npos)
                break;
            const auto end = gameObjectNames.find_first_of(" \t\r\n", offset);
            const auto token = gameObjectNames.substr(
                offset,
                end == std::string_view::npos
                    ? gameObjectNames.size() - offset
                    : end - offset);
            if (std::ranges::find(allowedGameObjectNames, token) !=
                allowedGameObjectNames.end())
            {
                return true;
            }
            if (end == std::string_view::npos)
                break;
            offset = end;
        }
        return false;
    };
```

### 2.2 两个不同的东西

```text
allowedGameObjectNames  （捕获）  ⇒ **允许列表**（函数的参数）
gameObjectNames         （参数）  ⇒ **实体自己的 script_gameobjectname**
```

**⇒ 三层**：

```text
1. **`allowedGameObjectNames` 是【捕获】**
2. ⇒ **`gameObjectNames` 是【参数】**
3. ⇒ **两者名字相似而语义完全不同**
```

**⚠ 这正是我读错的地方** —— 我把它当成了"传入的名字"，而它是**实体自己的名字串**。

### 2.3 而判断的真实语义

```text
若【实体没有名字】⇒ 返回 true（**总是允许**）
若【实体有名字】⇒ 扫描它的 token，任一在允许列表里 ⇒ true
               ⇒ 否则 false
```

**⇒ 四层**：

```text
1. **无名实体 ⇒ 总是允许**
2. ⇒ **有名实体 ⇒ 需要一个 token 命中允许列表**
3. ⇒ **允许列表为空 ⇒ 任何有名实体都【失败】**
4. ⇒ **所以 `setMapGameObjects({})` 是一个【清空】**
```

**✅ 与 §396 的"空即全部"判断**完全相反**。**

## 三、`setMapGameObjects({})` 的精确效果

### 3.1 四条路径

```text
无名实体（`scriptGameObjectName` 空）
    ⇒ `isAllowed("")` = true
    ⇒ `active = mapModeEligible && true` = **`mapModeEligible`**
    ⇒ **保持原状**

有名实体（非空）
    ⇒ `isAllowed("<tokens>")` = false（因为允许列表空）
    ⇒ `active = false`
    ⇒ **被禁用**
```

**⇒ 四层**：

```text
1. **无名 → 保持**
2. ⇒ **有名 → 禁用**
3. ⇒ **所以是一个【按名门控】的启用集**
4. ⇒ **而空列表 = 只留无名实体**
```

### 3.2 而 §367 的两条分支

```text
非画笔（脚本模型）：
    `solid = 0`
    `brushModelIndex` 保留
画笔：
    `solid = active ? *solid : 0`
    `brushModelIndex = active ? clipHandle : 0`
```

**⇒ 三层**：

```text
1. **脚本模型 ⇒ 不管 `active` 都 `solid = 0`**
2. ⇒ **而 `collisionLinked = active`**
3. ⇒ **所以脚本模型被"禁用"的表现是【不再连碰撞】而不是 `solid`**
```

**✅ 与 §396 的判断**不同**（那里我说"全部激活"）。**

## 四、`loadGameplayScript` 的两次清空现在自洽了

### 4.1 那段

```php
if (!world_.setMapGameObjects({}))
    return false;
if (scriptRuntime_.reload(sourceName, source))
    return true;
static_cast<void>(world_.setMapGameObjects({}));
return false;
```

### 4.2 七层

```text
1. **`setMapGameObjects({})` ⇒ 禁用每一个【有名】实体**
2. ⇒ **所以起点是"只有无名实体激活"**
3. ⇒ **然后 `reload` 会通过脚本调用 `setMapGameObjects(<新列表>)` 重新启用**
4. ⇒ **成功 ⇒ 返回 true**（启用集由脚本决定）
5. ⇒ **失败 ⇒ 【再清一次】**（撤销脚本部分执行的启用）
6. ⇒ **所以两次清空都是【禁用有名实体】**
7. ⇒ **完全自洽**
```

**✅ ⭐ **"清-做-失败再清"** 的三段在语义上**完全正确**。**

**⚠ 而 §396 的"语义可疑"是我**读错 lambda 参数**导致的假问题。**

## 五、这个错误揭示的一件事

### 5.1 两个名字只差一个词

```text
allowedGameObjectNames   （捕获，允许列表）
gameObjectNames          （参数，实体名字）
```

**⇒ 三层**：

```text
1. **只差 `allowed` 一个词**
2. ⇒ **而类型完全相同**（`std::string_view`）
3. ⇒ **⇒ 编译器不会报错**
```

**✅ 与 §360 的"索引→偏移相同而编解码器不同"**同族（**第七次"名字/形状相同而语义不同"）。**

**⚠ 而这里**我**就是受害者。**

**✅ 一个**诚实的自我记录**。**

### 5.2 而"`isAllowed("")` 返回 true"在我的读法下是对的

```text
若 `gameObjectNames` 是【允许列表】，则 `isAllowed("")` 就是"允许列表空 ⇒ 全允许"
若 `gameObjectNames` 是【实体名字】，则 `isAllowed("")` 就是"无名实体 ⇒ 允许"
```

**⇒ 三层**：

```text
1. **两种读法下 `isAllowed("")` 都返回 true**
2. ⇒ **所以那个返回值【不能区分**两种读法**】
3. ⇒ **⇒ 而我用它做了判断**
```

**✅ 与 §372 的"一个返回空的扫描不是证据"**同族（**第三次"一个结果在两种假设下都成立 ⇒ 无信息"）。**

**⚠ 这个是**更精确的一类**：**

```text
一个观测在【两种互斥假设】下【都成立】
⇒ **⇒ 它对区分它们【零信息】**
```

**✅ ⭐ **一个可复用的证据学判据**。**

## 六、关键结论

1. **更正 §396 §4.3 与 §367 的相应段**：`isAllowed` 的参数是**实体自己的 `scriptGameObjectName`**，而**捕获才是允许列表**。
2. **真实语义**：**无名实体总是允许；有名实体需要一个 token 命中允许列表**。
3. **所以 `setMapGameObjects({})` 是一个【清空】**（禁用每一个有名实体），与 `loadGameplayScript` 的"两次清空"意图**完全自洽**。
4. **而 §396 的"语义可疑"是我读错 lambda 参数导致的假问题**。
5. **⭐ 两个名字只差 `allowed` 一个词而类型完全相同** ⇒ **编译器不会报错**（第七次"名字/形状相同而语义不同"）。
6. **⭐⭐ `isAllowed("")` 在两种读法下都返回 `true`** ⇒ **那个返回值对区分两种假设【零信息】** —— 一个可复用的证据学判据（第三次"一个结果在两种假设下都成立"）。

## 七、受影响的报告

```text
§367  18525–18551 行那段  ⇒ **需要按下文更正**（`isAllowed` 的语义）
§396  §4.3                ⇒ **整段作废**
§397  本报告               ⇒ 更正来源
```

## 八、未闭合点

- `setMapGameObjects` 的调用方（脚本 builtin 名）。
- `mapModeEligible` 与 `scriptGameObjectName` 的生产者。
- 是否有其它"只差一个词"的参数对。
- `sv_main_mp.cpp` 2760 行之后未读取。
