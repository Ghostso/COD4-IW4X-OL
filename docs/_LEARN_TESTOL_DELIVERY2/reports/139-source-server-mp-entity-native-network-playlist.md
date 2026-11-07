# 139 · 实体池、原生 characterInfo/pmove、UDP 与预约状态机

## 学习范围

本报告完整阅读 `server_mp` 以下 **10 个文件**：

- `sv_entity_mp.hpp/.cpp`
- `sv_native_characterinfo_mp.hpp/.cpp`
- `sv_native_pmove_mp.hpp/.cpp`
- `sv_network_mp.hpp/.cpp`
- `sv_playlist_mp.hpp/.cpp`

重点不是只摘常量，而是核对实际分配、验证、回滚和状态转换。文件内保留了大量旧 build/旧结论注释，以下以当前可执行代码和最终修正说明为准。

## 一、实体编号与尸体环

### 1.1 当前 build 的编号边界

| 名称 | 值 | 用途 |
|---|---:|---|
| `EntityNumWorld` | 2046 | world，同时是实体池数组长度，池合法下标0..2045 |
| `EntityNumNone` | 2047 | 空引用 |
| `FirstDynamicServerEntityNum` | **37** | 普通动态分配起点 |
| `FirstPlayerCorpseEntityNum` | 19 | 玩家尸体环起点 |
| `PlayerCorpseRingSize` | **18** | 尸体槽19..36 |
| `EntityReuseDelayMilliseconds` | 500 | FIFO 普通槽复用等待 |
| `EntityEventLifetimeMilliseconds` | 300 | temp event 生命周期 |

`19 + 18 == 37` 由 `static_assert` 固定，防止把3.3.3.3的8槽尸体环带回1649370。文件前半仍保留旧 build 的“19..26、动态27”推导，后半明确说明那些代码地址/数量未在本 build 重跑；当前证据是本 build 6160/6160 快照里的 corpse 19..36 和最低动态37。

### 1.2 尸体相关常量与机制

- `SvCorpseReinitialiseFlag = 0x80000`
- `SvCorpseSpawnFlags = 0xA0000`
- `SvDeadPlayerHiddenFlag = 0x20000`
- corpse 初始 trajectory=1；ragdoll delay=1000 ms；ragdoll trajectory=9；angle trajectory=10。
- demo 中 ragdoll 值13不适用于本 build，本 build evaluator 只接0..12；直接把录制常量跨 build 发送会触发90错误。
- `SvCorpseSettleRespawnSeparationMs = 250`，且静态断言必须>0。

250 ms 的原因不是任意“让尸体更好看”：若 settle 与 respawn 同帧，客户端可能先把重生玩家 clientInfo 的10个模型槽清空，再把空 clientInfo 复制到 corpseinfo，最终 `BG_UpdatePlayerDObj` 因空 model 释放 corpse DObj。服务器快照仍有 corpse，但客户端不再绘制，所以仅做服务器侧状态测试抓不到这个回归。

`SvDeadPlayerHiddenFlag` 在 playerState 中仍保留供 pmove，仅在 holding death animation 时从线上 entityState 屏蔽；若一直置位而无 corpse 接管，会表现为敌人消失。

## 二、`SvEntityPool` 的真实分配与回滚语义

### 2.1 reset/reserve

`reset(first)`：

- 只要求 `first < 2046`；37是生产调用方政策，不是此函数硬编码。
- 清空所有 lifetime/reservation/FIFO；每项填 entityNum，other=2047，generation从0重新计。
- highWater=first，configured=true。

`reserve(n)` 只在 configured、`first <= n < 2046`、未使用且 `n >= highWater` 时成功。重复 reserve 是 no-op。reserved 槽用于地图 const-baseline 静态实体，普通 `spawn()` 会跳过，防止动态实体继承该编号的客户端 baseline。

### 2.2 `spawn` 与 `spawnAt`

普通 `spawn(serverTime)`：

