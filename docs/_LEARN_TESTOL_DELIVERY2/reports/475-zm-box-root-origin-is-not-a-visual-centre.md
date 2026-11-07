# 475 · **"那个 marker 是盒子中心，但模块化 M9 的水平中点是 `(-7.88635, .019425)`"** —— `sv_zm_box_mp.cpp` 的 `4400/10000/2000` 三段时间、`40` 单位的升、以及"一个错误的退款比一个卡住的付费抽取更坏"

## 一、范围

本报告学习 `sv_zm_box_mp.cpp`（**`574` 行**）全文件：`BoxRollMs/BoxOfferMs/BoxCloseMs/BoxCost` 四个常量、`SV_FactoryBoxBearRoll` 的概率分档、`SV_FactoryBoxRise` 的四段轨迹、`showSite` 的回滚、`announceFactorySoundAliases` 的两条配置串带、`processFactoryBoxUse` 的七条拒绝与退款、以及 `driveFactoryBox` 的六个阶段。

## 二、**"那个 marker 是盒子中心，但模块化 M9 的水平中点是 `(-7.88635, .019425)`"**（本组最重要的一段）

### 2.1 那段

```cpp
// OLMOD(factory_box_horizontal_center): the marker is centred on the box,
// but the modular M9 horizontal midpoint is (-7.88635,.019425).
// Root mesh origins are not visual centres. Compensate in the box's rotated
// horizontal plane; keep the measured rise height and FX anchor unchanged.
// This is presentation reconstruction, not a recovered retail script.
const float yaw=site.angles[1]*std::numbers::pi_v<float>/180.0f;
const auto &center=weapon->bodyCenter;
if(!std::isfinite(yaw) || !std::isfinite(center[0]) || !std::isfinite(center[1]))return origin;
origin[0]-=std::cos(yaw)*center[0]-std::sin(yaw)*center[1];
origin[1]-=std::sin(yaw)*center[0]+std::cos(yaw)*center[1];
```

### 2.2 二十四层

```text
1. **那个 marker 【是【居中【在那个盒子上**的**】
2. ⇒ **⚠ 而【模块化 M9 的【水平中点**【是 `(-7.88635, .019425)`**】
3. ⇒ **⇒ 所以【根网格的 origin 【不是【一个视觉中心**】
4. ⇒ **⇒ 补偿【在【那个盒子的【旋转后的**水平平面里**】
5. ⇒ **⇒ 而【保留【那个测量的**升起高度**与【那个 FX 锚点**】
6. ⇒ **⇒ 这是【一个**表现层重建**，不是【一个恢复的零售脚本**】
```

### 2.3 ⭐⭐⭐ **"根网格的 origin 不是视觉中心"**

**✅ 这是本报告里**最重要的一条"**一个模型的原点【不是【它的中心**"**。**

**✅ 与 §473 的"`~` 前缀的名字被截断"**——**不同**（那是**命名**，这是**几何**）但**同族**（**"一个资产的**元数据【不承载【视觉事实**"**）。

**⇒ 三层**：
```text
`origin` ⇒ **模型空间的零点**（**由 exporter 决定**）
`bodyCenter` ⇒ **视觉的**中点**（**`(-7.88635, .019425)`**）
⇒ **⇒ 所以【两者【相差 `7.89` 单位**】
```

**✅ ⭐⭐⭐ **"两者相差 7.89 单位"** —— 一个**可量化的偏差**。

**⚠ 而那个旋转补偿的算术**⇒ **一个**标准的 yaw 旋转**。**

**⇒ 独立验证**：
```text
`origin[0] -= cos(yaw)·cx - sin(yaw)·cy`
`origin[1] -= sin(yaw)·cx + cos(yaw)·cy`
⇒ **⇒ 而 `[cos -sin; sin cos]` 【是【一个【绕 `z` 的**旋转矩阵**】
⇒ **⇒ 所以【那个补偿【把 `center` 【从【模型空间【旋转到【世界空间**】并【减掉**
```

**✅ ⭐⭐⭐ **"那个补偿把 center 从模型空间旋转到世界空间并减掉"** —— 一个**正确的几何**。

**✅ 与 §467 的"`SV_SelectMiniMapCorners` 的 `north`/`west`（`{-ny, nx}`）"**——**同族**（**第二次"一个**二维旋转**"**）。

