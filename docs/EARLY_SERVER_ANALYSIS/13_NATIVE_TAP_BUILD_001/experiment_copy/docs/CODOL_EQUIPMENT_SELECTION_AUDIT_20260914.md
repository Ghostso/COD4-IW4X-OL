# Equipment selection and unknown item1227

Root cause verified and repaired in native source: C1 equipment playerdata
stores marketplace item ID plus1. Native loadout bridge used stored values as
actual IDs. Stored1227 means bouncingbetty item1226; this is C1 encoding,
not an item-specific alias or a newer catalogue revision.

The earlier bounded catalogue investigation below correctly established that
actual item1227 does not exist, but its tentative invalid-profile interpretation
was superseded by the direct getter/setter trace at the end.

Reference root: D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022.
Shipped Chinese client files under D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/client_shipRetail/chinese:
- code_post_gfx_mp.ff:938item rows,no1227;SHA256 ab6e420346258bb70526d9327c63136dd9afeb966ca9dff3eab69dc4ac1d84bc.
- patch_code_post_gfx_mp.ff:943item rows,no1227;SHA256 2b2223135eb29e49a9e054065853b5fc227b6e867e8904511e8a8bec13e7ebff.
- code_post_gfx_default_mp.ff contains no marketplace items table.

Python resources/marketplace_catalogue.json agrees: no1227 in item_names.
PRODUCT1227 exists but grants item2155=mag_extak,typewat,groupMAG.
SKUs2402/2403 buy this product. Converting equipment1227 via product lookup
would incorrectly equip an AK magazine. These namespaces are separate.

Newest resources/mpdata.<numeric-user-id>, modified2026-09-14T18:18:29.025041Z,
SHA256 ce9a8cb7bf21c46f7be907b4acd9200085185f71ba1d5aa264792092e62132ef:
class0 lethal1201,special1208,tactical1227;classes1..4 have1201/1204/1211.
Two other per-user uploads have class0 tactical1212; this is not proof they
belong to one user. Python records are eight92-byte records at inflated0x1511,
short members lethal leaf5,special44,tactical45; proposed schema agrees.
Native CODOL_ReadProfileLoadout resolves named members against mounted schema
and sign-extends short kind9. No evidence supports changing member offsets.
Bounded Python/JSON/docs search found no hardcoded equipment1227 producer.

Exact patch marketplace item/type/group rows:
1200frag_grenade_mp equ/let;1201semtex_mp equ/let;1202throwingknife_mp equ/let;
1204flash_grenade_mp equ/spe;1205smoke_grenade_mp equ/spe;
1206emp_grenade_mp equ/spe;1207concussion_grenade_mp equ/spe;
1208white_phosphorus_grenade_mp equ/let;
1209specialty_tacticalinsertion equ/tac;1210specialty_blastshield equ/tac;
1211claymore_mp equ/tac;1212c4_mp equ/tac;
1225scrambler_mp equ/tac;1226bouncingbetty_mp equ/tac.
Thus lethal/special/tactical ordering has explicit marketplace support.
Stored special1208 also conflicts with its actual let group; do not silently
reassign categories. Zombie8227 is valid trap_shrink_zm; never truncate a mode
prefix to derive1227.

## Live C1 follow-up

Parent reports class0 UI shows a round mine in third equipment slot.
Passive ReadProcessMemory capture:PID90944,imagebase400000,assetentry943,
StringTable0x1f0b9f4,11columns/943rows. Actual DB lookup4cb564..4cb575 selects
pool1c402c8+24*entry,type+0,header+8;4cb5f1 follows hashlink+12.
Only one type37 marketplace entry found. All943row IDs scanned: no1227.
Rows451/468/469 are1208/1225/1226 with exactly the names/groups above.
A different currently loaded marketplace revision does not explain1227.

Round-mine icon could be fallback/highlight for invalid selection or a producer
index/ID error; icon alone does not prove either. Investigate actual selection
producer before any alias. Current fallback may permit spawn but is not correct
selected-equipment support. Keep missing-item diagnostics visible.

Initial catalogue pass changed only this document; source correction is below.


## C1 producer/consumer proves item+1 representation

UI equipment slot builder6bb4ee loads member strings fromcd234c:
lethal,special,tactical,meleeWpn. It calls590bc0 at6bb4f9 and passes the returned
item directly asECX to6ba3d0. UI groups at6bb525/6bb54a/6bb56f are let/spe/tac,
published under equipment_0/equipment_1/equipment_2.

590bc0 resolves weaponClasses/class/member (optionally indexed) and calls
raw scalar reader590670 at590c7d. Kind9 signedshort branch5906e2..590701
reconstructs the stored signed16bit value without adjustment. The wrapper
then DECREMENTS EAX at590c8a. This proves stored1227 becomes actual1226 before
marketplace lookup/image generation. Stored1208 becomes concussion1207;
stored1201 becomes frag1200. The previously noted special1208 category mismatch
was the same missing decode, not a malformed profile.

Counterpart setter590ae0 loads actual supplied item from[ebp+c] intoEBX,
INCREMENTS EBX at590b56, formats the encoded value, and writes the named
weaponClasses member through590360 at590ba6. This paired writer/reader is the
encoding anchor. Stored0 decodes to actual-1(empty). Signedshort values are
promoted to nativeint before subtracting, so raw-32768 maps-32769 without
C overflow; negative decoded values remain empty under existing item policy.
No narrower guessed clamp is imposed. Valid stored32767 decodes32766.

Item image helper5c80c0 stores the decoded item_id at5c80f3/5c8101 and calls
69b680 at5c81c5 for imageURL. 728750/7287c0/728830 resolve item name/type/group
by exact marketplace column0 string ID. Missing row lookup61ed00 returns-1,
not a nearby row or decrement. Thus the observed round-mine image is explained
by the wrapper's correct1227->1226 decode, without UI fallback speculation.