1. 若 FIFO 非空，检查队首：`serverTime - eventTime >= 500` 或 highWater 已到2046时可复用；否则不取队首。
2. 未复用时，从 highWater 顺序分配，先跳过连续 reserved。
3. highWater 到2046且无可用 FIFO 时失败。
4. 新 lifetime 保留原 generation，写 birthTime、inUse=true、other=none。

FIFO 只检查队首是合理的，因为按 free 时间入队；不能把“队首未冷却”理解成应遍历后面找更老的项。

`spawnAt(n,time)` 仅允许 **reserved 且未使用** 的编号。它不推进 highWater，也不要求 n<highWater；因此静态编号可位于顺序高水位之外。generation同样保留，free后递增。

### 2.3 free 与 rollback

`free(handle,time)`：

- 验证编号、inUse、generation；
- 普通槽需 `< highWater`；reserved 槽即使 `>= highWater` 也允许；
- generation+1，清为未使用，eventTime=free time；
- 普通槽进入 FIFO；reserved 槽只回到 reservation，不进入 FIFO。

`rollbackFree` 只适用于刚 free 的普通 FIFO 槽：

- previousLifetime 必须同号、同 generation、原来 inUse；
- 当前实体必须未使用且 generation==handle.generation+1；
- FIFO 尾必须正好是该实体号；
- pop_back 后完整恢复 previousLifetime。

它要求 `handle.entityNum < highWater`，且要求 FIFO 尾存在同号项，所以 **reserved 槽的 free 不能靠这个函数回滚**。这与“free() appends exactly one FIFO entry”的注释前提一致：reserved free 根本不 append。

### 2.4 event 与 resolve

- `markFreeAfterEvent` 要求普通高水位内、handle匹配、otherEntityNum<=2047；写 eventTime/other/freeAfterEvent。
- `expiredEventEntities` 只收集，不释放；条件是 unsigned `serverTime-eventTime > 300`，**恰好300不expire**。
- `resolve(handle)` 先数字 resolve，再比 generation，陈旧 handle 失败。
- `resolve(entityNum)` 只返回 inUse；reserved 槽不受 highWater 限制，否则 spawnAt 的静态实体会无法用于碰撞/释放。
- mutation API 要 generation handle；纯数字 resolve 是内部/当前槽查询，不足以证明旧身份仍有效。

## 三、原生 characterInfo：stride、lerp frame 与条件表

### 3.1 当前布局

| 项 | 值 |
|---|---:|
| `SvNativeCharacterInfoSize` | **0x450** |
| legs lerp frame | **0x17C** |
| torso lerp frame | **0x1BC** |
| lerp frame size | 0x40 |
| set accessor（frame内） | +0x1C |
| get accessor | +0x20 |
| protected value | +0x24 |
| selector count | **33**（0..32） |

本 build 的 `BG_PlayerAnimation` 直接用 `characterInfo+0x17C/+0x1BC`，两者相距0x40。旧0x160/0x1A0属于3.3.3.3；差量是+0x1C，不能和整个 characterInfo stride 的增长混为一谈。

原生 frame 其他已确认字段：+0x10 animation number（&0x3FF）、+0x14 anim-def pointer、+0x34 lerp rate、+0x38 timestamp。

### 3.2 accessor 交叉解码

对 frameAddress = characterInfoAddress + frameOffset：

```text
set = encodedSet ^ setKey ^ (frameAddress + 0x20)
get = encodedGet ^ getKey ^ (frameAddress + 0x1C)
```

即 set 存在+0x1C、以+0x20地址为 key；get 存在+0x20、以+0x1C地址为 key。`SV_Decode...` 先检查 frameOffset 后完整0x40字节在 span 内，再 memcpy 避免对齐假设。

`SV_AreNativeLerpFrameAccessorsValid` 对 legs/torso 两帧都解码，并要求 `(set,get)` 同时匹配33对原生 RVA 的同一索引。RVA 是当前 build 逐 selector 提取的，前23对与旧 build 有+0x10差，后10对没有，所以不能做统一平移。

