# Bot torso and remote body audit — 2026-09-15

Read-only source/offline audit. No source edits, builds, tests, process changes,
or visual verification performed by this worker.

## Torso zero is expected

C1 `405b70` is the animation setter; `405c80` executes parsed animation commands.
The body selector uses 1=legs, 2=torso, 3=both. For selector 3, C1 writes the
chosen animation to playerstate legs (`405bec..405bf2`, duration +d0/index +c4),
then `405c02..405c08` explicitly sets the subsequent torso animation index to
zero. The torso writer at `405c4b..405c6b` stores index +cc, duration +d4, and
inverts restart bit 0x400. Existing matching animation may avoid this write.
Thus torso 0 or 1024 means no independent upper-body override, while the legs
animation supplies the full-body pose. It does not mean missing torso bones.

Retained native `BG_PlayAnim_160` and `BG_PlayAnim_50` implement the same branch:
selector 3 zeroes ecx, then writes native torsoAnim +94. `animBodyPartsStr` maps
`BOTH` to 3. `BG_ExecuteCommand` contains inlined instances of this setter.

Mounted `bin/home/codol_rawfiles/mp/playeranim.script` uses `both` throughout
ordinary standing/crouching/prone idle and walking/running. Examples: idle
default `pb_stand_alert` at line192, pistol idle `pb_stand_alert_pistol` at148,
and pistol combat walk `pb_combatwalk_forward_loop_pistol` at780. Independent
`torso` commands include flinch and weapon events, rather than all locomotion.

Offline disassembly saved in `obj/bot-torso-audit/c1-setanim-execute.txt`.

## Observed producer evidence and limits

Parent's initial active capture: bot entities1/3 had current weapons118/122,
legs1361/294 and torso0. Those torso values alone are valid.

During this audit the existing parent-owned
`obj/codol-live-player-render-active-20260915.json` had advanced to command472507:
entity1 legs1054/torso1024; entity2 legs1318/torso0; entity3 legs1054/torso1464.
All had nonzero weapon pairs and appearance-only DObj model lists. This is
saved evidence, not a fresh worker memory capture. The nonzero torso1464
demonstrates at least one independent torso animation is published; it does
not establish correct animation names, goal weights, playback time, or skinning.

Native conditions are selected before movement in `codol_pmove_c1.c` through
`BG_AnimUpdatePlayerStateConditions`. That function derives playerAnimType and
weaponClass from the selected viewmodel weapon definition. Idle/walk script
defaults still provide a full-body pose even without a specialized weapon
condition. No reason found to force a nonzero torso for normal locomotion.

## Concrete separate native lookup defect

`src/asmsource/_bg_animation_mp.asm`, `BG_PlayerAnimation_60`, computes
`(es.legsAnim & ~0x400) * 0x60`, then adds `[bgs]` before reading flags +50.
CoDOL animation records actually live in the independent
`CODOL_AnimationRecords` allocation (`codol_animation_tables.c:12`), and other
lookups in the same function explicitly use that base under CODOL_SERVER.
This remaining lookup therefore reads the old storage rather than the native
C1 animation record. Its test is mask0x30 and selects leg yaw handling.

Proposed narrow repair: replace that `add eax, [bgs]` with the existing
`ANIM_ADD_BASE eax` abstraction. Parent notified; worker has not edited it.
This is an evidenced native pose-condition defect, not proof of the client
freeze or missing world-gun cause. Client world-weapon DObj construction remains
a separate investigation owned by parent/another worker.

Next discriminant for frozen models: compare received legs/torso animation
names and actual C1 XAnim node goal weights/time across active snapshots.
Nonzero network indices alone cannot prove playback. Do not replace legitimate
torso0 with a fabricated idle torso as a workaround.

## Follow-up weapon condition audit

User subsequently reported bots now use the correct pose; no forced animation
change is justified. Two separate source omissions are nevertheless evidenced.

`build_weapon_core` in `codol_weapon_native.c` zero-initializes its result and
never assigns `WeaponDef.playerAnimType`. The selected viewmodel definition's
native +128 field is consumed by `BG_AnimUpdatePlayerStateConditions`.
C1 `405F25` obtains that definition and `405F32` reads **C1 definition+33c**
for current playerAnimType. Its source field should be validated and assigned
to the native named member, not inferred from weapon class.

C1 `405F78..405FC9` separately derives primary animation type from the held
weapon at **C1 playerstate+33c**, regardless of selected offhand. The current
native extension instead mirrors condition0, which uses view/offhand selection.
The correction should derive native condition16 from the held native ps.weapon
definition. In ordinary rifle use these coincide; while a grenade is selected
they can differ. The mounted script explicitly uses playerAnimTypePrimary for
shield/grenade combinations. This is not evidence that all rifles chose pistol.

C1 writes this mask at condition storage+0x78 (physical slot15). Native's named
extension places playeranimtypeprimary at slot16 because the retained name
ordering differs. Correct semantic named storage; do not copy a C1 numeric slot
into the native parser domain without migrating every consumer.

Saved exact offline trace: `obj/bot-torso-audit/c1-animation-conditions.txt`.
Parent notified of both producer omissions. No worker source edits or live
capture in this follow-up. A zero type selects named `none`, whose mounted idle
branch is `pb_stand_alert`, not the explicit pistol branch.

### Source correction written for parent review

`codol_weapon_native.c` now assigns verified source+33c to named playerAnimType,
with an offsetof128 native ABI assertion and a less-than64 condition-mask bound.
This preserves mounted named-type indices rather than hardcoding a rifle type
or mapping weapon classes. `codol_animation_tables.c` now reads the held native
weapon definition for condition16, with explicit invalid-type failure.

The existing end-frame caller remains. The pre-movement producer needs the same
helper immediately after BG_AnimUpdatePlayerStateConditions in codol_pmove_c1.c;
C1 performs both mask updates inside405f00 before input processing. Parent
notified of this third-file integration need. No builds/tests or live behavior
claim. Shared-file changes outside these two owned files were preserved.
