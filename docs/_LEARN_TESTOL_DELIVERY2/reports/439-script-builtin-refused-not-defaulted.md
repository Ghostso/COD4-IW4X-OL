# 439 · **"被拒绝，不是被默认"** —— `precachemodel` 的"沉默成功会隐藏它"、`spawnmodel` 的"名字从不编号"、以及两条分离的 spawn 路径

## 一、范围

本报告学习 `sv_script_builtin_mp.cpp` 360–700 行（`zmSetRound`、`readZmSpawnPoint`、`precacheModel`、`zmSpawnActor`、`zmSpawnActorAt`、`zmZoneAt` 的开头）。

## 二、**"被拒绝，不是被默认"**（本组最重要的一段）

### 2.1 那段（`zmSpawnActor` 的模型）

```php
const auto modelIndex = modelResolver(*modelName);
if (!modelIndex)
{
    // REFUSED, NOT DEFAULTED. Spawning with model index 0 puts a zombie
    // shaped like nothing at all into the world and hides the real fault,
    // which is that the map did not precache this model.
    return failure(
        SvScriptBuiltinErrorCode::InvalidArgumentValue,
        call.id.name + " could not resolve model " + *modelName);
}
```

### 2.2 二十层

```text
1. **`modelResolver(*modelName)` 返回 `nullopt`**
2. ⇒ **⇒ 【拒绝，不是默认**】**
3. ⇒ **用一个【模型索引 `0`**】出生【把一个形状【什么都不像**】的僵尸放进世界**】
4. ⇒ **而【隐藏了【真正的故障**】】**
5. ⇒ **⇒ 那个故障是【地图【没有 precache**】这个模型**
```

### 2.3 ⭐⭐⭐ **"用模型索引 `0` 出生把一个形状什么都不像的僵尸放进世界，而隐藏了真正的故障"**

**✅ 这是本报告里**最重要的一条"默认值的代价**。**

**✅ 与 §417 的"`field00E4 = 0` 是索引 0"**完全同族（**第五次"零是一个有效选择**）。

**⇒ 三次闭合**：
```text
§417  **`0` 是索引 0**
§435  **`viewmodelIndex = 0` ⇒ AV**
§439  **`modelIndex = 0` ⇒ 一个"形状什么都不像"的僵尸**
⇒ **⇒ 三次"零的后果**】
```

**✅ ⭐⭐⭐ **一个"零的后果"的三例表**。

**⚠ 而"隐藏了真正的故障"⇒ **一个可诊断性论证**。**

**✅ 与 §410 的"一个交付不了任何东西的特性对一场活的比赛没有主张"**不同（这是**一个"沉默的成功"**）。

**⇒ 三层**：
```text
默认 ⇒ **一个可见的错误实体** + **一个被隐藏的根因**
拒绝 ⇒ **一个明确的错误消息**
⇒ **⇒ 所以【后者【更快**】定位**】
```

**✅ ⭐⭐ **"拒绝更快"**。

### 2.4 而**`precacheModel` 的"沉默的成功会隐藏它直到僵尸没能画出"**

```php
if (!modelPrecacher(*modelName))
{
    // REFUSED, NOT IGNORED. A model the dedicated cannot resolve is one
    // zmspawnactor will refuse later anyway, and a silent success here
    // would hide it until the zombie failed to draw.
    return failure(
        SvScriptBuiltinErrorCode::InvalidArgumentValue,
        call.id.name + " could not precache model " + *modelName);
}
```

**⇒ 十层**：
```text
1. **拒绝，不是忽略**
2. ⇒ **一个专用服解不出的模型【正是 `zmspawnactor` 【稍后会拒绝**】的那个**
3. ⇒ **⇒ 所以【它【无论如何会被拒**】】**
4. ⇒ **而【一个沉默的成功【会隐藏它【直到僵尸【没能画出**】】】**
5. ⇒ **⇒ 所以【在【最早的**点拒绝**】
```

### 2.5 ⭐⭐⭐ **"一个沉默的成功会隐藏它直到僵尸没能画出"**

**✅ 与 §439 二.3 的"隐藏了真正的故障"**——**同一原则的两次**。

**⇒ 三层**：
```text
`precacheModel` 静默成功 ⇒ **错误延迟到【绘制时**】
而拒绝 ⇒ **错误在【脚本初始化时**】
⇒ **⇒ 所以【越早越好**】
```

**✅ ⭐⭐⭐ **"越早越好"** —— 与 §411 的"有一个阳性对照"**不同（那是**一个观测设计**，这是**一个错误时机**）。