## Native implementation and scope

src/codol/script/codol_script_profile_loadout.c now subtracts1 after reading
ONLY the four proven scalar equipment members lethal,special,tactical,meleeWpn
in CODOL_ReadProfileLoadout. Both getLoadoutItem and getLoadoutItemType consume
this decoded view, so name/category agree. Stored playerdata and generic
structured VM access remain unchanged; no profile rewrite.

Deathstreak, perks, killstreak arrays, weapon bases and attachments are left
unchanged pending their own producer/consumer trace. Although590ae0/590bc0 are
generic wrappers used by additional callers, that is not blanket proof every
leaf uses this representation. Weapon reader590a7d/590abf stores raw results
without decrement at those sites, reinforcing the need for specific tracing.

Source readback performed. No tests/builds/restarts/process writes/hooks/input.
Parent owns build and live verification.


## Native scrambler support, subsequent implementation

After correct equipment ID decoding, _class codol_giveEquipment already
resolves scrambler_mp/bouncingbetty_mp through generic giveWeapon, giveStartAmmo,
and setOffhandEquipment. Inventory grant and deployment gameplay are separate.
Mounted repo _weapons.gsc installs grenade_fire listeners for C4 and claymore,
but none for these two devices. Existing Python projectile_sim marks Betty as
360-degree claymore-style proximity and scrambler as persistent sticky device;
that is a behavioral lead, not proof of C1 trigger/pop-up timing or deployment.
OpenBLOPS provides client scrambler HUD methods but no matching server scripts
were found in this bounded search. No substitute device effects were installed.

C1 native makeScrambler,0x55caf0, gives concrete implementable support:
- exactly1 script argument checked55cafd;
- receiver resolves by534a10, must eType6/script mover at55cb55;
- cannot mutate willNeverChange eFlags80000000 at55cb9b;
- argument resolves to an entity reference via5ce110 at55cbdc, classnum0;
- owner is argument entityState.number, read55cbf8;
- receiver eFlags gains200000 at55cbfa and entityState+80 owner at55cc01.
There is no player-only requirement, radial server damage, synthetic team jam,
or timing behavior in this method.

Implemented codol_equipment_support.c/.h with full receiver/argument/mutability
checks and actual state production. Native s.otherEntityNum retains the owner;
existing radar carrier bit02000000 retains the flag independently of engine
flag numbering. The model/brush branch in codol_sv_gameframe now overlays
C1 bit200000 and owner+80 using only captured entityState. Both native fields
already travel through snapshot copies and internal archives (msg.c full32
NATIVE_EFLAGS_BITS and11bit otherEntityNum). Entity clear/free naturally resets
them; no process-global device side table or live owner lookup during archive
publication. Method registration makescrambler added in scr_vm_main.c.

No new equipment lifecycle listener installed: correct scriptmover construction
from the thrown scrambler, activation/deactivation/damage/pickup ownership, and
Betty arming/trigger/pop-up/explosion remain unimplemented until their actual
reference paths are established. The new method is real VM support, not a
claim that either complete equipment item now works. Parent handles build.
Source readback only; no tests/builds/restarts/process writes/UI input.


## Deployment follow-up: further reference limits and asset evidence

Decompressed every type36 rawfile in shipped common_mp/patch_common_mp,
common_gametype_mp/patch_common_gametype_mp, code_post_gfx_mp/patch,
ui_mp/ui_viewer_mp/development_mp. No scrambler/Betty lifecycle script or
makeScrambler call is present. The only GSC files in that set are the two
ui_viewer FX scripts. Main IWD ZIP directories contain no GSC/CSC/Lua files.
A further D:/CoD textual GSC/CSC/Lua search finds only alpha0022's surrogate
maps/mp/_weapons.gsc. That file labels scrambler beacon and explicitly performs
no lifecycle operation for beacons. It never calls makeScrambler.

Direct common_gametype_mp type28 definitions expose important contradictions
with Python projectile_sim, which cannot be treated as deployment proof:

| Field | Scrambler asset4137 | Betty asset4138 |
|---|---:|---:|
| +794 projectile speed |0|600|
| +798 vertical speed |-10000|0|
| +79c forward speed |2000|0|
| +7c8 stickiness |4|3|
| +be2 timedDetonation |0|0|
| +654 fuseTime |3500|3500|
| +778 explosion radius |256|256|
| +780 inner damage |200|100|
| +784 outer damage |50|70|

Scrambler has claymore-style placed launch; Betty has thrown launch. Python
instead says scrambler speed600/sticky and Betty placed/downward, and gives
Betty200/50 damage. Native projectile conversion already reads these real
asset fields. Do not copy Python launch/trigger data or infer scrambler should
explode just because its inherited damage fields are nonzero. Both are untimed;
the nominal3500 fuse is not authority to schedule an explosion.

Additional C1 friendly-scrambler compass evidence:43372e reads centity+164
(nextState+80 owner);433734..433741 indexes a19-owner list at16c78d0 and marks
its location valid, then writes the decoded entity origin. Draw435af0 consumes
that list and material16d9bc0 (compassping_scrambler_friendly, registered44ecd0).
The function entry immediately before433710 is obfuscated; static callers were
not resolved in this pass. This confirms owner+80 is a real client input,
without establishing the official server deployment caller.

Remaining implementation requires the native thrown-missile to script-mover
transition and actual activation/deletion/pickup/damage policy. No arbitrary
stand-in model, invisible proxy entity, radius-damage substitute, or guessed
arming timers were introduced. The exposed primitive and captured wire fields
are ready; complete scrambler deployment remains unfinished.
