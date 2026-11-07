# CoDOL snapshot bitmask audit (2026-09-16)

Goal (user): "audit all of the bitmasking the C1 client does for snapshots so
the snapshots can be 1:1 from server to client."

Method: every C1 1.1.1.13 snapshot reader was re-disassembled from
`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe` (unpacked, ImageBase
0x400000) with capstone; every post-decode mask/bit-test on the decoded fields
was collected from bg/cg (0x405000-0x4A0000) and the game module
(0x50B000-0x520000); the result was diffed against every producer in
`src/codol/snapshot/*` (and the retained producers they copy). All VAs below are
C1 VAs. Field names are IW4-style hints only; the offsets and the C1 reader are
the authority (see memory: "the netfield table's offsets are right but its IW4
names lie").

Counts: 244 playerstate fields + 7 trailing sections + 22x66 entity fields +
77 clientstate + 24 actor + 42 hudelem + 6 objective fields audited.
Verdicts: everything on the wire decodes 1:1 (encodings, widths, gap coders,
hint passes, delta bases) — no WRONG-ENCODING / WRONG-WIDTH found. Semantic
(bit-meaning) discrepancies: 1 fixed (EF_VOTED collides with C1
EF_VEHICLE_ACTIVE), 6 documented as NOT-PUBLISHED / MASKED-DIFFERENTLY with the
evidence for the owners of those files.

## 1. Wire structure as C1 reads it vs. as the server writes it

### 1.1 svc_snapshot body (CL_ParseSnapshot 0x49D800 / codol_snapshot.c)

| # | C1 read | server write (codol_snapshot.c:306-325) | verdict |
|---|---|---|---|
| 1 | ReadLong serverTime (0x49D89B) | WriteLong ctx->server_time | MATCH |
| 2 | ReadByte deltaNum (0x49D8C6) | WriteByte delta (<=31) | MATCH |
| 3 | ReadByte snapFlags; only bit 8 tested here (0x49D965 -> baseline) | WriteByte flags; PrepareServerSnapshot forces 8 on baseline (codol_sv_snapshot.c:261) | MATCH |
| 4 | ReadBit "delta playerstate" (0x49DBD2); 1 without base -> error 0xC490F8 | WriteBits(base!=NULL,1) | MATCH |
| 5 | MSG_ReadDeltaPlayerstate 0x5A19C0 (§2) | CODOL_WritePlayerState | see §2 |
| 6 | anim cmds 0x49D700 / 0x5A1170 | CODOL_WriteAnimCommands (codol_animcmd.c:232) | MATCH (type 4-bit, 7=ent, 8=time, terminator type 0) |
| 7 | actors 0x49D2F0 (idx 5 bits, ReadDeltaStruct 24 fields, indexBits 3) | CODOL_WriteActors (codol_actors.c:27-80) | MATCH |
| 8 | entities 0x49CA90 / MSG_ReadDeltaEntity 0x5A0C00 | CODOL_WriteEntities (codol_entities.c:63-129) | MATCH (§4) |
| 9 | clients 0x49CEC0 (idx 5 bits, ReadDeltaStruct 77, indexBits 1, flag 0) | CODOL_WriteClients (codol_clients.c:78-135) | MATCH |
| 10 | dynent/glass 0x4484A0 (2-bit state, idx 11 bits, 0x400 sentinel) | CODOL_WriteGlass (codol_glass_snapshot.c:362) | MATCH |
| 11 | msg->overflowed -> snapshot silently dropped (0x49DCD4); commandTime==0 -> invalid (0x49DCF6) | - | note: every codec fault below surfaces as a silent drop, never a Com_Error |

### 1.2 MSG_ReadDeltaField 0x5A0510 codecs vs CODOL_WriteDeltaValue (codol_delta.c:122-228)

| bits | C1 decode (VA) | server encode | verdict |
|---|---|---|---|
| >0, -8, -16 (default arm 0x5A092C) | Bit==0 -> to=0; else ReadBitsCompress(n)^(from&mask), sign-extend if bits<0 | presence=(to!=0); compressed((from^to)&mask,n) | MATCH |
| 0 (float, 0x5A053B) | b0=0 -> ±0 (sign bit); b0=1,b1=0 -> 13-bit `((int)from+0x1000)^v)-0x1000`; b1=1 -> ReadLong^from | codol_delta.c:215-217 + trimmed(13,4096) | MATCH (trunc(f) == C1 `(int)from`) |
| -88 (0x5A067B) | ReadLong ^ from | WriteLong(from^to) with the history-ring base | MATCH (needs real base: codol_history.c commit stores *reached* values) |
| -87 (0x5A0817) | ReadShort*180/32768 absolute | angle() short | MATCH |
| -100/-79 (0x5A03D0) | b=1: table delta; b=0,b=0: ReadShort absolute; b=0,b=1: 12-bit delta | WriteBits(0,2)+short (absolute arm) | MATCH |
| -97/-70/-72/-74 (0x59FFB0) | Bit==0 -> serverTime-Bits(8); else ReadLong | delta in 0..255 -> bit0+8 bits else bit1+long | MATCH |
| -71/-73/-78/-80 (0x5A09C0) | ReadLong raw | WriteLong(to) | MATCH |
| -75 (0x5A05BA) | Bit==1 -> from+1+Bits(5); else 11-bit xor | codol_delta.c:180-188 | MATCH |
| -76 (0x5A08D3) | Bit==1 -> from+Bits(5)-16; else 8-bit signed xor | :189-197 | MATCH |
| -77 (0x5A07B5) | ReadBitsCompress(8) | compressed(to,8) | MATCH |
| -93/-94/-84 | Bits(11)/ReadByte/Bits(7) absolute | :158-162 | MATCH |
| -96 (0x5A0040) | bit->0x7FE; bit->0; else Bits(3)\|ReadByte<<3 | :170-176 | MATCH |
| -98 (0x5A0140) | Bit==1 -> Bits(30) absolute; Bit==0 -> from^(1<<Bits(5)) | always the 30-bit absolute arm; fails if value>0x3fffffff | MATCH (single-bit-toggle arm unused; fine) |
| -92/-91/-90, -83/-82/-81 (0x5A0180/0x5A0230) | Bit==0 -> from+(Bits(7)-64); Bit==1 -> v=Bits(16); base=fistp(POS_BASE[axis]+2^-30); fromI=fistp(from+2^-30); to=((fromI-base+0x8000)^v)+base-0x8000 | position(): floor(x+0.5) both sides, base=round_even(center+2^-30) (codol_delta.c:20-30,103-120); always the wide arm | MATCH (fistp default RNE of x+2^-30 == floor(x+0.5) for every value the server can hold; POS_BASE = CS 16 map center, same string both sides) |
| -85 colour (0x5A0856) | bit->alpha toggle; else bit(sameRGB) [3 bytes], Bits(5)<<3 | :198-214 | MATCH |
| -86 (0x5A082C) | Bits(6)/10 | :166-169 | MATCH |
| -65 (0x5A0707) | Bits(10)*100 | :163-165 | MATCH |
| -99 (0x5A0696) | bit0->0; 1,1 long xor; 1,0 12-bit | :219-222 | MATCH |
| -89 (0x5A0617) | float without ±0 arm | :218 | MATCH |

Gap coders: playerstate main loop 0x5A1AC2 (bit==1 -> 1, else 1+15k+Bits(4)) ==
codol_playerstate.c:94-101; hudelem 0x5A18B2 (bit, 3-bit chunks, 7 continues)
== codol_player_arrays.c:60-70; MSG_ReadDeltaGap 0x5A09D0 (indexBits 1 =
unary; else bit==1 -> 1, else 1+max*k+Bits(n)) == codol_entities.c:24-31 (3),
codol_actors.c:36-46 (3), codol_clients.c:92-96 (unary). All MATCH.

## 2. Playerstate (MSG_ReadDeltaPlayerstate 0x5A19C0)

Structure (C1 -> server): memcpy(to,from,0x3368) 0x5A1A1A; predictedDeltaFlag =
ReadBit 0x5A1A24 (= server rov bit, codol_playerstate.c:117); lc = Bits(8),
lc>245 -> overflow 0x5A1A6C (server lc = last sent index+1, 8 bits); gap loop
while i<lc-1 with noXor = predictedDeltaFlag && changeHint==3 (0x5A1B5F; server
base 0 when rov && hint==3, :125); changeHint==2 second pass over fields[0..lc-2]
value-only (0x5A1BE2; server :128-131, hint-2 slots below lc-1 excluded from the
gap loop, the lc-1 slot itself stays in it); when predictedDeltaFlag==0 the
client overwrites origin/velocity/bobCycle/movementDir (0x5A1C67..) and
viewangles (0x5A1CD1, if clc+0x80260==1) from its own prediction ring — so hint-3
fields sent with rov=0 would be discarded; the server sends hint-3 only with
rov=1 (:56). MATCH.

Trailing sections (0x5A1CFB..0x5A206F) vs codol_player_arrays.c:147-223:

| S | C1 | server | verdict |
|---|---|---|---|
| 1 stats | gate; mask Bits(4); bit0 ps+0x190 short (health), bit1 +0x194 short, bit2 +0x198 short, bit3 +0x19C byte | mask 5 (health, maxhealth) | MATCH (stats[1]/[3] never sent; C1 only reads 0x190 for alive/health) |
| 2 clip array ps+0x3D8 (16x12) | loop: idx Bits(4); key Bits(10) (0x3FF -> -1, 0x5A1DE6); 2x [bit ? Bits(9)]; continue bit. Consumer BG 0x415F20 scans 15 entries matching elem[0] to WeaponDef+0x570 and tests elem[1]!=0 | clip_mask 0x7fff every frame, key 1023 for empty, ammo[0]=clip, ammo[1]=left-hand/duplicate | MATCH on the wire; key semantics owned by the ammo-bindings worker (elem[0] must equal WeaponDef+0x570 of the held weapon) |
| 3 weapons ps+0x2A0[15] + flags ps+0x2DC[15][5] | gate; 15x: present bit; if present: bit -> Bits(10) index; then 5x ReadBit -> bytes 0x2DC+i*5+k (0x5A1EBD..0x5A1F04) | 15x present, index-present, 10 bits, 5-bit flags LSB-first | MATCH. NOTE: the 5 bytes are booleans, not ammo: byte1 = "possessed" (0x419D4B, 0x47AD9B, with WeaponDef+0xBD5), byte2 tested at 0x4191C0/0x41E620. With dvar "1289" (default 1) BG_GetWeaponSlot 0x40AB60 returns slot 14 (ps+0x322) for every weapon without searching, so only slot 14's flag bytes are consulted by those callers |
| 4 reserve ps+0x360 (16x8) | idx Bits(4); Bits(10) type; Bits(11) ammo; continue bit. Consumers 0x422B10/0x422B70 key on [+0]==weaponIndex | reserve_mask 0x7fff; type = registry ammo key | MATCH on the wire |
| 5 objectives ps+0x5D0 (32x0x24) | gate; ALL 32: Bits(3) state + ReadDeltaStruct(6, 0xC39818 {+4/0,+8/0,+C/0,+0x20/12,+0x10/11,+0x14/4}, indexBits 1); lc = last index | write_objectives: gate off only when both sides empty; 3-bit state; changed bit; 3-bit last index; unary gaps | MATCH (field 5 = teamNum: left 0; team filtering is done server-side per recipient, see seed_objectives comment) |
| 6 hudelems | gate; sub_5A1830 archival (ps+0x1EB8) THEN current (ps+0xA60); count Bits(5); per elem lc Bits(6), 0 = unchanged, else last=lc-1; 42-field table 0xC39860; elems count..30 zeroed | hud_array(0) then hud_array(1); lc=0 for unchanged; type must be nonzero | MATCH |
| 7 ps+0x3340 words | gate; idx Bits(5), Bits(16) | always gate 0 | MATCH (nothing on C1 reads it client-side) |

### 2.1 The 244 fields

Columns: idx | ps off | bits/hint | C1 encoding | C1 consumers (bit tests / masks, VA) | server producer (file:line) + mask | verdict.
`ES` = src/codol/snapshot/codol_engine_state.c, `PS` = codol_playerstate.c,
`DEF(n)` = default arm (presence bit + n-bit xor).

| idx | off | bits/h | C1 enc | C1 consumers | server producer / mask | verdict |
|---|---|---|---|---|---|---|
| 0 | 0000 | -97 | TIME | commandTime: Pmove 0x416C74, CL_ParseSnapshot 0x49DCF6 (0 -> invalid) | ES:337 ps->commandTime | MATCH |
| 1 | 00f0 | -75 | SEQ | eventSequence `and 0x7ff` (40+ sites 0x408FA4..0x418557) | ES:1293 epoch&2047 | MATCH |
| 2 | 0114 | -75 | SEQ | oldEventSequence cmp 0 0x50F552 (server module) | none (0) | MATCH (client-owned cursor) |
| 3 | 026c | -16 | DEFs(16) | weaponTime cmp 0 x11 | ES:615 weaponTime | MATCH |
| 4 | 04a0 | -70/3 | TIME | int time lerped 0x45E987 | none; force-sent while 0x348!=0 (PS:50) as 0 | MATCH (mirrors C1 writer 0x5A44B0 predicate) |
| 5 | 00c8 | 16 | DEF | torsoTimer 0x405C0A | ES:334,209 | MATCH |
| 6 | 034c | -88 | RAW32 | float only (int cmps on +0x34c are WeaponDef) | ES:438 aimSpreadScale | MATCH |
| 7 | 00c4 | 11 | DEF | legsAnim: `and ~0x400` 0x405BB9, toggle 0x405BDF | ES:333,210 passthrough <=2047 | MATCH |
| 8,11,10 | 001c,0020,0024 | -88/3 | RAW32 | origin; client restore 0x5A1C67 when rov=0 | ES:386 float bits, base 0 when rov | MATCH |
| 9 | 0268 | 11 | DEF | weapAnim (no imm consumer) | ES:615 remap, 0x200->0x400 | MATCH |
| 12 | 0018 | 8/3 | DEF | bobCycle restore 0x5A1C91 | ES:344 | MATCH |
| 13,14,16 | 002c,0028,0030 | -88/3 | RAW32 | velocity | ES:387 | MATCH |
| 15 | 00e8 | -8/3 | DEFs | movementDir cmp 1/2/3/4/6/9/0xC | ES:344 | MATCH |
| 17 | 0278 | 6 | DEF | weaponstate enum cmp 6/7/8/0xB/0x15, writes 0..0x1B | ES:616 CODOL_TranslateEngineWeaponState | MATCH (translation table ES:450-490) |
| 18,19,33 | 0150,014c,0154 | -87 | A16 | viewangles; restore 0x5A1CD1 | ES:393; force predicate PS:36-49 = C1 writer 0x5A44B0 | MATCH |
| 20 | 000c | 31 | DEF(31) | pm_flags bits tested: 1,2,4,8,0x10,0x40,0x100,0x200,0x400,0x800,0x2000,0x4000,0x8000,0x10000,0x80000,0x100000,0x400000,0x800000,0x8000000,0x10000000,0x40000000 (0x41223D,0x46AF28,0x40A581,0x4095D0,0x406094,0x40FE2F,0x410A5A,0x416425,0x41296A,0x413D91,0x4093B0,0x40F91D,0x40F813,0x41BD87,0x414EBC,0x406160,0x409225,0x412EA9,0x41C07A,0x4160A2,0x4089DC) | ES:254 verbatim; RMW 0x80000 <- controlsEntNum (codol_player_links_wire.c:271) | MATCH (retained producers store C1 numbering, ES:230-253 evidence; bit 31 unsendable, unread) |
| 21-24 | 00f4-0100 | 8 | DEF | events ring 0x418535 | ES:1287 event id remap (codol_event_map.inc) | MATCH |
| 25 | 0118 | -75 | SEQ | unpredictableEventSequence | script/codol_script_events.c:55 | MATCH |
| 26 | 011c | -75 | SEQ | cursor | none | MATCH |
| 27-30 | 0104-0110 | -93 | ABS11 | eventParms | ES:1288 CODOL_EventParameterToWire | MATCH |
| 31 | 00cc | 11 | DEF | torsoAnim `and ~0x400` 0x405C25 | ES:334,211 | MATCH |
| 32 | 00ec | -98 | BITFLAG | eFlags (ps-owned readers): PmoveSingle `or 0x100` 0x4161EB / `and ~0x100,~0x200` 0x41627F; mantle `or 0x10000` 0x40A102 / `and ~0x10000` 0x40A984; stance 0xC 0x40A587; 0x100C00 0x413DBF; player/vehicle 0x100000 (0x4817CA + 29 sites) | ES:174 verbatim | **FIXED**: retained vote code set IW3 EF_VOTED 0x100000 = C1 EF_VEHICLE_ACTIVE (src/g_sv_cmds.c:349, src/g_cmds.c:598 now `#ifndef CODOL_SERVER`). Other IW3-only defines (EF_TALK 0x200000, EF_TAUNT 0x400000, EF_AIMDOWNSIGHT 0x40000, EF_MANTLE 0x8000) have no C writer; C1 mantle 0x10000 is produced by codol_pmove_c1_mantle.c |
| 34 | 024c | -88 | RAW32 | holdBreathScale float (fld only) | ES:382 | MATCH |
| 35 | 00c0 | 16 | DEF | legsTimer 0x405BA0 | ES:333,208 | MATCH |
| 36,37 | 01bc,01c0 | 8 | DEF | none | none | MATCH (unused) |
| 38 | 015c | -88 | RAW32 | viewHeightCurrent 0x411D80 | ES:374 | MATCH |
| 39,40 | 0240,0244 | -97 | TIME | sprint start/end 0x40F735/0x40F77D | codol_sprint_state.c:242-243 | MATCH |
| 41 | 0234 | -97 | TIME | dive-end / disableWeapons stamp 0x513E4F | ES:257 dive_end_time | MATCH |
| 42 | 0158 | -8 | DEFs | viewHeightTarget cmp 0x16 0x412183 | ES:368 | MATCH |
| 43 | 033c | 10 | DEF | weapon: bg_weaponDefs[idx] with NO bound check (0x4160CD, 0x419CEB) | ES:410 CODOL_WeaponToWire | MATCH (server must never publish an unbuilt index: 0x47C1F7 fault) |
| 44 | 0340 | 10 | DEF | altmode cmp 0/1/3 (0x418EEA,0x419791,0x43CAF8) | ES:410 | MATCH |
| 45 | 0348 | -88 | RAW32 | fWeaponPosFrac (fld x59) | ES:438 | MATCH |
| 46 | 00d8 | 10 | DEF | damageTimer cmp 0 0x416795 | ES:289 field_bits(10) | MATCH |
| 47 | 0248 | 16 | DEF | sprint allowance 0x50C88B | codol_sprint_state.c:244 | MATCH |
| 48 | 0270 | -16 | DEFs | weaponDelay | ES:616 | MATCH |
| 49,75,208 | 00a0,009c,00a4 | -100 | ANGLE | delta_angles (0x4141D3) | ES:392 | MATCH |
| 50,52-54 | 0120-012c | -93 | ABS11 | unpredictable events | codol_script_events.c:57 | MATCH |
| 51 | 00a8 | 11 | DEF | groundEntityNum ==0x7FF x23 | ES:362 | MATCH |
| 55 | 0284 | 11 | DEF | second-hand anim | ES:826/839 | MATCH |
| 56 | 0008 | -16 | DEFs | pm_time cmp 0x708 0x409400 | ES:341 | MATCH |
| 57 | 0328 | 10 | DEF | offhand: bg_weaponDefs[idx] unchecked (0x418255) when weapFlags&2 (0x41F850) | ES:410 | MATCH |
| 58 | 0010 | 26 | DEF | otherFlags bits 2,0x10,0x20,0x200,0x800(no-predict 0x45F44A),0x1000(0x4817BB),0x1800,0x8000,0x20000,0x80000,0x200000,0x400000,0x1000000,0x6000000(0x40A4C5) | ES:185 verbatim; RMW 0x400 EMP (codol_radar_state.c:483), 0x18 thermal, 0x82 camera (links_wire.c:275) | MATCH (POF_PLAYER 0x1000/POF_FOLLOW 0x800 under CODOL_SERVER, g_shared.h:422; bit 26 unsendable) |
| 59 | 0180 | 8 | DEF | damageYaw | ES:293 | MATCH |
| 60 | 0144 | 11 | DEF | viewmodel: `and 0x7ff` 0x440E44 | ES:1339 model slot <2048 | MATCH |
| 61 | 0148 | 11 | DEF | viewhands cmp 0 | ES:1333 | MATCH |
| 62 | 0038 | 11 | DEF | throwback owner 0x7FF (0x41C292..) | ES:748 | MATCH |
| 63 | 0254 | 0 | FLT | moveSpeedScaleMultiplier | ES:375 | MATCH |
| 64 | 0140 | 8 | DEF | clientNum cmp vs ent 0x4819BD | ES:362 | MATCH |
| 65 | 0098 | 16 | DEF | REAL speed (fild 0x410183) | ES:345 | MATCH |
| 66 | 01b0 | 16 | DEF | viewlocked_entNum 0x7FF 0x51FFB3 | ES:323 | MATCH |
| 67 | 0294 | 6 | DEF | hand state cmp 6/8 | ES:827/841 | MATCH |
| 68 | 0090 | 16 | DEF | REAL gravity (fild 0x410AD4) | ES:345 | MATCH |
| 69,70 | 05b0,05b4 | 0 | FLT | none | none | MATCH |
| 71 | 017c | 8 | DEF | damageEvent 0x45E685 | ES:292 | MATCH |
| 72 | 0208 | 11 | DEF | cursorHint cmp 0 0x45F868 | codol_usehint_wire.c:222 | MATCH |
| 73 | 01ec | 11 | DEF | linkWeaponEnt 0x7ff 0x4711AA | ES:367 / links_wire.c:294 | MATCH |
| 74 | 01f0 | 6 | DEF | server-module only | none | MATCH |
| 76-80,106,139,140 | 04bc-04cc,04b4,04b0,04b8 | 8 | DEF | perks (no bit tests) | codol_perks.c:83 | MATCH |
| 81,82 | 01cc,01d0 | 2 | DEF | none | none | MATCH |
| 83,84,85,86 | 0184,0188,00dc,00e0 | 8,7,16,2 | DEF | damage pitch/count/duration/flinch | ES:294,295,290,291 | MATCH |
| 87 | 0344 | 21 | DEF(21) | weapFlags: 1 (`and ~1` PmoveSingle 0x416075), 2 (46 sites, 0x41F850), 4 (0x4189AA hold-breath, 0x45765C, 0x47DAF0), 8 (0x43C509 friendly crosshair colour; PM 0x41DAAE `if(&8){ps+0x34=0;return}`), 0x10 (0x43C546/0x43A52F enemy colour), 0x80 (0x40C924 returns 0 = weapon unusable, 0x419C3F,0x41B0A3,0x41BC00,0x41C60E,0x41CA9D,0x4547FB,0x486778), 0x100 (0x41B32C), 0x200 (0x422407; client clears 0x41BB4A), 0x880 (0x480F37,0x4817AF), 0x1000 (client sets/clears 0x41979A/0x4197A6), 0x10000 (client clears 0x41A0C0), 0x20000/0x40000/0x80000 (0x41C5A0: 3 gates paired with WeaponDef flags 0x4000/0x8000/0x10000), 0x100000 (0x48112B). `cmp [..+0x344],7/8/9/0xB` sites are WeaponDef+0x344, NOT ps | composed: bit 2 ES:746; 0x9d ES:871; 0x800 ES:852; 0xE0000 all-or-nothing from native 0x1000 ES:882; 0x400 codol_recoil_state.c:64; native 0x100 routed to 0x27c (ES:625) | effective TX mask 0x000E0E9F. MATCH for 1,2,4,8,0x10,0x80,0x400,0x800,0xE0000. NOT-PUBLISHED: 0x200 (client-managed), 0x10000, 0x100000 (no native source; GSC builtins 0x5145CD/0x5145DC only). See §6 for the 0x80 "every frame" question |
| 88,92,99,105 | 0130-013c | -93 | ABS11 | unpredictableEventParms (C1's own server writes 32-bit values here that a -93 field cannot carry; irrelevant to us) | codol_script_events.c:58 <=2047 | MATCH |
| 89 | 0210 | 11 | DEF | cursorHintEnt 0x7ff | usehint_wire.c:224 | MATCH |
| 90 | 0034 | -16 | DEFs | grenadeTimeLeft cmp 0 / -1 (0x41CD1D); zeroed by weapFlags&8 path 0x41DAB7 | ES:747 | MATCH |
| 91 | 020c | -8 | DEFs | cursorHintString -1 | usehint_wire.c:223 | MATCH |
| 93 | 0164 | -8 | DEFs | viewHeightLerpTarget cmp 0x28 | ES:372 | MATCH |
| 94,95 | 0224,0228 | 2 | DEF | radar types cmp 0 (0x43322E/0x433272) | codol_radar_types.c:87-88 | MATCH |
| 96 | 0004 | 8 | DEF | pm_type cmp 8 (x83), 5/6/7, 1/9 | ES:184 | MATCH |
| 97 | 00e4 | 3 | DEF | corpse index | ES:201 | MATCH |
| 98 | 333c | -97 | TIME | 0x41B129 time delta | none | NOT-PUBLISHED (meaning unknown; C1 server module writes it at 0x45D253) |
| 100,101 | 021c,0220 | 1/2 | DEF | radar booleans (0x4331E6, 0x4714C2) | codol_radar_state.c:471,476 | MATCH (hint 2 pass) |
| 102 | 022c | 1 | DEF | - | radar_types.c:91 | MATCH |
| 103 | 0280 | 3 | DEF | hand[0].shotCount (stride 0x1C array, cmp 1..4 0x41A9F7) | ES:626 | MATCH |
| 104,141-150 | 0064,0068-008c | 8,8x5,5x5 | DEF | killstreak hud cmp 0 (0x45C431..) | codol_killstreak_hud.c:91-96 | MATCH |
| 107 | 0168 | 1/2 | DEF | viewheight lerp latch 0x40FFDB | ES:373 | MATCH |
| 108,109,136,137 | 016c,0170,0178,0174 | 0 | FLT | viewAngleClamp | ES:315-318 | MATCH |
| 110 | 0160 | 32 | DEF | viewHeightLerpTime | ES:371 | MATCH |
| 111 | 023c | 1/2 | DEF | sprint latch 0x40F5EC | sprint_state.c:241 | MATCH |
| 112-114 | 01a0,01a8,01a4 | 0 | FLT | prone dir/pitch | ES:319-321 | MATCH |
| 115 | 0214 | 1/2 | DEF | fld only | usehint_wire.c:226 | MATCH |
| 116 | 0264 | 7 | DEF | mantle flags test 4/8/0x20, or 0x10, and ~0x18 | ES:267 | MATCH |
| 117,154,191,204,238 | 054c,0544,0550,0548,0554 | 2 | DEF | action slot types cmp 1 0x48191B | codol_action_slots.c:109 | MATCH |
| 118 | 0238 | 1/2 | DEF | sprintButtonUpRequired | sprint_state.c:240 | MATCH |
| 119 | 00b8 | 32 | DEF | jumpTime | ES:342 | MATCH |
| 120,121,122 | 0594,0598,0590 | -97,16/2,4 | | shellshock block read together 0x478882..0x4788B3 | ES:1318-1320 | MATCH |
| 123 | 035c | 1/2 | DEF | dual-wield cmp 1 (16 sites) | ES:823 | MATCH |
| 124,175,207 | 028c,0288,0290 | -16 | DEFs | hand delay/time/restrict | ES:826/840 | MATCH |
| 125,130,131,132 | 025c,0260,00bc,0258 | 32,4,0,0 | | mantle timer/trans, jumpOriginZ, mantle yaw | ES:265,266,343,264 | MATCH |
| 126-128 | 032c-0334 | 32 | DEF | offhand slots | ES:425 | MATCH |
| 129 | 0338 | 32 | DEF | none | none | MATCH |
| 133,170,226-231 | 331c,3318,3310,3314,3320-332c | 32 | DEF | no in-range reader (0x3314 fild in server module) | none | MATCH |
| 134,135 | 003c,0040 | -16,10 | | throwback time/weapon (cmp 0 x13, 0x46CDBB) | ES:748-749 | MATCH |
| 138 | 027c | 1 | DEF | `and ~1` 0x41B646 (hand[0].shotCount==0 path) | ES:625 (weapFlags>>8)&1 | MATCH per prior evidence (codol_weapon_state.h:196) |
| 151 | 0a54 | 11 | DEF | killCamEntity | ES:356 | MATCH |
| 152,153 | 0a58,0a5c | 11,8 | DEF | none | none | MATCH |
| 155 | 029c | 3 | DEF | hand[1].shotCount | ES:828/842 | MATCH |
| 156,159,190,220,237 | 0560,0558,0564,055c,0568 | 11 | DEF | action slot weapons cmp 0/6 | codol_action_slots.c:112 | MATCH |
| 157 | 0a50 | 32 | DEF | deltaTime cmp 0 | ES:355 | MATCH |
| 158 | 0230 | 8 | DEF | locationSelectionInfo | ES:359 | MATCH |
| 160-162,221-223 | 05a4-05ac,05a0,05b8,05bc | 0 | FLT | none | none | MATCH |
| 163,164,165 | 04ac,04a4,04a8 | -97,-100,8 | | melee charge triple written by 0x415BC0 with PMF 0x10000 | ES:325-327 | MATCH |
| 166,177,178 | 01d8,01d4,01dc | -100 | ANGLE | linkAngles | links_wire.c:298-300 | MATCH |
| 167 | 0014 | 3 | DEF | linkFlags: bit 4 (19 sites: 0x416C60,0x40EC0E,0x4716DA,0x481D9A...), bit 1 (0x4141B8 PM_UpdateViewAngles when pm_type 1\|9: skip delta_angles) | links_wire.c:279-284 writes bits 2/4 only | MASKED-DIFFERENTLY (bit 1 never produced; native source unknown — only matters with pm_type 1/9 view-lock) |
| 168,169,179 | 01e0,01e4,01e8 | -100 | ANGLE | linkWeaponAngles | links_wire.c:288-290 | MATCH |
| 171 | 05c0 | 0 | FLT | spin-up charge | ES:1261 | MATCH |
| 172 | 01f4 | 8 | DEF | loop sound | codol_loop_sound.c:59 | MATCH |
| 173 | 018c | 1 | DEF | damageFlags (no ps reader) | none (ES:286) | MATCH |
| 174,194,205 | 00ac,00b0,00b4 | 0 | FLT | vLadderVec | ES:391 | MATCH |
| 176 | 0298 | 1 | DEF | hand fresh_pull | ES:827/841 | MATCH |
| 180-182 | 01fc-0204 | -100 | ANGLE | none (0x1FC tests are centity_t) | none | MATCH |
| 183 | 3334 | 3 | DEF | 0x406074 (+1 into per-client table) | none | NOT-PUBLISHED (unknown meaning; C1 server module 0x50D187) |
| 184 | 3338 | -97 | TIME | stun 0x41D720 | codol_script_player_builtins.c:452 | MATCH |
| 185,186,187 | 0054,0058,005c | 11,6,11 | DEF | camera ent/tag, controls ent (NOT speed/gravity: pmove reads +0x98/+0x90) | links_wire.c:304-310 | MATCH |
| 188 | 3330 | 7 | DEF | recoil percent fild 0x4222C6 | codol_recoil_state.c:67 | MATCH |
| 189 | 0250 | 16 | DEF | holdBreathTimer cmp 0 0x41893C, client writes 0x1194 at 0x418891 | ES:383 | MATCH |
| 192 | 0060 | -97 | TIME | cmp 0 0x47A793 | none | NOT-PUBLISHED (unknown) |
| 193 | 01ac | 2 | DEF | viewlocked cmp 0 | ES:322 | MATCH |
| 195 | 0218 | 32 | DEF | cmp 0 0x48FCA2 | none | NOT-PUBLISHED (unknown) |
| 196-203 | 056c-0588 | 10 | DEF | hud icon slots (-1 = none 0x41F324) | codol_script_hud_notifications.c:64 | MATCH |
| 206 | 0274 | -16 | DEFs | weaponRestrictKickTime | ES:624 | MATCH |
| 209,210 | 0354,0358 | 6,2 | DEF | fild / cmp 1 0x418C66 | none | NOT-PUBLISHED (C1 server module writes 1/2 at 0x5131C0; meaning unknown) |
| 211,212,213-215 | 048c,0490,0494-049c | 7,11,-92/-91/-90 | | weapon-lock block: 7 flag bits toggled by GSC builtins 0x5198F0/0x519A70/0x519D60/0x519E10, entity 0x7FF (0x47B383 indexes cg_entities), vector (0x47B45C) | codol_weapon_lock.c:52-55, WIDE arm | MATCH |
| 216-219 | 01b4-01c8 | 8 | DEF | none (game-module tests exceed 8 bits -> not ps) | none | MATCH |
| 224,225 | 05c4,05cc | 2,1 | DEF | 0x05cc `mov 1` 0x418525 | none | MATCH |
| 232 | 058c | 2 | DEF | none | none | MATCH |
| 233 | 0094 | 0 | FLT | leanf | ES:361 | MATCH |
| 234 | 0350 | 32/1 | DEF | enum 0..6: switch 0x41A9D6, cmp 5 0x415FA5 | none | NOT-PUBLISHED (only hint-1 ps field; C1 reads it like hint 0) |
| 235,236 | 053c,0540 | 10 | DEF | 0x4568D6 cmp 0 | none | NOT-PUBLISHED (unknown weapon slot) |
| 239 | 059c | 1/2 | DEF | poisoned cmp 0 0x4775A4 | ES:1321 | MATCH |
| 240-243 | 0044-0050 | 11 | DEF | none (bit ops on +0x44/+0x50 are other structs) | none | MATCH |

## 3. Clientstate (77 fields, 0xC38890; consumer CG_ProcessSnapshot 0x46C8DC-0x46CE53)

| off | bits | C1 consumer | server (ES:1003-1055 / codol_clients.c) | verdict |
|---|---|---|---|---|
| 0x004 | 3 | team -> ci+0x4C/0x50 | FREE 0, RED 1, BLUE 2, SPEC 6 (ES:1016-1027) | MATCH |
| 0x008,0x00c | 32 | -> ci+0x54 (8 bytes) | none | NOT-PUBLISHED (no reader beyond copy) |
| 0x010 | 3 | byte -> ci+0x5C | none | NOT-PUBLISHED |
| 0x014 | 11 | CS_MODELS 1315 -> ci+0xE0, dirty | ES:1027 model | MATCH |
| 0x018 / 0x01c | 1 | ci+0xB14 / ci+0xB1C | none | NOT-PUBLISHED |
| 0x020-0x05c | 11x16 | attach models (CS_MODELS) | ES:1038 slots 0-5 (16 via CODOL_OverlayClientAppearance) | MATCH |
| 0x060-0x09c | 6x16 | attach tags (CS_TAGS 5299) | ES:1038 | MATCH |
| 0x0a0 / 0x0a4 | 8 | rank / prestige | ES:1050-1051 | MATCH |
| 0x0a8 | 4 | ci+0xB18 | none | NOT-PUBLISHED |
| 0x0ac-0x0b8 | 10x4 | player cards | codol_script_player_builtins.c:570-576 | MATCH |
| 0x0bc | 32 | ci+0xB38 (vehicle ent) | ES:1028 attachedVehEntNum | MATCH |
| 0x0c0-0x0cc | 32x4 | abilities masks (own client -> cg+0x4D0) | codol_clients.c:353 | MATCH |
| 0x0d0-0x0f0 | float x9 | -> ci+0x78 | codol_clients.c:355 | MATCH |
| 0x0f4-0x128 | float x14 | not consumed in that loop | codol_clients.c:355 | MATCH |
| 0x12c / 0x130 / 0x134 | 11/11/8 | ci+0xAF4 / 0xAF8 / 0xB4C | none | NOT-PUBLISHED |

No bit masks are applied to any clientstate field.

## 4. Entities (MSG_ReadDeltaEntity 0x5A0C00; 22 tables at 0xC39A70)

Reader: removed bit; noDeltaPos bit; lc Bits(7) (= LAST index, >0x42 overflow);
gap ReadDeltaGap(3); field 0 = eType via 0xC35268 {4,-77}; table =
min(eType,0x15); lc>66 -> Com_Error; `noXor = from->eType != to->eType ||
(noDeltaPos && -83 <= bits <= -78)` (0x5A0D84); hint-2 pass over 0..lc-1
(0x5A0DF0); tail copied from `from`.
Server (codol_entities.c:63-92): writes noDeltaPos = same_type, base 0 for
!same_type or bits in [-83,-78], lc = last selected index, hint-2 below lc in the
second pass. MATCH (positions are therefore re-sent from base 0 whenever the
entity is sent; C1 decodes them the same way).

The per-eType tables in codol_entity_fields.inc were re-read from C1 (all 22 x 66
entries) and match byte for byte, including: ET_PLANE (13) is the only table
with changeHint 2 (idx 1-11); ET_HELICOPTER/ET_VEHICLE carry trBase as -88 raw
XOR; ET_MISSILE 0x98 is 10 bits; ET_ACTOR 0x34 is -72; ET_PLAYER 0x5C is -76.

Post-decode masks on entityState (cgame, cent = 0x228 stride, nextState at
cent+0xE4):

| es off | C1 mask / check (VA) | server producer | verdict |
|---|---|---|---|
| 0x04 eType | min(eType,0x15) for the table; dispatch `cmp 0x14` 0x443C70 | CODOL_EntityTypeToWire (codol_events.c:262) | MATCH |
| 0x08 eFlags | tests 0x10, 0x40 (+`cg.time-u[1]>200` 0x46B846), 0x200 (0x484E8B), 0xC00 (turret, 8 sites), 0x20000 (dead, players), 0x80000 (bit 19, 0x443103), 0x100000 (vehicle, 7 sites), 0x100C00, 0x400000 (0x435ADC), 0x4000000/0x8000000/0x20000000 (0x43398A) | player/corpse verbatim (ES:1733,1779); turret 0x200 <- native 0x40 (ES:1631); jammer 0x200000 RMW (codol_radar_state.c:105) | MATCH except the EF_VOTED collision fixed in §2 (ps eFlags feed the player entity) |
| 0x0C / 0x30 trType | BG_EvaluateTrajectory 0x40CA40: trType>12 -> warning, no eval | ES:1518-1541 (0..12) | MATCH |
| 0x58 | actor: byte slot (0x42A695), byte+1 `cmp 3` 0x47E087 (tree); player/general `&0xF` table index (0x4452CD); scriptmover entnum 0x7FF | ES:1827 slot\|tree<<8 (slot<32, tree<5); others per type | MATCH |
| 0x5C,0x68,0x6C (scriptmover anims) | `& 0x7FF` 0x440E32-0x440E44; 0x60 `test 0x800` 0x43FD45 | ES:1180-1192 model/anim entry | MATCH |
| 0x80/0x84/0x88 | `cmp 0x7FF` sentinels; 0x88 -96 (0x7FE world) | ES:1125,1204,1793 | MATCH |
| 0x9C clientNum | index *0xB50 into clientinfo, no bound check | ES:1861 (<64), corpse <18 | MATCH |
| 0xA8 solid | 0xFFFFFF = bmodel else packed mins/maxs bytes (0x4853BA) | ES:1218 brush 0xffffff | MATCH |
| 0xB0 eventSequence | wrap 0x800, catch-up limit 4 (0x447FD0) | ES:1510 epoch&2047 | MATCH |
| 0xD4 weapon | consumed as WORD; `>= bg_numWeapons+1 -> 0` (0x443BF7) | ES:1748 current\|primary<<16 | MATCH |
| 0xD8/0xDC anims | 11-bit, 0x400 toggle handled by bg anim code | ES:1759 passthrough | MATCH |
| 0xE8 link | low 16 bits SIGNED parent (0x44036E), bit 26 = skip-turret-check (0x440388) | ES:1812 link_info 27 bits | MATCH |

## 5. Actors (0xC37158, 24 fields), hudelems (0xC39860, 42), objectives (0xC39818, 6)

All three tables re-read from C1 and identical to codol_actor_fields.inc,
codol_player_arrays.c:9-21 and objective_bits. No masks are applied after
decode except: actor idx = 5 bits (32 slots, CL_GetSnapshot clamps to 0x20),
hudelem count clamp 31, hudelem type 0 stops the gather scan (server rejects
type 0, codol_player_arrays.c:59). MATCH.

## 6. Live-symptom cross-check

* **Client magazine counts wrong while server right** (fixed on 2CF09DD5): the
  wire for section 2 is 1:1; the only client-side interpretation is BG
  0x415F20 matching `elem[0]` to `WeaponDef+0x570` of the held weapon and reading
  `elem[1]` (right hand) / `elem[2]`. Any remaining mismatch is a key mismatch,
  not a codec one (owner: ammo-bindings worker, codol_sv_weapons.c:94-135).
* **Crosshair friend/foe bits (ps+0x344 & 8 / 0x10)**: C1 reads them at
  0x43C509 (friendly) / 0x43C546 (enemy) in CG_GetCrosshairColor, gated first on
  `WeaponDef+0xBC3 != 0` (0x43C4F6) and then on a settle time
  `cg+0xBF050 - cg+0xBF054 >= dvar(0x16D44DC)` (friendly) / `>= 250 ms` (0x43C563,
  enemy); 0x43A52F (CG_DrawCrosshairNames) tests only 0x10. The bits arrive
  (ES:871 mask 0x9d, delta-coded like every DEF field), so "not showing" is
  either the weapon-def gate or the settle timer (cg+0xBF054 is stamped
  client-side on transitions), not the snapshot. Also note PM 0x41DA20:
  `if (ps->weapFlags & 8) { ps+0x34 = 0; skip hand update }` — CoDOL blocks
  firing while the crosshair is on a friendly, so publishing bit 8 changes
  gameplay exactly as C1's own server would.
* **Hold-breath scale/timer (0x24c/0x250, PWF 4)**: C1 reads 0x250 at
  0x41893C/0x418976 and writes 4500 into it at 0x418891; bit 4 at 0x4189AA
  (scale), 0x47DAF0 (timer decrement), 0x45765C (a draw callback skipped while
  holding breath; see HUD note below). Publishing them is codec-correct.
* **weapFlags 87 "every frame to clear GSC 0x80"**: C1 never clears 0x80 itself
  (only tests it); the only clearing path is the snapshot XOR-delta against the
  last *received* value (0x5A0370, base = memcpy of the delta frame 0x5A1A1A).
  The C server's history ring stores the reached value per acked message
  (codol_history.c commit), so delta-only is correct here; the Python server
  needed the every-frame rule because it had no per-message ring.

### 6.1 HUD not drawn on 2CF09DD5 — none of the new bits can do it

C1 draws the whole HUD from CG_Draw2D 0x43B780, gated by: cg+0x35cc cubemap
(never set), dvar "585" cg_draw2D (0x43B7BA), **CG_ShouldDrawHUD 0x453A10**
(`cg+0xbf090 (cg.drawHud) != 0 && (dvar "952" || !(keyCatchers 0x16fc2e0 & 0x10)
|| byte 0x16fc2e4)`), then pm_type (6 = scoreboard only 0x43B7E7, 5 = reduced
0x43B866, >=8 no crosshair 0x43B8C7), killcam 0x475880, dvar "2620" (crosshair).
Hud elems (0x44B2F0) read ps+0xA60/0x1EB8; hud menus (0x43B6F0) are UI menus
whose visibility expressions read `scoped` (0x483980: eFlags&0xC00 or the
held/offhand WeaponDef overlay + ps+0x348 > 0.01), `usingvehicle` (eFlags &
0x100000), `inkillcam`, `scoreboard_visible`, `isintermission` (pm_type 6),
`ui_active`, `hudfade` (0x453A60).

Readers of the newly passed/published values, exhaustively: weapFlags 0x04 ->
ownerdraws 71/289 (hold-breath hint, hidden while set, 0x45765C/0x457848),
hold-breath SFX ducking 0x47DAC0, PM 0x4189AA; 0x08 -> PM 0x41DAAE only;
0x10 -> crosshair colour 0x43A52F/0x43C546; ps+0x24c -> PM lerp
0x4189FE/0x418A23 and BG sway amplitude 0x424BE1/0x424D1D; ps+0x250 -> PM
0x418860..0x4189BE and the hint gate 0x4576DF. Bit 0x80 blanks only the
ammo/weapon ownerdraws (0x4547FB, 0x486778 -> ownerdraws 81/83/103-110/284-287).
No UI expression handler reads 0x344/0x24c/0x250. **Ruled out** as HUD gates.

What does hide the entire HUD, ranked:
1. `cg.drawHud == 0`: reliable command `s hud_drawHud <n>` (CG_ServerCommand
   0x469381 -> 0x468A64, `atoi(value)`; an empty value is 0; the value is
   archived at 0x45AADF so it survives reconnects). The only server producer is
   `bin/home/codol_rawfiles/maps/mp/equipment/_tabun.gsc:243`
   (`self setClientDvar("hud_drawHud", 0)` on gas exposure) restored at :275 by
   clearExposure; the monitor thread ends on "disconnect"/"game_ended" before
   clearExposure runs, so a client gassed at round end keeps drawHud 0 on the
   next connect. Suggested guard (owner: equipment/GSC): send
   `self setClientDvar("hud_drawHud", 1)` from the spawn path (e.g. the
   onPlayerSpawned callback) unconditionally, and in `_tabun.gsc` restore inside
   the `disconnect`/`game_ended` cleanup.
2. KEYCATCH_UI with a fullscreen menu (server-opened menu, g_scriptMainMenu).
3. pm_type 6/5/>=8 at spawn (intermission/scoreboard paths).
4. ps+0x348 raw-XOR base wrong -> `scoped` true -> menus tagged `!scoped` hidden
   for overlay weapons only (partial HUD).
5. Empty hud arrays (only GSC elems missing, menus still drawn).

## 7. Remaining discrepancies / open items

1. ps+0x344 bits 0x200, 0x10000, 0x100000 read by C1 but never produced (no
   native source). 0x100000 = disable-weapon-pickup (GSC builtins 0x5145CD/
   0x5145DC); if a script needs it, add a codol_ps_ext flag and OR it in
   CODOL_OverlayEngineWeaponUseControl (ES:871) — the wire width already covers
   it.
2. ps+0x14 bit 1 (PM_UpdateViewAngles 0x4141B8 for pm_type 1/9) never produced
   (codol_player_links_wire.c:279 writes bits 2/4 only).
3. Unpublished ps fields with real C1 readers: 0x333c (-97), 0x3334 (3),
   0x0060 (-97), 0x0218 (32), 0x0354/0x0358, 0x0350 (32, hint 1), 0x053c/0x0540.
   All are read as plain values (no masks); meanings unresolved (C1's server
   module writes them; see table). Not needed for 1:1 of what we do publish.
4. Clientstate 0x008/0x00c/0x010/0x018/0x01c/0x0a8/0x12c/0x130/0x134 unpublished
   (copied into clientinfo, no downstream reader found in range).
5. Section-2 key semantics (WeaponDef+0x570) — owner: ammo-bindings worker.
6. Entities: server sends noDeltaPos=1 for same-type entities, which forces every
   nonzero position/angle/trDelta field to be re-sent (16+ bits each) whenever
   any field of that entity changes. Correct, but a noDeltaPos=0 path with the
   base from the ring would halve moving-entity cost. Optimisation only.

## 8. How to re-verify

* Tables: `python alpha0022/playerstate_fields.py` style dump of 0xC38CA8 (244 x
  {off,bits,hint}), 0xC38890 (77), 0xC37158 (24), 0xC39860 (42), 0xC39818 (6),
  0xC39A70 dispatch (22 x {ptr,66}) and compare with the .inc files / the tables
  in codol_player_arrays.c. Scratch tooling used today:
  `C:\Users\Michael\AppData\Local\Temp\claude\psaudit\c1dis.py` (capstone,
  `python c1dis.py 0xLO 0xHI`) and `...\scratchpad\re\nf.py`.
* Codecs: disassemble 0x5A0510 (ReadDeltaField), 0x5A0180/0x5A0230 (WIDE),
  0x5A03D0 (angle), 0x5A09D0 (gap) and compare with codol_delta.c.
* Reader structure: 0x5A19C0..0x5A2080 (playerstate + 7 sections), 0x5A0C00
  (entity), 0x5A0A40 (struct), 0x49D800 (snapshot).
* Bit tests: `python ps_xref.py 0x344 0xC 0x10 0xEC --context 2` in alpha0022;
  discard sites whose base register was loaded from `[idx*4+0x150D720]`
  (WeaponDef) or from cg_entities (`^0x189BFEAD`, stride 0x228) — those are the
  offset-name traps that produced the earlier wrong weapFlags notes.
* Live: `CoDOL crosshair wire:` lines (ES:878) show the 0x344 word as it leaves;
  a client that stops moving after a snapshot means a codec desync (silent drop
  at 0x49DCD4) — bisect by lc (fields > 100 need the hint-2 pass).