**⇒ 三层**：
```text
§467  **`west = {-north[1], north[0]}`**（**一个 `-90°` 旋转**）
§475  **`[cos -sin; sin cos]`**（**一个 `+yaw` 旋转**）
⇒ **⇒ 两次"一个**二维旋转**"**
```

**✅ ⭐⭐ **"一个二维旋转"两例**。

**⚠ 而"保留那个测量的升起高度与那个 FX 锚点"**⇒ **一个**极精确的**范围界定**。**

**⇒ 十层**：
```text
补偿 ⇒ **只【在【水平面**里】
⇒ **⇒ 所以【`origin[2]` 【不动**】
⇒ **⇒ 而【那个 FX 锚点【也不动**】
⇒ **⇒ 所以【那个 `40` 单位的升**【不受影响**】
```

**✅ ⭐⭐⭐ **"那个 40 单位的升不受影响"** —— 一个**精确的不变量**。

## 三、**"一个错误的退款比一个卡住的付费抽取更坏"**（本组第二重要）

### 3.1 那段

```cpp
// A malformed/stale offer must never strand the paid roll.  This
// owner can refund only the same living buyer, then closes so a
// repeated use cannot mint further refunds.
const bool refunded=world_.changeFactoryBattery(client.clientNum,
    static_cast<std::int32_t>(BoxCost),factoryBox_.life);
OlMod::RuntimeLog::write(...,"ZM BOX CLAIM_REJECT client=... refunded=...");
closeFactoryBox(now);
return false;
```

### 3.2 二十四层

```text
1. **一个畸形/陈旧的 offer 【绝不能【搁浅【那个付费的抽取**】
2. ⇒ **⇒ 【这个所有者【只能退款给【同一个活着的买家**】
3. ⇒ **⇒ 然后【关闭**，所以【一次重复的使用【不能【铸造**更多的退款**】
4. ⇒ **⇒ 而那个退款【用 `factoryBox_.life` （那个 `spawnGeneration`）**作守卫**】
```

### 3.3 ⭐⭐⭐ **"关闭，所以一次重复的使用不能铸造更多的退款"**

**✅ 这是本报告里**最精确的一条"**退款【的**幂等性**"**。**

**✅ 与 §464 的"appender 只能走一步"**——**同族**（**第三次"一个**重复操作【不能**累积**"**）。

**⇒ 三层**：
```text
若【不关闭**】⇒ **⇒ 一个【重复的 `use` 【会【再次【走到【那个退款**】⇒ **⇒ 无限铸造**】
若【关闭**】⇒ **⇒ 那个 `phase` 【变成 `Closing`** ⇒ **⇒ 那个 `Offer` 分支【不可达**】
⇒ **⇒ 所以【"关闭"【是【那个**幂等性**的**唯一**保证**
```

**✅ ⭐⭐⭐ **"'关闭'是那个幂等性的唯一保证"**。

**⚠ 而"那个 `life`（`spawnGeneration`）守卫"**⇒ **一个**第二道**。** 

**⇒ 十层**：
```text
`changeFactoryBattery(client, +1200, factoryBox_.life)` ⇒ **只在【那个玩家的 `spawnGeneration` 【等于 `life`** 时成功**
⇒ **⇒ 所以【一个【已死/重生**的玩家【拿不到【退款**
⇒ **⇒ 而【那【是【第二个**幂等守卫**】
```

**✅ ⭐⭐⭐ **"那是第二个幂等守卫"**。

**✅ 与 §463 的"`spawnGeneration` 的两级代次"**——**完全闭合** ✓

### 3.4 而**"一个畸形/陈旧的 offer 绝不能搁浅那个付费的抽取"**

