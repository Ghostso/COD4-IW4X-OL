# Phase 4 收口：netField 字段语义与 baseline（2026-10-23）

状态：`DONE`（已命名语义 + 未命名字段保留索引/offset/bits）

## 1. playerState

表：`0x00DA8078`，字段数：`87`。

| Index | Offset | Bits | Names |
|---:|---|---:|---|
| 0 | `0x140` | 11 | - |
| 1 | `0x040` | 32 | PlayerStateAmmoClipAuxiliarySection, PlayerStateEventSequenceField, PlayerStateHealthStatMask |
| 2 | `0x098` | 32 | PlayerStateDeadYawStatMask, PlayerStateHeldWeaponAuxiliarySection, PlayerStateOldEventSequenceField |
| 3 | `0x09C` | 32 | PlayerStateAmmoPoolAuxiliarySection, PlayerStateRightWeaponTimeField |
| 4 | `0x0A0` | 32 | PlayerStateImplementedAuxiliaryPrefix, PlayerStateMaxHealthStatMask, PlayerStateUnk04A4TimeField |
| 5 | `0x0A4` | 32 | PlayerStateTorsoTimerField |
| 6 | `0x0A8` | 32 | PlayerStateAimSpreadScaleField |
| 7 | `0x0AC` | 32 | PlayerStateLegsAnimField |
| 8 | `0x0B0` | 0 | PlayerStateLastChangedBits, PlayerStateSpawnGenerationStatMask |
| 9 | `0x0B4` | 0 | PlayerStateRightWeaponAnimField |
| 10 | `0x0B8` | 0 | - |
| 11 | `0x0BC` | 0 | PlayerStateObjectiveAuxiliarySection |
| 12 | `0x0C0` | 0 | PlayerStateBobCycleField, PlayerStateHudElemAuxiliarySection |
| 13 | `0x0C4` | 0 | - |
| 14 | `0x0C8` | 0 | - |
| 15 | `0x0CC` | 0 | PlayerStateMovementDirField |
| 16 | `0x0D0` | 0 | - |
| 17 | `0x150` | 4 | PlayerStateAuxiliarySectionBits, PlayerStateRightWeaponStateField, PlayerStateStatsMaskBits |
| 18 | `0x154` | 1 | - |
| 19 | `0x158` | 1 | - |
| 20 | `0x07C` | 16 | - |
| 21 | `0x04C` | 32 | - |
| 22 | `0x050` | 32 | - |
| 23 | `0x054` | 32 | - |
| 24 | `0x058` | 32 | - |
| 25 | `0x05C` | 32 | - |
| 26 | `0x060` | 32 | - |
| 27 | `0x064` | 32 | PlayerStateTorsoAnimField |
| 28 | `0x068` | 32 | PlayerStateEFlagsField |
| 29 | `0x06C` | 32 | - |
| 30 | `0x070` | 32 | PlayerStateHoldBreathScaleField |
| 31 | `0x074` | 32 | PlayerStateLegsTimerField |
| 32 | `0x078` | 32 | - |
| 33 | `0x018` | 10 | - |
| 34 | `0x01C` | 10 | - |
| 35 | `0x020` | 10 | PlayerStateLastSprintStartField |
| 36 | `0x004` | 11 | PlayerStateLastSprintEndField |
| 37 | `0x008` | 32 | - |
| 38 | `0x00C` | 32 | - |
| 39 | `0x010` | 3 | PlayerStateCurrentWeaponField |
| 40 | `0x014` | 10 | - |
| 41 | `0x144` | 11 | PlayerStateWeaponPositionFractionField |
| 42 | `0x14C` | 16 | PlayerStateDamageTimerField |
| 43 | `0x044` | 8 | PlayerStateSprintStartMaxLengthField |
| 44 | `0x024` | 10 | PlayerStateRightWeaponDelayField |
| 45 | `0x028` | 10 | - |
| 46 | `0x030` | 6 | - |
| 47 | `0x034` | 6 | PlayerStateGroundEntityField |
| 48 | `0x038` | 6 | - |
| 49 | `0x048` | 8 | - |
| 50 | `0x148` | 6 | - |
| 51 | `0x080` | 10 | PlayerStateLeftWeaponAnimField |
| 52 | `0x084` | 10 | PlayerStatePmTimeField |
| 53 | `0x088` | 11 | PlayerStateOffhandWeaponField |
| 54 | `0x08C` | 10 | PlayerStateOtherFlagsField |
| 55 | `0x090` | 10 | PlayerStateDamageYawField |
| 56 | `0x15C` | 5 | PlayerStateViewmodelIndexField |
| 57 | `0x02C` | 6 | PlayerStateGrenadeEntityField |
| 58 | `0x03C` | 6 | PlayerStateMoveSpeedScaleMultiplierField |
| 59 | `0x094` | 32 | PlayerStateClientNumField |
| 60 | `0x0D4` | 0 | PlayerStateSpeedField |
| 61 | `0x0D8` | 0 | - |
| 62 | `0x0DC` | 0 | PlayerStateLeftWeaponStateField |
| 63 | `0x0E0` | 0 | PlayerStateGravityField |
| 64 | `0x0E4` | 0 | - |
| 65 | `0x0E8` | 0 | - |
| 66 | `0x0EC` | 0 | PlayerStateDamageEventField |
| 67 | `0x0F0` | 0 | PlayerStateCursorHintField |
| 68 | `0x0F4` | 0 | PlayerStateViewEntityField |
| 69 | `0x0F8` | 0 | - |
| 70 | `0x0FC` | 0 | - |
| 71 | `0x100` | 0 | - |
| 72 | `0x104` | 0 | - |
| 73 | `0x108` | 0 | PlayerStateDamagePitchField |
| 74 | `0x10C` | 0 | PlayerStateDamageCountField |
| 75 | `0x110` | 0 | PlayerStateDamageDurationField |
| 76 | `0x114` | 0 | - |
| 77 | `0x118` | 0 | PlayerStateWeaponFlagsField |
| 78 | `0x11C` | 0 | PlayerStateCursorHintEntityField |
| 79 | `0x120` | 0 | PlayerStateGrenadeTimeField |
| 80 | `0x124` | 0 | PlayerStateCursorHintStringField |
| 81 | `0x128` | 0 | PlayerStateViewHeightLerpTargetField |
| 82 | `0x12C` | 0 | PlayerStateRadarFlagsField |
| 83 | `0x130` | 0 | PlayerStatePmTypeField |
| 84 | `0x134` | 0 | - |
| 85 | `0x138` | 0 | - |
| 86 | `0x13C` | 0 | PlayerStateCompassRadarField |

