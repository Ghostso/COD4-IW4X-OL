# C1 menu-response identity trace

Primary offline evidence from C1.exe1.1.1.13:
- Aligned entry487440 updates configstrings. At487666 it tests updated index3;
  48766c reads stringOffsets[3] (6d0d13c),487677 selects stringData,
  487684 converts decimal to integer,487689 writes6d0d12c and487691 stores
  the same ID in decoded client connection+33d0.
- Aligned menu emitter5fde90: loop5fdf10 reads32names from6d1137c,
  i.e. stringOffsets[4243];5fdf45 loads6d0d12c,5fdf53 passes it as first
  integer to format c6d1ec, cmd mr %i %i %s.
- Independent aligned entry6a5390 repeats bank search6a53e0 and reads
  the same ID6a5412, passing it to wait; cmd mr format6a541a.

This contradicts alpha0022/menu_spawn.py's INFERRED local-client/splitscreen
interpretation of mr argument1. A captured zero does not establish its type.
Do not accept0 as a local-client bypass of native server-ID validation.
The existing Cmd_MenuResponse_f check against sv_serverid is appropriate:
SV_GenerateServerId updates that cvar and publishes the same value as CS3.
Cvar_FindVar uses case-insensitive name comparison, so sv_serverId spelling
is not a mismatch. Gamestate refresh also stores sv_serverid in the CoDOL bank.

Rejected guessed helper entries49c56d/494adf; those mid-instruction listings
were not used to support behavior. Initial gamestate initialization of this
global was not established by this trace, only configstring update and emitters.
No tests/builds/runtime. Code comment added to prevent adopting Python inference.
