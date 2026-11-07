# Selected killstreak/deathstreak pipeline audit

## Concrete earned-reward blocker and staged correction

`_class.gsc::setKillstreaks` inserts cost-indexed rewards in ascending numeric
order and subsequently inserts rollover entries. However the native
`GetNewVariableIndexInternal2` in `cscr_variable.cpp:895` prepends new children:
it assigns the new child to `parentValue->nextSibling` and links the prior
head behind it. `FindFirstSibling` returns that head; `Scr_AddArrayKeys`
at2222 follows the sibling list. `codol_script_lower.cpp` lowers foreach to
an indexed traversal of getarraykeys, preserving that order rather than
sorting the source keys.

`_killstreaks.gsc::checkKillstreakReward` assumed ascending costs and broke
on its first cost above the current streak. A recently inserted rollover
cost can therefore prevent all lower earned rewards from being examined.
Merely replacing break with continue would still allow a high eligible cost
to update lastEarnedStreak before a lower reward, suppressing the lower grant.

Staged `obj/killstreak-order-stage/maps/mp/killstreaks/_killstreaks.gsc` now
iterates numeric costs0..maxVal and skips undefined entries. It preserves
the existing progress writer, eligibility modifier, successful-grant marker,
rollover exclusion, queue, ownership and action-slot publication. Each
existing cost is visited once in ascending order. This is a script adaptation
to actual native array iteration, not a change to generic VM array semantics.
Parent review/deployment and live reward confirmation remain pending.

## Existing native and script producers found

- Selected profile killstreak IDs are decoded in `codol_script_profile_loadout.c`
  with the established stored-ID-minus-one rule. `_class` reads all four
  class-local selections through the native bridge.
- `setKillstreak` writes copied playerState extension state; the native HUD
  publisher supplies C1 offset64 plus five IDs68..78 and targets7c..8c.
  `_damage` increments script kill progression and calls the reward checker;
  spawned-player and death waiters republish/reset the HUD count.
- Native action slots retain five type/weapon pairs in copied playerState
  state and publish C1 offsets544..554 and558..568. The IW4 queue script
  exposes its top owned reward in slot4; weapon_change dispatches its handler.
  Successful use removes that queue entry and gives the next owned item.
- Deathstreak accumulation/reset exists in `_damage`, and `_class` now reads
  the threshold from coPerkStatsTable column6. Earlier LastStand/Martyrdom
  native ability gates are implemented; this audit does not prove every
  reward-specific effect or its complete death lifecycle.

## Other concrete limitations, not changed in this stage

1. Equal-cost choices were investigated and are rejected by C1's selection UI.
   `6bf650` resolves existing selections through `6bf510` and candidate cost
   through `6bf4b0`, both using coKillstreakStatsTable column4. It compares
   all other slots (excluding current EDI) at6bf68a/696/6a2 and returns false
   on any equal cost. Equip code calls this at6bfc5d and only writes the new
   selection at6bfc9f on success. Keep the current unique-cost representation;
   arbitrary edited profiles with duplicate costs are not valid UI selections.
2. `_killstreaks::killstreakEarned` still reads the old global
   `getPlayerData("killstreaks",0/2)` for the wargasm challenge. Those roots
   are absent from CoDOL's declared profile and route to the IW4 session
   store, while the actual selections are class-local native bridge values.
   Thus that challenge check does not follow the chosen CoDOL class. This
   is separate from granting/using the reward and was not changed.
3. Five native action slots and five HUD previews are implemented facilities;
   their presence does not establish complete C1 reward-selection UX. The
   current script still presents an IW4-style single top-of-queue action.
   No original C1 reward-selection producer has been established here.

No tests, builds, live scripts, running processes, or client memory were changed.

## Final staged increment

The stage additionally includes `_class.gsc` with selected
`getSelectedPerkModifierValue("modKillstreakShift")` instead of a name-only
Hardline check. Undefined means no contribution; a present value is converted
to the integral kill-count unit once. Fresh coPerkStatsTable row8 declares
that modifier with value-1. Selected reward costs and HUD IDs now use the
verified C1 coKillstreakStatsTable columns4 and0. Broad reward dialog/weapon
column migration is deferred: columns after5 differ from the IW4 table,
and the CoDOL table includes reward handlers not implemented by this overlay.

Rollover aliasing was checked rather than presumed broken. Native
Scr_EvalArrayRef1453..1490 sees shared array refCount, allocates a new array
and copies before a write. Thus assigning newKillstreaks=self.killstreaks does
not establish recursively growing the source collection; no rollover change
is included. The explicit ascending grant traversal remains necessary
regardless of prepend order or any array copy's reversal of sibling order.
