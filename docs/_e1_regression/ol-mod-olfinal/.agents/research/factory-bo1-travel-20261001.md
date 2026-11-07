# Factory staged travel — optional BO1 reconstruction

Accepted October2: solo and simultaneous two-player Factory travel, plus exact-build
two-real-client Nuketown FFA, passed. The two-player travel run used debug godmode
and does not validate damage/revival. Machine checks: Release,seven suites,50ms
server,223-review partial source audit and four audit-validator regressions.

This extends the Factory teleporter contribution. It is not a recovered
CODOL paid-travel script. The inspected original CODOL recordings demonstrate
the hidden rooms during extraction, not during paid pad-to-mainframe travel.
Acceptance belongs to the frozen DA gameplay source; it is not inherited from a
preceding build.

## Evidence and boundaries

Original locally extracted BO1 patched Der Riese server script SHA256:
`b93ad9c9226a807f1ae8581b496ea56cb0b9f7b5a22e81f3f5596d685174e47b`.
`player_teleporting`, the nearby-player loop and `teleport_players` establish
two seconds charging, a 176-unit horizontal selection radius, separate hidden
rooms for two seconds, native mainframe landing markers and five seconds cooldown.
The companion client script switches to default vision in the room and restores
the previous vision afterward. This Factory adapter restores its map vision.

The map's four `teleport_room_*` origins match X2048/2368/2688/3008, Y-320,
Z56, yaw90. BO1 authored room FX is `maps/zombie/fx_zombie_flashback_american`,
approximately forty units ahead at eye height, facing270. Resolve the resident
CODOL asset; retain four map-owned emitters. Pad beam and mainframe beam/flat
are distinct assets at distinct authored positions. This first staged candidate
does not reproduce the full peripheral steam/heat-sink group or BO1 side effects
(dog spawns, random vision/FOV changes, zombie kills and powerup drops).

CODOL `out.exe` SHA256:
`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`.
Settled IDA decompilation/disassembly confirms command5 handler6127F0 parses
argument1, moves the integer to EDX at612822 and enters54AD10, which adds that
duration to the millisecond clock. `5 2000` requests the native transporter
overlay; `5 0` enters54AD80 fade. Renderer50AD80/C12670/C118B0 uses
`zombie_transporter_overlay`. The duration consumer does not prove CODOL's
original server-side schedule.

Retain the existing audited ClientThink/native Pmove boundary: CODOL41CB40,
BO1 ClientThink5F9980 and Ghosts140114E10 ownership/order comparison. No foreign
ABI, native layout, netfield or alternate physics algorithm is introduced.
Per-life project metadata temporarily supplies the established0x800 input gate
and pins the room origin around retained native movement. Snapshot-only NoDraw
uses the existing0x10 pre-class consumer (CODOL53C650/53C6AA), not the previously
rejected locked-entity0x100000 flag. Room/arrival animation presentation passed the Factory playtest.

## Opt-in and transaction ownership

Build the normal gameplay plugin. No source editing, compiler define or modified
game EXE is required. Before starting the server and matching clients, set:

```bat
set "OLMOD_FACTORY_INTERACTABLES=1"
set "OLMOD_FACTORY_TELEPORTERS=1"
set "OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1"
```

Use the normal Factory power settings and matching game assets. These variables
must be inherited by the running processes; setting them only during compilation
does not enable the feature. With the third variable unset, linking, gate and
the existing direct-return implementation remain independent of staged travel.
FFA does not admit this controller. Restart after changing the environment.

One payer owns a charge. Living players still near the pad at departure travel
without additional payment. The radius has an explicit reconstructed vertical
guard to exclude stacked floors. Leaving during charging clears the overlay.
The controller tracks every slot's spawn generation, separates room slots and
tries distinct collision-validated core markers; it does not respawn or replace
weapons, ammunition or perks. Room time starts at actual entry, so a late frame
cannot consume the whole visible interval before a snapshot is sent.

Failure policy is project reconstruction: reject missing room assets/endpoints
before charging; refund an empty trip only to the payer's original life. An
obstructed mainframe falls back to the original departure, then a small nearby
collision-checked recovery search. If every destination remains obstructed,
retain ownership and retry at most four times/second, logging at bounded cadence;
never bypass collision or declare arrival. Death/disconnect releases ownership;
map reset clears it. A new life cannot inherit an old hold or refund. A death
inside a room can still require the ordinary death/spectator flow; arbitrary
dead-body relocation is not introduced here.

## Validation

Source regressions exercise wrong-life refusal, snapshot-only freeze/hide,
authoritative inventory/flag retention, safe arrival/unlock, malformed snapshot
metadata rejection, full room duration after a late frame and charge clock wrap.
Real Factory testing must check both travelers, leaving the pad, occupied arrivals,
repeat/cooldown, camera/controls, weapon state and visual/audio effects. Exact-build
two-real-client FFA passed before publication of the combined contribution.

## 中文摘要

此为明确可选的BO1衍生重建，不声称已恢复CODOL原版付费传送脚本。通过独立环境
变量启用两秒充能、独立暗室两秒、主平台安全落点及五秒冷却。复用CODOL原生效果、
移动与快照消费者，不引入跨游戏ABI。玩家代次、费用和冻结独立持有；失败不穿墙。
本候选Factory及同构建双客户端FFA实测通过，不继承此前通过结果。