**✅ 与 §467 的"一个回落比一个失败更危险"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§467  **一个回落**（**选了一个错的出生点**）⇒ 【比失败坏**】
§475  **搁浅**（**收了钱不给东西**）⇒ 【比退款坏**】
⇒ **⇒ 两者【都是【"不做事【比【做错事【好**"**
```

**✅ ⭐⭐⭐ **"不做事比做错事好"两例** —— 而**这里【"退款"【是【"不做事"**（**回到【那个抽取之前**）**。

## 四、**`SV_FactoryBoxBearRoll` 的三段概率**

### 4.1 那段

```cpp
// OLMOD(factory_box_relocation): BO1 _zombiemode_weapons.gsc reference,
// not recovered CODOL probability. No bear on1..3;15% on4..7; first
// location guaranteed at8; later sites30% on8..12 and50% thereafter.
if(paidPull<4)return false;
if(!moves && paidPull>=8)return true;
return random%100 < (paidPull<8?15u:paidPull<13?30u:50u);
```

### 4.2 二十四层

```text
1. **`paidPull < 4` ⇒ 【没有熊**】
2. ⇒ **`paidPull` 在 `4..7` ⇒ `15%`**】
3. ⇒ **⇒ 而【在【第一个位置**（`moves == 0`）【`paidPull >= 8` ⇒ **必出**】
4. ⇒ **⇒ 否则 `8..12` ⇒ `30%`，`>= 13` ⇒ `50%`**
```

### 4.3 ⭐⭐⭐ **"在第一个位置，`paidPull >= 8` 必出"**

**✅ 与 §466 的"`bombzone` 恰好两个"**——**不同**（那是一个**全或无**，这是一个**保底**）但**同族**（**第二次"一个**保证**"**）。

**⇒ 独立验证那张概率表**：
```text
pull  1..3   ⇒ **0%**
pull  4..7   ⇒ **15%**
pull  8..12  ⇒ **30%**（**除非 `moves == 0` ⇒ 100%**）
pull 13+     ⇒ **50%**
⇒ **⇒ 一条【单调上升**的曲线**
```

**✅ ⭐⭐⭐ **"一条单调上升的曲线"**。

**⚠ 而"`random % 100 < X`"**⇒ **一个**有偏**的取模**（**但 `100` 是一个**常见的**基数**，偏差可忽略**）。

**⇒ 三层**：
```text
`random` 是 `uint32` ⇒ **`% 100` 【有【轻微**偏差**】（**`2^32 % 100 = 96`**）
⇒ **⇒ 所以【那个偏差【是【`96 / 2^32 ≈ 2.2e-8`**】⇒ **⇒ 可忽略**】
```

**✅ ⭐⭐ **"偏差可忽略（2.2e-8）"**。

**⚠ 而注释明确说"这不是恢复的 CODOL 概率，是 BO1 的参照"**⇒ **一个**诚实的标注**。**

**✅ 与 §451 的"BO1 Der Riese 是一个捐赠参照"**——**同族**（**第四次"一个**捐赠参照**"**）。

## 五、**`SV_FactoryBoxRise` 的四段轨迹与那个 `speed`**

### 5.1 那段

```cpp
// CODREF(actor_grounded_adapter): original Factory165550/entity781 and Sumpf870800/entity774
// agree on a40unit rise, native types7(2000ms),3(100ms),8(899ms), then0.
// out.exe410BD0 owns acceleration/deceleration; send its trajectory rather
// than stepping a model upward or resetting its clock at each reward swap.
constexpr float speed=25.80645179748535f;
SvNativeTrajectory result{.type=7,.time=...,.duration=2000,.base=origin,.delta={0,0,speed}};
const auto age=now-started;
if(age>=3000) { result.type=0; ... result.base[2]+=40; }
else if(age>=2100) { result.type=8; ... result.duration=899; result.base[2]+=speed*1.1f; }
else if(age>=2000) { result.type=3; ... result.duration=100; result.base[2]+=speed; }
```

### 5.2 二十四层

```text
1. **一个 `40` 单位的升**】
2. ⇒ **⇒ 而【四个原生类型**：`7`（`2000ms`）/ `3`（`100ms`）/ `8`（`899ms`）/ `0`**】
3. ⇒ **⇒ 而 `out.exe` 的 `410BD0` 【拥有【加速/减速**】
4. ⇒ **⇒ 所以【发送【它的轨迹**】而不是【每一帧【把一个模型【往上【步进**】
5. ⇒ **⇒ 也不用【在每次奖励交换时【重置它的时钟**】
```

### 5.3 ⭐⭐⭐ **"发送它的轨迹，而不是每一帧把一个模型往上步进"**

**✅ 与 §475 三 的"那个 `40` 单位的升不受影响"**——**完全闭合** ✓

**⚠ 而那个 `speed` 的精确值**⇒ **`25.80645179748535`** **⇒ 一个**极精确**的浮点**。**

**⇒ 独立验证**：
```text
`25.8064518 × 2000 / 1000 = 51.61` ⇒ **不是 `40`**
`25.8064518 × 1.1 = 28.387`
⇒ **⇒ 而 `40 / 25.8064518 = 1.55` 秒**
```

**⚠ 标注：那个 `speed` 与 `40` 单位的**关系**不明**（`2000ms` 的 `type 7` 用 `speed` 作 `delta`，但**净升** `40` 是在 `type 0` 时的 `base[2] += 40`）**。**

**⇒ 三层**：
```text
`type 7`（`2000ms`）⇒ **`delta = {0,0,speed}`**（**一个**速度场**）
`type 3`（`100ms`）⇒ **`base[2] += speed`**
`type 8`（`899ms`）⇒ **`base[2] += speed × 1.1`**
`type 0`（`3000ms`）⇒ **`base[2] += 40`**（**绝对**）
⇒ **⇒ 所以【`40` 是【那个【最终**的位移**，而【`speed` 是【那个**速度场的系数**】
```

**✅ ⭐⭐⭐ **"40 是那个最终的位移，而 speed 是那个速度场的系数"** —— 一个**精确的读法**。

**⚠ 而 `25.80645179748535` 的精确表示**⇒ **可能【是【某个**分数**。**

**⇒ 十层**：
```text
`1 / 25.80645179748535 = 0.0387500...`
⇒ **⇒ 而【`40 × 0.03875 = 1.55`**
⇒ **⇒ 所以【那个 `speed` 【可能【是 `40 / 1.55`**】
```

**⚠ 标注为未闭合**（`40 / 1.55 = 25.8064516...` —— **与那个值【吻合到 8 位**）**！**

**✅ ⭐⭐⭐ **"`40 / 1.55 = 25.8064516…` 与那个值吻合到 8 位"** —— 一个**几乎确定的推导**。

**⚠ 而"`1.1` 与 `899` 与 `100`"**⇒ **三个**分段**的时长**（`2000` / `100` / `899` = `2999`，**而 `3000` 是那个总和**）**。**

**⇒ 十层**：
```text
`2000 + 100 + 899 = 2999`
⇒ **⇒ 而【那个判据【是 `age >= 3000`**】⇒ **⇒ 所以【有 `1ms` 的【空隙**】
⇒ **⇒ 而那个空隙【落在 `type 8` 的结尾与 `type 0` 的开头之间**】
```

**✅ ⭐⭐⭐ **"`2000 + 100 + 899 = 2999`，而有 1ms 的空隙"** —— 一个**精确的算术观察**。

**✅ 与 §459 的"两个缩放窗口不相接（第三次更新重用 `t+100` 起点而 `172ms` 已过）"**——**同族**（**第二次"一个**时间窗口【不相接**"**）。

## 六、**`showSite` 的全量回滚**

### 6.1 那段

```cpp
bool showSite(SvServerWorld &world,const SvFactoryBoxSite &site,bool active) {
    std::vector<std::pair<SvEntityHandle,SvGameEntity>> changed;
    for(const auto h:{site.base,site.lid,site.rubble})if(h) {
        const auto e=world.entity(*h);if(!e)return false;
        changed.emplace_back(*h,*e);
    }
    for(const auto &[h,e]:changed) {
        const bool visible=site.rubble && h==*site.rubble?!active:active;
        if(!world.setScriptModelTransformAndActive(h,e.currentOrigin,e.currentAngles,visible)) {
            for(const auto &[prior,old]:changed)
                static_cast<void>(world.setScriptModelTransformAndActive(prior,old.currentOrigin,old.currentAngles,old.gameplayActive));
            return false;
        }
    }
    return true;
}
```

### 6.2 二十四层

```text
1. **先【收集**三个实体（`base`/`lid`/`rubble`）而【快照它们**】
2. ⇒ **⇒ 然后【逐个设置可见性**】
3. ⇒ **⇒ 若任一失败 ⇒ 【全量回滚**（遍历**全部**三个，不是【只回滚【已改的**）**
4. ⇒ **⚠ 而 `rubble` 【的可见性【是【取反**的】（`? !active : active`）**
```

### 6.3 ⭐⭐⭐ **"rubble 的可见性是取反的"**

**✅ 与 §474 的 `showSite` 的"一个加法不是一次翻译"**——**不同**（那是一个**存在性**，这是一个**极性**）但**同族**（**第三次"一个**字段的语义【与【它的名字**相反**"**）。

**⇒ 三层**：
```text
`base` / `lid` ⇒ **`active`**（**站点活跃 ⇒ 可见**）
`rubble` ⇒ **`!active`**（**站点活跃 ⇒ 隐藏**）
⇒ **⇒ 所以【`rubble` 的语义【是【"站点【不活跃**"的标志**】
```

**✅ ⭐⭐⭐ **"rubble 的语义是『站点不活跃』的标志"** —— 而**注释明说**："**Authored rubble is visible only at inactive sites**"。

**⚠ 而"全量回滚【遍历全部三个，不是只回滚已改的**"**⇒ **一个**正确的**的回滚**。**

**⇒ 十层**：
```text
若【只回滚【已改的**】⇒ **⇒ 一个【已成功改的**【留在【新状态**】
若【回滚全部**】⇒ **⇒ 那些【未改的【被【重设成【它们【原本的**值**】⇒ **⇒ 幂等** ✓
⇒ **⇒ 所以【后者【正确**】
```

**✅ ⭐⭐⭐ **"回滚全部是幂等的"** —— 与 §462 的"那是一个发现"**不同**，但与 §475 三 的"关闭是幂等性的唯一保证"**同族**（**第二次"幂等**"**）。

## 七、**`announceFactorySoundAliases` 的两条配置串带**

### 7.1 两带

```text
① 音效别名：`SoundAliasConfigStringBase + 50..90`（**`41` 个槽**）
   12 个名字（`zmb_box_open` … `zmb_monkey_song`）
