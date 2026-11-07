# Mounted-turret muzzle flash — 2026-09-20

**One-sentence defect:** the retained `turret_think_client` queues IW3's
`EV_FIRE_WEAPON_MG42` (38) on the turret entity for every shot, C1 has no event by that name, so
`CODOL_EventToWire` returned -1 and the snapshot writer's "unmapped event" adaptation silently
replaced the turret's fire event with `EV_NONE` on the wire — the client was never told the turret
fired, so it never drew the muzzle flash.

**Fix:** map `EV_FIRE_WEAPON_MG42` to C1's `EV_FIRE_TURRET` (55) and resolve its parameter (the
firing entity's number). Two files, both in `src/codol/snapshot/`.

**This is turret-specific.** It does not touch carried weapons, which the user confirms already
flash, and whose fire path never goes through this event.

---

## 1. Scope: which minigun, and the differential

`turret_minigun_mp` is the map-placed mounted MG (`misc_turret`) on `mp_overgrown`; the crash fix
(`docs/CODOL_MINIGUN_CRASH_20260920.md` §2) establishes that. The user reports muzzle flash works on
other weapons, so this is a differential against the carried-weapon path, not a pipeline audit.

The two fire sites compared:

| | carried weapon | mounted turret |
|---|---|---|
| producer | `hand_take_shot`, `src/codol/weapon/codol_weapon_state.c:1561` | `turret_think_client_340`, `src/asmsource/_g_misc_mp.asm:1974-1979` |
| ring | **player state** (`add_player_event`) | **entity** (`G_AddEvent` on the turret gentity) |
| event | `EV_FIRE_WEAPON` 26 / `EV_FIRE_WEAPON_LASTSHOT` 27 (`src/bg.h`) | `EV_FIRE_WEAPON_MG42` 38 |
| wire ID | 30/31, or 43/44/45/46 via `CODOL_PlayerFireEventToWire` | **none — unmapped** |
| parameter | zero | attacker's entity number |

The divergence is item 1 of the three candidates (the event), not the effect name and not the tag.
Items 2 and 3 are addressed in §4.

---

## 2. Evidence

### 2.1 The producer (MEASURED, our tree)

`src/asmsource/_g_misc_mp.asm:1974`:

```asm
turret_think_client_340:
	mov eax, [ebx]                  ; attacker->s.number  (gentity_s.s is entityState_s, +0 = number)
	mov [esp+0x8], eax              ; parameter
	mov dword [esp+0x4], 0x26       ; 38 = EV_FIRE_WEAPON_MG42
	mov [esp], edi                  ; the turret gentity
	call G_AddEvent
```

`ebx` is the shooter: the preceding `Bullet_Fire` call passes it as arg 0 (`mov [esp], ebx`), and
IW3's symbol `_Z15Bullet_FireP9gentity_sfPK11weaponParmsPKS_i` types arg 0 as the attacking
`gentity_s*`. `gentity_s` begins with `entityState_t s` and `entityState_s` begins with `int number`
(`src/entity.h:416`, and the `entityState_s` header), so `[ebx]` is `attacker->s.number`.

Both fire classes reach this site: the bullet path falls through from `Bullet_Fire`, and the
non-bullet path at `turret_think_client_230` jumps to `_340` (`_g_misc_mp.asm:2328`). Event 38 is
therefore queued on *every* turret shot.

`src/bg.h`'s `BGEvent` enum puts `EV_FIRE_WEAPON_MG42` at index 38 — counted from the file, not
assumed.

### 2.2 C1 has no such event (MEASURED, C1.exe 1.1.1.13)

Dumping all 187 entries of C1's event-name table at VA `0xCD81D8` (the same table
`tools/codol_event_map.py` reads):

```
30 EV_FIRE_WEAPON        43 EV_SV_FIRE_WEAPON            55 EV_FIRE_TURRET
31 EV_FIRE_WEAPON_LASTSHOT                               56 EV_FIRE_SENTRY
```

There is no `EV_FIRE_WEAPON_MG42`. IW4 made the same rename: `iw4mp.pdb` contains
`aEv_fire_turret` and `aEv_fire_sentry` and no MG42 event name.

`tools/codol_event_map.py` matches names exactly, so 38 was simply never emitted into
`src/codol/snapshot/codol_event_map.inc`. (That generator is already stale with respect to the
hand-added semantic overrides in that file — `EV_STOPSOUNDS`, `CODOL_EV_*` — and asserts a mismatch
today, before this change. The `.inc` is hand-maintained.)

### 2.3 C1's own turret code queues EV_FIRE_TURRET with the attacker's number (MEASURED)

C1's spawn table at `0xC3A248` binds `"misc_turret"` to `SP_turret` `0x57F330`, which calls
`G_SpawnTurret` `0x57E8C0`. The turret shot builder is `0x57ACF0` — it reads the turret's weapon from
`[ebx+0xd4]`, the offset `CODOL_OverlayEngineTurret` already publishes as the turret weapon selector.
Its tail:

```
0057af36  mov eax, [ebp+0xc]              ; the attacking entity
0057af39  cmp dword [eax+0x17c], 0        ; ent->client
0057af40  jne 0x57af5e                    ; has a client -> EV_FIRE_TURRET
0057af42  cmp dword [eax+0x180], 0        ; actor/agent
0057af49  jne 0x57af5e
0057af4b  xor edi, edi                    ; parameter 0
0057af4d  lea esi, [edi+0x38]             ; 56 = EV_FIRE_SENTRY
0057af50  mov eax, ebx                    ; the turret entity
0057af52  call 0x572d30                   ; G_AddEvent
...
0057af5e  cmp dword [ebx+0x1c4], 4        ; inlined G_AddEvent, turret entity
0057af65  mov edx, [ebp-4]
0057af68  mov edx, [edx]                  ; attacker->s.number  == the parameter
0057afce  mov dword [eax+ecx*4+0x120], 0x37   ; client ring:  55 = EV_FIRE_TURRET
0057afd9  mov dword [eax+ecx*4+0x130], edx    ;               parameter
0057b005  mov dword [ebx+eax*4+0xb4], 0x37    ; entity ring:  55
0057affe  mov dword [ebx+eax*4+0xc4], edx     ;               parameter
```

`G_AddEvent` in C1 is `0x572D30` with the argument registers `eax`=gentity, `esi`=event,
`edi`=parameter. Verified against this repo's own prior measurement: at `0x543F4C`,
`lea esi,[ebx+0x5a]` with `ebx == -1` yields 89, and `docs` already record that site as "queues
event 89 through G_AddEvent 572d30". `0x572D30`'s body writes the client playerstate ring at
`client+0x118/0x120/0x130` when `ent->client` is set and the entity ring at `ent+0xb0/0xb4/0xc4`
otherwise — the same two-ring shape as the retained `G_AddEvent`, and the same shape as the inlined
copy above.

So C1 emits **exactly** `(turret entity, EV_FIRE_TURRET, attacker->s.number)` for a
player/actor-driven turret, which is byte-for-byte the shape the retained producer emits as event 38.
`EV_FIRE_SENTRY` (56) is C1's no-client branch; the retained tree has no producer for it.

Corroboration from the IW3 consumer side: `tools/cod4_dasm/src/_cg_event.asm`'s `CG_EntityEvent`
jump table (line 3099, indexed by the raw event ID — entries 26 and 27 are the two
`CG_FireWeapon` arms, matching `EV_FIRE_WEAPON`/`_LASTSHOT`) sends index 38 to label `_2030`
(line 1291), which calls `CG_StartShakeCamera` and then
`CG_FireWeapon(localClientNum, cent /*the turret*/, 38, …)` and indexes `cg_entities` with the event
parameter. That is the routine that spawns the mounted gun's flash; it is driven by this event and
by nothing else.

### 2.4 Where the event died (MEASURED, our tree)

`CODOL_EventToWire(38)` falls through `codol_event_map.inc` to `default: return -1`
(`src/codol/snapshot/codol_events.c`). `entity_event_parameters` in
`src/codol/snapshot/codol_sv_gameframe.c:78-116` then takes its "adaptation" branch:

```c
/* Adaptation: an event slot the mapper cannot translate is published
 * as no event instead of refusing every frame ... */
events[i]=EV_NONE; parameters[i]=0; out[i]=0;
unmapped|=1u<<i;
```