## 2. entityState

表：`0x00DA63E8`，字段数：`24`。

| Index | Offset | Bits | Names |
|---:|---|---:|---|
| 0 | `0x04C` | -58 | EntityStateTypeField |
| 1 | `0x050` | -100 | EntityStateOriginYField |
| 2 | `0x054` | -100 | EntityStateOriginXField |
| 3 | `0x041` | -57 | EntityStateAngleYField, EntityStateFieldSkipBits |
| 4 | `0x044` | -97 | EntityStateMovementDirField |
| 5 | `0x048` | 16 | EntityStateOffhandWeaponField |
| 6 | `0x042` | -57 | EntityStateLastChangedBits, EntityStateOriginZField |
| 7 | `0x043` | -100 | EntityStateEventSequenceField, EntityStateTime2BitCount |
| 8 | `0x00C` | 10 | EntityStateAngleXField |
| 9 | `0x038` | 12 | EntityStateLegsAnimField |
| 10 | `0x03C` | -97 | EntityStateTorsoAnimField |
| 11 | `0x040` | -57 | EntityStateEFlagsField |
| 12 | `0x034` | 32 | EntityStateFirstEventField |
| 13 | `0x014` | 10 | - |
| 14 | `0x018` | 10 | - |
| 15 | `0x028` | 6 | - |
| 16 | `0x01C` | 10 | EntityStateGroundEntityField |
| 17 | `0x02C` | 6 | EntityStateSolidField |
| 18 | `0x020` | 10 | EntityStateWeaponField |
| 19 | `0x030` | 6 | - |
| 20 | `0x004` | 11 | - |
| 21 | `0x008` | 11 | - |
| 22 | `0x010` | 11 | - |
| 23 | `0x024` | 6 | EntityStateUnknownE0Field |

## 3. 数组元素类型

| Type | Table | Entity hint |
|---:|---|---|
| 0 | `0x00DA4608` | ET_GENERAL |
| 1 | `0x00DA4BF8` | ET_PLAYER |
| 2 | `0x00DA4EF0` | ET_PLAYER_CORPSE |
| 3 | `0x00DA6508` | ET_ITEM |
| 4 | `0x00DA7A20` | ET_MISSILE |
| 5 | `0x00DA4608` | ET_INVISIBLE |
| 6 | `0x00DA6808` | ET_SCRIPTMOVER |
| 7 | `0x00DA6E08` | ET_SOUND_BLEND |
| 8 | `0x00DA7108` | ET_FX |
| 9 | `0x00DA7408` | ET_LOOP_FX |
| 10 | `0x00DA7728` | ET_PROCEDURAL_LINE_FX |
| 11 | `0x00DA4608` | ET_PRIMARY_LIGHT |
| 12 | `0x00DA5AF0` | ET_TURRET |
| 13 | `0x00DA54E0` | ET_HELICOPTER |
| 14 | `0x00DA57D8` | ET_PLANE |
| 15 | `0x00DA51E8` | ET_VEHICLE |
| 16 | `0x00DA4608` | ET_VEHICLE_COLLMAP |
| 17 | `0x00DA4608` | ET_VEHICLE_CORPSE |
| 18 | `0x00DA4608` | ET_VEHICLE_SPAWNER |
| 19 | `0x00DA5DE8` | ET_ACTOR |
| 20 | `0x00DA4608` | ET_ACTOR_SPAWNER |
| 21 | `0x00DA60E8` | ET_ACTOR_CORPSE |
| 22 | `0x00DA6B08` | ET_LOOT |
| 23 | `0x00DA4900` | ET_EVENT_OR_FALLBACK |

## 4. Baseline

- 默认 wire baseline：全零。
- 快照首帧显式写入的已知默认值来自 `MotionSnapshot.cs` 和黄金首帧：
  - x=48, y=-572, z=-116
  - viewHeight=60, gravity=800, movement speed=190
  - groundEntity=2047, cameraEntity=2047
  - 默认武器 M4A1 1156
  - clip=30, reserve=90, ammoKey=585

## 5. 产物

- 语义 JSON：`fixtures/inmatch_field_semantics_20261023.json`
- 参考源：`sv_snapshot_mp.hpp/.cpp`、`MotionSnapshot.cs`、`golden_first_snapshot.hex`

## 6. 剩余未知

- playerState 未命名字段：36 项
- entityState 未命名字段：7 项
- 未命名字段仍有完整 offset、bits 和 codec 证据，不阻塞 Phase 5。

