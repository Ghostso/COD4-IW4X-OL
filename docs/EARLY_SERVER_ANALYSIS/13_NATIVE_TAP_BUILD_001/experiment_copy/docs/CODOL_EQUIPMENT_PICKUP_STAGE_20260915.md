# Equipment pickup stage

Source written and manually reviewed only. No tests, builds, live edits, process changes, or gameplay claims.

## Ready for parent integration

`obj/equipment-pickup-stage/maps/mp/equipment/_pickup.gsc` implements owner-only use, explicit hint text, exact weapon identity, one-unit stock restoration and successful-write verification before deletion. Full-capacity devices remain deployed. It refuses a weapon no longer owned (class changed), instead of silently granting an old loadout weapon. This uses retained native get/setWeaponAmmoStock; setter clamps clip-only items to clip capacity and other stock to player maximum. It assumes stock starts within that native capacity; anomalous above-cap stock needs a native atomic grant facility to avoid clamping the existing count.

Sibling staged Betty/scrambler copies replace their refund loops. Betty previously deleted even when a capacity clamp prevented a refund. Scrambler previously gave start ammo if empty (not necessarily one), and deleted without any refund if nonempty. Betty terminal damage/proximity paths close pickup before detonation begins.

Staged `_weapons.gsc` starts linked script_origin pickup triggers after C4/claymore settle. Actual missiles are deliberately not used as generic use receivers: native missile use is throwback logic. Trigger follows its missile and is deleted on death. C4/claymore existing missile_stuck waits are changed to the verified native stationary notification. Terminal damage, remote detonation and claymore activation close the hint/use path before delayed explosion. Existing native missiles, owners and arrays remain authoritative. Reclamation dispatches independent level cleanup, notifying death before deleting trigger and missile so all child lifecycle threads stop. No duplicate ammo and no retained missile/fuse remain after successful reclaim.

Parent must merge staged differences with concurrent live Betty repairs, not blindly replace the live file. Native generic hint/use and makeUnusable support on script_origin/script_model is required (parent owns).

## C4 detonator root cause

Active watchC4Detonation waits `waittillmatch("detonate", "c4_mp")`. Native HandleClientEvent_240 in _g_active_mp.asm emits event63's detonate notification with zero arguments. This cannot satisfy the script match; double-use succeeds through separate alt_detonate.

Both native emitters discard weapon identity: _bg_weapons.asm PM_Weapon_2400 reads ps+e8 (main weapon), and PM_Weapon_CoDOLOffHandDetonate reads ps+e0 (offhand), then both tail-call PM_AddEvent(63), whose parameter is zero. Parent owns native repair: publish engine identity as predictable event parameter at each producer, consume captured parameter to emit the one weapon-name notify argument. Do not derive the notification from a later mutable current weapon. No script polling workaround was staged.

## All remaining equipment: explicit scope

Verified C1 patch marketplace equipment catalogue (see selection audit):

- Reclaimable deployed objects staged: 1211 claymore_mp,1212 c4_mp,1225 scrambler_mp,1226 bouncingbetty_mp.
- Live fused throwable weapons:1200 frag_grenade_mp,1201 semtex_mp,1204 flash_grenade_mp,1205 smoke_grenade_mp,1206 emp_grenade_mp,1207 concussion_grenade_mp,1208 white_phosphorus_grenade_mp. No generic stock-refund listener installed: deleting one and incrementing stock would reset its running fuse on next throw. Native throwback/carry must retain absolute expiry, weapon identity, owner attribution and cleanup while presenting the hint. Sticky Semtex/active effects require explicit native attachment/effect lifecycle semantics. This is remaining implementation work, not permission-blocked.
-1202 throwingknife_mp: requires native settled-projectile/item pickup and original weapon ammo transfer; no fuse, but no duplicate script proxy should be layered over an existing native conversion. Needs actual current native knife transition audit.
-1209 specialty_tacticalinsertion: perk-driven placeable beacon, not an ordinary inventory missile. Needs native/script deployment/use/destroy and beacon ownership plus spawn reservation cancellation.
-1210 specialty_blastshield: wearable perk, no deployed object to recover. It should not receive a fabricated world pickup.

No trophy or portable radar appears in the verified alpha marketplace equipment rows. Their IW5 reference scripts alone do not prove availability or C1 assets. They are not counted as implemented.

## Reference

Primary plutoniummod/iw5-scripts commit42f3db22261febd7180075842e250d2e0f3d0507, maps/mp/gametypes/_weapons.gsc equipmentwatchuse1488: per-device hint, owner mask, stock+1 then device removal. Stage fixes that reference's unsafe deletion ordering, adds capacity refusal, and preserves native behavior rather than simulating effects.
