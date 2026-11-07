# Lobby-dependent DATA rejection investigation, 2026-09-14

Status: investigated, root cause unconfirmed; no source/build/runtime change.

User log: restored send counter257/receive0, matching destination tag52483, DATA counters28..79 rejected by authentication. CRC lines are ordinary preceding startup output. Failures precede the29.651-second hitch, so that hitch cannot explain their onset.

Native codol_association.c first checks the stored derived key, then derives from shared_x and the latest securitykey.bin. codol_crypto.c checks HMAC over the six-byte record header and ciphertext before counter expansion/decryption. Therefore changing the counter epoch cannot repair these MAC failures. No authentication bypass is appropriate.

Read-only wiretap-20260914.jsonl review found nine distinct security keys in lobby connection generation7, from13:27:04 through13:57:58. All recorded writes succeeded. Startgame entries matched their preceding live observation. Raw keys were not copied into this report.

Candidate: cached C1 association uses an intermediate lobby key not represented by either the persisted derived key or latest file. Need a failed record plus its matching shared-X to validate against the connection's observed keys before implementing a bounded, session-scoped key history. Do not declare this established from key churn alone; wrong shared-X or a different association is also possible.

Separate source defect: restore forces received=1 even when saved receive_window=0; it also does not persist send_exhausted and adds256 without overflow checks. These are real persistence gaps but not an explanation for the logged HMAC failures. Do not conflate them with the current failure.

## Follow-up capture and association audit

`bin/home/main/qconsole.log` lines11303..11356 contain53 rejected records,
destination tag52483, low counters28..80. Lines11369..11373 subsequently show
new INIT, retransmitted INITs, and COOKIE_ECHO establishing a fresh association.
The current saved association is therefore a different generation: local
tag14391, peer tag10362, receive counter3541, nonempty replay window, saved
at2026-09-14 14:00:08 America/New_York.

Read-only comparison using the existing Tiger implementation found that this
successful saved association's derived key exactly matches
`Tiger(saved shared-X || latest observed lobby key)`. The matching observations
are15 (live-observed13:57:58.355) and16 (startgame13:57:59.526), both lobby
connection generation7. No key bytes or shared secret are reproduced here.
This confirms the latest-key derivation works for the fresh association. It
does not identify the security material needed by the earlier failed one.

Capture inventory does not contain the decisive earlier DATA bytes:

- Today's `alpha0022/captures/wiretap-20260914.jsonl` has lobby tasks/pushes,
  security-key writes, and STUN records. Its only two UDP detail entries are
  type20, four bytes each. It has no captured type6 DATA or matching shared-X.
- Workspace `obj/dtls-diagnostic-retry.pcapng` and `dtls-rejection.pcapng`
  date from September10. They cannot establish today's failed association.
- Python's `alpha0022/dtls_capture.txt` records full DATA plus shared-X, but
  its last modification is September4. Its capture producer is in
  `game-server.py` around15580; that Python game server is not the current
  native game transport.
- `bin/home/codol_sessions.txt` contains the later successful association,
  not the earlier tag52483 state. No matching old state backup was located in
  the bounded workspace/capture inventory.

Proven: failures are associated with restored state; a fresh handshake later
succeeded with the latest lobby key. Still unproven: whether the lost context
was an intermediate lobby key, a different shared-X/peer association, or some
other stale state. No key-history retry implementation is justified as the
confirmed fix yet. The next useful evidence is one rejected full record plus
its contemporaneous association state; compare its MAC against observed
session-scoped candidate keys without emitting secrets or altering counters.

No native source, processes, installed assets, or runtime settings were changed.
No tests, builds, hooks, or restarts were performed.
