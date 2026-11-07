# MP perk support audit (2026-09-25)

Scope: every MP row of `mp/coPerkStatsTable.csv` (ids 1-42, 88-91) and every
modifier it names. Read-only audit of native source, `bin/home/codol_rawfiles`
GSC, and the C1 client binary (via `tools/codol_c1_disasm.py`). Nothing was
built, run or edited apart from this file.

Verdicts: **WORKING** = a consumer exists and the selected perk reaches it;
**PARTIAL** = consumer exists but it is incomplete or ignores the table value;
**MISSING** = nothing on the server acts on it; **CLIENT-ONLY** = C1 applies it
from the published ability mask/values, and the server has nothing
authoritative to do. "(uncertain)" means the evidence is incomplete, as the
notes explain.

## 1. How a selected perk reaches the modifiers (verified)

* **Loadout.** `_class.gsc::giveLoadout` reads the profile class through the
  native `codol_getLoadoutPerk` / `codol_getLoadoutItem` (custom classes,
  `_class.gsc:476-499`), or the bot CSV, or the class table. It calls
  `_clearPerks` (`_class.gsc:633`). If this is the life's first spawn and the
  death streak has reached the table's column-6 threshold, it gives the
  deathstreak (`:646-661`). Then it runs `loadoutAllPerks` (`:786-812`), which
  gives perk1-3 and then every pro perk (column 8) for which
  `isItemUnlocked(upgrade)` is true. Bots never get pro perks (`:799`).
  Profile equipment goes through `codol_giveEquipment` (`:173-202`). That path
  calls `givePerk` only for `specialty_blastshield` and
  `specialty_tacticalinsertion`.
* **`givePerk` -> `_utility::_setPerk` (`_utility.gsc:1833-1844`)** always calls
  the native `setPerk`, records `self.perks[name]` (used by `_hasPerk`) and
  runs the IW4 `level.perkSetFuncs` callback.
* **Native `setPerk`** (`codol_script_perks.c:9-71`) resolves the name in
  coPerkStatsTable. It stores the id in that row's slot (perk1-4, upgrade1-3,
  equipment) and calls `CODOL_CommitPerkState` (`codol_perk_runtime.c:104-117`).
  A name missing from the table is silently treated as absent
  (`codol_script_perks.c:39-54`). `hasPerk` is an exact slot-ID comparison.
  Each slot holds one ID, so a pro perk exists only because its upgrade-slot
  row was set separately.
* **Aggregation** (`codol_perk_effects.c:55-140`, header
  `codol_perk_effects.h:15-23`): for each modifier id, value =
  `default + sum(selected deltas)`, clamped to the table's min and max. Every
  referenced modifier sets its mask bit. Values that have a wire slot go into
  `abilities.values[slot]`. Server-only modifiers (clientside 0), plus numeric
  clientside modifiers that have no slot (only `modPistolDeath`), also go into
  `server_values[id]`. `merge()` (`codol_perk_runtime.c:29-49`) overlays these
  on the script-owned abilities (`setAbilityModifier*`). Script ownership wins
  for a value slot the script has written.
* **Readers.**
  * `HasAbilityModifier` reads the effective mask
    (`codol_script_abilities.c:43-47`).
  * `getSelectedPerkModifierValue` returns only `server_values`
    (`codol_perk_runtime.c:55-65`, `codol_script_abilities.c:67-86`). It is
    undefined for slotted clientside values.
  * Native C consumers read `ext->abilities` through
    `CODOL_GetActiveAbilityValue`.
* **Publication.** The owner's playerstate extension carries masks and values
  (`codol_playerstate_ext.c:1009-1020`). Every client's masks and values are
  republished each frame into clientState (`_g_active_mp.asm:451-461` ->
  `codol_clientstate_ext.c:68-73`, written at `:95-115`). This matches C1
  `G_UpdateClientInfo` 0x50d380..0x50d3b6. C1 copies them into its
  clientInfo at 0x46c988..0x46c9ec (ci+0x68..0x74, values at ci+0x78).
  Client-side consumers of *other* players' abilities therefore get correct
  data.

**Units and aggregation.** The additive, clamped policy is table-consistent. No
C1 producer that performs this aggregation has been recovered (see
`CODOL_PERK_ABILITY_AUDIT_20260914.md`). Every value it produces matches the
unit that its C1 consumer applies:

