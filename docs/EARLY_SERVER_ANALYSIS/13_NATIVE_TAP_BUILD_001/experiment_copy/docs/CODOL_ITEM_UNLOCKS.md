# isItemUnlocked integration evidence

## Native player binding (2026-09-08)

`isItemUnlocked` is now a native player method backed by the composed profile
reader. It checks player/argument validity, requires an attached secure profile,
loads the mounted schema and tables (with reference unlock CSV fallback), and
returns only a known result. Missing profile/data raises a script error; no
Python gameplay call or constant fallback is used.

`codol_bindprofile <connected client 0..31> <directory> <nonzero decimal uid>`
lets the server operator explicitly associate validated storage with a live
slot. The UID is chosen by the operator, not copied from client userinfo.
Storage zlib/CRC and schema headers are checked before an atomic owned copy is
attached. Failure preserves the old binding. Copies are isolated by slot and
cleared on new connection, disconnect, bot slot initialization, and map/server
clear. Automatic authenticated lobby-account attachment is not implemented;
an operator must rebind after map clear. This is an admin integration path,
not a claim that the lobby's shared key authenticates a claimed account.

Owned-profile tests passed 32-bit ASan/UBSan for copying, isolation, invalid
replacement, maximum UID, invalid slot/zero UID, replacement, and resets.
Windows build passed (`/tmp/sh1x-profile-bound-win32.log`). An isolated native
Bog server on UDP 17777 accepted an encrypted synthetic peer, completed public
stats/pure setup, and received an authenticated test-RCON operator binding to
synthetic secure UID 1. The native player GSC callback printed
`SH1X_UNLOCK_VM_PASS`: arctic/urban true, desert false, earned title true with
rank index 4 and challenge progress 100. Full and delta gameplay snapshots
also decoded. The fixture is `tests/fixtures/codol_unlock_vm`; the transport
probe supports `--bind-secure-profile` with its existing test-RCON option.
The isolated peer/server were stopped; no actual account profile was read.
The subsequent full-reference compile on UDP 17778 passed the former
`isItemUnlocked` failure and stopped at the unknown `getMapCustom` call in
`setGhillieModels( getMapCustom("environment") )`. That diagnostic server was
stopped after the fatal compile result. C1 and the Python lobby remained
responsive; vendor-script startup and real C1 match entry are still incomplete.

## Unknown title/icon overrides (2026-09-08)

Further schema inspection found selected `cardTitle`/`cardIcon` shorts in the
public profile but no established persisted ownership override equivalent in
either profile. The reference's decoded unlock-flag table has no exact entries
for `cardtitle_ghilliemist` or `cardicon_ghillie`. Selected cosmetics and UI
notification flags therefore are not used as ownership evidence.

The rule evaluator now retains an unavailable title/icon override as unknown
and evaluates the ordinary requirements. Because IW4's decision is override OR
requirements, satisfied requirements prove true even when the override is
unknown. If requirements fail, the unknown override prevents a known false
result; output remains unchanged. This replaces the earlier unconditional
failure on every unavailable title/icon override without inventing its value.

Focused 32-bit ASan/UBSan tests passed known true/false/unknown override cases.
An isolated native Bog run on UDP 17776 passed 14 composed queries using the
actual tables and synthetic stored profiles. Ghillie title/icon access was true
with completed requirements and unknown with unmet requirements; the preceding
ghillie feature tests also passed. Windows build passed in
`/tmp/sh1x-unlock-unknown-win32.log`. The probe was stopped afterward. Persisted
override ownership and live account attachment remain unresolved.

## Composed native unlock queries (2026-09-08)

`CODOL_ProfileItemUnlocked` now joins the rule evaluator with native profile
rank and challenge adapters. It accepts explicit profile/schema/table inputs,
validates the profile header before lookup, matches item names without ASCII
case sensitivity, rejects duplicate matching rows, and returns true for an
absent item row as IW4 does. Rank conditions use converted total XP and rank
lookup. Challenge conditions use CoDOL numeric progress translated to IW4's
stage convention. Required unavailable data leaves output unchanged. Title/icon
override groups deliberately remain unavailable; they are not treated as false.

The read-only `codol_checkunlock <directory containing mpdata_s> <item>` command
combines validated storage, mounted secure/rank/challenge assets and the unlock
table (mounted first, configured reference CSV if absent). It neither selects
a live user's profile nor exposes a GSC player binding.

