# Native Demonware association work

The native UDP path now supports a configured CoDOL association. An independent
synthetic encrypted peer completed handshake, challenge and connect over real
Win32 UDP sockets. Native CoDOL stats now also advances that synthetic peer to
CS_PRIMED and delivers a reassembled encrypted gamestate. Real C1 match entry is
not yet verified; see [stats upload evidence](CODOL_STATS_UPLOAD.md).

## P-224 exchange

`src/codol_ecdh.c` implements the missing public-key export and shared-secret
calculation using the existing mbedTLS P-224 backend. Public keys are 100-byte
padded libtomcrypt records: a SEQUENCE containing BIT STRING `07 00`, INTEGER
28, and the two positive coordinates. Coordinates use 28 bytes plus a sign byte
when required. Import also accepts shorter positive coordinates, validates the
record bounds and zero padding, and checks membership on the P-224 curve.

The caller supplies a valid private scalar and a cryptographic random generator
for multiplication blinding. Invalid scalars, malformed keys, off-curve points,
and RNG failures leave outputs unchanged. The resulting 28-byte big-endian X
coordinate is the input to `CODOL_DeriveKey` together with the session's 16-byte
security key. No live client, lobby process, or credential file is modified.

The protocol evidence is alpha0022 `dtls_crypto.py` functions `export_pubkey`,
`parse_pubkey`, and `shared_key20`, plus `game-server.py` around lines
15310–15533. The introduction of `dtls_crypto.py` contains obsolete SHA1/AES128
notes; its active implementation uses Tiger192 and AES192 for this build.

`tests/test_codol_ecdh.c` compares exported keys and shared X against independent
PyCryptodome P-224 vectors. It covers both sign-byte layouts, ECDH symmetry,
malformed records, invalid curve points and scalars, and RNG failure. The fixed
scalars and deterministic RNG in that test are test data only.

The RNG-failure test exposed a bundled mbedTLS defect:
`mbedtls_mpi_fill_random` discarded the RNG return code. It now propagates the
failure through the existing cleanup path. This also removes the leaked
allocations observed under LeakSanitizer when the ECDH blinding RNG failed.

Validation on 2026-09-08: full Linux `all test-codol` passed after the RNG fix;
the focused exchange test passed ASan/UBSan with leak checking enabled; a forced
Win32 server build passed. Logs are `/tmp/sh1x-ecdh-linux-final.log` and
`/tmp/sh1x-ecdh-win32.log` in WSL. These are offline/build checks, not client
connection evidence.

## DATA association state

`src/codol_association.c` now owns each established association's shared X,
derived key, local/peer tags, independent send and receive counters, and 32-bit
receive bitmap. The handshake owner must validate the peer and security ID
before starting it. A duplicate COOKIE_ECHO must reuse the owner's cached
response, rather than start the DATA state again.

The receive path authenticates before committing replay state. It permits
unseen reordered records within 32 positions, rejects duplicates and older
records, and extends the 16-bit counter using the existing full-counter codec.
On MAC failure it can derive a candidate from the trusted lobby's current
security key; the candidate replaces the active key only after authentication.
Rotation preserves both counter directions. Fresh association start clears
them. No credential file is read by this layer.

Each successful encryption consumes one send counter, regardless of payload
size, before socket submission. Socket failure must not rewind it: a retry
encrypts under a fresh counter. After sending UINT32_MAX the association refuses
further encryption instead of reusing IVs. There is no speculative receive-epoch
resynchronization. Evidence for the counter and replay rules is alpha0022
`dtls_seq.py`, especially its measured 32-packet window and documented client
`bdSequenceNumber` implementation.

`tests/test_codol_association.c` covers bidirectional records, out-of-order
acceptance, both replay-window boundaries, MAC/tag/length/capacity rejection,
16-bit rollover with late pre-wrap records, key rotation, send exhaustion,
first-record counters above 32768, and reset/clear behavior. It uses the actual
crypto primitives. The test's session keys are synthetic.

DATA-state validation on 2026-09-08 passed the full Linux `all test-codol`
suite, focused ASan/UBSan execution, and forced Win32 server build. Build logs:
`/tmp/sh1x-association-linux.log` and `/tmp/sh1x-association-win32.log` in WSL.
The state layer is now called by the native UDP owner described below.

## Stateful cookie handshake

`src/codol_handshake.c` now implements INIT/INIT_ACK and COOKIE_ECHO/COOKIE_ACK
state transitions. Its owner supplies the expected session security ID, binds
the object to a UDP endpoint, and provides a valid private scalar and fresh tag.
The INIT_ACK carries the observed IP and little-endian port. The exact issued
38-byte cookie is retained and compared when returned; zero signature/timestamp
fields do not bypass that comparison. The echoed security ID must also match.
The 37-byte common address is bounded opaque data, not a trusted routing address.