| Modifier | Value | How C1 applies it |
| --- | --- | --- |
| ADS | 1.5 | Multiplies elapsed msec (0x41875b) |
| Reload | 2 | Multiplies msec (0x41abb6) |
| Weapon switch | 2 | Multiplies msec (0x41ac09) |
| Offhand, weapon recovery | 2 | C1 *divides* the phase time (0x41c35e, 0x41d19c) |
| Sprint time | 10 s | Seconds (0x40e993) |
| Sprint force recover | 2 s | Multiplied by 1000 (0x40f60c) |
| Extra breath | +5 s | Multiplied by 1000 (0x4188bb) |
| Spread | 0.65 | Multiplier (0x422736) |
| View kick | 0.5 | Multiplier (0x411190) |
| Footstep ally / enemy | 0.1 / 2 | Volume multipliers (0x44f5b9 / 0x44f5d0) |

For the server-only modifiers the GSC consumers apply these values:

* 0.5 explosive damage, 0 fall damage, -1 killstreak shift.
* 10 s combat high (default 2 + 8).
* 20 s final stand, 10 s pistol death.
* 0.3 stun and flash protection.

Two semantic doubts remain:

* `modObjectiveUseTimeScale` aggregates to 1 + 0.5 = **1.5**. A time scale
  above 1 would slow the holder down, so either the value is a rate or the
  "default + delta" policy is wrong for this row. Unverified.
* Hacker (perk3) and Engineer (perk2) can both be selected. Their
  `modCaptureEnemyEquipmentTime` deltas stack to 4-2-2 = **0 s**, and their
  `modObjectiveUseTimeScale` deltas stack to 2.0. Unverified.

## 2. C1 native ability readers (evidence base for the verdicts)

A linear sweep of C1 `.text` found every direct read of the ability mask
`ps+0x4d0..0x4dc`. Only these read it:

* **Shared BG / pmove**, which runs on both client and server:
  * ids 0 (0x40e993), 1 (0x41abb6), 2 (0x40c96e, item grab), 6 (0x422736)
  * ids 9 (0x40a032), 10 (0x41875b, 0x41b4ea), 11 (0x41d178), 13 (0x4188bb)
  * ids 22 (0x41ac09), 23 (0x41ac92), 26 (0x418a29, 0x421f2e, 0x422e26)
  * ids 27 (0x41537d), 28 (0x41c33d, 0x41c4cd, 0x41c696, 0x41c8f8)
  * ids 33 (0x40f60c, 0x40f65d), 34 (0x4093ca), 39 (0x41c564)
  * ids 3 and 5, which no MP perk uses
* **Game server**:
  * 8 (0x51c1c4, last stand), 21 (0x5208b7, martyrdom)
  * 2 (0x5288a6, scavenger bag mask), 20 (0x57c126, turret target reject)
  * The script builtin (0x518723) and the UI expression (0x5de619)
* **Client**:
  * id 31 at 0x411190, whose only caller is cg 0x45ce12
  * Other players' clientInfo: id 19 (0x43fe0a, 0x45b829)
  * Compass actors: 24 and 40 (0x4348c2, 0x4348ec)
  * The local player's 37 and 38 (0x4348d8..0x4348e8)
  * Footsteps 15/16/17/36 (0x44f54f..0x44f618)
  * Weapon anim rates 1/22/23/28 (0x47ae8f..0x47b91b)

No C1 reader was located for ids 7, 12, 14, 18, 25, 30, 32, 35 or 41. The
search covered ps masks, clientInfo, actor copies, direct slot-value offsets
and the value-slot helpers 0x402f20/0x403070. None of them is read by C1's own
game-server code, so they are either client or UI effects, or C1 server-GSC
effects. Those rows are marked "(uncertain)".

## 3. Per-(perk, modifier) table

Value = table delta (effective value after aggregation in brackets). cs = clientside column.

