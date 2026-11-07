# Native death and deathstreak gates

Read-only source/offline C1 audit, 2026-09-14. Parent owns implementation.
No tests, builds, runtime writes, launches or UI actions were performed.

## Proven C1 gates and mode producers

| Path | C1 evidence | Native gap found |
|---|---|---|
| Lethal last-stand entry |51c1a8 health<=0;51c1bb client3a38==0;51c1c4..d0 ability8 `(ps4d0>>23)&1`| C helper and direct damage assembly still use legacy perk7 |
| Last-stand grace |51c1d6 setsdown1;51c1f1..f7 stores level.time+500 | Existing native grace500 matches; selected numeric10 is not this grace |
| Martyrdom activation |5208b7..c2 ability21 `(ps4d0>>10)&1` | Retained perk6 gate lacks current producer |
| player_die admission |520df8..520e07 permits modes0,1,7 | Retained entry permits0,1,6, rejecting C1 laststand7 |
| Immediate death mode |520e90..520e9b stores9 if oldmode1, otherwise8 | Retained producer stores8 if1, otherwise7 |

The last two differences require changing native producer/consumer semantics,
not a snapshot translation. A later ClientEndFrame correcting the mode does
not make the immediate death path correct.

C1 also excludes weapon flag800 at520e0d. Retained player_die instead checks
otherFlags+14 bit2. This is a separate representation/provenance question;
do not change that gate merely because the neighboring mode gates differ.

## MOD13 is suicide in C1; MOD12 is suicide in retained native source

C1 death grenade helper520790 excludes argument13 at5208a7.
At577619 it interns literal `MOD_SUICIDE`;577632 stores that result in24ee082.
The table atcd4940 points to24ee082 at index13. Native `g_shared.h` and
`g_combat_mp.cpp::modNames` instead put suicide at12 and trigger-hurt at13.
Keep the native suicide exclusion semantically correct until the full native
MOD enum, producers and script consumers are migrated together. Changing the
comparison to13 alone would suppress martyrdom on trigger-hurt instead.

The C1 MOD table differs beyond a constant shift: it includes
`MOD_EXPLOSIVE_BULLET` and `MOD_GAS`, and omits native `MOD_TELEFRAG` in this
17-entry table. Its callback parser562895 accepts0..16; native currently0..15.
This audit does not authorize inserting entries without updating producers.

## Grenade drop already matches several exact C1 parameters

C1 `5208c8` uses literalc53cd0=`frag_grenade_short_mp`. Native
`perk_grenadeDeath` defaults to exactly that name (`g_sv_main.c`,
`bg_perks_mp.cpp`). C1 uses definition654 fuse, randomXYZ scaled160, spawn
positionZ+40, then5309d0 launch. Constantsc853a8/c84a88 decode as doubles
160/40. Retained player_die_70 uses the same160/40 and the native definition's
mapped fuse field3ec before `G_FireGrenade`. Thus no new name or launch-speed
substitute is justified by the activation bug.

Before martyrdom, both paths separately drop an already primed grenade,
using its remaining timer and current/offhand selected weapon. This is not a
duplicate-martyrdom bug. C1 helper520790 tests timer34, weaponflag344 bit2,
and chooses offhand328 or current33c. Retained native fields differ and must
be audited by meaning, not copied offsets.

## Callback and script ownership limitations

C1 helper562840 marshals nine values in the same order as native
`Scr_PlayerLastStand`: leading zero, time offset, hit location, direction,
weapon name, MOD name, damage, attacker and inflictor (VM push order).
The inspected C1 body ends at562900/56290b without an explicit script-thread
execution call. It proves marshalling only. Native additionally executes the
registered callback and has a protective kill fallback if its script leaves
nonpositive health. Do not claim that fallback or thread dispatch was verified
against this C1 helper.

The overlay `_perkfunctions.gsc::setFinalStand` calls
`_setperk("specialty_pistoldeath")`; unsetFinalStand removes that selection.
With one selected ID per CoDOL perk slot, this can replace selected perk3 or
be overwritten by the later class perk3 assignment. `_class.gsc` awards the
deathstreak before `loadoutAllPerks`. `setC4Death` has a similar legacy bridge.
An independently owned activation is needed; inserting perk14 into selected
perk3 is not a sound representation of deathstreak41's effect.

The shipped finalstand41 row contributes `modFinalStandTime59=20`, while
pistoldeath14 contributes `modPistolDeath8=10`. Final Stand's complete duration,
revive and cleanup behavior still needs its original script/native evidence.
Do not treat the two selected perks or their timers as interchangeable.
