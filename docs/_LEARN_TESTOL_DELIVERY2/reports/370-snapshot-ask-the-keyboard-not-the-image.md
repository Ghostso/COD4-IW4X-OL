# 370 · **"哪个位是交替开火键？去问键盘，不要问镜像"** —— 两个错位的位（`0x100000` 是 ADS、`0x08000000` 在空闲客户端三分钟 63 次）、真正的触发器是 `n 89`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 19600–20000 行。

## 二、**原生 pmove 的两条换武器路径都不可达**（本组第二重要）

### 2.1 那段

```php
// Native Pmove has exactly two paths that begin a weapon change, and
// neither is reachable for an alt:
//
//   sub_429E10  selects from playerState +0x3E8/+0x3EC/+0x3F0. Those
//               three are not netfields (the complete table for this
//               build, indices 0..245, has no entry in that block) and
//               NOTHING in the image writes them. Filling them
//               server-side put the right host and the right alt in the
//               right fields and desynced the match, because the client
//               went on predicting against zeros.
//   sub_429DA0  needs playerState +0x254 != 2047, and +0x24C/+0x250/
//               +0x254 are cursorHint / cursorHintString /
//               cursorHintEntIndex in that order. That is the pick-up-a-
//               dropped-weapon path, not this one.
//
// And the player's own weapon list at +0x2F4 is never written either:
// sub_40E140, sub_4327E0 and sub_4329E0 all walk it, and all three have
// a branch that ignores it and scans the global weapon table instead.
// This build runs in that mode.
```

### 2.2 十四层

```text
1. **原生 pmove 恰好有两条开始一次换武器的路径，而两条对 alt 都不可达**
2. ⇒ **`sub_429E10` 从 `playerState +0x3E8/+0x3EC/+0x3F0` 选择**
3. ⇒ **那三个【不是 netfield】**
4. ⇒ **（这个 build 的完整表，索引 `0..245`，在那个块里【没有条目】）**
5. ⇒ **而镜像里【没有任何东西写它们】**
6. ⇒ **在服务端填它们把正确的宿主与正确的 alt 放进了正确的字段**
7. ⇒ **而让比赛【失步】**
8. ⇒ **因为客户端继续对着【零】做预测**
9. ⇒ **`sub_429DA0` 需要 `playerState +0x254 != 2047`**
10. ⇒ **而 `+0x24C/+0x250/+0x254` 按顺序是 `cursorHint` / `cursorHintString` / `cursorHintEntIndex`**
11. ⇒ **那是"捡起一把掉落的武器"的路径，不是这条**
12. ⇒ **而玩家自己的武器列表在 `+0x2F4` 也【从不被写】**
13. ⇒ **`sub_40E140`、`sub_4327E0`、`sub_4329E0` 都走它**
14. ⇒ **而三个都有一个分支【忽略它】并扫描全局武器表**
15. ⇒ **这个 build 运行在那个模式**
```

### 2.3 ⭐ **"在服务端填它们 ⇒ 客户端继续对着零做预测 ⇒ 失步"**

**✅ 与 §368 的"`constBaselines` 的 XOR 抵消"**同族（**第二次"服务端对了而客户端不一致"**）。

**⇒ 三层**：

```text
1. 服务端填了三个非 netfield
2. ⇒ **那些值【不上线】**
3. ⇒ **所以客户端仍是零**
4. ⇒ **⇒ 预测分叉 ⇒ 失步**
```

**✅ **一个极关键的原理：不能写非 netfield 来影响客户端。**

### 2.4 而**"完整表 0..245 在那个块里没有条目"**

**✅ 与 §339 的"`clientState_s` 从 76 项变 87 项"**不同**（那是**87 项**，这是 **246 项**）。**

**⚠ 所以**两张不同的表**：**

```text
playerState 的 netfield 表   **0..245**（246 项）
clientState 的 netfield 表   87 项
clientInfo 的                ?
```

