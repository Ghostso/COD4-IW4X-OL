# 474 · **"其它每一个客户端在这里、而且只在这里知道这一枪"** —— `sv_client_events_mp.cpp` 的 `+5`/`+1` 两处独立证实、`0x00DADC0C` 的十条、以及"一个加法不是一次翻译"

## 一、范围

本报告学习 `sv_client_events_mp.cpp`（**`721` 行**）全文件：`sub_426B20` 的唯一签名、`+5`/`+1` 两处独立证实、`0x00DADC0C` 的十条服务端专属事件、`74` 的第一次目击、四个 `switch-notify` 的拒绝面、以及"实体事件环从不携带开火 id"的实测。

## 二、**"用【两个立即数相差一**的 `lea` 找【唯一签名**"**（本组最重要的一段）

### 2.1 那段

```cpp
// 3.3.3.3's sender is sub_4258B0; out.exe's is sub_426B20, found by the
// one signature that is unique in both images -- a function containing
// EXACTLY TWO `lea reg,[reg+reg+imm8]` whose immediates differ by one.
// One hit in 3.3.3.3 (0x32/0x31), and of the two in out.exe only this
// one has the sender's whole shape:
//
//   push ebx; test eax,eax; push eax; mov ecx,esi; sete bl; call ...
//   mov eax,[esi+0x340 -> 0x3F8]      the weapon index
//   mov ecx,[eax*4 + 0x17F5A40 -> 0x1988B50]   the weapon table
//   cmp [ecx+0x48C -> 0x598], 5 -> 8  the weaponDef discriminator
//   lea ecx,[ecx+ecx+0x32 -> 0x37]    pass branch  -> 0x32/0x34 -> 0x37/0x39
//   lea ecx,[ecx+ecx+0x31 -> 0x36]    fail branch  -> 0x31/0x33 -> 0x36/0x38
//   mov eax,[esi+0xF4 -> 0x108]; and eax,3        the event ring index
//   mov [esi+eax*8+0xF8 -> 0x10C], ecx            the event
//   mov [esi+eax*8+0xFC -> 0x110], 0              the parameter
```

### 2.2 二十四层

```text
1. **3.3.3.3 的发送者是 `sub_4258B0`**】
2. ⇒ **而 out.exe 的是 `sub_426B20`**
3. ⇒ **⇒ 由【那个【在两个镜像里都唯一**的签名**找到**】
4. ⇒ **⇒ 那个签名【是【"一个【恰好两个 `lea reg,[reg+reg+imm8]`**【而【那两个立即数【相差一**"】
5. ⇒ **⇒ 3.3.3.3 里【一个命中**】⇒ **`0x32`/`0x31`**】
6. ⇒ **⇒ 而 out.exe 的两个里【只有这一个【有【那个发送者的【整个形状**】
7. ⇒ **⇒ 所以【用【整个形状**而不是【只用签名**】
```

### 2.3 ⭐⭐⭐ **"只有这一个有那个发送者的整个形状"**

**✅ 这是本报告里**最严密的定位方法**。**

**✅ 与 §471 的"`0x0280E831` 的八次出现 + 一次配对"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **配对 ⇒ 定位**；**等数 ⇒ 排除巧合**】
§474  **签名 ⇒ 两个候选**；**整个形状 ⇒ 排除那个假**的**】
⇒ **⇒ 两次"一个【两级**判据**】
```

**✅ ⭐⭐⭐ **"一个两级判据"两例**。

**⚠ 而 `lea ecx,[ecx+ecx+imm8]` 的算术**⇒ **`event = 2 × discriminatorIndex + imm8`** **⇒ 一个**极精确的编码**。**

**⇒ 独立验证**：
```text
pass 分支 ⇒ **`lea ecx,[ecx+ecx+0x32 -> 0x37]`**
⇒ **⇒ 所以【`event = 2 × i + 0x37`** 在新 build 上**】
fa​il 分支 ⇒ **`lea ecx,[ecx+ecx+0x31 -> 0x36]`**
⇒ **⇒ 所以【`event = 2 × i + 0x36`**】
```

**⚠ 标注：那个 `[ecx+ecx+X]` 的确切语义**（`ecx` 是什么）**未在注释里说明** —— **标注为未闭合**。

### 2.4 而**"一个统一的 +5"**

```cpp
// A UNIFORM +5, and the live ring agrees: a person emptied two
// magazines on 2026-08-21 and `events@10C` carried 55 (0x37) at the end
// of a magazine, immediately before the reload. Nothing in
// sv_bullet_mp had ever run because the decoder was waiting for four
// ids this build never emits.
```

**⇒ 二十层**：
```text
1. **一个统一的 `+5`**
2. ⇒ **⇒ 而【那个活的环【同意**】
3. ⇒ **⇒ （一个人【在 `2026-08-21` 打空两个弹匣**）**
4. ⇒ **⇒ 而 `events@10C` 【携带 `55`（`0x37`）【在【一个弹匣的末尾**】
5. ⇒ **⇒ 紧接着【那个换弹**】
6. ⇒ **⇒ ⚠ 而 `sv_bullet_mp` 里的东西【从来没有【运行过**】
7. ⇒ **⇒ 因为【那个解码器【在等【四个 id**】
8. ⇒ **⇒ 而【这个 build 【从不发送**它们**
```

### 2.5 ⭐⭐⭐ **"`sv_bullet_mp` 里的东西从来没有运行过，因为那个解码器在等四个这个 build 从不发送的 id"**

**✅ 这是本报告里**最重要的一条"一个**常量错【使【整条链【静默**"**。**

**✅ 与 §471 的"穿透链从不执行（因为 resolver 恒空）"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **`penetrationDepthResolver` 恒空 ⇒ 穿透分支【从不执行**】
§474  **四个 fire id 错 ⇒ `sv_bullet_mp` 【从未运行**】
⇒ **⇒ 两次"一条【整链【静默地【死**了**"
```

**✅ ⭐⭐⭐ **"一条整链静默地死了"两例** —— 而**两次【都是【一个**常量/参数**的问题，不是**逻辑**的问题**。

