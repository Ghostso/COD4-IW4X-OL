# Tabun parent integration — 2026-09-15

Reviewed staged area lifetime, owner lifetime, overlapping exposure cadence,
native damage arguments, water query, poison publication and HUD cleanup.
Installed the C1 asset adaptation in scripts/codol/maps/mp/equipment/_tabun.gsc.

Parent caught an unresolved T5 script dependency: mayApplyScreenEffect was absent
from both the installed script include tree and supplied BO1 dump. Recovered the
original maps/mp/_utility.gsc from plutoniummod/t5-scripts commit
70689b8288e60079d48926657e670c41aab4abdf (MP/Common), saved under
obj/reference/t5-equipment. Its method rejects a defined viewlockedentity.
OpenBLOPS Game/Server/game/g_client_fields.cpp implements that field from native
player state, returning undefined for WORLD/NONE. Added a CoDOL native method
that reads the existing viewlocked_entNum producer also published to C1 ps+1b0,
using native entity sentinels rather than T5 offsets or script-only remote flags.

Build obj/codol-tabun.exe completed with no compiler warnings. SHA256:
1436CB7AC4BD9B84382BA351615BFF736FAC9C9D5C4FFD917E69C10D56974968.
Copied both native executable names and launched with four bots requested.
No C1 or Python process was stopped. No automated tests run.

Native PID62152 reached gameplay with four training bots. Startup log contains
Tabun shellshock volume-cvar compatibility warnings; no script compile/runtime
error found in this startup scan. Those warnings are not evidence that all T5
audio mixing fields are supported by the native server.

Live gas damage, FX coverage, immunity, water duds, recovery, and HUD interaction
remain unverified. Original T5 dog gas reactions and battle chatter adjuncts are
not yet implemented. This does not constitute complete equipment parity.
