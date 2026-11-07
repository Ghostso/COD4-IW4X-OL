# Gameplay bugs queued after current implementations

User requested these be investigated and fixed after RC-XD, dogs, and current
equipment work (including Tabun). All entries are user-reported, unresolved,
and not yet assigned. Preserve this ordering; do not interrupt current workers.

1. **Riot shield:** does not block bullets. Trace equipped shield identity,
   collision/damage interception, orientation and front/back behavior.
2. **M203 attachment:** switching from grenade launcher back to the rifle plays
   the weapon-switch animation instead of the gun-angle/alternate-mode change.
   Trace alternate weapon state, event identity and attachment animations.
3. **Bot heads:** some heads do not attach. Trace composed model parts and bone
   compatibility using each bot's selected character/loadout.
4. ~~**Bare-hand character**~~ RESOLVED 2026-09-15 late, user-confirmed live. Original report: hands are absent in both first-person viewhands and
   the world model. Exact character remains unidentified; inspect appearance
   data and bare-hand part selection rather than substituting another character.
5. ~~**Killcam bot hands**~~ RESOLVED 2026-09-15 late, user-confirmed live. Original report: bots display the viewer's hands instead of their own.
   Trace archived killer appearance and viewhands ownership through killcam.
6. **Throwing-knife pickup:** still cannot retrieve a thrown knife. The recent
   native cleanup and attachment changes do not establish functional pickup.
   Follow the actual settled/linked missile through hint, use, capacity and
   inventory transfer paths; keep this issue open until live recovery works.
7. **Destructibles:** destroyed models do not appear after destruction. Vehicles
   also lack breakable windows and doors detaching after explosions. Inspect
   model/stage replacement, glass ownership, part breakage and piece physics;
   generic glass shattering previously confirmed does not cover vehicle glass.

8. **Predator thermal target boxes:** red boxes around enemies still do not
   appear in Predator missile thermal vision. Trace target eligibility,
   team filtering, remote-view ownership and C1 target-marker publication.

The Killhouse shadow issue is resolved and explicitly excluded from further
investigation at the user's request.

9. **Scoped-in sway (2026-09-16, user):** the ADS/scope sway is wrong on the
   live build. Trace what C1 drives scope sway from (playerstate fields,
   weapon def sway/breath values, server dvars) and what the server publishes.
10. **Crosshair friend/foe colouring (2026-09-16, user):** the green/red
    crosshair highlight over friendlies/enemies is not implemented. Trace
    C1's crosshair-entity identification (traced entity, team from clientinfo
    or an entity-state flag, any ps field) and publish what it needs.