| Perk | Modifier | Value | cs | Consumer | Verdict | Notes |
|---|---|---|---|---|---|---|
| 1 specialty_bulletaccuracy (perk3) | modBulletSpreadScale | -0.35 (0.65) | 1 | none | MISSING | Server bullet spread comes from the retained `BG_GetSpreadForWeapon`, which tests the legacy IW3 perk bit `ps+0x5fc & 2` (`_bg_weapons.asm:2778`); nothing sets that bit under CODOL_SERVER (setperk is `CODOL_Scr_SetPerk`, `scr_vm_main.c:701`). C1 0x422736..0x42276d multiplies min *and* max spread by value6. The client crosshair shrinks but the server's hit traces do not tighten. |
| 2 specialty_marathon (perk1) | modSprintTime | 6 (10 s) | 1 | `codol_sprint_state.c:146-157` | WORKING | C1 0x40e990. |
| 3 specialty_fastreload (perk1) | modReloadSpeedScale | 1 (2.0) | 1 | `codol_weapon_state.c:182-191` | WORKING | Applies only to weapons with inheritsPerks metadata (C1 def+0xbc2, 0x41abc7). |
| 4 specialty_scavenger (perk1) | modScavenger | flag | 1 | `codol_script_player_builtins.c:642-690` (bag clientMask + touch gate); `_weapons.gsc:825-895`; `_damage.gsc:632` | WORKING | Matches C1 0x528890 and BG grab 0x40c96e. |
| 5 specialty_flakjacket (perk2) | modArmorExplosiveDamageScale | -0.5 (0.5) | 0 | `_perks.gsc:310,338-342` | WORKING | Uses `_utility::isExplosiveDamage` coverage, including direct MOD_GRENADE/PROJECTILE. C1's exact MOD set is unverified. |
| 6 specialty_paint (perk1) | modExplosivePaint | flag | 1 | none | MISSING | The client only *displays* paint. C1 0x4348c2..0x43492b shows an enemy when (a) the enemy has ability 24 modRadarArrow and (b) the local player has 37/38 or the enemy has 40. Value slot 13 = 0 shows the enemy to all such viewers; value N shows it only to clientNum N-1. No server GSC sets modRadarArrow on a victim hit by a painter's explosives. |
| 7 specialty_lightweight (perk1) | modMoveSpeedScale | 0.1 (1.1) | 0 | `codol_perk_runtime.c:118-131` via `_g_active_mp.asm:404-407`; `codol_pmove_c1_ground.c:532` | WORKING | Side issue: `_damage.gsc:2308-2311` (dieHard revive) sets `moveSpeedScaler=1.07` for lightweight, which stacks with the native 1.1. |
| 8 specialty_hardline (perk2) | modKillstreakShift | -1 | 0 | `_class.gsc:1047-1117` (streak keys + HUD targets) | WORKING | setKillstreaks runs after loadoutAllPerks (`_class.gsc:665-668`). |
| 9 specialty_coldblooded (perk2) | modNoRadar | flag | 1 | none (server) | CLIENT-ONLY (uncertain) | Mask published per frame to all clients. No C1 reader located. `_tank.gsc:1099` still gates *tank* targeting on the IW4 name `specialty_coldblooded`. |
| 10 specialty_quickdraw (perk2) | modADSSpeedScale | 0.5 (1.5) | 1 | `codol_pmove_c1.c:512-530` | WORKING | Minor gap: the C1 ADS-fire-only delay 0x41b4ea divides by value10. The retained PM_Weapon path for adsFireOnly weapons does not. |
| 11 specialty_stalker (perk3) | modMoveFastWhileAiming | flag | 1 | none | MISSING | C1 PM_UpdateAdsFlag 0x415330..0x415391 skips setting PMF 0x40 when ability27 is set. Native `update_ads_flag` (`codol_pmove_c1.c:495-508`) always sets it, so the server applies the 0.4 ADS scale and the ADS weapon scale (`codol_pmove_c1_ground.c:508-523`) while the C1 client predicts full speed. This is a prediction desync. |
| 12 specialty_heartbreaker (perk3) | modNoHeartbeat | flag | 1 | none (server) | CLIENT-ONLY (uncertain) | Heartbeat sensor is a client HUD. No C1 reader located. |
| 12 | modNoSentryGuns | flag | 1 | none | MISSING | C1 target validator 0x57ca30 calls 0x57c0f0 at 0x57cb05. That function rejects a client target whose ps ability20 is set (0x57c126..0x57c132) and also rejects eFlags 0x10 targets. Native `TurretAuto_ValidateTarget` (`codol_script_turret_target.cpp:1284-1330`) and `TurretTarget_ValidTarget` (`:801-812`) have no such check. Sentry killstreaks use this native path (`_autosentry.gsc:166`). |
| 12 | modNoHelicopter | flag | 0 | `_helicopter.gsc:481,1047` | WORKING | |
| 12 | modNoAirplane | flag | 0 | `_harrier.gsc:768` | WORKING | |
| 13 specialty_detectexplosive (perk3) | modDetectExplosive | flag | 1 | `_weapons.gsc:295-404` (IW4 bombsquad models shown via `_hasPerk("specialty_detectexplosive")`) | WORKING | IW4 script semantics. No C1 reader located, so any additional C1 client highlight is unknown. |
| 13 | modDetectTurrets | flag | 1 | none | MISSING (uncertain) | Intended: see enemy turrets / sentries. T5 reference: `_weaponobjects.gsc:2403-2405` (showenemyequipment sees sentry, turret, TI). The C1 client may do this itself, but no reader was located. |
| 14 specialty_pistoldeath (perk3) | modPistolDeath | 10 | 1 (no slot; stored server-side) | Entry gate `codol_script_laststand.c:100-109` via `_g_client_script_cmd_mp.asm:1454-1456` (C1 0x51c1c4); duration `_damage.gsc:1778,1783-1791` | WORKING | |
| 15 specialty_hacker (perk3) | modCrateTrap | flag | 0 | none | MISSING | T5 hacker booby-trapped crate: `_supplydrop.gsc:1226-1227,1772`. |
| 15 | modCaptureEnemyEquipmentTime | -2 (2 s) | 0 | none | MISSING | T5 hack enemy equipment: `_weaponobjects.gsc:1311,1519`. `equipment/_pickup.gsc` has no enemy capture. |
| 15 | modObjectiveUseTimeScale | 0.5 (1.5) | 0 | none | MISSING | `objectiveScaler` exists (`_gameobjects.gsc:1439-1449`, `_playerlogic.gsc:590,1204`) but only IW4 saboteur writes it (`_perkfunctions.gsc:348`). The units question is in §1. |
| 16 specialty_holdbreath (upgrade3) | modDamageViewKickScale | -0.5 (0.5) | 1 | client C1 0x411190 (only caller cg 0x45ce12) | CLIENT-ONLY | Purely a view effect. |
| 17 specialty_fastmantle (upgrade1) | modSprintForceRecoverTime | 1 (2 s) | 1 | `codol_sprint_state.c:183-193` | WORKING | Name/effect swap: this row is sprint recovery, not mantle (C1 0x40f60c). |
| 18 specialty_quickswap (upgrade1) | modWeaponSwitchSpeedScale | 1 (2.0) | 1 | `codol_weapon_state.c:193-194` | WORKING | C1 0x41ac09 covers C1 states 1-5. Native maps its own phases 1-4; the state translation was not re-verified in this audit. |
| 19 specialty_extraammo (upgrade1) | modExtraAmmo | 30 | 0 | `_class.gsc:671,686` (`hasPerk(...)` -> `giveMaxAmmo`) | PARTIAL | IW4 policy. Value 30 is never read and its unit is unknown (`CODOL_EXTRA_AMMO_UNITS_20260914.md`). |
| 19 | modExtraExplosive | flag | 0 | none | MISSING | Localized PERKS_DESC_SCAVENGER_PRO: extra *initial* frag/semtex, which cannot be resupplied. `codol_giveEquipment` only calls `giveStartAmmo`. The grant quantity is unknown. |
| 20 specialty_flakjacket_pro (upgrade2) | modGasMask | flag | 0 | `equipment/_tabun.gsc:177` | WORKING | |
| 21 specialty_paint_pro (upgrade1) | modBulletPaint | flag | 1 | none | MISSING | Same paint mechanism as row 6, triggered by bullet damage. |
| 22 specialty_fastsprintrecovery (upgrade1) | modFastMantle | flag | 1 | none | MISSING | C1 0x40a02c..0x40a067 sets `mantleState.flags \|= 0x40` for ability9 and picks the anim table `0x15088bc[bit6]`, i.e. the fast mantle anims. Native `mantle_start` (`codol_pmove_c1_mantle.c:158-176`) never sets 0x40 and has one anim set, so mantle duration and origin path differ from C1's prediction. Name swap: this is Lightweight Pro, not "fastmantle". |
| 22 | modFallDamageScale | -1 (0) | 0 | `_perks.gsc:321-342`; `_damage.gsc:1239-1243` (`if (!iDamage) return`) | WORKING | `emitFallDamage` (`_damage.gsc:1135`) still fires before scaling. The IW4 name `specialty_falldamage` is never set. |
| 23 specialty_rollover (upgrade2) | modDeathstreakShift | -1 | 0 | `_class.gsc:648-651` | WORKING | Hard-codes -1 via `getPerkUpgrade(...) == "specialty_rollover"`. Does not read the table value. |
| 23 | modKillstreakAssists | 2 | 0 | none | MISSING | `_gamescore.gsc:364-386 processAssist` never advances `cur_kill_streak`. IW4 has no equivalent; the intended semantics (N assists = 1 kill) are an MW3-style inference and uncertain. |
| 24 specialty_spygame (upgrade2) | modNoThermal | flag | 1 | client C1 0x43fe0a / 0x45b829 (other players' ci+0x68 bit id19) | CLIENT-ONLY | Server publishes per frame. Verified. |
| 24 | modNoCrosshair | flag | 1 | none (server) | CLIENT-ONLY (uncertain) | No C1 game-server reader. `codol_lookat.c` has no gate (C1 has none either). Client reader not located. |
| 25 specialty_fastoffhand (upgrade2) | modOffhandSpeedScale | 1 (2.0) | 1 | none | MISSING | C1 offhand phases 0x41c33d, 0x41c4cd, 0x41c696/0x41c6cf and 0x41c8f8 set phase time = ftol(time / value28). The native offhand machine (`codol_weapon_state.c`, `weapon_frame_msec` `:172-219`) has no ability28 path. |
| 25 | modWeaponRecoveryTimeScale | 1 (2.0) | 1 | none | MISSING | C1 sprint-out 0x41d162..0x41d1af: state25 time = ftol(sprintOutTime / value11). No native reader. |
| 26 specialty_delaymine (upgrade3) | modFootstepVolumeScaleEnemy | 1 (2.0) | 1 | client C1 0x44f5d0 | CLIENT-ONLY | Verified. |
| 26 | modFootstepVolumeScaleAlly | -0.9 (0.1) | 1 | client C1 0x44f5b9 | CLIENT-ONLY | Verified. |
| 26 | modInvalidCounterUav | flag | 1 | none | MISSING (uncertain) | `ps->radarBlocked` is server-produced from the team counter-UAV block (`codol_script_radar.c:47-67`) with no exemption. C1 game server has no ability35 reader, so C1 either ignores radarBlocked client-side or exempts in server GSC. Unresolved. Name clash: IW4 scripts treat `specialty_delaymine` as the *claymore delay* perk (`_weapons.gsc:1492`, `_bouncingbetty.gsc:176`), so Stalker Pro holders wrongly get a 3 s claymore delay. |
| 27 specialty_quieter (upgrade3) | modQuieter | -0.9 | 1 | none | CLIENT-ONLY (uncertain) | No reader located anywhere, including C1 (no call with id 14). |
| 27 | modAntiPaint | -0.5 (0.5) | 0 | none | MISSING | Should shorten or scale paint on the holder. Depends on the missing paint producer. |
| 28 specialty_selectivehearing (upgrade3) | modDrawAirSupport | flag | 0 | none | MISSING (uncertain) | Server-only flag, so the server must publish enemy air support to the holder's minimap. Mechanism unknown. |
| 28 | modAlliesShareDetectionRange | 500 | 0 | none | MISSING (uncertain) | Intended: teammates within 500 units share the holder's detection (bombsquad). Unverified. |
| 29 specialty_laststandoffhand (upgrade3) | modFinalStandTime | 10 | 0 | `_damage.gsc:1723` only reads it on the *final stand* path; offhands are allowed by name at `_damage.gsc:1773` | PARTIAL | The value 10 is unused for the pistol last stand. With Final Stand also selected it inflates final stand to 30 s. Intended C1 meaning unverified. |
| 30 specialty_hackerpro (upgrade3) | modOpenCrateAsOwner | flag | 0 | none | MISSING | `_airdrop.gsc:1199-1216` non-owner capture is always 3000 ms; owner capture is 500 ms (`:1236`). |
| 31/32/33/36/37 frag, semtex, throwingknife, claymore, c4 (equipment) | none | - | - | `codol_giveEquipment` / `givePerk` | n/a | No modifiers. |
| 34 specialty_tacticalinsertion (equipment) | modTacticalInsertion | flag | 0 | `_class.gsc:185-189` -> `_perkfunctions.gsc:745-760` (flare + monitorTIUse) | WORKING | Script-driven. The flag itself is not read. |
| 35 specialty_blastshield (equipment) | modBlastShield | flag | 0 | `_perkfunctions.gsc:701-733`; damage `_perks.gsc:311-316` (45 % taken) | PARTIAL | The toggle waits for the script notify `"empty_offhand"`, and no native producer of it was found (only the EV_EMPTY_OFFHAND name exists). No offhand weapon is given for it (`_class.gsc:180-183`). C1 activation is unverified. |
| 38 specialty_copycat (perk4) | modCopyPerks | flag | 0 | `_damage.gsc:234-235,792`; `_class.gsc:445-471` | WORKING | IW4 script path. The killcam copy button is not live-verified. |
| 39 specialty_combathigh (perk4) | modCombatHighTime | 8 (10 s) | 0 | `_perkfunctions.gsc:127`; damage/3 `_perks.gsc:344-372` | WORKING | |
| 40 specialty_grenadepulldeath (perk4) | modGrenadePullDeath | flag | 1 | `codol_script_laststand.c:111-120` via `_g_combat_mp.asm:199-205` (C1 0x5208b7) | WORKING | |
| 41 specialty_finalstand (perk4) | modFinalStandTime | 20 | 0 | `_damage.gsc:1711-1723`; entry via `setFinalStand` -> script `setAbilityModifier("modPistolDeath")` (`_perkfunctions.gsc:315-324`) | WORKING | |
| 42 specialty_callforsupport (equipment) | modCallForSupport | flag | 0 | none | MISSING | Not referenced by any GSC. Intended behaviour unknown and needs C1/localization evidence. |
| 88 specialty_marksman (perk3) | modIncreaseCrosshairRange | 4000 | 1 | none (server) | CLIENT-ONLY (uncertain) | C1 game server has no reader. The server lookat range is fixed at 8192 (`codol_lookat.c:133`). Client reader not located. |
| 88 | modMarksman | flag | 1 | none (server) | CLIENT-ONLY (uncertain) | As above. |
| 89 specialty_marksmanpro (upgrade3) | modExtraBreathTime | 5 | 1 | `codol_pmove_c1_breath.c:265-272` | WORKING | C1 0x4188bb. |
| 90 specialty_engineer (perk2) | modDelayTriggeredExplosive | flag | 0 | none | MISSING | The delay exists only under the wrong name (`specialty_delaymine`, `_weapons.gsc:1492`, `_bouncingbetty.gsc:176`). |
| 90 | modCaptureEnemyEquipmentTime | -2 | 0 | none | MISSING | Stacks with Hacker (§1). |
| 90 | modObjectiveUseTimeScale | 0.5 | 0 | none | MISSING | |
| 91 specialty_engineerpro (upgrade2) | modStunProtectionScale | -0.7 (0.3) | 0 | `_weapons.gsc:2135` | WORKING | |
| 91 | modFlashProtectionScale | -0.7 (0.3) | 0 | `_flashgrenades.gsc:135` | WORKING | |

**Counts (60 perk/modifier pairs):**

| Verdict | Count | Notes |
| --- | --- | --- |
| WORKING | 24 | |
| PARTIAL | 3 | |
| CLIENT-ONLY | 10 | 6 of them uncertain |
| MISSING | 23 | 5 of them uncertain in exact semantics |

## 4. Script names versus the loadout

* **IW4 perk names that scripts check but that C1's table cannot set** (always
  false):
  * `specialty_armorpiercing`, `armorvest`, `bling`, `bulletdamage`
  * `c4death`, `dangerclose`, `empimmune`, `explosivedamage`
  * `extendedmelee`, `falldamage`, `fmj`, `gpsjammer`
  * `localjammer`, `omaquickchange`, `onemanarmy`
  * `_specialty_blastshield`, which is a script-only toggle flag and fine

  These are dead branches rather than missing effects, except where they
  shadow a C1 effect: the fall-damage branch (`_perks.gsc:324`) and explosive
  damage.
