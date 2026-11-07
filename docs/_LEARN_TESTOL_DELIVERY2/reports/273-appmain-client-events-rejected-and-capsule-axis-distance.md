# 273 · **`client_events_rejected` 的三个症状一个原因**、`capsule` 的 `axisDist`、`SV_EncodePlayerSolid` 的 70/50/30

## 一、范围

本报告学习 `Appmain.cpp` 599–820 行。

## 二、`bullet-penetration-result` 的**十二个量**

```php
"bullet-penetration-result shooter=%u weapon=%u "
"result=%u hitEntity=%u playerDamage=%d entityDamage=%d "
"impacts=%zu hitType=%u hitId=%u fraction=%.4f "
"surfaceFlags=0x%08X surface=%u"
```

### 2.1 十二项

```text
shooter / weapon
result / hitEntity / playerDamage / entityDamage
impacts / hitType / hitId / fraction
surfaceFlags / surface
```

### 2.2 而 `hitEntity` 用 `value_or(BulletNoneEntityNum)`

```php
executionStatus.hitEntityNum.value_or(CodolGameServer::BulletNoneEntityNum)
```

**⇒ 所以**无命中**会打成一个特定数值而不是 "none"。**

**⇒ 与 §273 后面 `bullet fire REFUSED` 里的 `? std::to_string(*...) : "none"` **不同**。**

**⇒ 两处对同一个 `optional` 用了两种表示。**

### 2.3 `surface = (surfaceFlags >> 20) & 0x1F`

**⇒ 与 §272 一致** ✓

### 2.4 48 条上限

**⇒ 与 §272 的 96 不同（两个不同诊断）。**

## 三、**"两个 damage staged 分开报告"**

```php
executionStatus.playerDamageStaged ? 1 : 0,
executionStatus.entityDamageStaged ? 1 : 0,
```

### 3.1 而后面那段解释

```php
// Report player and generic-entity staging separately. Zombies use
// the latter, so a single damageStaged flag was misleading here.
```

**⇒ "僵尸用后者，所以单个 `damageStaged` 标志在这里是误导的。"**

**⇒ 所以**玩家与通用实体**是两条不同的伤害路径。**

**⇒ 与 §268 的"actor 走通用实体伤害路径"一致** ✓

## 四、**`client_events_rejected` 的三个症状一个原因**（本组最重要的一段）

```php
// SECTION 191z: SAY WHICH REFUSAL IT WAS, ONCE PER KIND PER WEAPON.
//
// A refused shot rejects the WHOLE usercmd upstream
// (`client_events_rejected`), so the player sees no damage, no
// movement commit and a desync -- three symptoms, one cause, and the
// stage name distinguishes none of the thirteen ways to get here.
// Silent while shots are landing; the first alt-fire burst printed
// nothing but `bullet-hit ... damageStaged=1` and a stage name.
```

### 4.1 六层

```text
1. 一次被拒绝的开火在【上游】拒绝【整个 usercmd】
2. ⇒ 玩家看到：没有伤害、没有位移提交、失步
3. ⇒ 【三个症状，一个原因】
4. 而 stage 名区分不了【十三种】到达这里的方式
5. 而成功时沉默
6. 第一次副开火爆发只打了 `bullet-hit ... damageStaged=1` 和一个 stage 名
```

### 4.2 **"十三种方式"**

**⇒ 所以 `SV_ExecuteBulletFire` 有十三条失败路径。**

**⇒ 而 `SV_LastBulletFireFailure()` 返回一个字符串** —— 但那不够（注释说"stage 名区分不了十三种"）。

**⇒ 所以 §273 加了 `reason` + `weapon` + `type` + `class` + `shotCount` + `hitEntity` + `partGroup` + `staged`。**

### 4.3 而"整个 usercmd 被拒"的解释力

**⇒ 这解释了为什么"不移动"与"没伤害"同时出现** —— 因为 usercmd 被整个丢弃。

**⇒ 与记忆里"duplicate usercmd accepted then discarded (rejecting deadlocks)"相关。**

**⇒ 所以拒绝 usercmd 是危险的** —— 会导致卡住。

### 4.4 去重是 `(reason, weaponAssetIndex)` 对

```php
static std::set<std::pair<std::string, std::uint16_t>> bulletFailuresSeen;
report = bulletFailuresSeen.size() < 64 &&
    bulletFailuresSeen.emplace(reason, weapon.weaponAssetIndex).second;
```

