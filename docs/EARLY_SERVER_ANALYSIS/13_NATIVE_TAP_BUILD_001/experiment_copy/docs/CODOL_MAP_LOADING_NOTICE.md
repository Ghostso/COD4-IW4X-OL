# C1 map-loading notification

Offline C1.exe 1.1.1.13 evidence; no client/server execution.

The retained server used reliable command `l` with map and gametype. C1's
CG dispatch maps `l` to `0x469698`, which hashes argument 1, converts
argument 2 to a float, and calls audio code `0x739870`. It does not load maps.

C1 connectionless parser `0x497080` reads the packet header and first line,
tokenizes that line and calls handler `0x4963e0` (ordinary path call at
`0x497289`). The handler compares the command with `loadingnewmap` at
`0xc4812c`, comparison at `0x496e9b`. On a match it checks connection state,
queues local console text `uploadStats` (`0xc4813c`) through `0x58ba60`,
and compares the packet and connected-server
addresses through `0x5a3680`. The accepted branch calls line reader
`0x59f6d0` twice: first map at `0x496f3e` (copied into 64-byte storage), then
gametype at `0x496f6c`. That reader consumes bytes through newline or NUL.
The branch sets connection state 5 through `0x486e90` and calls loading
handler `0x499560`. That handler's diagnostic at `0xc48830` explicitly
identifies map and gametype.

The CoDOL branch in `src/sv_main.c:SV_SpawnServer` now sends:

```text
FFFFFFFF loadingnewmap\n<map>\n<gametype>\n
```

`FFFFFFFF` denotes four raw `0xff` bytes, with no following space;
`NET_OutOfBandPrint` supplies those bytes. Bot addresses are skipped. Native
non-CoDOL reliable notification and subsequent snapshot/teardown remain in
their existing paths.

The payload is derived from C1's actual consumer. The matching C1 server
producer, retransmission behavior, local uploadStats execution and full
map-change lifecycle remain unverified. This does not establish completed
fastfile loading, gamestate ingestion, or entry into a match. Misaligned
exploratory starts `0x496e90` and `0x497110` are not used as evidence.
