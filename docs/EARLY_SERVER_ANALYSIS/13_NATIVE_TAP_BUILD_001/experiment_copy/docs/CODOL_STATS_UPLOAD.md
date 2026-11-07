# Native CoDOL stats upload

C1's post-connect upload differs from both IW4OL and alpha0022's current shortcut.
The client sends OOB `stats\0`, qport (uint16 little endian), chunk index (uint8),
then profile bytes. The server returns OOB `statResponse <missing-mask>\0`.
The argument is a bitmask of missing chunks, not the received chunk index.

## Evidence

- C1 connect-response handling at 0x496998 enters state 6, clears 27 per-chunk
  send times, and sets the missing mask to 0x07ffffff at 0x4969bb.
- Chunk selection at 0x495970 tests each mask bit and scans 27 slots
  (comparison at 0x4959ad). It chooses an unsent/oldest outstanding chunk.
- The sender at 0x495b60 uses `index * 0x4d8` as the profile offset. At
  0x495ba3–0x495bbf it sends `min(1240, 32768 - index * 1240)` bytes.
  Thus chunks 0–25 are 1240 bytes and chunk 26 is 528 bytes.
- The statResponse handler at 0x496a71 parses argument 1 as an integer.
  Nonzero is masked with 0x07ffffff and stored at 0x496aa8–0x496aad. Zero
  transitions out of SENDINGSTATS and clears the mask at 0x496a8e–0x496a9c.
- Offline decryption of alpha0022 `dtls_capture.txt` line 3 verifies the DATA
  MAC and shows a 1253-byte plaintext packet with index 0 and 1240 profile bytes.
  No captured profile data is copied into tests.

The active Python server echoes the received index. For index 0 that sends zero
and prematurely finishes the upload. Its comments identifying statResponse as
a chunk acknowledgement do not match C1's handler. The native server implements
the measured mask protocol instead.

## Native ownership and integration

`src/codol_stats.c` retains 32768 bytes and a received-bit mask per client slot,
outside the retained assembly-sensitive client layout. Wrong indices/lengths
are rejected. Identical retransmissions are acknowledged; conflicting duplicate
payloads leave the accepted data unchanged. `CODOL_ClientStats` exposes the
owned blob only when all 27 bits are present. Profile schema interpretation and
GSC profile queries remain separate work; these bytes are not copied into the
incompatible retained IW3 stats structure.

Native `SV_ReceiveStats` requires an authenticated DATA association, locates the
connected client by address/qport, stores the actual chunk, updates its timeout,
and returns a NUL-terminated missing mask through encrypted `NET_SendPacket`.
Client allocation, disconnect and bot reset clear the store.

`SV_SendClientGameState` now requires a verified DATA association and the complete
CoDOL upload. It no longer requests IW4OL `clc_statscommands` or calls the IW4OL
SApi/XAC handshake in the CoDOL build. The game and ban checks remain. A connected
client with a complete upload can also receive the reference's
`heartbeatresponse` reply. Incomplete uploads do not unlock gamestate.

## Verification scope

`tests/test_codol_stats.c` covers reverse-order chunks, exact final length,
missing masks, identical/conflicting duplicates, full byte preservation,
slot isolation, invalid indices, reset and response framing. It passes with
ASan/UBSan. The full Linux `all test-codol` suite passed after integration
(`/tmp/sh1x-stats-linux.log`).

`tools/codol_transport_probe.py --upload-stats --request-gamestate` uploads a
synthetic profile to an isolated native server, verifies every encrypted mask,
then checks heartbeat and reassembles/de-XORs gamestate. It does not launch or
modify C1, and a successful probe is not evidence of a playable C1 match.

The Win32 build passed (`/tmp/sh1x-stats-win32.log`). The live synthetic peer on
localhost port 17743 then verified all 27 masks, heartbeat and a 2985-byte
gamestate reassembled from three encrypted fragments, netchan sequence 3, map
`mp_bog_sh`, zone `mp`. No IW4OL reliable packets appeared in the gamestate
exchange. The native log confirms `CS_CONNECTED` -> `CS_PRIMED`.

Probe home: `C:/Users/Michael/AppData/Local/Temp/sh1x-stats-20260908-055750`.
Its process 34760 was stopped after executable/home validation. Existing C1
and Python processes were untouched and responsive. This proves encrypted
transport, full upload ownership and gamestate production; it does not prove
that C1 accepts every configstring/asset, acknowledges gamestate or enters play.
