# Native getMapCustom

IW4's registration at 0x79ae64 binds `getmapcustom` to 0x5f69b0. The builtin
requires at least one argument, passes its key to 0x42f200 and adds the returned
string. The lookup searches the current map's arena metadata using
case-insensitive map/key comparisons and returns the empty string when absent.
Its metadata is assembled by 0x4a95b0. This differs from alpha0022's Python
`mapcustom_<key>` dvar approximation and undefined missing-value result.

The native implementation now reads the mounted CoDOL `mp/basemaps.arena`
rawfile and selects the `mapname` dvar's record. The bounded parser supports
brace-delimited key/value records, quoted values, comments, and keys before
the map name. Missing map/key/asset returns an empty string. Invalid present
data raises a script error; it does not fall back to dvars. Parsing validates
the complete file before publishing output. Files above 16 MiB and tokens
above 1023 bytes are rejected. The implementation does not emulate IW4's
fixed arena/key/value truncation limits or arbitrary arena-extension files.

Tests passed 32-bit ASan/UBSan for ordering, case, quoting/comments, empty and
missing fields, malformed records and insufficient output capacity. Windows
build passed (`/tmp/sh1x-map-custom-win32.log`). An isolated native Bog startup
on UDP 17779 printed `SH1X_MAP_CUSTOM_VM_PASS`, reading `urban` environment,
`socom_141_desert` allies, its exact map name, and empty for a missing key from
the actual mounted asset. The fixture is `tests/fixtures/codol_map_custom_vm`.

The full-reference compile on UDP 17780 passed the previous `getMapCustom`
failure and stopped at `PrecacheFxTeamThermal(effect, "J_Spine4")` in
`maps/mp/gametypes/_teams.gsc:32`. Both diagnostic servers were stopped. C1
and the Python lobby remained responsive; real match entry is not yet proven.
