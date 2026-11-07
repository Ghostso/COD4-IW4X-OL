# Bot difficulty implementation, exact 1.1.1.13

The four tier names are `recruit`, `regular`, `hardened`, and `veteran`.
`sv_botDifficulty` selects the tier. The Windows launcher exposes it as
`CODOL_BOT_DIFFICULTY` and defaults to Recruit. The local test stack also
defaults to Recruit. The earlier manually exaggerated reaction, fire and FOV
settings are no longer launcher inputs.

## Authoritative data

The native server loads `mp/botdifficultytable.csv` from the mounted exact
1.1.1.13 `code_post_gfx_mp.ff` table. The shipped `mp/botclasstable.csv`
`botDifficulties` row establishes the tier names and eligible classes.
Class IDs 0, 1, 2 and 7 are eligible for Recruit; all nine are eligible for
Regular, Hardened and Veteran. Bot class selection cycles within that set.

| Field used by the current controller | Recruit | Regular | Hardened | Veteran |
| --- | ---: | ---: | ---: | ---: |
| Reaction time, ms | 800 | 400 | 200 | 100 |
| Aim response, min–max ms | 500–700 | 150–250 | 100–200 | 50–150 |
| Nonautomatic fire delay, min–max ms | 900–1300 | 400–600 | 300–500 | 200–400 |
| ADS allowed | No | Yes | Yes | Yes |
| Hip yaw/pitch tracking rate | 1.5 / 1 | 3.5 / 2 | 4.5 / 2.5 | 5.5 / 3 |
| ADS yaw/pitch tracking rate | 1.5 / 1.5 | 4 / 4 | 5 / 5 | 6 / 6 |

The loader validates all four columns and pauses bot commands if this exact
table is unavailable or malformed. Values are copied before zone transitions
can retire the table. A tier can be changed through `sv_botDifficulty`; a map
restart also rebuilds the bot class lineup for that tier.

## Verification and boundary

The Windows native build succeeded and the effective GSC tree resolved against
971 registered builtins. A live 12-bot server loaded the exact table and the
human client reached `CS_ACTIVE` on Killhouse Combat. Sequential restarts of
the same server process verified all four tiers with 12 bots and no script
errors: Recruit cycled classes `0,1,2,7`; Regular, Hardened, and Veteran each
cycled `0..8`. A runtime test first exposed that the enum setter ignored named
values and silently selected Recruit. `Cvar_Set2` now accepts authored enum
names, and RCON readback confirmed all four transitions. Human balance across
the four tiers remains to be judged.

The original table has 48 rows. The controller currently consumes the fields
listed above; it does not yet implement the table's inaccuracy, grenade,
personality, strafing, dive, vehicle and other tactical fields. That is the
remaining boundary for claiming full original bot AI difficulty parity. The
four named profiles and their listed behavior are data-driven and do not use
the temporary manual timing ranges.