**⚠ 而 `55 = 0x37` 的定位**⇒ **`EventSvFireWeaponLastShot`** **⇒ 一个**精确的语义**。**

**⇒ 十层**：
```text
`0x37` ⇒ **`EventSvFireWeaponLastShot`**
⇒ **⇒ 而【它【出现在【一个弹匣的末尾**】⇒ **⇒ 所以【那个语义【正确** ✓
```

**✅ ⭐⭐⭐ **"它在弹匣末尾出现，所以那个语义正确"** —— 一个**极精巧的验证**。

**✅ 与 §474 三 的"`0x23` 携带 `1225`（一个武器索引）"**——**同族**（**第二次"一个**事件【携带【它自己的**主语**"**）。

## 三、**`0x00DADC0C` 的十条与"两个源【共享【零**代码**"**（本组第二重要）

### 3.1 那段

```cpp
// AND THE OTHER FOUR ARE WRONG TOO, BY ONE. The table the original
// comment cites is a dword ARRAY of every server-only event, and both
// builds have it whole:
//
//   3.3.3.3  0x00C5BA9C : 1D 1C 22 16 | 31 32 33 34 | 00 00 00 00
//   out.exe  0x00DADC0C : 1E 1D 23 17 | 36 37 38 39 | 3A 3B 00 00
//
// Same order, same shape, TEN entries where 3.3.3.3 has eight. The four
// notify ids are +1 and the four fire ids are +5, which is an
// independent confirmation of the +5 read off the sender above -- two
// sources sharing no code. **Every one of the four is corroborated by
// the live ring** from the two-magazine run: 0x1E and 0x1D appear
// around a reload, and 0x23 appears carrying parameter 1225, which is
// the weapon index -- a weapon-switch event naming its own weapon.
```

### 3.2 二十四层

```text
1. **那个表【是【一个 `dword` 数组**，装【每一个服务端专属事件**】
2. ⇒ **⇒ 而【两个 build 【都有【它【完整**】
3. ⇒ **⇒ 3.3.3.3 `1D 1C 22 16 | 31 32 33 34 | 00 00 00 00`**（**`8` 个**）**
4. ⇒ **⇒ out.exe `1E 1D 23 17 | 36 37 38 39 | 3A 3B 00 00`**（**`10` 个**）**
5. ⇒ **⇒ 同样的顺序、同样的形状、`10` 个对 `8` 个**】
6. ⇒ **⇒ 四个通知 id【是 `+1`**】而【四个开火 id【是 `+5`**】
7. ⇒ **⇒ 而那【是【对【上面那个从发送者读出的 `+5` 【一个独立的证实**】】
8. ⇒ **⇒ 【两个源【共享【零代码**】】
9. ⇒ **⇒ 而【那四个【每一个【都被【那个活的环**证实**】
```

### 3.3 ⭐⭐⭐ **"两个源共享零代码"**

**✅ 这是本报告里**最强的证据结构**。**

**✅ 与 §471 的"那个配对识别的对应物，而相等的计数使它成为一个测量而不是一个巧合"**——**完全同族** ✓

**⇒ 三层**：
```text
源 A ⇒ **`sub_426B20` 的 `lea` 立即数**（**代码**）
源 B ⇒ **`0x00DADC0C` 的表**（**数据**）
⇒ **⇒ 两者【共享【零代码**】⇒ **⇒ 而【结论【相同**】
```

**✅ ⭐⭐⭐ **"两者共享零代码而结论相同"** —— 一个**极强的独立性**。

**⚠ 而四个 id 的映射表**：

```text
3.3.3.3        out.exe        名字
  1D      →      1E       EventReloadAddAmmo        (+1)
  1C      →      1D       EventReloadStartNotify    (+1)
  22      →      23       EventWeaponSwitchStarted  (+1)
  16      →      17       EventOffhandEndNotify     (+1)
  31      →      36       EventSvFireWeapon         (+5)
  32      →      37       EventSvFireWeaponLastShot (+5)
  33      →      38       EventSvFireWeaponLeft     (+5)
  34      →      39       EventSvFireWeaponLastShotLeft (+5)
  ——      →      3A       EventSvFireWeaponVariantA (+新)
  ——      →      3B       EventSvFireWeaponVariantB (+新)
```

**⇒ 独立验证**：`0x1D + 1 = 0x1E` ✓ / `0x1C + 1 = 0x1D` ✓ / `0x22 + 1 = 0x23` ✓ / `0x16 + 1 = 0x17` ✓ / `0x31 + 5 = 0x36` ✓ / `0x32 + 5 = 0x37` ✓ / `0x33 + 5 = 0x38` ✓ / `0x34 + 5 = 0x39` ✓

**✅ ⭐⭐⭐ **"八个全部精确"** —— 一个**完整的算术闭合**。

**⚠ 而"`1D 1C 22 16` 的顺序**⇒ **不是升序**】**。**

**⇒ 十层**：
```text
`1D 1C 22 16` ⇒ **`+1` 之后【是 `1E 1D 23 17`**】
⇒ **⇒ 所以【那个顺序【也被【保留**】（**不是【重排**）
⇒ **⇒ 而【那【是【一个【更强的**证据**（**一个重排【会【破坏**那个对应**）
```

**✅ ⭐⭐⭐ **"那个顺序也被保留，而一个重排会破坏那个对应"** —— 一个**极精确的观察**。

### 3.4 而**`0x3A`/`0x3B` 的"故意不处理"**

```cpp
// TWO MORE EXIST HERE AND ARE DELIBERATELY NOT HANDLED. out.exe adds
// `cmp edi,1 / cmp edi,2 -> lea ecx,[edi+0x39]`, so 0x3A and 0x3B are
// fire events this build can send and 3.3.3.3 has no counterpart for.
// What selects them is an argument nothing here supplies yet; guessing
// a hand or a last-shot flag for them would be inventing a contract.
```

