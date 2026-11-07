# Missing class-perk enable default

The active native process101540 at relocated base0x110000 has464 registered
cvars. A read-only walk of cvar_indexes (76-byte native cvar_t records) finds
scr_game_hardpoints after the previous fix, but no scr_game_perks. An initial
pointer-array interpretation failed and was discarded; source cvar.c declares
an inline array, and cvar.h establishes the record layout.

validatePerk reads getDvarInt("scr_game_perks")==0 and replaces every selected
nonequipment perk with specialty_null. The live log contains these null
lookups. The primary IW4 default_mp_gamesettings.cfg line55 specifies1; its
absence in the native bootstrap was never an explicit user/mode disable.

The staged perk init sets1 only if getDvar returns an empty string. Explicit0
is preserved. This unlocks the existing selected-perk grant/aggregation path;
it does not establish that every individual modifier has a gameplay consumer.

Source reviewed; deployment tracked in implementation ledger. No tests.
