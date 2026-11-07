# Living cyborg collision against the player

Status: BB accepted on published96208b3. Factory and exact-build two-client
Nuketown FFA playtests PASS. No native authoritative AI controller claim.

## Evidence

Exact out.exe SHA256044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
IDA instanceeeah settled at35783functions. Link gate0x46D9F0 and0x46DA30 feed
the spatial tree0x43EC90. Walker0x46DCF0 calls capsule clip0x46DAE0, which uses
entityState+0xAC and gives packed non-player entities contents1. Bounds decode
0x46D6E0 insets each side: solid68010F -> midpoint(0,0,36),half(14,14,35).
Native0x668560/0x667590 retain capsule narrow phase. Player movement helper
0x413E60 removes02004000 only when recovering a start-solid trace; cyborg bit1
is not removed. This is not evidence for timed zombie pass-through.

Five original zm recordings:46664 exact snapshots.452153 standard-solid actor
frames and1373872 known corpse frames with solid0 (19 unknown retained).
Two Factory recordings yield3992 nearby standard-solid actor/standing-player
pair observations,min28.44/28.64units; another map contains a few closer cases.
Transmitted actor capsules can overlap each other. Snapshot positions, remote
player coverage and absent server decision state limit crowd-policy inference.
Full local reproducible census and hashes remain outside the contribution.

1130 death-command positions exactly match independently decoded entity positions.
974 commands arrive while solid is still nonzero; all1130 become zero within
0–1400ms,median500ms. The accepted project policy clears during its first death
lifecycle frame instead; this change preserves that policy and corpse retention.

## Implementation

Create a separate player-movement view at the existing collision rebuild boundary.
Only linked zombie_actor entities of type19 with a valid nonzero packed solid
receive the native-decoded capsule and contents1. Other actors remain excluded.
Non-actor entries are copied unchanged. Pmove alone consumes this view; bullets
retain body contents and skeletal hit poses, while navigation retains its previous
actor-free view. No animation, crowd-pushing, attacks, movement caps or packet
layout changes. Reset/failure and entity lifetime rebuild clear the added view.

No extra world trace, DObj update or asset lookup per actor. Existing swept-AABB
broadphase rejects distant capsules before native narrow phase; do not replace
this with arbitrary nearest-N dropping that could permit walking through a crowd.
OLMOD_ZM_PLAYER_COLLISION_PROFILE=1 enables five-second aggregate cost of actual
projected actor capsule calls. It is off by default. Existing frame/Pmove timings
remain necessary to assess total server cost; unit tests cannot establish live FPS.

## Verification and remaining work

Focused source checks cover Pmove handoff, separate navigation/weapon views,
standard native shape/contents, distant broadphase rejection, death/free cleanup,
and identical ordinary two-player collision views. Required canonical suites,
50ms regression,Release and evidence audit must pass before packaging.

Factory: hold forward into a stationary zombie; slide along its sides; approach
a group; cross dying/settled bodies; test stair/window exits and initial overlap.
Profile a dense wave and compare frame cost against the accepted base. No claim
of performance equivalence until measured. Two-client FFA uses this exact DLL.
Actor avoidance is unchanged; this is not rigid actor-actor collision restoration.

## 中文摘要

依据同版本IDA胶囊裁剪与原始录像，恢复玩家移动对活机械僵尸的阻挡。
独立Pmove投影使用网络solid解码边界和contents1；不改变子弹骨骼碰撞、
僵尸导航或多人实体。沿用已有宽相位剔除，诊断为可选五秒汇总。
录像允许僵尸胶囊互相重叠，不宣称恢复原生群体控制器。Factory至第4回合101击杀及同构建双客户端FFA实测通过。

## Accepted candidate verification

DLL203F34303C5620CC5E09C38BF71D32525633CD9E3C328B4D6442B5BB11B4DCF5.
Factory reached101 kills/round4 with correct collision and no noticeable
performance issues. Exact-build two-client Nuketown FFA passed. These are
playtest results; reciprocal combat was not individually instrumented.
Seven canonical suites,50ms server regression,Release and source audit passed.
538133 profiled capsule calls averaged0.490us; largest five-second aggregate
8.220ms. Isolated timing spikes remain; no claim of zero stutter or a controlled
same-population comparison. Gameplay source matches the accepted package.