**⇒ 两个键 + 64 上限。**

**⇒ "每一种每武器一次"** ✓

**⇒ 与 §240 的 `ordinalReported`（整行）、§244 的 `refuse`（边沿）、§264 的位掩码不同 —— 第四种去重粒度。**

## 五、`entity.lastBulletExecutionStatus` 的保存

```php
if (executionStatus.traced)
    entity.lastBulletExecutionStatus = executionStatus;
```

**⇒ 只在 `traced` 时保存。**

**⇒ 所以"上一次成功的 trace"供后续（如控制台读出）使用。**

## 六、**`SV_EncodePlayerSolid` 的 70/50/30**（本组第二重要）

```php
// OLMOD(locational-hit-diagnostics): report the hit against the pose the
// trace ACTUALLY saw. The control-socket readout joins the target's
// origin from whichever frame it happens to sample and records no
// stance at all, so a hit skeleton that is one stance low and a target
// that was simply crouching produce identical numbers there - of 26
// measured player hits only one could be pinned to a known stance
// afterwards. `collisionEntities` is the exact list this trace ran
// against, and a live player's bounds carry the stance directly:
// SV_EncodePlayerSolid publishes maxs[2] 70 standing / 50 crouch / 30
// prone, measured off retail's own dm recording.
```

### 6.1 三层

```text
1. 控制台读出从某个帧取目标的 origin 而【完全不记录姿态】
2. ⇒ "命中骨架低一个姿态"与"目标只是蹲着"在那边产生【相同数字】
3. ⇒ 26 次实测命中里【只有一次】能事后确定到已知姿态
```

### 6.2 而 `maxs[2]` 的三档

```text
70   站立
50   蹲
30   趴
```

**⇒ "从零售自己的 dm 录像测量"。**

**⇒ 与记忆里"seven adjacent height functions (15/70/50/30/60/40/11)"**相关** —— 其中 70/50/30 是这三个。**

**✓ 一次交叉确认。**

### 6.3 所以 `maxsZ` 是**姿态的直接证据**

**⇒ 而 §273 的 `bullet-trace` 日志打印 `maxsZ=%.0f`** ⇒ 所以每次都能确定姿态。

## 七、**`bullet-trace` 的 `axisDist`**（本组第三重要）

```php
if constexpr (BulletTraceDiagnostics)
{
    if (executionStatus.traced)
    {
        std::string capsules;
        for (const auto &candidate : collisionEntities)
        {
            if (candidate.shape != Capsule) continue;
            // Perpendicular distance from the shot to the capsule's axis,
            // clamped to the segment, in the plane - the same quantity the
            // broadphase decides candidacy on.
            const auto &s = executionStatus.start;
            const auto &e = executionStatus.end;
            std::array<double, 3> d{ e[0]-s[0], e[1]-s[1], e[2]-s[2] };
            std::array<double, 3> w{ candidate.origin[0]-s[0], candidate.origin[1]-s[1], candidate.origin[2]-s[2] };
            const auto dd = d[0]*d[0] + d[1]*d[1] + d[2]*d[2];
            const auto t = dd > 0.0
                ? std::clamp((w[0]*d[0] + w[1]*d[1] + w[2]*d[2]) / dd, 0.0, 1.0)
                : 0.0;
            const auto nearest = std::hypot(w[0] - d[0]*t, w[1] - d[1]*t);
            ... " #%u{linked=%d maxsZ=%.0f axisDist=%.1f}", entityNum, linked, maxsZ, nearest ...
        }
        ...
    }
}
```

### 7.1 数学

```text
d = end - start                    射线段向量
w = candidate.origin - start       从起点到实体原点的向量
t = clamp(w·d / |d|², 0, 1)        【投影参数，夹到 [0,1]】
nearest = hypot(w_x - d_x*t, w_y - d_y*t)    【二维垂直距离】
```

### 7.2 **`nearest` 只用 x 与 y**

**⇒ `hypot(w[0] - d[0]*t, w[1] - d[1]*t)` —— 只有两个分量。**

**⇒ 所以它是**水平**垂直距离。**

**⇒ 而注释说"in the plane"** ✓

**⇒ 这是正确的**，因为胶囊的轴是竖直的（z 轴），所以垂直距离就在 xy 平面内。

### 7.3 而"与宽相判定的是同一个量"

