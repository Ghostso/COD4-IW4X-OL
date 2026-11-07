# Mortar runaway trajectory — source correction

The snapshot failure is a consequence of wrong missile integration, not evidence
of memory exhaustion. Parent's hash-verified passive capture
`obj/crash-bots-runaway-capture.jsonl` at server times347750/348250 found four
live type4 missiles, handler9, weapon77, gravity trajectory5, vertical launch
velocity1197, and nextthink exactly trTime+30000. The independent definition
capture `obj/crash-bots-runaway-weapon.jsonl` identifies weapon77 as `mortar_mp`.
Origins continued upward through38594 and39192. The earlier rotated log's
entity997 position first exceeds the codec range at z bits470033a8, then advances
about59.85 units each50ms. This is finite, constant-speed ascent.

`MissileTrajectory` in retained `_g_missile.asm` only bypassed its guided
integrator for launch delay, linear trajectory2, or a handler other than9.
`CODOL_SpawnMortarBomb` correctly sets gravity5 and explosion handler9, so after
launch delay the bomb entered `MissileTrajectory_180`: trBase += frame*trDelta.
That branch never applies gravity and destroys the ballistic origin. Explosion
at its authored30-second lifetime can subsequently produce a general/event
entity at the same unreachable coordinates. Parent found an explicit server
quit in the previous run, not a server exception; do not label it a proven crash.

C1 evidence: DropBomb531742 initializes gravity5;5317a8..5317e9 writes the
explicit launch velocity; guidance4 keeps gravity and sets angular spin at
5319c7. Shipped mortar type4/guidance4 has lifetime30 seconds, acceleration0,
curvature0, destabilization0. See the existing mortar activation audit and its
saved disassembly. The direct C1 authoritative trajectory dispatcher has not
been located. Primary reference OpenBLOPS `Game/Server/game/g_missile.cpp`,
`MissileTrajectory` around3650, explicitly sends bomb weapons and ballistic
guidance to BG_EvaluateTrajectory instead of the guided integrator.

The native correction adds `CODOL_BombUsesBallisticTrajectory` and a dispatch
branch before remote/guided processing. It recognizes only this module's
generation-checked, constructor-owned active mortar with gravity trajectory.
The existing evaluator now uses the unchanged launch trBase/trTime/velocity;
collision, impact, angular motion, lifetime and explosion ownership remain in
their existing paths. The assembly reloads level.time after the C call and
preserves the condition flags across MOV before its conditional jump. No
position clamp, packet masking, lifetime reduction or client alteration.

Source written and reviewed locally; parent owns build/deployment and live
verification. No automated tests, builds or process changes by this worker.
Already corrupted live mortar trajectories are not repaired by this source edit.