* **Same name, different meaning:**
  * `specialty_delaymine`: IW4 claymore delay vs C1 Stalker Pro footsteps and
    counter-UAV. See rows 26 and 90.
  * `specialty_coldblooded` in `_tank.gsc:1099`: IW4 AI immunity vs C1
    radar-only.
  * `specialty_lightweight` 1.07 at `_damage.gsc:2308`.
* **Name/effect swaps in the C1 table itself** are handled correctly because
  the native layer is table-driven:
  * Row 17 `specialty_fastmantle` = sprint recovery
  * Row 22 `specialty_fastsprintrecovery` = fast mantle + no fall damage
* **Dead files.** `perks/_deathstreaks.gsc` and `killstreaks/_codol.gsc` are
  not referenced by any script. They describe removed Python host bridges
  (`magicGrenade`, `giveDeathstreakHealth`, `setCopycatLoadout`). Deathstreaks
  actually run through `_class.gsc:646-661` plus the native martyrdom and
  last-stand gates.

## 5. Pro-perk (upgrade) unlock path

`loadoutAllPerks` (`_class.gsc:801-811`) and `getPerkUpgrade` (`:771-784`) give
the column-8 upgrade when `isItemUnlocked(upgrade)` is true. That is native
`codol_script_unlock.c:19-45` over `mp/unlocktable.csv`, the secure profile,
rankTable and allChallengesTable.

