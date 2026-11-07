# CoDOL player action audit (2026-09-09)

Method. Every action has three legs, and the mantle failure showed that any
one of them can be missing: (1) the client's usercmd button reaches the
retained engine with the meaning it expects; (2) the retained engine actually
simulates the action; (3) every player-state field the C1 client re-seeds
from the snapshot for that action is published. Evidence sources: the C1
button table (alpha0022 usercmd_codec.py), the retained engine's own button
tests (disassembled in this tree), the CoDOL netfield table
(codol_player_fields.inc, 244 fields), a runtime audit of which wire fields
ever carry a non-zero value, and driver runs against the real client with the
per-action pacing trace. "Verified" means seen in a trace this session.

## 1. Input: C1 button -> retained engine

| C1 bit | action | engine bit tested | status |
|---|---|---|---|
| 0x1 | fire | 0x1 | verified (weapon_fired, hits) |
| 0x2 | sprint | 0x2 (PM_UpdateSprint) | verified: 271 u/s = 180.5 x 1.5, weaponstate 22/23 |
| 0x4 | melee | 0x4 | forwarded; melee temp entity seeds now published |
| 0x8 | use | 0x8 | verified in pacing |
| 0x10 / 0x20 | reload / usereload | same | verified: magazine 30/55 after reload |
| 0x100 / 0x200 | prone / crouch | same | crouch verified (pm_flags 2, viewheight 40); prone now remains a level on every command, matching C1 CL_CmdButtons and retained PM_CheckDuck; live hold/release check pending |
| 0x400 | jump | 0x400 (bg_jump.cpp) | verified (PMF 0x4000, vz) |
| 0x800 | ADS | 0x800 (PM_UpdateAimDownSightFlag bit 11) | verified: pm_flags 0x50 |
| 0x1000 | stance-came-from-held-key | passed through as IW3 0x1000 | harmless, unused |
| 0x2000 | hold breath | 0x2000 | forwarded, unverified |
| 0x4000 / 0x8000 | frag / smoke | same | forwarded; grenade lifecycle events published |
| 0x10000 | tactical (+tact, third equipment slot) | masked from the IW3 word, but read raw by the retained offhand selector (PM_Weapon_CheckForOffHand) | implemented (audit correction) |
| 0x20000 | selected location | -> 0x10000 | killstreak location pick, unverified |
| 0x100000 | ADS throw | -> KEY_MASK_ADS 0x80000 | unverified |
| 0x200000 | remote control | filtered to a fixed mask | killstreak remote, unverified |
| 0x400000 | **4th equipment slot** | dropped | not implemented |
| 0x800000 | dive (dolphin dive) | read raw by codol_dive.c | implemented natively; launch, flight, touchdown, completion verified |
| 0x1000000 | marker slot | dropped | unverified |
| direction bits | move | forward/back/left/right 127 | verified |

## 2. Simulation and publication per action

| action | server simulates | published to client | status |
|---|---|---|---|
| walk / strafe / backpedal | yes | origin, velocity, speed, moveSpeedScale | verified; speeds match the client exactly |
| sprint | yes | PMF sprint bit, sprint phases, sprint state block +0x238..+0x248 | verified (the audit's never-non-zero list was a sampling artefact for these) |
| crouch / prone | yes | stance bits, view height lerp, prone direction floats +0x1a0..+0x1a8 | crouch verified; C1 and retained PM_CheckDuck both consume prone as a level, and the incorrect edge adapter is removed; prone hold/release needs a live check |
| jump / land | yes | PMF jumping, jumpTime +0xb8, jumpOriginZ +0xbc | jump verified; landing pain events mapped |
| mantle | retained Mantle_Check runs every frame; **never starts in any run** | mantle flag, mantle block, EF_MANTLE (added this session) | **open**: 90 brushes carry CONTENTS_MANTLE, so surfaces exist; my runs were at a tall wall, not a ledge. mantle_debug is now forced on in developer builds so the retained check prints its failure reason on a real ledge |
| ladder | retained | PMF ladder, ladder vector | unverified on this map |
| dive | yes (codol_dive.c) | dive bit, jumpTime, EV_DTP_LAND | implemented and verified |
| ADS | yes | ADS bits 0x40/0x10 now published | verified |
| fire | yes | weapon phases, events, ammo arrays | verified |
| reload | yes | reload phases, ammo | verified |
| weapon switch | yes | raise/drop phases | switching by keys 1/2 did not change the weapon in the driver run; bind unknown, unverified |
| frag / smoke | yes | projectile events (bounce, explode) | fixed this session, verified no rejection |
| tactical | yes (raw-word offhand selector) | offhand weapon states | implemented; needs a live throw to verify |
| melee | yes | melee events, weapon states | melee-end animation now translated |
| damage taken | yes | damage indicator fields +0x17c..+0x188 now published | needs a live hit to verify on the HUD |
| death / respawn | yes | pm_type, teleport toggle | verified; fall death fixed |
| player animation | yes | legs/torso timers and indices +0xc0..+0xcc now published | unverified visually |
| view lock / linked weapon | retained | +0x1ac/+0x1b0/+0x1ec never published | killstreak turrets, unverified |
| perk HUD icons | script | +0x4b0..+0x4b8 never published | unverified |

## 3. Confirmed this session (before the audit)

Connect, secure profile, class selection, spawn, walk, sprint, crouch, jump,
fire, reload, grenade, melee events, fall damage death, map restart with
profile re-attach, match end bookkeeping. Rubber-banding fixed (client and
server speeds agree exactly; origin re-assert off by default).

## 4. Remaining gaps

1. Mantle: the retained Mantle_Check never starts. 90 CONTENTS_MANTLE brushes
   exist (nearest to spawn 4246,-732 is brush 13918 at 3948,-532, top z 52).
   Developer builds force mantle_debug on and trace every attempt.
2. Weapon switching by key: verify the bind and the raise/drop publication.
3. Fourth equipment slot (0x400000) and marker slot (0x1000000): dropped.
4. View lock, linked weapon entity and perk HUD icon fields: never published.
5. Live verification still owed for: damage indicators on the HUD, tactical
   throw, ladder, dive feel from the client's side.