C1 static evidence establishes the nested cookie layout: COOKIE_ECHO serializer
0xa62220 calls the header serializer at 0xa6223a and its embedded INIT_ACK virtual
serializer at 0xa62255, then writes 37 bytes at 0xa62260, 8 bytes at 0xa6227b,
and 100 bytes at 0xa62296. Constructor 0xa62539 installs vtable 0xbe49ac;
its embedded INIT_ACK uses vtable 0xbe49c4 and serializer 0xa65750. That serializer
includes its own header. Thus COOKIE_ECHO is outer header[6], complete
INIT_ACK[38], common address[37], security ID[8], public key[100] = 189 bytes.
This agrees with alpha0022's offsets 81/89 for security ID/public key.

On valid echo the implementation derives ECDH and DATA state, emits its own
public key in COOKIE_ACK, and clears the retained private scalar. Exact
COOKIE_ECHO retransmissions return the cached ACK without resetting counters.
Changed echoes after establishment are rejected. Identical INIT retransmissions
reuse the cookie; a different valid INIT stages new state and clears the previous
DATA state on success. The endpoint owner must still supply timeouts, eviction,
freshness policy and game-client reset on a new association. The state functions
do not themselves authenticate player identity or send UDP traffic.

`tests/test_codol_handshake.c` checks exact INIT_ACK bytes, corruption of every
issued-cookie byte, tag/version/security-ID/public-key rejection, ECDH from the
returned ACK, bidirectional encrypted OOB records, retransmissions after DATA,
failed replacement preserving old state, fresh INIT and secure clear.

Handshake validation on 2026-09-08 passed the full Linux `all test-codol` suite,
focused ASan/UBSan (including the additional failed-replacement cases), and a
forced Win32 server build. Logs are `/tmp/sh1x-handshake-linux.log` and
`/tmp/sh1x-handshake-win32.log` in WSL. No live C1 association was attempted.

The lobby's trusted session-ID source was located in alpha0022 `dw-capture.py`:
`SESSION_ID = bytes([70, 0, 0, 0, 0, 0, 0, 0])`, returned by createSession and
included in StartGame. Its current session key is relayed through
`securitykey.bin`. Wiring the native owner to this reference setup remains work;
the handshake library neither reads that file nor accepts an arbitrary INIT ID.

## Native UDP owner

`src/codol_network.c` owns 64 endpoint-bound slots. `NET_UDPPacketEvent` dispatches
to it before plaintext parsing. Valid DATA passes through MAC/replay checks and
then into `SV_PacketEvent`. `NET_SendPacket` encrypts server traffic for the
established endpoint, including connectionless responses and each netchan
fragment; handshake replies call the raw socket function directly. Enabled
transport drops plaintext inbound traffic and refuses outgoing packets without
an established association. No hooks, injected client code or Python relay are
used by this path.

Configuration:

- `codol_securityKeyPath`: path to the trusted lobby's exact 16-byte session-key
  file. Empty retains plaintext diagnostic mode. Missing/malformed files prevent
  new handshakes; there is no zero-key fallback. Established DATA can still use
  its current authenticated key while the file is temporarily unavailable.
- `codol_securityId`: 16 hex digits, default `4600000000000000` for alpha0022's
  SESSION_ID. INIT must match this configured ID.

For the supplied lobby, point `codol_securityKeyPath` at alpha0022's
`securitykey.bin`. The native code reads it only; it does not modify lobby
credentials or settings. Changes to the configured path/ID clear association
state. Successful new INIT disconnects an old game client at that endpoint.
Pending slots expire after 10 seconds, established slots after 120 seconds
without accepted receive activity; outbound traffic does not keep keys alive.
Server shutdown clears all slots. IPv4 is implemented; IPv6 and Demonware NAT
traversal messages are not yet implemented.

The owner uses alpha0022's known-working P-224 scalar `01 02 ... 1c`, obtains
fresh tags from `Sys_RandomBytes`, and supplies the platform RNG for ECDH
blinding. This keeps the C1 shared X reproducible across native restarts and
avoids the observed all-record MAC failure with randomized COOKIE_ACK keys. It reloads the session key on
incoming DATA so the authenticated rotation behavior follows the existing lobby.
The reference's single session-ID/key-file design is preserved; independent
per-player lobby credentials would require a session lookup provider.

`tools/codol_transport_probe.py` is a synthetic peer for an isolated server,
using the independent alpha0022 Python crypto implementation. It requires a
separate test key file and refuses the live reference `securitykey.bin`. It
checks encrypted handshake/challenge/connect, plaintext rejection, replay
rejection, bad-MAC rejection without consuming the valid counter, and identical
COOKIE_ACK retransmission after DATA. Optional `--request-gamestate` reports
the types of encrypted packets returned after an in-band request.