**✅ 与 §316 的 `ClientInfoFieldCount = 87`**配合。**

### 2.5 而**"全局武器表模式"**

**⇒ 三层**：

```text
1. 三个函数都【能】走玩家的武器列表
2. ⇒ **但三个都有分支忽略它**
3. ⇒ **并扫描全局武器表**
4. ⇒ **这个 build 在【那个】模式**
```

**✅ 一个**明确的"这个 build 的行为"陈述**。**

## 三、**两个错位的按钮位**（本组最重要的一段）

### 3.1 那段

```php
// WHICH BIT IS THE ALT-FIRE KEY? ASK THE KEYBOARD, NOT THE IMAGE.
//
// sect.190 spent two sessions on 0x100000 read out of a decompilation,
// and it is AIM DOWN SIGHTS. The player's key is "3", so the answer is
// one press away: print the bits that go from clear to set, and the bit
// that appears when they press 3 and nothing else IS the button. The
// config cannot answer it -- players/config_mp.cfg is encrypted -- and
// guessing a second constant off the same decompilation would repeat
// the mistake exactly ([[a-decompiled-constant-is-a-hypothesis]]).
//
// RISING EDGES ONLY, so a held key prints once instead of every frame,
// and capped. OLMOD_LOG_BUTTONS=1.
```

### 3.2 十三层

```text
1. **哪个位是交替开火键？去问【键盘】，不要问【镜像】**
2. ⇒ **sect.190 花了两个会话在从反编译读出的 `0x100000` 上**
3. ⇒ **而它是【瞄准镜】**
4. ⇒ **玩家的键是 `3`，所以答案只有一次按键之遥**
5. ⇒ **打印那些从清零变置位的位**
6. ⇒ **而按下 `3` 而没有别的时出现的那个位【就是】那个按钮**
7. ⇒ **配置不能回答它** —— `players/config_mp.cfg` 是【加密的】
8. ⇒ **而从同一份反编译猜第二个常数会【精确地重复那个错误】**
9. ⇒ **（`[[a-decompiled-constant-is-a-hypothesis]]`）**
10. ⇒ **只报告上升沿**
11. ⇒ **所以一个按住的键打印一次而不是每帧**
12. ⇒ **并封顶**
13. ⇒ **`OLMOD_LOG_BUTTONS=1`**
```

### 3.3 ⭐⭐ **"从反编译读出的常数是一个假设"**

**✅ 这是本文件里**最重要的一条方法论陈述**，而且它**引用了一个记忆条目**。**

**⇒ 三层**：

```text
1. 反编译给出【一个常量】
2. ⇒ **而常量在什么上下文里用【由反编译决定】**
3. ⇒ **所以"0x100000 出现"不等于"0x100000 是 alt 键"**
```

**✅ 与 §360 的"索引→偏移相同而编解码器不同"**同族（**第三次"反编译的局部正确"**）。

**⚠ 而"两个会话"⇒ **一个昂贵的教训**。**

**✅ 与 §355 的"0.385 错了 4.8 倍"**同族（**第三次"一个数值错整个结论错"**）。

### 3.4 而**第二个错位的位**

```php
// sect.190's **0x100000** was read off sub_425440's fire types and
// never confirmed against a press: it is AIM DOWN SIGHTS, which is
// why the switch shipped and re-readied the weapon on every
// right-click. **0x08000000** was mine, taken from a window I
// called isolated on two edges for ten presses, and it fires
// **63 times in three minutes on an IDLE client** -- it is not a
// keypress at all.
constexpr std::uint32_t FlickeringButtonBit = 0x08000000;
```

**⇒ 八层**：

```text
1. **`0x100000` 是从 `sub_425440` 的 fire types 读出而【从未】对一次按键确认**
2. ⇒ **它是【瞄准镜】**
3. ⇒ **那就是为什么那个切换发布后【每次右键都重新举起武器】**
4. ⇒ **`0x08000000` 是【我的】**
5. ⇒ **取自一个我称为"隔离"的窗口，十次按键两个边沿**
6. ⇒ **而它在【一个空闲客户端】上三分钟【触发 63 次】**
7. ⇒ **它【根本】不是一个按键**
8. ⇒ **所以被从边沿触发中排除**
```

