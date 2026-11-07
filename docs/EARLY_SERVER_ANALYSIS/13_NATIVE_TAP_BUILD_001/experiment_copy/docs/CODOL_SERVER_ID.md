# CoDOL server ID publication

The native server validated the low byte of incoming server IDs, but its CoDOL
gamestate did not publish the current ID. A reference client left at zero could
therefore acknowledge gamestate and still have subsequent commands rejected by
`SV_ExecuteClientMessage`'s ID comparison.

C1 configstring-change handling identifies index 3 at 0x487666. It resolves the
string using offset 0x6d0d13c and string base 0x6d1370c, parses it as an integer
at 0x487684, and writes the full ID to global 0x6d0d12c at 0x487689 and active
client state +0x33d0 at 0x487691. The adjacent unchanged-string path also tests
index 3 at 0x487561. Client netchan encoding consumes the low byte of global
0x6d0d12c at 0x49c593. This is a dedicated configstring, not the protocol dvar.

`CODOL_SetServerId` writes the native signed 32-bit ID to CoDOL CS 3, including
zero and signed boundaries. `SV_WriteGameState` refreshes that slot from the
server-owned `sv_serverid` before serialization. `SV_SetServerId` calls
`CODOL_PublishServerId` after changing the ID; primed/active recipients with a
sent gamestate receive `d 3 <id>`. Repeating the same ID produces no duplicate
reliable command. The initial map's later configstring reset cannot lose the ID
from its eventual gamestate because serialization refreshes it again.

The existing native tests now cover signed boundary values, inclusion in the
serialized gamestate comparison, publication recipient gating and deduplication.
The full Linux `all test-codol` suite passed (`/tmp/sh1x-server-id-linux.log`).

The encrypted transport probe now decodes the whole configstring block and
gamestate trailer, reads CS 3, and optionally sends a reliable userinfo command
using that ID, the gamestate acknowledgement and server-command key. It requires
the native server to acknowledge client command 1. This tests command acceptance,
not movement, pure-file validation or a playable C1 match.

The forced Win32 build passed (`/tmp/sh1x-server-id-win32.log`). The encrypted
probe on localhost 17744 received a 2992-byte gamestate with 743 configstrings,
CS 3 = 1793, map `mp_bog_sh`, zone `mp`, and client slot 0. It used that ID to
send reliable client command 1; the native log records the userinfo command and
the peer verified its acknowledgement. The gamestate used three fragments.
One retained IW4OL `0xfffffff0` reliable packet also appeared in this capture;
its source remains to be traced. Do not infer that all legacy messages are gone
from the earlier stats probe that happened not to observe one.

Probe home: `C:/Users/Michael/AppData/Local/Temp/sh1x-server-id-20260908-060817`.
Process 54524 was stopped after executable/home verification; C1 and Python were
untouched and responsive. Pure-file validation, movement entry, live snapshot
acceptance and the full vendor script closure remain unverified.