* **Gated by an IW4 challenge.** `unlocktable.csv` lists fastmantle,
  holdbreath, extraammo, fastsprintrecovery, rollover, spygame, delaymine,
  quieter, selectivehearing and laststandoffhand, each gated on an IW4-named
  challenge such as `ch_marathon_pro`. Delaymine is gated on
  `ch_scrambler_pro`, an IW4 mapping.
* **Always unlocked.** Quickswap, flakjacket_pro, paint_pro, fastoffhand,
  hackerpro, marksmanpro and engineerpro are *not listed*, so they are always
  unlocked (IW4 semantics).
* **Unverified.** Whether C1 unlocks pros through these challenges or through
  a purchase / playerdata flag was not established.
* **Risk.** `isItemUnlocked` raises `Scr_Error` when the profile does not
  satisfy the table's requirement semantics (`codol_script_unlock.c:40-42`).
  If that ever fires inside `loadoutAllPerks`, it aborts the loadout.
* Bots never receive pro perks (`_class.gsc:799`).

## 6. Implementation work needed

### Movement / pmove
1. **Stalker, modMoveFastWhileAiming (27).** In `update_ads_flag`
   (`codol_pmove_c1.c:495-508`), do not set PMF 0x40 when the effective mask
   has id 27. Evidence: C1 0x41537d..0x41538e. The effect then follows through
   `PM_CmdScale` (`codol_pmove_c1_ground.c:508-523`) and the footstep ADS test
   (`:1161`, `:1213`), as in C1.
