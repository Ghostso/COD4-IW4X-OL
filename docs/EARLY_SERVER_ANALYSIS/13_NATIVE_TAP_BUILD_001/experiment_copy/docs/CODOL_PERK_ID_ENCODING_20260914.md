# Selected-class item encoding

## Proven ID+1 families

C1's selected-class scalar/array accessor590bc0 performs the structured
signed-short read through590670 and decrements its result at590c8a. Its setter
590ae0 increments the supplied value at590b56 before the structured write.
Stored0 therefore decodes to-1 (empty), not marketplace item0.

The same accessor is used by equipment **and** these additional families:

| Profile member | Getter evidence | Setter evidence |
| --- | --- | --- |
| perks[0..2] | 591483 loads stringc60688=`perks`;591488 calls590bc0;591491 stores returned ID unchanged; loops three entries through59149e. | 591735 loads same member;59173a calls590ae0; loops three entries through591748. |
| killstreaks[0..2] | 5914b5 loads stringc60690=`killstreaks`;5914ba calls590bc0;5914c3 stores returned ID unchanged; loops three entries through5914d0. | 59175f loads same member;591764 calls590ae0; loops three entries through591772. |
| deathstreak | 6be71a loads stringc6069c=`deathstreak`, EDI=-1 for scalar access;6be71f calls590bc0;6be737 compares returned ID directly to the selected item. | No dedicated setter was needed to establish this getter's decoding; not independently traced in this pass. |

Native `CODOL_ReadProfileLoadout` currently reads these leaves as raw signed
shorts. They require subtraction of1 at the profile-to-runtime boundary, as
the already identified equipment fields do. The raw structured profile API and
stored profile bytes must remain unchanged. This applies before marketplace
name/group lookup, not after perk-name-to-perk-slot-ID conversion.

## Do not blanket-decrement every loadout field

Weapon bases use the same generic accessor but their callers immediately undo
its decrement: primaryBase6b91bf/6b91c4 is followed by `lea esi,[eax+1]` at
6b91c9; secondaryBase6b928f/6b9294 likewise re-adds1 at6b9299. Their current
effective raw ID representation is therefore different from perks/equipment.
No attachment-array encoding change is established by this pass.

These distinctions explain why generic read-short subtraction would corrupt
already functioning weapon descriptors. Correct only proven item families.

## Coordination and verification state

Parent was notified immediately of the additional perk/killstreak/deathstreak
decoding requirement. This worker owns documentation only; the profile-loadout
implementation remains with the coordinated integration worker/parent. Evidence
is direct offline C1 disassembly, not a Python assumption or live-state guess.
No source edits, tests, builds, process writes, restarts or UI actions.