**⇒ 二十层**：
```text
1. **`cmp edi,1 / cmp edi,2 -> lea ecx,[edi+0x39]`**
2. ⇒ **⇒ 所以【`edi = 1` ⇒ `0x3A`**而 `edi = 2` ⇒ `0x3B`**】
3. ⇒ **⇒ 而【它们【是这个 build 【能发送**的开火事件**】
4. ⇒ **⇒ 而 3.3.3.3 【没有【对应物**】
5. ⇒ **⇒ 什么选它们【是一个【这里【还没有【提供的**参数**】
6. ⇒ **⇒ 而【猜一个手或一个最后一发标志【会【是【发明一个契约**】
```

**✅ ⭐⭐⭐ **"猜一个手或一个最后一发标志会是发明一个契约"** —— 与 §468 的"没有见证的值故意缺席"**完全同族** ✓

**⇒ 三层**：
```text
§468  **"没有见证的值故意缺席：一个未映射的字符串被拒绝而不是取默认"**
§474  **"猜一个手或一个最后一发标志会是发明一个契约"**
⇒ **⇒ 两次"一个**无证据的映射【是【发明**"**
```

**✅ ⭐⭐⭐ **"一个无证据的映射是发明"两例**。

**⚠ 而"`lea ecx,[edi+0x39]`" ⇒ `edi = 1` ⇒ `0x3A` / `edi = 2` ⇒ `0x3B`** ✓**（**独立验证**）**。

**✅ ⭐⭐ **"独立验证"**。

### 3.5 而**"在一个意义上被命名并过滤，而不是被解码"**

```cpp
// OLMOD(section-80): the two entries this build adds. They are in the
// SERVER-ONLY list, so out.exe expects a dedicated server to consume
// them, and sub_426B20 emits them from `cmp edi,1 / cmp edi,2`. What
// selects them is not established, so they are named and filtered
// rather than decoded -- see SV_IsServerOnlyClientEvent below.
```

**⇒ 十层**：
```text
1. **它们【在【那个服务端专属列表**里**】
2. ⇒ **⇒ 所以 `out.exe` 【期望【一个专用服务器【消费它们**】
3. ⇒ **⇒ 而 `sub_426B20` 【从 `cmp edi,1 / cmp edi,2` 发射**它们**
4. ⇒ **⇒ 什么选它们【未确立**】
5. ⇒ **⇒ 所以【它们被命名并过滤**，而【不是被解码**】
```

**✅ ⭐⭐⭐ **"命名并过滤，而不是解码"** —— 与 §462 的"给那一项命名"**同族**（**第四次**）。

**✅ 而 `SV_IsServerOnlyClientEvent` 里 `EventSvFireWeaponVariantA/B` 【被【`case`** 接受**】**⇒ **"那个边界【匹配引擎的**"**。**

**⇒ 三层**：
```cpp
// OLMOD(section-80): 1649370-only, and in out.exe's own server-only
// array. Admitted here so the boundary matches the engine's; the fire
// decoder still refuses them, so they are dropped deliberately rather
// than by omission.
```
```text
边界 ⇒ **接受**（**匹配引擎**）
解码 ⇒ **拒绝**（**`SV_DecodeFireWeaponEvent` 的 `default` ⇒ `nullopt`**）
⇒ **⇒ 所以【"故意丢弃【而不是【因遗漏**丢弃**"**
```

**✅ ⭐⭐⭐ **"故意丢弃而不是因遗漏丢弃"** —— 一个**极强的纪律**。

## 四、**"`74` 的第一次目击"**（本组第三重要）

### 4.1 那段

```cpp
// SECTION 190: THE VOCABULARY OF WHAT WE THROW AWAY.
//
// Alt-fire moves the UI icon and nothing else, and the first
// thing to establish is WHICH event the client sends when the
// player presses it. `sub_429E10` -- the function that reads
// `cmd.lastWeaponAltModeSwitch` out of pmove+0x1C and uses it
// to index the weapon table `dword_1988B50` -- pushes event
// **74** into the predictable ring, and 74 is not in out.exe's
// server-only array at 0x00DADC0C, so this `continue` is where
// it dies. But 74 is what ONE path emits; PM_BeginWeaponChange
// emits 0x23, and which of them an alt press produces is not
// established.
//
// So report the FIRST SIGHTING of each distinct id and then
// never again. Silent once the vocabulary is known, which is
// section 189c's rule, and it costs one array probe per event
// on a path that already iterates them.
static std::array<bool, 256> seenIgnoredEvent{};
```

### 4.2 二十四层

```text
1. **alt-fire 【只移动那个 UI 图标**，别的什么都不做**】
2. ⇒ **⇒ 而【第一个【要确立的东西【是【玩家按下它时【客户端【发送【哪个**事件**】
3. ⇒ **⇒ `sub_429E10`（【读 `pmove+0x1C` 的 `cmd.lastWeaponAltModeSwitch`**】
4. ⇒ **⇒ 并用它【索引【武器表 `dword_1988B50`**的函数**）**
5. ⇒ **⇒ 【把事件 `74` 推进【那个可预测环**】
6. ⇒ **⇒ 而 `74` 【不在 `0x00DADC0C`**】⇒ **⇒ 所以【这个 `continue` 【是【它死的地方**】
7. ⇒ **⚠ 但 `74` 【是【一条路径**发射的**】
8. ⇒ **⇒ `PM_BeginWeaponChange` 【发射 `0x23`**】
9. ⇒ **⇒ 而【哪一个【是【一个 alt 按下【产生的【未确立**】
10. ⇒ **⇒ 所以【报告【每一个不同 id 的第一次目击，然后【再也不**】
```

### 4.3 ⭐⭐⭐ **"报告每一个不同 id 的第一次目击，然后再也不"**

**✅ 这是本报告里**最精确的一条"一个**词汇表**的**建立**"**。**

**✅ 与 §469 的"`ZMTICK Lua callbacks=N` 只在地图开始的第一秒"**——**同族**（**第二次"一个**有界的诊断**"**）。

