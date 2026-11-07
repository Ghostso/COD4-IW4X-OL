# CoDOL reliable traffic

CoDOL uses the encrypted native netchan stream for gamestate fragments and
reliable text commands. IW4OL's separate binary reliable transport uses sequence
marker `0xfffffff0` and is not part of that protocol. An isolated encrypted probe
previously observed one such packet after connection despite successful CoDOL
gamestate delivery and a reliable client-command acknowledgement.

The CoDOL build now excludes binary-channel allocation at direct connect and
binary-channel transmit/receive servicing in the client frame loop. Incoming
`0xfffffff0` markers are discarded before netchan processing. The old binary
send API reports unsupported use instead of dereferencing the absent channel.
IW4OL file download requests are explicitly rejected; CoDOL file transfer has
not been implemented. These changes do not alter the retained non-CoDOL paths.

`tools/codol_transport_probe.py --upload-stats --request-gamestate
--ack-gamestate` rejects legacy binary-channel output. It also sends an encrypted
legacy marker before a valid reliable client command, then requires the command
acknowledgement to prove the marker did not crash or poison the connection.

Validation on 2026-09-08: forced Linux build plus the full `test-codol` target
passed (`/tmp/sh1x-reliable-retirement-linux.log`); forced Windows build passed
(`/tmp/sh1x-reliable-retirement-win32.log`). The isolated native server on UDP
17745 delivered all 743 configstrings in a 2,992-byte gamestate across three
encrypted fragments, with zero IW4OL reliable packets. All 27 synthetic stats
chunks completed, and reliable command 1 was acknowledged after the injected
legacy marker. The test home was
`%TEMP%/sh1x-reliable-retirement-20260908-062017`. The initial probe failed during
startup at its COOKIE_ACK check; the probe now tolerates exact duplicate
INIT_ACKs from its startup retry loop. A rerun against the same running server
passed. Only the isolated probe server was stopped; C1 and the Python lobby
remained running and responsive. This synthetic transport check does not verify
real C1 movement, the vendor gametype, or a match.

## Next connection gate

The retained `SV_VerifyPaks_f` parser expects `cp @ L<locale> <serverid>` followed
by checksums. Alpha0022's `docs/usercmd_starvation_20260902.md` and
`docs/INTEGRATION-NEXT.md` instead document C1 sending `cp @ <18 signed integers>`
before menu interaction. The latter explicitly says their contents are
unidentified and assembled in virtualized `.tvm0` code. That is evidence of a
format mismatch, not proof that these values authenticate the client's assets.

The retained parser interprets the first integer as a locale after skipping its
first character, and the second integer as a server ID. Its early ID mismatch
can leave `pureAuthentic` zero, which gates `SV_UserMove` with `sv_pure` enabled.
The CoDOL checksum semantics still require recovery; this change does not bypass
that gate or claim a real-client match.

### Checksum analysis, 2026-09-08

`tools/codol_pure_analysis.py` now reads the historical `_REAL_INBOUND` fixture
from alpha0022's `netchan_ack.py` and compares its `cp` integers against current
IWD central-directory checksum candidates. The saved result is
[CODOL_PURE_ANALYSIS.json](CODOL_PURE_ANALYSIS.json).

There are 18 signed integers. The XOR of the first 17 is `0xd0859caf`; the final
integer is `0xd0859cbe`. Their XOR is exactly 17. This is consistent with 17
archive checksums followed by `checksumFeed XOR checksumCount XOR checksums`,
with feed zero. It is an inference from one historical fixture, not proof that
all CoDOL `cp` commands use that count or that those assets belong to this build.
It gives no support for interpreting the first two integers as locale/server ID.

The tool inspected all 39 current `main/*.iwd` archives without reading file
contents or decrypting names. For each archive, it collected central-directory
CRCs for nonempty entries in directory order, matching the retained native
`FS_LoadZipFile` input construction. No captured checksum matched any of:

- CRC32 with feed zero (the current native `Com_BlockChecksumKey32` algorithm).
- XOR-folded MD4 of the CRC vector.
- XOR-folded MD4 of a zero feed word followed by the CRC vector.

This rules out accepting the historical list against these candidate checksums
for the current installation. It does not distinguish a different checksum
algorithm from different historical archive contents. Further evidence must
identify the current C1 checksum producer or obtain a fresh `cp` from this
installation and compare it against the same archives. Neither the historical
list nor its aggregate should be hardcoded as an authentication baseline.

A read-only check of C1 PID 59512 found reliable sequence and acknowledgement both
zero and no `cp` in its 256-slot reliable-command ring. The ring address came
from alpha0022's measured client-connection pointer and offsets; the process was
not attached to a debugger, paused, or modified. No fresh live checksum list was
available from that ring at the time of the check. The server pure gate remained
unchanged at that point. Subsequent read-only archive-table inspection resolved
the checksum algorithm and matched all 39 current archives; see
[native IWD checksums](CODOL_IWD_CHECKSUMS.md). The subsequent
[CoDOL cp parser](CODOL_PURE_COMMAND.md) now uses these checksums.
