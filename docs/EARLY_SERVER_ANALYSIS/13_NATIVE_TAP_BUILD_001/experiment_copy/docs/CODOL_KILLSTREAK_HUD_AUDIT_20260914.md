# Killstreak action-slot publication, 2026-09-14

Status: native source written; parent review/build pending. No tests or process
changes performed by this worker.

The alpha0022 overlay `gsc_overlay/maps/mp/killstreaks/_killstreaks.gsc`
grants the earned streak weapon in `giveKillstreakWeapon`, then calls
`self _setActionSlot(4, "weapon", weapon)` at line624. Use clears slot4 at
line313. This is the IW4-style earned-streak action route. Its separate
`_codol.gsc` installs replacement killstreak behavior, not action-slot netfields.
Local `scripts/codol/maps/mp/gametypes/_class.gsc` selects per-class loadout
streaks through the native profile bridge. Merely reading those selections
does not make an earned action slot appear.

The registered `setactionslot` method still targeted retained IW3 assembly.
That implementation accepts slots1..4 and writes retained ps+0x600 types and
ps+0x610 weapon parameters, both indexed by slot-1. No C1 snapshot publisher
read these arrays. Consequently scripts could grant a weapon and set their
action slot while C1 received empty action-slot fields.

C1 setter0x516740 establishes five slots. At0x5167cf it checks slot-1 <=4.
Weapon mode resolves an already registered name through0x41f6c0 at0x51680a;
0x516829 writes type1 to ps+0x540+4*slot, and0x51683a writes the weapon ID to
ps+0x554+4*slot. Altmode sets type2 at0x516865; nightvision sets type3 at
0x516894; empty string sets type0 at0x5168c3. Nonweapon modes leave the last
parameter unchanged. C1 netfields corroborate types0x544..0x554 at2 bits and
weapon parameters0x558..0x568 at11 bits.

Implemented native `codol_action_slots.c/.h` with all five slots and the four
action types. The script setter validates receiver, integer slot, type string,
and registered weapon name. It neither grants nor precaches a weapon. Storage
is part of `codol_ps_ext_t`, so captures, delayed archives, spectator follows,
and state copies carry the selected actions independently of the live client.
Internal archive block follows icon overrides: changed bit, then five pairs
of type2 and native weapon7. Reader and writer changed together, with bounds
preflight and atomic read commit. Existing internal native registry is128
weapons; client weapon IDs are mapped to their11-bit C1 domain at publication.

`codol_sv_gameframe.c` publishes captured slot state using `CODOL_WeaponToWire`,
never the current live client's action store. Missing mappings fail the frame
instead of publishing the wrong weapon. Spawn clears only the live action
state alongside the playerState memset; connect/disconnect resets clear it;
map reset clears every extension through the existing complete reset. The
existing spectator bundle compile-time size assertion remains authoritative.

Separate icon overrides are already implemented: C1 setter0x549300 stores
eight material overrides; UI consumer0x5e41b0 reads action icon fields from
ps+0x574+4*slot, slots1..5. That facility does not replace missing action types
and weapon parameters. This change repairs earned action publication; it does
not assert that unearned class streak previews or all mode-specific HUD
playerdata fields are complete.

Changed integration sites: `scr_vm_main.c`, `g_client_mp.cpp`,
`codol_game.c`, `codol_sv_gameframe.c`, `codol_playerstate_ext.c/.h`.
No local class/equipment/perk scripts changed by this worker.


## Selected reward previews and progress (second pass)

C1 setters directly own these playerState words:
- 0x516fb0 / 0x51704d: count at ps+0x64, clamped 0..256.
- 0x517110 / 0x5171fe: reward ID at ps+0x68+4*slot. Arguments ID, slot;
  negative ID becomes0, ID above128 errors; slot clamps0..4.
- 0x5172f0 / 0x5173a5: required kills at ps+0x7c+4*slot. Arguments target,
  slot; target clamps0..25 and slot clamps0..4.
Getters 0x517070/0x517230/0x5173d0 read the same words. Invalid getter slot
returns0. Native method receiver and integer arguments are validated.

UI consumers prove these are actual HUD inputs: 0x45c3a0 reads killstreak,
0x45c4c0 reads killstreakID0..4, 0x45c500 reads killstreakTarget0..4.
0x45c3e0 computes the next positive target above current count among active
IDs, or the maximum achieved target. These are distinct from earned weapon
action slots. Netfields carry count/IDs as8bits and targets as5bits.

New codol_killstreak_hud.c/.h implements all six script methods, live state
reset, and captured-state publication of all11 fields. Extension copies travel
through archive/spectator capture; no live client lookup during publication.
Archive block directly after action slots: changedbit, count9, then5 pairs
ID8/target5. Reader/writer ordering matches, malformed reads fail atomically.
The 9-bit internal count preserves the C1 setter's valid256, while8-bit wire
publication retains low8bits. Explicit C1 sender overflow-path tracing remains
unverified; normal playable target range0..25 is unaffected.

Native _killstreaks.gsc override retains source attribution/comments and vendor
killstreak module initialization, but removes Python _codol::init replacement
of actual killstreak behavior with simplified server effects. It publishes
progress from checkKillstreakReward, restores script progress after spawn,
and resets published progress on death. The existing earned/consumed queue
continues to grant weapons and assign/clear action slot4. Parent-owned _class
publishes sorted selected reward IDs and adjusted targets (including fourth
profile selection); these previews remain separate from earned inventory.

Removed Python-only overrides include double_uav/blackbird/advanced_uav/sr71,
sam_turret/mortar/rcbomb/rcxd/dogs. Availability of real native modules for those
names has not been demonstrated here; do not count them as supported because
Python previously installed substitute effects.

Integration touched scr_vm_main.c, g_client_mp.cpp, codol_game.c,
codol_sv_gameframe.c, codol_playerstate_ext.c/.h, and new native helper/script.
No tests, builds, restarts, or live verification performed by this worker.