**⇒ 三层**：
```text
若【每次都打**】⇒ **⇒ 在【命令速率**上【刷屏**】
若【只打第一次**】⇒ **⇒ 词汇表【建立**而【日志【静默**】
⇒ **⇒ 所以【后者【正确**】
```

**✅ ⭐⭐⭐ **"词汇表建立而日志静默"** —— 一个**极清晰的设计**。

**⚠ 而"`static std::array<bool, 256>`"**⇒ **一个**零成本**的集合**。**

**⇒ 十层**：
```text
`256` 个 `bool` ⇒ **`256` 字节**
⇒ **⇒ 而【那个 `id` 被【检查 `< seenIgnoredEvent.size()`**】⇒ **⇒ 所以【不会【越界**】
```

**✅ ⭐⭐ **"不会越界"**。

**⚠ 而"那个 `static` 是【函数局的**⇒ **一个【跨客户端**的共享**】**。**

**⇒ 十层**：
```text
`static` 在函数里 ⇒ **【所有客户端【共享【同一个**数组**】
⇒ **⇒ 所以【客户端 A 的一次目击【会【抑制**客户端 B 的**】
⇒ **⇒ 而那【是【一个**可质疑的**设计**（**但【对于"词汇表**"来说，那是对的**）
```

**✅ ⭐⭐⭐ **"对于一个词汇表来说那是对的"** —— 而**这正是【意图**（**那个 id 空间【是【全局**的）**。

