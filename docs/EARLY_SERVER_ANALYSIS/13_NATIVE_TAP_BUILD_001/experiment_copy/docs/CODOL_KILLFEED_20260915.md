# Missing killfeed: obituary producer and snapshot payload

Status: native source written; shared integration proposed for parent review.
No builds, automated tests, restarts or client changes by worker.

## Proven blockers

Retained GScr_Obituary creates EV_OBITUARY66 with victim+74, attacker+78 and an
IW3 packed parameter (weapon or80h|MOD). codol_event_map.inc maps66 to C1event107,
but CODOL_EventParameterToWire has no obituary branch. Generic temp entity seed
in codol_sv_gameframe.c rejects the unhandled parameter and omits the event.
Additionally, that generic seed supplies neither obituary victim nor attacker.
Merely adding a pass-through parameter branch would leave the payload wrong.

C1 producer54E560 and consumer4445F0 were disassembled directly, using alpha0022
docs/damage_death.md as a lead. C1 event107 uses eType128, victim+80, attacker+84,
and a16-bit deathCode split lowbyte+AC/highbyte+E0 (54E71D..54E72F). Ordinary
deathCode is C1 weapon index below700; special codes are700+MOD. C1specialMODs
are melee8, headshot9, crush11, falling12, suicide13, impact16. Melee with source
WeaponDef+340==3 (shield) keeps the weapon icon; impact with source+344==9
(throwingknife) keeps it. These exceptions were verified54E6F8 and54E78F.
CG_Obituary444622/628 reads victim/attacker;44464F compares code with700. The
obfuscated caller's joining of the split bytes was not independently recovered,
but the native producer and consumer prove their endpoints.

## Native replacement and shared integration

New codol_obituary.c/h parses the exact17 C1 MOD names independently of the
different retained enum. It captures native weapon in s.weapon, C1MOD in
s.eventParm, icon selector0/1 in s.index, and victim/attacker in their existing
entity-state fields. These fields already participate in native archive coding;
weapon fits its7-bit native field, selector its10-bit index field, MOD the
parameter field. There is no ambiguous80h encoding or live victim lookup during
snapshot replay. The helper resolves captured weapon identity to wire only when
needed. Shield/knife exceptions use verified original metadata getters.

obj/killfeed-audit/integration.patch proposes registration replacement under
CODOL_SERVER, a typed snapshot seed before the generic temp path, and an atomic
four-field overlay. The retained registration remains for other builds. Parent
owns these shared sources and must integrate/review before claiming support.

C1 consumer bounds victim to0..18, so the producer rejects a nonplayer/out-of-pool
victim before generating an event that the client cannot display. Undefined or
nonentity attacker uses2046, preserving original obituary behavior. Events remain
broadcast via the existing flag8 and normal temporary-event lifecycle.

MOD_TELEFRAG is absent from the measured C1 MOD table; no mapping was invented.
Search of live scripts/codol and alpha0022 GSC found only a _missions.gsc category
list reference, not an obituary producer passing it explicitly. The general
_damage obituary passes its received MOD, so a future retained telefrag producer
would still need a deliberate policy; ordinary kills do not require it.

Client info-valid/HUD rendering prerequisites remain independent. Source review
fixes the definite event omission and wrong payload; visible live killfeed is not
yet verified.
