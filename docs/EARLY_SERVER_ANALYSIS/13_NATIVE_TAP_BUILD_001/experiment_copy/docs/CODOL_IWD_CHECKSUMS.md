# Native CoDOL IWD checksums

The native archive loader now includes C1's full-filename hash contribution in
each checksum word. This fixes the archive checksum mismatch identified by the
historical `cp @` command. The subsequent [CoDOL cp parser](CODOL_PURE_COMMAND.md)
uses these checksums for native IWD validation.

## Client evidence

C1.exe SHA-256:
`d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`.

`FS_Path_f` at 0x616386 reads `fs_searchpaths` from 0x6c3d8c4. Node+4 points to
the pack. The path printer reads entry count at pack+0x314 and compares the
checksum at +0x304 with the server pure list (0x616433). Archive loading writes
the ordinary checksum at +0x304 (0x615b72) and the seeded checksum at +0x308
(0x615bb2).

A read-only observation of C1 PID 59512 on 2026-09-08 collected 39 loaded archive
records. Both checksums were equal in every record. All 17 preceding values in
alpha0022's historical `netchan_ack._REAL_INBOUND` `cp` command matched these
live records, in search-path order. This resolves the historical/current-content
ambiguity for this list. Its final value equals the XOR of those 17 checksums
and 17, consistent with a zero feed. Records without process pointers are in
[CODOL_IWD_CLIENT_CHECKSUMS.json](CODOL_IWD_CLIENT_CHECKSUMS.json).

## Algorithm

At 0x6159f0 C1 hashes the complete lowercase filename, including its extension,
normalizing backslashes to slashes. The sum uses each signed character times
`(position + 119)`. At 0x615a1a it folds the sum as
`h XOR (h arithmetic-shift-right 10) XOR (h arithmetic-shift-right 20)` and masks
by `(archive hash-table size - 1)`.

For each nonempty file, 0x615a2f checks uncompressed size; 0x615a38 loads the
central-directory CRC; 0x615a44 adds the masked filename hash; and 0x615a4c stores
the 32-bit result. Words follow directory order. The native hash-table size
calculation agrees with all 39 live pack records.

The loop at 0x615b50 computes CRC32 of these little-endian words, starting at all
ones and complementing the result. For a nonzero feed, 0x615b83 complements the
feed before the same recurrence at 0x615b94. The retained native
`Com_BlockChecksumKey32` already implements this recurrence. The missing filename
contribution was the difference; the lookup hash cannot be reused because it
stops at the first dot.

`CODOL_IwdChecksumWord` implements the full-filename calculation with explicit
arithmetic shifts and modulo-32-bit arithmetic. `FS_LoadZipFile` uses it only in
the CoDOL build. The lookup hash and non-CoDOL checksum path are retained.

## Validation

`tests/test_codol_iwd_crypto.py` accepts an optional environment variable
`CODOL_IWD_CHECKSUM_CATALOG`. Given this catalog and the C1.exe argument, it
derives the archive key through the native reader, opens original IWDs through
the native ZIP implementation, reads decrypted filenames and entry CRCs, calls
the native checksum-word function, and compares final CRC32 values with the
independently observed client records. All 39 archives match: model, image,
stripped-image, configuration, sound and localized archives. This reads central
directories and does not claim file-content validation.

The optional run passed in `/tmp/sh1x-iwd-checksum-live.log`. No debugger was
attached and no client memory was changed. Nonzero-feed behavior is supported
by the static loop; no live nonzero-feed record was sampled. The `cp` parser has
subsequently been replaced; validating real C1 reaching CS_ACTIVE remains outstanding.

The forced Linux build and complete `test-codol` target passed in
`/tmp/sh1x-iwd-checksum-linux.log`; the forced Windows server build passed in
`/tmp/sh1x-iwd-checksum-win32.log`. C1 and the Python lobby remained responsive.