**⇒ 三层**：
```text
§403  **错位取证**（位置决定结论）
§439  **错误时机**（越早越好）
⇒ **⇒ 两个相反的方向**
```

**✅ ⭐⭐ **"一个测量的位置 vs 一个错误的位置"**。

### 2.6 而**"名字，从不编号"**

```php
// The model is named, never numbered. The client rebuilds its own model
// configstring band at map load, so an index that is right in one session is
// wrong in the next
```

**⇒ 六层**：
```text
1. **模型【被命名，从不被编号**】**
2. ⇒ **客户端【在地图加载时重建它自己的模型 configstring 带**】**
3. ⇒ **⇒ 所以【一个在【一个会话里正确**】的索引【在【下一个里是错的**】】**
```

**✅ 与 §417 的"从不 demo 的字面 `287`"**、§414 的"按名字从不按零售的数字"**完全同族（**第六次"按名字不用数字"）。

**⇒ 三层**：
```text
§407  **`\ent\<n>` 用实体索引**（**不猜**）
§414  **`_tp` 按 `<map>_tp` 名字**
§417  **从不 demo 的字面 `287`**
§418  **`tag_origin` 按名字解索引**
§439  **模型被命名从不编号**
⇒ **⇒ 五次"按名字**】
```

**✅ ⭐⭐⭐ **一个"按名字"的五例表**。

## 三、**`precacheModel` 的"在脚本初始化时调用"**（本组第二重要）

### 3.1 那段

```php
// PUT A MODEL IN THE CLIENT'S BAND BEFORE ANYTHING SPAWNS.
// precachemodel(modelName) -> the band index the clients will resolve.
//
// zmspawnactor sends a model INDEX in the agent element, and the client
// resolves it against ITS OWN band -- which holds only what this server has
// transmitted. Until this ran, index 308 was empty on the client, the record's
// model name stayed "" and sub_52FBE0 built no DObj: zombies were on the wire,
// validated, and invisible. 12.21.
//
// CALL IT AT SCRIPT INIT. It publishes into the gamestate, so it has to happen
// before a client is served one; doing it at spawn time is a LIVE configstring
// change and the client could not enter the session at all (12.21).
```

### 3.2 二十四层

```text
1. **在任何东西出生之前【把一个模型放进客户端的带**】**
2. ⇒ **`precachemodel(modelName)` ⇒ 返回【客户端将解析的那个带索引**】**
3. ⇒ **`zmspawnactor` 在 agent 元素里发【一个模型索引**】**
4. ⇒ **而客户端【对它自己的带**】解析它**
5. ⇒ **⇒ 而那个带【只持有【这个服务器发送过的东西**】】**
6. ⇒ **⚠ 在它运行之前**：
      · **索引 `308` 在客户端上是空的**
      · **记录的模型名【停在 `""`**】
      · **而 `sub_52FBE0` 【没有构建 DObj**】
7. ⇒ **⇒ 所以僵尸【在线上、被验证、而【不可见**】】**
8. ⇒ **⇒ 【在脚本初始化时调用它**】**
9. ⇒ **它【发布进 gamestate**】**
10. ⇒ **⇒ 所以【它必须在【一个客户端被服务一份之前**】发生**
11. ⇒ **⇒ 而在出生时做是【一个实时的 configstring 变更**】**
12. ⇒ **⇒ 而【客户端【根本无法进入会话**】（`12.21`）**
```

### 3.3 ⭐⭐⭐ **"在出生时做是一个实时的 configstring 变更，而客户端根本无法进入会话"**

**✅ 与 §430 的"`d` 必须在 gamestate 之后，因为 gamestate 已经含它"**——**完全同源** ✓

**⇒ 三层**：
```text
§430  **`d` 在 gamestate 之前发 ⇒ 描述一个客户端没有表的 configstring**
§439  **precache 在出生时 ⇒ 一个实时 configstring 变更 ⇒ 客户端无法进入**
⇒ **⇒ 两次"configstring 的时机**】
```

**✅ ⭐⭐⭐ **一个"configstring 时机"的两例表**。

**⚠ 而"`308` 是空的"⇒ **一个具体的索引**。**

**⇒ 三层**：
```text
`308` ⇒ **一个模型带索引**
而【客户端上它是空的**】 ⇒ **因为服务器【从未发送过**】
⇒ **⇒ 所以【索引 308 是【服务器侧**的一个号**】
```

**✅ 与 §417 的"从名字解析成【这个服务器的带索引**】"**完全闭合 ✓

