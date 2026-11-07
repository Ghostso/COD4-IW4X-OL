# Authored aerial paths

Source audit, not a live flight verification.

The retained Killhouse asset dump `obj/killhouse-mapents-shadow.bin` contains
the NUL-delimited worldspawn entity text at byte 4920029 through 5147037
(227009 bytes, 1967 entity records). The file is not a standalone MapEnts
stream; parsing its first bytes as a MapEnts header is invalid.

All helicopter route target links in that entity text resolve uniquely:

- Three `heli_start` entries traverse authored nodes and terminate at `auto467`.
- One `heli_loop_start` enters the seven-node cycle
  `auto476 -> auto477 -> auto478 -> auto479 -> auto480 -> auto481 -> auto493 -> auto476`.
- One `heli_crash_start` follows `auto482 -> auto42 -> auto44` and terminates.
- Five `heli_leave` records provide exit destinations; two share an origin.

Intermediate nodes include `script_airspeed` and `script_accel`. The existing
`scripts/codol/maps/mp/killstreaks/_helicopter.gsc` follows `target` links in
`heli_fly_simple_path` and `heli_fly_loop_path`, applies these speed fields,
sets vehicle goals, and waits for `near_goal` / `goal` notifications.
`src/codol/collision/codol_collision_native.c` copies the loaded MapEnts entity
text unchanged into the native map representation.

Therefore, missing authored routes do not explain a stationary helicopter on
Killhouse. Remaining investigation must follow script execution, native vehicle
goal movement and notifications, and snapshot publication. This audit does not
establish that every aerial killstreak uses helicopter routes or that every map
has the same route names. Preserve each killstreak's authored routing behavior.
