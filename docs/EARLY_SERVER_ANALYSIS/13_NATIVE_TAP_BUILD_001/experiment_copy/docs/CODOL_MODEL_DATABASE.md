# Dedicated native model lookup

`DB_FindXAssetHeader(ASSET_TYPE_XMODEL, ...)` now calls the existing native
physics-model provider before falling through to the retained database.
This view has resolved skeleton strings, bounds, collision surfaces, active
LOD meshes, dedicated material handles, physics presets and primitive maps.
The archive generation owns those dependencies and retains their lifetime.
It is a dedicated-server asset, not a graphical renderer resource.

A ready conversion returns the cached model pointer. An invalid/unresolved
conversion raises an explicit error; an absent name retains the existing
database/default lookup behavior. `DB_IsXAssetDefault` recognizes ready
converted models, keeping the actual configured default model name classified
as default. This matters because `XModelBad` uses that query: the old database
hash table alone would classify all converted models as bad.

The Windows build passes. A shipped Bog probe now passes the former
`me_electricbox4` failure and reaches a request for `?0`, which falls through
and fails while loading fallback `void`. The reference map-spawn data uses
`?0` on trigger entities (for example `trigger_use_touch`); the native source
already decodes separate trigger models/hulls/slabs, but entity spawning and
collision handling for that reference syntax still need integration. It must
not be replaced with a dummy XModel or assumed to be the same as `*0`.

Probe log: `%TEMP%/sh1x-modeldb-vm-probe/main/qconsole.log`, PID 61764, clean
game shutdown and exit. The existing client/lobby were untouched. No planned
vehicle-node VM assertion success marker or playable match has been observed.

Existing registry fixtures cover cached physics model identity, dependency
resolution, provider mismatch, absent names, malformed physics rejection and
generation retention. The live probe tests the newly connected DB lookup;
it does not prove every model or DObj gameplay use is supported.
Full Linux `make -B -j6 all test-codol` passes
(`/tmp/sh1x-modeldb-linux-regression.log`).