② Tesla 视图特效：`4536 + 1..31`（**`31` 个槽**）
   每个 `fx` ⇒ `digits = std::to_string(1000+fx).substr(1) + "tag_brass"`
```

### 7.2 二十四层

```text
1. **`50..90` ⇒ `41` 个音效别名槽**】
2. ⇒ **⇒ 而【`4536 + 1..31` ⇒ `31` 个 Tesla 槽**】
3. ⇒ **⇒ 而那个 `digits` 的构造【是【`1000+fx` 的【后三位】+ `tag_brass`**】
4. ⇒ **⇒ 所以【`fx = 183` ⇒ `std::to_string(1183).substr(1)` = `"183"` + `"tag_brass"`**】
```

### 7.3 ⭐⭐⭐ **"`std::to_string(1000+fx).substr(1)` 是把一个三位数左边补零的写法"**

**✅ 一个**极精巧**的惯用法**。**

**⇒ 独立验证**：
```text
`fx = 183` ⇒ **`1000 + 183 = 1183`** ⇒ **`substr(1) = "183"`** ✓
`fx = 7`   ⇒ **`1000 + 7 = 1007`**   ⇒ **`substr(1) = "007"`** ✓
`fx = 400` ⇒ **`1400`** ⇒ **`"400"`**（**但 `fx >= 400` 被拒绝**）✓
```

**✅ ⭐⭐⭐ **"那是把一个三位数左边补零的写法"** —— 而 **`fx < 400` ⇒ 恰好三位** ✓

**✅ 与 §470 的"`std::to_string` 的用法"**——**不同**（那里**直接用**，这里**借 `1000+` 补零**）。

**⚠ 而"`cs 4536 + (parm >> 1)`"**⇒ **一个**正确的消费者**。**

**⇒ 十层**：
```cpp
// CODREF(sv_build_client_snapshot): CODOL5328D0 consumes cs4536+(parm>>1).
// Original July31 Factory registers 183/184/186 + tag_brass at4537/39/40.
```
```text
消费者 ⇒ **`cs 4536 + (parm >> 1)`**
而【原版【注册 `183`/`184`/`186` ⇒ **在 `4537`/`4539`/`4540`**
⇒ **⇒ 所以【`parm` 是【偶数**：（`4537-4536）×2 = 2`，而 `(4539-4536)×2 = 6`，`(4540-4536)×2 = 8`
⇒ **⇒ ⚠ 但 `4540` 是【奇数**差（`4`）×2 = `8`，而 `4539` 差 `3` ×2 = `6` —— **一致**
```

**✅ ⭐⭐ **"parm 是偶数"** —— 而 `parm >> 1` 的语义**正确**。

**✅ 与 §465 的 `EffectConfigStringCount = 400`**——**一个衔接**（**`fx >= 400` 被拒绝**）。

## 八、**`processFactoryBoxUse` 的七个拒绝与四个后果**

### 8.1 七个拒绝

```text
1  factoryBoxHint 空 ⇒ return false（不是拒绝，是"不适用"）
2  !state 或 !health 或 gameplayState != Playing ⇒ return false
3  !canQueueReliableCommands ⇒ return false（**在扣钱之前**）
4  奖励授予失败 ⇒ 退款 + closeFactoryBox + CLAIM_REJECT
5  显示实体创建失败 ⇒ freeEntity + return false（**在扣钱之前**）
6  电池扣除失败 ⇒ freeEntity + return false
7  choices 空 ⇒ return false（**在扣钱之前**）
```

### 8.2 二十四层

```text
1. **三道【在扣钱之前**（`canQueue` / `display` / `choices`）**
2. ⇒ **⇒ 而【第四道【是【唯一的**扣钱后失败**（**退款**）**
3. ⇒ **⇒ 而【第六道（电池扣除失败）【在【扣钱【那一刻**【失败**】⇒ **⇒ 无退款需求**（**没扣成**）
```

### 8.3 ⭐⭐⭐ **"三道在扣钱之前，一道在扣钱之后（退款），一道是扣钱本身失败"**

**✅ 与 §471 的 `GlassCommandRollback`**——**同族**（**第五次"一个**两阶段**的提交**"**）。

**⇒ 三层**：
```text
扣钱前 ⇒ **三道【预检**】⇒ **⇒ 无副作用**
扣钱 ⇒ **一次**【原子**
扣钱后 ⇒ **一道【可能失败**】⇒ **⇒ 需要退款**
⇒ **⇒ 所以【"扣钱"【是【那个**分界线**】
```

**✅ ⭐⭐⭐ **"'扣钱'是那个分界线"** —— 而**退款【只【在分界线之后**出现**。

**⚠ 而"`changeFactoryBattery(client, -1200, state->spawnGeneration)`"**⇒ **一个**带 `spawnGeneration` 守卫**的扣款**。**

**⇒ 十层**：
```text
若【扣款【不带 `spawnGeneration`**】⇒ **⇒ 一个【在【两个 usercmd 之间【重生**的玩家【会【被【扣掉**新生命的**电池**】
带 ⇒ **⇒ 那个扣款【在【旧的 generation 上【失败**】⇒ **⇒ 正确**】
```

**✅ ⭐⭐⭐ **"那个扣款在旧的 generation 上失败 ⇒ 正确"** —— 第三次"一个代次守卫"（与 §463/§469 同族）。

## 九、**`driveFactoryBox` 的六个阶段**

```text
Closed ⇒ Rolling ⇒ {Offer | Bear} ⇒ Closing ⇒ Closed
                              Bear ⇒ Departing ⇒ Relocating ⇒ Closing ⇒ Closed