33而非34是硬边界：原生 initializer `cmp selector,0x20; ja bail`。旧模34会让约1/17选择落到永远不可达的第34对。

### 3.3 动画投影的当前 offsets

`SV_ProjectNativePlayerAnimationToCharacterInfo` 要求 characterInfo 至少0x450且 `SV_ReadNativeEntityState(entityState)` 成功，然后复制：

| entityState 源 | characterInfo 目的 |
|---:|---:|
| 0xDC | 0x258 |
| 0xE0 | 0x25C |
| 0x70 | 0x260 |
| 0x6C | 0x264 |

再将 characterInfo 0x268、0x26C 写0。0x68/0x6C 的旧语义在本文件中保持 opaque，不擅自命名。该函数只投影这6个 dword，不声称完成完整 characterInfo 初始化。

### 3.4 anim script/condition 表是两个全局块

- animScript stride = **0x204**。
- scrap script offset=0x25D7C；event table=0x25F80，二者恰好相差0x204并静态断言。
- `SV_NativeAnimScriptEventOffset(event)` 只接0..39，越界返回 `nullopt`，不夹到邻近脚本。
- 事件总数40；条件总数 **19**。
- condition base=characterInfo+0x2EC，stride=8。

`BG_AnimScriptEvent` 使用两个不同全局：`0x0827F734` 指 script table，`0x0827F730` 指 characterInfo。引擎正常流可能让它们相同，但本项目只安装后者，不保证前者同步。每个 animScript 首 dword 是 numItems，`<=0` 时 walker 不写 out，调用方预置的-1就成为唯一失败信号。

旧把 condition 数当38会多读19个相邻槽，诊断出的 nonzero 不再能证明条件是否缺失。

## 四、Native usercmd/pmove ABI

### 4.1 `SvNativeUserCmd` = 0x2C

字段顺序与静态断言：

- commandTime 0x00、buttons 0x04、angles[3] 0x08；
- weapon 0x14、offHandIndex 0x16、lastWeaponAltModeSwitch 0x18；
- forwardMove 0x1A、rightMove 0x1B；
- conditionalAngle 0x1C；
- conditionalByte、padding、conditionalElevenBits；
- selectedLocation[3]、selectedDirection[2]、结尾 padding[3]。

`SV_ToNativeUserCmd` 逐字段转换，padding 保持值初始化0；没有凭空从其他字段推导条件数据。

### 4.2 `SvNativePmove` = 0x12C，x86专用

| 字段 | offset |
|---|---:|
| playerState* | 0x000 |
| cmd | 0x004 |
| oldcmd | 0x030 |
| traceMask | 0x05C |
| numTouch | 0x060 |
| touchEntities[32] | 0x064 |
| bounds | 0x0E4 |
| xySpeed | 0x0FC |
| proneChange | 0x100 |
| mantleStarted | 0x104 |
| mantleEndPosition | 0x108 |
| mantleDuration | 0x114 |
| viewChangeTime | 0x118 |
| viewChange | 0x11C |
| torsoPitch | 0x120 |
| waistPitch | 0x124 |
| handler | 0x128 |

`sizeof(void*)==4` 是硬 ABI gate；在x64宿主直接 static_assert 失败，而不是错误地按8字节指针继续。

本 build 与旧 build 的 pmove_t 自身位移已核对不变；变化主要发生在 `pmove->playerState` 指向的字段，不应因此误判整个 pmove_t 都平移。

### 4.3 输出验证与未证明域

`SV_ReadNativePmoveOutput` 先拒绝：

- numTouch<0 或 >32；
- handler !=0；
- mantleStarted>1。

然后只复制前 numTouch 个 touch，要求0..2047。`SV_IsNativePmoveOutputValid` 还要求：