### 3.5 ⭐ **"在一个空闲客户端上三分钟 63 次"**

**✅ 一个**决定性的否证**。**

**⇒ 三层**：

```text
正面证据：十次按键两个边沿（看起来是键）
负面证据：**空闲客户端三分钟 63 次** ⇒ **不是键**
```

**✅ 与 §353 的"`zmDamageRoll` 的 LCG 低位交替"**同族（**第二次"看起来随机其实是确定性伪影"**）。**

**⚠ 而"最可能是 sect.186 的 delta 解码里一个持续位在闪烁"⇒ **一个具体的解释**。**

### 3.6 而**"排除出边沿但不从掩码里隐藏"**

```php
// 0x08000000 produced 63 rising edges in three minutes,
// including a run on the IDLE second client that nobody was
// touching, so it is not a press -- most likely a held bit
// flickering through sect.186's delta decode. Left in, it is
// the only thing that ever appears and it buried the bit this
// probe exists to find. Excluded from the EDGE only: the mask
// still carries it, so this is not filtering on what is being
// measured, it is removing a known oscillator from the trigger.
const auto rising = (now & ~before) & ~FlickeringButtonBit;
```

**⇒ 九层**：

```text
1. **只从【边沿】里排除**
2. ⇒ **而【掩码仍携带它】**
3. ⇒ **所以这不是在过滤【被测量的东西】**
4. ⇒ **它是从一个触发器里移除一个【已知的振荡器】**
5. ⇒ 所以 `rising = (now & ~before) & ~FlickeringButtonBit`
6. ⇒ **而日志仍打印完整的 `mask=0x%08X`**
```

**✅ ⭐ 一个**极精细的证据学区分**：**

```text
过滤【测量】⇒ 数据丢失
过滤【触发器】⇒ 只影响何时记录，数据仍完整
```

**✅ 与 §347 的"这是线半而对另一半盲"**第七次"声明边界"。

### 3.7 而**"键 3 根本不产生 usercmd 按钮"**

```php
// Key 3 emits NO usercmd button. Measured with a positive control:
// two left-clicks gave exactly two 0x00000001 edges in the same
// window where five presses of 3 gave NONE.
```

**⇒ 六层**：

```text
1. **键 3【根本不】发出一个 usercmd 按钮**
2. ⇒ **用一个【阳性对照】测量**
3. ⇒ **两次左键给出恰好两个 `0x00000001` 边沿**
4. ⇒ **在同一个窗口里按下 `3` 五次给出【零个】**
5. ⇒ **所以阳性对照证明探针在工作**
6. ⇒ **而 `3` 确实不产生按钮**
```

**✅ ⭐ **"阳性对照"** —— 一个**教科书级的实验设计**。**

**⚠ 而"五次按键零边沿"⇒ **一个强的负面**。**

**✅ 与 §340 的"定向的负面"**第六次。

## 四、**真正的触发器：`n 89` 可靠命令**（本组第三重要）

### 4.1 那段

```php
// AND THE REAL TRIGGER, WHICH IS A COMMAND AND NOT A BUTTON.
//
// Two wrong bits preceded this: sect.190's 0x100000, read off
// sub_425440 and actually aim-down-sights, and 0x08000000, which I
// took from a contaminated window and which fires 63 times in three
// minutes on an IDLE client. Key 3 emits NO usercmd button at all --
// measured with a control, two left-clicks giving exactly two
// 0x00000001 edges while five presses of 3 gave none.
//
// The player's menu names the action "Weapon Attachments" and puts
// it beside the killstreaks on 4-7, none of which are `+` binds. It
// arrives as the reliable client command `n 89`: ten presses, ten
// commands, an exact count match.
```