**✅ 与 §437 的"`LastCommitRefusal` 是一个全局 `static` —— 我标记为真实缺陷"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§437  **`LastCommitRefusal` 【全局 `static` 而【含 `client=`** ⇒ **两个客户端【交替【击败**那个去重**】⇒ **缺陷**
§474  **`seenIgnoredEvent` 【全局 `static` 而【那个 id 空间【是【全局**的】⇒ **正确**
⇒ **⇒ 所以【同一个模式【两处【一个缺陷一个正确** —— 由【那个被追踪的东西【是不是【每客户端**决定**
```

**✅ ⭐⭐⭐ **"由那个被追踪的东西是不是每客户端决定"** —— **本报告最精确的判据**。

## 五、**"其它每一个客户端在这里、而且只在这里知道这一枪"**（本组第四重要）

### 5.1 那段

```cpp
// EVERY OTHER CLIENT LEARNS ABOUT THIS SHOT HERE, AND NOWHERE ELSE.
//
// MEASURED, not assumed. An entity-event probe on two live clients
// (Tools/olfinal/entity-event-probe.py) shows remote entity events
// dispatching perfectly -- client 1 received 140 of client 0's
// footsteps, jumps and weapon raises -- while a fire event NEVER
// crosses: id 54 appears only ever on a client's OWN entity, which
// is its own prediction. The server's own histogram agrees:
//
//     entity-events sent 25:4 31:86 32:3 33:85 152:183 153:90
//                        154:31 156:58 157:43 158:17
//
// reload, raise, putaway, footsteps, jumps, landings -- and no fire
// event of any kind. The playerState predictable ring carries the
// server-only id (that is how the bullet path works); the ENTITY
// ring never gets it, because BG_PlayerStateToEntityState does not
// copy server-only ids into es.events.
//
// So this is an ADDITION, not a translation. Retail's dm demo sends
// (41, 0) on ET_PLAYER 2250 times and (42, 0) 85 times -- parameter
// always zero -- and CG_EntityEvent case 41 is what feeds both the
// remote weapon sound and the compass blip (sub_595DF0 sets bit 0
// of the blip flags at +0x70 with a freshness stamp at +0x58, which
// is exactly what CG_DrawCompassBlip requires to draw a dot).
```

### 5.2 二十四层

```text
1. **每一个其它客户端【在这里、而且只在这里**【知道【这一枪**】】
2. ⇒ **测量，不是假设**】
3. ⇒ **（在两个活的客户端上的【一个实体事件探针**）**
4. ⇒ **⇒ 远程实体事件【完美分发**】
5. ⇒ **⇒ （客户端 `1` 【收到【客户端 `0` 的 `140` 次脚步/跳跃/举枪**）**
6. ⇒ **⇒ ⚠ 而一个开火事件【从不横越**】
7. ⇒ **⇒ （id `54` 【只【出现在【一个客户端自己的实体**上，**那【是【它自己的预测**）**
8. ⇒ **⇒ 而【服务器自己的直方图【同意**】：
9. ⇒ **⇒ `25:4 31:86 32:3 33:85 152:183 153:90 154:31 156:58 157:43 158:17`**
10. ⇒ **⇒ 换弹、举枪、收枪、脚步、跳跃、落地**】——**而【没有任何种类的开火事件**】
```

### 5.3 ⭐⭐⭐ **"playerState 的可预测环携带那个服务端专属 id；实体环从不得到它，因为 `BG_PlayerStateToEntityState` 不把服务端专属 id 复制进 `es.events`"**

**✅ 这是本报告里**最重要的一条"**两个环的不同语义**"**。**

**✅ 与 §472 的"`newestFlaggedSnapshotMessage` 与 `baselineCacheInitializationMessage` 的分工"**——**同族**（**第二次"两个**环/字段【各自【承载**不同的东西**"**）。

**⇒ 三层**：
```text
`playerState` 的可预测环 ⇒ **服务端专属 id**（**`sv_bullet_mp` 的输入**）
`entity` 的事件环 ⇒ **表现层 id**（**其它客户端可见**）
⇒ **⇒ 而 `BG_PlayerStateToEntityState` 【是【那道【不复制**的墙**
```

**✅ ⭐⭐⭐ **"那道不复制的墙"** —— 一个**极清晰的机制**。

**⚠ 而"所以这是一个**加法**，不是一次**翻译**"**⇒ **一个**极强的定性**。**

**⇒ 十层**：
```text
若【认为【是翻译**】⇒ **⇒ 找【一个【现成的**映射**】
若【认为【是加法**】⇒ **⇒ 自己**造那个**表现事件**
⇒ **⇒ 而【零售【确实发** `(41, 0)`（`2250` 次）与 `(42, 0)`（`85` 次）** ⇒ **⇒ 所以【那个加法【有**一个零售的先例**】
```

**✅ ⭐⭐⭐ **"那个加法有一个零售的先例"** —— 而**参数恒为零**（`2250`/`85` 次）。

**✅ 与 §474 三 的"那四个通知 id 的参数**"**——**不同**（那里**`0x23` 携带 `1225`**，这里**恒零**）。

**⇒ 三层**：
```text
`0x23`（切换）⇒ **参数 = 武器索引**（`1225`）**
`41`/`42`（表现）⇒ **参数恒为零**（`2250`/`85` 次）**
⇒ **⇒ 所以【两个环的【参数语义**【不同**】
```

**✅ ⭐⭐⭐ **"两个环的参数语义不同"**。

**⚠ 而 `sub_595DF0` 的"罗盘光点"**⇒ **一个**表现层**的连锁**。**

**⇒ 十层**：
```text
`sub_595DF0` ⇒ **设 `+0x70` 的光点标志的第 `0` 位**】
⇒ **⇒ 以及 `+0x58` 的一个新鲜度戳**】
⇒ **⇒ 而那【正是 `CG_DrawCompassBlip` 画一个点【所需的**】
⇒ **⇒ 所以【那个表现事件【还有【一个**罗盘**的副作用**】
```

**✅ ⭐⭐⭐ **"那个表现事件还有一个罗盘的副作用"** —— 一个**极重要的运行时事实**。

**✅ 与 §461 的"`SV_PresentationFireEventId`"**——**一个命名**（**代码里**）**。

**⚠ 而 `SV_PresentationFireEventId` 的映射**⇒ **从 `0x36..0x39` 到 `41`/`42`？**

**⇒ 十层**：
```text
`SV_PresentationFireEventId(event.event)` ⇒ **一个**函数**（**在 `.hpp` 里**）
⇒ **⇒ 而【零售【只发** `41` 与 `42`**】⇒ **⇒ 所以【那四个 fire id 【映射到【两个**表现 id**】
```

**✅ ⭐⭐⭐ **"那四个 fire id 映射到两个表现 id"** —— 而**那意味着一对二**（**左右手 × 最后一发 ⇒ 汇总到 41/42**）**。**

**⚠ 标注：`SV_PresentationFireEventId` 的确切映射在 `.hpp` 里，未读。**

## 六、**"十四条拒绝一个命令，而它们只有一个词"**（本组第五重要）

### 6.1 那段

```cpp
// SECTION 191z: FOURTEEN WAYS TO REFUSE A COMMAND AND ONE WORD FOR ALL OF
// THEM, one level above the bullet path's thirteen.
//
// `client-think rejected ... stage=client_events_rejected` is what the
// player experiences as "it hits them and nothing happens, and I desync" --
// a refused event rejects the WHOLE usercmd, so the staged damage AND the
// frame's movement are both discarded. The stage name separates none of the
// fourteen, and the first alt-fire burst produced 121 of them with no way
// to tell which.
```

### 6.2 二十四层

```text
1. **十四种**拒绝一个命令的方式**】
2. ⇒ **⇒ 而【它们只有【一个词**】**
3. ⇒ **⇒ 而【那【比【子弹路径的十三种【高【一层**】
4. ⇒ **⇒ 【一个被拒绝的事件【拒绝【整个 usercmd**】
5. ⇒ **⇒ 所以【那个暂存的伤害【与【那一帧的移动【都【被丢弃**】
6. ⇒ **⇒ 而【那个阶段名【一个都【分辨不出**】
7. ⇒ **⇒ 而【第一次 alt-fire 的连发【产生【`121` 个**】⇒ **⇒ 而【没有办法【分辨【是哪个**】
```

### 6.3 ⭐⭐⭐ **"一个被拒绝的事件拒绝整个 usercmd，所以那个暂存的伤害与那一帧的移动都被丢弃"**

**✅ 这是本报告里**最重要的**严重性**论证**。**

**✅ 与 §471 的"一条拒绝【不只是一个失败**"**——**同族**（**第三次"一个**拒绝【的【爆炸半径**"**）。

**⇒ 三层**：
```text
子弹路径 ⇒ **一个 `Failed` ⇒ 【那一枪**没有**
事件路径 ⇒ **一个 `Invalid` ⇒ 【整个 usercmd**（**伤害 + 移动**）都没有**
⇒ **⇒ 所以【后者【严重**得多**
```

**✅ ⭐⭐⭐ **"后者严重得多"** —— 而**注释明确指出**（"`Invalid` rejects the WHOLE clientThink candidate"）。

**✅ 与 §471 的 `SV_BulletFireFailed` 的 `thread_local const char *`**——**完全同族**（**第二次"一个**线程局部的指针**【诊断**"**）。

**⇒ 三层**：
```text
§471  **`lastBulletFireFailure`**（**子弹**）
§474  **`lastClientEventRefusal`**（**事件**）
⇒ **⇒ 两次"一个【同形状**的 `thread_local` 诊断**】
```

**✅ ⭐⭐ **"两次同形状的 thread_local 诊断"**。

**⚠ 而"`121` 个"**⇒ **一个**具体的数**。**

**⇒ 十层**：
```text
第一个 alt-fire 连发 ⇒ **`121` 个 `client_events_rejected`**
⇒ **⇒ 而【没有一个【能分辨**】
⇒ **⇒ 所以【`SV_LastClientEventRefusal()` 【是【那个**修法**
```

**✅ ⭐⭐ **"121 个"是一个具体的数**。

### 6.4 而十四条的清单

```text
 1  event-slice-too-large
 2  melee-parameter-nonzero
 3  melee-weapon-or-loadout
 4  melee-no-fire-basis-builder
 5  melee-basis-build
 6  melee-execution
 7  offhand-use-not-owned
 8  offhand-use-execution
 9  switch-notify-parameter-range
