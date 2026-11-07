# Native PrecacheFxTeamThermal

The Python reference registers this function at alpha0022/gsc/gscbuiltins.py:1046.
Its handler records `effect@tag` in a precache ledger; that representation is not
the C1 configstring format. The native implementation uses the measured client
executable instead, without hooks or live process modification.

C1 1.1.1.13 (SHA-256
`d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`):

- Builtin 0x550130 checks initialization and exactly two arguments, reads the
  effect integer and tag, rejects quotes, formats `%03d%s`, and calls 0x54f9d0
  with the half-open configstring range [6100, 6132).
- Range helper 0x54f9d0 searches case-insensitively for a duplicate before
  choosing the first effective empty entry. All 32 thermal slots are usable.
- Effect lookup 0x570730 uses base 3651 and IDs 1..319; zero is reserved.
- IW4's matching builtin is 0x5f83c0, with the same formatting and timing rules
  but a different configstring range. Its indices must not be sent to C1.

The source binding retains IW3 `loadFx` IDs for the engine, resolves their
registered names through `CS_FX`, and selects the corresponding CoDOL effect ID
from the effective inherited/override bank. It lowercases the attachment tag,
reuses inherited matches, and publishes new thermal records. Both allocations
are prepared before either bank entry changes. Invalid inputs or exhausted
banks raise a script error without partial registration. Tags above 1020 bytes,
control characters, and invalid effect-name tokens are rejected rather than
truncated. This is a bounded native input policy, not exact retail truncation.

Validation on 2026-09-08:

- 32-bit ASan/UBSan test `tests/test_codol_team_fx.c` passed namespace translation,
  inherited reuse, case-insensitive thermal deduplication, final-slot boundaries,
  atomic capacity failures, and VM timing/argument gates.
- Windows server build passed (`/tmp/sh1x-team-fx-win32.log`).
- Isolated native Bog fixture on UDP 17781 printed `SH1X_THERMAL_VM_PASS`.
  The mounted constant table identified `misc/thermal_beacon_inverted` at 3730,
  meaning CoDOL effect ID 79. The regular spine attachment was inherited.
  A distinct diagnostic tag exercised a new override, decoded from encrypted
  gamestate as `079sh1x_thermal_probe`, with no duplicate after changing case.
  Full and delta snapshots also passed the synthetic peer decoder.
- Full-reference compilation on UDP 17782 advanced to missing player method
  `WeaponLockFinalize` in `maps/mp/_stinger.gsc:339`. Both probes were stopped;
  C1 and the Python lobby remained responsive.

The diagnostic tag proves registration and serialization, not attachment
rendering. General retained playFx/event translation and real C1 match entry
remain separate requirements. The complete IW4/T5 builtin surface is unfinished.