### 4.2 十四层

```text
1. **而【真正的】触发器，它是一个【命令】而不是一个【按钮】**
2. ⇒ **两个错的位在它之前**
3. ⇒ **sect.190 的 `0x100000`，从 `sub_425440` 读出而实际上是 ADS**
4. ⇒ **而 `0x08000000`，我从一个【污染过的】窗口取的**
5. ⇒ **而它在空闲客户端上三分钟触发 63 次**
6. ⇒ **键 3 【根本】不发出一个 usercmd 按钮**
7. ⇒ **用一个对照测量：两次左键给出恰好两个 `0x00000001` 边沿**
8. ⇒ **而按 `3` 五次给出零个**
9. ⇒ **玩家的菜单把那个动作命名为 "Weapon Attachments"**
10. ⇒ **并把它放在 4-7 的连杀奖励旁边**
11. ⇒ **而那些都不是 `+` 绑定**
12. ⇒ **它以可靠客户端命令 `n 89` 到达**
13. ⇒ **十次按键，十条命令，一个精确的数量匹配**
14. ⇒ **所以那个命令是触发器**
```

### 4.3 ⭐ **"十次按键十条命令，一个精确的数量匹配"**

**✅ 与 §352 的"`a <n>` 与 `(35, n)` 的 7/7 配对"**同族（**第二次"精确计数匹配"**）。

**⚠ 而这里是 **10/10**。**

**✅ 与 §353 的"15/15"、§362 的"145/145"**同族（**第四次"全对"**）。

### 4.4 而**"那不是 `+` 绑定"**

**⇒ 三层**：

```text
1. 菜单放在 4-7 的连杀旁边
2. ⇒ **而连杀不是 `+` 绑定**
3. ⇒ **所以 alt-fire 也不是一个 `+` 绑定**
4. ⇒ **⇒ 它不走 usercmd 按钮**
```

**✅ 一个**从 UI 布局推导的机制结论**（不是猜测）。**

### 4.5 而 `pendingAltToggle_` 的**一次性消费**

```cpp
const auto altSlot = (size_t)playerState.clientNum;
if (altSlot < pendingAltToggle_.size() && pendingAltToggle_[altSlot]) {
    pendingAltToggle_[altSlot] = false;
    pressed = true;
    wasPressed = false;
}
```

**⇒ 四层**：

```text
1. **`pendingAltToggle_` 由 `requestAltWeaponToggle` 设置**（§349）
2. ⇒ **这里消费并清**
3. ⇒ **`pressed = true` / `wasPressed = false`**
4. ⇒ **所以每次按键恰好一个上升沿**
```

**✅ 与 §349 的 `requestAltWeaponToggle` **完全闭合 ✓**

**⇒ 而 §349 说"`= true` 而不是 `^= true`"⇒ **这与"一次性消费"配合**。**

**✅ **一个完整的两端设计。**

### 4.6 而**"一个无人值守的驱动"**

```php
// AND AN UNATTENDED DRIVER, because nobody can press a key in a
// cycle that runs with no one at the machine. A three-second square
// wave produces a switch and a switch back, which exercises the
// toggle as well as the switch. OLMOD_ALT_FORCE_TEST=1 to arm; off,
// it costs one static bool.
if (altForceTest) {
    static std::array<bool, 64> lastForced{};
    const auto wave = ((commandState.currentUserCmd.commandTime / 3000u) & 1u) != 0;
    ...
}
```

**⇒ 七层**：

```text
1. **一个无人值守的驱动**
2. ⇒ **因为在一个无人在机器旁的循环里没人能按键**
3. ⇒ **一个三秒方波产生一次切换与一次切回**
4. ⇒ **既锻炼切换也锻炼往返**
5. ⇒ **`OLMOD_ALT_FORCE_TEST=1` 武装**
6. ⇒ **关闭时它花一个 `static bool`**
7. ⇒ **`wave = (commandTime / 3000) & 1`**
```

