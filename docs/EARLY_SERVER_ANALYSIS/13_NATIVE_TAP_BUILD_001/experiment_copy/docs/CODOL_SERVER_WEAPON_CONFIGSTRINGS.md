# Native weapon configstring initialization

Map startup now initializes the 700-slot CoDOL weapon window after installing
inherited constants. MP names come from column zero of the mounted
`mp/coWeaponAttachmentTable.csv`, in row order, with duplicate names removed.
The initializer includes implicit `none` and `defaultweapon_mp`, and follows
each newly registered weapon's +0xb78 then +0xb88 dependencies recursively.
Already registered partners reuse their original slots, including cycles.
Coop/ZM skip the MP pre-pass and begin with the two implicit definitions.

Every unused weapon slot receives an explicit empty override. This matters:
the first native probe inherited `gl_famas_mp` at slot 77 after a registration
gap. Alpha0022 `weapon_configstrings.py` documents the same stale-constant
problem and C1's fatal `181 <name> <got> <want>` validation. The client validates
slots 1..699 (CG_Init at 0x450ae2); wire weapon IDs being ten bits does not make
the configstring window 1024 entries. Slots outside this window are preserved.

The native initializer stages both names and ammo-key registry before replacing
published state. Failed initialization leaves configstrings unchanged and makes
the registry unavailable. Before gamestate writing, the server refreshes the
registry from effective override/inherited names, rejecting gaps, unresolved
stock assets and conflicts with implicit definitions. Empty overrides suppress
inherited values. Map reset frees registry ownership.

`codol_checkweaponregistry` runs that same refresh and reports readiness or its
failure reason. The isolated native Bog probe now prints:

    CoDOL weapon registry ready: 54 definitions from published/inherited names

The probe home is `%TEMP%/sh1x-server-weapons-final-20260908-034230`. Its native
VM log also contains all four path-node, vehicle-node, PhysicsLaunchClient and
HUD font-scale PASS markers. PID 66036 exited through normal quit. The earlier
diagnostic probe identified the slot-77 gap; it was not treated as a successful
initialization. No existing C1 client or Python lobby was modified.

Unit tests cover precedence, gaps, empty overrides, partner ordering/cycles,
unrelated configstring preservation and atomic failures. The dedicated test
passes ASan/UBSan with halt-on-error. Live gameplay still needs to associate its
native weapons with the registry and feed ammo bindings into frame construction.
Dynamic custom-definition construction, complete scripts and client match entry
remain incomplete.

Final validation: Windows build `/tmp/sh1x-server-weapons-final-win32.log`
passes, followed by a forced Linux build and full suite in
`/tmp/sh1x-server-weapons-final-linux.log`. The sequence exited zero. Shared
static libraries were last built for Linux.