**⇒ 三层**：
```text
§417  **`actorField009C` 是【这个服务器的带索引**】
§439  **`precachemodel` 返回【客户端将解析的那个带索引**】
⇒ **⇒ 所以【两者【必须一致**】】
```

**✅ ⭐⭐ **一个"两个带索引必须一致"的实例**。

## 四、**两条分离的 spawn 路径**（本组第三重要）

### 4.1 那段

```php
// SPAWN ONE ZOMBIE AT AN EXPLICIT POSITION.
// zmspawnactorat(position, yaw, modelName) -> entity number.
//
// SEPARATE FROM zmspawnactor ON PURPOSE. That one spawns at a map spawner,
// and every zm spawner sits in a closet behind the barriers -- by design,
// that is where zombies come from. So it answers "are the spawners where I
// think they are" and CANNOT answer "does an ET_ACTOR draw", because nothing
// is ever in a position to see one. This takes a position so the second
// question can be asked on its own.
```

### 4.2 二十层

```text
1. **在一个显式位置出生一个僵尸**
2. ⇒ **与 `zmspawnactor` 【故意分离**】**
3. ⇒ **那一个【在一个地图出生点**】出生**
4. ⇒ **而【每一个 zm 出生点【坐在屏障后面的一个壁橱里**】】**
5. ⇒ **⇒ 按设计，那就是僵尸【来的地方**】**
6. ⇒ **⇒ 所以它回答"出生点【在我以为的地方**吗"**
7. ⇒ **⇒ 而【它【不能**回答"一个 `ET_ACTOR`【会画**吗"**
8. ⇒ **因为【没有任何东西【处在一个能看见它**】的位置**】
9. ⇒ **⇒ 这个接受一个位置**】
10. ⇒ **⇒ 所以【第二个问题【可以单独**被问**】
```

### 4.3 ⭐⭐⭐ **"它回答『出生点在我以为的地方吗』，而它不能回答『一个 ET_ACTOR 会画吗』，因为没有任何东西处在一个能看见它的位置"**

**✅ 与 §370 的"去问键盘不要问镜像"**——**完全同族**（**第十一次"用什么测决定能测出什么"）。

**⇒ 三层**：
```text
`zmspawnactor` ⇒ **测"出生点位置对否"**
`zmspawnactorat` ⇒ **测"ET_ACTOR 会画否"**
⇒ **⇒ 两个不同的问题【需要两个不同的入口**】
```

**✅ ⭐⭐⭐ **"一个入口回答一个问题"** —— 与 §420 的"`zmGoalRoutable` 是一个可达性测试，不是一个回退"**同族（**第三次"一个函数一件事"）。

**⇒ 三层**：
```text
§412  **"去问键盘不要问镜像"**
§420  **"一个可达性测试不是回退"**
§439  **"两条分离的 spawn 路径答两个问题"**
⇒ **⇒ 三次"工具对准问题**】
```

**✅ ⭐⭐ **一个"工具对准问题"的三例表**。

**⚠ 而"每一个 zm 出生点【按设计】坐在屏障后面的壁橱里"⇒ **一个地图设计的确认**。**

**✅ 与 §420 的"factory 的 `30` 个 spawner 里只有 `5` 个跨屏障"**配合。

### 4.4 而**"四个参数现在是可选的头部模型"**

```php
// FOUR ARGS NOW, the fourth an OPTIONAL head model -- the same shape
// zmspawnactor already takes. Without it this builtin could put a
// zombie in view but never a zombie with a HEAD, which is exactly
// the thing 12.48 needs looking at.
```

**⇒ 六层**：
```text
1. **四个参数，第四个是一个【可选的头部模型**】**
2. ⇒ **与 `zmspawnactor` 【已经接受的形状相同**】**
3. ⇒ **⚠ 没有它，这个内建【可以【把一个僵尸放进视野**】**
4. ⇒ **而【永远不是一个【有头部**的僵尸**】**
5. ⇒ **⇒ 而那正是【`12.48` 需要看的东西**】**
```

**✅ ⭐⭐ **"可以放一个僵尸进视野，而永远不是一个有头部的僵尸"** —— 一个**精确的能力边界**。

**✅ 与 §418 的"僵尸的头"**（`actorAttachModelIndex0` 与 `c_zom_ger_head`/`c_zom_ger_body_blue`）**完全闭合 ✓

**⇒ 三层**：
```text
§417  **`actorAttachModelIndex0` 是"这个 actor 的头"**
§439  **`zmspawnactorat` 现在可接受一个可选的头部模型**
⇒ **⇒ 所以【`12.48` 的问题需要这个参数**】
```

**✅ ⭐⭐ **一个"一个字段与一个参数"的闭合**。