**✅ 与 §349 的"`OLMOD_PLAYER_VOCALS=0`"**同族（**第六次环境变量旋钮**）。

**⚠ 而"关闭时花一个 `static bool`"⇒ **一个成本陈述**。**

**✅ 与 §355 的"廉价在 32 个 actor"**同族。

## 五、**交替武器的往返对（`altPair`）**（本组第四重要）

### 5.1 那段

```php
// TOGGLE. The alt links host -> alt only: the alt's own +3720
// is zero and its +12 names the BASE weapon, not the modular
// host this server published, so the way back is remembered
// rather than looked up. A plain array, not a member: adding a
// field to a struct the address-keyed native buffer contains is
// what broke the death animation twice (section 184h).
// REMEMBER BOTH ENDS, and match on the ALT. Remembering only
// the host is wrong the moment the player switches weapons
// normally while holding the alt: the pair goes stale and the
// next press hands them a weapon they are no longer near.
// Keyed on the alt, a stale pair simply does not match and the
// press resolves fresh.
static std::array<std::pair<std::uint16_t, std::uint16_t>, 64> altPair{};
...
if (slot < altPair.size() && altPair[slot].second == current && altPair[slot].first) {
    target = altPair[slot].first;   // 回宿主
    altPair[slot] = {};
    returningToHost = true;
} else {
    target = altFireResolver_(current);
    if (target && slot < altPair.size()) altPair[slot] = { current, target };
}
```

### 5.2 十三层

```text
1. **切换。alt 只链接 host → alt**
2. ⇒ **因为 alt 自己的 `+3720` 是零**
3. ⇒ **而它的 `+12` 命名【基础武器】而不是这个服务器发布的模块化宿主**
4. ⇒ **所以【回去的路被记住】而不是被查**
5. ⇒ **一个普通数组，不是一个成员**
6. ⇒ **因为向一个被按地址键的原生缓冲区包含的结构加一个字段**
7. ⇒ **正是让死亡动画坏了两次的东西（第 184h 节）**
8. ⇒ **记住【两端】，而在 alt 上匹配**
9. ⇒ **只记宿主在玩家持着 alt 时正常换枪的那一刻就错了**
10. ⇒ **那一对会变陈旧而下一次按键给他们一把不再靠近的武器**
11. ⇒ **以 alt 为键，一个陈旧的对应不匹配而那次按键【重新解析】**
12. ⇒ 所以 `altPair[slot] = {host, alt}`
13. ⇒ 而回宿主时清空
```

### 5.3 ⭐ **"向被按地址键的原生缓冲区加一个字段让死亡动画坏了两次"**

**✅ 与 §331 的"不能增长一个按地址键的缓冲区"**完全一致 ✓

**⇒ **第六次确认那个铁律。**

**⚠ 而"坏了两次"⇒ **那次事故的复发。**

**✅ 与 §350 的"`noteworthy` 用旁表"**同族（**第二次"旁表而不是扩字段"**）。

### 5.4 而**"以 alt 为键，陈旧对不匹配 ⇒ 重新解析"**

**✅ 一个**优雅的陈旧检测**。**

**⇒ 三层**：

```text
若以 host 为键：
    玩家持 alt 时换枪 ⇒ pair 陈旧 ⇒ **下一次按键给错武器**
若以 alt 为键：
    玩家换枪 ⇒ current 不再等于 alt ⇒ **pair 不匹配 ⇒ 重新解析** ✓
```

**✅ 与 §362 的"代际匹配"**同族（**第二次"用一个哨兵自动失效"**）。

### 5.5 而**"这两次都是从一手数据读出来的"**

**✅ 与 §347 的"THE TIME FIRST"**不同**。**

## 六、**`altHeldWeapon` 与 cmd 的每帧覆盖**（本组第五重要）

### 6.1 那段