An isolated native Bog run on UDP 17775 passed 11 composed queries using
synthetic CRC-valid secure profiles: below/at all three ghillie thresholds,
rank gating despite completed challenges, uppercase item lookup, forest at
rank zero, absent-item behavior, and rejection of an unmapped title override.
The parser/header/lookup failure cases also passed focused 32-bit ASan/UBSan.
Windows build passed in `/tmp/sh1x-unlock-composed-win32.log`. The probe was
stopped afterward; C1 and the Python lobby remained responsive.

`CODOL_RankForExperience` now maps nonnegative total XP through the numeric
rank keys, rather than treating CSV row positions as rank IDs. It validates
unique rows 0..maxrank with contiguous minimum/next-total ranges and saturates
above-max XP to maxrank. Invalid/duplicate/missing rows preserve output. This
implements the interval selection needed by the unlock-rule rank callback;
it does not reproduce undefined behavior on malformed IW4 table layouts.

`codol_checkexperience <directory containing mpdata_s>` is a read-only operator
diagnostic combining stored-profile zlib/CRC validation, mounted secure-schema
selection, total-XP conversion and mounted rank lookup. It explicitly reads
the shared file in the supplied directory; it neither chooses a live account
nor attaches it to a client.

An isolated Bog run on UDP 17774 verified 76 synthetic stored profiles against
the actual mounted tables: all 70 rank minima, 1999/2000 XP at rank zero,
version-matched and stale-version overflow from rank one, equality at its span,
and the upper bound at maximum rank. Expected totals used independently decoded
reference data; profile offsets were 4400 (experience), 5100 (rank), and 5104
(rankVersion), including the CRC prefix. All 76 results matched. The focused
rank/conversion test also passed 32-bit ASan/UBSan, and the Windows build passed
(`/tmp/sh1x-experience-mounted-win32.log`). The probe was stopped afterward;
C1 and the Python lobby remained responsive. Live profile attachment and
title/icon override mapping remain incomplete.

## Native total-experience conversion (2026-09-08)

`CODOL_ProfileExperience` reads `rank`, `experience` and `rankVersion` as mapped
integers from an explicitly supplied decoded secure profile. It resolves the
zero-based stored rank (zero stored rank floors to zero), obtains minimum XP
from rank-table column 2 and next total XP from column 7, and reads the table
version from column 3 of `maxrank`.

This follows C1 0x58eeb0, with an important correction to the earlier simple
base-plus-XP description: at 0x58efa7 it compares stored `rankVersion` with
helper 0x49f6d0's table version. Equal versions return minimum plus within-rank
XP directly. Different versions clamp to next-total-minus-one only when
within-rank XP is **strictly greater** than next-total-minus-minimum; equality
still returns the next threshold. Schema names/types were checked against
the reference's decoded secure definition. The native adapter rejects missing
or duplicate rank rows, malformed thresholds, negative fields and overflow
rather than manufacturing a valid rank. Outputs remain unchanged on failure.

The focused test uses real native schema selection and mapped scalar reads;
32-bit ASan/UBSan passed version agreement/disagreement, exact span boundary,
zero-rank behavior, missing rows and overflow cases. Windows build passed in
`/tmp/sh1x-experience-win32.log`. The API returns stored zero-based rank and total
XP; it does not yet apply IW4's XP-to-rank lookup or attach a live account.

`codol_checkchallenge <profile directory> <decimal uid> <challenge>` is now a
read-only operator diagnostic. It reads the explicitly selected stored secure
profile with the bounded zlib/CRC loader, loads the mounted secure schema and
CoDOL challenge table, and reports the derived IW4 stage. The UID comes from
the console argument, not connect userinfo; this command does not authenticate
or attach a player profile. Full unsigned-64-bit UID parsing rejects overflow.