```php
// the same quantity the broadphase decides candidacy on.
```

**⇒ 所以 `axisDist` 与 `SV_ShouldBroadphaseClipToEntity` 用的是同一个判据。**

**⇒ 那把日志值直接对照宽相阈值就能判断"为什么这个实体被/没被考虑"。**

**✓ 一个非常实用的诊断。**

### 7.4 而每个 capsule 打印四个量

```text
entityNum
linked          ← 【我们的】标志（§268）
maxsZ           ← 【姿态】
axisDist        ← 【宽相距离】
```

**⇒ 四个量正好覆盖 §268 里"重生后打不到"的三个可能原因（linked / 姿态 / 距离）。**

## 八、**"一次穿透而过的射击与一次从未开火的射击无法区分"**

```php
// OLMOD(locational-miss-diagnostics): a MISS has to be visible too.
// Logging only entity hits made a shot that passed straight through a
// player indistinguishable from a shot never fired: after the script
// model sponge was removed, the post-respawn magazine produced no lines
// at all, and the control socket showed the last trace stopping in a
// wall 1007 units away while the target stood 148 units away. So report
// every committed trace together with the player capsules that were
// actually in the list it ran against, and how close the ray came to
// each - a capsule that is absent, or present but never intersected,
// are different bugs with the same symptom.
```

### 8.1 四层

```text
1. 只记实体命中 ⇒ 一次穿过玩家的射击与一次从未开火的射击【无法区分】
2. 在 script model sponge 被移除之后，重生后的弹匣【一行都没有】
3. 而控制台显示最后一次 trace 停在【1007 单位外的墙】里，而目标站在【148 单位】处
4. ⇒ 所以报告每一棵已提交的 trace + 它实际跑过的玩家胶囊 + 射线离每一个多近
```

### 8.2 而两个缺陷同一个症状

```text
胶囊【不存在】
胶囊【存在但从未被相交】
```

**⇒ 两个不同的 bug，而"没有命中日志"对两者都一样。**

**⇒ 与 §255 的 `NULL`/`EMPTY`/`UNREADABLE` 三态同族** —— 把"没结果"细分成多种原因。

### 8.3 而那两个数字

```text
1007 单位    最后一次 trace 停的墙
148 单位     目标的距离
```

**⇒ 所以射线被**一堵更近的墙**挡住了。**

**⚠ 而如果目标在 148 而墙在 1007，那墙**更远** ⇒ 不该挡住。**

**⇒ 除非"1007"是**trace 的终点**而不是墙的距离。**

**⇒ 或者那堵墙**在 148 之前**而"1007"是整条射线的长度。**

**⇒ 表述不清。但"停在一堵 1007 单位外的墙里"读起来像是矛盾的。**

**⇒ 值得指出这个表述的可疑处。**

### 8.4 而 `TODO(CODOL): remove once a post-respawn player is hittable`

**⇒ 与 §268 的 `TODO` **完全相同的措辞** ⇒ 同一个未解决问题。**

## 九、**`bullet-trace` 汇总行的六个量**

```php
"bullet-trace shooter=%u hitType=%u hitEntity=%s fraction=%.4f "
"travelled=%.0f capsules=%zu%s"
```

### 9.1 六项

```text
shooter
hitType
hitEntity        （"none" 或数字）
fraction
travelled        = fraction × |end - start|
capsules         数量
（+ 每个 capsule 的明细）
```

### 9.2 而 `travelled` 的三层 `hypot`

```php
executionStatus.trace.fraction * std::hypot(
    std::hypot(
        end[0] - start[0],
        end[1] - start[1]),
    end[2] - start[2])
```

**⇒ `hypot(hypot(dx, dy), dz)` = 三维长度** ✓

**⇒ 而乘 `fraction` 得到**实际行进距离**。**

### 9.3 ⚠ **`std::to_string(*hitEntityNum).c_str()` 是临时对象**

```php
executionStatus.hitEntityNum
    ? std::to_string(*executionStatus.hitEntityNum).c_str()
    : "none",
```

**⇒ `std::to_string(...)` 返回临时 `std::string`，`.c_str()` 指向它。**

**⇒ 而这个临时对象的生命周期到**完整表达式结束** —— 也就是 `snprintf` 调用结束。**

**⇒ 因为 `snprintf` 在完整表达式内执行 ⇒ **安全** ✓**

