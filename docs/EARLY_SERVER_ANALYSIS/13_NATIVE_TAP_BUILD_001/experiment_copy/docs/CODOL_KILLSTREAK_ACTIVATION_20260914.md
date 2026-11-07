# Selected killstreak activation lifecycle increment (2026-09-14)

Source stage: `obj/killstreak-activation-stage/maps/mp/killstreaks/_killstreaks.gsc`.
Based on live B7C9 reward-order script. No live scripts, native code, running
processes or client state changed; no tests/builds run.

## Proven script lifecycle gaps

`waitForChangeTeam` calls `clearKillstreaks`, which previously deleted only
queue entries. Native action slot4 and granted killstreak inventory items
survived that ownership revocation. The stage clears slot4 and removes item
weapons using the same existing `getWeaponsListItems`/`isSubStr("killstreak")`
classification as `giveKillstreakWeapon`. This includes a currently held
reward because team change revokes ownership. Normal successful-use handling
is unchanged: it can finish its current weapon switch before removing items.

`giveOwnedKillstreakItem` now explicitly clears slot4 when there is no owned
head, making empty ownership publication complete on spawn/class changes too.
The native action-slot writer already provides the correct operation: empty
kind sets type0, preserving its parameter exactly as the C1 setter does;
consumers gate the parameter by type. No new native facility was needed.

`killstreakUseWaiter` accepted a `weapon_change` matching head0, yielded via
`waittillframeend`, then reread head0 without validating identity or existence.
`giveKillstreak` can prepend another reward during that yield; team change can
clear the array. The stage saves the existing unique `kID` before yielding,
then checks alive/head existence/same `kID` before dispatch. A stale event
cannot activate a different reward or dereference an empty head. The queued
reward remains available for a subsequent weapon selection. The callback's
existing captured `kID` and identity-aware removal are preserved.

## Remaining concrete limitations

Native five action slots and HUD count/ID/target producers exist; this patch
does not claim a recovered C1 multi-reward selection interface. The current
IW4-based script exposes only its queue head through action slot4.

Class selection costs and HUD IDs now use C1 `coKillstreakStatsTable`, but the
activation script still uses IW4 `killstreakTable`. C1 columns7..16 correspond
to IW4 columns6..15 (hint, sound, dialog, team dialogs, inform-enemy, weapon,
points and shaders). Migrating all rows is not a safe mechanical table rename:
C1 has69 rows and additional MP/ZM rewards lacking registered handlers in the
current script suite. Existing initialization also stops at first missing
numeric ID and asserts all dialog/score values; current log reports legacy
row17 missing. A future increment needs explicit handler coverage and verified
optional-field policy, rather than precaching every catalogue entry or
claiming missing handlers implemented. No catalogue changes included here.

HUD counter already has script increment/death reset/spawn republish and native
copied playerState publication. No additional missing count writer was proven
in this bounded audit. Live earned reward/use verification remains pending.

## Deferred callback review

The stage also invalidates each removed reward's `pers["kIDs_valid"][kID]`
before removing weapon items. Primary IW4 `_airdrop.gsc` uses that separate
permission in `tryUseAirdrop` (line239), and the detached marker watcher
checks it at371 before starting delivery and clears it at377. Queue deletion
alone therefore leaves a discarded marker permission usable. Already committed
markers have consumed their permission and are not cancelled by this cleanup.

A successful use callback can yield while team change clears its queue entry.
Before award/use bookkeeping and the asserting shuffle, the stage now scans
for the captured name/kID anywhere in the current queue. A newly earned head
does not cancel the old reward; revoked ownership suppresses stale bookkeeping.
This does not retroactively undo a callback's already committed world effect.

Death endons in primary IW4 marker callbacks terminate the invoking waiter
thread; they do not return an undefined result to its caller. No specific
undefined-on-death return defect was established, so callback return semantics
remain unchanged. Native/script callback-specific cleanup still merits live
coverage; this increment claims only the demonstrated ownership races.

## Live missing HUD root: absent reward-enable default

Passive C1 PID102092 capture passed camera/animation instruction guards and had
an active predicted+snapshot commandTime398906. Both copies had count0,
IDs[0,0,0,0,0], targets[0,0,0,0,0]. This establishes absent selected HUD data,
not merely a renderer visibility assertion.

Native PID82912 MainModule was0x1e0000 (ASLR). Using its matching executable
COFF symbols `_cvar_numIndexes`0x7f4b80 and `_cvar_indexes`0x7f4ba0 relocated
from0x400000, a read-only walk found464 cvars and **no scr_game_hardpoints**.
The initial unre-based attempt read count0 and was discarded. No dvar was set
or process memory written during this investigation.

`_gamelogic::Callback_StartGameType` reads `getDvarInt("scr_game_hardpoints")`; absent
values become0. `_class` therefore selects four `"none"` rewards and publishes
zero IDs/targets. No coKillstreakStatsTable lookup occurred in the current log,
consistent with this branch. The primary IW4
`DevData/devraw/default_mp_gamesettings.cfg:57` establishes default1, whereas
the current native/script/config bootstrap did not establish it.

Staged `_gamelogic.gsc` now sets default1 only when getDvar returns an empty
string, immediately before reading level.killstreakRewards. Explicit0 remains
respected, including gamemode/admin disables. This is restoration of the
primary IW4 default for the adapted script, not a newly invented C1 HUD flag.
The selected IDs/costs and existing HUD counter writers can then execute.
Post-deployment live HUD rendering still requires confirmation; no client-side
HUD flag or snapshot field was changed speculatively.