```php
// SECTION 191y: CARRY THE ALT IN THE USERCMD SO RETAINED WEAPON
// TRANSITIONS SELECT THE REQUESTED ALT.
//
// out.exe **sub_424470**, reached from the pmove's weapon think, does
//
//     0x004245B4   *(_DWORD *)(ps + 0x3F8) = *(_WORD *)(pmove + 0x18)
//
// and pmove+0x18 IS cmd.weapon -- pmove_t's cmd starts at +0x04 and
// SvNativeUserCmd::weapon sits at 0x14, which this tree already pins
// with a static_assert and which sub_429E10 corroborates by reading
// cmd.lastWeaponAltModeSwitch two fields along at pmove+0x1C.
//
// CORRECTION (2026-09-06, checkpoint83): this is the finish-drop
// transition, not an unconditional write on every pmove. Both known
// callers gate it on weapon states3..5: 42B043..56 and 4260BB..DB.
```

### 6.2 十一层

```text
1. **在 usercmd 里携带 alt，所以保留的换武器选择请求的 alt**
2. ⇒ **`out.exe sub_424470`，从 pmove 的武器 think 到达，做**
     · **`0x004245B4  *(_DWORD *)(ps + 0x3F8) = *(_WORD *)(pmove + 0x18)`**
3. ⇒ **而 `pmove+0x18` 【就是】 `cmd.weapon`**
4. ⇒ **因为 `pmove_t` 的 cmd 从 `+0x04` 开始而 `SvNativeUserCmd::weapon` 坐在 `0x14`**
5. ⇒ **（`0x04 + 0x14 = 0x18`）**
6. ⇒ **而这一棵树已经用一个 `static_assert` 钉住它**
7. ⇒ **而 `sub_429E10` 佐证它，因为它读 `cmd.lastWeaponAltModeSwitch` 隔两个字段在 `pmove+0x1C`**
8. ⇒ **更正（2026-09-06，checkpoint83）：这是一个 finish-drop 转换**
9. ⇒ **不是每个 pmove 的一次无条件写**
10. ⇒ **两个已知调用方把它门控在武器状态 3..5：`42B043..56` 与 `4260BB..DB`**
11. ⇒ **而 BO1 的 `PM_Weapon_FinishWeaponChange 452B90` 有对应的控制流**
```

### 6.3 而**"371 / 374"**

```php
// The three `from=1225` lines in section191x record the observed reset.
// 371 of 374 presses read the HOST back at the top of the next think;
// the three that read the ALT are presses that landed inside the one
// frame it survived. A value that survives sometimes is not a value
// that is never written -- it is a value something else owns.
```

**⇒ 八层**：

```text
1. **section191x 里的三行 `from=1225` 记录了观察到的重置**
2. ⇒ **374 次按键里的 371 次在下一个 think 的开头读回【宿主】**
3. ⇒ **而读到 alt 的那三次是【落在它存活的那一帧之内】的按键**
4. ⇒ **一个【有时】存活的值不是一个【从不被写】的值**
5. ⇒ **它是【别的东西拥有】的值**
6. ⇒ **所以必须每帧覆盖**
```

### 6.4 ⭐ **"一个有时存活的值不是一个从不被写的值 —— 它是别的东西拥有的值"**

**✅ 这是本文件里**最精辟的一条推断**。**

**⇒ 三层**：

```text
若值"从不被写" ⇒ 它【永不】被重置
若值"有时存活" ⇒ 它【有时】被重置
⇒ **所以有另一个写者**
```

**✅ 与 §363 的"持有 `0x80000` 不重置"（因为有探针测到恰好一次）**同族（**第二次"频率证据定性质"**）。

**⚠ 而"371/374"⇒ **一个精确的比例**。**

### 6.5 而**"cmd 与 oldcmd 必须一致"**

