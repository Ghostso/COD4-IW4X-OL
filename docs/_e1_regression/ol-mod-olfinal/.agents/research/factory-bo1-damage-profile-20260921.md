# Factory BO1-derived dismemberment profile

This is an opt-in reconstruction (`OLMOD_FACTORY_BO1_DAMAGE=1`, together with
the existing Factory presentation/death-FX options). It is not recovered CODOL
retail probability code. The previous lethal-only presentation remains available
with the new option disabled. Historical profile; current refinements and dual-publication gates are in factory-refined-damage-fx-20260922.md.

## Evidence and scope

The supplied BO1 common_zombie and common_zombie_patch fastfiles contain the
original `_zombiemode_spawner`, `_zombiemode_weap_tesla`, and
`animscripts/zombie_death` scripts. Local extraction verifies source fastfile,
decompressed zone and payload hashes. These are script-source facts, not a new
IDA or live BO1 test. Private source copies/provenance stay outside this repo.

- Ordinary gib eligibility: damage >=10% of pre-hit health. Head loss additionally
  needs remaining health <=10% of maximum, an eligible player/weapon/method and
  head/helmet/neck hit. No ordinary headshot chance roll.
- Eligible torso hits choose equally between guts and right-arm loss, once per
  body; head loss is independent and can follow body damage.
- Tesla head choice is 50%, delayed 530–1000ms, using a real configured weapon
  identity rather than an animation name. Known packaged Tesla names are resolved
  against the current map's actual weapon band. Missing entries stay disabled.
- Nonlethal damaged actors keep moving and taking damage. A headless survivor
  loses 20% of its health at decapitation per second, rounded up for integer
  health, with one bounded tick per frame. The four-head-removals/frame cap is
  BO1-derived. The existing cannotDie protection is respected.

CODOL original player recordings independently establish torso_1/head/lowclean,
body/behead, and rarmoff_1/head/lowclean multipart states. Existing exact-build
IDA 0x530C90/0x52FBE0 and the native reader replay establish agent attachment
semantics; 0x452970/0x452D60 establish play/stop FX events. The prior native
server hit-pose/trace evidence and notifyType0 correction are preserved.
No native executable address or network-field layout is added by this increment.

## Implementation boundaries

Per-generation state retains original outfit and maximum health separately from
the current damaged body. Actual pre-hit health is recorded by the committed
damage transaction, avoiding overkill-clamp errors. Source-only collision poses
now include the lower-body part; the native hit DObj is rebuilt when any part
changes. Native server XAnim goals still suppress client notifications.

Torso and head emissions have separate bounded owners. New head loss does not
erase earlier torso damage or strand an earlier body effect. Native blue FX
are reused; right-shoulder placement for arm loss is an explicit reconstruction
using a resolved named bone. The 1000ms emission stop remains candidate policy.
Corpse retention, noncollision, ammo, navigation and player protection are unchanged.

Electrical body shock is supported. Electrical eye-shock playback remains guarded
until a composed-DObj eye index is resolved: a standalone head-model bone index
must not be used as if it were the composed actor index. Do not claim eye-shock
visual acceptance or a naturally working Tesla weapon solely from source tests.
This adds the 50% head decision to classified electrical kills; it does not
implement the missing Wunderwaffe chain-lightning weapon/controller.

The current ordinary damage profile is scoped to bullet methods. BO1's additional
grenade/projectile proximity, freeze/thunder special paths and full limb-location
selection are outside the four requested behaviors. Exclusions are mapped by
resolved asset identity, not guesses about every CODOL pistol skin.

## Validation

Release build passed. Seven canonical suites passed on the final candidate;
the first suite run had a local-networking failure that did not reproduce in
the standalone test or final full suite. No network-source change was made.
Server tests also passed at 50ms cadence.

New source integration cases exercise weak/high-health head-hit rejection,
both torso choices, nonlethal multipart hit-pose identity, torso-then-head
state preservation, bounded headless lifetime, and both delayed Tesla branches.
Legacy disabled-profile tests still pass. These are source tests, not rendering
or natural electrical-weapon verification. Factory playtest is pending. FFA not
run; private workflow does not require it for each increment. No commit/push yet.

## Private publication acceptance

The AO candidate is accepted for private publication on September 21. Factory
testing has shown head spray and torso debris; read-only AO logs also show living
arm/guts damage followed by head loss. Two recorded lethal headshots selected
different body clips (647 and 659), but client playback equivalence is unverified.
The ordinary seven-clip death preview mix is still independent of damage cause;
do not describe it as recovered native animation selection. All four BO1-derived
rules have source coverage; natural electrical-weapon activation, eye-shock bone
placement and complete model-family visual coverage remain limitations.
No same-candidate two-player FFA run is claimed. Native actor pose initialization
is Factory/opt-in scoped and the seven canonical regression suites passed.

Accepted DLL SHA256:
F38D657672E3135F217C1569632FCBEC21FCDF8E96AE7922D578FC8B25A9874E.
Private native binaries, IDBs, live logs and original script extracts are excluded
from the repository. Prior failed experiments remain documented as failures.