- bounds midpoint/halfSize 全 finite，halfSize 各分量>=0；
- xySpeed finite 且>=0；
- mantleEndPosition/viewChange/torsoPitch/waistPitch finite；
- touch 数量与数组一致，值<=2047。

**proneChange、mantleDuration、viewChangeTime 的 sentinel/范围尚未证明**，当前原样复制，没有虚构合法区间。`failure` 默认None；失败 enum 有16种，名称函数覆盖 binding/command/thread/reentrancy/handler/anim condition/commandTime/slice/native exception/trace/output 等具体阶段。

## 五、UDP transport：每帧上限、锁与统计

### 5.1 参数

- 默认端口28960；
- 每帧最多接收64个 UDP datagram；
- receive buffer=65,507 bytes（IPv4 UDP 理论最大 payload）；
- peer key = `(uint64(ipv4)<<16)|port`，故 IPv4+port 联合标识，不混淆同IP不同客户端。

### 5.2 start/stop

`start(port)` 在 mutex 下：

- 已 open 且端口相同：幂等成功；
- 否则 close，清 status 和 peerStatus，再 `NET_IPSocket(port)`；
- 失败只保留 lastSocketError；
- 成功 bound=true，port取 socket 实际端口。

`stop` close，bound=false、port=0，清 peerStatus、nonce=0；其他计数没有全部清零，读取状态时要注意这不是完整 `status_={}`。

### 5.3 收包与 DTLS entropy

`NET_Frame` 持同一 mutex，未 open直接返回。每包：

- Empty 停止本轮；Error 记录 lastSocketError并停止；
- 成功收包增加 packetsReceived/lastPacketReceivedTime；
- 每 peer 前8个包记录大小和首字节 type（全局 `transportPacketDiagnostics` 计数，不随 stop 清除）；
- `nonce = nonce*1664525 + 1013904223`（uint32自然回绕）；
- entropy = `nonce ^ now ^ ipv4 ^ (port<<16)`；
- 调 `server.NET_DtlsPacket(peer, bytes, now, entropy)`；
- reply非空立即回发。

这个 entropy 是传输层给 DTLS 握手的输入，不应仅凭 LCG 名称把它称为密码学随机数；具体用途和强度需到 `NET_DtlsPacket` 实现核对。

### 5.4 发包统计

每次 `NET_SendPacket`，无论成败都：

- 建/取 peerStatus；
- attempts++，写 lastSendTime、lastSendBytes、lastSendError；
- 同步全局 status.lastSocketError。

成功才 succeeded++、bytesSent+=packet.size、全局 packetsSent++、lastPacketSentTime=now；失败 failed++。空 outbound packet 在 `NET_SendPackets` 中被跳过，不计 attempt。

`status()` 和 `peerStatus()` 都加锁并返回值拷贝。`NET_Frame` 在锁内调用 server 和可能的 send，所以 transport 层串行化收发；更高层 ServerCore 自己的锁/重入边界要另读，不能假设无锁。

## 六、Booking 两种语法与 playlist 解析

### 6.1 两种形式

**CODOL 当前形式**：

```text
mmstart 2486 1; 2481 18; 2489 1; 2500 0;
g_gametype war; 2483 1; map mp_bloc
```

直接携带 map 和 g_gametype，不必有 playlist/rotation。

**3.3.3.3形式**：

```text
mmstart sv_resetServer; 2486 1; 3265 12; 2489 0;
playlist 26; start_map_rotate_once 0
```

必须有首个 `sv_resetServer` 和五个数值字段。

`SvBookingCommand` 用 `hasPlaylistId/hasRotationIndex` 区分“没携带”与“携带0”。后续比较绝不能把缺省0当真实 playlist 0。

### 6.2 解析细节

- trim 只去空格、tab、CR，不去 LF；
- 第一个非空 token 必须以精确小写 `mmstart ` 开头；
- 后续按分号拆分，空 token 跳过；
- `parseCommandToken` 要 name/value 都非空；不能解析的普通 token 被跳过；
- lookup 遇重复 name 返回 `nullopt`，防歧义；
- 数值用 `from_chars` 完整消费 uint32；
- map/gameType 只接受 `_`、数字、英文字母，非空。