Validation on 2026-09-08: full Linux `all test-codol` passed; the final incremental
Linux build and forced Win32 build passed. Logs: `/tmp/sh1x-network-linux.log`,
`/tmp/sh1x-network-linux-final.log`, `/tmp/sh1x-network-win32.log` in WSL.
The real UDP probe used localhost 17742 with home
`C:/Users/Michael/AppData/Local/Temp/sh1x-encrypted-20260908-054442` and a synthetic
key. Both encrypted connection runs logged `CS_FREE` -> `CS_CONNECTED`; the first
returned server DATA counters 1 and 2 without reset on cookie retransmission.
The in-band run then received encrypted empty frames and IW4OL `0xfffffff0`
reliable messages, not gamestate. At that point `SV_SendClientGameState` called
`SV_ConnectSApi` and `SV_RequestStats` before advancing to CS_PRIMED. The latter
emitted `clc_statscommands`, set `receivedstats = -1`, and returned false.
The subsequent native CoDOL stats implementation replaces that flow and passes
the encrypted gamestate probe documented in `CODOL_STATS_UPLOAD.md`. Probe process
19708 was stopped after checking its executable and unique home argument.
Existing C1/Python processes were unchanged and responsive.

## Remaining connection integration

Remaining integration work:

- Verify native gamestate ACK, user commands and live snapshots with C1, while
  preserving the existing auth/lobby service.
- Exercise session-key rotation and endpoint timeout/reconnect through the
  complete UDP owner, beyond the primitive fixtures. Fragmented gamestate now
  passes the synthetic encrypted peer probe.
- Integrate Demonware NAT traversal if required by the lobby's selected route.

The connectionless responses now use `src/codol_connect.c`: `SV_GetChallenge`
sends only the retained integer cookie challenge and omits IW4OL authorization
server lookups/extensions. `SV_DirectConnect` sends mapname, gametype, the real
configured client limit, protocol **1** and shortversion **1.1.1.13**. Both packets
include the four-byte OOB prefix and trailing NUL. Invalid session descriptions
are rejected before client allocation.

Correction to the initial analysis: `game-server.py`'s fallback and comments
suggested 187/1.2, but its active `dvars.connect_response` helper explicitly
records a live 2026-09-02 bisect in which 187 stalled the client and 1 connected.
Both branches of that helper default to 1/1.1.1.13. Dvar 2490's ROM value 187
does not establish the connect-response wire value. The helper does not claim
that shortversion 1.2 was independently proven broken. The earlier statement
that `protocol_map.md`'s protocol-1 response was stale was incorrect.

`tests/test_codol_connect.c` checks exact response bytes and token/capacity/client
limit rejection, and invokes the actual `SV_GetChallenge` entry point with a
fixture cookie service and captured socket sends. The native connect acceptance
path is not exercised by that test; association and real-client checks remain.

Offline decryption of alpha0022 `dtls_capture.txt`, line 2, verified its DATA MAC
and established the incoming envelope: `connect <xuid> "<userinfo>"`. Userinfo is
argument 2, not the retained IW3 argument 1. It contains `xuid`, `challenge`,
`qport`, and numeric key `2490`, but no textual `protocol` or `shortversion`.
The observed `2490` value is -1157214325, not 187. Its encoding is unresolved;
the server must not equate it with a plain protocol dvar. No captured credentials
or real player identifiers are included in the regression fixture.

The native handler now reads argument 2 after validating a 16-hex envelope XUID
and one matching userinfo XUID. It rejects malformed/truncated info strings and
keeps internal codec selection at `CODOL_PROTOCOL` (187), independently of the
opaque client field and outgoing connect-response value (1). XUID consistency
is not identity authentication; that still belongs to association/session
validation. Existing address-cookie challenge checks and game connection checks
remain in force. Real-client authenticated connection acceptance remains unverified.

Connection validation on 2026-09-08 passed full Linux `all test-codol`, the
Win32 rebuild, and ASan/UBSan for the response/parser fixture (the retained
`sv_client.c` object was linked without sanitizer instrumentation to avoid
retaining unrelated VM command tables). Logs: `/tmp/sh1x-connect-linux-final.log`
and `/tmp/sh1x-connect-win32.log` in WSL.

An isolated Win32 server on localhost port 17741 loaded the Bog VM fixture.
A synthetic plaintext UDP request received a NUL-terminated challenge with one
integer argument, then a NUL-terminated connect response for `mp_bog_sh`, `dm`,
16 clients, protocol 1 and shortversion 1.1.1.13. The server logged
`CS_FREE` -> `CS_CONNECTED` for the synthetic client. The probe home is
`C:/Users/Michael/AppData/Local/Temp/sh1x-connect-20260908-052826` and its process
65700 was stopped after verifying its executable and unique home argument.
The startup log also reports missing `steam_api.dll`; it did not prevent this
exchange. This probe exercised real socket dispatch and native connection
allocation, but bypassed the still-unconnected bdDTLS layer and did not send
gameplay commands. Existing C1 and Python processes were not modified.

The reference's unsigned cookie and fallback that echoes the client's public
key are not sufficient native association implementations. No association or
authenticated match is claimed by these exchange primitives.