**⇒ 但这是一个**极易变成悬垂**的写法** —— 如果改成先存指针再用就崩。

**⇒ 与 §244 里 `refuse(("..." + ...).c_str())` 同族。**

## 十、`bullet-hit` 的**十四项**

```php
"bullet-hit shooter=%u target=%u part=%u group=%u "
"playerDamageStaged=%d entityDamageStaged=%d "
"hitZ=%.2f hitRadial=%.2f "
"targetOrigin=%.2f,%.2f,%.2f "
"targetMaxsZ=%.2f targetMinsZ=%.2f targetMaxsX=%.2f "
"targetYaw=%.2f targetScale=%.3f eyeZ=%.2f"
```

### 10.1 十四项

```text
shooter / target / part / group
playerDamageStaged / entityDamageStaged
hitZ          = axis(2) - target->origin[2]      【相对高度】
hitRadial     = hypot(axis(0)-origin[0], axis(1)-origin[1])
targetOrigin (x3)
targetMaxsZ / targetMinsZ / targetMaxsX
targetYaw / targetScale
eyeZ          = start[2] - playerState.origin[2]
```

### 10.2 而 `hitZ` 与 `hitRadial` 是**相对目标原点**的

**⇒ 所以与 `targetMaxsZ`/`targetMinsZ` 对照就能判断命中部位。**

**⇒ 例如 `hitZ` 接近 `targetMaxsZ` ⇒ 头部。**

### 10.3 而 `targetYaw` 是 `angles[1]`

**⇒ 与 §266 的 `entity.angles[1]` 一致** ✓

### 10.4 而 `eyeZ` 是**射击者**的枪口相对高度

```php
executionStatus.start[2] - playerState.origin[2]
```

**⇒ 用 `playerState.origin` 而不是 `entity.networkState`。**

**⇒ 一个细节：两个来源的 origin 可能不同。**

### 10.5 而 `partName`/`partGroup` 都在

**⇒ 与记忆里"hit-location partGroup 2 = head confirmed live"相关。**

## 十一、`switch (result)` 的三支

```php
switch (result)
{
case Applied:        return SvFireWeaponResult::Applied;
case DeferredImpact: return SvFireWeaponResult::DeferredImpact;
default:             return SvFireWeaponResult::Failed;
}
```

### 11.1 **三个状态映射到三个**

**⇒ 而 `default` 覆盖所有其它** —— 所以新增状态会自动变成 `Failed`。

**⚠ 这可能掩盖新的失败类型。**

## 十二、关键结论

1. **`client_events_rejected` 的三个症状（无伤害、无位移、失步）一个原因** —— 整个 usercmd 被拒。
2. **十三条失败路径**，而 stage 名区分不了。
3. **失败去重是 `(reason, weaponAssetIndex)` 对，64 上限** —— 第四种去重粒度。
4. **玩家伤害与通用实体伤害是两条路径**（僵尸用后者）。
5. **`SV_EncodePlayerSolid` 的 `maxs[2]` 70/50/30** 从零售 dm 录像测量 —— 与记忆里的高度函数表交叉确认。
6. **"26 次实测命中里只有一次能确定姿态"** —— 因为控制台不记姿态。
7. **`axisDist` 是二维垂直距离**（因为胶囊轴竖直），且与宽相判据相同。
8. **每个 capsule 打四个量（entityNum/linked/maxsZ/axisDist）** —— 正好覆盖"重生后打不到"的三个可能原因。
9. **"穿过玩家的射击与从未开火的射击无法区分"** —— 引出 miss 诊断。
10. **1007 单位 vs 148 单位的表述可疑**（更远的墙不该挡住更近的目标）。
11. **`std::to_string(...).c_str()` 在 `snprintf` 里安全但易变悬垂**。
12. **`bullet-hit` 的 `hitZ`/`hitRadial` 相对目标原点** ⇒ 与 `maxsZ`/`minsZ` 对照可判断部位。
13. **`eyeZ` 用 `playerState.origin` 而其它用 `entity.networkState`**。
14. **`switch` 的 `default ⇒ Failed`** 可能掩盖新状态。

## 十三、未闭合点

- "1007 单位外的墙"与"148 单位的目标"的表述。
- `BulletNoneEntityNum` 的具体值。
- `SV_EncodePlayerSolid` 的 70/50/30 是否还随 `modelScale` 变。
- `Appmain.cpp` 820 行之后未读取。