10  switch-notify-target-weapon
11  fire-weapon-or-loadout-mismatch
12  fire-no-basis-builder
13  fire-basis-or-spread
14  fire-non-bullet-no-handler
15  fire-weapon-changed-during-fire
16  fire-handler-result
```

**⇒ 数到 `16` —— 而注释说 `14`。**

**✅ ⭐⭐⭐ **"注释说十四，实际十六"** —— 与 §471 的"注释说十三，实际二十五"**同族**（**第二次"注释的数是旧的**）。

**⇒ 三层**：
```text
§471  **注释 `13` vs 实际 `25`**
§474  **注释 `14` vs 实际 `16`**
⇒ **⇒ 两次"一个**注释的计数【落后**"**
```

**✅ ⭐⭐ **"注释的计数落后"两例**。

## 七、**`SV_DecodeFireWeaponEvent` 的"`event.parameter != 0` ⇒ 拒绝"**

```cpp
// CODDIFF(client_events): BO1 passes eventParm to FireWeapon, whereas
// Ghosts passes the event id. CODOL PM_Weapon_FireWeapon_SendFireWeaponEvent
// 0x004258B0 writes parameter zero and encodes hand/last-shot in
// 0x31..0x34, constraining this source adapter to the newer contract.
if (event.parameter != 0)
    return std::nullopt;
