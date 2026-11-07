# CoDOL cp command

The CoDOL build now parses `cp @ <referenced IWD checksums> <aggregate>` as signed
32-bit decimal tokens. It no longer interprets the first two checksums as a
locale and server ID. The retained non-CoDOL parser is unchanged.

The format is evidenced by alpha0022's captured `netchan_ack._REAL_INBOUND`:
its first 17 integers match independently read live C1 archive records in search
path order, and its last equals their XOR and the count, at feed zero. The native
archive checksum calculation now matches all 39 C1 records; see
[IWD checksums](CODOL_IWD_CHECKSUMS.md).

`CODOL_VerifyPureChecksums` checks exact command framing, bounded signed integer
conversion, uniqueness of reported checksums, membership in the native loaded
nonlocalized IWD checksum list, and `feed XOR count XOR checksums` as the final
aggregate. It accepts a referenced subset, as the retained pure protocol does;
it does not require clients to report every server archive. The empty subset
has the feed as its aggregate. Both client and server lists are bounded at
1,024 checksums. Malformed or oversized server lists also fail validation.

`SV_VerifyPaks_f` uses the current native checksum feed and loaded checksum list.
Success sets `pureAuthentic` to 1; failure sets it to 2 for the existing movement
and client-entry handling. The client locale is untouched. A successful check
prints a developer message with the number of validated IWD checksums.
This validates IWD checksum claims, not fastfile contents. It does not add a
fake fastfile validation result or bypass the existing pure gate.

The focused test exercises the actual native command handler with command and
filesystem fixtures, signed limits, malformed values, duplicate and unknown
checksums, feed/aggregate mismatches, bounded lists, and purity-state updates.
The parser and test also pass AddressSanitizer/UndefinedBehaviorSanitizer; the
retained `sv_client.c` object is not instrumented in that focused link.

The transport probe's optional `--pure-catalog` argument sends a reliable `cp`
after stats, gamestate and a userinfo command. It derives seeded values from the
independent zero-feed C1 catalog using CRC32 linearity and the gamestate's feed.
Only nonlocalized records are included. The output reports command ACK separately
from validation: the native developer log must confirm the checksum check passed.
This probe is synthetic and does not establish real C1 movement or match entry.

Validation on 2026-09-08: forced Linux build and full `test-codol` passed in
`/tmp/sh1x-pure-linux.log`; forced Windows build passed in
`/tmp/sh1x-pure-win32.log`. The isolated native server on UDP 17746 used home
`%TEMP%/sh1x-pure-20260908-064001`. The probe completed the encrypted handshake,
all 27 stats chunks, the 743-configstring gamestate, and reliable commands 1
(userinfo) and 2 (cp). The gamestate published checksum feed 1914063344.
The native log confirmed `CoDOL verified 32 client IWD checksums`, proving the
seeded membership/aggregate check succeeded rather than merely acknowledging
the command. No IW4OL binary reliable packets were observed. The owned probe
server was stopped after process-identity verification; C1 and the Python lobby
remained running and responsive. No user movement packet was sent in this run.