2. **Lightweight Pro, modFastMantle (9).** In `mantle_start`, set
   `mantleState.flags |= 0x40` for ability 9. Load the second mantle
   transition/anim set that C1 indexes by that bit (`0x15088bc[bit6]`, used at
   0x40a060..0x40a067 and in `mantle_up_ms` / `mantle_total_ms`). Evidence:
   C1 0x40a02c..0x40a07b.

### Weapon timing
3. **modOffhandSpeedScale (28).** Divide each offhand phase time by value28
   with C1 `ftol`. Evidence: C1 0x41c33d, 0x41c4cd, 0x41c696, 0x41c6cf and
   0x41c8f8, each `fild time; fdiv value; call 0xae0410`.
4. **modWeaponRecoveryTimeScale (11).** Divide the sprint-out (state 25)
   duration by value11. Evidence: C1 0x41d178..0x41d1af.
5. **modBulletSpreadScale (6).** Replace the legacy perk-bit branch in
   `BG_GetSpreadForWeapon` (`_bg_weapons.asm:2778`) with the C1 ability
   multiply of min *and* max spread. Evidence: C1 0x422736..0x42276d. The
   other legacy `ps+0x5fc` perk tests are equally unreachable under CoDOL:
   `_bg_weapons.asm:6623` (breath), `:6844` (reload), `:8401` (rate of fire)
   and `_bullet.asm:724,843` (penetration). Audit or remove them together.