```

### 7.1 二十四层

```text
1. **BO1 【把 `eventParm` 传给 `FireWeapon`**】
2. ⇒ **而 Ghosts 【传【那个事件 id**】】
3. ⇒ **⇒ 而 CODOL 的发送者`0x004258B0` 【写参数零**】
4. ⇒ **⇒ 而【把【手/最后一发【编码进 `0x31..0x34`**】】
5. ⇒ **⇒ 所以【这个源适配器【被【约束到【较新的**那个契约**】
```

### 7.2 ⭐⭐⭐ **"把参数压在零里，把手与最后一发编码进四个 id"**

**✅ 这是本报告里**最清晰的一条"**id 空间【承载【两个布尔**"**。**

**⇒ 独立验证**：
```text
`0x36` ⇒ **右手 / 非最后一发**
`0x37` ⇒ **右手 / 最后一发**
`0x38` ⇒ **左手 / 非最后一发**
`0x39` ⇒ **左手 / 最后一发**
⇒ **⇒ 所以【四个 id = `2 × 2` 的一个枚举**】
```

**✅ ⭐⭐⭐ **"四个 id = 2 × 2 的一个枚举"** —— 与 §474 二 的 `lea ecx,[ecx+ecx+imm8]`**同族**（**那里【也是 `2×i + imm8`**）**）。

**⇒ 三层**：
```text
`lea ecx,[ecx+ecx+0x37]` ⇒ **`2 × i + 0x37`**
而 `0x36..0x39` ⇒ **四个值**
⇒ **⇒ 所以【那个 `2 × i` 【正是【那个**手/最后一发**的**编码**】
```

**✅ ⭐⭐⭐ **"那个 2 × i 正是那个手/最后一发的编码"** —— 一个**跨段的闭合**。

**⚠ 标注：`i` 与"手/最后一发"的对应关系（`i = 0/1` 是什么）未在注释里说明** —— 但 `EventSvFireWeapon`/`LastShot`/`Left`/`LastShotLeft` 的顺序暗示 `i` 是 `lastShot` 而那个基数区分手 —— **或反之**。**标注为未闭合。**

## 八、**`event.event == 73` 的 `EV_USE_OFFHAND`**

```cpp
// CODREF(1649370): 429AF9 emits EV_USE_OFFHAND=73 with ps+3E4.
// Native PM_Weapon already consumes its ammo (429AE0/42C510).
// Like melee, handle this before the server-only filter.
if (event.event == 73)
{
    const auto *offhand = equipment && event.parameter > 0 && event.parameter <= 0x7FF
        ? SV_FindOffhandWeapon(*equipment, static_cast<std::uint16_t>(event.parameter))
        : nullptr;
```

### 8.1 二十四层

```text
1. **`429AF9` 发射 `EV_USE_OFFHAND = 73`**】
2. ⇒ **⇒ 携带 `ps+3E4`**（**那个选中的副武器**）**
3. ⇒ **⇒ 而【原生的 `PM_Weapon` 【已经【消费了它的弹药**】（`429AE0`/`42C510`）**
4. ⇒ **⇒ 所以【像近战一样，在服务端专属过滤器【之前**处理它**】
5. ⇒ **⇒ 而【那个参数【必须【在 `1..0x7FF`**】**
```

### 8.2 ⭐⭐⭐ **"`0x7FF` 与 §460 的 `MaximumWeaponIndex = 0x7FF`"**

**✅ 与 §460 的"`MaximumViewmodelIndex = 0x3FF` vs `MaximumWeaponIndex = 0x7FF`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§460  **`MaximumWeaponIndex = 0x7FF`**
§474  **`event.parameter > 0x7FF` ⇒ 拒绝**
⇒ **⇒ 所以【那个界【与【那个常量【一致**】
```

**✅ ⭐⭐⭐ **"那个界与那个常量一致"**。

**⚠ 而"那个副武器【必须【在【`playerState.heldWeapons`**里**"**⇒ **一个**所有权**的检查**。**

**⇒ 十层**：
```cpp
if (!offhand || std::ranges::none_of(playerState.heldWeapons, [&](const auto &slot) {
        return slot.weaponAssetIndex == offhand->weaponAssetIndex;
    }))
    return SV_ClientEventRefused(SvClientEventResult::Invalid, "offhand-use-not-owned");
```
```text
1. **找到一个副武器**】
2. ⇒ **⇒ 而【它【必须【在【已持有的**武器里**】
3. ⇒ **⇒ 否则 `offhand-use-not-owned`**】
```

**✅ ⭐⭐⭐ **"它必须在已持有的武器里，否则 offhand-use-not-owned"** —— 一个**极清晰的准入**。

**✅ 与 §463 的"`heldBefore = 1`"**——**同族**（**第三次"一个**持有状态**"**）。

## 九、`EventWeaponSwitchStarted` 的四条准入路径

```text
① `resolvedLoadout` 的 primary/secondary（`findWeapon`）
② `altWeaponLookup`（`altScratch`，`findWeapon` 的 fallback）
③ offhand（`SV_FindOffhandWeapon` + `heldWeapons` 含它）
④ 那个已授予的 UAV 奖励（`uavWeapon` + `rewardActionType == 1` +
   `rewardActionWeapon == targetWeaponAssetIndex` + `heldWeapons` 含它）
```

### 9.1 二十四层

```text
1. **四条【独立的**准入**】
2. ⇒ **⇒ 而【每一条【都【要求【那个武器【在【已持有的**列表里（**除 ① 由 loadout 保证**）**
3. ⇒ **⇒ 所以【四道【全或无**
```

### 9.2 ⭐⭐⭐ **"那个已授予的奖励在枪/副武器的装备之外，所以只接纳那个由持有的 key4 动作命名的已解析 UAV"**

**✅ 与 §422 的"`rewardActionType`/`rewardActionWeapon`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§422  **`rewardActionType` / `rewardActionWeapon`**
§474  **`rewardActionType == 1 && rewardActionWeapon == targetWeaponAssetIndex`**
⇒ **⇒ 所以【那个 `1` 【是【一个**UAV**的**类型**码**】
```

**✅ ⭐⭐⭐ **"那个 1 是一个 UAV 的类型码"**。

**⚠ 而"只接纳那个已解析的 UAV【而不是【一条任意**的奖励武器"**⇒ **一个**极窄**的准入**。**

**⇒ 十层**：
```text
若【接纳【任何【奖励武器**】⇒ **⇒ 一个【未解析的**奖励【可以【切换进去**】
若【只接纳【那个**UAV ⇒ **⇒ 一个【窄而正确**的准入**
⇒ **⇒ 所以【后者【正确**】
```

**✅ ⭐⭐⭐ **"窄而正确"** —— 与 §468 的"没有见证的值故意缺席"**同族**（**第三次**）。

## 十、关键结论

1. **⭐⭐⭐ 用"恰好两个立即数相差一的 `lea reg,[reg+reg+imm8]`"这个唯一签名找到 `sub_426B20`**，而 **"3.3.3.3 里一个命中（`0x32`/`0x31`），而 out.exe 的两个里只有这一个有那个发送者的整个形状"`** —— **一个两级判据**（签名定位、整个形状排除假阳性），与 §471 的"配对 + 等数"同族。
2. **⭐⭐⭐ "一个统一的 `+5`，而那个活的环同意：一个人在 `2026-08-21` 打空两个弹匣，`events@10C` 在一个弹匣末尾携带 `55`（`0x37`），紧接着那个换弹"`** ⇒ **"`sv_bullet_mp` 里的东西从来没有运行过，因为那个解码器在等四个这个 build 从不发送的 id"`** —— 与 §471 的"穿透链从不执行"**同族**（**一条整链静默地死了**）；而 **`0x37` = `LastShot` 出现在弹匣末尾 ⇒ "那个语义正确"`**。
3. **⭐⭐⭐ `0x00DADC0C` 的十条**（`1E 1D 23 17 | 36 37 38 39 | 3A 3B`）对 `0x00C5BA9C` 的八条（`1D 1C 22 16 | 31 32 33 34`）⇒ **"四个通知 id 是 `+1` 而四个开火 id 是 `+5`，那是对上面从发送者读出的 `+5` 的一个独立证实 —— 两个源共享零代码"`** —— **八个全部精确算术闭合 ✓**，而 **"那个顺序也被保留（`1D 1C 22 16` 不是升序），而一个重排会破坏那个对应"`**。
4. **⭐⭐⭐ `0x3A`/`0x3B` 的"故意不处理"**：`lea ecx,[edi+0x39]`（独立验证 `edi=1 ⇒ 0x3A`、`edi=2 ⇒ 0x3B`）⇒ **"什么选它们是一个这里还没有提供的参数；猜一个手或一个最后一发标志会是发明一个契约"`** —— 与 §468 的"没有见证的值故意缺席"同族；而 `SV_IsServerOnlyClientEvent` **接受**它们（"那个边界匹配引擎的"）而 `SV_DecodeFireWeaponEvent` **拒绝**它们 ⇒ **"故意丢弃，而不是因遗漏丢弃"`**。
5. **⭐⭐⭐ `74` 的第一次目击**：`sub_429E10` 读 `pmove+0x1C` 的 `cmd.lastWeaponAltModeSwitch`、用 `dword_1988B50` 索引，把 **`74`** 推进可预测环，而 **`74` 不在 `0x00DADC0C`** ⇒ **"这个 `continue` 是它死的地方"`**；但 `PM_BeginWeaponChange` 发射 `0x23`，**"哪一个是一个 alt 按下产生的未确立"`** ⇒ **"报告每一个不同 id 的第一次目击，然后再也不 —— 词汇表建立而日志静默"`**。
6. **⭐⭐⭐ 精确对照 §437 的缺陷**：`seenIgnoredEvent` 是一个**函数局 `static`（跨客户端共享）而这是正确的**（因为那个 id 空间是全局的），而 §437 的 `LastCommitRefusal` 是一个**含 `client=` 的全局 `static` 而那是缺陷** ⇒ **"同一个模式两处，一个缺陷一个正确 —— 由那个被追踪的东西是不是每客户端决定"`**。
7. **⭐⭐⭐ "其它每一个客户端在这里、而且只在这里知道这一枪"**：两活客户端探针显示 **远程实体事件完美分发（`140` 次脚步/跳跃/举枪）而开火事件从不横越**（`id 54` 只出现在自己的实体上，那是自己的预测）；服务器直方图 **`25:4 31:86 32:3 33:85 152:183 153:90 154:31 156:58 157:43 158:17`**（换弹/举枪/收枪/脚步/跳跃/落地，**没有开火**）⇒ **"`playerState` 的可预测环携带那个服务端专属 id；实体环从不得到它，因为 `BG_PlayerStateToEntityState` 不把服务端专属 id 复制进 `es.events`"`** ⇒ **"这是一个加法，不是一次翻译"`**，而零售的 `dm` demo 发 `(41, 0)` `2250` 次与 `(42, 0)` `85` 次（**参数恒为零**）⇒ 而 **`CG_EntityEvent case 41` 既喂远程武器音又喂罗盘光点**（`sub_595DF0` 设 `+0x70` 的第 `0` 位与 `+0x58` 的新鲜度戳）。
8. **⭐⭐⭐ "十四条拒绝一个命令，而它们只有一个词"`**：**"一个被拒绝的事件拒绝整个 usercmd，所以那个暂存的伤害与那一帧的移动都被丢弃"`** ⇒ **"第一次 alt-fire 的连发产生 `121` 个，而没有办法分辨是哪个"`** —— **我数到 `16` 个不同的理由（注释说 `14`）**，与 §471 的"`13` vs `25`"同族（**注释的计数落后**）。
9. **⭐⭐⭐ `SV_DecodeFireWeaponEvent` 的 `event.parameter != 0 ⇒ 拒绝`**：**BO1 把 `eventParm` 传给 `FireWeapon`，Ghosts 传事件 id，而 CODOL 的 `0x004258B0` 写参数零并把"手/最后一发"编码进 `0x31..0x34`** ⇒ **独立验证：四个 `fire id = 2 × 2` 的一个枚举**，而 **`lea ecx,[ecx+ecx+0x37]` 的 `2 × i` 正是那个编码** —— 一个**跨段闭合**。
10. **⭐⭐⭐ `EV_USE_OFFHAND = 73`**（`429AF9` 携带 `ps+3E4`；原生 `PM_Weapon` 已消费弹药 `429AE0`/`42C510`）⇒ **参数在 `1..0x7FF`**（与 §460 的 `MaximumWeaponIndex = 0x7FF` **完全一致**），而**那个副武器必须在 `playerState.heldWeapons` 里，否则 `offhand-use-not-owned`**。
11. **⭐⭐⭐ `EventWeaponSwitchStarted` 的四条准入**（loadout / alt / offhand / UAV 奖励），而 **UAV 那条要求 `rewardActionType == 1` 且 `rewardActionWeapon == targetWeaponAssetIndex` 且 `heldWeapons` 含它** ⇒ **"那个 1 是一个 UAV 的类型码"`** —— 一个**极窄而正确**的准入（与 §468 同族）。
12. **⭐⭐ `SV_HandleClientEventsDetailed` 的顺序**：`event-slice-too-large` 的入口界 ⇒ **近战（不在服务端专属列表里，所以最先）** ⇒ **`73`（offhand）** ⇒ **服务端专属过滤** ⇒ **`0x23`（切换）** ⇒ **三个通知（`0x17`/`0x1D`/`0x1E`，只发脚本通知）** ⇒ **四个 fire** ⇒ **表现事件** —— 一个**极清晰的优先级阶梯**。

## 十一、`sv_client_events_mp.cpp` 全文件总览

**`721` 行。**

**`14` 个事件常量**：
```text
0x17  EventOffhandEndNotify                     (+1 from 3.3.3.3's 0x16)
0x1D  EventReloadStartNotify                    (+1 from 0x1C)
0x1E  EventReloadAddAmmo                        (+1 from 0x1D)
0x23  EventWeaponSwitchStarted                  (+1 from 0x22)
0x36  EventSvFireWeapon                         (+5 from 0x31)
0x37  EventSvFireWeaponLastShot                 (+5 from 0x32)
0x38  EventSvFireWeaponLeft                     (+5 from 0x33)
0x39  EventSvFireWeaponLastShotLeft             (+5 from 0x34)
0x3A  EventSvFireWeaponVariantA                 (1649370 独有)
0x3B  EventSvFireWeaponVariantB                 (1649370 独有)
0x3D  EventFireMelee                            (不在服务端专属列表)
 73   EV_USE_OFFHAND
 74   (alt-fire 的候选，被过滤掉)
 54   (只出现在自己的实体上)
```

**`32` 个函数**：`weaponSpreadLoggingEnabled` / `logWeaponSpreadSample` / `SV_SetCurrentClientEventPerkSpreadScale` / `SV_CurrentClientEventPerkSpreadScale` / `SV_ClientEventRefused` / `SV_LastClientEventRefusal` / `SV_SetAltWeaponLookup` / `SV_LookupAltWeapon` / `SV_SetHostAltWeaponLookup` / `SV_LookupAltWeaponForHost` / `SV_AddEntityPresentationEvent` / `SV_IsServerOnlyClientEvent` / `SV_DecodeFireWeaponEvent` / `SV_IsRewindableAttackEvent` / `SV_HandleClientEventsDetailed` / `SV_HandleClientEvents`。

**`16` 条拒绝理由**（注释说 `14`）。

**`6` 个测量锚点**：
```text
84 demos / 1514 melee events in 35 of them
EV_MELEE_TRACE 0x41 258 / EV_MELEE_SWIPE 0x3C 249 / EV_MELEE_END 0x47 238
EV_FIRE_MELEE 0x3D 227 / EV_MELEE_HIT 0x4B 0 / EV_MELEE_MISS 0x4C 0
entity-events sent 25:4 31:86 32:3 33:85 152:183 153:90 154:31 156:58 157:43 158:17
retail dm demo: (41,0) × 2250 / (42,0) × 85
两活客户端探针: 140 次远程实体事件 / 开火 0 次横越
两弹匣 run (2026-08-21): events@10C = 55 (0x37) 在弹匣末尾
```

## 十二、未闭合点

- `lea ecx,[ecx+ecx+imm8]` 里 `ecx` 的来源（那个 `weaponDef` 判别子的语义）。
- `i`（那个 `2 × i` 的 `i`）与"手/最后一发"的对应。
- `SV_PresentationFireEventId` 的映射（在 `.hpp` 里）。
- `MaximumClientEventsPerCommand` 的值。
- `EventSvFireWeaponVariantA/B` 的 `edi` 参数来源。
- 下一个文件：`sv_zm_box_mp.cpp`（`35,482` 字节）。
