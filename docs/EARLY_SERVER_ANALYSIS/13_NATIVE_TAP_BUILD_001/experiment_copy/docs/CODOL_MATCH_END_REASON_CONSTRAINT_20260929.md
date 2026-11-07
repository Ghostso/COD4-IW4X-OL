# C1 match-end reason and secure-profile refresh boundary

Observed client: `E:\codol-classic\C1.exe`, SHA-256
`086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F`.
The addresses below are virtual addresses in this executable. They were checked
against its bytes and 32-bit x86 disassembly on 2026-09-29.

In the human score-limit run, the server sent `t
"EXE_MATCHEND_PARTNER_LEAVE"`, and C1 displayed a false partner-left notice.
That reason invalidated C1's cached secure profile so the lobby's updated
`mpdata_s` could be fetched. The normal match result is written before
`exitLevel`.

## Client control flow

- `CL_HandleDisconnect` starts at `0x004960E0`. The `EXE_MATCHENDED` comparison
  is at `0x0049610A` using `0x006283D0`; equality at `0x00496114` takes the
  `0x00496116` branch, which calls `Com_Error(5, ...)` and returns at
  `0x00496165`. It never reaches profile invalidation.
- The other bypass reasons are `EXE_MIGRATIONABORTED`,
  `EXE_MIGRATION_IN_PROGRESS`, `hostquit`, the `EXE_PLAYERKICKED` prefix,
  `roundsdone`, and `XBOXLIVE_SIGNINCHANGED` (comparisons at
  `0x00496166..0x00496255`). They also return or jump past invalidation.
- A non-bypassed reason reaches `0x0049627D`. When the saved client state is at
  least 8, `0x00496283` clears byte `0x06C3D3D9`, and `0x0049628A` clears
  DWORD `0x06C3D3DC`. The lobby-connected Demonware tick then has the
  conditions for a new `mpdata_s` request, as documented in
  `CODOL_RANK_XP_20260915.md` section 9f.
- `EXE_MATCHEND_PARTNER_LEAVE` is compared at `0x00496294` and additionally
  calls `0x00624FC0(handler, 1)` at `0x004962AC`. Its effect is unverified.
  The common non-bypassed path then builds a localized
  `EXE_SERVERDISCONNECTREASON` message and calls `Com_Error(4, ...)` at
  `0x004962D8`. Thus a notice is expected even if another non-bypassed string
  replaces the current one.
- `0x006283D0` compares ASCII case-insensitively (`A..Z` folded by adding
  `0x20`). A case-only variant of `EXE_MATCHENDED` still takes its bypass.

## Consequence

The `t` reason alone cannot produce both C1's quiet normal-match exit and an
immediate profile refetch. C1's independently recovered `K` command writes
directly into the same cached secure record that its rank and career pages
read. The server already sends in-match profile changes this way, but normally
batches for 250 ms. The source now forces a final `K` flush immediately before
the reliable `t "EXE_MATCHENDED"`, preserving their order in one reliable
stream. The backend still applies the written match report for persistence.

This is a source-level resolution of the conflicting reason strings, not yet a
real-client result. Verify on one C1 process: normal score-limit end and return
to lobby; no partner-left or generic disconnect popup; result summary
preserved; new match XP and unlock state visible without restart. Compare
the displayed rank/XP to the backend account after the report folds. Keep one
dedicated server on UDP/17733 during the test.
