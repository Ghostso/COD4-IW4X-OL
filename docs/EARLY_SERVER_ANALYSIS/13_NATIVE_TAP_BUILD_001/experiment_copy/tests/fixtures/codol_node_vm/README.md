Isolated native VM fixture for shipped `mp_bog_sh`. Requires `developer 1`.
See `docs/CODOL_PATH_NODES.md` for launch settings and expected markers.
Empty callbacks isolate loader/node behavior; this is not a playable gametype.
It also invokes native `PhysicsLaunchClient` with two vectors and with no
arguments, checks the retained origin, and deletes the temporary script models.
