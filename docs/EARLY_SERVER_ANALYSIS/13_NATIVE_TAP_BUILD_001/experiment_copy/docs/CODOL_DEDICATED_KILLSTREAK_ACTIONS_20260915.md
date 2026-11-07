# Dedicated selected killstreak actions — 2026-09-15

User requirement: first three selected rewards have independent activation
slots; final slot is for care-package rewards. C1's actual native bank has FIVE
slots, verified setter5167cf checks slot-1<=4, type544..554 and weapon558..568.
C1 command IDs17..26 are the five press/release pairs. Native action/icon code
already uses this bank independently of the three offhand classes.

Script implementation follows selected slots1..3 and final native slot5.
Slot4 remains reserved; fourth profile data is retained in
codolSelectedKillstreaks[3] but not automatically earned/published as a fourth
selection. This layout is the explicit requested policy using verified native
slot numbering, not a claim that a recovered C1 script established the optional
fourth profile field's meaning.

Previously giveKillstreakWeapon deleted every other noncurrent killstreak
weapon and assigned only slot4. Earning Predator after RC therefore removed
RC's inventory/action representation. killstreakUseWaiter could activate only
the overall queue head. These were concrete obstacles to independent icons
and activation even when selected HUD IDs were present.

Changes limited to _killstreaks.gsc and the authorized _class.gsc blocks:

- Each grant keeps kID/lifeId/earned/XP/owner and adds stable actionSlot. Earned
  matching selected entries map1..3; package/unselected grants map5.
- Ownership remains a collection of reward instances (duplicates retained),
  but each action displays its own newest owned instance. Granting one slot
  neither removes another slot's weapon nor replaces its action.
- Native +actionslotN notifications capture the corresponding kID. The existing
  weapon_change activation path resolves that reward rather than queue[0],
  rechecks identity after frame/callback yields and consumes only that instance.
  Ordinary weapon selection retains a matching-weapon fallback. When the same
  activation weapon is already equipped, the slot listener uses the shared
  dispatcher directly because the native weapon selection has no change edge.
- Slot rebuilding preserves all owned reward weapon grants. Revocation clears
  all five actions and deferred validity records. Care reward preview is HUD
  index4 and clears when empty. Selected previews remain first three entries
  in profile order; earning/rollover traversal still sorts by required kills.
- Class initialization no longer assigns IW4 altmode to selected reward slot3.
  Missing-controller guard and parent metadata-before-handler change retained.

RC icon conclusion: loss of owned weapon/action was proven by the old grant
routine; independent slots now retain it. A separate missing RC material has
not been demonstrated, so no guessed icon substitution or extra assets added.
C1 native HUD/action serializers need no changes for this increment.

Lifecycle review: per-slot listeners share the established single-instance
killstreakUseWaiter endon, disconnect, finish_death and game_ended boundaries.
Pending input identity resets on listener restart/team revoke; IDs are checked
against current ownership after yields. Persistent reward instances retain
original assigned bank through respawn. The care bank supports duplicate
reward ownership; consuming one exposes its next record.

Follow-up lifecycle review:

- Exact catalogue activation-weapon membership replaces substring cleanup;
  this includes rcbomb_mp. Cleanup retains weapons owned by any reward record
  and postpones removal of the consumed current weapon until switching away.
  Every subsequent weapon_change also runs this cleanup.
- Both activation routes acquire one shared busy flag before their first yield,
  retain the selected kID, and resolve ownership again after that yield. Input
  while a callback is busy does not overwrite pending selection. A delayed
  weapon_change for the just-activated weapon cannot consume its next copy
  without another explicit action. Existing marker-listener restart resets
  this state after grenade_fire terminates a placement callback.
- The five action slots retain native weapon indices (<128). The snapshot
  overlay calls CODOL_WeaponToWire and accepts mapped values through 2047;
  thus native107/wire127 and later wire128 do not imply an index-limit bug.
  No index identity assumption or native serializer change was introduced.

Source written and locally reviewed only. Parent review and real C1 activation
confirmation pending; no automated tests, builds or process changes by worker.
