# Challenges: the vanilla shape, and the egress to the lobby (2026-09-21)

## What vanilla does

CoDOL stores challenge progress as **one cumulative float per challenge** in
the secure profile's `challenges[1000]` (byte offset 0x0174, stride 4, with
`challegeUpdateTime` at 0x0170 — the typo is the client's own member name).
The index is the **numeric id in column 4** of `mp/allChallengesTable.csv`.

There is no ref-string storage and no stored tier anywhere in vanilla:

* `mp/challengeWeight.csv` (mounted in `common_gametype_mp`, 649 × 3) is
  `(condition, challengeId, weight)` and its conditions read
  `private.challenges[800] < 1` / `private.challenges[800] == 1`.
* C1's condition evaluator (`0x0048EA72`) supports exactly three namespaces —
  the error string at `0xC46A30` reads *"Support: inventory, public, and
  private"* — where `private.` is `mp/playersecuredata.def`, `public.` is
  `mp/playerdata.def`, and `inventory.<id>.<have|count|xp|time|valid|expired>`
  is the marketplace record.
* C1 logs `Challenge starts, chID: %d` and `Cleared onboard challenge @%d`.
* The tier is derived, not stored: `CODOL_ProfileChallengeState` counts the
  thresholds in columns 6, 8, … that the progress has passed.

**IW4's `challengeProgress` / `challengeState` roots do not exist in CoDOL.**
Neither string occurs anywhere in the 33 MB C1.exe, and neither is declared by
either definition, so `legacy_routed()` (`codol_script_profile_vm.c:137-147`)
diverted every read and write of them into a scratch map that is never
persisted and never consulted by anything that decides an unlock. Writing them
was a no-op with extra steps.

## What changed

### `bin/home/codol_rawfiles/maps/mp/gametypes/_missions.gsc`

* `ch_getProgress` / `ch_setProgress` now address `challenges[<numeric id>]`
  through `getPlayerData("challenges", id)` / `setPlayerData(...)`. `challenges`
  **is** a declared root of `playersecuredata.def`, so the native accessor
  routes it to the secure blob with no C change required — an int path
  component indexes an indexed array, exactly as C1 does.
* `ch_challengeId()` resolves ref → id from a `level.challengeIds` map built in
  `buildChallegeInfo()` from column 4, alongside `level.challengeInfo`.
* `ch_getState` is **derived** — one plus the number of thresholds the progress
  has reached — matching `CODOL_ProfileChallengeState`. `ch_setState` is inert,
  kept only so vendor call sites still compile.
* `processChallenge` no longer clamps progress back to the tier target on
  completion. IW4 did that and carried the tier separately; with a derived tier
  it would pin the challenge at the tier it just awarded.
* `challenge_rewardVal` reads CoDOL's reward series at columns **24..32**,
  parallel to the targets, not IW4's interleaved 7, 9, 11, …. Against CoDOL's
  table the IW4 columns return 0 for **1349 of the 2330 authored tiers (58%)**,
  because CoDOL fills only the first two of those cells.
* The three remaining direct `setPlayerData("challengeProgress"/"challengeState")`
  call sites (patient-zero seeding, the bulk percentage setter, and
  `_hud_message.gsc`'s splash read) now go through the accessors.

`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only mp`
exits 0.

### `src/codol/stats/codol_match_report.c`

Each non-bot row may now carry

    "progression": {"challenges": {"<numeric id>": <delta>, ...}}

next to `xp` and `lifetime`. It is omitted when nothing moved, so an ordinary
match adds nothing to the file.

**The delta needs no baseline of its own.** `codol_profile_clients.c` keeps the
attached bytes (`data`) and the script-edited copy (`session`) apart precisely
so readers observe edits without altering the attached bytes, so
`session − attached` *is* this stay's progress — and re-measuring it is
idempotent, which is what lets a report be written twice in one match (a map
change and then `gameended`) without double-counting.

* `challenge_stay_deltas()` walks ids 0..999 across both views.
* `freeze()` settles them into the row before a departing slot's session blob is
  freed; `CODOL_MatchReportClientAttached` carries them across a reconnect the
  way `stat_carry` already is.
* A live row diffs at emit time rather than storing, so the carry and the
  current stay cannot overlap.
* 64 changed challenges per player per match; overflow warns rather than
  silently truncating.

Nothing here writes a profile. The lobby owns persistence.

## The lobby half

`alpha0022/rank_writeback._merge_progression` → `player_profiles.add_xp(
progression_deltas=…)` → `progression.credit()` applies the deltas under the
same lock and in the same save as the XP, and `ensure_blob` re-renders
`challenges[]` into `mpdata_s.<uid>` — which is the file this server reads back
on the next connect (`codol_profilePath` is the lobby's own `resources`
directory). `challenges.Challenges.get()` accepts a numeric id as well as a
ref, so the whole chain is id-native.

Verified end to end offline against a report in exactly the shape emitted here:
two challenges advanced, two tiers awarded, three unlock flags gained, both
values landing at the right `challenges[<id>]` offsets in the re-rendered blob.

## Still open

* Not verified against a live client. The lobby needs a restart to pick up its
  half, and the server needs a build and relaunch for this one.
* Weapon levels do **not** travel this way. A weapon's level is field 4
  (`+0x18`) of its `bdMarketplaceInventoryItem` — see
  `alpha0022/docs/progression.md` §2.2 — and is served by the lobby on task 10,
  not by this server.
* `isItemUnlocked` still evaluates IW4's `mp/unlocktable.csv` (CoDOL does not
  mount one, so it always falls back to the `codol_scriptPath` CSV) against
  CoDOL challenge state. C1's own implementation of that method is deprecated
  (`IsItemUnlocked is a depricated function`, `0x8589b0`), so the front end's
  flag set — which the lobby now derives — is the real gate.
* `SV_ClearServer` still does not save the legacy store or forget it on a map
  change; that store no longer holds challenge progress, but anything else
  routed there is still rolled back by the re-attach.
