# Native C1 mover trajectories

Built and deployed `obj/codol-c1-mover.exe`:
`DEAD476A7220B0E89C909AD5C073330A329B87742DAFA3B1A7E9E5891756EF07`.
Build exit 0; no automated tests or visual Betty verification.

Betty's moveTo/rotateVelocity producers previously wrote retained acceleration
6 and deceleration 7, which snapshot publication rejected. The native CoDOL
enum, mover producers, transition checks and BG evaluators now use C1
acceleration 7, deceleration 8 and physics 9 directly. PhysicsLaunch and
G_MoverTeam's physics exclusion changed together. The gravity-ragdoll mover
check now uses C1 11. Non-CoDOL builds retain their original values.

Snapshot publication accepts these native curve IDs and validates positive
duration; it does not translate the old enum. Position and angular tracks
share this writer. Evidence: C1 table 0x40cca8, acceleration 0x40cb86 and
deceleration 0x40cbfe, matching retained evaluator equations. C1's additional
gravity mode 6 has no producer in this slice and remains unsupported rather
than being aliased to a different equation.

Also deployed the reviewed Betty team/owner marker and moving HUD Y/Z fix.
Actual triggered motion and marker appearance require gameplay observation.