The mounted-schema integration run on UDP 17773 used eight synthetic zlib
profiles with valid CRCs, secure v11/0x096b8f57 headers, and challenge 60 progress
at record offset 608 (profile offset 612, independently obtained from the
reference's decoded schema). Values 0, 49.5, 50, 99.5, 100, 199.5, 200, 10000
produced IW4 stages 1, 1, 2, 2, 3, 3, 4, 4. A ninth file with a bad CRC was
rejected by storage before schema conversion. The queries ran from an exec
config because the initial long startup command line was truncated after five
queries. Windows build passed in `/tmp/sh1x-challenge-mounted-win32.log`.
The isolated probe was stopped; C1 and the Python lobby remained responsive.
No live account profile was read or changed.

## CoDOL challenge progress bridge (2026-09-08)

The decoded secure definition's `challenges` property is an indexed array of
1000 floats, starting at logical leaf 105. It is not a named array of integer
IW4 challenge stages. C1 0x590ca0 formats a numeric index and reads
`challenges[index]` from secure storage through 0x590670. That reader's type-8
jump-table entry is 0x59070a, which obtains the float and converts it to integer.
C1 0x48bf60 loads `mp/allChallengesTable.csv`, finds the numeric challenge ID
in column 4 and collects thresholds from columns 6, 8, ... 22 until zero.

An isolated native Bog probe on UDP 17772 queried the mounted table through
GSC: `ch_ghillie` has ID 60 and thresholds 50, 100, 200. No reference CSV root
containing that table was configured; these values came from mounted CoDOL
assets. The executable's table names and numeric column distinguish this from
the exported IW4 CSV, whose corresponding ghillie ID cell is empty.

`CODOL_ProfileChallengeState` now accepts an explicit decoded secure profile,
its schema and a CoDOL challenge table. It finds the unique named row, validates
the 0..999 ID, resolves `challenges[ID]` through the native mapped field reader,
and derives the IW4 next tier as one plus the number of completed thresholds.
This stage convention follows IW4 `_missions.gsc`'s `finalTier = tierId + 1`
and is distinct from C1's presentation helper at 0x48d6c0. It preserves output
on missing/malformed data, wrong field type, non-finite/negative progress,
non-increasing thresholds and mismatched schema headers. It does not validate
CRC, choose an account, attach a live profile, or grant an unlock by itself.

The focused 32-bit ASan/UBSan test uses real schema selection, path resolution
and mapped float reads with synthetic profile bytes. Ghillie thresholds are
tested immediately below and at 50/100/200, plus malformed inputs. Windows
build passed (`/tmp/sh1x-challenge-win32.log`). The native
probe was stopped; C1 and the Python lobby remained responsive. Rank conversion,
title/icon equivalents and trusted live profile attachment remain incomplete.

The native script asset boundary now loads missing reference CSV tables;
see [reference table loading](CODOL_REFERENCE_TABLES.md). The actual unlock
table was queried successfully through the native VM, independently of the
still-incomplete player-profile adapter.

## Native rule evaluator (2026-09-08)

`codol_unlock_rules.c` now implements the found-row decision logic from IW4
0x40d630 and its challenge helper 0x60d640. It applies title/icon overrides,
rank gating, and all semicolon/ASCII-whitespace-separated challenge requirements.
Tokens are bounded to 63 characters like the executable's 64-byte buffer; only
a final underscore plus one digit on a name longer than two characters changes
the required stage. The challenge state's comparison is strictly greater than
that stage. Rank text follows decimal-prefix conversion, with out-of-range
values rejected instead of relying on overflowing `atoi`.

The reference `vendor/iw4/mp/unlocktable.csv` contains actual ghillie rows:
forest has rank 0 and no challenge; arctic has rank 4 and `ch_ghillie`; urban
uses `ch_ghillie_2`; desert uses `ch_ghillie_3`. The focused native test covers
these stage transitions, overrides, rank short-circuiting, multiple tokens,
suffix distinctions, invalid rank overflow, and unavailable profile data.
ASan/UBSan and the Windows build (`/tmp/sh1x-unlock-rules-final-win32.log`)
passed. The reader callback distinguishes unavailable data from a
false result and failure preserves the caller's output. No constant unlock
result or gameplay binding was added. Trusted identity, CoDOL-to-IW4 profile
field mapping, table lookup, and integration remain required.

Additional disassembly resolves IW4's XP-to-rank helper at 0x4ff8a0: it performs
a binary search over `mp/rankTable.csv`, compares total XP against columns 2
(minimum) and 7 (next total), and converts column 0 of the selected row to rank.
The vendor CSV also has header and maxrank rows; blindly assuming that the raw
CSV's row number is the rank would be incorrect. This conversion is not yet
connected to CoDOL's secure one-based rank plus within-rank XP.

The current vendor-script compile failure is the player method
`isItemUnlocked` at `maps/mp/gametypes/_teams.gsc:629`. The reference also calls
it for primary/secondary weapons, attachments, camouflage, perks and
deathstreaks in `_class.gsc`. Returning a constant merely to compile would
change loadout validation.

alpha0022 `gsc/gscbuiltins.py:1634` delegates to the host when available and
otherwise returns true. `gsc/host.py:541` also returns true, citing an
everything-unlocked policy. This is not a player-profile implementation.

Static executable evidence collected on 2026-09-08:

- IW4x's method table at 0x79afc0 binds `isitemunlocked` to 0x5f9960.
  It validates a player, obtains the player's stats buffer, loads
  `mp/unlocktable.csv`, and looks up argument zero in column zero. A missing
  row returns true. A found row calls 0x40d630 with the profile descriptor.
- IW4 0x40d630 reads columns 2, 3 and 1. It has category-specific profile
  checks, checks the required rank when column 2 is nonempty, and checks
  semicolon/whitespace-separated requirements from column 3. Thus it is not
  equivalent to the reference Python host's unconditional result. Exact
  category/challenge schema interpretation remains to be completed.
- C1 0x5544d0 instead installs the diagnostic string at 0xc599b0,
  `IsItemUnlocked is a depricated function`, calls script-error handling
  0x5cd3a0, and only afterward has an add-int-1 path. The error must not be
  omitted when interpreting this as engine behavior. This finding came from
  on-disk disassembly, not a live invocation.

The frontend unlock flags described in alpha0022 `docs/ui_unlocks.md` are a
different mechanism: notification/flag tables and the server's
`cg_unlockFlagSet` command. That document does not establish the semantics of
the deprecated GSC player method. Do not substitute UI flags for IW4 profile
requirements without evidence connecting the item names and categories.

A trusted offline zone-reader check found no `.gsc` rawfile names in
`code_post_gfx_mp` (69 type-36 assets) or `common_mp` (236). `mp_bog_sh` has
six rawfiles, with two GSC names: its FX and createfx scripts. No type-40
assets were found in those three zones. This limited check did not locate a
shipped `_teams`/`_class` replacement; it does not prove scripts are absent
from every archive or external source.

No new binding has been registered for this method. Native IW4 compatibility
requires completing its table/profile rules and mapping the CoDOL profile
schema, or finding the actual CoDOL script replacement. The existing
32768-byte native client profiles and mounted structured-definition reader
provide the inputs for further work. Full vendor compilation remains
incomplete; no server/client process was launched or modified for this audit.

Further IW4 tracing resolves the category overrides to `title` / `icon`,
reading `titleUnlocked[item]` and `iconUnlocked[item]` through 0x60d570.
The column-2 threshold reads `experience` and passes it to 0x4ff8a0 before
comparison; exact XP-to-rank conversion still needs porting. Requirement
helper 0x60d640 defaults the required stage to 1, removes a final underscore
and single digit when present, and requires `challengeState[name] > stage`
(strictly greater). The threshold must not be changed to greater-or-equal.
The decoded CoDOL player definitions contain `experience` and `rank`, but
no exact `challengeState`, `titleUnlocked` or `iconUnlocked` property names.
This does not prove no equivalent data exists under other names.

`codol_profile.c` now provides native schema-validated access to complete
client uploads. It selects the unique matching definition by version and
format checksum at upload offsets 4 and 8, then exposes the structured record
after the four-byte CRC prefix. Record size must fit the remaining upload.
Scalar field reads use the native path resolver and mapped storage reader;
no IW4 field layout or unlock policy is assumed. Outputs remain unchanged
on incomplete uploads, missing/ambiguous definitions and invalid bounds.
CRC authenticity is not established by this accessor.

Linux ASan/UBSan passed its focused test using real native chunk assembly and
two synthetic client profiles, including partial uploads, version/checksum
selection, nonidentity mapped field access, client isolation, ambiguity and
oversized definitions. The Windows build passed (`/tmp/sh1x-profile-win32.log`).
This is profile-access infrastructure, not a completed `isItemUnlocked` binding
or verification against a live player's unlock data.

The reference schema comparison was refined: `experience` and `rank` are
root fields in `mp/playersecuredata.def` (v11, checksum 158043991, size 6665).
They are absent from the public `mp/playerdata.def` root (v220,
checksum 0xe4fd5218, size 6650). The current synthetic upload matches the
public definition. Secure rank/challenge data must not be inferred from that
public upload or from a similarly named field in another definition.

`codol_checkprofile <client> <schema> <root scalar field>` now exposes a
console diagnostic using the mounted schema and native profile accessor.
An isolated native Bog server on UDP 17767 loaded the real public definition
and returned `acestreak` bits 1234 after encrypted upload of a synthetic
v220 profile with that short at upload offset 12 (record offset 8). The
transport probe's optional `--profile-rcon-password` sends the query through
the same encrypted association and asserts the response. This validates
mounted schema selection, mapped field access and the CRC prefix together.
It does not establish secure-profile transport or actual unlock state.

The initial plaintext console attempt received no response. The encrypted
attempt reached RCON but exposed a probe assumption that all OOB responses
end with NUL; RCON print replies do not. The optional console receive path
now retains the raw payload while existing OOB checks still require NUL.
The rerun passed. Windows build: `/tmp/sh1x-profile-mounted-win32.log`.
Probe home: `%TEMP%/sh1x-profile-mounted-20260908-084138`; its server was
stopped after verification. C1 and the Python lobby remained responsive.

The lobby's secure-profile source is storage GETFILE `mpdata_s`, not the
public UDP stats upload. `dw-capture.py` prefers `resources/mpdata_s.<uid>`
when per-user mode is enabled, then uses the shared file or configured seed.
It may apply pending rank writeback before serving. The game-side Python rank
pump uses the shared file and does not itself establish per-user parity.
Native integration must bind file selection to the authenticated user and
preserve that precedence; blindly reading a shared profile is insufficient.

`playerdata_editor.py` documents stored files as zlib streams inflating to
32768 bytes, with CRC32 over decoded bytes 4 onward. Native
`CODOL_DecodeStoredProfile` now implements this storage-format boundary using
the existing bounded inflater, requiring exact output size, complete stream
consumption and matching CRC, and preserving caller output on any failure.
`CODOL_ProfileRecord` generalizes schema/header validation to an explicit
decoded buffer; the client-upload accessor delegates to it. This permits a
separately owned secure record without conflating it with the public upload.
No filesystem selection or client association is implemented by these APIs.

The reference rank service also establishes that secure `rank` is one-based
and `experience` is XP within that rank. A future compatibility query must
convert through the shipped rank table before using IW4 total-XP rules.

Linux ASan/UBSan passed native storage decoding and the profile-access tests.
Storage cases include all truncations of a synthetic valid stream, trailing
bytes, insufficient output capacity and a valid zlib stream with a wrong
profile CRC. Synthetic fixtures contain a secure-schema header and zero data;
no user profile was read or modified. Windows build passed in
`/tmp/sh1x-profile-storage-win32.log`. No live processes were changed.

Native identity audit: `CODOL_ReadConnectUserinfo` validates the 16-digit
claimed XUID and its consistency with the userinfo copy. The bdDTLS layer
validates the configured lobby security ID/key and endpoint association, but
does not currently bind that claimed XUID to an authenticated account. These
checks must not be described as account authentication, and the claimed XUID
must not select another user's secure file.

`CODOL_ReadSecureProfile` now implements read-only file selection given an
explicit trusted UID supplied by its caller: per-user decimal-UID filename
when enabled and nonzero, shared `mpdata_s`, then an optional seed basename.
Missing files fall through; existing unreadable, malformed or CRC-invalid
files fail without trying a lower-priority profile. Decoding is bounded and
failure preserves output. It does not seed/write files, apply pending lobby
rank reports, or bind itself to the unverified connection XUID. A trusted
session/account binding remains required before live per-player use.

Linux ASan/UBSan passed temporary-file tests covering precedence, maximum
64-bit UID formatting, per-user disable/zero UID behavior, invalid seed paths,
missing files, and corrupt higher-priority files. The Windows build passed
(`/tmp/sh1x-profile-selection-final-win32.log`). Only synthetic temporary
profiles were used; no lobby profile or live process was modified.