## 五、**`zmZoneAt` 的"一个空名字是一个真实的答案，不是一个错误"**

```php
const auto *zone = SV_ZmZoneAt(zones, *position);
// AN EMPTY NAME IS A REAL ANSWER, NOT AN ERROR. Standing outside every
```

**⇒ 八层**：
```text
1. **一个空名字【是一个真实的答案，不是一个错误**】**
2. ⇒ **站在【每一个区域之外**】是一个【合法状态**】
3. ⇒ **⇒ 所以【返回 `""` 而不是 `failure(...)`**】
```

**✅ 与 §438 的"一个没有目标的点没有路由可测 ⇒ 那是『否』，不是『一个错误』"**完全同族（**第十次"缺失的输入不是错误"）。

**⇒ 三次闭合**：
```text
§420  **不可路由的目标 ⇒ 永远得不到一个 actor**
§438  **没有目标的 spawn 点 ⇒ 返回 0**
§439  **在每一个区域之外 ⇒ 返回 `""`**
⇒ **⇒ 三次"一个合法的空**】
```

**✅ ⭐⭐⭐ **一个"合法的空"的三例表**。

## 六、**`zmSpawnActorAt` 的 `isfinite` 检查**

```php
bool finitePosition = std::isfinite(yaw);
for (const auto value : *position) {
    if (!std::isfinite(value)) finitePosition = false;
}
if (!finitePosition) return failure(..., " expects a finite position and yaw");
```

**⇒ 八层**：
```text
1. **`yaw` 必须有限**
2. ⇒ **而【三个位置分量**都有限**】
3. ⇒ **`NaN` 与 `Inf` ⇒ 拒绝**
4. ⇒ **⇒ 所以【一个 `NaN` 位置【不会进入世界**】**
```

### 6.1 ⭐⭐⭐ **"一个 NaN 位置不会进入世界"**

**✅ 与 §412 的"`!std::isfinite(combatYaw) ⇒ 回落到精确对准"**同族（**第三次"`NaN` 的防护"）。

**⇒ 三层**：
```text
§412  **bot 瞄准的 `NaN` ⇒ 回落**
§417  **`zmSpawnActorAt` 的 `isfinite`**
§439  **脚本传入的 `NaN` ⇒ 拒绝**
⇒ **⇒ 三次"`NaN` 防护**】
```

**✅ ⭐⭐ **一个"`NaN` 防护"的三例表**。

**⚠ 而"脚本【可以**传一个 `NaN`"⇒ **一个信任边界**。**

**⇒ 三层**：
```text
脚本 ⇒ **一个【外部输入**】
⇒ **⇒ 所以【必须检查**】
```

**✅ 与 §417 的"`parseUserInfo` 的大小上限 `1024`"**同族（**第六次"边界检查"）。

**⇒ 三层**：
```text
§425  **`parseUserInfo` 的上限**
§438  **`readZmIndex` 的两端检查**
§439  **`isfinite` 检查**
⇒ **⇒ 三次"边界检查**】
```

**✅ ⭐ **一个"边界检查"的三例表**。

## 七、**`zmSetRound` 的 `1..255` / `0..255`**

```php
if (*round < 1 || *round > 255 || *goal < 0 || *goal > 255)
    return failure(..., " round must be 1..255 and goal 0..255");
SV_SetZmRound(static_cast<std::uint32_t>(*round), static_cast<std::uint32_t>(*goal));
world.setZmPresentationRound(static_cast<std::uint32_t>(*round));
```

**⇒ 十层**：
```text
1. **`round` 是 `1..255`**（**不从 `0` 开始**）
2. ⇒ **`goal` 是 `0..255`**（**可以从 `0` 开始**）
3. ⇒ **⇒ 所以【两个不同的下界**】
4. ⇒ **而 `SV_SetZmRound` 【也做 `round ? round : 1`**】（§432）
5. ⇒ **⇒ 所以【两层防护**】】
6. ⇒ **而 `setZmPresentationRound` 【也只接受 `1..255`**】（§420 的 `if (round >= 1 && round <= 255)`）**
7. ⇒ **⇒ 所以【三层防护**】
```

**✅ ⭐⭐ **"三层防护同一个区间"** —— 与 §432 的"`gZmRound.store(round ? round : 1u)`"**完全闭合**。

**⇒ 三层**：
```text
`zmSetRound` ⇒ **拒绝 `< 1` 或 `> 255`**
`SV_SetZmRound` ⇒ **`round ? round : 1`**
`setZmPresentationRound` ⇒ **`if (round >= 1 && round <= 255)`**
⇒ **⇒ 所以【三层，同一区间**】
```