若 map 和 gameType 均存在，走 CODOL 形式，读取2486/2481/2489为 player/max/private（缺或非法时保持0），并返回直接名称；其他数字 id 不臆测语义。

若没有同时存在这两个名称，则走旧形式，必须 sawReset 和2486/3265/2489/playlist/start_map_rotate_once全部有效，两个 has 标志设true。

`SV_ParsePlaylistDocument`、engine/booking gametype 双向映射直接委托 shared `CodolPlaylist`，真正映射表在 shared 文件，不在此 cpp；`ffa→dm、tdm→war、kc→conf` 是头文件给出的例子。

### 6.3 Resolve 的优先级

1. 先 parse command。
2. command 同时有 map/gameType：直接构造 weight=1 的 rotation，不查 playlist。
3. 否则按 playlistId 找 playlist 且 rotationIndex 在范围内，命中即用。
4. 未命中才使用 optional nativeSelection fallback。
5. authoritativeSelection overload 自身仍要求 map/gameType 合法、weight!=0；不是盲信上层任意空 entry。

这与 Appmain 的“command map/gameType 为准、rotationIndex 不一致只记录”相配合，避免把含义不稳定的 capture index 当地图真相。

## 七、`SvPendingBooking` 的代际门槛

状态：optional rotation、initialChecksum、generationRequirement、sawReset。

`assign` 替换 rotation、记录初始 checksum/要求，sawReset=false。

`observeConfigStrings(initialized,checksum,allowReady)`：

1. 无 pending rotation：null；
2. `!initialized || !checksum`：sawReset=true，返回未就绪；
3. `!allowReady`：返回未就绪，**不改变 sawReset**；
4. NewGeneration 且尚未见 reset、initialChecksum非零、当前 checksum==initial：继续等；
5. 否则返回 ready{rotation,currentChecksum}。

所以：

- `CurrentGeneration` 不等待代际变化；
- `NewGeneration` 可通过观察到未初始化/0 checksum 后的新有效值，或 checksum 改变来满足；
- 若 initialChecksum=0 且第一次观察就得到非零 initialized checksum，则不会仅因“没见过reset”而等待；
- allowReady=false 是外部闸，不是 reset 证据。

`commit(ready)` 只检查 pending 且 rotation 完全相等，然后清 rotation；它不重新比较 checksum。调用方必须提交刚从 observe 得到的 ready，不能构造同 rotation 的任意旧 checksum 并声称经过代际验证。`cancel` 清 rotation、initialChecksum和sawReset，但 generationRequirement 保留到下次 assign 覆盖。

## 八、本组关键结论与未闭合点

1. **当前 build 动态起点是37，不是27**；reserved 静态编号和 generation handle 是两套同时必要的机制。
2. **普通池与 reserved 静态池的回滚能力不同**；`rollbackFree` 不能回滚 reserved free。
3. **characterInfo 是0x450，lerp frame 是0x17C/0x1BC，selector 33个**；旧 offsets 自洽验证也可能整套都错，必须用引擎真实 consumer 反证。
4. **anim script 与 characterInfo 来自两个全局**，只安装一个不能推出另一个有效。
5. **pmove ABI 固定x86**，输出中仍有三个未证明时间/哨兵域，验证没有假装全覆盖。
6. **UDP peer 是 IP+port**，每帧64包，统计区分尝试/成功/失败；DTLS entropy 的密码学性质不在本层证明。
7. **Booking command 的直接 map/gameType 比 playlist index 更权威**；`has...` 标志不可丢。
8. **PendingBooking commit 不重新校验 checksum**，代际安全依赖 observe→commit 的正确调用链。

**本组10文件完成。继续学习 `server_mp` 的 Lua/source/splash/use/weapon movement 等文件。**