6. **Minor: quickdraw on adsFireOnly weapons.** Scale the hip-to-ADS fire
   delay by value10. Evidence: C1 0x41b4c0..0x41b52a.

### Damage
7. **Blast shield activation.** Confirm the C1 activation, then provide the
   `"empty_offhand"` producer or an offhand item. Evidence: IW4
   `_perkfunctions.gsc` blastshieldUseTracker. The damage factor already
   exists.
8. **Last Stand Pro, modFinalStandTime 10 on row 29.** Decide the C1
   semantics (localized PERKS_DESC string) and consume it in the pistol-death
   path. Avoid the 20+10 stacking into final stand unless that is intended.

### Killstreak system
9. **modNoSentryGuns (20).** In `TurretAuto_ValidateTarget` /
   `TurretTarget_ValidTarget`, reject client targets whose effective abilities
   include 20. Evidence: C1 0x57c0f0 (0x57c11c..0x57c143), called from
   validator 0x57ca30 at 0x57cb05 and also from 0x57c565, 0x57df63 and
   0x6ef9cc. Check those other turret paths too.
10. **modKillstreakAssists (23).** In `processAssist`, count assists for
    holders and credit one killstreak kill per `value` assists. The
    semantics are an inference; get C1 or alpha0022 evidence first.
11. **`_tank.gsc:1099`** should use the heartbreaker abilities, not
    `specialty_coldblooded`. Which modifier covers ground vehicles is
    uncertain.

