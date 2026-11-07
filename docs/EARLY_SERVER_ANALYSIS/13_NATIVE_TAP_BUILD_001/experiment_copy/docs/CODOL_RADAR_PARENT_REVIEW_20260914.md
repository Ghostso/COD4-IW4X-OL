# Radar integration review

Parent source review, not live verification.

The new spyplane/satellite pair is captured at ClientEndFrame beside existing
radar-block inputs, before entity-state publication. Spectator-follow copies
retain the followed player's extension rather than publishing the spectator's
own input. Archive reader and writer both insert the changed bit and two 2-bit
types after killstreak HUD and before event epoch; preflight rejects values
outside 0..3. Recent corpse-index and throwback fields remain present.

Client field callbacks resolve live gclient ownership and access separate
script-owned input. Team selection uses existing allies/axis/none mapping.
Nonzero per-client input takes precedence over team input, following the T5
producer; legacy hasRadar explicitly supplies ordinary spyplane type1 only
when no spyplane input exists. Snapshot publication targets C1 0x224/0x228.

Staged SR71 initializer runs from _uav during killstreak registration. The
gamelogic starts _spawnlogic first; its init creates level.players before
yielding, so the SR71 worker's initial player walk has a valid array. Catalogue
initialization follows callback registration and can discover sr71_mp.

Thirty seconds is an explicit IW5 lifetime adaptation, not recovered C1/T5
SR71 timing. Flyby cosmetics and real immunity/jamming behavior remain
unverified. Build/deployment waits for the concurrent bot source boundary.