```

### 9.1 二十四层

```text
1. **`Closed` ⇒ 【初始**】
2. ⇒ **`Rolling` ⇒ `4400ms`**（**那个 `BoxRollMs`**）⇒ **⇒ `Offer`（`10000ms`）或 `Bear`**
3. ⇒ **`Offer` ⇒ `10000ms` 后【自动关闭**】
4. ⇒ **`Bear` ⇒ `2500ms` 升 + `5500ms` 移动 + `6500ms` 后【分离** ⇒ `Departing`**
5. ⇒ **`Departing` ⇒ `5000ms` ⇒ `Relocating`**
6. ⇒ **`Relocating` ⇒ `12000ms` ⇒ 跳到【新站点**】⇒ `Closing`**
7. ⇒ **`Closing` ⇒ `2000ms` ⇒ `Closed`**
```

### 9.2 ⭐⭐⭐ **"一个完整周期 `4400 + 10000 + 2000 = 16400ms` 或 `4400 + 6500 + 5000 + 12000 + 2000 = 29900ms`"**

**✅ 与 §475 二 的"`40` 单位的升"**——**配合**（**`BoxRollMs = 4400` 内**那个 `3000ms` 的升【已完成**）**。

**⇒ 独立验证**：
```text
`SV_FactoryBoxRise` 的 `age >= 3000` ⇒ **`type 0`**（**静止在 +40**）
而 `BoxRollMs = 4400` ⇒ **⇒ 所以【`1400ms` 的**静止展示**】
```

**✅ ⭐⭐⭐ **"1400ms 的静止展示"** —— 一个**精确的余量**。

**✅ 与 §475 五 的"`2000 + 100 + 899 = 2999` 而有 1ms 空隙"**——**配合**。

### 9.3 而**"一次的 relocation 只在 `Bear` 之后"**

**⇒ 十层**：
```text
若【普通 `Offer` ⇒ 关闭**】⇒ **⇒ 【不移动**】
若【`Bear` ⇒ 退款 ⇒ 【移动**】
⇒ **⇒ 所以【只有【熊【触发【relocation**】
```

**✅ ⭐⭐⭐ **"只有熊触发 relocation"** —— 而**那【正是【BO1 的规则**（**熊 = 盒子移动**）**。**

**⚠ 而 `factoryBox_.moves` 的**双重用途**】。**

**⇒ 十层**：
```text
`SV_FactoryBoxBearRoll(factoryBox_.pulls, factoryBox_.moves, seed>>8)` ⇒ **`moves` 是一个**参数**】
`++factoryBox_.moves` ⇒ **在 relocation 之后**
⇒ **⇒ 所以【`moves` 【是【"已移动过几次**"**】
```

**✅ ⭐⭐ **"moves 是『已移动过几次』"** —— 而 `!moves && paidPull >= 8` ⇒ **在第一个位置保底**。

**✅ 与 §475 四 的"在第一个位置保底"**——**完全闭合** ✓

## 十、关键结论

1. **⭐⭐⭐ "那个 marker 是居中在那个盒子上的，但模块化 M9 的水平中点是 `(-7.88635, .019425)`；根网格的 origin 不是视觉中心"`** ⇒ **"补偿在那盒子的旋转后的水平平面里；保留那个测量的升起高度与那个 FX 锚点"`** —— 而那个补偿是一个**标准的 `[cos -sin; sin cos]` 旋转**（与 §467 的 `north`/`west` 同族），且 **`origin[2]` 不动 ⇒ "那个 40 单位的升不受影响"`**。
2. **⭐⭐⭐ "一个畸形/陈旧的 offer 绝不能搁浅那个付费的抽取：这个所有者只能退款给同一个活着的买家，然后关闭，所以一次重复的使用不能铸造更多的退款"`** —— **"'关闭'是那个幂等性的唯一保证"`**，而 **`changeFactoryBattery(client, +1200, factoryBox_.life)` 的 `life`（`spawnGeneration`）是第二个幂等守卫** —— 与 §467 的"一个回落比一个失败更危险"构成 **"不做事比做错事好"两例**。
3. **⭐⭐⭐ `SV_FactoryBoxBearRoll` 的三段概率**（`1..3` ⇒ 0% / `4..7` ⇒ 15% / `8..12` ⇒ 30% / `13+` ⇒ 50%），而 **`!moves && paidPull >= 8` ⇒ 在第一个位置保底 100%** ⇒ **"一条单调上升的曲线"`**；`random % 100` 的偏差是 **`96 / 2^32 ≈ 2.2e-8`**（可忽略）。
4. **⭐⭐⭐ `SV_FactoryBoxRise` 的四段轨迹**（`type 7` `2000ms` / `type 3` `100ms` / `type 8` `899ms` / `type 0`）⇒ **"发送它的轨迹，而不是每一帧把一个模型往上步进，也不用在每次奖励交换时重置它的时钟"`**；而 **`speed = 25.80645179748535` 恰好是 `40 / 1.55` 的 float32 舍入值**（`40/1.55 = 25.806451612903…`，与那个常量差 `1.85e-7`，而该量级的 float32 ulp 是 `1.91e-6` ⇒ **在一个 ulp 之内**）⇒ **"那个 `speed` 就是『40 单位在 1.55 秒内走完』的速率，而它被写成了 float32 的精确舍入"`**；且 **`2000 + 100 + 899 = 2999` 而判据是 `age >= 3000` ⇒ 有 1ms 的空隙**（与 §459 的"两个缩放窗口不相接"同族）。
5. **⭐⭐⭐ `showSite` 的全量回滚**（遍历**全部**三个，不是只回滚已改的）⇒ **"回滚全部是幂等的"`**；而 **`rubble` 的可见性是取反的**（`? !active : active`）⇒ **"rubble 的语义是『站点不活跃』的标志"`**（注释：**"Authored rubble is visible only at inactive sites"`**）。
6. **⭐⭐⭐ `announceFactorySoundAliases` 的两条配置串带**：音效 `50..90`（`41` 槽、`12` 个名字）、Tesla `4536+1..31`（`31` 槽）⇒ 而 **`std::to_string(1000+fx).substr(1)` 是把一个三位数左边补零的写法**（独立验证 `fx=7 ⇒ "007"`、`fx=183 ⇒ "183"`）—— 而 `fx < 400` 保证恰好三位。消费者是 **"`cs 4536 + (parm >> 1)`"**，而原版注册 `183`/`184`/`186` 在 `4537`/`4539`/`4540` ⇒ **`parm` 是偶数 ✓**。
7. **⭐⭐⭐ `processFactoryBoxUse` 的七个拒绝** ⇒ **"三道在扣钱之前（`canQueue` / `display` / `choices`），一道在扣钱之后（退款），一道是扣钱本身失败"`** ⇒ **"'扣钱'是那个分界线"`** —— 与 §471 的 `GlassCommandRollback` 同族；而 **扣款带 `spawnGeneration` 守卫 ⇒ "那个扣款在旧的 generation 上失败 ⇒ 正确"`**。
8. **⭐⭐⭐ `driveFactoryBox` 的六个阶段**（`Closed ⇒ Rolling(4400) ⇒ Offer(10000)/Bear(6500) ⇒ Closing(2000) ⇒ Closed`；`Bear ⇒ Departing(5000) ⇒ Relocating(12000) ⇒ Closing`）⇒ **独立算得两个周期 `4400 + 10000 + 2000 = 16400ms` 与 `4400 + 6500 + 5000 + 12000 + 2000 = 29900ms`**；而 **`SV_FactoryBoxRise` 的 `3000ms` 在 `BoxRollMs = 4400` 内完成 ⇒ "1400ms 的静止展示"`**。
9. **⭐⭐ `factoryBox_.moves` 的双重用途**：作为 `SV_FactoryBoxBearRoll` 的参数（`!moves && paidPull >= 8` ⇒ 第一个位置保底）与在 relocation 之后 `++` ⇒ **"moves 是『已移动过几次』"`**。
10. **⭐⭐ 只有 `Bear` 触发 relocation**（普通 `Offer` 直接关闭）—— **那正是 BO1 的规则**（熊 = 盒子移动）。

## 十一、`sv_zm_box_mp.cpp` 全文件总览

**`574` 行。**

**`4` 个时间/代价常量**：
```text
BoxRollMs   4400
BoxOfferMs 10000
BoxCloseMs  2000
BoxCost     1200
```

**`6` 个匿名命名空间函数**：`elapsed` / `showSite` / `freePresentation` / `boxPoof` / `SV_FactoryBoxBearRoll` / `SV_FactoryBoxNextSite` / `SV_FactoryBoxDisplayOrigin` / `SV_FactoryBoxRise` / `SV_StopFactoryBoxFx` / `SV_StartFactoryBoxFx` / `SV_FactorySoundAliasSlot`。

**`5` 个 `ServerCore` 方法**：`setFactoryBoxResources` / `announceFactorySoundAliases` / `factoryInteractionSound` / `factoryBoxHint` / `closeFactoryBox` / `processFactoryBoxUse` / `driveFactoryBox`。

**六个阶段**：`Closed` / `Rolling` / `Offer` / `Bear` / `Closing` / `Departing` / `Relocating`。

**`12` 个音效名**（`zmb_box_open` / `zmb_music_box` / `zmb_box_cycle` / `zmb_box_select` / `zmb_box_close` / `zmb_box_move` / `zmb_box_poof` / `zmb_box_poof_land` / `zmb_box_raise` / `zmb_couch_slam` / `zmb_vox_ann_magicbox` / `zmb_monkey_song`）+ **`5` 个 pack-a-punch**（`mus_perks_packa_sting` / `zmb_perks_packa_upgrade` / `zmb_perks_packa_ready` / `zmb_perks_packa_ticktock` / `zmb_packapunch_pickup`）。

**`5` 个测量锚点**：Factory `165550` 开 / `169950` 选 / Sumpf `870800` 升 / `870850` FX / Prototype `590750` 弹药实体 `537` / `591550` 弹药奖励。

**`7` 条拒绝路径**，`2` 条退款路径。

## 十二、未闭合点

- `speed = 25.8064518` 与 `40` 单位的精确关系（我推 `40 / 1.55`）。
- `type 7/3/8/0` 的语义（加速 / 保持 / 减速 / 静止？）。
- `SV_FactoryBoxNextSite` 的"uniform OTHER authored location"与 CODOL 原版的 shuffle 的关系。
- `factorySoundResolver_` 的绑定。
- `SvFactoryBoxResources::reconstructedPool` 的语义。
- 下一个文件：`sv_collision_mp.cpp`（`33,184` 字节）。