```php
if (playerState.currentWeaponAssetIndex == altHeldWeapon[altTraceSlot]) {
    frozenCommandState.currentUserCmd.weapon = altHeldWeapon[altTraceSlot];
    // oldcmd TOO, so the pair is consistent. A cmd/oldcmd that
    // disagree every single frame is a weapon CHANGE every single
    // frame, which is the raise animation on a loop rather than a
    // gun in the player's hands.
    if (frozenCommandState.oldUserCmd)
        frozenCommandState.oldUserCmd->weapon = altHeldWeapon[altTraceSlot];
}
```

**⇒ 七层**：

```text
1. **旧 cmd 也设，所以那一对是一致的**
2. ⇒ **一个【每一帧】都不同意的 cmd/oldcmd**
3. ⇒ **就是【每一帧】一次换武器**
4. ⇒ **那是一段循环播放的举起动画**
5. ⇒ **而不是玩家手里的一把枪**
```

**✅ 与 §347 的"重复施加命令 ⇒ 动画看起来冻结"**同族（**第四次"命令不一致导致动画错"**）。

**⚠ 而"每一帧一次换武器"⇒ **一个极具体的后果**。**

### 6.6 而**"武器离开了我们的手 ⇒ 停止强制"**

```php
else {
    // The weapon left our hands some other way -- a death, a class
    // change, an ordinary switch. Stop forcing it: a stale override
    // hands the player a gun they are no longer holding, which is
    // the same failure the alt PAIR above is keyed to avoid.
    altHeldWeapon[altTraceSlot] = 0;
}
```

**⇒ 四层**：

```text
1. **武器以别的方式离开了我们的手**（死亡 / 换职业 / 普通切换）
2. ⇒ **停止强制它**
3. ⇒ **一个陈旧的覆盖给玩家一把他们不再持有的枪**
4. ⇒ **那是 alt 对上面被键控以避免的【同一个失败】**
```

**✅ 与 §370 五.4 的"以 alt 为键自动失效"**完全一致 ✓

**⇒ **第二次"陈旧检测"。**

## 七、`altTrace` 的**三帧武装**

```php
static std::array<std::uint8_t, 64> altTraceFrames{};
auto altTraceThisFrame = false;
if (altWeaponTraceEnabled && altTraceSlot < altTraceFrames.size() && altTraceFrames[altTraceSlot]) {
    altTraceThisFrame = true;
    --altTraceFrames[altTraceSlot];
}
...
if (altWeaponTraceEnabled && altTraceSlot < altTraceFrames.size()) {
    altTraceFrames[altTraceSlot] = 3;
    altTraceThisFrame = true;
}
```

### 7.1 六层

```text
1. **一个按客户端的 3 帧计数器**
2. ⇒ **每帧递减**
3. ⇒ **归零后停**
4. ⇒ **切武器时重新武装到 3**
5. ⇒ **理由**：
     · **"切武器【之后一帧】的回退与【在它之内】的回退是不同的发现"**
     · **而每帧记录会把那少数几行载着答案的行淹没**
```

**✅ 与 §355 的"前 40 帧的日志结论都作废"**同族（**第三次"日志窗口"）。**

**⚠ 而"3 帧"是一个**精确的选择**（覆盖"下一帧"的情况）。**

### 7.2 而**"锁存武装并在这里花掉"**

```php
// Latch the arming and spend it HERE, so every stage below reads one
// consistent answer and an early return cannot leave the trace stuck
// on for the rest of the match.
```

**⇒ 四层**：

```text
1. **锁存武装并【在这里】花掉**
2. ⇒ **所以下面每一个阶段读一个一致的答案**
3. ⇒ **而一个早退不能让 trace【卡在开】整个比赛**
4. ⇒ **一个精确的资源管理**
```

**✅ 与 §355 的"事务性"**第六次。

## 八、关键结论

