# Native path-node records and map spawning

`src/codol_script_path_nodes.c` retains every `node_*` record from the native
map entity parser in an owned store. It uses the retained VM's class 2
(`pathnode`), separate from networked `g_entities`. Class fields expose the
source targetname, target, script_linkname, script_noteworthy, classname,
origin, angles and spawnflags. Missing keys return undefined; malformed typed
fields raise errors. Native field writes remain explicitly unsupported; dynamic
GSC fields work through the existing VM.

`getnode`, `getnodearray`, and `getallnodes` query this store. Node identity and
ordering follow the map record order. Singular ambiguous matches raise an error;
missing singular matches return undefined. These are record queries, not path
finding: graph links, path visibility, node-type semantics and AI navigation
remain incomplete. The Python reference's `builtin_surface.py` path-node section
documents stripped graph arrays and returns empty arrays/refusals; the native
implementation uses the actual entity-lump records rather than copying that
limitation into the record queries.

Script initialization loads the store and restores the entity parser position.
The source-edited spawn pass recognizes stored path-node classes before calling
`G_Spawn`. Previously these unrecognized classes fell through to ordinary entity
allocation, exhausting slots through 1021. Shutdown frees the store. Initialization
failure prevents the spawn pass from silently discarding uncaptured nodes.

The focused C fixture checks owned records after parser reuse, class identity,
fields, case-sensitive value matching, duplicates, arrays, misses, filtering and
reset. The 32-bit AddressSanitizer/UndefinedBehaviorSanitizer run passes.
Full Linux `make -B -j6 all test-codol` passes as well
(`/tmp/sh1x-pathnodes-linux.log`).

Windows builds pass (`/tmp/sh1x-pathnodes-win32.log` and the incremental log).
The isolated shipped `mp_bog_sh` probe completes game initialization, with both
`SH1X_PATH_NODE_VM_PASS` and `SH1X_VEHICLE_NODE_VM_PASS` in
`%TEMP%/sh1x-pathnodes-native-probe/main/games_mp.log`. These assertions execute
in the native VM and verify fields, repeated-query identity, missing lookups,
array lookup and dynamic fields. Probe PID 12800 exited through `quit` with no
startup error. Existing client and lobby processes were untouched.

Reproduction scripts are in `tests/fixtures/codol_node_vm`. Set `codol_scriptPath`
to its absolute path, `codol_scriptOverlay` to an empty string, `developer 1`,
`g_gametype dm`, and load shipped `mp_bog_sh`, using the CoDOL installation as
`fs_basepath`, an isolated `fs_homepath` and loopback port 17739. Then quit and
check the two markers in `main/games_mp.log`. The fixture has empty gameplay
callbacks solely to isolate native startup and VM integration; it is not a
gametype implementation or evidence of full reference script/client match entry.