with a once-per-event `Com_DPrintf` ("CoDOL entity %d (type %d): unmapped event %u parameter %u
dropped from the wire"). The suppressed slot is then published as event 0 by
`CODOL_OverlayEngineEntityEventQueueVisible`. The turret entity itself keeps rendering, so the
failure is invisible unless `developer` is on — `bin/home/main/qconsole*.log` currently contains only
the event-2 instances of this line, because the turret crashed on mount before it could ever fire.

The transport downstream of the mapper is fine: eType 11 (`ET_MG42`) carries all nine event fields
in its measured netfield table — `0xb0` (sequence) and `0xb4/0xb8/0xbc/0xc0` + `0xc4/0xc8/0xcc/0xd0`
(events + parameters) are all present in `src/codol/snapshot/codol_entity_fields.inc`. The parameter
codec is -93, 11 bits.

---

## 3. The change

Both files are in `src/codol/snapshot/`, which this pass owns.

**Line endings:** both files were **LF at HEAD but partly CRLF in the working tree** before this pass
touched them (`codol_events.c` 195 CR / 275 lines, `codol_event_map.inc` 134 CR / 144 lines), an
uncommitted, pre-existing CRLF-ification that was already producing a whole-file `git diff` for each
of them. Per the standing rule ("restore what HEAD has", and `.gitattributes` `* text=lf`), both are
now pure LF, so `git diff --stat src/codol/snapshot/` reports exactly `14 ++` and `14 ++` — the lines
added here and nothing else. Nearby files that are legitimately CRLF *in HEAD as well*
(`codol_engine_state.c` 2045/2045, `codol_asset_registry.c` 2334/2334) were not touched.

### `src/codol/snapshot/codol_event_map.inc`

```c
    case EV_FIRE_WEAPON_MG42: return 55;
```

placed after the `EV_FIRE_WEAPON_LASTSHOT` case, with the C1 addresses above in the comment.

### `src/codol/snapshot/codol_events.c` — `CODOL_EventParameterToWire`

```c
    case EV_FIRE_WEAPON_MG42:
        if(parameter >= MAX_GENTITIES) return -1;
        *out=parameter; return 1;
```

This case is required in addition to the ID mapping: `entity_event_parameters` drops a slot whose
parameter does not resolve just as readily as one whose ID does not, and the resolver's `default`
returns 0 (unimplemented). The accepted domain is `0 .. MAX_GENTITIES-1` = `0..2047`
(`GENTITYNUM_BITS` 11, `src/entity.h:513`), exactly the width of the -93 wire field, so every legal
entity number including `ENTITYNUM_NONE` fits and nothing wider is accepted.

`CODOL_PlayerFireEventToWire` deliberately does **not** special-case this event: its 43/44/45/46
hand family is the player-state fire encoding, and a turret event lives on the turret entity, which
has no client. It falls through to `CODOL_EventToWire` → 55, which is correct if a producer ever
puts it on a playerstate ring.

### Build

Objects only, never a bare `make`:

```
make obj/codol/codol_events.o obj/codol/codol_engine_state.o obj/codol/codol_sv_gameframe.o
```

All three compile clean; the only warnings are the pre-existing `-Wmisleading-indentation` in
`codol_engine_state.c:777` and the pre-existing `-Wswitch` set in `codol_sv_gameframe.c`. Nothing was
linked and nothing was copied into `bin/`.

---

## 4. The other two candidates, and what is not changed

**The effect name (candidate 2) is fine.** `docs/zone_assets/ALL_fx.txt` ships
`muzzleflashes/minigun_flash_view` in `mp_overgrown` itself (line 1775) *and* in
`common_gametype_mp` (1771), and the world flash `muzzleflashes/minigun_flash` in
`common_gametype_mp` (1763). A fastfile's asset list is the closure of its dependencies, and
`mp_overgrown`'s only weapon is `turret_minigun_mp` (`docs/zone_assets/mp_overgrown.txt:229`), so the
view flash is in that zone *because* that weapon names it. Both flashes therefore exist in a mounted
zone. (MEASURED for the asset/zone membership; INFERRED for "the def names them", from the
dependency closure.)

Note that the flash is resolved **client-side** from the client's own copy of the WeaponDef
(`viewFlashEffect`/`worldFlashEffect`, `src/xassets/weapondef.h:229`); the server's copy, loaded in
`src/codol/weapon/codol_weapon_loader.c:67`, is not what the client draws. There is nothing for the
server to register or publish for a muzzle flash beyond the fire event, which is why carried weapons
already work and why **no change is needed in `src/codol/weapon/**` or in
`src/codol/assets/codol_effects*.c`**. Nothing is handed back to the weapon-side worker.

**The tag (candidate 3) cannot be wrong here** in a way the server could cause: the tag lookup is
`CG_FireWeapon`'s, against the turret XModel the client loads from its own fastfile. If it were
broken, IW3's identical path would be broken too. Not investigated further; if the flash is still
absent after this change, that is the next thing to look at, and it is a client-asset question, not
a server one.

**Already published, unrelated:** `turret_think_client` also sets eFlags `0x40` on the turret one
frame per shot, and `CODOL_OverlayEngineTurret`
(`src/codol/snapshot/codol_engine_state.c:1722-1726`) already translates it to C1's `0x200`. C1's
consumers of that bit are its spin/heat updates (`0x57b229`), not the flash, so it is not a
substitute for the event.

**Not covered:** `EV_FIRE_SENTRY` (56). C1 emits it for a turret whose attacker has neither a client
nor an actor; the retained tree has no such producer, so there is nothing to map yet. If sentry
killstreaks later fire server-side without a client attacker, they will need `56` and a zero
parameter.

---

## 5. Verification status

Static and offline only. The change is not linked, not deployed and not seen in game; no server,
lobby or client was started or stopped. What is established is that the event the turret raises now
has a wire ID and a resolved parameter, that eType 11 carries the fields to deliver it, and that the
ID and the parameter match what C1's own turret code writes.

Live check when someone next mounts the Overgrown turret: the muzzle flash should appear, and with
`developer 1` the line

```
CoDOL entity <n> (type 11): unmapped event 38 parameter <m> dropped from the wire
```

must *not* appear. Before this change it was the expected first symptom.