1. **⭐ 原生 pmove 的两条换武器路径都不可达**：`sub_429E10` 的三个字段**不是 netfield**（表 `0..245` 无条目）且**镜像不写它们**；`sub_429DA0` 需要 `cursorHintEntIndex != 2047`（那是捡武器路径）。
2. **"在服务端填它们把正确的值放进正确的字段而让比赛失步，因为客户端继续对着零预测"`** —— 第二次"服务端对了而客户端不一致"。
3. **"玩家自己的武器列表 `+0x2F4` 从不被写；三个函数都有分支忽略它并扫描全局武器表；这个 build 在那个模式"`**。
4. **⭐⭐ "哪个位是交替开火键？去问键盘，不要问镜像"`**。
5. **`0x100000` 从 `sub_425440` 读出而**从未对一次按键确认** ⇒ 它是**瞄准镜** ⇒ 每次右键都重新举枪。
6. **`0x08000000` 是作者自己的，取自一个**污染过的窗口**，而**在空闲客户端上三分钟 63 次** ⇒ **根本不是按键**。
7. **⭐ "从反编译读出的常数是一个假设"`** —— 引用记忆条目 `[[a-decompiled-constant-is-a-hypothesis]]`，而**两个会话的代价**。
8. **⭐ "只从【边沿】里排除而不从掩码里隐藏 —— 这不是过滤被测量的东西，这是从触发器里移除一个已知的振荡器"`** —— 一个极精细的证据学区分。
9. **⭐ 阳性对照**：两次左键 ⇒ 恰好两个 `0x00000001` 边沿，而同一窗口五次按 `3` ⇒ **零个**。
10. **⭐⭐ 真正的触发器是可靠命令 `n 89`**（**十次按键十条命令，精确数量匹配**）。
11. **"菜单把它命名为 'Weapon Attachments' 并放在 4-7 的连杀旁边，而那些不是 `+` 绑定"`** —— 从 UI 布局推导机制。
12. **`pendingAltToggle_` 的一次性消费**与 §349 的 `= true`（非异或）**完整闭合**。
13. **`OLMOD_ALT_FORCE_TEST` 的三秒方波**（"无人值守的驱动"）—— 第六次环境变量旋钮。
14. **⭐ `altPair` 的"记住两端而以 alt 为键"`** —— 所以**陈旧对自动不匹配并重新解析**（第二次陈旧检测）。
15. **⭐ "向一个被按地址键的原生缓冲区包含的结构加一个字段正是让死亡动画坏了两次的东西"`** —— **第六次"不能增长按地址键的缓冲区"**。
16. **"alt 的 `+3720` 是零而 `+12` 命名基础武器 ⇒ 回去的路必须被记住而不是被查"`**。
17. **`sub_424470` 的 `*(ps + 0x3F8) = *(pmove + 0x18)`**，而 `pmove+0x18 = cmd.weapon`（`0x04 + 0x14`），已被 `static_assert` 钉住。
18. **⭐ 更正（2026-09-06 checkpoint83）：那是 `finish-drop` 转换而非每次 pmove 的无条件写**（两个调用方门控在武器状态 3..5）。
19. **⭐ "一个【有时】存活的值不是一个【从不被写】的值 —— 它是【别的东西拥有】的值"`** —**371/374 次按键读回宿主而只有三次落在它存活的那一帧之内**。
20. **"cmd/oldcmd 每一帧都不同意就是每一帧一次换武器 ⇒ 循环播放的举起动画"`** —— 第四次"命令不一致导致动画错"。
21. **"武器以别的方式离开我们的手 ⇒ 停止强制，因为陈旧覆盖给玩家一把不再持有的枪"`**。
22. **`altTrace` 的三帧武装** —— "切武器**之后一帧**的回退与**在它之内**的回退是不同的发现"，而**锁存并在开头花掉**。

## 九、未闭合点

- `playerState` netfield 表的 246 项完整清单。
- `SvNativeUserCmd` 的完整布局。
- `sub_424470` 的 finish-drop 转换的完整条件。
- `FactoryPowerPieces` 之外 `n 89` 的其它命令号。
- `altFireResolver_` 的实现（`weaponDefinition +3720` 链）。
- `sv_snapshot_mp.cpp` 20000 行之后未读取（27,016 行，进度 74%）。