### Radar / visibility
12. **Paint: modExplosivePaint (37), modBulletPaint (38), modAntiPaint (94).**
    In the damage callback (`_damage.gsc` Callback_PlayerDamage /
    `cac_modified_damage`), when the attacker has ability 37 and the damage is
    explosive, or 38 and the damage is a bullet:
    * `victim setAbilityModifier("modRadarArrow")`
    * `setAbilityModifierValue("modRadarArrow", attackerClientNum+1)`, or 0 to
      show the victim to everyone
    * clear it after a duration scaled by the victim's
      `getSelectedPerkModifierValue("modAntiPaint")`

    The duration is unknown. The client side is proven at C1
    0x4348c2..0x43492b.
13. **modInvalidCounterUav (35).** Determine whether C1's client ignores
    `radarBlocked` for ability 35. If not, exempt holders from the team
    counter-UAV block in `CODOL_PublishClientRadar`
    (`codol_script_radar.c:47-67`), but not from EMP.
14. **modDrawAirSupport (95), modAlliesShareDetectionRange (80) and
    modDetectTurrets (25).** Semantics unverified. Reference: T5
    `_weaponobjects.gsc:2380-2405` (detect explosive / showenemyequipment
    visibility). The existing IW4 bombsquad is `_weapons.gsc:295-404`.
15. **Optional confirmation of the uncertain CLIENT-ONLY rows** (ids 7, 12,
    14, 18, 32, 41) with a targeted C1 client search. The server already
    publishes the masks every frame.

### Equipment / crates
16. **modCrateTrap (61) and modOpenCrateAsOwner (78).** In `_airdrop.gsc`
    capture:
    * Use the owner time of 500 ms for crateOpenAsOwner holders.
    * Let a CrateTrap holder who captures an enemy crate re-arm it as a
      booby trap.

    Reference: T5 `_supplydrop.gsc:1226-1227,1772`.
17. **modCaptureEnemyEquipmentTime (62).** Let holders hack or capture enemy
    equipment in `modCaptureEnemyEquipmentTime` seconds. Reference: T5
    `_weaponobjects.gsc:1311,1519`, where the hacker trigger uses
    `SetPerkForTrigger`. The native `SetPerkForTrigger` equivalent needs
    checking.
18. **modDelayTriggeredExplosive (92).** Replace the
    `_hasPerk("specialty_delaymine")` claymore and betty checks
    (`_weapons.gsc:1492`, `_bouncingbetty.gsc:176`) with
    `HasAbilityModifier("modDelayTriggeredExplosive")` on the *triggering*
    player. This also removes the Stalker Pro mis-grant.
19. **modExtraExplosive (93).** Give +N initial frag/semtex after
    `codol_giveEquipment`, never refilled by scavenger. The existing exclusion
    is at `_weapons.gsc:846-849`. N is unknown.
20. **modExtraAmmo 30.** The unit is unknown and IW4 `giveMaxAmmo` is the
    current fallback.
21. **modCallForSupport (68).** The behaviour is unknown; needs C1
    localization and script evidence.

### Deathstreaks
22. Functionally working: Painkiller, Martyrdom, Final Stand and Copycat,
    plus the rollover shift. Clean-up items:
    * Delete or mark the unreferenced `perks/_deathstreaks.gsc`, whose header
      describes a nonexistent host-bridge design.
    * Optionally read modDeathstreakShift instead of the hard-coded -1 at
      `_class.gsc:650`.

### Other
23. **modObjectiveUseTimeScale (77) for hacker and engineer.** Set
    `self.objectiveScaler` from the selected value at spawn, next to
    `_playerlogic.gsc:590/1204`. It feeds `_gameobjects.gsc:1439-1449`. First
    resolve whether 1.5 means rate or time (§1).
24. **Lightweight revive.** Drop the 1.07 at `_damage.gsc:2308-2311`. The
    native perk producer owns lightweight speed.
25. **Pro-perk unlock.** Confirm C1's pro unlock source (§5). Consider making
    `isItemUnlocked` failure non-fatal inside `loadoutAllPerks`.
