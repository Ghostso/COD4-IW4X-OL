# Mortar selected-reward identity failure

Source reviewed; staged script written. No tests/build/restarts, live script
edits, or client/lobby changes. No native projectile behavior changes.

## Proven failure path

The dedicated action-slot dispatcher resolves selectedID into a reward record,
then retains its kID and lifeId locally in _killstreaks::killstreakUsePressed.
Mortar's existing callback accepts only lifeId and obtains kID from queue[0],
which is the newest earned reward rather than necessarily the selected one.

Example: own mortar kID11, then earn dogs kID12. Select mortar's dedicated
action slot. The dispatcher uses kID11; tryUseMortar stores12 in selection.
All three targeting confirmations complete normally. The dispatcher verifies
11 still owned, marks mortar used, removes11, then calls commitMortar(life,11).
commitMortar clears pending state, notices pending.kID12 !=11, and returns
without fireMortar. The reward is consumed but no bombs are spawned.

This is independent of mortar ballistics, FX, collision, or explosion clocks;
that path never executes. It also explains why using the newest reward can
work while using the same mortar after earning a later reward fails.

## Narrow correction staged

obj/mortar-identity-stage/maps/mp/killstreaks/_mortar.gsc changes
tryUseMortar to accept (lifeId,kID), rejects missing identity, and stores that
exact dispatcher-owned kID rather than looking at mutable queue position0.
The existing cancellation, three confirmations, ownership check, consumption
and post-consumption commit remain intact. No fake fallback takes the newest
reward or launches missiles before selection/ownership is committed.

Coordinated _killstreaks.gsc is staged in the same directory. Its sole change
in killstreakUsePressed adds `streakName == "mortar_mp"` to the existing airdrop/airdrop_sentry_minigun/
airdrop_mega branch which invokes the callback with `(lifeId,kID)`.
All other callbacks retain their existing argument contract. Deploy the stage
and this dispatcher change together, after source review.

Native codol_bomb.c already creates actual ET_MISSILE objects via
CODOL_SpawnMortarBomb, using C1 type4/guidance4 metadata and real G_ExplodeMissile
impact handling. This audit does not claim its flight path is live-verified or
that the identity fix rules out independent geometry issues.

Other effective reward callbacks were searched for queue[0] kID/lifeId reads;
none besides mortar were found. Remaining main-script uses are the explicit
default-selection fallback, constructing the newest queue record, and earned
dialogue. No broader activation rewrite was made.