**✅ ⭐⭐⭐ **"同一个区间在三层被防护"** —— 一个**纵深防御**的实例。

**⚠ 而"`goal` 可以是 `0`"⇒ **一个不同的语义**。**

**⇒ 三层**：
```text
`round = 0` ⇒ **无意义** ⇒ 拒绝
`goal = 0` ⇒ **可能意味着"无目标/无限"** ⇒ 接受
⇒ **⇒ 所以【两个下界不同是因为语义不同**】
```

**✅ ⭐ **一个"下界由语义决定"的实例**。

## 八、关键结论

1. **⭐⭐⭐ "用模型索引 `0` 出生把一个【形状什么都不像】的僵尸放进世界，而【隐藏了真正的故障】—— 那个故障是地图没有 precache 这个模型"`** —— 第五次"零是一个有效选择"（与 §417、§435 同族）。
2. **⭐⭐⭐ "`precacheModel` 拒绝，不是忽略：一个专用服解不出的模型正是 `zmspawnactor` 稍后会拒绝的那个，而【一个沉默的成功会隐藏它直到僵尸没能画出】"`** ⇒ **"越早越好"**。
3. **⭐⭐ "模型被命名，从不被编号：客户端在地图加载时重建它自己的模型 configstring 带，所以一个在一个会话里正确的索引在下一个里是错的"`** —— 第六次"按名字不用数字"（与 §407/§414/§417/§418 同族）。
4. **⭐⭐⭐ `precacheModel` 的病历**：**在它运行之前索引 `308` 在客户端上是空的、记录的模型名停在 `""`、`sub_52FBE0` 没有构建 DObj ⇒ 僵尸在线上、被验证、而不可见**（`12.21`）。
5. **⭐⭐⭐ "在脚本初始化时调用它：它发布进 gamestate，所以它必须在一个客户端被服务一份之前发生；而在出生时做是一个【实时的 configstring 变更】而客户端【根本无法进入会话】"`** —— 第二次"configstring 时机"（与 §430 的 `d` 必须在 gamestate 之后同族）。
6. **⭐⭐ "`precachemodel` 返回客户端将解析的那个带索引"`** 与 **§417 的 `actorField009C` 是"这个服务器的带索引"** 闭合 ⇒ **两者必须一致**。
7. **⭐⭐⭐ "两条分离的 spawn 路径：`zmspawnactor` 在一个地图出生点出生，而每一个 zm 出生点按设计坐在屏障后面的一个壁橱里 ⇒ 它回答『出生点在我以为的地方吗』而【不能回答『一个 ET_ACTOR 会画吗』，因为没有任何东西处在一个能看见它的位置】；`zmspawnactorat` 接受一个位置，所以第二个问题可以单独被问"`** —— 第十一次"用什么测决定能测出什么"（与 §370 的"去问键盘不要问镜像"同族）。
8. **⭐ "四个参数现在是可选的头部模型：没有它，这个内建可以放一个僵尸进视野，而永远不是一个有头部的僵尸，而那正是 `12.48` 需要看的东西"`** —— 与 §417 的 `actorAttachModelIndex0`（`c_zom_ger_head`）闭合。
9. **⭐⭐⭐ `zmZoneAt` 的"一个空名字是一个真实的答案，不是一个错误：站在每一个区域之外"`** —— 第三次"合法的空"（与 §420、§438 同族）。
10. **⭐⭐ "一个 `NaN` 位置不会进入世界"**（`isfinite` 检查 `yaw` 与三个位置分量）—— 第三次"`NaN` 防护"（与 §412、§417 同族），也是第六次"边界检查"（**脚本是一个外部输入**）。
11. **⭐⭐ `zmSetRound` 的 `round 1..255` 而 `goal 0..255`** ⇒ **同一个区间在【三层】被防护**（`zmSetRound` 的检查、`SV_SetZmRound` 的 `round ? round : 1`、`setZmPresentationRound` 的 `if` 区间）—— 一个**纵深防御**的实例；而 **两个下界不同【因为语义不同】**（`round = 0` 无意义而 `goal = 0` 可能意味着"无目标"）。

## 九、未闭合点

- `12.21` 的完整记录。
- `12.48` 的"头部"问题。
- `sub_52FBE0` 的 DObj 构建。
- `SvZmSpawnPoint` 的字段。
- `SV_ZmZoneAt` 的实现（如何判定"在区域内"）。
- `sv_script_builtin_mp.cpp` 700 行之后未读取（**共 `4424` 行**）。
