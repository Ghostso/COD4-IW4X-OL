# Native Bog baseline

`native_bog_baseline.bin` is a 3,078-byte plaintext snapshot section emitted by
the native sh1x Windows server on 2026-09-08. It starts at opcode 0, includes the
seven-byte snapshot header and ends at EOF. It contains no transport keys or
credentials. The four-byte reliable client-command ACK is excluded.

Source: isolated UDP 17750 probe, home
`%TEMP%/sh1x-snapshot-decode-20260908-070808`, minimal node VM fixture scripts,
map `mp_bog_sh`, snapshot sequence 4, server time 6600. The synthetic peer completed
native encryption, stats upload, gamestate, checksum validation and a first
movement command. This fixture is server output, not a packet accepted by C1.

Run `tests/test_codol_snapshot_decode.py --reference <trusted alpha0022>` to check
it using the reference's independently transcribed client readers. The check
requires their existing dependencies and does not launch either server.

`native_bog_delta_base.bin` and `native_bog_delta.bin` come from the isolated
UDP 17751 probe on 2026-09-08, home `%TEMP%/sh1x-delta-20260908-071739`.
The same minimal scripts were used. Baseline sequence 6 (time 5650, 3078 bytes)
was acknowledged in a second native `clc_move` packet, using the updated
message-ACK-dependent usercmd key. Sequence 7 (time 5800, 1758 bytes) identifies
sequence 6 as its base. Both sections decode to exact EOF; the delta changes
player state and retains 140 entities and all 35 brush models. The server log
confirms 32 verified IWD checksums and CS_ACTIVE. No vendor-script gameplay or
real C1 acceptance is established by these fixtures. The isolated server was
stopped after capture; the existing C1 and Python lobby processes were retained.

The delta reader currently rejects changed client records and nonempty animation
commands/reserved player arrays; this fixture does not validate those cases.
Reproduce capture with `tools/codol_transport_probe.py` using `--move --delta`
and `--snapshot-output <baseline.bin>` in addition to the encrypted handshake,
stats, gamestate, and pure-catalog options. It saves the delta and sequence
metadata alongside the baseline.
